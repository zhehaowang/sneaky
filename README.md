# Sneaky

Feed and strategy for secondary markets for sneakers.

### Strategy

##### stockx

* [stockxapi](https://pypi.org/project/stockx-py-sdk/)
* Search term --> product ID
* product ID --> current book, past sales, transaction history
* Book builder (per `<shoe model, size>` of given product ID)
* arbitrary throttling

##### flightclub

* scrapy full site scrape
* model, size --> sell price
* sell page: style id to sell item id, sell price

##### ebay

* scrapy search-term based scrape
* html page (size, price) scrape
* data deemed too low quality and high chance of subquality item to be of use

##### du

### strategies

##### matching

* name subset based match
* reverse search term query: one <-> one result item means a match
* style ID based match

##### strategies

* market making on stockx
  * widest spread items have very low profit rate and long turn-around time: widest spread is about commission rate of the platform
  * large volatility, low volume, low liquidity
* arbitrage between stockx and flightclub
