import datetime
import json
import requests
import time

from stockxsdk.item import StockxItem
from stockxsdk.order import StockxOrder
from stockxsdk.product import StockxProduct

def now_plus_thirty():
    return (datetime.datetime.now() + datetime.timedelta(30)).strftime('%Y-%m-%d')

def now():
    return datetime.datetime.now().strftime('%Y-%m-%d')

def parse_cookie_str(cookie_str):
    parts = cookie_str.split(';')
    res = {}
    for part in parts:
        if part:
            kv = part.split('=')
            res[kv[0].strip()] = kv[1].strip()
    return res

class Stockx():
    API_BASE = 'https://stockx.com/api'

    def __init__(self):
        self.customer_id = None
        self.headers = None
        self.cookies = parse_cookie_str("__cfduid=d872b61c169ed04ad1c8fc249f8d7c3141559356547; _ga=GA1.2.144777368.1559356549; cto_lwid=9de93bee-bd8b-4507-8e21-795b787f61a9; _gcl_au=1.1.1951555545.1559356550; _tl_duuid=069a06ef-baee-4032-a7f1-2171bbd61b2d; tracker_device=51682130-9b63-414e-be28-25a499a56402; IR_gbd=stockx.com; ajs_group_id=null; _fbp=fb.1.1559356553059.129148643; rskxRunCookie=0; rCookie=7305g4oqqe449qv5wkc089; _pxhd=d844d67f707bc84ebb56a18e99c91b32e871953686b336a39217548c2419eaa5:04c25671-8417-11e9-b057-edcb5fe9ed72; _scid=d8f68103-065d-4005-8b2e-4900caf6d42c; stockx_bid_ask_spread_seen=true; stockx_multi_edit_seen=true; show_bid_ask_spread=false; show_below_retail=true; stockx_seen_ask_new_info=true; _gac_UA-67038415-1=1.1560037346.CjwKEAjwue3nBRCCyrqY0c7bw2wSJACSlmGZilf6CAcsMxFJm4ZJY59NWo8_11ZFC6RBA3iad0wFTxoC_GDw_wcB; _gcl_aw=GCL.1560037347.CjwKEAjwue3nBRCCyrqY0c7bw2wSJACSlmGZilf6CAcsMxFJm4ZJY59NWo8_11ZFC6RBA3iad0wFTxoC_GDw_wcB; _gid=GA1.2.1923016505.1560479845; stockx_learn_more_dismiss=true; _sctr=1|1560398400000; _pxvid=04c25671-8417-11e9-b057-edcb5fe9ed72; stockx_default_sneakers_size=7.5; _sp_ses.1a3e=*; _tl_csid=60d572b7-7e20-4baf-879d-f9834ecea514; _pk_ref.421.1a3e=%5B%22%22%2C%22%22%2C1560573414%2C%22https%3A%2F%2Fwww.google.com%2F%22%5D; _pk_ses.421.1a3e=*; _tl_auid=5cf1e486049897000f690756; _tl_sid=5d0475e76c0fee00a10a0786; _gat=1; is_gdpr=false; cookie_policy_accepted=true; show_all_as_number=false; brand_tiles_version=v1; show_bid_education=v2; show_bid_education_times=1; mobile_nav_v2=true; multi_edit_option=beatLowestAskBy; product_page_v2=watches%2Chandbags; show_watch_modal=true; _derived_epik=dj0yJnU9V1lJYXRTeU16MGF2eHl2VlZFOXZKOWFOZHNwb3ZHb2cmbj1nODlpN2RqRUZxSGF3azJsY2d1X25nJm09MSZ0PUFBQUFBRjBFZDBJ; _sp_id.1a3e=1e9c87cf-e416-485c-8050-e01d906c916d.1559356549.17.1560573781.1560562849.f04bf985-e96c-41a2-b57f-11c09e23b134; stockx_user_logged_in=true; token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdG9ja3guY29tIiwic3ViIjoic3RvY2t4LmNvbSIsImF1ZCI6IndlYiIsImFwcF9uYW1lIjoiSXJvbiIsImFwcF92ZXJzaW9uIjoiMi4wLjAiLCJpc3N1ZWRfYXQiOiIyMDE5LTA2LTE1IDA0OjQzOjAwIiwiY3VzdG9tZXJfaWQiOiI3NDk5MjE1IiwiZW1haWwiOiIxMjEzODY2OTY0QHFxLmNvbSIsImN1c3RvbWVyX3V1aWQiOiI2ZTEyNTlhMS04ZTU4LTExZTktODg4MC0xMmRlYjkwOWU5N2MiLCJmaXJzdE5hbWUiOiJaaGVoYW8iLCJsYXN0TmFtZSI6IldhbmciLCJnZHByX3N0YXR1cyI6bnVsbCwiZGVmYXVsdF9jdXJyZW5jeSI6IlVTRCIsImxhbmd1YWdlIjoiZW4tVVMiLCJzaGlwX2J5X2RhdGUiOm51bGwsInZhY2F0aW9uX2RhdGUiOm51bGwsInByb2R1Y3RfY2F0ZWdvcnkiOiJzdHJlZXR3ZWFyIiwiaXNfYWRtaW4iOiIwIiwic2Vzc2lvbl9pZCI6IjEzMDkxMDQxNzAwMzI0NDkxNTgwIiwiZXhwIjoxNTYxMTc4NTgwLCJhcGlfa2V5cyI6W119.Ak-dRv4lRF2PDUwzLkTY_B3RA5zltRGiTnWzx8hJBCQ; fs_uid=rs.fullstory.com`J4TYT`6215852469977088:6753299780009984`6e1259a1-8e58-11e9-8880-12deb909e97c`; _tl_uid=6e1259a1-8e58-11e9-8880-12deb909e97c; ajs_user_id=%226e1259a1-8e58-11e9-8880-12deb909e97c%22; ajs_anonymous_id=%22dd363046-f59f-485a-bcfa-69a0be9cacad%22; stockx_selected_currency=USD; stockx_selected_locale=en_US; lastRskxRun=1560573781170; _pk_id.421.1a3e=0102423b573ff79c.1559356551.16.1560573781.1560573412.; tl_sopts_60d572b7-7e20-4baf-879d-f9834ecea514_p_p_n=JTJG; tl_sopts_60d572b7-7e20-4baf-879d-f9834ecea514_p_p_l_h=aHR0cHMlM0ElMkYlMkZzdG9ja3guY29tJTJG; tl_sopts_60d572b7-7e20-4baf-879d-f9834ecea514_p_p_l_t=U3RvY2tYJTNBJTIwQnV5JTIwYW5kJTIwU2VsbCUyMFNuZWFrZXJzJTJDJTIwU3RyZWV0d2VhciUyQyUyMEhhbmRiYWdzJTJDJTIwV2F0Y2hlcw==; tl_sopts_60d572b7-7e20-4baf-879d-f9834ecea514_p_p_l=JTdCJTIyaHJlZiUyMiUzQSUyMmh0dHBzJTNBJTJGJTJGc3RvY2t4LmNvbSUyRiUyMiUyQyUyMmhhc2glMjIlM0ElMjIlMjIlMkMlMjJzZWFyY2glMjIlM0ElMjIlMjIlMkMlMjJob3N0JTIyJTNBJTIyc3RvY2t4LmNvbSUyMiUyQyUyMnByb3RvY29sJTIyJTNBJTIyaHR0cHMlM0ElMjIlMkMlMjJwYXRobmFtZSUyMiUzQSUyMiUyRiUyMiUyQyUyMnRpdGxlJTIyJTNBJTIyU3RvY2tYJTNBJTIwQnV5JTIwYW5kJTIwU2VsbCUyMFNuZWFrZXJzJTJDJTIwU3RyZWV0d2VhciUyQyUyMEhhbmRiYWdzJTJDJTIwV2F0Y2hlcyUyMiU3RA==; tl_sopts_60d572b7-7e20-4baf-879d-f9834ecea514_p_p_v_d=MjAxOS0wNi0xNVQwNCUzQTQzJTNBMDEuMTkxWg==; IR_9060=1560573762412%7C0%7C1560573415364%7C%7C; IR_PI=e9ea8dde-4f7d-11e9-a97b-12cd5acec8a1%7C1560660162412")
        self.last_query_time = None

        # min space in between each request we send
        self.throttle_seconds = 1
        # retry timeout 500s error
        self.server_retry_seconds = 3
        # retry timeout 400s error
        self.client_retry_seconds = 20

    def __api_query(self, request_type, command, data=None):
        if self.throttle_seconds > 0 and self.last_query_time:
            if datetime.datetime.now() <= self.last_query_time + datetime.timedelta(0, self.throttle_seconds):
                time.sleep(self.throttle_seconds)
                return self.__api_query(request_type, command, data)

        endpoint = self.API_BASE + command
        response = None
        if request_type == 'GET':
            response = requests.get(
                endpoint,
                params=data,
                headers=self.headers,
                cookies=self.cookies)
        elif request_type == 'POST':
            response = requests.post(
                endpoint, json=data,
                headers=self.headers,
                cookies=self.cookies)
        elif request_type == 'DELETE':
            response = requests.delete(
                endpoint,
                json=data,
                headers=self.headers,
                cookies=self.cookies)
        else:
            print("Unknown request type: {}".format(request_type))
            return
        self.last_query_time = datetime.datetime.now()
        if response.status_code == 200:
            return response.json()
        elif int(response.status_code) // 100 == 5:
            # series 5 error, their stuff. We wait a bit.
            print("response: {}. we wait {}s.".format(response, self.server_retry_seconds))
            time.sleep(self.server_retry_seconds)
            return self.__api_query(request_type, command, data)
        else:
            print("response: {}. we wait {}s.".format(response, self.client_retry_seconds))
            time.sleep(self.client_retry_seconds)
            return self.__api_query(request_type, command, data)

    def __get(self, command, data=None):
        return self.__api_query('GET', command, data)

    def __post(self, command, data=None):
        return self.__api_query('POST', command, data)

    def __delete(self, command, data=None):
        return self.__api_query('DELETE', command, data)

    def authenticate(self, email, password):
        endpoint = self.API_BASE + '/login'
        payload = {
            'email': email,
            'password': password
        }
        auth_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
            'Referer': 'https://stockx.com/',
            'Origin': 'https://stockx.com',
            'Content-Type': 'text/plain'
        }
        response = requests.post(endpoint, json=payload, headers=auth_headers, cookies=self.cookies)
        if response.status_code == 200:
            customer = response.json().get('Customer', None)
            if customer is None:
                raise ValueError('Authentication failed, check username/password')
            self.customer_id = response.json()['Customer']['id']
            self.headers = {
                'JWT-Authorization': response.headers['jwt-authorization'],
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
                'Referer': 'https://stockx.com/',
                'Origin': 'https://stockx.com',
                'Content-Type': 'text/plain'
            }
            return True
        else:
            print("auth failed {} {}".format(response.status_code, response.text))
            return False

    def me(self):
        command = '/users/me'
        return self.__get(command)

    def selling(self):
        command = '/customers/{0}/selling'.format(self.customer_id)
        response = self.__get(command)
        return [StockxItem(item_json) for item_json in response['PortfolioItems']]

    def buying(self):
        command = '/customers/{0}/buying'.format(self.customer_id)
        response = self.__get(command)
        return [StockxItem(item_json) for item_json in response['PortfolioItems']]

    def rewards(self):
        command = '/users/me/rewards'
        return self.__get(command)

    def stats(self):
        command = '/customers/{0}/collection/stats'.format(self.customer_id)
        return self.__get(command)

    def cop_list(self):
        command = '/customers/{0}/cop-list'.format(self.customer_id)
        response = self.__get(command)
        return [StockxItem(item_json) for item_json in response['PortfolioItems']]

    def add_product_to_follow(self, product_id):
        command = '/portfolio?a=1001'
        payload = {
            'timezone': 'America/Chicago',
            'PortfolioItem': {
                'amount': 0,
                'matchedWithDate': '',
                'condition': '2000',
                'skuUuid': product_id,
                'action': 1001
            }
        }
        response = self.__post(command, payload)
        success = response['PortfolioItem']['text'] == 'Following'
        return success

    def add_product_to_portfolio(self, product_id, purchase_price, condition='new', purchase_date=None):
        purchase_price = purchase_price or now()
        conditions = {
            'new': 2000,
            '9.5': 950,
            '9': 900,
            '8.5': 850,
            '8': 800,
            '7': 700,
            '6': 600,
            '5': 500,
            '4': 400,
            '3': 300,
            '2': 200,
            '1': 100
        }
        condition = conditions.get(condition, None)
        command = '/portfolio?a=1000'
        payload = {
            'timezone': 'America/Chicago',
            'PortfolioItem': {
                'amount': purchase_price,
                'matchedWithDate': '{0}T06:00:00+0000'.format(purchase_date),
                'condition': condition,
                'skuUuid': product_id,
                'action': '1000'
            }
        }
        response = self.__post(command, payload)
        success = response['PortfolioItem']['text'] == 'In Portfolio'
        return success
        
    def get_product(self, product_id):
        command = '/products/{0}'.format(product_id)
        product_json = self.__get(command)
        return StockxProduct(product_json)

    def __get_activity(self, product_id, activity_type, suffix=""):
        command = '/products/{0}/activity?state={1}{2}'.format(product_id, activity_type, suffix)
        return self.__get(command)

    def get_transactions(self, product_id, limit=50):
        res = self.__get_activity(product_id, 480, "&currency=USD&limit={}&page=1&sort=createdAt&order=DESC".format(limit))
        return res

    def get_asks(self, product_id):
        return [StockxOrder('ask', order) for order in self.__get_activity(product_id, 400)]

    def get_lowest_ask(self, product_id):
        res = self.get_asks(product_id)
        if len(res) > 0:
            return res[0]
        else:
            return None
    
    def get_bids(self, product_id):
        return [StockxOrder('bid', order) for order in self.__get_activity(product_id, 300)]

    def get_highest_bid(self, product_id):
        res = self.get_bids(product_id)
        if len(res) > 0:
            return res[0]
        else:
            return None

    def create_ask(self, product_id, price, expiry_date=None):
        expiry_date = expiry_date or now_plus_thirty()
        command = '/portfolio?a=ask'
        payload = {
            'PortfolioItem': {
                'amount': price,
                'expiresAt': '{0}T06:00:00+0000'.format(expiry_date),
                'skuUuid': product_id
            }
        }
        response = self.__post(command, payload)
        if response.get('error', None):
            raise ValueError(json.loads(response['message'])['description'])
        return response['PortfolioItem']['chainId']

    def update_ask(self, ask_id, new_price, expiry_date=None):
        expiry_date = expiry_date or now_plus_thirty()
        command = '/portfolio?a=ask'
        payload = {
            'PortfolioItem': {
                'amount': new_price,
                'expiresAt': '{0}T06:00:00+0000'.format(expiry_date),
                'chainId': ask_id
            }
        }
        response = self.__post(command, payload)
        success = response['PortfolioItem']['statusMessage'] == 'Ask Listed'
        return success

    def cancel_ask(self, ask_id):
        command = '/portfolio/{0}'.format(ask_id)
        payload = {
            'chain_id': ask_id,
            'notes': 'User Canceled Ask'
        }
        response = self.__delete(command, payload)
        success = response['PortfolioItem']['notes'] == 'User Canceled Ask'
        return success

    def create_bid(self, product_id, price, expiry_date=None):
        expiry_date = expiry_date or now_plus_thirty()
        command = '/portfolio?a=bid'
        payload = {
            'PortfolioItem': {
                'amount': price,
                'expiresAt': '{0}T06:00:00+0000'.format(expiry_date),
                'skuUuid': product_id,
                'meta': {
                    'sizePreferences': ''
                }
            }
        }
        response = self.__post(command, payload)
        if response.get('error', None):
            raise ValueError(json.loads(response['message']['description']))
        return response['PortfolioItem']['chainId']

    def update_bid(self, bid_id, new_price, expiry_date=None):
        expiry_date = expiry_date or now_plus_thirty()
        command = '/portfolio?a=bid'
        payload = {
            'PortfolioItem': {
                'amount': new_price,
                'expiresAt': '{0}T06:00:00+0000'.format(expiry_date),
                'chainId': bid_id,
                'meta': {
                    'sizePreferences': ''
                }
            }
        }
        response = self.__post(command, payload)
        success = response['PortfolioItem']['statusMessage'] == 'Bid Placed'
        return success

    def cancel_bid(self, bid_id):
        command = '/portfolio/{0}'.format(bid_id)
        payload = {
            'chain_id': bid_id,
            'notes': 'User Canceled Bid'
        }
        response = self.__delete(command, payload)
        success = response['PortfolioItem']['notes'] == 'User Canceled Bid'
        return success

    def search(self, query):
        endpoint = 'https://xw7sbct9v6-dsn.algolia.net/1/indexes/products/query'
        params = {
            'x-algolia-agent': 'Algolia for vanilla JavaScript 3.22.1',
            'x-algolia-application-id': 'XW7SBCT9V6',
            'x-algolia-api-key': '6bfb5abee4dcd8cea8f0ca1ca085c2b3'
        }
        payload = {
            'params': 'query={0}&hitsPerPage=50&facets=*'.format(query)
        }
        return requests.post(endpoint, json=payload, params=params).json()['hits']

    def get_first_product_id(self, query):
        return self.search(query)[0]['objectID']
