# Sneaky

Can we make money by buying sneakers low on one platform and selling high on another?

**Sneaky** is a prototype with multi-venue feed, price-margin-based strategy and history / volume / volatility analytics tooling for trading sneakers on consignment stores and exchanges.

Sneaky系统从多个平台 (毒app，StockX) 抓取球鞋价格数据、存储，并决定哪些款式有合适的价差、volatility、volume，提供倒卖建议。

### What to expect

* Feed
  * Scrapes venues for current price listing and historical transactions.
  * Three main modes of operation:
    * Query: given search terms, scrape models on a venue, record static information (e.g. style ID, title, release date, product ID / URL query key on the venue, __feed/static_info_serializer.py__).
    * Update: given static info produced by query, dump current price readings and transactions since the last update to local file system (__feed/time_series_serializer.py__).
    * Study: given style ID and size, query a venue for current listing prices and historical transactions data.
  * Venues:
    * Du (__feed/du_feed.py__, fully implemented): scrapes Du WeChat app for product detail and transaction history.
    * StockX (__feed/stockx_feed.js__, fully implemented): scrapes StockX (web service) for current best bid and offer.
    * Flightclub (__flightclub/__, on v1): scrapy-based crawler to parse sell prices from FlightClub webpage.
    * Goat (not implemented).
    * Ebay (not pursued, low match rate and lack of authenticity guarantee would greatly hurt automation).
* Strategy
  * Given time series data feed produced and a configurable set of options, print the most lucrative models for purchase (__strategy/strategy.py__).
* Analytics
  * Given time series data and a model, print stats or plot historical transactions (__feed/du_analyzer.py__).

* Model of operation
  * Run query every month / year to account for new releases and potential changes in (StyleID, platform-specific ID) map.
  * After scraping static info from multiple venues, run a join to produce items for which we have data on multiple venues (__feed/csv_merge.py__)
  * Run update every day to produce a sample of today's prices and record transactions since yesterday.
  * Run strategy whenever you want to see its recommendations based off of currently recorded readings.
  * Before making a purchase, run analytics to double check its volume, volatility and historical transaction prices.

### How to run

* Dependencies
* Credentials
* Feed
```sh
# Du product details => du.mapping.{now}.csv
./du_feed.py --mode query --kw ../stockx/query_kw.txt --pages 20

# StockX product details => stockx.mapping.{now}.csv
# This is recommended to circumvent an antibot mechanism enforced by StockX
./stockx_query.sh

# Merge
./csv_merge.py --output merged.20191225.csv stockx.20191225.csv du.mapping.20191221-150959.csv 

# Du current listing and historical transactions => data/{model}/{size}.json
./du_feed.py --mode update --start_from merged.20191225.csv --transaction_history_date 20190801 --transaction_history_maxpage 20 --min_interval_seconds 3600

# StockX current listing and historical transactions => data/{model}/{size}.json
# This is recommended to circumvent an anti-bot mechanism enforced by StockX
./stockx_update.sh merged.20191225.csv
```
* Strategy
```sh
# Time series price/transaction data data/{model}/{size}.json => recommendations
./strategy.py --start_from ../feed/merged.20191225.csv
```
* Analytics
```sh
# plot Du historical transaction prices
./du_analyzer.py --style_id 881426-009 --size 7.0 --mode plot

# product Du historical transaction statistics
./du_analyzer.py --style_id 881426-009 --size 7.0 --mode stats
```

### Sample outputs

Strategy prints its recommendation and key stats.
```
310810-022 8.0 41.0
air-jordan-13-retro-low-chutney , Air Jordan 13 Retro Low Chutney
Release date:           2017-06-10 23:59:59
  du listing price:     2009.00 CNY 287.17 USD
  du transaction price: 2009.00 CNY 287.17 USD
  du transaction time:  2019-12-25T03:20:56.453461Z
  stockx bid:           147.00 USD
  stockx ask:           160.00 USD
  stockx annual high:   188.00 USD
  stockx annual low:    111.00 USD
  stockx volatility:    0.11
  stockx sale last 72h: 0
  profit ratio (bid to last): 37.68 %
  profit value (bid to last): 66.30 USD
  profit ratio (mid to last): 32.77 %
  profit value (mid to last): 59.80 USD
  profit ratio (ask to last): 28.21 %
  profit value (ask to last): 53.30 USD
  Du Transactions:
    First Date:       2019-08-03T03:21:02.509691
    Number of Sales:  8
    Sales / Day:      0.06
    High:             2019.00 CNY 288.60 USD
    Low:              1259.00 CNY 179.96 USD
    First:            1469.00 CNY 209.98 USD
    Last:             2009.00 CNY 287.17 USD
    Average:          1691.50 CNY 241.78 USD
    Stdev:            273.30 CNY 39.07 USD
  Plot command: ./du_analyzer.py --style_id 310810-022 --size 8.0 --mode plot
...
```

Analytics produce stats and historical transaction prices plot.

![Historical transaction prices](src/feed/BQ6623-800.9.5.png)

### Lessons, progress, and TODO

Tracked in [issues](https://github.com/zhehaowang/sneaky/issues).
Some interesting items:
* [My take on the venue du](https://github.com/zhehaowang/sneaky/issues/55)
* [Post-mortem on one item we bought](https://github.com/zhehaowang/sneaky/issues/54)
* [Engineering realizations](https://github.com/zhehaowang/sneaky/issues/56)

### [Playbook](docs/playbook.md)

### License: GNU General Public License v3.0

### Credits

* [Unofficial NodeJS stockx API](https://github.com/matthew1232/stockx-api)
* [Du app sign mechanism](https://github.com/luo1994/du-app-sign)

### Contact

Zhehao Wang wangzhehao410305@gmail.com