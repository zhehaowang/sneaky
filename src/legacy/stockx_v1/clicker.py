#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

import time
import urllib.request

class Query():
    url = 'https://stockx.com'

    def send_query(self):
        driver = webdriver.Chrome()
        driver.get(Query.url)

        el=driver.find_elements_by_xpath("//div[contains(@class, 'g-recaptcha')]")[0]

        action = webdriver.common.action_chains.ActionChains(driver)
        time.sleep(1)
        action.move_to_element_with_offset(el, 5, 5)
        action.click()
        action.perform()

        time.sleep(300)

if __name__ == "__main__":
    q = Query()
    q.send_query()

