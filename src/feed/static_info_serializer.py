import datetime
import csv

from du_response_parser import DuItem

class StaticInfoSerializer():
    def __init__(self):
        return

    def extract_item_static_info(self, items):
        result = [items[i].get_static_info() for i in items]
        return result

    def dump_static_info_to_csv(self, items, filename=None):
        static_items = self.extract_item_static_info(items)
        date_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        if not filename:
            static_mapping_file = "du.mapping.{}.csv".format(date_time)
        else:
            static_mapping_file = filename
        with open(static_mapping_file, "w") as outfile:
            wr = csv.writer(outfile)
            wr.writerow(["style_id", "du_product_id", "du_title", "release_date", "gender"])
            for row in static_items:
                wr.writerow([row["style_id"], row["product_id"], row["title"], row["release_date"], row["gender"]])
        print("dumped {} entries to {}".format(len(static_items), static_mapping_file))

    def load_static_info_from_csv(self, filename):
        result = {}
        with open(filename, "r") as infile:
            rr = csv.DictReader(infile)
            for row in rr:
                product_id = row["du_product_id"]

                item = DuItem(product_id, row["du_title"], 0)
                item.release_date = row["release_date"]
                item.style_id = row["style_id"]
                item.gender = row["gender"]
                result[product_id] = item
        return result

