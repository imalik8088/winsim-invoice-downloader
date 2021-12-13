from pathlib import Path

import scrapy
from scrapy.http import FormRequest

from .credentials import credentials


class WinsimInvoiceSpider(scrapy.Spider):
    name = 'winsim'
    allowed_domains = ['service.winsim.de']
    start_urls = ['https://service.winsim.de/']
    last_n_invoices = None
    cookies = {}
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Host': 'www.service.winsim.de',
        'Referer': 'https://www.service.winsim.de',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    def __init__(self, last_n_invoices=1, **kwargs):
        self.last_n_invoices = int(last_n_invoices)

    def parse(self, response, **kwargs):
        self.logger.info(f"Visiting {self.start_urls[0]}...")
        authenticity_token = response.xpath('//*[@id="UserLoginType_csrf_token"]/@value').extract_first()

        yield FormRequest.from_response(response, formdata={'UserLoginType[csrf_token]': authenticity_token,
                                                            'UserLoginType[alias]': credentials['user'],
                                                            'UserLoginType[password]': credentials['password']},
                                        meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}, callback=self.after_login)

    def after_login(self, response):
        cookie = response.headers.getlist('Set-Cookie')[0].decode("utf-8").split(';')[0]
        self.cookies = dict(cookie.split("=") for x in cookie.split(";"))
        self.logger.info(f"[Cookie] {self.cookies}")
        self.logger.info('Logged in... ')

        invoice_overview_url = "https://service.winsim.de/mytariff/invoice/showAll"
        yield scrapy.Request(url=invoice_overview_url, cookies=self.cookies, callback=self.overview_invoices)

    def overview_invoices(self, response):
        INVOICE_CARD_SELECTOR = 'div.card'
        for invoice_block in response.css(INVOICE_CARD_SELECTOR)[0:self.last_n_invoices]:
            INVOICE_DATE_SELECTOR = 'button.card-header > span::text'
            INVOICE_URL_SELECTOR = 'p.pdf > a::attr(href)'
            invoice_date = invoice_block.css(INVOICE_DATE_SELECTOR).extract_first().split(" ")[-1]
            invoice_url = invoice_block.css(INVOICE_URL_SELECTOR).extract_first()
            yield scrapy.Request(url=f"https://service.winsim.de{invoice_url}", cookies=self.cookies, callback=self.save_pdf_invoice, meta={'invoice_date': invoice_date})

    def save_pdf_invoice(self, response):
        download_dir = f"{Path.home()}/Downloads"
        filename = f"{response.meta.get('invoice_date')}.pdf"
        self.logger.info(f"Saving PDF {filename}")
        with open(f"{download_dir}/{filename}", 'wb') as f:
            f.write(response.body)
