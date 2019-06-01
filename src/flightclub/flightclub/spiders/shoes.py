# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

import json
import date

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
            yield Request(url, headers={'User-Agent':'Mozilla/5.0'}, callback=self.parse_items_page)

    def parse_items_page(self, response):
        # second level menu
        selector = Selector(response)
        content_table = selector.xpath("//li[contains(@class, 'item')]//@href").getall()
        for url in content_table:
            yield Request(url, headers={'User-Agent':'Mozilla/5.0'}, callback=lambda r: self.parse_single_model_page(r, url))

    def parse_single_model_page(self, response, url):
        # single model page
        selector = Selector(response)
        size_buttons = selector.xpath("//button[contains(@class, 'attribute-button-text')]/text()").getall()
        for btn in size_buttons:
            try:
                shoe_size = float(btn.strip())
                yield Request(url + '?size=' + str(shoe_size), headers={'User-Agent':'Mozilla/5.0'}, callback=lambda r: self.get_price_of_model_size(r, shoe_size))
            except:
                # swallow
                continue

    def get_price_of_model_size(self, response, shoe_size):
        selector = Selector(response)
        price_elems = selector.xpath("//span[@class='price']/text()").getall()
        brand_elems = selector.xpath("//h2[@itemprop='brand']/text()").getall()
        name_elems = selector.xpath("//h1[@itemprop='name']/text()").getall()
        if len(price_elems) > 0:
            px = price_elems[0].strip().strip('$')
            if len(brand_elems) > 0 and len(name_elems) > 0:
                shoe_full_name = brand_elems[0].strip() + ' -- ' + name_elems[0].strip() + ' -- ' + str(shoe_size)
                self.prices[shoe_full_name] = px

    def closed(self, reason):
        with open("flightclub.{}.txt".format(datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))

