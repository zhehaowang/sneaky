#!/usr/bin/env python3

import os
import sys
import json
import pprint

from stockxsdk import Stockx

class StockXFeed():
	def __init__(self):
		self.stockx = Stockx()
		return 

	def authenticate(self, usrname, pwd):
		if not self.stockx.authenticate(usrname, pwd):
			raise RuntimeError("failed to log in as {}".format(usrname))

	def get_details(self, product_id):
		# product_id = stockx.get_first_product_id('BB1234')
		product = self.stockx.get_product(product_id)
		print("product title: {}".format(product.title))

		highest_bid = self.stockx.get_highest_bid(product_id)
		print("size: {}, best bid: {}".format(highest_bid.shoe_size, highest_bid.order_price))

		lowest_ask = self.stockx.get_lowest_ask(product_id)
		print("size: {}, best ask: {}".format(lowest_ask.shoe_size, lowest_ask.order_price))

		asks = self.stockx.get_asks(product_id)
		print(len(asks))
		for ask in asks:
			print(ask)

		bids = self.stockx.get_bids(product_id)
		for bid in bids:
			print(bid)

	def search(self, query):
		results = self.stockx.search(query)
		pp = pprint.PrettyPrinter(indent=2)
		for item in results:
			pp.pprint(item)
			# print("name {}\n  best bid {}\n  best ask {}\n  last sale {}\n  sales last 72 {}\n  release date {}\n".format(item['name'], item['highest_bid'], item['lowest_ask'], item['last_sale'], item['sales_last_72'], item['Release Date']['value']))


if __name__ == "__main__":
	stockx_feed = StockXFeed()
	with open("../credentials/credentials.json", "r") as cred_file:
		cred = json.loads(cred_file.read())["stockx"]
		stockx_feed.authenticate(cred["username"], cred["password"])
		stockx_feed.get_details('2c91a3dc-4ba6-40bc-af0b-a259f793a223')

		# stockx_feed.search('air jordan')
