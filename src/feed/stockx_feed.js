#!/usr/bin/env node

const stockxAPI = require('stockx-api');
const stockX = new stockxAPI();

const fs = require('fs');
const csvParser = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

function setupArgs() {
    var ArgumentParser = require('argparse').ArgumentParser;
    var parser = new ArgumentParser({
        version: '1.0.0',
        addHelp: true,
        description: 'entry point for stockx feed'
    });
    parser.addArgument(['-m', '--mode'], {
        help: '[query|update] query builds the static mapping file, update takes a mapping and updates entries',
        required: true
    });
    parser.addArgument(['-k', '--kw'], {
        help: 'in query mode, the query keyword'
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
    var content = fs.readFileSync(credentialsFile);
    var cred = JSON.parse(content);

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
            await logIn('../../credentials/credentials.json');

            const resultsPerPage = 20;
            const productList = await stockX.searchProducts(args.kw, {
                limit: parseInt(args.pages) * resultsPerPage
            });

            let resultList = [];
            if (args.start_from) {
                throw new Error("args.start_from should not be provided in query mode: each query is a full refresh")
            }

            const productArray = productList.map(product => {
                return {
                    gender: product.gender,
                    urlKey: product.urlKey,
                    colorWay: product.colorWay,
                    name: product.name,
                    title: product.title,
                    retail: product.retail,
                    uuid: product.uuid,
                    pid: product.pid,
                    styleId: product.styleId
                }});

            let currentTime = new Date(new Date().getTime()).toISOString();
            let csvFilePath = "stockx.mapping." + currentTime + ".csv"
            const csvWriter = createCsvWriter({
                path: csvFilePath,
                header: [
                    {id: 'gender', title: 'stockx_gender'},
                    {id: 'urlKey', title: 'stockx_url_key'},
                    {id: 'colorWay', title: 'stockx_color_way'},
                    {id: 'name', title: 'stockx_name'},
                    {id: 'title', title: 'stockx_title'},
                    {id: 'retail', title: 'stockx_retail_price'},
                    {id: 'uuid', title: 'stockx_uuid'},
                    {id: 'pid', title: 'stockx_pid'},
                    {id: 'styleId', title: 'stockx_style_id'},
                ]
            });
             
            csvWriter.writeRecords(productArray)
                .then(() => {
                    console.log('Done writing query result to ' + csvFilePath);
                });
        } else if (args.mode == 'update') {

        } else {
            throw new Error("unrecognized mode " + args.mode);
        }

        //Returns an array of products

        // console.log(productList);

        //Fetch variants and product details of the first product
        // const product = await stockX.fetchProductDetails(productList[0]);

        // console.log(product);

        // console.log('Placing an ask for ' + product.name);

        // //Places an ask on that product
        // const ask = await stockX.placeAsk(product, {
        //     amount: 5000000000, 
        //     size: '9.5'
        // });

        // console.log('Successfully placed an ask for $5000 for ' + product.name);

        // //Updates the previous ask
        // await stockX.updateAsk(ask, {
        //     amount: 600000
        // });

        // console.log('Updated previous ask!');
    }
    catch (e) {
        console.log('Error: ' + e.message);
    }
})();
