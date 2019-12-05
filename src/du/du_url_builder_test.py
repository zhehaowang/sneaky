#!/usr/bin/env python3

import unittest
import json
import requests

from du_url_builder import DuRequestBuilder
from du_response_parser import DuParser, SaleRecord

# test connectivity
class TestConnectivityAndParse(unittest.TestCase):
    def setUp(self):
        self.request_builder = DuRequestBuilder()
        self.parser = DuParser()
        return

    def test_recent_sales(self):
        recentsales_list_url = self.request_builder.get_recentsales_list_url(0, 40755)
        recentsales_list_response = requests.get(url=recentsales_list_url, headers=DuRequestBuilder.du_headers)
        try:
            status = json.loads(recentsales_list_response.text)["status"]
        except KeyError as e:
            self.assertFalse(str(e))
        except json.decoder.JSONDecodeError as e:
            self.assertFalse(str(e))
        self.assertEqual(status, 200)

        last_id, sales = self.parser.parse_recent_sales(recentsales_list_response.text)
        print("retrieved last_id {} and {} records.".format(last_id, len(sales)))
        if len(sales) > 0:
            print("example record {}".format(sales[0]))

    def test_search_by_keywords(self):
        search_by_keywords_url = self.request_builder.get_search_by_keywords_url("aj", 0, 1, 0)
        search_by_keywords_response = requests.get(url=search_by_keywords_url, headers=DuRequestBuilder.du_headers)
        try:
            status = json.loads(search_by_keywords_response.text)["status"]
        except KeyError as e:
            self.assertFalse(str(e))
        except json.decoder.JSONDecodeError as e:
            self.assertFalse(str(e))
        self.assertEqual(status, 200)

    def test_brandlist(self):
        brand_list_url = self.request_builder.get_brand_list_url(1, 4)
        brand_list_response = requests.get(url=brand_list_url, headers=DuRequestBuilder.du_headers)
        try:
            status = json.loads(brand_list_response.text)["status"]
        except KeyError as e:
            self.assertFalse(str(e))
        except json.decoder.JSONDecodeError as e:
            self.assertFalse(str(e))
        self.assertEqual(status, 200)

    def test_product_details(self):
        product_detail_url =  self.request_builder.get_product_detail_url(53489)
        product_detail_response = requests.get(url=product_detail_url, headers=DuRequestBuilder.du_headers)
        try:
            status = json.loads(product_detail_response.text)["status"]
        except KeyError as e:
            self.assertFalse(str(e))
        except json.decoder.JSONDecodeError as e:
            self.assertFalse(str(e))
        self.assertEqual(status, 200)

if __name__ == '__main__':
    unittest.main()
