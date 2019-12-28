#!/usr/bin/env python3

import sys

# hack for import
sys.path.append("../feed/")

from sizer import Sizer, SizerError


class ResultSerializer:
    def __init__(self, fees, fx_rate):
        self.fees = fees
        self.fx_rate = fx_rate
        self.sizer = Sizer()
        return

    def get_annotation_str(self, annotation, style_id, size):
        return_str = ""
        for source in ["bid", "mid", "ask"]:
            for dest in ["listing", "last"]:
                option_name = "profit_ratio_{}_to_{}".format(source, dest)
                if option_name in annotation:
                    return_str += "  profit ratio ({} to {}): {:.2f} %\n".format(
                        source, dest, annotation[option_name] * 100
                    )
                option_name = "profit_value_{}_to_{}".format(source, dest)
                if option_name in annotation:
                    return_str += "  profit value ({} to {}): {:.2f} USD\n".format(
                        source, dest, annotation[option_name]
                    )
        if "du_analyzer" in annotation:
            stats = annotation["du_analyzer"]
            return_str += "  Du Transactions:\n" \
                          "    First Date:       {}\n" \
                          "    Number of Sales:  {}\n" \
                          "    Sales / Day:      {:.2f}\n" \
                          "    High:             {:.2f} CNY {:.2f} USD\n" \
                          "    Low:              {:.2f} CNY {:.2f} USD\n" \
                          "    First:            {:.2f} CNY {:.2f} USD\n" \
                          "    Last:             {:.2f} CNY {:.2f} USD\n" \
                          "    Average:          {:.2f} CNY {:.2f} USD\n" \
                          "    Stdev:            {:.2f} CNY {:.2f} USD\n" \
                          "  Plot command: {}\n".format(
                            stats["first_date"].isoformat(),
                            stats["num_sales"],
                            stats["sales_per_day"],
                            stats["high"], self.fx_rate.get_spot_fx(stats["high"], "CNY", "USD"),
                            stats["low"], self.fx_rate.get_spot_fx(stats["low"], "CNY", "USD"),
                            stats["first"], self.fx_rate.get_spot_fx(stats["first"], "CNY", "USD"),
                            stats["last"], self.fx_rate.get_spot_fx(stats["last"], "CNY", "USD"),
                            stats["avg"], self.fx_rate.get_spot_fx(stats["avg"], "CNY", "USD"),
                            stats["stdev"], self.fx_rate.get_spot_fx(stats["stdev"], "CNY", "USD"),
                            "./du_analyzer.py --style_id {} --size {} --mode plot".format(style_id, size))
        return return_str

    def to_str(self, sorted_size_prices, static_info, static_info_extras):
        for i in sorted_size_prices:
            style_id, size = i["identifier"]
            item = static_info[style_id]
            item_extras = static_info_extras[style_id]
            data = i["data"]
            data["annotation"]["du_price_usd"] = self.fx_rate.get_spot_fx(
                data["du"]["prices"][0]["list_price"] / 100, "CNY", "USD"
            )
            data["annotation"]["du_last_transaction_usd"] = self.fx_rate.get_spot_fx(
                data["du"]["transactions"][0]["price"] / 100, "CNY", "USD"
            )

            # TODO: until merged has the right sizing, this reverse translation may
            # not be accurate
            try:
                chinese_size = self.sizer.get_shoe_size(size, item.gender.replace("eu", "us"), "eu")
                print(
                    "{} {} {}\n{} , {}\nRelease date:           {}".format(
                        style_id,
                        size,
                        chinese_size,
                        item_extras["stockx_url_key"],
                        item.title,
                        item_extras["stockx_release_date"],
                    )
                )
                print(
                    "  du listing price:     {:.2f} CNY {:.2f} USD\n"
                    "  du transaction price: {:.2f} CNY {:.2f} USD\n"
                    "  du transaction time:  {}\n"
                    "  stockx bid:           {:.2f} USD\n"
                    "  stockx ask:           {:.2f} USD\n"
                    "  stockx annual high:   {:.2f} USD\n"
                    "  stockx annual low:    {:.2f} USD\n"
                    "  stockx volatility:    {:.2f}\n"
                    "  stockx sale last 72h: {}\n"
                    "{}".format(
                        data["du"]["prices"][0]["list_price"] / 100,
                        data["annotation"]["du_price_usd"],
                        data["du"]["transactions"][0]["price"] / 100,
                        data["annotation"]["du_last_transaction_usd"],
                        data["du"]["transactions"][0]["time"],
                        data["stockx"]["prices"][0]["bid_price"],
                        data["stockx"]["prices"][0]["ask_price"],
                        data["stockx"]["prices"][0]["annual_high"],
                        data["stockx"]["prices"][0]["annual_low"],
                        data["stockx"]["prices"][0]["volatility"],
                        data["stockx"]["prices"][0]["sale_72_hours"],
                        self.get_annotation_str(data["annotation"], style_id, size),
                    )
                )
            except SizerError:
                print("sizer failed to translate {} {}. continuing".format(style_id, size))
                continue
