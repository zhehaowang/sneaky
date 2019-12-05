#!/usr/bin/env python3

import execjs

class DuRequestBuilder():
   du_headers = {
      'Host': "app.poizon.com",
      'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)"
      " Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.4.501 NetType/WIFI "
      "MiniProgramEnv/Windows WindowsWechat",
      'appid': "wxapp",
      'appversion': "4.4.0",
      'content-type': "application/x-www-form-urlencoded",
      'Accept-Encoding': "gzip, deflate",
      'Accept': "*/*",
   }

   def __init__(self):
      self.salt = "19bc545a393a25177083d4a748807cc0"
      self.base_url = "https://app.poizon.com/api/v1/h5"

      with open('sign.js', 'r', encoding='utf-8') as f:
         self.ctx = execjs.compile(f.read())

   def get_recentsales_list_url(self, last_id, product_id, limit=20):
      # recent sales
      sign = self.ctx.call('getSign','lastId{}limit{}productId{}sourceAppapp{}'.format(last_id, limit, product_id, self.salt))
      url = self.base_url + '/product/fire/recentSoldList?' \
            'productId={}&lastId={}&limit={}&sourceApp=app&sign={}'.format(product_id, last_id, limit, sign)
      return url

   def get_search_by_keywords_url(self, page, sort_mode, sort_type, limit=20):
      # search by keyword
      sign = self.ctx.call('getSign','limit{}page{}sortMode{}sortType{}titleajunionId{}'.format(limit, page, sort_mode, sort_type, self.salt))
      url = self.base_url + '/product/fire/search/list?title=aj&page={}&sortType={}&sortMode={}&' \
            'limit={}&unionId=&sign={}'.format(page, sort_type, sort_mode, limit, sign)
      return url

   def get_brand_list_url(self, last_id, tab_id, limit=20):
      # list
      sign = self.ctx.call('getSign', 'lastId{}limit{}tabId{}{}'.format(last_id, limit, tab_id, self.salt))
      url = self.base_url + '/index/fire/shoppingTab?' \
            'tabId={}&limit={}&lastId={}&sign={}'.format(tab_id, limit, last_id, sign)
      return url

   def get_product_detail_url(self, product_id):
      # product details
      sign = self.ctx.call('getSign', 'productId{}productSourceNamewx{}'.format(product_id, self.salt))
      url = self.base_url + '/index/fire/flow/product/detail?' \
            'productId={}&productSourceName=wx&sign={}'.format(product_id, sign)
      return url
