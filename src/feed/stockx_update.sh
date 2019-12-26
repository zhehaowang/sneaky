#!/usr/bin/env bash

# ./stockx_update.sh merged.csv wraps around daily stockx update in several runs
# to circumvent 403

if [ "$#" -ne 1 ]; then
  echo "Expect one csv argument to update from. Usage: ./stockx_update.sh merged.csv" >&2
  exit 1
fi

limit=50
number_lines=$(wc -l "$1" | tr -s ' ' | cut -d' ' -f 2)
number_iterations=$((number_lines / limit))
((++number_iterations))

for i in $(seq 1 $number_iterations); do
    cmd="./stockx_feed.js -m update --start_from \"$1\" --min_interval_seconds 86400 --limit 50"
    echo "$cmd"
    # $cmd
    ./stockx_feed.js -m update --start_from "$1" --min_interval_seconds 86400 --limit 50
    sleep 60
done
