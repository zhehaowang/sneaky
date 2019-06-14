import json

class StockxProduct(object):
    def __init__(self, product_json):
        # print(json.dumps(product_json, indent=4))
        if not 'Product' in product_json:
            return
        product = product_json['Product']
        self.product_id = product['id']
        self.title = product['title']
        if 'retailPrice' in product:
            self.retail_price = product['retailPrice']
        else:
            self.retail_price = None
        if 'styleId' in product:
            self.style_id = product['styleId']
            print(self.style_id)
        else:
            self.style_id = None
        self.brand = product['brand']
        self.image = product['media']['imageUrl']
        children = [product['children'][child] for child in product['children']]
        self.sizes = {child['shoeSize']: child['id'] for child in children}

        if len(product['breadcrumbs']) > 0:
            self.url = "https://stockx.com" + product['breadcrumbs'][-1]['url']
        else:
            self.url = None

