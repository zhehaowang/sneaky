#!/usr/bin/env python3

import csv
import argparse

"""
Given multiple csvfile sources, inner join them on style id and write the result
"""


def sanitize_style_id(style_id):
    return style_id.upper()


def parse_file(filename, style_id_key):
    result = {}
    with open(filename, "r") as infile:
        rr = csv.DictReader(infile, delimiter=",")
        for row in rr:
            result[sanitize_style_id(row[style_id_key])] = row
    return result


def infer_source(name):
    if "du" in name:
        return "du"
    elif "stockx" in name:
        return "stockx"
    else:
        return ""


def source_to_style_id_key(source):
    return "style_id"


def merge_csvs(csvs, outfile_name, populate_no_match):
    if populate_no_match:
        raise RuntimeError("not implemented")

    results = []
    keys = None
    for f in csvs:
        entries = parse_file(f, source_to_style_id_key(infer_source(f)))
        results.append(entries)
        set_keys = set(entries.keys())
        if not keys:
            keys = set_keys
        else:
            in_both = keys.intersection(set_keys)
            print(
                "dropping {} keys in {} not present in current intersection".format(
                    len(set_keys - in_both), f
                )
            )
            print(
                "dropping {} keys in current intersection".format(len(keys - in_both))
            )
            keys = in_both

    merged = {}
    fieldnames = {}

    for style_id in keys:
        for r in results:
            if style_id not in merged:
                merged[style_id] = {"sanitized_style_id": style_id}
            for k in r[style_id]:
                merged[style_id][k] = r[style_id][k]
                fieldnames[k] = True

    fieldnames["sanitized_style_id"] = True

    with open(outfile_name, "w") as outfile:
        wr = csv.DictWriter(outfile, delimiter=",", fieldnames=fieldnames.keys())
        wr.writeheader()
        for style_id in keys:
            wr.writerow(merged[style_id])

    print("write {} merged result to {}".format(len(keys), outfile_name))
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        """
        merge static csvs generated from different sources.

        example usage:
          ./csv_merge.py --output result stockx.mapping.2019-12-21T18:58:50.487Z.csv du.mapping.20191206-211125.csv
    """
    )
    parser.add_argument("files", nargs="*")
    # TODO: we should revise this when at least two out of three sources is supported
    parser.add_argument(
        "--populate_no_match",
        action="store_true",
        help=(
            "fill in entry in result csv even if one input doesn't have entry matching style_id"
        ),
    )
    parser.add_argument("--output", help=("output csv file name"))

    args = parser.parse_args()
    if len(args.files) < 2:
        print("specify at least two csvs to merge from")
        exit(1)

    outfile_name = "merged.csv"
    if args.output:
        outfile_name = args.output
    merge_csvs(args.files, outfile_name, args.populate_no_match == True)
