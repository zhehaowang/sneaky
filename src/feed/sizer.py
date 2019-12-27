# agree
# http://www.shoesizes.co/
# https://www.quora.com/What-is-the-difference-between-Chinese-and-U-S-shoe-sizes
#
# disagree:
# https://tbfocus.com/size-conversion-cn-uk-us-eu-fr-intls
#
# adopted: separate nike and adidas charts


class SizerError(Exception):
    def __init__(self, message, in_code, out_code, in_size):
        super().__init__(message)
        self.in_code = in_code
        self.out_code = out_code
        self.in_size = in_size
        self.msg = message


class Sizer:
    def __init__(self):
        # adidas formatSize has fraction strings, example: CP9366
        self.adidas_eu_us_men_size_mapping = {
            "36.0": "4.0",
            "36.5": "4.5",
            "37.0": "5.0",
            "38.0": "5.5",
            "38.5": "6.0",
            "39.0": "6.5",
            "40.0": "7.0",
            "40.5": "7.5",
            "41.0": "8.0",
            "42.0": "8.5",
            "42.5": "9.0",
            "43.0": "9.5",
            "44.0": "10.0",
            "44.5": "10.5",
            "45.0": "11.0",
            "46.0": "11.5",
            "46.5": "12.0",
            "47.0": "12.5",
            "48.0": "13.0",
            "48.5": "13.5",
            "49.0": "14.0",
        }
        self.adidas_us_eu_men_size_mapping = {}

        # nike US has "Y" to the end for women
        # du would claim 575441-028 is women mapping, but stockx listed this style_id as child
        self.nike_eu_us_women_size_mapping = {
            "35.5": "3.5Y",
            "36.0": "4.0Y",
            "36.5": "4.5Y",
            "37.5": "5.0Y",
            "38.0": "5.5Y",
            "38.5": "6.0Y",
            "39.0": "6.5Y",
            "40.0": "7.0Y",
        }
        self.nike_us_eu_women_size_mapping = {}

        # du has multiple size charts for nike-women, AH7389-003 is an example different from the above
        self.nike_eu_us_women_size_mapping_2 = {}

        # an example kid shoe on du: 36634 Title: 【BP幼童】Air Jordan 1 Low ALT 低帮 黑脚趾;

        self.nike_eu_us_men_size_mapping = {
            "35.5": "3.5",
            "36.0": "4.0",
            "36.5": "4.5",
            "37.5": "5.0",
            "38.0": "5.5",
            "38.5": "6.0",
            "39.0": "6.5",
            "40.0": "7.0",
            "40.5": "7.5",
            "41.0": "8.0",
            "42.0": "8.5",
            "42.5": "9.0",
            "43.0": "9.5",
            "44.0": "10.0",
            "44.5": "10.5",
            "45.0": "11.0",
            "45.5": "11.5",
            "46.0": "12.0",
            # note the "47.0" and "46.5" duplicated entries are in du size chart for 554724-058
            "46.5": "12.5",
            "47.0": "12.5",
            "47.5": "13.0",
            "48.0": "13.5",
            "48.5": "14.0",
            # this is off the charts from du but people can buy this size. this is inferred. example 852542-301
            "49.0": "15.0",
        }
        self.nike_us_eu_men_size_mapping = {}

        # I pretty much guessed these from the adidas website as du's CQ1843 doesn't have a chart
        self.adidas_eu_us_women_size_mapping = {
            # not even adidas chart has these
            "35.0": "4.0",
            "35.5": "4.5",
            # adidas site has these
            "36.0": "5.0",
            "36.5": "5.5",
            "37.0": "6.0",
            "38.0": "6.5",
            "38.5": "7.0",
            "39.0": "7.5",
            "40.0": "8.0",
            "40.5": "8.5",
            "41.0": "9.0",
            "42.0": "9.5",
        }
        self.adidas_us_eu_women_size_mapping = {}

        if not self.adidas_us_eu_men_size_mapping:
            for key in self.adidas_eu_us_men_size_mapping:
                self.adidas_us_eu_men_size_mapping[
                    self.adidas_eu_us_men_size_mapping[key]
                ] = key
        if not self.adidas_us_eu_women_size_mapping:
            for key in self.adidas_eu_us_women_size_mapping:
                self.adidas_us_eu_women_size_mapping[
                    self.adidas_eu_us_women_size_mapping[key]
                ] = key
        if not self.nike_us_eu_men_size_mapping:
            for key in self.nike_eu_us_men_size_mapping:
                self.nike_us_eu_men_size_mapping[
                    self.nike_eu_us_men_size_mapping[key]
                ] = key
        if not self.nike_us_eu_women_size_mapping:
            for key in self.nike_eu_us_women_size_mapping:
                self.nike_us_eu_women_size_mapping[
                    self.nike_eu_us_women_size_mapping[key]
                ] = key

        return

    def get_shoe_size(self, in_size, in_code, out_code):
        try:
            if in_code == out_code:
                return in_size
            elif in_code == "eu-adidas-men":
                if out_code == "us":
                    return self.adidas_eu_us_men_size_mapping[in_size]
            elif in_code == "eu-adidas-women":
                if out_code == "us":
                    return self.adidas_eu_us_women_size_mapping[in_size]
            elif in_code == "eu-nike-women":
                if out_code == "us":
                    return self.nike_eu_us_women_size_mapping[in_size]
            elif in_code == "eu-nike-men":
                if out_code == "us":
                    return self.nike_eu_us_men_size_mapping[in_size]
            elif in_code == "us":
                if out_code == "eu-adidas-men":
                    return self.adidas_us_eu_men_size_mapping[in_size]
                elif out_code == "eu-adidas-women":
                    return self.adidas_us_eu_women_size_mapping[in_size]
                elif out_code == "eu-nike-men":
                    return self.nike_us_eu_men_size_mapping[in_size]
                elif out_code == "eu-nike-women":
                    return self.nike_us_eu_women_size_mapping[in_size]
        except KeyError as e:
            print(
                "failed to get shoe_size {} to {} size {}".format(
                    in_code, out_code, in_size
                )
            )
            raise SizerError("failed to get shoe_size", in_code, out_code, in_size)
        return None

    def infer_gender(self, size_list_float):
        # sorted by number of entries
        candidates = [
            (self.nike_eu_us_women_size_mapping, "eu-nike-women"),
            (self.adidas_eu_us_women_size_mapping, "eu-adidas-women"),
            (self.adidas_eu_us_men_size_mapping, "eu-adidas-men"),
            (self.nike_eu_us_men_size_mapping, "eu-nike-men"),
        ]

        inferred = []
        for c in candidates:
            size_list_candidate = set([float(k) for k in c[0]])
            if size_list_float.issubset(size_list_candidate):
                inferred.append(c[1])
        if len(inferred) > 1:
            # raise SizerError('failed to infer gender', inferred, len(inferred), size_list_float)
            print(
                "multiple matches: {} for {}. Going to assume the most restrictive: {}".format(
                    inferred, size_list_float, inferred[0]
                )
            )
        if len(inferred) == 0:
            raise SizerError(
                "no match to infer gender", inferred, len(inferred), size_list_float
            )
        return inferred[0]
