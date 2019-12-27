#!/usr/bin/env python3

import json
from fx_rate import FxRate


class Fees:
    def __init__(self, conf_file, fx_rate):
        with open(conf_file, "r") as infile:
            self.conf = json.loads(infile.read())
        self.fx_rate = fx_rate
        return

    def get_total_buy_side_fees(self, venue, buy_price_usd=None):
        """
        Buy side fees. All fees are denominated in USD.
        """
        if venue == "stockx":
            return self.conf[venue]["buy_shipping_usd"]
        raise RuntimeError("fees: unsupported venue / unimplemented {}".format(venue))

    def get_total_sell_side_fees(self, venue, sell_price_usd=None):
        """
        Sell side fees. All fees are denominated in USD.
        """
        if venue == "du":
            if not sell_price_usd:
                raise RuntimeError(
                    "sell_price_usd is required to get fees on {}".format(venue)
                )
            return sell_price_usd * (
                self.conf[venue]["commission_percent"]
                + self.conf[venue]["tech_service_percent"]
                + self.conf[venue]["transfer_percent"]
            ) / 100 + self.fx_rate.get_spot_fx(
                self.conf[venue]["packaging_cny"]
                + self.conf[venue]["verification_cny"]
                + self.conf[venue]["service_cny"],
                "CNY",
                "USD",
            )
        raise RuntimeError("fees: unsupported venue / unimplemented {}".format(venue))

    def get_shipping_cost(self, buy_venue, sell_venue):
        """
        Cost of transfers the item from buy side to sell side: shipping, etc.
        All fees are denominated in USD.
        """
        if buy_venue == "stockx" and sell_venue == "du":
            return self.conf["shipping"]["stockx_du_usd"]
        raise RuntimeError(
            "fees: unsupported venue / unimplemented {} {}".format(
                buy_venue, sell_venue
            )
        )

    def get_list_price_for_sell_value(self, venue, target_value_usd, out_ccy=None):
        """
        The reverse of `get_total_sell_side_fees`.
        All fees are denominated in USD unless specified otherwise.
        """
        if venue == "du":
            list_price_usd = (
                target_value_usd
                + self.fx_rate.get_spot_fx(
                    self.conf[venue]["packaging_cny"]
                    + self.conf[venue]["verification_cny"]
                    + self.conf[venue]["service_cny"],
                    "CNY",
                    "USD",
                )
            ) / (
                1
                - (
                    (
                        self.conf[venue]["commission_percent"]
                        + self.conf[venue]["tech_service_percent"]
                        + self.conf[venue]["transfer_percent"]
                    )
                    / 100
                )
            )
            if not out_ccy or out_ccy == "USD":
                return list_price_usd
            else:
                return self.fx_rate.get_spot_fx(list_price_usd, "USD", "CNY")
        raise RuntimeError("fees: unsupported venue / unimplemented {}".format(venue))

    def _get_income_expenditure(
        self, buy_venue, sell_venue, buy_price_usd, sell_price, sell_price_ccy=None
    ):
        if not sell_price_ccy:
            sell_price_usd = sell_price
        else:
            sell_price_usd = self.fx_rate.get_spot_fx(sell_price, sell_price_ccy, "USD")
        total_expenditure = (
            buy_price_usd
            + self.get_total_buy_side_fees(buy_venue, buy_price_usd=buy_price_usd)
            + self.get_shipping_cost(buy_venue, sell_venue)
        )
        total_income = sell_price_usd - self.get_total_sell_side_fees(
            sell_venue, sell_price_usd=sell_price_usd
        )
        return total_income, total_expenditure

    def get_profit_percent(
        self, buy_venue, sell_venue, buy_price_usd, sell_price, sell_price_ccy=None
    ):
        """
        How much percent can we make if we buy and sell at the given prices.
        Fees on both sides are applied in this function.
        Ratio is calculated as:
            total_expenditure = buy_price + buy_fees + shipping_buy_to_sell
            total_income = sell_price - sell_fees
            ratio = (total_income - total_expenditure) / total_expenditure
        
        All fees are denominated in USD unless specified otherwise.
        """
        total_income, total_expenditure = self._get_income_expenditure(
            buy_venue, sell_venue, buy_price_usd, sell_price, sell_price_ccy
        )
        profit_ratio = (total_income - total_expenditure) / total_expenditure
        return profit_ratio

    def get_profit_value(
        self, buy_venue, sell_venue, buy_price_usd, sell_price, sell_price_ccy=None
    ):
        """
        Similar as `get_profit_percent` but in value
        """
        total_income, total_expenditure = self._get_income_expenditure(
            buy_venue, sell_venue, buy_price_usd, sell_price, sell_price_ccy
        )
        return total_income - total_expenditure

    def get_target_list_price_for_target_ratio(
        self, buy_venue, sell_venue, target_ratio, buy_price_usd, out_ccy=None
    ):
        """
        The reverse of `get_profit_percent`.
        All fees are denominated in USD unless specified otherwise.
        """
        total_expenditure = (
            buy_price_usd
            + self.get_total_buy_side_fees(buy_venue, buy_price_usd=buy_price_usd)
            + self.get_shipping_cost(buy_venue, sell_venue)
        )
        total_income = total_expenditure * (1 + target_ratio)
        list_price = self.get_list_price_for_sell_value(
            sell_venue, total_income, out_ccy=out_ccy
        )
        return list_price


if __name__ == "__main__":
    fx_rate = FxRate()
    fees = Fees("fees.json", fx_rate)
