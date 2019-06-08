# -*- coding: utf-8 -*-

import scrapy

import re
import datetime
import json
import pprint
import copy

from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

pp = pprint.PrettyPrinter()

class EfinderSpider(scrapy.Spider):
    name = 'efinder'
    allowed_domains = ['ebay.com']
    start_urls = ['https://ebay.com/']

    def start_requests(self):
        base_url = "https://www.ebay.com/sch/i.html"
        self.keyword = "Jordan 4 Retro Bred 2019 receipt"
        keyword_sanitized = self.keyword.replace(" ", "+")
        self.shoe_size = "9.5"
        shoe_size_sanitized = self.shoe_size.replace(".", "%252E")
        self.asks = {}
        self.asks[self.shoe_size] = {"ask": []}

        # defaults to men's; US size; condition new_with_box (LH_ItemCondition=1000)
        query_url = "{}?_fsrp=1&_nkw={}&_sacat=0&_from=R40&rt=nc&_oaa=1&US%2520Shoe%2520Size%2520%2528Men%2527s%2529={}&_oaa=1&_dcat=15709&LH_ItemCondition=1000".format(base_url, keyword_sanitized, shoe_size_sanitized)
        print(query_url)
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
            # print(title)
            # print(low_px)
            # print(high_px)
            # print(link)

            yield Request(link, headers={'User-Agent':'Mozilla/5.0'}, callback=lambda r, link=link, low_px=low_px, high_px=high_px: self.extract_prices(r, link, low_px, high_px))
        return

    def extract_prices(self, response, url, low_px, high_px):
        response_text = response.body.decode("utf-8")
        idx = response_text.find('$rwidgets')
        selectid_sizes = {}
        size_prices = {}

        if idx > -1:
            next_newline = response_text.find('\n', idx)
            if next_newline > -1:
                extracted_line = response_text[idx:next_newline]

                # (select-id, size-value) mapping line
                value_id_groups = re.findall(r"\"valueId\":([0-9]+)", extracted_line)
                value_name_groups = re.findall(r"\"valueName\":\"([^\"]+)\"", extracted_line)

                if len(value_id_groups) != len(value_name_groups):
                    print("value_id and value_names length mismatch:\n{}\n{}\n{}".format(extracted_line, value_id_groups, value_name_groups))
                for i in range(len(value_id_groups)):
                    selectid_sizes[value_id_groups[i]] = value_name_groups[i]

                # if len(selectid_sizes.keys()) == 0:
                #     print("did not populate select-id map: {}".format(selectid_sizes))

                pprinted = pp.pformat(extracted_line)
                for line in pprinted.split('\n'):
                    if "\"Size\"" in line:
                        # (select-id, price) mapping line
                        match = re.search(r"{\"Size\":([0-9]+)}", line)
                        if match:
                            select_id = str(match.group(1))
                            if not select_id in selectid_sizes:
                                print("select-id {} not in mapping".format(select_id))
                                continue
                            price_match = re.search(r"\'\$([0-9.]+)\"", line)
                            if price_match:
                                size_prices[selectid_sizes[select_id]] = float(price_match.group(1))
                            else:
                                print("no price found in line:\n{}".format(line))

                if len(size_prices.keys()) == 0:
                    # we failed to parse, try a different format
                    size_groups = re.findall(r"Shoe Size [^:]+:([0-9]+)", extracted_line)
                    price_groups = re.findall(r"\"priceAmountValue\":{\"value\":([0-9.]+),\"currency\":\"[^:]+\"}", extracted_line)
                    if len(size_groups) == len(price_groups):
                        for i in range(len(size_groups)):
                            select_id = size_groups[i]
                            if str(select_id) not in selectid_sizes:
                                print("select-id {} not in mapping".format(select_id))
                                continue
                            size_prices[selectid_sizes[select_id]] = float(price_groups[i])
                    else:
                        print("Sizes and prices length mismatch:\n{}\n{}".format(size_groups, price_groups))
        if len(size_prices) == 0:
            if low_px != high_px:
                print("failed to find out price for {}. not added to book.".format(url))
            else:
                # we failed to parse again, assume the listed price and the listed size match
                print("failed to assign per-size prices: {}, assume listed price and listed size match".format(url))
                self.populate_book(low_px, url)
        else:
            if self.shoe_size in size_prices:
                self.populate_book(size_prices[self.shoe_size], url)
            else:
                print("cannot find size in size_prices map, assume size not available: {}. not added to book".format(url))



    def populate_book(self, low_px, link):
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

    def closed(self, reason):
        if len(self.asks) > 0:
            with open("{}.{}.{}.txt".format(self.keyword, self.shoe_size, datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
                wfile.write(json.dumps({self.keyword: self.asks}, indent=4, sort_keys=True))
        return
