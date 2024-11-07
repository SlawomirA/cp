import os

import scrapy
import json
from scrapy.http import Request


class PDFSpider(scrapy.Spider):
    name = "pdf_spider"

    custom_settings = {
        'FEEDS': {
            'pdf_links.json': {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True
            }
        }
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super(PDFSpider, self).__init__(*args, **kwargs)
        self.start_urls = [start_url] if start_url else []

    def parse(self, response):
        pdf_links = []
        for link in response.css('a::attr(href)').getall():
            if link.lower().endswith('.pdf'):
                full_link = response.urljoin(link)
                pdf_links.append(full_link)
                self.log(f"Found PDF link: {full_link}")

        if pdf_links:
            for pdf_link in pdf_links:
                yield {'pdf_link': pdf_link}