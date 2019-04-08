#!/usr/bin/python

import scrapy
import re

# crawls a website starting at the provided link
# extracts all links from the website and either follows them and repeats the process
# or prints out the link when it's pointing to an artifact
# an 'artifact' is considered to be a file with an extension
# ignores / does not follow links from the IGNORE_LIST

# run command: scrapy runspider scrapy-maven.py -a start_url='http://localhost:8443/maven-repo'


class MavenRepositorySpider(scrapy.Spider):
    name = 'maven-repo-spider'

    custom_settings = {
        'LOG_LEVEL': 'DEBUG'
    }

    IGNORE_LIST = ['javadoc/']
    EXTENSION_REGEX = '\.[a-zA-Z]*$'

    def __init__(self, *args, **kwargs):
        super(MavenRepositorySpider, self).__init__(*args, **kwargs)
        self.start_urls = [self.start_url]

    def parse(self, response):
        for next_page in response.css('a'):
            text = next_page.css('a ::text').extract_first()

            if re.search(self.EXTENSION_REGEX, text):
                print '{}'.format(response.url + text)
            elif not any([ignored in text for ignored in self.IGNORE_LIST]):
                yield response.follow(next_page, self.parse)
