import requests
import json
import time
from jsoncfg import load_config
from logs_handler import logger


class Crypto:
    def __init__(self, config: dict):
        self.config = config.currencies_settings
        self.crypto_data = {}
        self.success_update = []
        self.url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        self.headers = {
            "X-CMC_PRO_API_KEY": config.crypto_api_key.value,
            "Accepts": "application/json"
        }

        self.fetch_crypto_data()

    def fetch_crypto_data(self):
        for i in self.config.convert_crypto:   
            self.currency = i.value
            self.crypto_data[self.currency] = {}
            self.item_data = self.crypto_data[self.currency]

            params = {"start": "1", "limit": "100", "convert": self.currency}
            self.response = requests.get(self.url, params=params, headers=self.headers)
            
            self.status_code()
        
        else:
            log_time = time.strftime("%d.%m.%y %H:%M:%S")
            success_update = ", ".join(self.success_update)

            logger.info(f"[Parser] Successful update of cryptocurrencies {success_update}")

        self.return_data()

    def status_code(self):
        log_time = time.strftime("%d.%m.%y %H:%M:%S")

        try:
            self.response.raise_for_status()
            self.data = json.loads(self.response.text)["data"]
            self.data_processin()
        
            self.success_update.append(self.currency)
        
        except requests.HTTPError as e:
            self.crypto_data == {}
            self.error = e 
            logger.error(f"[Parser Error] Crypto. Connection error: {e}")

    def data_processin(self):
        symbol = load_config("parser/data.json")["symbol"][self.currency].value

        for coin in self.data:
            name = coin["symbol"]
            price = round(coin["quote"][self.currency]["price"], 4)
            self.item_data[name] = [name, price, symbol]

    def return_data(self) -> dict:
        if self.crypto_data == {}: 
            return {"Error": f"{self.error}"}
        else: 
            return self.crypto_data
            
