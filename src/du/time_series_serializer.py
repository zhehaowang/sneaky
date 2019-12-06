import json
import os
import pathlib

from du_response_parser import SaleRecord

class TimeSeriesSerializer():
    def __init__(self):
        return
    
    def find_path(self, style_id, size):
        return "../data/{}/{}.json".format(style_id, size)

    def get_size_transactions(self, transactions):
        result = {}
        for t in transactions:
            if t.size not in result:
                result[t.size] = []
            else:
                result[t.size].append({
                    "price": t.price,
                    "time": t.time,
                    "id": t.id
                })
        return result

    def update(self, venue, update_time, style_id, size_prices, size_transactions):
        for size in size_prices:
            outfile = self.find_path(style_id, size)
            if os.path.isfile(outfile):
                with open(outfile, "r") as infile:
                    data = json.loads(infile.read())
            else:
                outdir = os.path.dirname(outfile)
                pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
                data = {}
            
            if not venue in data:
                data[venue] = {
                    "prices": [],
                    "transactions": []
                }
            
            prices = size_prices[size]
            data[venue]["prices"].append({
                "time": update_time.strftime("%Y%m%d-%H%M%S"),
                "bid_price": prices["bid_price"] if "bid_price" in prices else None,
                "ask_price": prices["ask_price"] if "ask_price" in prices else None
            })

            if size in size_transactions:
                transactions = size_transactions[size]
                if len(data[venue]["transactions"]) > 0:
                    last_id = data[venue]["transactions"][0]["id"]
                    idx = 0
                    for t in transactions:
                        if t["id"] == last_id:
                            break
                        else:
                            idx += 1
                    data[venue]["transactions"] = transactions[:idx] + data[venue]["transactions"]
                else:
                    data[venue]["transactions"] = transactions
            
            with open(outfile, "w") as infile:
                infile.write(json.dumps(data))
        return
