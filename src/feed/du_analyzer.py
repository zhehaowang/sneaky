#!/usr/bin/env python3

import argparse
import sys
import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# only needed when running this binary
from time_series_serializer import TimeSeriesSerializer
from du_response_parser import SaleRecord
import sys
# hack for import
sys.path.append("../strategy/")
from fx_rate import FxRate

"""
Provides analytics (price history, volume, vol) based on given transactions.
Built-in binary takes stored time series. Import in feed (gets) for live data processing.
"""

class ItemAnalyzer:
    def __init__(self):
        return

    @staticmethod
    def to_ordered_sale_record(transactions):
        result = []
        for t in transactions[::-1]:
            # size or id matters not
            result.append(SaleRecord("", t["price"], t["time"]))
        return result

    def plot_historical_transactions(self, transactions, plot_title=None, save_png=None):
        """
        Given ordered transactions (earliest to latest), plot transaction prices on a monthly scale.
        Optionally title and save the plot.
        """
        x = np.array([datetime.datetime.strptime(t.time, "%Y-%m-%dT%H:%M:%S.%fZ") for t in transactions])
        y = np.array([(t.price / 100) for t in transactions])

        if len(x) > 0:
            months = mdates.MonthLocator()  # every month
            year_month_fmt = mdates.DateFormatter('%Y%m')

            fig, ax = plt.subplots()

            ax.plot(x, y, marker='o')
            # format the ticks
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(year_month_fmt)

            # round to nearest months.
            datemin = np.datetime64(x[0], 'm')
            datemax = np.datetime64(x[-1], 'm') + np.timedelta64(1, 'm')
            ax.set_xlim(datemin, datemax)

            # format the coords message box
            ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
            ax.format_ydata = lambda x: '$%1.2f' % x  # format the price.
            ax.grid(True)

            # rotates and right aligns the x labels, and moves the bottom of the
            # axes up to make room for them
            fig.autofmt_xdate()

            if plot_title:
                fig.suptitle(plot_title)
            if save_png:
                plt.savefig(save_png)
                print("historical transaction figure saved to {}".format(save_png))

            plt.show()            
        else:
            print("no historical transactions found for {} {}".format(args.style_id, args.plot_size))
    
    def get_historical_transactions_stats(self, transactions, furthest_back=None):
        dates = [datetime.datetime.strptime(t.time, "%Y-%m-%dT%H:%M:%S.%fZ") for t in transactions]
        prices = [(t.price / 100) for t in transactions]

        if furthest_back:
            for idx in range(0, len(dates)):
                if dates[idx] < furthest_back:
                    dates = dates[:idx]
                    prices = prices[:idx]
                    break

        start_date = dates[0]
        end_date = dates[-1]

        elapsed_days = (end_date - start_date).days + 1
        sales_per_day = float(len(prices)) / elapsed_days
        high = max(prices)
        low = min(prices)
        last = prices[-1]
        
        prices_np = np.array(prices)
        stdev = np.std(prices_np)
        avg = np.average(prices_np)

        return {
            "num_sales": len(prices),
            "elapsed_days": elapsed_days,
            "sales_per_day": sales_per_day,

            "high": high,
            "low": low,
            "first": prices[0],
            "last": last,
            "first_date": start_date,
            "last_date": end_date,

            "avg": avg,
            "stdev": stdev,
        }


def parse_args():
    parser = argparse.ArgumentParser(
        """
        entry point for Du analysis.

        example usage:
            ./du_analyzer.py --style_id BQ6623-800 --size 9.5 --mode plot
    """
    )
    parser.add_argument(
        "--mode",
        help="comma separated list of [plot|stats] to perform"
    )
    parser.add_argument(
        "--style_id",
        help="the style id to analyze",
    )
    parser.add_argument(
        "--size",
        help="the size to analyze",
    )
    args = parser.parse_args()
    if not args.style_id:
        parser.print_help(sys.stderr)
        raise RuntimeError("args.style_id is required in analysis")
    if not args.size:
        parser.print_help(sys.stderr)
        raise RuntimeError("args.size is required in analysis")
    if not args.mode:
        parser.print_help(sys.stderr)
        raise RuntimeError("args.mode is required in analysis")
    return args


def serialize_stats(stats, fx_rate):
    serialized = """
        First Date:       {}
        Last Date:        {}
        Number of Sales:  {}
        Sales / Day:      {:.2f}
        High:             {:.2f} CNY {:.2f} USD
        Low:              {:.2f} CNY {:.2f} USD
        First:            {:.2f} CNY {:.2f} USD
        Last:             {:.2f} CNY {:.2f} USD
        Average:          {:.2f} CNY {:.2f} USD
        Stdev:            {:.2f}
    """.format(
        stats["first_date"].isoformat(),
        stats["last_date"].isoformat(),
        stats["num_sales"],
        stats["sales_per_day"],
        stats["high"], fx_rate.get_spot_fx(stats["high"], "CNY", "USD"),
        stats["low"], fx_rate.get_spot_fx(stats["low"], "CNY", "USD"),
        stats["first"], fx_rate.get_spot_fx(stats["first"], "CNY", "USD"),
        stats["last"], fx_rate.get_spot_fx(stats["last"], "CNY", "USD"),
        stats["avg"], fx_rate.get_spot_fx(stats["avg"], "CNY", "USD"),
        stats["stdev"])
    return serialized


if __name__ == "__main__":
    args = parse_args()
    analyzer = ItemAnalyzer()

    serializer = TimeSeriesSerializer()
    data = serializer.get(args.style_id, args.size)
    du_transactions = data[args.size]["du"]["transactions"]
    if len(du_transactions) == 0:
        print("no transactions found for {} {}".format(args.style_id, args.size))
        exit(0)
    transactions = ItemAnalyzer.to_ordered_sale_record(du_transactions)

    modes = args.mode.split(',')

    for mode in modes:
        if mode == "plot":
            analyzer.plot_historical_transactions(transactions)
        elif mode == "stats":
            stats = analyzer.get_historical_transactions_stats(transactions)
            fx_rate = FxRate()
            print(serialize_stats(stats, fx_rate))
        else:
            raise RuntimeError("unrecognized mode {}".format(mode))
