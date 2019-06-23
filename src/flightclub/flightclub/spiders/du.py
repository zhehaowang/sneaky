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
        self.max_pages = 400

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
        Top-level menu on homepage, filter links by known brands.
        Send request for each (brand, series), e.g.
        `https://www.flightclub.com/air-jordans/air-jordan-2`
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

    def get_sign(self, api_params):
        hash_map = {
            "uuid": self.headers["uuid"],
            "platform": self.headers["platform"],
            "v": self.headers["v"],
            "loginToken": self.du_token,
        }

        for k in api_params:
            hash_map[k] = api_params[k]

        hash_map = sorted(hash_map.items(), key=lambda x: x[0])

        result = ''
        for v in hash_map:
            result += v[0] + v[1]

        result += "重要参数用于接口sign加密。"

        m1 = hashlib.md5()
        m1.update(result.encode("GBK"))
        sign = m1.hexdigest()
        return sign

    def get_api_url(self, api_url, api_params):
        url = DuSpider.base_url
        url += api_url
        url += '?'
        for k in api_params:
            url += k + '=' + api_params[k] + '&'
        # 获取sign
        sign = self.get_sign(api_params)
        url += 'sign=' + sign
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
            "limit": "20",
        }
        url = self.get_api_url('/search/list', params)
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
                        yield self.get_details(product_id)
            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print('unexpected parse_list response {}'.format(e))
        return

    def get_details(self, product_id):
        params = {
            # fixed
            'lastId': '',
            'mode': '0',
            'platform': 'iPhone',
            'shumeiid': '201906191136236fded65cbbdfa090f71e09578a0feac101227030b29a0ef5',
            'token': urllib.parse.quote_plus('JLIjsdLjfsdII%3D%7CMTQxODg3MDczNA%3D%3D%7C07aaal32795abdeff41cc9633329932195'),
            'uuid': '1C6BD899-8A6A-4E9A-BCA8-9E6BA149D7A7',
            'v': '4.2.1',

            'productId': str(product_id),
            'isChest': '1',
            'loginToken': urllib.parse.quote_plus(self.du_token),

            # may need to change
            'timestamp': self.timetamp
        }
        url = self.get_api_url('/product/detail', params)
        get_details_head = dict(self.headers)
        get_details_head['token'] = 'JLIjsdLjfsdII%3D%7CMTQxODg3MDczNA%3D%3D%7C07aaal32795abdeff41cc9633329932195'
        get_details_head['logintoken'] = self.du_token
        get_details_head['shumeiid'] = '201906191136236fded65cbbdfa090f71e09578a0feac101227030b29a0ef5'
        if 'content-type' in get_details_head:
            del get_details_head['content-type']

        product_id_url = self.get_product_url(product_id)

        return Request(
            product_id_url,
            # cookies=self.cookie,
            # headers=get_details_head,
            callback=lambda r, product_id=product_id, url=product_id_url: self.parse_item(r, product_id, product_id_url))

    def get_product_url(self, product_id):
        if not self.js_ctx:
            with open('sign.js', 'r', encoding='utf-8')as f:
                all_ = f.read()
                self.js_ctx = execjs.compile(all_)

        sign = self.js_ctx.call('getSign', 'productId{}sourceshareDetail048a9c4943398714b356a696503d2d36'.format(product_id))
        product_url = 'https://m.poizon.com/mapi/product/detail?productId={}&source=shareDetail&sign={}'.format(product_id, sign)
        return product_url

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

            except json.JSONDecodeError as e:
                print(e)
                print("unable to decode {}".format(response.body_as_unicode()))
            except KeyError as e:
                print('unexpected parse_item response {}'.format(e))
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
            datetime.date.today().strftime("%Y%m%d")), "w") as wfile:
            wfile.write(json.dumps(self.prices, indent=4, sort_keys=True))

        return
