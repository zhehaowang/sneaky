const fs = require('fs');

class TimeSeriesSerializer {
    constructor() {
        this.venue = "stockx";
    }

    findPath(styleId, size) {
        return "../data/" + styleId + "/" + size + ".json"
    }

    update(updateTime, styleId, sizePrices, sizeTransactions) {
        
        return;
    }
}

module.exports = TimeSeriesSerializer;
