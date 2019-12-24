const csvParser = require('csv-parser');
const fs = require('fs');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

class LastUpdatedSerializer {
    constructor(lastUpdatedFile, minUpdateTime) {
        this.lastUpdatedFile = lastUpdatedFile;
        this.minUpdateTime = minUpdateTime;
        this.lastUpdated = {};
    }
    shouldUpdate(styleId) {
        if (this.minUpdateTime === undefined || this.lastUpdated[styleId] === undefined) {
            return true;
        } else {
            return (this.lastUpdated[styleId] - new Date()) / 1000 > this.minUpdateTime;
        }
    }
    updateLastUpdated(styleId) {
        this.lastUpdated[styleId] = new Date();
        return;
    }
    dumps() {
        const csvWriter = createCsvWriter({
            path: this.lastUpdatedFile,
            header: [
                {id: 'styleId', title: 'style_id'},
                {id: 'lastUpdated', title: 'stockx_last_updated'}
            ]
        });
        let records = [];
        for (let key in this.lastUpdated) {
            records.push({
                styleId: key,
                lastUpdated: this.lastUpdated[key].toISOString()
            });
        }
        csvWriter.writeRecords(records)
            .then(() => {
                console.log('Done dumping last updated to ' + this.lastUpdatedFile);
            });
        return;
    }
    loads(callback) {
        if (fs.existsSync(this.lastUpdatedFile)) {
            fs.createReadStream(this.lastUpdatedFile)
                .pipe(csvParser())
                .on('data', (data) => {
                    this.lastUpdated[data['style_id']] = new Date(Date.parse(data['stockx_last_updated']));
                })
                .on('end', () => {
                    callback();
                });
            return;
        } else {
            callback();
        }
    }
}

module.exports = LastUpdatedSerializer;
