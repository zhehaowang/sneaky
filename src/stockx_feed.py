#!/usr/bin/env python3

import os
import sys
import json
import pprint

from stockxsdk import Stockx

pp = pprint.PrettyPrinter(indent=2)
		
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
		bids = self.stockx.get_bids(product_id)
		
		book = StockXFeed.build_book(product, bids, asks)
		StockXFeed.print_book(product, book)
		return

	@staticmethod
	def is_better(px1, px2, side):
		if side == 'bid':
			return px1 > px2
		elif side == 'ask':
			return px1 < px2
		else:
			raise RuntimeError('unknown side {}'.format(side))
		return

	@staticmethod
	def build_book(product, bids, asks):
		"""Given a product and bids and asks of all shoe sizes, for each shoe
		size construct a book.

		@param product stockxsdk.product
		@param bids    [stockxsdk.order]
		@param asks    [stockxsdk.order]

		@return {"9": {"bid": [{"px": 20, "size": 1, "orders": ...},
							   {"px": 19, "size": 2, "orders": ...}]},
					   "ask": [{"px": 21, "size": 1, "orders": ...},
							   {"px": 22, "size": 1, "orders": ...}]}},
			     "8": ...}
		"""
		sizes = {}

		def init_level(order):
			return {"px": order.order_price, "size": int(order.num_orders), "orders": [order]}

		def build_half(sizes, orders):
			for order in orders:
				if not order.shoe_size in sizes:
					sizes[order.shoe_size] = {"bid": [], "ask": []}
					sizes[order.shoe_size][order.order_type].append(init_level(order))
				else:
					half = sizes[order.shoe_size][order.order_type]
					level_idx = 0
					while level_idx < len(half):
						if order.order_price == half[level_idx]["px"]:
							half[level_idx]["orders"].append(order)
							half[level_idx]["size"] += int(order.num_orders)
							break
						elif StockXFeed.is_better(order.order_price, half[level_idx]["px"], order.order_type):
							half.insert(level_idx, init_level(order))
							break
						level_idx += 1

					if level_idx == len(half):
						half.append(init_level(order))

		build_half(sizes, bids)
		build_half(sizes, asks)

		# pp.pprint(sizes)
		return sizes

	@staticmethod
	def print_book(product, book):
		for shoe_size in book:
			print('---- {} : {} ----'.format(product.title, shoe_size))
			print('---- Bid ----  ---- Ask ----')
			for level in book[shoe_size]['ask'][::-1]:
				print("               {:.2f} {}".format(level["px"], level["size"]))
			for level in book[shoe_size]['bid']:
				print("{:6d} {:.2f}".format(level["size"], level["px"]))
			print('----------------------------')
			if len(book[shoe_size]["bid"]) > 0 and len(book[shoe_size]["ask"]) > 0:
				print('Spread: {:.2f}. Mid: {:.2f}'.format(book[shoe_size]["ask"][0]["px"] - book[shoe_size]["bid"][0]["px"], (book[shoe_size]["ask"][0]["px"] + book[shoe_size]["bid"][0]["px"]) / 2))
			else:
				print('One side is empty')
			print()

	def search(self, query):
		results = self.stockx.search(query)
		for item in results:
			# pp.pprint(item)
			print("name {}\n  best bid {}\n  best ask {}\n  last sale {}\n  sales last 72 {}\n".format(item['name'], item['highest_bid'], item['lowest_ask'], item['last_sale'], item['sales_last_72']))
		return

if __name__ == "__main__":
	stockx_feed = StockXFeed()
	with open("../credentials/credentials.json", "r") as cred_file:
		cred = json.loads(cred_file.read())["stockx"]
		stockx_feed.authenticate(cred["username"], cred["password"])
		stockx_feed.get_details('2c91a3dc-4ba6-40bc-af0b-a259f793a223')

		# stockx_feed.search('air jordan')
