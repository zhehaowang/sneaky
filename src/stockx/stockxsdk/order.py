class StockxOrder(object):
    def __init__(self, order_type, order_json):
        try:
            self.product_uuid = order_json['skuUuid']
            self.order_type = order_type
            self.order_price = order_json['amount']
            self.shoe_size = order_json['shoeSize']
            self.num_orders = order_json['frequency'] if 'frequency' in order_json else 0
        except TypeError as e:
            print("error constructing StockxOrder: {}".format(e))
            print(order_json)
            print(order_type)
        except KeyError as e:
            print("error constructing StockxOrder: {}".format(e))
            print(order_json)
            print(order_type)

    def __str__(self):
    	return "uuid: {}; size: {}; order_type: {}; px: {}; num_orders: {}".format(self.product_uuid, self.shoe_size, self.order_type, self.order_price, self.num_orders)
    