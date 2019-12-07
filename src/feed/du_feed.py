#!/usr/bin/env python3

import json
import requests
import datetime

import pprint
import csv
import argparse

from du_url_builder import DuRequestBuilder
from du_response_parser import DuParser, SaleRecord, DuItem
from last_updated import LastUpdatedSerializer
from time_series_serializer import TimeSeriesSerializer
from static_info_serializer import StaticInfoSerializer

def send_du_request(url):
    if __debug__:
        print("request {}".format(url))
    return requests.get(url=url, headers=DuRequestBuilder.du_headers)

class DuFeed():
    def __init__(self):
        self.parser = DuParser()
        self.builder = DuRequestBuilder()

    def search_pages(self, keyword, pages=0, result_items=None):
        max_page = pages
        if max_page == 0:
            request_url = self.builder.get_search_by_keywords_url(keyword, 0, 1, 0)
            search_response = send_du_request(request_url)
            total_num = json.loads(search_response.text)["data"]["total"]
            max_page = total_num / 20 + 1

        if not result_items:
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

    def get_prices_from_product_id(self, product_id):
        try:
            request_url = self.builder.get_product_detail_url(product_id)
            product_detail_response = send_du_request(request_url)
            _, size_list, _ = self.parser.parse_product_detail_response(
                product_detail_response.text)
            return size_list
        except RuntimeError as e:
            print("get_detail runtime error {}".format(e))
            return None
        except json.decoder.JSONDecodeError as e:
            print("get_detail unexpected response {}".format(e))
            return None
        except KeyError as e:
            print("get_detail key error {}".format(e))
            return None
    
    def get_prices_from_style_id(self, style_id, static_info):
        if not style_id in static_info:
            raise RuntimeError("failed to find product_id from style_id {}".format(style_id))
        product_id = static_info[style_id]
        return self.get_details_from_product_id(product_id)

    # TODO: paging
    def get_historical_transactions(self, product_id, in_code, page=0):
        recentsales_list_url = self.builder.get_recentsales_list_url(page, product_id)
        recentsales_list_response = requests.get(url=recentsales_list_url, headers=DuRequestBuilder.du_headers)
        last_id, sales = self.parser.parse_recent_sales(recentsales_list_response.text, in_code)
        return sales

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        help=("[query|update]"))
    parser.add_argument(
        "--kw",
        help="in query mode, the query keyword")
    parser.add_argument(
        "--start_from",
        help="in query mode, continue from entries not already populated in given\n"
             "in update mode, the file from which to load the product_id, style_id mapping")
    parser.add_argument(
        "--pages",
        help="in query mode, the number of pages to query")
    parser.add_argument(
        "--last_updated",
        help="in update mode, the file containing the last_updated time of each item")
    parser.add_argument(
        "--min_interval_seconds",
        help="in update mode, only items whose last update time is at least this much from now will get updated")
    args = parser.parse_args()
    feed = DuFeed()
    serializer = StaticInfoSerializer()

    if args.mode == "query":
        if not args.kw:
            raise RuntimeError("args.kw is mandatory in query mode")
        if not args.pages:
            raise RuntimeError("args.pages is mandatory in query mode")

        if args.start_from:
            items = serializer.load_static_info_from_csv(args.start_from)
            result = feed.search_pages(args.kw, pages=int(args.pages), result_items=items)
        else:
            result = feed.search_pages(args.kw, pages=int(args.pages))
        serializer.dump_static_info_to_csv(result)
    elif args.mode == "update":
        if not args.start_from:
            raise RuntimeError("args.start_from is mandatory in update mode")
        
        last_updated_file = "last_updated.log"
        if args.last_updated:
            last_updated_file = last_updated

        last_updated_serializer = LastUpdatedSerializer(last_updated_file, args.min_interval_seconds)
        time_series_serializer = TimeSeriesSerializer()

        static_info = serializer.load_static_info_from_csv(args.start_from)
        for product_id in static_info:
            if last_updated_serializer.should_update(product_id, "du"):
                try:
                    style_id = static_info[product_id].style_id
                    gender = static_info[product_id].gender
                    size_prices = feed.get_prices_from_product_id(product_id)
                    transactions = feed.get_historical_transactions(product_id, gender)
                    size_transactions = time_series_serializer.get_size_transactions(transactions)
                    update_time = last_updated_serializer.update_last_updated(style_id, "du")
                    time_series_serializer.update(
                        "du", update_time, style_id, size_prices, size_transactions)
                except KeyError as e:
                    print("get_tick failed {}".format(e))
                except RuntimeError as e:
                    print("get_tick failed {}".format(e))
                except json.decoder.JSONDecodeError as e:
                    print("get_tick failed {}".format(e))
                last_updated_serializer.save_last_updated()
            else:
                print("should skip {}".format(product_id))
    else:
        raise RuntimeError("Unsupported mode {}".format(args.mode))

