#!/usr/bin/env python3

import os
import re
import sys
import json

import pprint

pp = pprint.PrettyPrinter()

def analyze_match(match_file):
    current_term = ""
    mapping = {}
    # <search_term, [titles]>
    cnts = {}
    # <number_of_matches, [search_terms]>

    with open(match_file, "r") as rfile:
        for line in rfile:
            match = re.match("Querying (.+)", line)
            if match:
                current_term = match.group(1)
            else:
                title_match = re.match("product title: (.+)", line)
                if title_match:
                    item = title_match.group(1)
                    if not current_term in mapping:
                        mapping[current_term] = [title_match]
                    else:
                        mapping[current_term].append(title_match)

    for key in mapping:
        if not len(mapping[key]) in cnts:
            cnts[len(mapping[key])] = [key]
        else:
            cnts[len(mapping[key])].append(key)

    for key in sorted(list(cnts.keys())):
        print("{} search terms matched with {} items from stockx".format(len(cnts[key]), key))

    if 1 in cnts:
        return cnts[1]
    else:
        return []

def read_files(match_filter, fc_file, stockx_files):
    fc_prices = {}
    sx_prices = {}
    res_sx_prices = {}
    print(match_filter)

    with open(fc_file, "r") as rfile:
        fc_prices = json.loads(rfile.read())

    for key in list(fc_prices.keys()):
        if not key in match_filter:
            del fc_prices[key]

    for f in stockx_files:
        with open(f, "r") as rfile:
            obj = json.loads(rfile.read())
            for key in obj:
                sx_prices[key] = obj[key]

    for key in sx_prices:
        search_term = ""
        for size in sx_prices[key]:
            search_term = sx_prices[key][size]['search_term'].strip()
            break
        if search_term in match_filter:
            if search_term in res_sx_prices:
                res_sx_prices[search_term].append(sx_prices[key])
            else:
                res_sx_prices[search_term] = [sx_prices[key]]

    return fc_prices, res_sx_prices

def match_items(fc_prices, sx_prices):
    # pp.pprint(len(list(fc_prices.keys())))
    # pp.pprint(list(sx_prices.keys()))

    # TODO: sx_prices reports 36 keys while fc_prices has the all 75.
    # It appears stockx_feed saved all to book str out, but not all to best_prices out.
    
    matches = {}
    for term in fc_prices:
        for item in fc_prices[term]:
            if term in sx_prices:
                size = str(float(item['fc_size']))
                # assume we only trust 1-1 match
                # print(list(sx_prices[term][0].keys()))
                # print(size)
                if size in sx_prices[term][0]:
                    fc_item = item
                    sx_item = sx_prices[term][0][size]
                    if not term in matches:
                        matches[term] = {size: {"fc": fc_item, "sx": sx_item}}
                    else:
                        matches[term][size] = {"fc": fc_item, "sx": sx_item}
    return matches

def find_margin(matches):
    sx_threshold = 50
    sx_bid_commission = 13.95
    fc_commission_rate = 0.2
    cut_in_tick = 1

    total_model_size_pairs = 0
    margins = {}

    for search_term in matches:
        for size in matches[search_term]:
            total_model_size_pairs += 1
            item = matches[search_term][size]

            # eligible items from stockx
            if item['sx']['best_ask'] and item['sx']['best_bid']:
                if item['sx']['sales_last_72'] > sx_threshold:

                    crossing_margin = float(item['fc']['fc_px'].replace(',', '')) * (1 - fc_commission_rate) - float(item['sx']['best_ask']) - sx_bid_commission
                    adding_margin = float(item['fc']['fc_px'].replace(',', '')) * (1 - fc_commission_rate) - float(item['sx']['best_bid']) - (cut_in_tick + sx_bid_commission)

                    crossing_margin_rate = crossing_margin / float(item['sx']['best_ask'])
                    adding_margin_rate = adding_margin / (float(item['sx']['best_bid']) + cut_in_tick)

                    margins[item['fc']['fc_url'] + ' -- ' + size] = {
                        'search_term': search_term,
                        'shoe_size': size,

                        'fc_px': item['fc']['fc_px'],
                        'fc_url': item['fc']['fc_url'],

                        'sx_best_bid': item['sx']['best_bid'],
                        'sx_best_ask': item['sx']['best_ask'],
                        'sx_volume_last_72': item['sx']['sales_last_72'],
                        'sx_url': "https://stockx.com/" + item['sx']['url'],

                        'crossing_margin': crossing_margin,
                        'crossing_margin_rate': crossing_margin_rate,
                        'adding_margin': adding_margin,
                        'adding_margin_rate': adding_margin_rate
                    }


    print("found matching {} (model, size) in fc and sx".format(total_model_size_pairs))
    return margins

if __name__ == "__main__":
    matches_filter = analyze_match("match.txt")
    fc_prices, sx_prices = read_files(matches_filter, "fc_by_search_terms.txt", ["../../data/stockx/20190609-193946/promising/best_prices.txt", "../../data/stockx/20190609-195140/promising/best_prices.txt"])
    matches = match_items(fc_prices, sx_prices)
    margins = find_margin(matches)

    crossing_margin_rate_sorted_items = sorted(margins.items(), key=lambda kv: kv[1]['crossing_margin_rate'], reverse=True)
    pp.pprint(crossing_margin_rate_sorted_items)
    with open("crossing_margin_sorted.txt", "w") as wfile:
        wfile.write(pp.pformat(crossing_margin_rate_sorted_items))

    regular_size_crossing_margin_rate_sorted_items = []
    for item in crossing_margin_rate_sorted_items:
        shoe_size = float(item[1]['shoe_size'])
        if shoe_size == 9.0 or shoe_size == 8.5 or shoe_size == 9.5:
            regular_size_crossing_margin_rate_sorted_items.append(item[1])

    pp.pprint(regular_size_crossing_margin_rate_sorted_items)
    with open("regular_size_crossing_margin_sorted.txt", "w") as wfile:
        wfile.write(pp.pformat(regular_size_crossing_margin_rate_sorted_items))

