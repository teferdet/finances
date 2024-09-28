import time
import json
import random
import requests
from bs4 import BeautifulSoup as bs4
from jsoncfg import load_config
from logs_handler import logger
from fake_useragent import UserAgent
import cloudscraper

class Currency:
    def __init__(self, currencies: list):
        from parser.parser_handler import CACHE

        self.CACHE = CACHE 
        self.success_update = []
        self.scraper = cloudscraper.create_scraper(browser='chrome')
        self.ua = UserAgent()
        self.setup_session()

        times = int(time.strftime("%H"))
        day = time.strftime("%m.%d")

        for self.currency in currencies:
            self.log_time = time.strftime("%d.%m.%y %H:%M:%S")
            self.CACHE[self.currency] = {}
            self.currency_cash = self.CACHE[self.currency]
            self.currency_cash["update"] = {
                "time": times,
                "day": day
            }
            self.request()
        
        else:
            success_update = ", ".join(self.success_update)
            logger.info(f"[Parser] Successful update of currencies {success_update}")

    def setup_session(self):
        self.scraper.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    def get_cf_clearance(self):
        try:
            response = self.scraper.get('https://fx-rate.net/')
            return self.scraper.cookies.get('cf_clearance')
        except Exception as e:
            logger.error(f"Error getting Cloudflare clearance: {e}")
            return None

    def request(self):       
        url = f"https://fx-rate.net/{self.currency}/"
        
        self.scraper.headers.update({
            'User-Agent': self.ua.random,
            'Referer': 'https://fx-rate.net/',
        })

        cf_clearance = self.get_cf_clearance()
        if cf_clearance:
            self.scraper.cookies.set('cf_clearance', cf_clearance)
        
        try:
            time.sleep(random.uniform(2, 5))
            
            response = self.scraper.get(url, timeout=15)
            response.raise_for_status()
            
            self.response = response.text
            self.currency_cash["status"] = "good"
            self.data_retrieval()
        except requests.RequestException as e:
            self.currency_cash["status"] = "bad request"
            logger.info(f"[Parser Error] Currency. Request error: {e}")
            logger.info(f"Response content: {response.text[:500]}...") 

    def data_retrieval(self):
        try:
            soup = bs4(self.response, "html.parser")
            self.site_data = soup.find_all("tbody")[1].find_all("tr")
            self.data_processin()
        except IndexError as e:
            self.currency_cash["status"] = "bad request"
            logger.info(f"[Parser Error] Currency. Data retrieval: {e}")
            logger.info(f"Response content: {self.response[:500]}...")

    def data_processin(self):
        self.currency_cash["status"] = "good"
        self.currency_cash["symbol"] = self.symbol()

        for data in self.site_data:
            info = load_config("parser/data.json").currencies_info
            settings = load_config("files/config.json").currencies_settings
            convert_currencies = [i.value for i in settings["convert_currencies"]]

            try:
                cells = data.find_all("td")
                name = cells[0].get_text(strip=True)

                if name in convert_currencies:
                    self.currency_cash[name] = [
                        float(cells[1].text), float(cells[2].text),
                        info[name][0].value, info[name][1].value, 
                        info[name][2].value
                    ] 
            
            except IndexError:
                pass
        
        self.success_update.append(self.currency)

    def symbol(self):
        path = "handlers/functions/currencies_data.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        
        for i in data:
            if i["code"] == self.currency:
                return i["symbol"]