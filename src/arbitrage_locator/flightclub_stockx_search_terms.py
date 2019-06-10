#!/usr/bin/env python3

import os
import re
import sys
import json

import pprint
pp = pprint.PrettyPrinter()

def read_files(infile1, infile2):
    # infile1: flightclub
    # infile2: stockx, with last 72 hours sale
    with open(infile1, "r") as in1:
        with open(infile2, "r") as in2:
            content1 = json.loads(in1.read())
            content2 = json.loads(in2.read())
    return content1, content2

def find_match(content1, content2):
    blacklist_words = ['kid', 'infant']

    in1_namelist = {}
    in2_namelist = {}

    for key in content1:
        parts = key.split('--')
        if len(parts) != 3:
            print("unexpected brand -- name -- size {}".format(key))
        brand = parts[0].strip()
        name = parts[1].strip().replace('"', '')
        size = parts[2].strip()
        in1_namelist["{} {}".format(brand, name)] = True

    for key in content2:
        parts = key.split('--')
        if len(parts) != 2:
            print("unexpected shoe -- size name {}".format(key))
            continue
        name = parts[0].strip()
        size = parts[1].strip()
        in2_namelist[name] = True

    in1_names = sorted(in1_namelist.keys())
    in2_names = sorted(in2_namelist.keys())

    # pp.pprint(in1_names)
    pp.pprint(in2_names)

    in1_names_sorted = [[set(x.split()), x] for x in in1_names]
    in2_names_sorted = [[set(x.split()), x] for x in in2_names]

    one_to_two = {}
    two_to_one = {}

    for name1 in in1_names_sorted:
        for name2 in in2_names_sorted:
            if name1[0] == name2[0]:
                print("found a match: {}".format(name1[0]))
                one_to_two[name1[1]] = name2[1]
                two_to_one[name2[1]] = name1[1]
            elif name1[0].issubset(name2[0]) or name2[0].issubset(name1[0]):
                match_failed = False
                diff = set.union(name1[0] - name2[0], name2[0] - name1[0])
                for word in blacklist_words:
                    for d in diff:
                        if word in d.lower():
                            match_failed = True
                            break
                if not match_failed:
                    print("found a match: flightclub {} stockx {}".format(name1[0], name2[0]))
                    one_to_two[name1[1]] = name2[1]
                    two_to_one[name2[1]] = name1[1]
            else:
                common_words = set.intersection(name1[0], name2[0])
                if len(common_words) >= 4:
                    print("found this similar looking but not too sure:\n  flightclub {}\n  stockx     {}".format(name1[1], name2[1]))

    return one_to_two, two_to_one

def find_stockx_search_terms(content1):
    content_copy = {}
    for key in content1.keys():
        parts = key.split('--')
        if len(parts) != 3:
            print("unexpected brand -- name -- size {}".format(key))
        sanitized = parts[1].strip().replace('"', '').lower()
        if not sanitized in content_copy:
            content_copy[sanitized] = [{"fc_px": content1[key]["px"], "fc_size": parts[2], "fc_url": content1[key]["url"]}]
        else:
            content_copy[sanitized].append({"fc_px": content1[key]["px"], "fc_size": parts[2], "fc_url": content1[key]["url"]})

    search_terms = {}
    keys = list(content_copy.keys())
    for i in range(len(keys)):
        to_add = True
        for j in range(len(keys)):
            if i == j:
                continue
            elif keys[i] in keys[j]:
                print("\"{}\" is a substring of \"{}\" and presumably less specific. dropping \"{}\" as search term".format(keys[i], keys[j], keys[i]))
                to_add = False
                break
        if to_add:
            search_terms[keys[i]] = content_copy[keys[i]]

    return search_terms

if __name__ == "__main__":
    content1, content2 = read_files("flightclub.20190608.txt", "stockx.20190608.txt")
    # match rate with this is too low
    # mapping1, mapping2 = find_match(content1, content2)

    # print(mapping1)
    # print(mapping2)
    search_terms = find_stockx_search_terms(content1)
    pp.pprint(search_terms)
    with open("fc_by_search_terms.txt", "w") as wfile:
        wfile.write(json.dumps(search_terms, indent=4, sort_keys=True))
    with open("stockx_search_terms.txt", "w") as wfile:
        for key in search_terms.keys():
            wfile.write(key + '\n')
