# -*- coding: utf-8 -*-

import scrapy
import re
import datetime
import json

from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

class EfinderSpider(scrapy.Spider):
    name = 'efinder'
    allowed_domains = ['ebay.com']
    start_urls = ['https://ebay.com/']

    def start_requests(self):
        base_url = "https://www.ebay.com/sch/i.html"
        self.keyword = "Jordan 4 Retro Bred 2019"
        keyword_sanitized = self.keyword.replace(" ", "+")
        self.shoe_size = "9.5"
        shoe_size_sanitized = self.shoe_size.replace(".", "%252E")
        self.asks = {}
        self.asks[self.shoe_size] = {"ask": []}

        # defaults to men's; US size; and other default options
        query_url = "{}?_fsrp=1&_nkw={}&_sacat=0&_from=R40&rt=nc&_oaa=1&US%2520Shoe%2520Size%2520%2528Men%2527s%2529={}&_oaa=1&_dcat=15709".format(base_url, keyword_sanitized, shoe_size_sanitized)
        yield Request(query_url, headers={'User-Agent':'Mozilla/5.0'}, callback=self.parse)

    def parse(self, response):
        selector = Selector(response)
        results = selector.xpath("//li[contains(@id, 'srp-river-results-')]")
        for index, item in enumerate(results):
            # . for relative xpath
            title = item.xpath(".//h3[contains(@class, 's-item__title')]/text()").get(default="")
            if not title:
                # fallback to title with <span>
                title = item.xpath(".//h3[contains(@class, 's-item__title')]/span").get(default="")
                if not title:
                    print("title not found {}".format(item.get()))
                    continue

            px_item = item.xpath(".//span[contains(@class, 's-item__price')]")
            px_string = px_item.get()
            high_px = 0.0
            low_px = 0.0
            if not " to " in px_string:
                # <span...>$123</span>
                try:
                    dollar_px = item.xpath(".//span[contains(@class, 's-item__price')]/text()").get(default="").strip('$')
                    low_px = float(dollar_px)
                    high_px = low_px
                except ValueError as e:
                    print("px not found {} \n {}".format(e, item.get()))
                    continue
            else:
                # <span...>$123<span...> to </span>$234</span>
                match = re.match(r"<span[^>]+>\$([0-9.]+)[^\$]+\$([0-9.]+)</span>", px_string)
                if not match:
                    print("px not found {}".format(item.get()))
                    continue
                else:
                    low_px = float(match.group(1))
                    high_px = float(match.group(2))

            if high_px == 0.0 or low_px == 0.0:
                print("px not found {}".format(item.get()))
                continue

            link = item.xpath(".//a[contains(@class, 's-item__link')]/@href").get(default="")
            if not link:
                print("link not found {}".format(item.get()))
                continue
            print(title)
            print(low_px)
            print(high_px)
            print(link)

            # @TODO: handle px range; need to open each page and parse directly from response; parse from the likes of $rwidgets
            half = self.asks[self.shoe_size]["ask"]
            level_idx = 0
            while level_idx < len(half):
                if low_px == half[level_idx]["px"]:
                    half[level_idx]["orders"].append({"link": link})
                    half[level_idx]["size"] += 1
                    break
                elif low_px < half[level_idx]["px"]:
                    half.insert(level_idx, {
                        "px": low_px,
                        "size": 1,
                        "orders": [{
                            "link": link
                        }]
                    })
                    break
                level_idx += 1

            if level_idx == len(half):
                half.append({
                    "px": low_px,
                    "size": 1,
                    "orders": [{
                        "link": link
                    }]
                })
        return

    def closed(self, reason):
        with open("{}.{}.{}.txt".format(self.keyword, self.shoe_size, datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
            wfile.write(json.dumps({self.keyword: self.asks}, indent=4, sort_keys=True))
        return
