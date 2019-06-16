#!/usr/bin/env python3

import os
import re
import sys
import json
import csv
import pytz

import pprint
import datetime

import argparse

import smtplib
from email.mime.text import MIMEText

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
            shoe_size = sanitize_size(row[3])
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
                            sx_size: {
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
    # us to china 
    # du_shipping_fee = 20
    # du_commission_rate = 0.095

    # china to us
    # du_batch_size = 3
    
    # du_batch_fee = 106
    # 90 - 5kg + 16 / kg

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
                        'style_id': style_id,
                        'name': item['sx']['name'],
                        'shoe_size': sanitize_size(size),

                        'fc_px': float(item['fc']['px'].replace(',', '')),
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

def annotate_score(margins, score_mode):
    for item in margins:
        if score_mode == 'naive':
            score, volume = score_crossing_margin_rate(margins[item])
        elif score_mode == 'multi':
            score, volume = score_margin_single_entity_transactions_size(margins[item])
        margins[item]['score'] = score
        margins[item]['volume'] = volume
    return margins

def score_crossing_margin_rate(item):
    return item['crossing_margin_rate'], 0

def score_margin_single_entity_transactions_size(item):
    # an item with a high crossing margin rate, low single entity price, high
    # volume and close to norm size scores better

    # we can't really accurately account for transaction rate as some data is 
    # still being scraped. when we don't have such data we use the this table
    # as approximation

    size_discount_multiplier = {
        '3.5':  0.40,
        '4':    0.50,
        '4.5':  0.60,
        '5':    0.70,
        '5.5':  0.75,
        '6':    0.80,
        '6.5':  0.85,
        '7':    0.90,
        '7.5':  0.95,
        '8':    0.98,
        '8.5':  1.00,
        '9':    1.00,
        '9.5':  1.00,
        '10':   1.00,
        '10.5': 1.00,
        '11':   1.00,
        '11.5': 0.98,
        '12':   0.95,
        '12.5': 0.90,
        '13':   0.85,
        '13.5': 0.80,
        '14':   0.75,
        '14.5': 0.70,
        '15':   0.70,
        '16':   0.60,
        '17':   0.50,
        '18':   0.40
    }

    if len(item['sx_transactions']) > 0:
        duration = datetime.datetime.now(
            pytz.timezone('America/New_York')) - datetime.datetime.strptime(
            item['sx_transactions'][-1]['time'], "%Y-%m-%dT%H:%M:%S%z")
        transaction_rate = len(item['sx_transactions']) * 3600 * 24 // duration.total_seconds()
    else:
        if item['shoe_size'] in size_discount_multiplier:
            transaction_rate = 0.2 * size_discount_multiplier[item['shoe_size']]
        else:
            print('unknown size {}'.format(item['shoe_size']))
            transaction_rate = 0

    price_discount = 1
    if item['sx_best_ask'] > 1000:
        price_discount = 0.3
    elif item['sx_best_ask'] > 500:
        price_discount = 0.6
    elif item['sx_best_ask'] > 300:
        price_discount = 0.9

    return item['crossing_margin_rate'] * transaction_rate * price_discount, transaction_rate

def generate_html_report(score_sorted_item, limit, **run_info):
    text = ("<html><head></head><body>"
        "Hi,<br><p>Please see below for a list of candidate shoes.</p>")

    text += ("<table>"
                "<tr>"
                    "<th>Name</th>"
                    "<th>Size</th>"
                    "<th>StockX</th>"
                    "<th>FlightClub</th>"
                    "<th>Crossing Margin</th>"
                    "<th>Crossing Margin Rate</th>"
                    "<th>StockX Transaction Rate</th>"
                    "<th>Score</th>"
                    "<th>Style ID</th>"
                "</tr>")

    report_cnt = 0
    for key in score_sorted_item:
        shoe = key[1]
        if shoe["crossing_margin_rate"] > 0 and (not limit or report_cnt < limit):
            text += ("<tr>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{}</td>"
                     "</tr>").format(shoe['name'], shoe['shoe_size'],
                        "<a href=\"{}\">{:.2f}</a>".format(
                            shoe['sx_url'], float(shoe['sx_best_ask'])),
                        "<a href=\"{}\">{:.2f}</a>".format(
                            shoe['fc_url'], float(shoe['fc_px'])),
                        shoe['crossing_margin'], shoe['crossing_margin_rate'],
                        shoe['volume'], shoe['score'], shoe['style_id'])
            report_cnt += 1

    text += "<table><br><br>{}".format(pp.pformat(run_info))
    text += "<br><br>Thanks,<br>Sneaky Bot</body></html>"

    return text if report_cnt > 0 else "But didn't find anything :("

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    fc_file = "flightclub.20190614.txt"
    sx_file = "best_prices.20190614-230824.txt"
    sx_transactions_folder = "../../data/stockx/20190615-145954/"

    parser.add_argument(
        "--score_mode",
        help=("[multi|naive] with what criteria we decide how much we want to "
             " buy this pair shoes"))
    parser.add_argument(
        "--emails",
        help="comma separated list of email addresses to send report")
    parser.add_argument(
        "--limit",
        help="max number of items to send in one email")
    parser.add_argument(
        "--out",
        help="output file to write to")
    args = parser.parse_args()

    runtime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    fc_prices, sx_prices = read_files(fc_file, sx_file)
    sx_prices = annotate_transaction_history(sx_prices, sx_transactions_folder)
    matches = match_items(fc_prices, sx_prices)

    margins = find_margin(matches)
    score_mode = args.score_mode if args.score_mode else 'multi'
    margins = annotate_score(margins, score_mode)

    score_sorted_item = sorted(
        margins.items(), key=lambda kv: kv[1]['score'], reverse=True)
    outfile = args.out if args.out else "score_sorted.{}.txt".format(runtime)
    with open(outfile, "w") as wfile:
        wfile.write(pp.pformat(score_sorted_item))

    if args.emails:
        report = generate_html_report(
            score_sorted_item, args.limit, runtime=runtime, score=score_mode,
            fc_file=fc_file, sx_file=sx_file,
            sx_transactions_folder=sx_transactions_folder)

        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login('testname.zhehao@gmail.com', 'test@2019')

        msg = MIMEText(report, 'html')
        msg['Subject'] = 'Check out these shoes %s' % runtime
        msg['From'] = 'testname.zhehao@gmail.com'
        msg['To'] = args.emails

        # Send the message via our own SMTP server.
        server.send_message(msg)
        server.quit()

    # "regular sized" shoes usually have low profit margin. we should revisit
    # this from time to time

    # regular_size_crossing_margin_rate_sorted_items = []
    # for item in score_sorted_item:
    #     shoe_size = float(item[1]['shoe_size'])
    #     if shoe_size == 9.0 or shoe_size == 8.5 or shoe_size == 9.5:
    #         regular_size_crossing_margin_rate_sorted_items.append(item[1])

    # with open("regular_size_crossing_margin_sorted.{}.txt".format(runtime), "w") as wfile:
    #     wfile.write(pp.pformat(regular_size_crossing_margin_rate_sorted_items))


