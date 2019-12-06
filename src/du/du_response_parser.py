#!/usr/bin/env python3

import re
import json
import datetime

def timestr_to_epoch(timestr, timenow=None):
    """
    helper function to convert last_transaction time format to epoch

    @param timestr  str the input Chinese string time offset from now
    @param timenow  datetime (optional) if specified use specified time as
        opposed to actual time now
    @return str iso8601 time string corresponding to the time of the input
    """
    time_now = timenow if timenow else datetime.datetime.now()

    if timestr == '刚刚':
        return time_now.isoformat()
    
    match = re.match(r'([0-9]+)分钟前', timestr)
    if match:
        minutes = int(match.group(1))
        return (time_now - datetime.timedelta(minutes=minutes)).isoformat()
    
    match = re.match(r'([0-9]+)小时前', timestr)
    if match:
        hours = int(match.group(1))
        return (time_now - datetime.timedelta(hours=hours)).isoformat()
    
    match = re.match(r'([0-9]+)天前', timestr)
    if match:
        days = int(match.group(1))
        return (time_now - datetime.timedelta(days=days)).isoformat()
    
    match = re.match(r'([0-9]+)月前', timestr)
    if match:
        months = int(match.group(1))
        return (time_now - datetime.timedelta(days=months * 30)).isoformat()

    match = re.match(r'([0-9]+)月([0-9]+)日', timestr)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        return time_now.replace(day=day, month=month).isoformat()
    
    raise RuntimeError('failed to parse timestr {}'.format(timestr))

class SaleRecord():
    def __init__(self, size, price, time):
        self.size = size
        self.price = price
        self.time = time

    def __str__(self):
        return str(self.size) + " " + str(self.price) + " " + self.time

class DuItem():
    def __init__(self, product_id, title, sold_num):
        self.product_id = product_id
        self.title = title
        self.sold_num = sold_num
        self.style_id = None
        self.size_prices = {}

    def populate_details(self, style_id, size_prices, release_date):
        self.style_id = style_id
        self.size_prices = size_prices
        self.release_date = release_date
        return

    def get_static_info(self):
        return {
            "style_id": self.style_id,
            "product_id": self.product_id,
            "title": self.title,
            "release_date": self.release_date
        }

    def __str__(self):
        if self.style_id:
            return "{} {} {} {} {}".format(
                self.style_id, self.product_id, self.title, self.sold_num, self.size_prices)
        else:
            return "{} {} {}".format(
                self.product_id, self.title, self.sold_num)

class DuParser():
    def __init__(self):
        return
    
    @staticmethod
    def sanitize_size(size_str):
        match = re.match("^([0-9.]+)[^0-9.]*", size_str)
        if not match:
            raise RuntimeError("failed to parse size {}".format(size_str))
        return match.group(1)

    @staticmethod
    def sanitize_time(time_str):
        return timestr_to_epoch(time_str)

    @staticmethod
    def sanitize_price(price_str):
        return float(price_str)

    def parse_recent_sales(self, in_text):
        o = json.loads(in_text)
        if o["status"] != 200:
            raise RuntimeError("parse_recent_sales aborted response status {}".format(o["status"]))
        data = o["data"]
        sales_list = data["list"]
        result = []
        for s in sales_list:
            result.append(
                SaleRecord(
                    self.sanitize_size(s['sizeDesc']),
                    self.sanitize_price(s['price']),
                    self.sanitize_time(s['formatTime'])))
        return data["lastId"], result

    def parse_search_results(self, in_text):
        o = json.loads(in_text)
        if o["status"] != 200:
            raise RuntimeError("parse_search_results aborted response status {}".format(o["status"]))
        data = o["data"]
        product_list = data["productList"]
        result = []
        for p in product_list:
            result.append(DuItem(p["productId"], p["title"], p["soldNum"]))
        return result

    def parse_size_list(self, size_list):
        result = {}
        for s in size_list:
            bid = s["buyerBiddingItem"]
            bid_price = bid["price"]
            size = s["formatSize"]
            result[size] = {
                "bid_price": bid_price
            }
        return result

    def parse_product_detail_response(self, in_text):
        o = json.loads(in_text)
        if o["status"] != 200:
            raise RuntimeError("parse_product_detail_response aborted response status {}".format(o["status"]))
        data = o["data"]
        detail = data["detail"]
        style_id = detail["articleNumber"]
        release_date = detail["sellDate"]
        size_list = self.parse_size_list(data["sizeList"])
        return style_id, size_list, release_date
