# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals, FormRequest
from scrapy.xlib.pydispatch import dispatcher

import json
import datetime
import os
import hashlib
import pprint
import urllib
import execjs
import re

pp = pprint.PrettyPrinter()

class DuSpider(scrapy.Spider):
    name = 'du'
    allowed_domains = ['m.poizon.com']
    base_url = 'https://m.poizon.com'
    token_file = './du_token.txt'

    def start_requests(self):
        self.timetamp = '1561177360584' # '1561250002466'
        self.headers = {
            # common http fixed
            'content-type': 'application/x-www-form-urlencoded; charset=utf-8',
            'accept': '*/*',
            'accept-language': 'en-US;q=1.0, zh-Hans-US;q=0.9, fr-FR;q=0.8',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'user-agent': 'duapp/4.2.1 (com.siwuai.duapp; build:4.2.1; iOS 11.4.0) Alamofire/4.8.2',

            # du http fixed
            'mode': '0',
            'platform': 'iPhone',
            'v': '4.2.1',
            'uuid': '1C6BD899-8A6A-4E9A-BCA8-9E6BA149D7A7',

            # may need to change
            'timestamp': self.timetamp
        }

        self.du_token = None
        self.cookie = None
        self.js_ctx = None
        self.prices = {}
        self.max_pages = 2

        self.max_history_page = 3
        self.history_queries = {}

        if os.path.isfile(DuSpider.token_file):
            with open(DuSpider.token_file, 'r') as rfile:
                token_obj = json.loads(rfile.read())
                self.du_token = token_obj['token']
                self.cookie = token_obj['cookie']

        # if no valid token, log in first
        if not self.du_token or not self.cookie:
            yield self.get_login_request()
        else:
            for page_id in range(1, self.max_pages):
                yield self.get_list_request(page_id)

    def get_login_request(self):
        login_form = {
            # fixed
            'accessToken': '',
            'code': '',
            'expire': '0',
            'mode': '0',
            'openId': '',
            'sourcePage': '',
            'platform': 'iPhone',
            'refreshToken': '',
            'token': 'JLIjsdLjfsdII%3D%7CMTQxODg3MDczNA%3D%3D%7C07aaal32795abdeff41cc9633329932195',
            'shumeiid': '201906191136236fded65cbbdfa090f71e09578a0feac101227030b29a0ef5',
            'v': '4.2.1',

            # per user fixed
            'countryCode': '1',
            'userName': '4243338516',
            'password': 'c00d0cf35e1bf706933662476b7c8e4c',
            'uuid': '1C6BD899-8A6A-4E9A-BCA8-9E6BA149D7A7',
            'type': 'pwd',
            
            # may need to change
            'timestamp': self.timetamp,
            'sign': 'ee2e8b977be6a8f8220ddd2d002ad9cb'
        }

        login_url = DuSpider.base_url + '/users/unionLogin'
        return FormRequest(
            login_url,
            headers=self.headers,
            formdata=login_form,
            callback=self.parse_login)

    def parse_login(self, response):
        """
        we can log in with this, but later steps doesn't really require logging
        in
        """
        if response.status != 200:
            print("login http request failed: {}".format(response.status))
        else:
            try:
                resobj = json.loads(response.body_as_unicode())
                if 'status' in resobj and resobj['status'] != 200:
                    print("app login failed: {}".format(resobj['status']))
                else:
                    self.du_token = resobj['data']['loginInfo']['loginToken']
                    self.headers['logintoken'] = self.du_token
                    
                    set_cookies = response.headers.getlist('Set-Cookie')
                    print(set_cookies)
                    cookies = set_cookies[0].decode('utf-8').split(';')
                    self.cookie = {}
                    for cookie in cookies:
                        kv = cookie.strip().split('=')
                        self.cookie[kv[0]] = kv[1]

                    with open(DuSpider.token_file, 'w') as wfile:
                        wfile.write(json.dumps({
                            "token": self.du_token,
                            "cookie": self.cookie
                        }))
                        print(
                            "du token written.\ntoken {}\ncookie {}.".format(
                                self.du_token, self.cookie))
                
                for page_id in range(1, self.max_pages):
                        yield self.get_list_request(page_id)
            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print("unexpected key {}".format(e))

    def get_url(self, target, params):
        if not self.js_ctx:
            with open('sign.js', 'r', encoding='utf-8')as f:
                all_ = f.read()
                self.js_ctx = execjs.compile(all_)

        sign_query = ''
        url_get = ''
        for key in sorted(params.keys()):
            sign_query += key + params[key]
            url_get += key + '=' + params[key] + '&'

        sign_query += '048a9c4943398714b356a696503d2d36'
        sign = self.js_ctx.call('getSign', sign_query)

        url = 'https://m.poizon.com/mapi/' + target + '?{}sign={}'.format(url_get, sign)
        return url

    def get_list_request(self, page_id):
        params = {
            "size": "[]",
            "title": "",
            "typeId": "0",
            "catId": "0",
            "unionId": "0",
            "sortType": "0",
            "sortMode": "1",
            "page": str(page_id),
            "limit": "20"
        }
        url = self.get_url('search/list', params)
        return Request(
            url, headers=self.headers, callback=self.parse_list)

    def parse_list(self, response):
        if response.status != 200:
            print('http get_list request failed')
        else:
            try:
                resobj = json.loads(response.body_as_unicode())
                if resobj['status'] != 200:
                    print('app get_list failed: {}', response.body_as_unicode())
                else:
                    product_list = resobj['data']['productList']
                    print('retrieved {} items'.format(len(product_list)))
                    for product in product_list:
                        product_id = product['product']['productId']
                        params = {
                            'source': 'shareDetail',
                            'productId': str(product_id)
                        }
                        product_id_url = self.get_url('product/detail', params)
                        yield Request(
                            product_id_url,
                            callback=lambda r, product_id=product_id, url=product_id_url: self.parse_item(r, product_id, product_id_url))
            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print('unexpected parse_list response {}'.format(e))
        return

    def parse_item(self, response, product_id, product_id_url):
        if response.status != 200:
            print('http get_item request failed')
        else:
            try:
                resobj = json.loads(response.body_as_unicode())
                if resobj['status'] != 200:
                    print('app get_list failed: {}', response.body_as_unicode())
                else:
                    style_id = resobj['data']['item']['product']['articleNumber']
                    try:
                        color = resobj['data']['item']['product']['color']
                    except KeyError as e:
                        color = 'N/A'
                    items = resobj['data']['sizeList']
                    for item in items:
                        if isinstance(item['item'], (list,)):
                            # du doesn't have this size
                            continue

                        shoe_size = item['formatSize']
                        title = item['item']['productTitle']
                        px_cny = float(item['item']['price']) / 100
                        if style_id not in self.prices:
                            self.prices[style_id] = {}

                        self.prices[style_id][shoe_size] = {
                            'px': px_cny,
                            'title': title,
                            'size': shoe_size,
                            'du_id': product_id,
                            'product_id_url': product_id_url,
                            'color': color
                        }

                    yield self.get_last_sold_items(style_id, product_id)
            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print('unexpected parse_item response {}'.format(e))
        return

    def get_last_sold_items(self, style_id, product_id, last_id=None):
        params = {
            'limit': '20',
            'productId': str(product_id)
        }
        if last_id:
            params['lastId'] = last_id
        url = self.get_url('product/lastSoldList', params)
        return Request(url, callback=lambda r, style_id=style_id, product_id=product_id: self.parse_transactions(r, style_id, product_id))

    def timestr_to_epoch(self, timestr, timenow=None):
        time_now = timenow if timenow else datetime.datetime.now()
        
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
        
        print('failed to parse timestr {}'.format(timestr))

    def parse_transactions(self, response, style_id, product_id):
        if response.status != 200:
            print('http last_sold_list request failed')
        else:
            try:
                resobj = json.loads(response.body_as_unicode())
                if resobj['status'] != 200:
                    print('app last_sold_list request failed: {}', response.body_as_unicode())
                else:
                    last_id = resobj['data']['lastId']
                    transactions_list = resobj['data']['list']
                    for transaction in transactions_list:
                        size = transaction['item']['formatSize']
                        if style_id not in self.prices or size not in self.prices[style_id]:
                            print('cannot find item to attach transaction to: {} size {}'.format(style_id, size))
                            continue
                        transaction_time = self.timestr_to_epoch(transaction['formatTime'])
                        if 'transactions' not in self.prices[style_id][size]:
                            self.prices[style_id][size]['transactions'] = [{
                                'time': transaction_time
                            }]
                        else:
                            self.prices[style_id][size]['transactions'].append({
                                'time': transaction_time
                            })
                    if product_id not in self.history_queries:
                        self.history_queries[product_id] = 1
                    else:
                        self.history_queries[product_id] += 1
                    if self.history_queries[product_id] < self.max_history_page:
                        yield self.get_last_sold_items(style_id, product_id, last_id)
            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print('unexpected parse_transactions response {}'.format(e))
        return

    def closed(self, reason):
        """
        On graceful shutdown, record the
        1. consignment sell prices keyed by first style id then size
        2. website url, sell price keyed by first style id then size
        3. updated <style id, consignment sell id> map

        Don't Ctrl+C twice the application if we want this to be called.
        """
        with open("../../data/du/du.{}.txt".format(
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")), "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))

        return
