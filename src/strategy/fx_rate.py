import requests


class FxRate:
    def __init__(self):
        self.fx_rates = {}

    def get_spot_fx(self, in_amount, in_curr, out_curr):
        if not (in_curr, out_curr) in self.fx_rates:
            r = requests.get(
                "http://rate-exchange-1.appspot.com/currency?from={}&to={}".format(
                    in_curr, out_curr
                )
            )
            self.fx_rates[(in_curr, out_curr)] = r.json()["rate"]
        return in_amount * self.fx_rates[(in_curr, out_curr)]
