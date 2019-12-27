#!/usr/bin/env python3

import sys

# hack for import
sys.path.append("../feed/")

import argparse
import json
import datetime

from static_info_serializer import StaticInfoSerializer
from time_series_serializer import TimeSeriesSerializer
from fees import Fees
from fx_rate import FxRate
from result_serializer import ResultSerializer


class Strategy:
    def __init__(self, fees_file, fx_rate):
        self.static_info = {}
        self.fees = Fees(fees_file, fx_rate)
        self.fx_rate = fx_rate
        self.serializer = ResultSerializer(self.fees, self.fx_rate)
        return

    def load_static_info(self, static_info_file):
        serializer = StaticInfoSerializer()
        (
            self.static_info,
            self.static_info_extras,
        ) = serializer.load_static_info_from_csv(
            static_info_file, return_key="style_id"
        )
        return

    def load_all_size_prices(self, data_folder):
        serializer = TimeSeriesSerializer(data_folder)
        self.all_size_prices = {}
        for style_id in self.static_info:
            size_prices = serializer.get(style_id)
            self.all_size_prices[style_id] = size_prices
        return

    def run(self, options):
        """
        Strategy execution.
        Steps:
          - load data (done at this point),
          - filter (configurable options),
          - rank (configurable method)
        
        @return sorted list of
          {(style_id, size_str): { mkt_data, annotation }}
        """
        total_items = 0
        matched_items = []

        # transform the input into {(style_id, size): data} format
        size_prices = {}
        for style_id in self.all_size_prices:
            for size in self.all_size_prices[style_id]:
                size_prices[(style_id, size)] = self.all_size_prices[style_id][size]
        print("total (style_id, size) pairs {}".format(len(size_prices)))

        # filter items by having last valid 'du' and 'stockx' data
        def has_data(v):
            # TODO: here we want last reading to be valid, not necessarily
            if not ("du" in v and "stockx" in v):
                return False
            if (
                not "bid_price" in v["du"]["prices"][0]
                or not "ask_price" in v["stockx"]["prices"][0]
            ):
                return False
            if (
                not v["du"]["prices"][0]["bid_price"]
                or not v["stockx"]["prices"][0]["ask_price"]
            ):
                return False
            return True

        size_prices_has_data = {k: v for k, v in size_prices.items() if has_data(v)}
        print(
            "total (style_id, size) pairs {} with data".format(
                len(size_prices_has_data)
            )
        )

        # filter items by last data being valid and recent enough
        def has_fresh_data(v, data_lifetime_seconds=259200):
            # 3 days
            if len(v["du"]["prices"]) == 0 or len(v["stockx"]["prices"]) == 0:
                return False
            last_du_time = datetime.datetime.strptime(
                v["du"]["prices"][0]["time"], "%Y%m%d-%H%M%S"
            )
            last_stockx_time = datetime.datetime.strptime(
                v["stockx"]["prices"][0]["time"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            if (
                datetime.datetime.now() - last_du_time
            ).total_seconds() > data_lifetime_seconds:
                return False
            if (
                datetime.datetime.now() - last_stockx_time
            ).total_seconds() > data_lifetime_seconds:
                return False
            return True

        size_prices_has_fresh_data = {
            k: v for k, v in size_prices_has_data.items() if has_fresh_data(v)
        }
        print(
            "total (style_id, size) pairs {} with fresh data".format(
                len(size_prices_has_fresh_data)
            )
        )

        # filter items with at least one recent enough du historical transactions
        def has_fresh_recent_transactions(v, data_lifetime_seconds=1.21e6):
            # 2 weeks
            if len(v["du"]["transactions"]) == 0:
                return False
            for i in v["du"]["transactions"]:
                transaction_time = datetime.datetime.strptime(
                    i["time"], "%Y-%m-%dT%H:%M:%S.%f"
                )
                if (
                    datetime.datetime.now() - transaction_time
                ).total_seconds() < data_lifetime_seconds:
                    return True
            return False

        size_prices_has_fresh_transactions = {
            k: v
            for k, v in size_prices_has_fresh_data.items()
            if has_fresh_recent_transactions(v)
        }
        print(
            "total (style_id, size) pairs {} with fresh transactions".format(
                len(size_prices_has_fresh_transactions)
            )
        )

        # filter items by total profit ratio
        def satisfies_total_profit_ratio(
            v, value, ratio_or_value="ratio", source="mid", dest="listing"
        ):
            if source == "mid":
                stockx_px = 0.5 * (
                    v["stockx"]["prices"][0]["bid_price"]
                    + v["stockx"]["prices"][0]["ask_price"]
                )
            elif source == "ask":
                stockx_px = v["stockx"]["prices"][0]["ask_price"]
            elif source == "bid":
                stockx_px = v["stockx"]["prices"][0]["bid_price"]
            else:
                raise RuntimeError("unrecognized ratio filter option {}".format(source))
            if dest == "listing":
                du_bid = v["du"]["prices"][0]["bid_price"] / 100
            elif dest == "last":
                du_bid = v["du"]["transactions"][0]["price"] / 100
            else:
                raise RuntimeError("unrecognized ratio filter option {}".format(dest))
            if ratio_or_value == "ratio":
                profit_value = self.fees.get_profit_percent(
                    "stockx", "du", stockx_px, du_bid, "CNY"
                )
            elif ratio_or_value == "value":
                profit_value = self.fees.get_profit_value(
                    "stockx", "du", stockx_px, du_bid, "CNY"
                )
            else:
                raise RuntimeError(
                    "unrecognizied ratio_or_value {}".format(ratio_or_value)
                )
            if profit_value > value:
                if "annotation" not in v:
                    v["annotation"] = {}
                v["annotation"][
                    "profit_{}_{}_to_{}".format(ratio_or_value, source, dest)
                ] = profit_value
                return True
            else:
                return False

        size_prices_profit_cutoff = size_prices_has_fresh_transactions
        for source in ["bid", "mid", "ask"]:
            for dest in ["listing", "last"]:
                for ratio_or_value in ["ratio", "value"]:
                    option_name = "cutoff_net_profit_{}_{}_to_{}".format(
                        ratio_or_value, source, dest
                    )
                    if option_name in options:
                        size_prices_profit_cutoff = {
                            k: v
                            for k, v in size_prices_profit_cutoff.items()
                            if satisfies_total_profit_ratio(
                                v, options[option_name], ratio_or_value, source, dest
                            )
                        }
                        print(
                            "total (style_id, size) pairs {} satisfying profit cutoff {} ({} to {}) of {}".format(
                                len(size_prices_profit_cutoff),
                                ratio_or_value,
                                source,
                                dest,
                                options[option_name],
                            )
                        )

        # sort
        result_array = [
            {"data": size_prices_profit_cutoff[k], "identifier": k}
            for k in size_prices_profit_cutoff
        ]

        result_array.sort(
            key=lambda x: x["data"]["annotation"][options["sort"]], reverse=True
        )
        print("total results {}".format(len(result_array)))
        return result_array

    def report(self, sorted_size_prices):
        self.serializer.to_str(
            sorted_size_prices, self.static_info, self.static_info_extras
        )
        return


def parse_args():
    parser = argparse.ArgumentParser(
        """
        entry point for strategy.

        example usage:
    """
    )
    parser.add_argument(
        "--start_from",
        help="the merged static info containing all eligible pairs to ask for",
    )
    parser.add_argument(
        "--data_folder",
        help="the data folder from where to look for price and transaction readings",
    )
    args = parser.parse_args()
    if not args.start_from:
        raise RuntimeError("args.start_from is required in strategy")
    return args


def parse_strategy_options(options_file):
    options = {}
    with open(options_file, "r") as infile:
        options = json.loads(infile.read())
    return options


if __name__ == "__main__":
    args = parse_args()
    fx_rate = FxRate()
    strategy = Strategy("fees.json", fx_rate)
    strategy.load_static_info(args.start_from)
    strategy.load_all_size_prices(args.data_folder)
    result = strategy.run(parse_strategy_options("options.json"))
    strategy.report(result)
