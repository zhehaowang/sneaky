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
        data = json.loads(in_text)["data"]
        sales_list = data["list"]
        records = []
        for s in sales_list:
            records.append(
                SaleRecord(
                    self.sanitize_size(s['sizeDesc']),
                    self.sanitize_price(s['price']),
                    self.sanitize_time(s['formatTime'])))
        return data["lastId"], records
