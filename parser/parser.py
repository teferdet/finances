import config
import requests 
import json 
import time
import pymongo
from bs4 import BeautifulSoup as bs4

client = pymongo.MongoClient(config.data(["database"]))
database = client["finances"]["Currency"]
cash = {}

class Currency:
    def __init__(self, currency: list, convert_currency: list):
        self.convert_currency = convert_currency
        times = int(time.strftime("%H"))
        day = time.strftime("%m.%d")

        for self.item in currency:
            cash[self.item] = {}
            cash[self.item]['update'] = {}
            self.cash = cash[self.item]
            self.cash['update']['time'] = times
            self.cash['update']['day'] = day

            url = f"https://fx-rate.net/{self.item}/"
            self.response = requests.get(url, timeout=5)

            status_code = self.response.status_code
            self.cash['status'] = status_code

            if status_code == 200:
                self.data_retrieval()

            else:
                self.cash['status'] = "server error"
                print(f"[Parser Error] {time.strftime('%d.%m.%y %H:%M%S')}. Connection error, status code: {status_code}")
                break

    def data_retrieval(self):
        try:
            soup = bs4(self.response.text, "html.parser")
            self.site_data = soup.find_all("tbody")[1].find_all("tr")
            self.symbol = soup.find("div", class_="fmenu2").find_all("li")[1].text[-1]
            self.data_processin()

        except IndexError as error:
            self.cash['status'] = "bad request"
            print(f"[Parser Error] {time.strftime('%d.%m.%y %H:%M%S')}: Currency. Data retrieval: {error}")

    def data_processin(self):
        cash[self.item]['symbol'] = self.symbol

        for data in self.site_data:
            info = self.info("currency_info")
            
            try:
                cells = data.find_all("td")
                name = cells[0].get_text(strip=True)

                if name in self.convert_currency:
                    self.cash[name] = [
                        float(cells[1].text),
                        float(cells[2].text),
                        info[name][0], info[name][1],
                        info[name][2]
                    ] 
            
            except IndexError:
                pass

        print(f"[Parser] {time.strftime('%d.%m.%y %H:%M%S')}: Currency. Successful update {self.item}")

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
            "X-CMC_PRO_API_KEY":config.data(['crypto api key']),
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
        
        print(f"[Parser] {time.strftime('%d.%m.%y %H:%M%S')}: Crypto. Successful update {self.currency}")

    def symbol(self):
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            symbol = file["symbol"][self.currency]

        return symbol

class Share:
    def __init__(self):
        key = config.data(['share api kay'])
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={key}"
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

        print("[Parser] {time.strftime('%d.%m.%y %H:%M%S')}: Share. Successful upgrade")
    
    def share_list(self):
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            share_list = file["symbols company"]

        return share_list

class CurrencyHandler:
    def __init__(self, currency: str, amount: float,
                 convert_currency: list, index: int):
        self.currency = currency.upper()
        self.amount = float(amount)
        self.index = index
        self.convert_currency = convert_currency

        time_now = int(time.strftime("%H"))
        date = time.strftime("%m.%d")

        if self.currency not in list(cash):
            Currency([self.currency], self.convert_currency)
        
        else:
            update = cash[self.currency]['update']
            times = int(update['time']) + 3
            day = update['day']

            if times <= time_now or day != date:
                Currency([self.currency], self.convert_currency)
        
        self.cash = cash[self.currency]
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
                    convert = round(info[0]*self.amount, 2)
                    symbol = info[4]                
                    currency = f"{self.currency}/{info[3]}"

                else:
                    convert = round(info[1]*self.amount, 2)

                    if convert == "0.0":
                        convert = round(info[1]*self.amount, 4)

                    symbol = self.cash['symbol']                
                    currency = f"{info[3]}/{self.currency}"

                data =  f"{info[2]} {currency.upper()} | {convert}{symbol}"
                message.append(data)

        self.cash['inline'] = message 
        return "\n".join(map(str, message))

def refreshed():
    currency_update = 3

    while True:
        times = time.strftime("%H:%M")
        if currency_update == 3:
            data = config.data(['currencies', 'convert currency'])
            Currency(data[0], data[1])
            currency_update = 0
        
        Crypto()
        Share()

        print(f"[Parser] {time.strftime('%d.%m.%y %H:%M%S')}: Update of all cryptocurrency currencies is completed")

        currency_update += 1
        time.sleep(3600)
