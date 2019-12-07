#!/usr/bin/env python3

import os
import sys
import json
import pprint
import datetime
import argparse
import time

from random import randrange
from stockxsdk import Stockx
from static_info_serializer import StaticInfoSerializer

class StockXFeed():
    def __init__(self):
        self.retry_time = 120
        self.stockx = Stockx()
        return

    def authenticate(self, usrname, pwd):
        self.usrname = usrname
        self.pwd = pwd
        if not self.stockx.authenticate(usrname, pwd):
            time.sleep(self.retry_time)
            self.authenticate(usrname, pwd)

    def get_product(self, product_id):
        product = self.stockx.get_product(product_id)
        return product

    def search(self, query):
        results = self.stockx.search(query)
        # for item in results:
        # pp.pprint(item)
        # print("name {}\n  best bid {}\n  best ask {}\n  last sale {}\n  sales last 72 {}\n".format(item['name'], item['highest_bid'], item['lowest_ask'], item['last_sale'], item['sales_last_72']))
        return results

    @staticmethod
    def parse_transaction(transactions):
        result = []
        try:
            activities = transactions["ProductActivity"]
            for item in activities:
                if "amount" in item and "createdAt" in item and "shoeSize" in item:
                    result.append({"time": item["createdAt"],
                                   "px": item["amount"],
                                   "shoe_size": item["shoeSize"]})
        except ValueError as e:
            print("ValueError")
            print(e)
        except KeyError as e:
            print("KeyError")
            print(e)
        return result

if __name__ == "__main__":
    stockx_feed = StockXFeed()

    serializer = StaticInfoSerializer()
    with open("../../credentials/credentials.json", "r") as cred_file:
        cred = json.loads(cred_file.read())["stockx"]
        cred_cnt = len(cred)
        cred_idx = randrange(cred_cnt)

        items_map = {}
        with open("query_kw.txt", "r") as query_file:
            for line in query_file:
                line = line.strip()
                if not line:
                    continue
                print("authenticating")
                stockx_feed.authenticate(
                    cred[cred_idx]["username"],
                    cred[cred_idx]["password"])
                print("Querying \"{}\" using account {}".format(
                    line, cred[cred_idx]["username"]))
                cred_idx = (cred_idx + 1) % cred_cnt

                results = stockx_feed.search(line)
                results_cnt = len(results)
                print('found {} items for keyword {}'.format(results_cnt, line))

                for item in results:
                    if 'objectID' in item and item['objectID'] not in searched_items:
                        product = stockx_feed.get_product(item['objectID'])
                        items_map[item['objectID']] = product

        serializer.dump_stockx_static_info_to_csv(items_map)
