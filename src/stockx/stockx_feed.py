#!/usr/bin/env python3

import os
import sys
import json
import pprint
import datetime

from stockxsdk import Stockx

pp = pprint.PrettyPrinter(indent=2)
        
class StockXFeed():
    def __init__(self):
        self.stockx = Stockx()
        return

    def authenticate(self, usrname, pwd):
        if not self.stockx.authenticate(usrname, pwd):
            raise RuntimeError("failed to log in as {}".format(usrname))

    def get_details(self, product_id):
        """
        @param product_id rfc 4122 uuid string
        @return book string. See build_book
        """
        # product_id = stockx.get_first_product_id('BB1234')
        product = self.stockx.get_product(product_id)
        print("product title: {}".format(product.title))

        # highest_bid = self.stockx.get_highest_bid(product_id)
        # print("size: {}, best bid: {}".format(highest_bid.shoe_size, highest_bid.order_price))

        # lowest_ask = self.stockx.get_lowest_ask(product_id)
        # print("size: {}, best ask: {}".format(lowest_ask.shoe_size, lowest_ask.order_price))

        asks = self.stockx.get_asks(product_id)
        bids = self.stockx.get_bids(product_id)
        
        book = StockXFeed.build_book(product, bids, asks)
        bookstr = StockXFeed.serialize_book(product, book)
        return bookstr

    @staticmethod
    def is_better(px1, px2, side):
        if side == 'bid':
            return px1 > px2
        elif side == 'ask':
            return px1 < px2
        else:
            raise RuntimeError('unknown side {}'.format(side))
        return

    @staticmethod
    def build_book(product, bids, asks):
        """Given a product and bids and asks of all shoe sizes, for each shoe
        size construct a book.

        @param product stockxsdk.product
        @param bids    [stockxsdk.order]
        @param asks    [stockxsdk.order]

        @return {"9": {"bid": [{"px": 20, "size": 1, "orders": ...},
                               {"px": 19, "size": 2, "orders": ...}]},
                       "ask": [{"px": 21, "size": 1, "orders": ...},
                               {"px": 22, "size": 1, "orders": ...}]}},
                 "8": ...}
        """
        sizes = {}

        def init_level(order):
            return {"px": order.order_price, "size": int(order.num_orders), "orders": [order]}

        def build_half(sizes, orders):
            for order in orders:
                if not order.shoe_size in sizes:
                    sizes[order.shoe_size] = {"bid": [], "ask": []}
                    sizes[order.shoe_size][order.order_type].append(init_level(order))
                else:
                    half = sizes[order.shoe_size][order.order_type]
                    level_idx = 0
                    while level_idx < len(half):
                        if order.order_price == half[level_idx]["px"]:
                            half[level_idx]["orders"].append(order)
                            half[level_idx]["size"] += int(order.num_orders)
                            break
                        elif StockXFeed.is_better(order.order_price, half[level_idx]["px"], order.order_type):
                            half.insert(level_idx, init_level(order))
                            break
                        level_idx += 1

                    if level_idx == len(half):
                        half.append(init_level(order))

        build_half(sizes, bids)
        build_half(sizes, asks)

        # pp.pprint(sizes)
        return sizes

    @staticmethod
    def serialize_book(product, book):
        res_str = ""
        for shoe_size in book:
            res_str += '---- {} : {} ----\n'.format(product.title, shoe_size)
            res_str += '---- Bid ----  ---- Ask ----\n'
            for level in book[shoe_size]['ask'][::-1]:
                res_str += "               {:.2f} {}\n".format(level["px"], level["size"])
            for level in book[shoe_size]['bid']:
                res_str += "{:6d} {:.2f}\n".format(level["size"], level["px"])
            res_str += ('----------------------------\n')
            if len(book[shoe_size]["bid"]) > 0 and len(book[shoe_size]["ask"]) > 0:
                res_str += ('Spread: {:.2f}. Mid: {:.2f}\n'.format(book[shoe_size]["ask"][0]["px"] - book[shoe_size]["bid"][0]["px"], (book[shoe_size]["ask"][0]["px"] + book[shoe_size]["bid"][0]["px"]) / 2))
            else:
                res_str += ('One side is empty\n')
            res_str += '\n'
        return res_str

    def search(self, query):
        results = self.stockx.search(query)
        # for item in results:
            # pp.pprint(item)
            # print("name {}\n  best bid {}\n  best ask {}\n  last sale {}\n  sales last 72 {}\n".format(item['name'], item['highest_bid'], item['lowest_ask'], item['last_sale'], item['sales_last_72']))
        return results

if __name__ == "__main__":
    stockx_feed = StockXFeed()
    with open("../../credentials/credentials.json", "r") as cred_file:
        cred = json.loads(cred_file.read())["stockx"]
        stockx_feed.authenticate(cred["username"], cred["password"])
        # stockx_feed.get_details('2c91a3dc-4ba6-40bc-af0b-a259f793a223')

        results = stockx_feed.search('air jordan 4')
        items_map = []
        for item in results:
            if 'objectID' in item:
                bookstr = stockx_feed.get_details(item['objectID'])
                book_filename = "../../data/stockx/" + item['name'] + '-' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.txt'
                with open(book_filename, 'w') as wfile:
                    wfile.write(bookstr)
                if 'sales_last_72' in item and item['sales_last_72']:
                    items_map.append({
                        'book': book_filename,
                        'sales_last_72': int(item['sales_last_72']),
                        'name': item['name'],
                        'last_price': -1 if not 'last_sale' in item else float(item['last_sale'])
                    })

        items_map.sort(key=lambda x: x['sales_last_72'], reverse=True)
        pp.pprint(items_map)

