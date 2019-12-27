#!/usr/bin/env bash

# ./stockx_update.sh merged.csv wraps around static info query to circumvent 403
# copy stdout csv files to worklog and run them through combine_csv.sh, copy
# header back

while read p; do
  echo "$p"
  ./stockx_feed.js -m query --kw "$p" --pages 10
  sleep 60
done < "../stockx/query_kw.txt"
