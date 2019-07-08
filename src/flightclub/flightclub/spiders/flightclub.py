# -*- coding: utf-8 -*-

import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

import json
import datetime
import os
import re

# TODO: put these in a shared lib folder?
def get_run_paths(source):
    time_now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    data_prefix = "../../data/{}.data.{}/".format(source, time_now)
    data_path = os.path.join(data_prefix, "{}.txt".format(source))

    log_prefix = "../../logs/{}.logs.{}/".format(source, time_now)
    log_path = os.path.join(log_prefix, "{}.log.txt".format(source))
    exceptions_path = os.path.join(
        log_prefix, "{}.exceptions.txt".format(source))
    
    debug_dir = os.path.join(log_prefix, "all")
    if not os.path.isdir(data_prefix):
        os.makedirs(data_prefix)
    if not os.path.isdir(log_prefix):
        os.makedirs(log_prefix)

    return {
        "time": time_now,
        "data": data_path,
        "log": log_path,
        "exceptions": exceptions_path,
        "debug_dir": debug_dir
    }

def write_entire_page(name, content):
    with open(name, "w") as wfile:
        wfile.write(content)
    return

class ShoesSpider(scrapy.Spider):
    name = 'flightclub'
    allowed_domains = ['www.flightclub.com', 'sell.flightclub.com']

    """cached mapping from style ID (flightclub) to the item's ID on flightclub
    consignment portal.
    """

    def __init__(self, log_all=False, **kwargs):
        """

        Initialize. Load style ID to sell IDs map.
        """
        self.start_urls = ['https://www.flightclub.com/']
        self.log_all = True if log_all else False

        self.prices = {}
        self.sell_prices = {}

        self.style_id_to_sell_id = \
            "../../data/flightclub/style_id_sell_item_id_map.txt"

        if os.path.isfile(self.style_id_to_sell_id):
            with open(self.style_id_to_sell_id, "r") as rfile:
                self.style_id_sell_item_id_map = json.loads(rfile.read())

        self.style_id_sell_item_id_map = {}
        self.queried_sell_price = {}
        self.request_headers = {'User-Agent':'Mozilla/5.0'}

        paths = get_run_paths(ShoesSpider.name)
        self.data_path = paths["data"]
        self.debug_dir = paths["debug_dir"]

        super().__init__(**kwargs)
        return

    def start_requests(self):
        """
        Send request `https://www.flightclub.com/`
        """
        for i, url in enumerate(self.start_urls):
            yield Request(
                url,
                headers=self.request_headers,
                callback=self.parse)

    def parse(self, response):
        """
        Top-level menu on homepage, filter links by known brands.
        Send request for each (brand, series), e.g.
        `https://www.flightclub.com/air-jordans/air-jordan-2`
        """
        self.log_debug_if_enabled(response)
        
        selector = Selector(response)
        content_table = selector.xpath(
            "//li[contains(@class, 'level1')]//@href").getall()
        for url in content_table:
            if 'jordan' in url or 'nike' in url or 'adidas' in url or 'yeezy' in url:
                yield Request(
                    url,
                    headers=self.request_headers,
                    callback=self.parse_items_page)

    def parse_items_page(self, response):
        """
        For each model in a (brand, series) page, request that model's page.
        E.g. `https://www.flightclub.com/air-jordan-2-retro-black-infrared-23-pr-pltnm-wht-011906`
        """
        self.log_debug_if_enabled(response)

        selector = Selector(response)
        content_table = selector.xpath(
            "//li[contains(@class, 'item')]//@href").getall()
        for url in content_table:
            yield Request(
                url,
                headers=self.request_headers,
                callback=self.parse_single_model_page)

    def parse_single_model_page(self, response):
        """
        For each model, parse listed price, name and style id from the returned
        page. Parse the sizes and price of each size from returned JavaScript.
        If we don't know the consignment sell ID of this model, send a query to
        find out. E.g. `https://sell.flightclub.com/api/public/search?page=1&perPage=20&query=385475%20023`
        If we do know and haven't already requested the consignment selling
        prices, use the sell ID to request the consignment selling prices for
        all sizes of this model. E.g.
        `https://sell.flightclub.com/products/19821`
        """
        self.log_debug_if_enabled(response)
        url = response.request.url

        selector = Selector(response)
        style_id_elems = selector.xpath("//li[@class='attribute-list-item']/text()").getall()

        style_id = ""
        release_date = ""
        color = ""
        if len(style_id_elems) > 0:
            style_id = style_id_elems[0].strip().lower()
        if not style_id:
            print("failed to retrieve style id in {}".format(url))

        if len(style_id_elems) > 1:
            color = style_id_elems[1].strip().lower()
        if len(style_id_elems) > 2:
            release_date = style_id_elems[2].strip().lower()
        if not style_id in self.prices:
            self.prices[style_id] = {}

        response_text = response.body_as_unicode()

        for line in response_text.split('\n'):
            match = re.match(r"<script type=\"text/javascript\">var productConfiguration = ([^;]+);.*", line)
            if match:
                product_configuration_str = match.group(1)
                try:
                    product_configuration = json.loads(product_configuration_str)
                    products_dict = product_configuration['products']['new']['products']
                    shoe_name = product_configuration['product']['name']

                    for key in products_dict:
                        for secondary_key in products_dict[key]:
                            item = products_dict[key][secondary_key]
                            size_str = item['size']['label']
                            px_str = item['price']
                            latest_update = item['latest_price_update_date']
                            
                            self.prices[style_id][size_str] = {
                                "px": float(px_str.strip().replace('$', '').replace(',', '')),
                                "url": url,
                                "name": shoe_name,
                                "release_date": release_date,
                                "size": size_str,
                                "color": color
                            }

                            print(shoe_name, size_str, self.prices[style_id][size_str]["px"], style_id, color, release_date)
                except KeyError as e:
                    print(e)
                    print('unexpected key in {}, page {}'.format(product_configuration_str, url))
                except json.JSONDecodeError as e:
                    print(e)
                    print('unable to decode {}, page {}'.format(product_configuration_str, url))
                break

        if style_id not in self.style_id_sell_item_id_map:
            yield Request(
                "https://sell.flightclub.com/api/public/search?page=1&perPage=20&query={}".format(style_id),
                headers=self.request_headers,
                callback=lambda r, style_id=style_id: self.get_sell_model_product_id(r, style_id))
        else:
            sell_id = str(self.style_id_sell_item_id_map[style_id])
            sell_url = "https://sell.flightclub.com/api/public/products/{}".format(sell_id)
            for shoe_size in self.prices[style_id]:
                self.prices[style_id][shoe_size]["sell_id"] = sell_id
            if sell_url not in self.queried_sell_price:
                self.queried_sell_price[sell_url] = True
                yield Request(
                    sell_url,
                    headers=self.request_headers,
                    callback=lambda r, style_id=style_id: self.get_sell_prices(r, style_id))

        # selector = Selector(response)
        # size_buttons = selector.xpath(
        #     ("//button[contains(@class, 'attribute-button-text') and "
        #      "contains(@class, 'jpi-product-size')]/text()")).getall()
        # print(len(size_buttons))
        # print(size_buttons)

        # we probably don't need this:

        if not self.prices[style_id]:
            print("did not find any sizes on page {}".format(url))
        return

    def get_sell_model_product_id(self, response, style_id):
        """
        Given the response of a style ID --> sell ID query, record it in our
        cached mapping.
        If we do know and haven't already requested the consignment selling
        prices, use the sell ID to request the consignment selling prices for
        all sizes of this model. E.g.
        `https://sell.flightclub.com/products/19821`
        """
        self.log_debug_if_enabled(response)

        results = json.loads(response.body_as_unicode())
        if "results" in results:
            if len(results["results"]) != 1:
                print("unexpected number of results {}".format(len(results)))
            else:
                sell_id = str(results["results"][0]["id"])
                self.style_id_sell_item_id_map[style_id] = sell_id
                sell_url = "https://sell.flightclub.com/api/public/products/{}".format(sell_id)
                for shoe_size in self.prices[style_id]:
                    self.prices[style_id][shoe_size]["sell_id"] = sell_id
                if sell_url not in self.queried_sell_price:
                    self.queried_sell_price[sell_url] = True
                    yield Request(
                        sell_url,
                        headers=self.request_headers,
                        callback=lambda r, style_id=style_id: self.get_sell_prices(r, style_id))
        return

    def get_sell_prices(self, response, style_id):
        """
        Given the response consignment sell price query, parse the price marks
        of all sizes and record in a different dict
        """
        self.log_debug_if_enabled(response)

        results = json.loads(response.body_as_unicode())
        try:
            if 'suggestedPrices' in results:
                if 'sizes' in results['suggestedPrices']:
                    for size in results['suggestedPrices']['sizes']:
                        item = results['suggestedPrices']['sizes'][size]
                        high_marks = item['priceMarks']['upperMarks']
                        highest_mark = 0
                        for high in high_marks:
                            highest_mark = max(highest_mark, high_marks[high])
                        if style_id not in self.sell_prices:
                            self.sell_prices[style_id] = {
                                size: {
                                    "market": float(item['price']) / 100,
                                    "highest": float(highest_mark) / 100
                                }}
                        else:
                            self.sell_prices[style_id][size] = {
                                "market": float(item['price']) / 100,
                                "highest": float(highest_mark) / 100
                            }
        except KeyError as e:
            print("Unexpected sell price page")
            print(e)
        return

    def closed(self, reason):
        """
        On graceful shutdown, record the
        1. consignment sell prices keyed by first style id then size
        2. website url, sell price keyed by first style id then size
        3. updated <style id, consignment sell id> map

        Don't Ctrl+C twice the application if we want this to be called.
        """
        for style_id in self.sell_prices:
            for size in self.sell_prices[style_id]:
                if style_id in self.prices and size in self.prices[style_id]:
                    if "market" in self.sell_prices[style_id][size] and "highest" in self.sell_prices[style_id][size]:
                        self.prices[style_id][size]["sell_px_market"] = self.sell_prices[style_id][size]["market"]
                        self.prices[style_id][size]["sell_px_highest"] = self.sell_prices[style_id][size]["highest"]

        with open(self.data_path, "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))
        
        with open(self.style_id_to_sell_id, "w") as style_id_sell_id_map_file:
            style_id_sell_id_map_file.write(
                json.dumps(
                    self.style_id_sell_item_id_map, indent=4, sort_keys=True))

    def log_debug_if_enabled(self, response):
        if self.log_all:
            if not os.path.isdir(self.debug_dir):
                os.makedirs(self.debug_dir)
            filename = os.path.join(
                self.debug_dir, response.request.url.replace('/', '|'))
            referrer = response.request.headers.get(
                'Referer', "none").decode("utf-8")
            content = str(response.status) + '\n' + referrer + '\n' + \
                response.body.decode("utf-8")
            write_entire_page(filename, content)

    # Unused after parsing price of each size from JavaScript
    def get_price_of_model_size(self, response, shoe_size, url):
        """
        For each specific size of a model, parse listed price, name and style id
        from the returned page.
        If we don't know the consignment sell ID of this model, send a query to
        find out. E.g. `https://sell.flightclub.com/api/public/search?page=1&perPage=20&query=385475%20023`
        If we do know and haven't already requested the consignment selling
        prices, use the sell ID to request the consignment selling prices for
        all sizes of this model. E.g.
        `https://sell.flightclub.com/products/19821`
        """
        self.log_debug_if_enabled(response)

        selector = Selector(response)
        price_elems = selector.xpath("//span[contains(@id, 'current-price')]/span/text()").getall()
        brand_elems = selector.xpath("//h2[@itemprop='brand']/text()").getall()
        name_elems = selector.xpath("//h1[@itemprop='name']/text()").getall()
        style_id_elems = selector.xpath("//li[@class='attribute-list-item']/text()").getall()

        style_id = ""
        release_date = ""
        color = ""
        if len(style_id_elems) > 0:
            style_id = style_id_elems[0].strip().lower()
        if len(style_id_elems) > 1:
            color = style_id_elems[1].strip().lower()
        if len(style_id_elems) > 2:
            release_date = style_id_elems[2].strip().lower()
        
        px = None
        if len(price_elems) == 1:
            px = price_elems[0].strip().strip('$')
        else:
            for elem in price_elems:
                if not px:
                    px = elem.strip().strip('$')
                elif px != elem.strip().strip('$'):
                    print('cannot determine px for {}'.format(url))

        if len(brand_elems) > 0 and len(name_elems) > 0 and px and style_id:
            shoe_name = name_elems[0].strip()
            if not style_id in self.prices:
                self.prices[style_id] = {}
                
            self.prices[style_id][shoe_size] = {
                "px": float(px.replace(',', '')),
                "url": url,
                "name": shoe_name,
                "release_date": release_date,
                "size": shoe_size,
                "color": color
            }
            print(shoe_name, shoe_size, px, style_id, color, release_date)
            if style_id not in self.style_id_sell_item_id_map:
                yield Request(
                    "https://sell.flightclub.com/api/public/search?page=1&perPage=20&query={}".format(style_id),
                    headers=self.request_headers,
                    callback=lambda r, style_id=style_id: self.get_sell_model_product_id(r, style_id))
            else:
                sell_id = str(self.style_id_sell_item_id_map[style_id])
                sell_url = "https://sell.flightclub.com/api/public/products/{}".format(sell_id)
                for shoe_size in self.prices[style_id]:
                    self.prices[style_id][shoe_size]["sell_id"] = sell_id
                if sell_url not in self.queried_sell_price:
                    self.queried_sell_price[sell_url] = True
                    yield Request(
                        sell_url,
                        headers=self.request_headers,
                        callback=lambda r, style_id=style_id: self.get_sell_prices(r, style_id))
        else:
            print("unable to find brand / name / style / px {}".format(url))

