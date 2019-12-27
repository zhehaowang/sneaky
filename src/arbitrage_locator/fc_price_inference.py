#!/usr/bin/env python3

import os
import re
import sys
import json
import csv

import pprint
import datetime
import numpy as np

pp = pprint.PrettyPrinter()

def fc_price_inference(fc_prices, sizes_list):
    benchmark = '9.0'
    significance_threshold = 20

    all_multipliers = []
    for style_id in fc_prices:
        if benchmark in fc_prices[style_id]:
            multipliers = []
            for size in sizes_list:
                if size in fc_prices[style_id]:
                    multipliers.append(
                        "{:.2f}".format(
                            float(fc_prices[style_id][size]['px'].replace(',', '')) / float(fc_prices[style_id][benchmark]['px'].replace(',', ''))))
                else:
                    multipliers.append('None')
            # print(', '.join(multipliers))
            all_multipliers.append(list(multipliers))

    for idx in range(len(sizes_list)):
        filtered = [x[idx] for x in all_multipliers if x[idx] != 'None']
        filtered = [float(x) for x in filtered]
        if len(filtered) > significance_threshold:
            filtered_np = np.array(filtered)
            print('size {} multiplier (sample: {})\n  stdev          {}\n  mean'
                '           {}\n  25-percentile  {}\n  median         {}\n'
                '  75-percentile  {}\n'.format(
                sizes_list[idx],
                len(filtered),
                np.std(filtered_np),
                np.mean(filtered_np),
                np.percentile(filtered_np, 25),
                np.percentile(filtered_np, 50),
                np.percentile(filtered_np, 75)))
    return

if __name__ == "__main__":
    fc_file = "flightclub.20190614.txt"
    sizes_list = [
        '3.5', '4.0', '4.5', '5.0', '5.5', '6.0', '6.5', '7.0', '7.5', '8.0',
        '8.5', '9.0', '9.5', '10', '10.5', '11', '11.5', '12', '12.5', '13',
        '13.5', '14', '14.5', '15', '16', '17']

    with open(fc_file, "r") as rfile:
        fc_prices = json.loads(rfile.read())
    fc_price_inference(fc_prices, sizes_list)