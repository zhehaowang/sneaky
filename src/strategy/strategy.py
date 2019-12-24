#!/usr/bin/env python3

import sys
# hack for import
sys.path.append('../feed/')

import argparse

from static_info_serializer import StaticInfoSerializer
from time_series_serializer import TimeSeriesSerializer

class Strategy():
    def __init__(self):
        self.static_info = {}
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

    def find_best(self):
        total_items = 0
        for style_id in self.all_size_prices:
            for size in self.all_size_prices[style_id]:
                if "du" in self.all_size_prices[style_id][size] and "stockx" in self.all_size_prices[style_id][size]:
                    du_item = self.all_size_prices[style_id][size]["du"]
                    stockx_item = self.all_size_prices[style_id][size]["stockx"]
                    total_items += 1
        print("total (model, size) matched {}".format(total_items))
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

if __name__ == "__main__":
    args = parse_args()
    strategy = Strategy()
    strategy.load_static_info(args.start_from)
    strategy.load_all_size_prices()
    strategy.find_best()



