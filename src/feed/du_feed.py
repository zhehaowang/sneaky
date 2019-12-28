#!/usr/bin/env python3

import os
import json
import requests
import datetime

import pprint
import csv
import argparse
import pprint

from du_url_builder import DuRequestBuilder
from du_response_parser import DuParser, SaleRecord, DuItem
from last_updated import LastUpdatedSerializer
from time_series_serializer import TimeSeriesSerializer
from static_info_serializer import StaticInfoSerializer
from sizer import Sizer, SizerError

# for timeseries plot; these probably should belong to a different analysis binary?
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

class DuFeed:
    def __init__(self):
        self.sizer = Sizer()
        self.parser = DuParser(self.sizer)
        self.builder = DuRequestBuilder()

    def _send_du_request(self, url):
        if __debug__:
            print("request {}".format(url))
        return requests.get(url=url, headers=DuRequestBuilder.du_headers)

    def search_pages(self, keyword, pages=0, result_items=None):
        print("querying keyword {}".format(keyword))
        max_page = pages
        if max_page == 0:
            request_url = self.builder.get_search_by_keywords_url(keyword, 0, 1, 0)
            search_response = self._send_du_request(request_url)
            total_num = json.loads(search_response.text)["data"]["total"]
            max_page = total_num / 20 + 1

        def handle_search_error(search_response, e):
            # exception_name = type(e).__name__
            if search_response:
                print("search_page {} from {}".format(e, search_response.text))
            else:
                print("search_page unexpected response {}".format(e))

        if not result_items:
            result_items = {}
        for i in range(max_page):
            try:
                request_url = self.builder.get_search_by_keywords_url(keyword, i, 1, 0)
                search_response = self._send_du_request(request_url)
                items = self.parser.parse_search_results(search_response.text)
                for j in items:
                    if j.product_id in result_items:
                        print(
                            "item {} is already queried in this call".format(
                                j.product_id
                            )
                        )
                        continue
                    self._populate_item_details(j, j.product_id)
                    result_items[j.product_id] = j
            except json.decoder.JSONDecodeError as e:
                handle_search_error(search_response, e)
            except RuntimeError as e:
                handle_search_error(search_response, e)
            except KeyError as e:
                handle_search_error(search_response, e)
            except SizerError as e:
                print(
                    "search_page sizer error {} {} {}".format(
                        e.in_code, e.in_size, e.out_code
                    )
                )
        return result_items

    def _populate_item_details(self, in_item, product_id):
        request_url = self.builder.get_product_detail_url(product_id)
        product_detail_response = self._send_du_request(request_url)
        print("querying details for {} {}".format(product_id, in_item))
        (
            style_id,
            size_prices,
            release_date,
            gender,
        ) = self.parser.parse_product_detail_response(
            product_detail_response.text, self.sizer
        )
        print("inferred gender: {}".format(gender))
        in_item.populate_details(style_id, size_prices, release_date, gender)
        return

    def get_size_prices_from_product_id(self, product_id):
        try:
            # TODO: we don't actually use loaded static_info's gender in update, do we?
            # ^this is arguably better?
            request_url = self.builder.get_product_detail_url(product_id)
            product_detail_response = self._send_du_request(request_url)
            _, size_prices, _, gender = self.parser.parse_product_detail_response(
                product_detail_response.text, self.sizer
            )
            return size_prices, gender
        except RuntimeError as e:
            print("get_detail runtime error {}".format(e))
            return None
        except json.decoder.JSONDecodeError as e:
            print("get_detail unexpected response {}".format(e))
            return None
        except KeyError as e:
            print("get_detail key error {}".format(e))
            return None

    def get_details_from_product_id_raw(self, product_id):
        request_url = self.builder.get_product_detail_url(product_id)
        return self._send_du_request(request_url).text

    def get_transactions_from_product_id_raw(self, product_id):
        recentsales_list_url = self.builder.get_recentsales_list_url(0, product_id)
        return self._send_du_request(recentsales_list_url).text

    def split_size_transactions(self, transactions):
        result = {}
        for t in transactions:
            if t.size not in result:
                result[t.size] = []
            else:
                result[t.size].append({"price": t.price, "time": t.time, "id": t.id})
        return result

    def get_historical_transactions(
        self, product_id, in_code, max_page=0, up_to_time=None, up_to_id=None
    ):
        def get_one_page(page, product_id, in_code):
            recentsales_list_url = self.builder.get_recentsales_list_url(
                page, product_id
            )
            recentsales_list_response = requests.get(
                url=recentsales_list_url, headers=DuRequestBuilder.du_headers
            )
            return self.parser.parse_recent_sales(
                recentsales_list_response.text, in_code
            )

        all_sales = []
        page_idx = 0
        while max_page >= 0:
            page_idx, sales = get_one_page(page_idx, product_id, in_code)
            if len(sales) == 0:
                return all_sales
            all_sales += sales
            if (
                up_to_time
                and datetime.datetime.strptime(sales[-1].time, "%Y-%m-%dT%H:%M:%S.%fZ")
                < up_to_time
            ):
                return all_sales
            if up_to_id:
                for sale in all_sales[::-1]:
                    if sale.id == up_to_id:
                        return all_sales
            max_page -= 1
        return all_sales


def parse_args():
    parser = argparse.ArgumentParser(
        """
        entry point for du feed.

        example usage:
          ./du_feed.py --mode update --start_from du.mapping.20191206-211125.csv --min_interval_seconds 3600 --transaction_history_date 20190801 --transaction_history_maxpage 20
          ./du_feed.py --mode query --kw aj --pages 2 --start_from du.mapping.20191206-145908.csv
          ./du_feed.py --mode query --kw aj --pages 30
          ./du_feed.py --mode getraw --style_id 575441-028 --start_from merged.20191225.csv
          ./du_feed.py --mode gets --style_id BQ6623-800 --start_from du.historical.csv --transaction_history_date 20190801 --transaction_history_maxpage 20 --plot_size 9.5
    """
    )
    parser.add_argument(
        "--mode",
        help=(
            "[query|update|getraw|gets]"
            "query builds the static mapping file,"
            "update takes a mapping and updates entries,"
            "getraw retrieves product detail and transactions (raw) for a style id,"
            "gets retrieves structured size prices and transactions for a style id, mimicing what would be written in update mode"
        ),
    )
    parser.add_argument("--kw", help="in query mode, the query keyword")
    parser.add_argument(
        "--start_from",
        help="in query mode, continue from entries not already populated in given\n"
        "in update mode, the file from which to load the product_id, style_id mapping",
    )
    parser.add_argument("--pages", help="in query mode, the number of pages to query")
    parser.add_argument(
        "--last_updated",
        help="in update mode, the file containing the last_updated time of each item",
    )
    parser.add_argument(
        "--min_interval_seconds",
        help="in update mode, only items whose last update time is at least this much from now will get updated",
    )
    parser.add_argument(
        "--style_id",
        help="in get modes, get product detail for this style_id. No effect in other modes",
    )
    parser.add_argument(
        "--product_id",
        help="in get modes, get product detail for this product_id. No effect in other modes",
    )
    parser.add_argument(
        "--limit",
        help="in update mode, the most number of entries this will attempt to update",
    )
    parser.add_argument(
        "--transaction_history_date",
        help="in update mode, the furthest back in time this tries to look for historical transactions\n"
        "this performs an 'and' on all conditions",
    )
    parser.add_argument(
        "--transaction_history_maxpage",
        help="in update mode, the furthest back in pages this tries to look for historical transactions\n"
        "this performs an 'and' on all conditions",
    )
    parser.add_argument(
        "--plot_size",
        help="in gets mode, plot the historical prices of the given size"
    )
    args = parser.parse_args()
    return args


def query_mode(args):
    feed = DuFeed()
    serializer = StaticInfoSerializer()

    keywords = []
    if os.path.isfile(args.kw):
        with open(args.kw, "r") as infile:
            keywords = infile.read().split("\n")
    else:
        keywords = args.kw.split(",")
    if args.start_from:
        result_items, _ = serializer.load_static_info_from_csv(
            args.start_from, return_key="du_product_id"
        )
    else:
        result_items = {}

    for keyword in keywords:
        result_items = feed.search_pages(
            keyword.strip(), pages=int(args.pages), result_items=result_items
        )
    serializer.dump_static_info_to_csv(result_items)


def update_mode(args):
    feed = DuFeed()
    serializer = StaticInfoSerializer()

    last_updated_file = "last_updated.log"
    if args.last_updated:
        last_updated_file = args.last_updated

    last_updated_serializer = LastUpdatedSerializer(
        last_updated_file, args.min_interval_seconds
    )
    time_series_serializer = TimeSeriesSerializer()

    static_info, _ = serializer.load_static_info_from_csv(
        args.start_from, return_key="du_product_id"
    )
    count = 0
    try:
        for product_id in static_info:
            style_id = static_info[product_id].style_id
            if last_updated_serializer.should_update(style_id, "du"):
                count += 1
                if args.limit and count > int(args.limit):
                    break
                print(
                    "working with {} style_id {} brand {}".format(
                        product_id, style_id, static_info[product_id].title
                    )
                )
                try:
                    size_prices, gender = feed.get_size_prices_from_product_id(product_id)

                    max_page = (
                        int(args.transaction_history_maxpage)
                        if args.transaction_history_maxpage
                        else 0
                    )
                    up_to_time = (
                        datetime.datetime.strptime(
                            args.transaction_history_date, "%Y%m%d"
                        )
                        if args.transaction_history_date
                        else None
                    )
                    transactions = feed.get_historical_transactions(
                        product_id, gender, max_page=max_page, up_to_time=up_to_time
                    )
                    size_transactions = feed.split_size_transactions(transactions)
                    
                    update_time = last_updated_serializer.update_last_updated(
                        style_id, "du"
                    )
                    time_series_serializer.update(
                        "du", update_time, style_id, size_prices, size_transactions
                    )
                except KeyError as e:
                    print("get_tick failed {}".format(e))
                except RuntimeError as e:
                    print("get_tick failed {}".format(e))
                except json.decoder.JSONDecodeError as e:
                    print("get_tick failed {}".format(e))
                except SizerError as e:
                    print(e.msg, e.in_code, e.out_code, e.in_size)
                last_updated_serializer.save_last_updated()
            else:
                print("should skip {}".format(product_id))
    except KeyboardInterrupt:
        last_updated_serializer.save_last_updated()
        print("Caught KeyboardInterrupt. Saving last_updated and exiting")
        exit(1)


def get_mode(args):
    feed = DuFeed()
    serializer = StaticInfoSerializer()
    pp = pprint.PrettyPrinter()

    if args.style_id:
        static_info, _ = serializer.load_static_info_from_csv(
            args.start_from, return_key="style_id"
        )
        if not args.style_id in static_info:
            print(
                "cannot find product info for {} from {}".format(
                    args.style_id, args.start_from
                )
            )
            return
        else:
            static_item = static_info[args.style_id]
            print(static_item)
            product_id = static_item.product_id
    elif args.product_id:
        product_id = args.product_id

    if args.mode == "getraw":
        product_detail_response = feed.get_details_from_product_id_raw(
            product_id
        )
        details_obj = json.loads(product_detail_response)
        pp.pprint(details_obj)

        recentsales_list_response = feed.get_transactions_from_product_id_raw(
            product_id
        )
        transaction_obj = json.loads(recentsales_list_response)
        pp.pprint(transaction_obj)
    elif args.mode == "gets":
        size_prices, gender = feed.get_size_prices_from_product_id(product_id)
        pp.pprint(size_prices)
        print(gender)
        max_page = (
            int(args.transaction_history_maxpage)
            if args.transaction_history_maxpage
            else 0
        )
        up_to_time = (
            datetime.datetime.strptime(
                args.transaction_history_date, "%Y%m%d"
            )
            if args.transaction_history_date
            else None
        )
        transactions = feed.get_historical_transactions(
            product_id, gender, max_page=max_page, up_to_time=up_to_time
        )
        for t in transactions:
            print(t)
        if args.plot_size:
            reversed_t = transactions[::-1]
            for t in reversed_t:
                t.size = t.size.strip().strip('Y')

            x = np.array([datetime.datetime.strptime(t.time, "%Y-%m-%dT%H:%M:%S.%fZ") for t in reversed_t if float(t.size) == float(args.plot_size)])
            y = np.array([(t.price / 100) for t in reversed_t if float(t.size) == float(args.plot_size)])

            if len(x) > 0:
                months = mdates.MonthLocator()  # every month
                year_month_fmt = mdates.DateFormatter('%Y%m')

                fig, ax = plt.subplots()

                ax.plot(x, y)
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
                if args.style_id:
                    fig_filename = "{}.{}.png".format(args.style_id, args.plot_size)
                elif args.product_id:
                    fig_filename = "{}.{}.png".format(args.product_id, args.plot_size)
                fig.suptitle(fig_filename)
                plt.savefig(fig_filename)
                print("historical transaction figure saved to {}".format(fig_filename))

                plt.show()            
            else:
                print("no historical transactions found for {} {}".format(args.style_id, args.plot_size))
            

if __name__ == "__main__":
    args = parse_args()

    if args.mode == "query":
        if not args.kw:
            raise RuntimeError("args.kw is mandatory in query mode")
        if not args.pages:
            raise RuntimeError("args.pages is mandatory in query mode")
        query_mode(args)
    elif args.mode == "update":
        if not args.start_from:
            raise RuntimeError("args.start_from is mandatory in update mode")
        update_mode(args)
    elif args.mode == "getraw" or args.mode == "gets":
        if not args.start_from:
            raise RuntimeError("args.start_from is required in get modes")
        if not args.style_id and not args.product_id:
            raise RuntimeError("one among args.style_id and args.product_id is required in get modes")
        get_mode(args)
    else:
        raise RuntimeError("Unsupported mode {}".format(args.mode))
