import scrapy
from scrapy.selector import Selector
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher

import re
import json
from copy import deepcopy

class FlightClubSpider(scrapy.Spider):
    name = ""
    def __init__(self):
        self.url_base = "https://www.flightclub.com/"

    def start_requests(self):
        page = "air-jordans"
        yield Request(url = self.url_base + page, callback = self.parse)

    def parse(self, response):
        selector = Selector(response)
        content_table = selector.xpath("//li").extract()
        for item in content_table:
            print(item)
        # for item in content_table:
        #     if item.startswith("./"):
        #         item = item[2:]
        #     url = self.url_base + item
        #     # note the lambda capture to not bind url_item to the outer scope
            yield Request(url, callback = lambda response, url_item = item.split('=')[1]: self.parse_checkee_table(response, url_item))

    def parse_checkee_table(self, response, url_item):
        selector = Selector(response)
        content_table = selector.xpath("//table[@align='center']//tr").extract()
        entries = []
        for entry in content_table:
            if "personal_detail.php" in entry:
                """
                <tr align="center" bgcolor="#00FF00">
                    <td><a href="./update.php?casenum=816587">Update</a></td>
                    <td>201803</td>
                    <td>B1</td>
                    <td>Renewal</td>
                    <td>ShangHai</td>
                    <td>N/A</td>
                    <td>Clear</td>
                    <td>2018-01-02</td>
                    <td>2018-01-26</td>
                    <td>24</td>
                    <td><a href="./personal_detail.php?casenum=816587" target="_blank"
                           title="Case Created:\t29-Dec-2017\r\n
                                  Case first Updated:\t02-Jan-2018\r\n
                                  Case 2nd updated: 25-Jan-2018\r\nIssued
                                  3rd updated: 26-Jan-2018\r\n">detail</a> <img src="notes.png" align="top"></td>
                </tr>
                """
                # lookahead alternative: r'<td>((?!</td>).*?)</td>'
                trs = re.findall(r'<td>([^<]*?)</td>', entry)
                if len(trs) == 9:
                    info = {
                        "visa":          trs[1],
                        "type":          trs[2],
                        "loc":           trs[3],
                        "major":         trs[4],
                        "status":        trs[5],
                        "check_date":    trs[6],
                        "complete_date": trs[7],
                        "waiting_days":  trs[8]
                    }
                    entries.append(info)
                elif len(trs) > 6 and len(trs) < 12:
                    print("potential re match error: " + len(trs) + ": " + entry)
                else:
                    pass
        with open('./data/' + url_item + '.txt', 'w') as result_file:
            result_file.write(json.dumps(entries))
