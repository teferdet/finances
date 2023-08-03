import config
import requests 
import json 
import time
import pymongo
from bs4 import BeautifulSoup as bs4

client = pymongo.MongoClient(config.database)
database = client["finances"]["Currency"]

class Currency:
    def __init__(self, currency, rate_index, currency_list, number):
        self.currency = currency 
        self.rate_index = rate_index
        self.currency_list = currency_list
        self.number = float(number) 

        self.main() 
    
    def main(self):
        global url 
        global name 

        name = "fx-rate"
        url = f"https://fx-rate.net/{self.currency}/"

        self.response = requests.get(url)
        self.status()
    
    def status(self):
        global status_code
        
        status_code = self.response.status_code
        
        if status_code == 200:
            self.parser()
        
        else:
            pass

    def parser(self):
        global status 
        
        try:
            status = True
            soup = bs4(self.response.text, "html.parser")
            self.site_data = soup.find_all("tbody")[1]
            self.symbol = soup.find("div", class_="c_symbols").get_text(strip=True)

            self.currency_data()

        except Exception as error:
            status = False

    def currency_data(self):
        global send_list 
        global send

        send_list = []
        self.currency_info(name="currency_info")

        for data in self.site_data: 
            try: 
                table_data = data.find("td").get_text(strip=True)

                if table_data in self.currency_list:
                    rate = float(data.find_all("a")[self.rate_index].text)
                    convert = round(rate*self.number, 4)
                        
                    if self.rate_index == 1:
                        symbol = self.symbol
                        currency = f"{info[table_data][1]}/{self.currency}"
                        
                    else:
                        symbol = info[table_data][2]                
                        currency = f"{self.currency}/{info[table_data][1]}"
                    
                    add = f"{info[table_data][0]} {currency.upper()} | {convert}{symbol}"
                    send_list.append(add)
                
            except AttributeError:
                pass
            
            except Exception:
                pass

        send = "\n".join(map(str, send_list))

    def currency_info(self, name):
        global info
        
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            info = file[name]

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
        data_object = {}
        symbol = self.symbol()
    
        for coin in self.data:
            name = coin["symbol"] 
            price = round(coin["quote"][self.currency]["price"], 4)
            add = {name:[name, price, symbol]}
            data_object.update(add)

        database.update_one(
            {"_id":"Crypto"}, 
            {"$set":{self.currency:data_object}},
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
        data_object = {}
        share_list = self.share_list()

        for info in self.data:
            symbol = info["symbol"]
            name = info["name"]
            price = info["price"]
            
            if symbol in share_list:
                add = {symbol:[symbol, name, price]}
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

def main():
    while True:
        Share()
        Crypto()
        time.sleep(1800)
