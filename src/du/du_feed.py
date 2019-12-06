#!/usr/bin/env python3

import json
import requests
import datetime

import pprint
import csv
import argparse

from du_url_builder import DuRequestBuilder
from du_response_parser import DuParser, SaleRecord, DuItem

def send_du_request(url):
    if __debug__:
        print("request {}".format(url))
    return requests.get(url=url, headers=DuRequestBuilder.du_headers)

class DuFeed():
    def __init__(self):
        self.parser = DuParser()
        self.builder = DuRequestBuilder()

    def search_pages(self, keyword, pages=0):
        max_page = pages
        if max_page == 0:
            request_url = self.builder.get_search_by_keywords_url(keyword, 0, 1, 0)
            search_response = send_du_request(request_url)
            total_num = json.loads(search_response.text)["data"]["total"]
            max_page = total_num / 20 + 1

        result_items = {}
        for i in range(max_page):
            try:
                request_url = self.builder.get_search_by_keywords_url(keyword, i, 1, 0)
                search_response = send_du_request(request_url)
                items = self.parser.parse_search_results(search_response.text)
                for j in items:
                    if j.product_id in result_items:
                        print("item {} is already queried in this call".format(j.product_id))
                        continue
                    self.populate_item_details(j, j.product_id)
                    result_items[j.product_id] = j
            except json.decoder.JSONDecodeError as e:
                if search_response:
                    print("search_page unexpected response {} from {}".format(
                        e, search_response.text))
                else:
                    print("search_page unexpected response {}".format(e))
            except RuntimeError as e:
                if search_response:
                    print("search_page runtime error {} from {}".format(
                        e, search_response.text))
                else:
                    print("search_page runtime error {}".format(e))
            except KeyError as e:
                if search_response:
                    print("search_page key error {} from {}".format(
                        e, search_response.text))
                else:
                    print("search_page key error {}".format(e))
        return result_items
    
    def populate_item_details(self, in_item, product_id):
        request_url = self.builder.get_product_detail_url(product_id)
        product_detail_response = send_du_request(request_url)
        style_id, size_list, release_date = self.parser.parse_product_detail_response(
            product_detail_response.text)
        in_item.populate_details(style_id, size_list, release_date)
        return

    def search_product_ids(self, product_ids):
        return
    
    def search_style_ids(self, style_ids):
        return
    
    def load_style_id_product_id_map(self, map_file):
        return

    def extract_item_static_info(self, items):
        result = [items[i].get_static_info() for i in items]
        return result

if __name__ == "__main__":
    feed = DuFeed()
    items = feed.search_pages("aj", 1)

    for i in items:
        print(items[i])
    
    static_items = feed.extract_item_static_info(items)
    date_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    static_mapping_file = "du.mapping.{}.csv".format(date_time)
    with open(static_mapping_file, 'w') as outfile:
        wr = csv.writer(outfile)
        wr.writerow(["style_id", "du_product_id", "du_title", "release_date"])
        for row in static_items:
            wr.writerow([row["style_id"], row["product_id"], row["title"], row["release_date"]])
    print("dumped static mapping to {}".format(static_mapping_file))
