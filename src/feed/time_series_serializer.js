const fs = require('fs');
const path = require('path');
let shell = require('shelljs');

class TimeSeriesSerializer {
    constructor() {
        this.venue = "stockx";
    }

    findPath(styleId, size) {
        return "../data/" + styleId + "/" + size + ".json"
    }

    update(updateTime, styleId, sizePrices) {
        for (let size in sizePrices) {
            let outfile = this.findPath(styleId, size);
            let data = {};
            if (fs.existsSync(outfile)) {
                data = JSON.parse(fs.readFileSync(outfile));
                console.log(outfile + " exists, updating");
            } else {
                let dirname = path.dirname(outfile);
                if (!fs.existsSync(dirname)) {
                    shell.mkdir('-p', dirname);
                }
            }
            if (data[this.venue] === undefined) {
                data[this.venue] = {
                    prices: [],
                    transactions: []
                }
            }

            data[this.venue].prices.push({
                time: updateTime.toISOString(),
                bid_price: sizePrices[size]["bestBid"],
                ask_price: sizePrices[size]["bestAsk"],
                annual_high: sizePrices[size]["annualHigh"],
                annual_low: sizePrices[size]["annualLow"],
                volatility: sizePrices[size]["volatility"],
                sale_72_hours: sizePrices[size]["salesLast72Hours"],
                number_asks: sizePrices[size]["numberOfAsks"],
                number_bids: sizePrices[size]["numberOfBids"]
            })

            fs.writeFileSync(outfile, JSON.stringify(data));
        }
    }
}

module.exports = TimeSeriesSerializer;
