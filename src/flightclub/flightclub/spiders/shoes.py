# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

import json
import datetime

class ShoesSpider(scrapy.Spider):
    name = 'shoes'
    allowed_domains = ['www.flightclub.com']
    start_urls = ['https://www.flightclub.com/']

    def start_requests(self):
        self.prices = {}
        for i,url in enumerate(self.start_urls):
            print(url)
            yield Request(url, headers={'User-Agent':'Mozilla/5.0'}, callback=self.parse)

    def parse(self, response):
        # top level menu
        selector = Selector(response)
        content_table = selector.xpath("//li[contains(@class, 'level1')]//@href").getall()
        for url in content_table:
            # print(item)
            if 'jordan' in url or 'nike' in url or 'adidas' in url or 'yeezy' in url:
                yield Request(url, headers={'User-Agent':'Mozilla/5.0'}, callback=self.parse_items_page)

    def parse_items_page(self, response):
        # second level menu
        selector = Selector(response)
        content_table = selector.xpath("//li[contains(@class, 'item')]//@href").getall()
        for url in content_table:
            yield Request(url, headers={'User-Agent':'Mozilla/5.0'}, callback=lambda r, url=url: self.parse_single_model_page(r, url))

    def parse_single_model_page(self, response, url):
        # single model page
        selector = Selector(response)
        size_buttons = selector.xpath("//button[contains(@class, 'attribute-button-text') and contains(@id, 'jpi_option') and not(contains(@id, 'for-notification'))]/text()").getall()
        for btn in size_buttons:
            try:
                shoe_size = float(btn.strip())
                print(url, shoe_size)
                yield Request(url + '?size=' + str(shoe_size), headers={'User-Agent':'Mozilla/5.0'}, callback=lambda r, shoe_size=shoe_size, url=url: self.get_price_of_model_size(r, shoe_size, url))
            except:
                # swallow
                continue

    def get_price_of_model_size(self, response, shoe_size, url):
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
                "px": px,
                "url": url,
                "name": shoe_name,
                "release_date": release_date,
                "size": shoe_size,
                "color": color
            }
            print(shoe_name, shoe_size, px, style_id, color, release_date)
        else:
            print("unable to find brand / name / style / px {}".format(url))

    def closed(self, reason):
        with open("flightclub.{}.txt".format(datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))

