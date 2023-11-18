import config
import requests 
import json 
import time
import pymongo
from bs4 import BeautifulSoup as bs4

client = pymongo.MongoClient(config.database)
database = client["finances"]["Currency"]
cash = {"currency": {}}

currencies = [
    "USD", "EUR", "GBP",
    "PLN", "CZK", "UAH",
    "CHF", "BGN", "JPY"
]

convert_currency = [
    'Argentine Peso', 'Australian Dollar', 'British Pound',
    'Bulgarian Lev', 'Canadian Dollar', 'Chinese Yuan Renminbi',
    'Czech Koruna', 'Danish Krone', 'Egyptian Pound',
    'Euro', 'Iceland Krona', 'Indian Rupee',
    'Israeli New Shekel', 'Japanese Yen', 'Korean Won',
    'Norwegian Krone', 'Polish Zloty', 'Romanian Leu',
    'Singapore Dollar', 'Swedish Krona', 'Swiss Franc',
    'Turkish Lira', 'Ukraine Hryvnia', 'American Dollar'
]

class Currency:
    def __init__(self, currency: list, convert_currency: list):
        self.convert_currency = convert_currency
        update = int(time.strftime("%H"))

        for self.item in currency:
            cash["currency"][self.item] = {}
            self.cash = cash["currency"][self.item]
            self.cash['time'] = update

            url = f"https://fx-rate.net/{self.item}/"
            self.response = requests.get(url, timeout=5)

            status_code = self.response.status_code
            self.cash['status'] = status_code

            if status_code == 200:
                self.data_retrieval()

            else:
                self.cash['status'] = "server error"
                print(f"Parser error. Status code: {status_code}")
                break

    def data_retrieval(self):
        try:
            soup = bs4(self.response.text, "html.parser")
            self.site_data = soup.find_all("tbody")[1]
            self.symbol = soup.find("div", class_="c_symbols").get_text(strip=True)
            self.data_processin()

        except IndexError as error:
            self.cash['status'] = "bad request"
            print(f"Parser: Currency. Error. Data retrieval: {error}")

    def data_processin(self):
        cash["currency"][self.item]['symbol'] = self.symbol

        for data in self.site_data:
            info = self.info("currency_info")
            try:
                name = data.find("td").get_text(strip=True)
                if name in self.convert_currency:
                    self.cash[name] = [
                        float(data.find_all("a")[0].text),
                        float(data.find_all("a")[1].text),
                        info[name][0], info[name][1], info[name][2]
                    ] 

            except AttributeError:
                pass
        
        print("Parser: Currency. Successful upgrade")

    def info(self, name):
        path = "parser/currency_data.json"
        with open(path, "rb") as file:
            file = json.load(file)
            info = file[name]

        return info

class Crypto: 
    def __init__(self):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        headers = {
            "X-CMC_PRO_API_KEY":config.crypto_api_key,
            "Accepts":"application/json"
        }
        currencies = [
            "USD", "GBP", "EUR",
            "UAH", "PLN", "CZK"
        ]

        for self.currency in currencies:
            params = {
                "start":"1",
                "limit":"100",
                "convert":self.currency 
            }        

            self.response = requests.get(url, params=params, headers=headers)
            self.status_code()

    def status_code(self):
        if self.response.status_code == 200:             
            self.data = json.loads(self.response.text)["data"]
            self.write()
    
    def write(self):
        update = time.strftime("%d.%m.%y | %H:%M")
        data_object = {}
        symbol = self.symbol()
    
        for coin in self.data:
            name = coin["symbol"] 
            price = round(coin["quote"][self.currency]["price"], 4)
            add = {name:[name, price, symbol]}
            data_object.update(add)

        database.update_one(
            {"_id":"Crypto"}, 
            {"$set":{
                "update time":update,
                self.currency:data_object
            }},
            upsert=True
        )

    def symbol(self):
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            symbol = file["symbol"][self.currency]

        return symbol

class Share:
    def __init__(self):
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={config.share_api_kay}"
        self.response = requests.get(url)

        if self.response.status_code == 200:             
            self.data = json.loads(self.response.text)
            self.write()

    def write(self):
        update = time.strftime("%d.%m.%y | %H:%M")
        data_object = {}
        share_list = self.share_list()

        database.update_one(
            {"_id":"Shares"}, 
            {"$set":{"update time":update}},
            upsert=True
        )

        for info in self.data:
            symbol = info["symbol"]
            name = info["name"]
            price = info["price"]
            currency = '$'

            if symbol in share_list:
                add = {symbol:[symbol, name, price, currency]}
                data_object.update(add)

        database.update_one(
            {"_id":"Shares"}, 
            {"$set":data_object},
            upsert=True
        )
    
    def share_list(self):
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            share_list = file["symbols company"]

        return share_list

class CurrencyHandler:
    def __init__(self, currency: str, amount: float,
                 convert_currency: list, index: int):
        self.currency = currency
        self.amount = amount
        self.index = index
        self.convert_currency = convert_currency

        data = list(cash['currency'])
        time_now = int(time.strftime("%H"))

        if self.currency not in data:
            Currency([self.currency], self.convert_currency)
        
        else:
            update = int(cash['currency'][self.currency]['time']) + 2

            if update <= time_now:
                Currency([self.currency], self.convert_currency)
        
        self.cash = cash['currency'][self.currency]
        
        if self.cash['status'] == 200:
            self.__str__()

        else:
            return self.cash['status']

    def __str__(self):
        message = []

        for item in self.convert_currency:
            if item in list(self.cash):
                info = self.cash[item]

                if self.index == 0:
                    convert = round(info[1]*self.amount, 2)
                    symbol = self.cash['symbol']                
                    currency = f"{info[3]}/{self.currency}"

                else:
                    convert = round(info[0]*self.amount, 2)
                    symbol = info[4]                
                    currency = f"{self.currency}/{info[3]}"

                data =  f"{info[2]} {currency.upper()} | {convert}{symbol}"
                message.append(data)
        
        self.cash['inline'] = message 
        return "\n".join(map(str, message))

def main():
    while True:
        Currency(currencies, convert_currency)
        Share()
        Crypto()
  
        print("Update data")
        time.sleep(7200)
