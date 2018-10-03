#!/usr/bin/python

import scrapy
import re


class MavenRepositorySpider(scrapy.Spider):
    name = 'maven-repo-spider'
    start_urls = ['http://sdnpoc-vrodev.englab.juniper.net/vco-repo']

    custom_settings = {
        'LOG_LEVEL': 'DEBUG'
    }

    IGNORE_LIST = ['javadoc/']
    EXTENSION_REGEX = '\.[a-zA-Z]*$'

    def parse(self, response):
        for next_page in response.css('a'):
            text = next_page.css('a ::text').extract_first()

            if re.search(self.EXTENSION_REGEX, text):
                print '{}'.format(response.url + text)
            elif not any([ignored in text for ignored in self.IGNORE_LIST]):
                yield response.follow(next_page, self.parse)
