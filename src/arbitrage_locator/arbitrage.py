#!/usr/bin/env python3

import os
import re
import sys
import json
import csv
import pytz
import math

import pprint
import datetime
import requests

import argparse

import smtplib
from email.mime.text import MIMEText

pp = pprint.PrettyPrinter()

fx_rates = {}

def get_spot_fx(in_amount, in_curr, out_curr):
    if not (in_curr, out_curr) in fx_rates:
        r = requests.get(
            'http://rate-exchange-1.appspot.com/currency?from={}&to={}'.format(
                in_curr, out_curr))
        fx_rates[(in_curr, out_curr)] = r.json()["rate"]
    return in_amount * fx_rates[(in_curr, out_curr)]

def get_brand(name):
    nike_names = ['nike', 'jordan']
    adidas_names = ['yeezy', 'adidas']

    for n in nike_names:
        if n in name.lower():
            return 'nike'
    for n in adidas_names:
        if n in name.lower():
            return 'adidas'
    return None

# agree
# http://www.shoesizes.co/
# https://www.quora.com/What-is-the-difference-between-Chinese-and-U-S-shoe-sizes
# 
# disagree:
# https://tbfocus.com/size-conversion-cn-uk-us-eu-fr-intls
# 
# adopted: separate nike and adidas charts
def get_shoe_size(in_size, in_code, out_code):
    us_chinese_men_size_mapping = {
        3.5:   35.0,
        4.0:   36.0,
        4.5:   37.0,
        5.0:   38.0,
        5.5:   39.0,
        6.0:   39.5,
        6.5:   40.0,
        7.0:   41.0,
        7.5:   41.5,
        8.0:   42.0,
        8.5:   43.0,
        9.0:   43.5,
        9.5:   44.0,
        10.0:  44.5,
        10.5:  45.0,
        11.0:  46.0,
        11.5:  46.5,
        12.0:  47.0,
        12.5:  47.5
    }
    chinese_us_men_size_mapping = {}

    adidas_eu_us_men_size_mapping = {
        36.0:  4.0,
        36.5:  4.5,
        37.0:  5.0,
        38.0:  5.5,
        38.5:  6.0,
        39.0:  6.5,
        40.0:  7.0,
        40.5:  7.5,
        41.0:  8.0,
        42.0:  8.5,
        42.5:  9.0,
        43.0:  9.5,
        44.0:  10.0,
        44.5:  10.5,
        45.0:  11.0,
        46.0:  11.5,
        46.5:  12.0,
        47.0:  12.5,
        48.0:  13.0,
        48.5:  13.5,
        49.0:  14.0
    }
    adidas_us_eu_men_size_mapping = {}

    nike_eu_us_men_size_mapping = {
        35.5:  3.5,
        36.0:  4.0,
        36.5:  4.5,
        37.5:  5.0,
        38.0:  5.5,
        38.5:  6.0,
        39.0:  6.5,
        40.0:  7.0,
        40.5:  7.5,
        41.0:  8.0,
        42.0:  8.5,
        42.5:  9.0,
        43.0:  9.5,
        44.0:  10.0,
        44.5:  10.5,
        45.0:  11.0,
        45.5:  11.5,
        46.0:  12.0,
        46.5:  12.5,
        47.5:  13.0,
        48.0:  13.5,
        48.5:  14.0,
    }
    nike_us_eu_men_size_mapping = {}

    if not chinese_us_men_size_mapping:
        for key in us_chinese_men_size_mapping:
            chinese_us_men_size_mapping[us_chinese_men_size_mapping[key]] = key
    if not adidas_us_eu_men_size_mapping:
        for key in adidas_eu_us_men_size_mapping:
            adidas_us_eu_men_size_mapping[adidas_eu_us_men_size_mapping[key]] = key
    if not nike_us_eu_men_size_mapping:
        for key in nike_eu_us_men_size_mapping:
            nike_us_eu_men_size_mapping[nike_eu_us_men_size_mapping[key]] = key

    try:
        if in_code == out_code:
            return in_size
        elif in_code == 'eu-adidas-men':
            if out_code == 'us':
                return adidas_eu_us_men_size_mapping[in_size]
        elif in_code == 'eu-nike-men':
            if out_code == 'us':
                return nike_eu_us_men_size_mapping[in_size]
    except KeyError as e:
        print('failed to get shoe_size {} to {} size {}'.format(in_code, out_code, in_size))
    return None

def sanitize_style_id(key):
    return key.lower().replace('-', '').replace(' ', '')

def sanitize_size(size):
    return size.strip('.0')

def read_files(fc_file, stockx_file, du_file):
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
    du_prices = {}

    with open(fc_file, "r") as rfile:
        fc_prices_presantize = json.loads(rfile.read())

    for key in fc_prices_presantize:
        fc_prices[sanitize_style_id(key)] = fc_prices_presantize[key]

    with open(du_file, "r") as rfile:
        du_prices_presanitize = json.loads(rfile.read())

    for key in du_prices_presanitize:
        du_prices[sanitize_style_id(key)] = du_prices_presanitize[key]

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
                    style_id_san = sanitize_style_id(style_id)
                    if style_id_san in sx_prices:
                        sx_prices[style_id_san][shoe_size] = {
                            "name": name,
                            "url": url,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "sales_last_72": sx_volume_last_72,
                            "style_id_ori": style_id
                        }
                    else:
                        sx_prices[style_id_san] = {shoe_size: {
                            "name": name,
                            "url": url,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "sales_last_72": sx_volume_last_72,
                            "style_id_ori": style_id
                        }}
            else:
                print("{} (url: {}) has None style ID".format(name, url))

    return fc_prices, sx_prices, du_prices

def match_items(fc_prices, sx_prices, du_prices):
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

    source_key_map = ["fc", "sx", "du"]
    idx = 0

    for source in [fc_prices, sx_prices, du_prices]:
        for style_id in source:
            for size in source[style_id]:
                # special size handling for du
                item = source[style_id][size]
                if idx == 2:
                    sanitized_size = None
                    try:
                        brand = get_brand(source[style_id][size]['title'])
                        if not brand:
                            print('failed to get brand from {}'.format(
                                source[style_id][size]['title']))
                            break
                        sanitized_size = sanitize_size(str(get_shoe_size(
                            float(size),
                            in_code="eu-{}-men".format(brand),
                            out_code="us")))
                    except ValueError as e:
                        continue
                    if not sanitized_size or sanitized_size.lower() == "none":
                        print('failed to find matching size for {}'.format(source[style_id][size]))
                        continue

                    item['size_us'] = sanitized_size
                else:
                    sanitized_size = sanitize_size(size)

                if style_id not in matches:
                    matches[style_id] = {
                        sanitized_size: {
                            source_key_map[idx]: item
                        }}
                elif sanitized_size not in matches[style_id]:
                    matches[style_id][sanitized_size] = {
                        source_key_map[idx]: item
                    }
                else:
                    matches[style_id][sanitized_size][source_key_map[idx]] = item
        idx += 1

    for key in matches:
        for size in matches[key]:
            if len(matches[key][size].keys()) > 1:
                total_matches += 1

    pp.pprint("found {} (model, size) listed on at least two sites".format(
        total_matches))
    return matches, total_matches

def find_margin(matches):
    """Given the combined prices from sx and fc produce a dict of items with
    crossing margin computed.

    @param matched dict
        {"style_id": {"8":
            {"fc": {...},
             "sx": {...}}}}
    @return {"style-id size": {"crossing_margin": xxx, 
                               "sx_xxx": ...,
                               "fc_yyy": ...}}
    """
    # us to china 
    # du_shipping_fee = 20

    # china to us
    # du_batch_size = 3
    
    # du_batch_fee = 106
    # 90 - 5kg + 16 / kg

    # pp.pprint(matches)

    du_shipping_fee = 16
    du_commission_rate = 0.095

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

            if len(item.keys()) < 2:
                continue

            name = ''
            release_date = ''
            if 'sx' in item:
                name = item['sx']['name']
            elif 'fc' in item:
                name = item['fc']['name']
                release_date = item['fc']['release_date']
            elif 'du' in item:
                name = item['du']['title']

            match_item = {
                'style_id': style_id,
                'name': name,
                'shoe_size': size,
                'release_date': release_date
            }

            if 'fc' in item:
                sell_px = float(item['fc']['px'])
                if 'sell_px_highest' in item['fc']:
                    sell_px = min(sell_px, float(item['fc']['sell_px_highest']))
                if 'sell_px_market' in item['fc']:
                    sell_px = min(sell_px, float(item['fc']['sell_px_market']))
                sell_link = ''
                if 'sell_id' in item['fc']:
                    sell_link = 'https://sell.flightclub.com/products/{}'.format(item['fc']['sell_id'])

                fc_url_with_size = item['fc']['url'] + '?size=' + size
                match_item['fc_list_px'] = float(item['fc']['px'])
                match_item['fc_sell_px'] = sell_px
                match_item['fc_sell_url'] = sell_link
                match_item['fc_url'] = fc_url_with_size

            if 'sx' in item:
                match_item['sx_best_bid'] = item['sx']['best_bid']
                match_item['sx_best_ask'] = item['sx']['best_ask']
                match_item['sx_volume_last_72'] = item['sx']['sales_last_72']
                match_item['sx_url'] = item['sx']['url']
                match_item['sx_transactions'] = item['sx']['sx_transactions'] if 'sx_transactions' in item['sx'] else []

            if 'du' in item:
                match_item['du_price_usd'] = get_spot_fx(
                    item['du']['px'], 'CNY', 'USD')
                match_item['du_url'] = item['du']['product_id_url']
                match_item['du_size_chinese'] = item['du']['size']

            crossing_margin = 0.0
            crossing_margin_rate = 0.0
            adding_margin = 0.0
            adding_margin_rate = 0.0

            # sx and fc
            if 'sx' in item and item['sx']['best_ask'] and item['sx']['best_bid']:
                # if int(item['sx']['sales_last_72']) > sx_threshold:
                if 'fc' in item:
                    sell_px = match_item['fc_sell_px']

                    crossing_margin = sell_px * (1 - fc_commission_rate) - float(item['sx']['best_ask']) - sx_bid_commission
                    crossing_margin_rate = crossing_margin / float(item['sx']['best_ask'])

                    if item['sx']['best_bid'] > 0:
                        adding_margin = sell_px * (1 - fc_commission_rate) - float(item['sx']['best_bid']) - (cut_in_tick + sx_bid_commission)
                        adding_margin_rate = adding_margin / (float(item['sx']['best_bid']) + cut_in_tick)
                    else:
                        adding_margin = 0
                        adding_margin_rate = 0

                    match_item['action'] = 'sx->fc'
                
                if 'du' in item:
                    sell_px = match_item['du_price_usd']

                    val = sell_px * (1 - du_commission_rate) - float(item['sx']['best_ask']) - sx_bid_commission - du_shipping_fee
                    if val > crossing_margin:
                        crossing_margin = val
                        crossing_margin_rate = crossing_margin / float(item['sx']['best_ask'])

                        if item['sx']['best_bid'] > 0:
                            adding_margin = sell_px * (1 - du_commission_rate) - float(item['sx']['best_bid']) - (cut_in_tick + sx_bid_commission + du_shipping_fee)
                            adding_margin_rate = adding_margin / (float(item['sx']['best_bid']) + cut_in_tick)
                        else:
                            adding_margin = 0
                            adding_margin_rate = 0

                        match_item['action'] = 'sx->du'

                match_item['crossing_margin'] = crossing_margin
                match_item['crossing_margin_rate'] = crossing_margin_rate
                match_item['adding_margin'] = adding_margin
                match_item['adding_margin_rate'] = adding_margin_rate

                margins[style_id + ' ' + size] = match_item

    return margins

def annotate_transaction_history(sx_prices, data_prefix="../../data/stockx/"):
    """For all (style id, size) in stockx prices, find if a matching transaction
    file exists in given folder.
    If so, modify sx_prices object with transactions attached to each
    (style id, size).

    @param sx_prices modified in place
    """
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

    return

def annotate_score(margins, score_mode):
    """For all (style id, size) in stockx prices, calculate a score for the item
    using the given score_mode, and modify each (style id, size) with score of
    the item attached.

    @param margins modified in place
    """
    for item in margins:
        if score_mode == 'naive':
            score, volume = score_crossing_margin_rate(margins[item])
        elif score_mode == 'multi':
            score, volume = score_margin_single_entity_transactions_size(margins[item])
        margins[item]['score'] = score
        margins[item]['volume'] = volume
    return

def score_crossing_margin_rate(item):
    return item['crossing_margin_rate'], 0

def score_margin_single_entity_transactions_size(item):
    """An item with a high crossing margin rate, low single entity price, high
    volume and close to norm size scores better.

    We can't really accurately account for transaction rate as some data is 
    still being scraped. when we don't have such data we use the this table
    as approximation.
    """
    # TODO: move transaction rate calc to annotation step?

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
            item['volume_approximated'] = True
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

    return item['crossing_margin_rate'] * math.sqrt(transaction_rate) * price_discount, transaction_rate

def generate_html_report(score_sorted_item, limit, **run_info):
    crossing_margin_cutoff_rate = 0.01
    if 'crossing_margin_cutoff_rate' in run_info:
        crossing_margin_cutoff_rate = run_info['crossing_margin_cutoff_rate']
    crossing_margin_cutoff_value = 10
    if 'crossing_margin_cutoff_value' in run_info:
        crossing_margin_cutoff_value = run_info['crossing_margin_cutoff_value']

    text = ("<html><head></head><body>"
        "Hi,<br><p>Please see below for a list of candidate shoes.</p>")

    text += ("<table>"
                "<tr>"
                    "<th>Name</th>"
                    "<th>Release</th>"
                    "<th>Size</th>"
                    "<th>StockX</th>"
                    "<th>Du</th>"
                    "<th>FlightClub: Listed Sell Price</th>"
                    "<th>FlightClub: Sell Market Price</th>"
                    "<th>Action</th>"
                    "<th>Crossing Margin</th>"
                    "<th>Crossing Margin Rate</th>"
                    "<th>StockX Volume / Day</th>"
                    "<th>Score</th>"
                    "<th>Style ID</th>"
                "</tr>")

    report_cnt = 0
    for key in score_sorted_item:
        shoe = key[1]
        if shoe["crossing_margin_rate"] > crossing_margin_cutoff_rate and \
           shoe["crossing_margin"] > crossing_margin_cutoff_value and \
           (not limit or report_cnt < limit):
            text += ("<tr>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{}</td>"
                        "<td>{:.2f}</td>"
                        "<td>{}</td>"
                     "</tr>").format(
                        shoe['name'], shoe['release_date'], shoe['shoe_size'],
                        "<a href=\"{}\">{:.2f}</a>".format(
                            shoe['sx_url'], float(shoe['sx_best_ask'])),
                        "N/A" if not "du_price_usd" in shoe else "<a href=\"{}\">{:.2f}</a> ({})".format(
                            shoe['du_url'], float(shoe['du_price_usd']), shoe['du_size_chinese']),
                        "N/A" if not "fc_list_px" in shoe else "<a href=\"{}\">{:.2f}</a>".format(
                            shoe['fc_url'], float(shoe['fc_list_px'])),
                        "N/A" if not 'fc_sell_url' in shoe else "<a href=\"{}\">{:.2f}</a>".format(
                            shoe['fc_sell_url'], shoe['fc_sell_px']),
                        shoe["action"], shoe['crossing_margin'], shoe['crossing_margin_rate'],
                        "{:.2f}{}".format(shoe['volume'], ' (approx)' if 'volume_approximated' in shoe else ''),
                        shoe['score'], shoe['style_id'])
            report_cnt += 1

    text += "<table><br><br>{}".format(json.dumps(run_info, indent=4, sort_keys=True))
    text += "<br><br>Thanks,<br>Sneaky Bot</body></html>"

    return text if report_cnt > 0 else "But didn't find anything :("

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    fc_file = "../../data/flightclub/flightclub.20190623.txt"
    sx_file = "../../data/stockx/20190622-095347/promising/best_prices.txt"
    du_file = "../../data/du/du.20190623.txt"
    sx_transactions_folder = "../../data/stockx/20190622-095347/"

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

    fc_prices, sx_prices, du_prices = read_files(fc_file, sx_file, du_file)
    annotate_transaction_history(sx_prices, sx_transactions_folder)
    matches, total_matches = match_items(fc_prices, sx_prices, du_prices)

    margins = find_margin(matches)
    score_mode = args.score_mode if args.score_mode else 'multi'
    annotate_score(margins, score_mode)

    score_sorted_item = sorted(
        margins.items(), key=lambda kv: kv[1]['score'], reverse=True)
    outfile = args.out if args.out else "score_sorted.{}.txt".format(runtime)
    with open(outfile, "w") as wfile:
        wfile.write(pp.pformat(score_sorted_item))

    if args.emails:
        report = generate_html_report(
            score_sorted_item, args.limit, runtime=runtime, score=score_mode,
            fc_file=fc_file, sx_file=sx_file, du_file=du_file,
            sx_transactions_folder=sx_transactions_folder,
            total_model_size_matches=total_matches,
            crossing_margin_cutoff_rate=0.05,
            crossing_margin_cutoff_value=20)

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


