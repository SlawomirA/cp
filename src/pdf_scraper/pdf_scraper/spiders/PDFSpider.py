import scrapy
import json

class PDFSpider(scrapy.Spider):
    name = "pdf_spider"
    start_urls = ['https://dziennikustaw.gov.pl/DU/rok/2024']

    def parse(self, response):
        pdf_links = []
        # Extract all PDF links from the page (assuming they have .pdf in the href attribute)
        for link in response.css('a::attr(href)').getall():
            if link.endswith('.pdf'):
                pdf_links.append(response.urljoin(link))

        # Save the PDF links to a JSON file if any are found
        if pdf_links:
            with open('pdf_links.json', 'w') as f:
                json.dump(pdf_links, f)

        self.log(f'Scraped {len(pdf_links)} PDF links.')
