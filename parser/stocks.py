import requests
import json
from jsoncfg import load_config
from logs_handler import logger


class Stocks:
    def __init__(self, config):
        self.stocks_data = {}

        key = config.stocks_api_key.value
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={key}"
        self.response = requests.get(url)

        try:
            self.response.raise_for_status()         
            self.data = json.loads(self.response.text)
            self.data_processin()

        except requests.HTTPError as e:
            self.error = e 
            logger.error(f"[Parser Error] Stocks. Connection error: {e}")

    def data_processin(self):
        get_stocks_list = load_config("parser/data.json").company
        stocks_list = [item.value for item in get_stocks_list]

        for info in self.data:
            symbol = info["symbol"]
            name = info["name"]
            price = info["price"]
            currency = "$"      

            if symbol in stocks_list:
                self.stocks_data[symbol] = symbol, name, price, currency

        logger.info(f"[Parser] Successful upgrade of stocks")
        self.return_data()

    def return_data(self) -> dict:    
        if self.stocks_data  == {}: 
            return {"Error": f"{self.error}"}
        else: 
            return self.stocks_data 