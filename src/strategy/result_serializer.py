#!/usr/bin/env python3

import sys
# hack for import
sys.path.append('../feed/')

from sizer import Sizer

class ResultSerializer():
    def __init__(self, fees, fx_rate):
        self.fees = fees
        self.fx_rate = fx_rate
        self.sizer = Sizer()
        return

    def get_annotation_str(self, annotation):
        return_str = ""
        for source in ["bid", "mid", "ask"]:
            for dest in ["listing", "last"]:
                option_name = "profit_ratio_{}_to_{}".format(source, dest)
                if option_name in annotation:
                    return_str += "  profit ratio ({} to {}): {:.2f} %\n".format(source, dest, annotation[option_name] * 100)
                option_name = "profit_value_{}_to_{}".format(source, dest)
                if option_name in annotation:
                    return_str += "  profit value ({} to {}): {:.2f} USD\n".format(source, dest, annotation[option_name])
        return return_str

    def to_str(self, sorted_size_prices, static_info, static_info_extras):
        for i in sorted_size_prices:
            style_id, size = i["identifier"]
            item = static_info[style_id]
            item_extras = static_info_extras[style_id]
            data = i["data"]
            data["annotation"]["du_price_usd"] = self.fx_rate.get_spot_fx(
                data["du"]["prices"][0]["bid_price"] / 100,
                "CNY", "USD"
            )
            data["annotation"]["du_last_transaction_usd"] = self.fx_rate.get_spot_fx(
                data["du"]["transactions"][0]["price"] / 100,
                "CNY", "USD"
            )

            chinese_size = self.sizer.get_shoe_size(size, "us", item.gender)
            print("{} {} {}\n{} , {}\n{}".format(
                style_id, size, chinese_size, item_extras["stockx_url_key"], item.title, item_extras["stockx_release_date"]))
            print("  du listing price:     {:.2f} CNY {:.2f} USD\n"
                  "  du transaction price: {:.2f} CNY {:.2f} USD\n"
                  "  du transaction time:  {}\n"
                  "  stockx bid:           {:.2f} USD\n"
                  "  stockx ask:           {:.2f} USD\n"
                  "{}".format(
                data["du"]["prices"][0]["bid_price"] / 100,
                data["annotation"]["du_price_usd"],
                data["du"]["transactions"][0]["price"] / 100,
                data["annotation"]["du_last_transaction_usd"],
                data["du"]["transactions"][0]["time"],
                data["stockx"]["prices"][0]["bid_price"],
                data["stockx"]["prices"][0]["ask_price"],
                self.get_annotation_str(data["annotation"])))
