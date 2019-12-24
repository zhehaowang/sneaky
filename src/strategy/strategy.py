#!/usr/bin/env python3

import sys
# hack for import
sys.path.append('../feed/')

import argparse
import json
import datetime

from static_info_serializer import StaticInfoSerializer
from time_series_serializer import TimeSeriesSerializer
from fees import Fees
from fx_rate import FxRate

class Strategy():
    def __init__(self, fees_file, fx_rate):
        self.static_info = {}
        self.fees = Fees(fees_file, fx_rate)
        self.fx_rate = fx_rate
        return
    
    def load_static_info(self, static_info_file):
        serializer = StaticInfoSerializer()
        self.static_info = serializer.load_static_info_from_csv(static_info_file, return_key="style_id")
        return

    def load_all_size_prices(self, style_ids=None):
        serializer = TimeSeriesSerializer()
        self.all_size_prices = {}
        for style_id in self.static_info:
            size_prices = serializer.get(style_id)
            self.all_size_prices[style_id] = size_prices
        return

    def run(self, options):
        total_items = 0
        matched_items = []
        
        # transform the input into {(style_id, size): data} format
        size_prices = {}
        for style_id in self.all_size_prices:
            for size in self.all_size_prices[style_id]:
                size_prices[(style_id, size)] = self.all_size_prices[style_id][size]
        print('total (style_id, size) pairs {}'.format(len(size_prices)))

        # filter items by having last valid 'du' and 'stockx' data
        def has_data(v):
            # TODO: here we want last reading to be valid, not necessarily
            if not ("du" in v and "stockx" in v):
                return False
            if not v["du"]["prices"][-1]["bid_price"] or not v["stockx"]["prices"][-1]["ask_price"]:
                return False
            return True
        size_prices_has_data = {
            k : v for k, v in size_prices.items() if has_data(v)
        }
        print('total (style_id, size) pairs {} with data'.format(len(size_prices_has_data)))

        # filter items by last data being valid and recent enough
        def has_fresh_data(v, data_lifetime_seconds=259200):
            # 3 days
            if len(v["du"]["prices"]) == 0 or len(v["stockx"]["prices"]) == 0:
                return False
            # TODO: here we are assuming ordered. Not unnecessarily
            last_du_time = datetime.datetime.strptime(v["du"]["prices"][-1]["time"], "%Y%m%d-%H%M%S")
            last_stockx_time = datetime.datetime.strptime(v["stockx"]["prices"][-1]["time"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if (datetime.datetime.now() - last_du_time).total_seconds() > data_lifetime_seconds:
                return False
            if (datetime.datetime.now() - last_stockx_time).total_seconds() > data_lifetime_seconds:
                return False
            return True
        size_prices_has_fresh_data = {
            k : v for k, v in size_prices_has_data.items() if has_fresh_data(v)
        }
        print('total (style_id, size) pairs {} with fresh data'.format(len(size_prices_has_fresh_data)))

        # filter items with at least one recent enough du historical transactions
        def has_fresh_recent_transactions(v, data_lifetime_seconds=1.21e+6):
            # 2 weeks
            if len(v["du"]["transactions"]) == 0:
                return False
            for i in v["du"]["transactions"]:
                transaction_time = last_stockx_time = datetime.datetime.strptime(i["time"], "%Y-%m-%dT%H:%M:%S.%f")
                if (datetime.datetime.now() - transaction_time).total_seconds() < data_lifetime_seconds:
                    return True
            return False
        size_prices_has_fresh_transactions = {
            k : v for k, v in size_prices_has_fresh_data.items() if has_fresh_recent_transactions(v)
        }
        print('total (style_id, size) pairs {} with fresh transactions'.format(len(size_prices_has_fresh_transactions)))

        # filter items by total profit ratio cutoff
        if "cutoff_net_profit_ratio" in options:
            def satisfies_total_profit_ratio(v, ratio):
                stockx_mid = 0.5 * (v["stockx"]["prices"][-1]["bid_price"] + v["stockx"]["prices"][-1]["ask_price"])
                du_bid = v["du"]["prices"][-1]["bid_price"] / 100
                profit_ratio_mid = self.fees.get_profit_percent(
                    "stockx", "du", stockx_mid, du_bid, "CNY")
                if profit_ratio_mid > ratio:
                    profit_ratio_cross = self.fees.get_profit_percent(
                        "stockx", "du", v["stockx"]["prices"][-1]["ask_price"], du_bid, "CNY")
                    v["annotation"] = {
                        "profit_ratio_mid": profit_ratio_mid,
                        "profit_ratio_cross": profit_ratio_cross
                    }
                    return True
                else:
                    return False
            size_prices_profit_ratio = {
                k : v for k, v in size_prices_has_fresh_transactions.items() if satisfies_total_profit_ratio(v, options["cutoff_net_profit_ratio"])
            }
            print('total (style_id, size) pairs {} satisfying profit cutoff ratio of {}'.format(len(size_prices_profit_ratio), options["cutoff_net_profit_ratio"]))
        else:
            size_prices_profit_ratio = size_prices_has_fresh_transactions
                    
        print("total results {}".format(len(size_prices_profit_ratio)))
        for i in size_prices_profit_ratio:
            style_id, size = i
            item = self.static_info[style_id]
            size_prices_profit_ratio[i]["annotation"]["du_price_usd"] = self.fx_rate.get_spot_fx(
                size_prices_profit_ratio[i]["du"]["prices"][-1]["bid_price"] / 100,
                "CNY", "USD"
            )
            size_prices_profit_ratio[i]["annotation"]["du_last_transaction_usd"] = self.fx_rate.get_spot_fx(
                size_prices_profit_ratio[i]["du"]["transactions"][0]["price"] / 100,
                "CNY", "USD"
            )

            print(i, item)
            # print(size_prices_profit_ratio[i])
            print("  du listing price:     {:.2f} CNY {:.2f} USD\n"
                  "  du transaction price: {:.2f} CNY {:.2f} USD\n"
                  "  du transaction time:  {}\n"
                  "  stockx bid:           {:.2f} USD\n"
                  "  stockx ask:           {:.2f} USD\n"
                  "  profit ratio (mid):   {:.2f} %\n"
                  "  profit ratio (cross): {:.2f} %\n"
                  "  profit value (cross): {:.2f} USD\n".format(
                size_prices_profit_ratio[i]["du"]["prices"][-1]["bid_price"] / 100,
                size_prices_profit_ratio[i]["annotation"]["du_price_usd"],
                size_prices_profit_ratio[i]["du"]["transactions"][0]["price"] / 100,
                size_prices_profit_ratio[i]["annotation"]["du_last_transaction_usd"],
                size_prices_profit_ratio[i]["du"]["transactions"][0]["time"],
                size_prices_profit_ratio[i]["stockx"]["prices"][-1]["ask_price"],
                size_prices_profit_ratio[i]["stockx"]["prices"][-1]["bid_price"],
                size_prices_profit_ratio[i]["annotation"]["profit_ratio_mid"] * 100,
                size_prices_profit_ratio[i]["annotation"]["profit_ratio_cross"] * 100,
                self.fees.get_profit_value(
                    "stockx",
                    "du",
                    size_prices_profit_ratio[i]["stockx"]["prices"][-1]["ask_price"],
                    size_prices_profit_ratio[i]["du"]["prices"][-1]["bid_price"] / 100, "CNY")))
        return

def parse_args():
    parser = argparse.ArgumentParser("""
        entry point for strategy.

        example usage:
    """)
    parser.add_argument(
        "--start_from",
        help="in query mode, continue from entries not already populated in given\n"
             "in update mode, the file from which to load the product_id, style_id mapping")
    args = parser.parse_args()
    if not args.start_from:
        raise RuntimeError("args.start_from is required in strategy")
    return args

def parse_strategy_options(options_file):
    options = {}
    with open(options_file, 'r') as infile:
        options = json.loads(infile.read())
    return options

if __name__ == "__main__":
    args = parse_args()
    fx_rate = FxRate()
    strategy = Strategy("fees.json", fx_rate)
    strategy.load_static_info(args.start_from)
    strategy.load_all_size_prices()
    strategy.run(parse_strategy_options("options.json"))



