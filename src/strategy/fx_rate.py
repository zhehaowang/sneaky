import requests


class FxRate:
    def __init__(self):
        self.fx_rates = {}

    def get_spot_fx(self, in_amount, in_ccy, out_ccy):
        if not (in_ccy, out_ccy) in self.fx_rates:
            r = requests.get(
                "http://rate-exchange-1.appspot.com/currency?from={}&to={}".format(
                    in_ccy, out_ccy
                )
            )
            self.fx_rates[(in_ccy, out_ccy)] = r.json()["rate"]
        return in_amount * self.fx_rates[(in_ccy, out_ccy)]
