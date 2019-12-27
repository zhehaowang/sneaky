#!/usr/bin/env bash

outfile="stockx.20191225.csv"

while read p; do
  echo "$p"
  awk 'NR>1' "$p" >> "$outfile"
  
done < "worklog"
