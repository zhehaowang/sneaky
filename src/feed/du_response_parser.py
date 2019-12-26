#!/usr/bin/env python3

import re
import json
import datetime
import hashlib

from sizer import Sizer

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
    def __init__(self, size, price, time, id=None):
        self.size = size
        self.price = price
        self.time = time
        self.id = id

    def __str__(self):
        return str(self.size) + " " + str(self.price) + " " + self.time

class DuItem():
    def __init__(self, product_id, title, sold_num):
        self.product_id = DuParser.sanitize_style_id(product_id)
        self.title = str(title)
        self.sold_num = int(sold_num)
        self.style_id = None
        self.size_prices = {}
        self.gender = None
    
    @staticmethod
    def infer_gender(title):
        # TODO: smarter women handling
        lt = title.lower()
        if "nike" in lt or "jordan" in lt or "airforce" in lt:
            if "女" in lt:
                return "eu-nike-women"
            else:
                return "eu-nike-men"
        elif "adidas" in lt or "yeezy" in lt:
            if "女" in lt:
                return "eu-adidas-women"
            else:
                return "eu-adidas-men"
        else:
            raise RuntimeError("failed to infer gender from {}".format(title))

    def populate_details(self, style_id, size_prices, release_date):
        self.style_id = str(style_id)
        self.size_prices = size_prices
        self.release_date = str(release_date)
        self.gender = self.infer_gender(self.title)
        return

    def get_static_info(self):
        return {
            "style_id": self.style_id,
            "product_id": self.product_id,
            "title": self.title,
            "release_date": self.release_date,
            "gender": self.gender
        }

    def __str__(self):
        if self.style_id:
            return "Style ID: {}; Title: {}; Du Sold Num: {}".format(
                self.style_id, self.title, self.sold_num)
        else:
            return "Title: {}; Du Sold Num: {}".format(self.title, self.sold_num)

class DuParser():
    def __init__(self, sizer):
        self.sizer = sizer
        return
    
    @staticmethod
    def sanitize_size(sizer, size_str, in_code, out_code='us'):
        sanitized_size_str = size_str.strip().strip('码').upper()
        if re.match("^[0-9]+$", sanitized_size_str):
            # size like 36 becomes 36.0
            sanitized_size_str += ".0"
        elif re.match("^[0-9]+Y$", sanitized_size_str):
            # size like 5Y becomes 5.0Y
            sanitized_size_str = sanitized_size_str.strip("Y") + ".0Y"
        elif re.match("^[0-9]+\.[05]Y?$", sanitized_size_str):
            # size like 36.5 or 5.0Y is fine
            pass
        else:
            raise RuntimeError("unrecognized size {}".format(size_str))
        return sizer.get_shoe_size(sanitized_size_str, in_code, out_code)

    @staticmethod
    def sanitize_time(time_str):
        return timestr_to_epoch(time_str)

    @staticmethod
    def sanitize_price(price_str):
        return float(price_str)

    @staticmethod
    def sanitize_style_id(style_id):
        return str(style_id).strip().upper()

    @staticmethod
    def get_sale_id(sales_list_obj):
        m = hashlib.md5()
        m.update(str(sales_list_obj['price']).encode('utf-8'))
        m.update(str(sales_list_obj['sizeDesc']).encode('utf-8'))
        m.update(str(sales_list_obj['userName']).encode('utf-8'))
        return m.hexdigest()

    def parse_recent_sales(self, in_text, in_code):
        o = json.loads(in_text)
        if o["status"] != 200:
            raise RuntimeError("parse_recent_sales aborted response status {}".format(o["status"]))
        data = o["data"]
        sales_list = data["list"]
        result = []
        for s in sales_list:
            result.append(
                SaleRecord(
                    self.sanitize_size(self.sizer, s['sizeDesc'], in_code),
                    self.sanitize_price(s['price']),
                    self.sanitize_time(s['formatTime']),
                    id=self.get_sale_id(s)))
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

    def parse_size_list(self, size_list, in_code):
        result = {}
        for s in size_list:
            bid = s["buyerBiddingItem"]
            bid_price = self.sanitize_price(bid["price"])
            size = self.sanitize_size(self.sizer, s["formatSize"], in_code)
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
        gender = DuItem.infer_gender(detail["title"])
        size_list = self.parse_size_list(data["sizeList"], gender)
        return style_id, size_list, release_date
