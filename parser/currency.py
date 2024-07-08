import requests
import time
import json
from bs4 import BeautifulSoup as bs4
from jsoncfg import load_config
from logs_handler import logger


class Currency:
    def __init__(self, currencies: list):
        from parser.parser_handler import CACHE

        self.CACHE = CACHE 
        self.success_update = []

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

    def request(self):
        url = f"https://fx-rate.net/{self.currency}/"
        self.response = requests.get(url, timeout=5)

        status_code = self.response.status_code
        self.currency_cash["status"] = status_code

        if status_code == 200:
            self.data_retrieval()

        else:
            self.currency_cash["status"] = "server error"
            logger.error(f"[Parser Error] Connection error, status code: {status_code}")

    def data_retrieval(self):
        try:
            soup = bs4(self.response.text, "html.parser")
            self.site_data = soup.find_all("tbody")[1].find_all("tr")
            self.data_processin()

        except IndexError as e:
            self.currency_cash["status"] = "bad request"
            logger.info(f"[Parser Error] Currency. Data retrieval: {e}")

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
            