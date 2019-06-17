# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

import json
import datetime
import os

class ShoesSpider(scrapy.Spider):
    name = 'shoes'
    allowed_domains = ['www.flightclub.com', 'sell.flightclub.com']
    start_urls = ['https://www.flightclub.com/']

    """cached mapping from style ID (flightclub) to the item's ID on flightclub
    consignment portal.
    """
    style_id_to_sell_id = "../../data/flightclub/style_id_sell_item_id_map.txt"

    def start_requests(self):
        """
        Load style ID to sell IDs map.
        Send request `https://www.flightclub.com/`
        """
        self.prices = {}
        self.sell_prices = {}

        self.style_id_sell_item_id_map = {}
        self.queried_sell_price = {}

        if os.path.isfile(ShoesSpider.style_id_to_sell_id):
            with open(ShoesSpider.style_id_to_sell_id, "r") as rfile:
                self.style_id_sell_item_id_map = json.loads(rfile.read())
        for i, url in enumerate(self.start_urls):
            print(url)
            yield Request(
                url,
                headers={'User-Agent':'Mozilla/5.0'},
                callback=self.parse)

    def parse(self, response):
        """
        Top-level menu on homepage, filter links by known brands.
        Send request for each (brand, series), e.g.
        `https://www.flightclub.com/air-jordans/air-jordan-2`
        """
        selector = Selector(response)
        content_table = selector.xpath(
            "//li[contains(@class, 'level1')]//@href").getall()
        for url in content_table:
            # print(item)
            if 'jordan' in url or 'nike' in url or 'adidas' in url or 'yeezy' in url:
                yield Request(
                    url,
                    headers={'User-Agent':'Mozilla/5.0'},
                    callback=self.parse_items_page)

    def parse_items_page(self, response):
        """
        For each model in a (brand, series) page, request that model's page.
        E.g. `https://www.flightclub.com/air-jordan-2-retro-black-infrared-23-pr-pltnm-wht-011906`
        """
        selector = Selector(response)
        content_table = selector.xpath(
            "//li[contains(@class, 'item')]//@href").getall()
        for url in content_table:
            yield Request(
                url,
                headers={'User-Agent':'Mozilla/5.0'},
                callback=lambda r, url=url: self.parse_single_model_page(r, url))

    def parse_single_model_page(self, response, url):
        """
        For each model page, request different available sizes of that model.
        E.g. `https://www.flightclub.com/air-jordan-2-retro-black-infrared-23-pr-pltnm-wht-011906?size=8.5`
        """
        selector = Selector(response)
        size_buttons = selector.xpath(
            ("//button[contains(@class, 'attribute-button-text') and "
             "contains(@id, 'jpi_option') and "
             "not(contains(@id, 'for-notification'))]/text()")).getall()
        for btn in size_buttons:
            try:
                shoe_size = str(float(btn.strip())).strip('.0')
                print(url, shoe_size)
                yield Request(
                    url + '?size=' + shoe_size,
                    headers={'User-Agent':'Mozilla/5.0'},
                    callback=lambda r, shoe_size=shoe_size, url=url: self.get_price_of_model_size(r, shoe_size, url))
            except:
                continue

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
                    headers={'User-Agent':'Mozilla/5.0'},
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
                        headers={'User-Agent':'Mozilla/5.0'},
                        callback=lambda r, style_id=style_id: self.get_sell_prices(r, style_id))
        else:
            print("unable to find brand / name / style / px {}".format(url))

    def get_sell_model_product_id(self, response, style_id):
        """
        Given the response of a style ID --> sell ID query, record it in our
        cached mapping.
        If we do know and haven't already requested the consignment selling
        prices, use the sell ID to request the consignment selling prices for
        all sizes of this model. E.g.
        `https://sell.flightclub.com/products/19821`
        """
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
                        headers={'User-Agent':'Mozilla/5.0'},
                        callback=lambda r, style_id=style_id: self.get_sell_prices(r, style_id))
        return

    def get_sell_prices(self, response, style_id):
        """
        Given the response consignment sell price query, parse the price marks
        of all sizes and record in a different dict
        """
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

        with open("../../data/flightclub/flightclub.{}.txt".format(
            datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))
        
        with open(ShoesSpider.style_id_to_sell_id, "w") as style_id_sell_id_map_file:
            style_id_sell_id_map_file.write(
                json.dumps(
                    self.style_id_sell_item_id_map, indent=4, sort_keys=True))
