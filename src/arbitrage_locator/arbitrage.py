#!/usr/bin/env python3

import os
import re
import sys
import json
import csv

import pprint
import datetime

pp = pprint.PrettyPrinter()

def sanitize_key(key):
    return key.lower().replace('-', '').replace(' ', '')

def sanitize_size(size):
    return size.strip('.0')

def read_files(fc_file, stockx_file):
    """Read in two files and produce two dictionaries of stockx and flightclub
    prices

    @param str fc_file name
    @param str stockx_file name
    @return fc_dict, stockx_dict, both of the form
        {"style-id": {"8": {...},
                      "9": {...}}}
    """
    fc_prices = {}
    sx_prices = {}

    with open(fc_file, "r") as rfile:
        fc_prices_presantize = json.loads(rfile.read())

    for key in fc_prices_presantize:
        fc_prices[sanitize_key(key)] = fc_prices_presantize[key]

    with open(stockx_file, "r") as rfile:
        stockx_reader = csv.reader(rfile, delimiter=',', quotechar='\"')
        for row in stockx_reader:
            style_id = row[2]
            name = row[0]
            url = 'https://stockx.com/' + row[1]
            shoe_size = row[3]
            best_bid = float(row[4])
            best_ask = float(row[5])
            sx_volume_last_72 = int(row[6])
            if style_id.lower() != "none":
                if best_ask > 0:
                    style_id = sanitize_key(style_id)
                    if style_id in sx_prices:
                        sx_prices[style_id][shoe_size] = {
                            "name": name,
                            "url": url,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "sales_last_72": sx_volume_last_72
                        }
                    else:
                        sx_prices[style_id] = {shoe_size: {
                            "name": name,
                            "url": url,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "sales_last_72": sx_volume_last_72
                        }}
            else:
                print("{} (url: {}) has None style ID".format(name, url))

    return fc_prices, sx_prices

def match_items(fc_prices, sx_prices):
    """Combine given dictionaries of fc prices and stockx prices and produce
    matched items.

    @param dict fc_prices {"style_id": {"8": {...}}}
    @param dict sx_prices {"style_id": {"8": {...}}}
    @return matched dict
        {"style_id": {"8":
            {"fc": {...},
             "sx": {...}}}}
    """
    matches = {}
    total_matches = 0
    total_model_matches = 0

    for style_id in fc_prices:
        if style_id in sx_prices:
            total_model_matches += 1
            for size in fc_prices[style_id]:
                # TODO: strip this awkward float - str match
                sx_size = sanitize_size(size)
                if sx_size in sx_prices[style_id]:
                    total_matches += 1
                    fc_item = fc_prices[style_id][size]
                    sx_item = sx_prices[style_id][sx_size]
                    if not style_id in matches:
                        matches[style_id] = {
                            size: {
                                "fc": fc_item,
                                "sx": sx_item
                            }}
                    else:
                        matches[style_id][size] = {"fc": fc_item, "sx": sx_item}

    pp.pprint("found {} model matches, {} (model, size) matches".format(
        total_model_matches, total_matches))
    return matches

def find_margin(matches):
    """Given the combined prices from sx and fc produce a dict of items with
    crossing margin computed.

    @param matched dict
        {"style_id": {"8":
            {"fc": {...},
             "sx": {...}}}}
    @return {"fc_url?size": {"crossing_margin": xxx, 
                             "sx_xxx": ...,
                             "fc_yyy": ...}}
    """
    sx_threshold = 50
    sx_bid_commission = 13.95
    fc_commission_rate = 0.2
    cut_in_tick = 1

    total_model_size_pairs = 0
    margins = {}

    for style_id in matches:
        for size in matches[style_id]:
            total_model_size_pairs += 1
            item = matches[style_id][size]

            # eligible items from stockx
            if item['sx']['best_ask'] and item['sx']['best_bid']:
                if int(item['sx']['sales_last_72']) > sx_threshold:

                    crossing_margin = float(item['fc']['px'].replace(',', '')) * (1 - fc_commission_rate) - float(item['sx']['best_ask']) - sx_bid_commission
                    crossing_margin_rate = crossing_margin / float(item['sx']['best_ask'])

                    if item['sx']['best_bid'] > 0:
                        adding_margin = float(item['fc']['px'].replace(',', '')) * (1 - fc_commission_rate) - float(item['sx']['best_bid']) - (cut_in_tick + sx_bid_commission)
                        adding_margin_rate = adding_margin / (float(item['sx']['best_bid']) + cut_in_tick)
                    else:
                        adding_margin = 0
                        adding_margin_rate = 0

                    fc_url_with_size = item['fc']['url'] + '?size=' + size
                    match_item = {
                        # 'style_id': style_id,
                        'shoe_size': size,

                        'fc_px': item['fc']['px'],
                        'fc_url': fc_url_with_size,

                        'sx_best_bid': item['sx']['best_bid'],
                        'sx_best_ask': item['sx']['best_ask'],
                        'sx_volume_last_72': item['sx']['sales_last_72'],
                        'sx_url': item['sx']['url'],
                        'sx_transactions': item['sx']['sx_transactions']
                            if 'sx_transactions' in item['sx'] else [],

                        'crossing_margin': crossing_margin,
                        'crossing_margin_rate': crossing_margin_rate,
                        'adding_margin': adding_margin,
                        'adding_margin_rate': adding_margin_rate
                    }
                    margins[style_id + ' ' + size] = match_item
    # pp.pprint(margins)
    return margins

def annotate_transaction_history(sx_prices, data_prefix="../../data/stockx/"):
    for style_id in sx_prices:
        style_id_file = os.path.join(data_prefix, style_id + ".transaction.txt")
        transactions = {}

        if os.path.isfile(style_id_file):
            with open(style_id_file, 'r') as sfile:
                transactions_reader = csv.reader(
                    sfile, delimiter=',', quotechar='\"')
                for row in transactions_reader:
                    size = row[0]
                    time = row[1]
                    px = row[2]
                    if size in transactions:
                        transactions[size].append({"time": time, "px": px})
                    else:
                        transactions[size] = [{"time": time, "px": px}]
            for size in sx_prices[style_id]:
                if size in transactions:
                    sx_prices[style_id][size]["sx_transactions"] = transactions[size]
            # print('attached transactions: {}'.format(style_id))

    return sx_prices

if __name__ == "__main__":
    runtime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    fc_prices, sx_prices = read_files("flightclub.20190614.txt", "best_prices.txt")
    sx_prices = annotate_transaction_history(sx_prices, "../../data/stockx/20190615-145954/")
    matches = match_items(fc_prices, sx_prices)

    margins = find_margin(matches)

    crossing_margin_rate_sorted_items = sorted(margins.items(), key=lambda kv: kv[1]['crossing_margin_rate'], reverse=True)
    with open("crossing_margin_sorted.{}.txt".format(runtime), "w") as wfile:
        wfile.write(pp.pformat(crossing_margin_rate_sorted_items))

    regular_size_crossing_margin_rate_sorted_items = []
    for item in crossing_margin_rate_sorted_items:
        shoe_size = float(item[1]['shoe_size'])
        if shoe_size == 9.0 or shoe_size == 8.5 or shoe_size == 9.5:
            regular_size_crossing_margin_rate_sorted_items.append(item[1])

    with open("regular_size_crossing_margin_sorted.{}.txt".format(runtime), "w") as wfile:
        wfile.write(pp.pformat(regular_size_crossing_margin_rate_sorted_items))

