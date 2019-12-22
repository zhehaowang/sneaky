#!/usr/bin/env node

const stockxAPI = require('stockx-api');
const stockX = new stockxAPI();

const fs = require('fs');

const LastUpdatedSerializer = require('./last_updated.js');
const StaticInfoSerializer = require('./static_info_serializer.js');
const TimeSeriesSerializer = require('./time_series_serializer.js');

function setupArgs() {
    var ArgumentParser = require('argparse').ArgumentParser;
    var parser = new ArgumentParser({
        version: '1.0.0',
        addHelp: true,
        description: 'entry point for stockx feed.\nExample usage:\n' +
            './stockx_feed.js -m query --kw ../stockx/query_kw.txt --pages 5\n'
    });
    parser.addArgument(['-m', '--mode'], {
        help: '[query|update] query builds the static mapping file, update takes a mapping and updates entries',
        required: true
    });
    parser.addArgument(['-k', '--kw'], {
        help: 'in query mode, a query keyword file, or the query keyword separated by comma'
    });
    parser.addArgument(['-s', '--start_from'], {
        help: 'in query mode, continue from entries not already populated in given\n' +
            'in update mode, the file from which to load the product_id, style_id mapping'
    });
    parser.addArgument(['-n', '--pages'], {
        help: 'in query mode, the number of pages to query'
    });
    parser.addArgument(['-l', '--last_updated'], {
        help: 'in update mode, the file containing the last_updated time of each item'
    });
    parser.addArgument(['-i', '--min_interval_seconds'], {
        help: 'in update mode, only items whose last update time is at least this much from now will get updated'
    });

    return parser.parseArgs();
}

async function logIn(credentialsFile) {
    let content = fs.readFileSync(credentialsFile);
    let cred = JSON.parse(content);

    console.log('Logging in...');

    //Logs in using account email and password
    if (cred['stockx'][0]['username'] === undefined) {
        throw new Error("unexpected credentials file");
    }

    await stockX.login({
        user: cred['stockx'][0]['username'],
        password: cred['stockx'][0]['password']
    });

    console.log('Successfully logged in as ' + cred['stockx'][0]['username']);
}

async function queryByKeyword(keyword, pages, seenStyleIds) {
    if (keyword === "") {
        return [];
    }
    const resultsPerPage = 20;
    const productList = await stockX.searchProducts(keyword, {
        limit: pages * resultsPerPage
    });

    if (seenStyleIds === undefined) {
        seenStyleIds = {};
    }
    let productArray = productList.filter(product => !(product.styleId in seenStyleIds));
    productArray = productArray.map(product => {
        seenStyleIds[product.styleId] = true;
        return {
            gender: product.gender,
            urlKey: product.urlKey,
            colorWay: product.colorWay,
            name: product.name,
            title: product.title,
            retail: product.retail,
            uuid: product.uuid,
            pid: product.pid,
            styleId: product.styleId,
            releaseDate: product.releaseDate
        }});
    
    console.log('query ' + keyword + ' returned ' + productList.length + ' items');
    return productArray;
}

function parseProduct(product) {
    let variants = product["variants"];
    let sizePrices = {};

    for (v in variants) {
        let variant = variants[v];
        let size = variant["size"];
        let mktData = variant["market"];

        sizePrices[size] = {
            bestAsk: mktData["lowestAsk"],
            bestBid: mktData["highestBid"],
            annualHigh: mktData["annualHigh"],
            annualLow: mktData["annualLow"],
            volatility: mktData["volatility"],
            lastSale72Hours: mktData["salesLast72Hours"],
            numberAsks: mktData["numberOfAsks"],
            numberBids: mktData["numberOfBids"]
        }
    }

    return sizePrices;
}

(async () => {
    try {
        var args = setupArgs();

        if (args.mode == 'query') {
            if (!args.kw) {
                throw new Error("args.kw is mandatory in query mode");
            }
            if (!args.pages) {
                throw new Error("args.pages is mandatory in query mode");
            }
            if (args.start_from) {
                throw new Error("args.start_from should not be provided in query mode: each query is a full refresh")
            }
            await logIn('../../credentials/credentials.json');

            let keywordsList = [];
            if (fs.existsSync(args.kw)) {
                // reading args.kw arg from file
                let content = fs.readFileSync(args.kw, "utf8");
                keywordsList = content.split('\n');
            } else {
                // parsing args.kw arg from cmdline
                keywordsList = args.kw.split(',');
            }
            
            let productArray = [];
            let seenStyleIds = {};
            for (let i in keywordsList) {
                let products = await queryByKeyword(keywordsList[i], parseInt(args.pages), seenStyleIds);
                productArray = productArray.concat(products);
            }
            
            console.log("found " + productArray.length + " unique items from query " + keywordsList.join());

            let currentTime = new Date().toISOString();
            let csvFilePath = "stockx.mapping." + currentTime + ".csv"

            let staticInfoSerializer = new StaticInfoSerializer();
            staticInfoSerializer.dumpStaticInfoToCsv(productArray, csvFilePath);
        } else if (args.mode == 'update') {
            if (!args.start_from) {
                throw new Error("args.start_from is mandatory in update mode");
            }

            await logIn('../../credentials/credentials.json');

            let staticInfoSerializer = new StaticInfoSerializer();
            let timeSeriesSerializer = new TimeSeriesSerializer();

            staticInfoSerializer.loadStaticInfoFromCsv(args.start_from, async (staticInfo) => {
                let lastUpdatedFile = "last_updated_stockx.log";
                if (args.last_updated) {
                    lastUpdatedFile = args.last_updated;
                }
                
                let lastUpdated = new LastUpdatedSerializer(lastUpdatedFile, args.min_interval_seconds);
                lastUpdated.loads();
                
                const urlEndPoint = "https://stockx.com/";

                let count = 0;
                for (let key in staticInfo) {
                    console.log(urlEndPoint + staticInfo[key].urlKey);
                    await stockX.fetchProductDetails(urlEndPoint + staticInfo[key].urlKey)
                        .then(((styleId) => {
                            return p => {
                                let sizePrices = parseProduct(p);
                                count += 1;
                                timeSeriesSerializer.update(new Date(), styleId, sizePrices);
                                console.log("finished updating " + styleId);
                            };
                        })(key))
                        .catch(err => {
                            console.log(`Error scraping product details: ${err.message}`);
                        });
                }
                console.log("finished updating " + count + " items");
            });
        } else {
            throw new Error("unrecognized mode " + args.mode);
        }
    }
    catch (e) {
        console.log('Error: ' + e.message);
    }
})();
