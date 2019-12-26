# agree
# http://www.shoesizes.co/
# https://www.quora.com/What-is-the-difference-between-Chinese-and-U-S-shoe-sizes
# 
# disagree:
# https://tbfocus.com/size-conversion-cn-uk-us-eu-fr-intls
# 
# adopted: separate nike and adidas charts
def get_shoe_size(in_size, in_code, out_code):
    adidas_eu_us_men_size_mapping = {
        "36.0":  "4.0",
        "36.5":  "4.5",
        "37.0":  "5.0",
        "38.0":  "5.5",
        "38.5":  "6.0",
        "39.0":  "6.5",
        "40.0":  "7.0",
        "40.5":  "7.5",
        "41.0":  "8.0",
        "42.0":  "8.5",
        "42.5":  "9.0",
        "43.0":  "9.5",
        "44.0":  "10.0",
        "44.5":  "10.5",
        "45.0":  "11.0",
        "46.0":  "11.5",
        "46.5":  "12.0",
        "47.0":  "12.5",
        "48.0":  "13.0",
        "48.5":  "13.5",
        "49.0":  "14.0"
    }
    adidas_us_eu_men_size_mapping = {}

    # nike US has "Y" to the end for women
    # du would claim 575441-028 is women mapping, but stockx listed this style_id as child
    nike_eu_us_women_size_mapping = {
        "35.5":  "3.5Y",
        "36.0":  "4.0Y",
        "36.5":  "4.5Y",
        "37.5":  "5.0Y",
        "38.0":  "5.5Y",
        "38.5":  "6.0Y",
        "39.0":  "6.5Y",
        "40.0":  "7.0Y"
    }
    nike_us_eu_women_size_mapping = {}

    # du has multiple size charts for nike-women, AH7389-003 is an example different from the above
    nike_eu_us_women_size_mapping_2 = {}

    # an example kid shoe on du: 36634 Title: 【BP幼童】Air Jordan 1 Low ALT 低帮 黑脚趾;
    
    nike_eu_us_men_size_mapping = {
        "35.5":  "3.5",
        "36.0":  "4.0",
        "36.5":  "4.5",
        "37.5":  "5.0",
        "38.0":  "5.5",
        "38.5":  "6.0",
        "39.0":  "6.5",
        "40.0":  "7.0",
        "40.5":  "7.5",
        "41.0":  "8.0",
        "42.0":  "8.5",
        "42.5":  "9.0",
        "43.0":  "9.5",
        "44.0":  "10.0",
        "44.5":  "10.5",
        "45.0":  "11.0",
        "45.5":  "11.5",
        "46.0":  "12.0",
        # note the "47.0" and "46.5" duplicated entries are in du size chart for 554724-058
        "46.5":  "12.5",
        "47.0":  "12.5",
        "47.5":  "13.0",
        "48.0":  "13.5",
        "48.5":  "14.0"
    }
    nike_us_eu_men_size_mapping = {}

    adidas_eu_us_women_size_mapping = {

    }
    adidas_us_eu_women_size_mapping = {}

    if not adidas_us_eu_men_size_mapping:
        for key in adidas_eu_us_men_size_mapping:
            adidas_us_eu_men_size_mapping[adidas_eu_us_men_size_mapping[key]] = key
    if not adidas_us_eu_women_size_mapping:
        for key in adidas_eu_us_women_size_mapping:
            adidas_us_eu_women_size_mapping[adidas_eu_us_women_size_mapping[key]] = key
    if not nike_us_eu_men_size_mapping:
        for key in nike_eu_us_men_size_mapping:
            nike_us_eu_men_size_mapping[nike_eu_us_men_size_mapping[key]] = key
    if not nike_us_eu_women_size_mapping:
        for key in nike_eu_us_women_size_mapping:
            nike_us_eu_women_size_mapping[nike_eu_us_women_size_mapping[key]] = key

    try:
        if in_code == out_code:
            return in_size
        elif in_code == 'eu-adidas-men':
            if out_code == 'us':
                return adidas_eu_us_men_size_mapping[in_size]
        # elif in_code == 'eu-adidas-women':
        #     if out_code == 'us':
        #         return adidas_eu_us_women_size_mapping[in_size]
        elif in_code == 'eu-nike-women':
            if out_code == 'us':
                return nike_eu_us_women_size_mapping[in_size]
        elif in_code == 'eu-nike-men':
            if out_code == 'us':
                return nike_eu_us_men_size_mapping[in_size]
    except KeyError as e:
        print('failed to get shoe_size {} to {} size {}'.format(in_code, out_code, in_size))
    return None

def has_women_only_adidas_size(sizes):
    return False