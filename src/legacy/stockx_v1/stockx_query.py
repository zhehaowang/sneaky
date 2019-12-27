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

pp = pprint.PrettyPrinter(indent=2)

RETRY_TIME = 120
PER_QUERY_SLEEP_TIME = 120

def sanitize_style_id(key):
    return key.lower().replace('-', '').replace(' ', '')

def sanitize_filename(key):
    return key.replace(
        '(', '-').replace(')', '-').replace(' ', '-').replace('/', '-')

class StockXQuery():
    def __init__(self):
        self.stockx = Stockx()
        return

    def authenticate(self, usrname, pwd):
        self.usrname = usrname
        self.pwd = pwd
        if not self.stockx.authenticate(usrname, pwd):
            time.sleep(RETRY_TIME)
            self.authenticate(usrname, pwd)

    def get_details(self, product_id):
        """
        @param product_id rfc 4122 uuid string
        @return book string. See build_book for book string details. None if getting the product fails
        """
        # product_id = stockx.get_first_product_id('BB1234')
        product = self.stockx.get_product(product_id)
        if not hasattr(product, 'title'):
            print(("get details failed for {}. presumably we need to throttle "
                   "and re-auth. sleeping {}s").format(product_id, PER_QUERY_SLEEP_TIME))
            time.sleep(PER_QUERY_SLEEP_TIME)
            self.authenticate(self.usrname, self.pwd)
            self.get_details(product_id)
            return

        print("product title: {}".format(product.title))

        # highest_bid = self.stockx.get_highest_bid(product_id)
        # print("size: {}, best bid: {}".format(highest_bid.shoe_size, highest_bid.order_price))

        # lowest_ask = self.stockx.get_lowest_ask(product_id)
        # print("size: {}, best ask: {}".format(lowest_ask.shoe_size, lowest_ask.order_price))

        asks = self.stockx.get_asks(product_id)
        bids = self.stockx.get_bids(product_id)
        transactions = self.stockx.get_transactions(product_id)

        # if len(bids) > 0:
        #     best_bid = bids[-1]
        # else:
        #     best_bid = None

        # if len(asks) > 0:
        #     best_ask = asks[0]
        # else:
        #     best_ask = None

        book = StockXQuery.build_book(product, bids, asks)
        # bookstr = StockXQuery.serialize_book(product.title, book)
        return book, transactions

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
            return {"px": order.order_price, "size": int(
                order.num_orders), "orders": [order]}

        def build_half(sizes, orders):
            for order in orders:
                if not hasattr(order, 'shoe_size'):
                    # we had trouble processing this order. Skip it.
                    continue
                if order.shoe_size not in sizes:
                    sizes[order.shoe_size] = {"bid": [], "ask": []}
                    sizes[order.shoe_size][order.order_type].append(
                        init_level(order))
                else:
                    half = sizes[order.shoe_size][order.order_type]
                    level_idx = 0
                    while level_idx < len(half):
                        if order.order_price == half[level_idx]["px"]:
                            half[level_idx]["orders"].append(order)
                            half[level_idx]["size"] += int(order.num_orders)
                            break
                        elif StockXQuery.is_better(order.order_price, half[level_idx]["px"], order.order_type):
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
    def serialize_book(product_title, book):
        res_str = ""
        for shoe_size in book:
            res_str += '---- {} : {} ----\n'.format(product_title, shoe_size)
            res_str += '---- Bid ----  ---- Ask ----\n'
            for level in book[shoe_size]['ask'][::-1]:
                res_str += "               {:.2f} {}\n".format(
                    level["px"], level["size"])
            for level in book[shoe_size]['bid']:
                res_str += "{:6d} {:.2f}\n".format(level["size"], level["px"])
            res_str += ('----------------------------\n')
            if len(book[shoe_size]["bid"]) > 0 and len(
                    book[shoe_size]["ask"]) > 0:
                res_str += (
                    'Spread: {:.2f}. Mid: {:.2f}\n'.format(
                        book[shoe_size]["ask"][0]["px"] -
                        book[shoe_size]["bid"][0]["px"],
                        (book[shoe_size]["ask"][0]["px"] +
                         book[shoe_size]["bid"][0]["px"]) /
                        2))
            else:
                res_str += ('One side is empty\n')
            res_str += '\n'
        return res_str

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

    @staticmethod
    def deserialize_book(bookstr):
        return

    def search(self, query):
        results = self.stockx.search(query)
        # for item in results:
        # pp.pprint(item)
        # print("name {}\n  best bid {}\n  best ask {}\n  last sale {}\n  sales last 72 {}\n".format(item['name'], item['highest_bid'], item['lowest_ask'], item['last_sale'], item['sales_last_72']))
        return results


def find_promising(items_map):
    """Given products sorted by transactions in last 72 hours (more -> less),
    find promising ones whose spread is larger than commissioned adjusted price.

    """
    volume_threshold = 100
    ask_commission_percent = 0.125  # 9.5% commission + 3% payment proc
    bid_commission_value = 13.95  # 13.95 shipping + 0 authentication fee
    cut_in_tick = 1  # cut in $1
    size_filter = ['8.5', '9', '9.5']

    promising = []

    for item in items_map:
        if item['sales_last_72'] < volume_threshold:
            return promising
        # midpx = (item['best_ask'] + item['best_bid']) / 2
        for want_size in size_filter:
            if want_size not in item['size_prices']:
                print("size {} not found in book. sizes: {}".format(
                    want_size, item['size_prices'].keys()))
            else:
                size_price = item['size_prices'][want_size]
                if size_price['best_ask'] == 0 or size_price['best_bid'] == 0:
                    continue
                spread = size_price['best_ask'] - size_price['best_bid']
                margin = spread - \
                    (bid_commission_value +
                     size_price['best_ask'] * ask_commission_percent + cut_in_tick * 2)
                if margin > 0:
                    res = dict(size_price)
                    res["size"] = want_size
                    res["title"] = item["name"]
                    res["book"] = item["book"]
                    res["sales_last_72"] = item["sales_last_72"]
                    res["margin"] = margin
                    res["margin_percent"] = margin / \
                        (size_price['best_ask'] + size_price['best_bid']) * 2
                    promising.append(res)
    return promising


if __name__ == "__main__":
    relevant_levels = 30

    runtime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = "../../data/stockx/" + runtime
    os.mkdir(outdir)


    promising_dirname = os.path.join(outdir, 'promising')
    os.mkdir(promising_dirname)

    best_prices = {}
    searched_items = {}

    with open("../../credentials/credentials.json", "r") as cred_file:

        cred = json.loads(cred_file.read())["stockx"]
        cred_cnt = len(cred)
        cred_idx = randrange(cred_cnt)
        promising_items = []

        with open("query_kw.txt", "r") as query_file, open(os.path.join(promising_dirname, "best_prices.txt"), 'w') as bests_file:
            for line in query_file:
                line = line.strip()
                if not line:
                    continue
                stockx_feed = StockXQuery()
                stockx_feed.authenticate(
                    cred[cred_idx]["username"],
                    cred[cred_idx]["password"])
                print("Querying \"{}\" using account {}".format(
                    line, cred[cred_idx]["username"]))
                cred_idx = (cred_idx + 1) % cred_cnt

                results = stockx_feed.search(line)
                results_cnt = len(results)
                print('found {} items for keyword {}'.format(results_cnt, line))

                items_map = []
                for item in results:
                    if 'objectID' in item and item['objectID'] not in searched_items:
                        try:
                            book, transactions_json = stockx_feed.get_details(item['objectID'])
                            searched_items[item['objectID']] = True

                            if not book:
                                print('no book parsed for {}. skipping'.format(
                                    item['name']))
                                continue

                            if 'sales_last_72' not in item or not item['sales_last_72']:
                                print('no sales parsed for {}. skipping'.format(
                                    item['name']))
                                continue
                            if 'style_id' not in item or not item['style_id']:
                                print('no style_id parsed for {}. skipping'.format(
                                    item['name']))
                                continue

                            style_id = sanitize_style_id(item['style_id'])
                            bookstr = StockXQuery.serialize_book(
                                item['name'], book)
                            transactions = StockXQuery.parse_transaction(
                                transactions_json)

                            book_filename = os.path.join(
                                outdir, sanitize_filename(style_id + '.txt'))
                            transactions_filename = os.path.join(
                                outdir, sanitize_filename(
                                    style_id + '.transaction.txt'))

                            with open(book_filename, 'w') as wfile, open(transactions_filename, 'w') as tfile:
                                wfile.write(bookstr)
                                for transaction in transactions:
                                    tfile.write("{},{},{}\n".format(
                                        transaction["shoe_size"],
                                        transaction["time"],
                                        transaction["px"]))

                            items_map.append({
                                'book': book_filename,
                                'sales_last_72': int(item['sales_last_72']),
                                'name': item['name'],
                                'last_price': -1 if 'last_sale' not in item else float(item['last_sale']),
                                'size_prices': {}
                            })
                            for shoe_size in book:
                                if len(book[shoe_size]["bid"]) == 0:
                                    best_bid = 0
                                else:
                                    best_bid = book[shoe_size]["bid"][0]["px"]
                                if len(book[shoe_size]["ask"]) == 0:
                                    best_ask = 0
                                else:
                                    best_ask = book[shoe_size]["ask"][0]["px"]

                                bid_size = 0
                                ask_size = 0
                                for level in book[shoe_size]["bid"]:
                                    if abs(
                                            level["px"] - best_bid) < relevant_levels:
                                        bid_size += level["size"]
                                for level in book[shoe_size]["ask"]:
                                    if abs(
                                            level["px"] - best_ask) < relevant_levels:
                                        ask_size += level["size"]
                                items_map[-1]['size_prices'][shoe_size] = {
                                    "best_bid": best_bid,
                                    "best_ask": best_ask,
                                    "relevant_bid_total_size": bid_size,
                                    "relevant_ask_total_size": ask_size
                                }

                                # distilled view, in current workflow this is
                                # all we care about
                                release_date = item["release_date"] if "release_date" in item else ""
                                item_to_add = {
                                    "best_bid": best_bid,
                                    "best_ask": best_ask,
                                    "sales_last_72": int(item["sales_last_72"]),
                                    "search_term": line,
                                    "url": item["url"],
                                    "name": item["name"],
                                    "style_id": item["style_id"],
                                    "release_date": release_date
                                }
                                if style_id in best_prices:
                                    best_prices[style_id][shoe_size] = item_to_add
                                else:
                                    best_prices[style_id] = {
                                        shoe_size: item_to_add}

                                bests_file.write(
                                    "{},{},{},{},{},{},{},{},{}\n".format(
                                        item["name"],
                                        item["url"],
                                        style_id,
                                        shoe_size,
                                        best_bid,
                                        best_ask,
                                        int(item["sales_last_72"]),
                                        line,
                                        release_date))

                        except TypeError as e:
                            print(e)
                            print('TypeError. skipping {}'.format(
                                item['objectID']))


                print("voluntary throttle, flush to file")
                bests_file.flush()
                time.sleep(PER_QUERY_SLEEP_TIME)

                items_map.sort(key=lambda x: x['sales_last_72'], reverse=True)
                # pp.pprint(items_map)
                # attempt1 : find "promising" shoes with a margin large enough
                # for us to make money as market makers
                promising_items += find_promising(items_map)
                print("done")

            # we no longer care about promising items for market making on
            # stockx alone.

            # with open(os.path.join(promising_dirname, "items.txt"), 'w') as promising_file:
            #     promising_file.write(pp.pformat(promising_items))
            #     for item in promising_items:
            #         basename = os.path.basename(item['book'])
            #         os.symlink(item['book'], os.path.join(
            #             promising_dirname, basename.replace(' ', '-')))

