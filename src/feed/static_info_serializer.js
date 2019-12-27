const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const csvParser = require('csv-parser');
const fs = require('fs');

class StaticInfoSerializer {
    constructor() {
        
    }

    dumpStaticInfoToCsv(productArray, fileName) {
        const csvWriter = createCsvWriter({
            path: fileName,
            header: [
                {id: 'gender', title: 'stockx_gender'},
                {id: 'urlKey', title: 'stockx_url_key'},
                {id: 'colorWay', title: 'stockx_color_way'},
                {id: 'name', title: 'stockx_name'},
                {id: 'title', title: 'stockx_title'},
                {id: 'retail', title: 'stockx_retail_price'},
                {id: 'uuid', title: 'stockx_uuid'},
                {id: 'pid', title: 'stockx_pid'},
                {id: 'styleId', title: 'style_id'},
                {id: 'releaseDate', title: 'stockx_release_date'}
            ]
        });
         
        csvWriter.writeRecords(productArray)
            .then(() => {
                console.log('Done writing query result to ' + fileName);
            });
        return;
    }

    loadStaticInfoFromCsv(fileName, callback) {
        if (fs.existsSync(fileName)) {
            let result = {};
            console.log(fileName);
            fs.createReadStream(fileName)
                .pipe(csvParser())
                .on('data', (data) => {
                    result[data['style_id']] = {
                        gender: data['stockx_gender'],
                        urlKey: data['stockx_url_key'],

                        colorWay: data['stockx_color_way'],
                        name: data['title'],
                        title: data['stockx_title'],
                        retail: data['stockx_retail_price'],
                        uuid: data['stockx_uuid'],
                        pid: data['stockx_pid'],
                        styleId: data['style_id'],
                        releaseDate: data['stockx_release_date']
                    };
                })
                .on('end', () => { callback(result); });
        }
    }
}

module.exports = StaticInfoSerializer;
