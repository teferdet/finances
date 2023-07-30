import config
import requests 
import json 
import time
import pymongo
from bs4 import BeautifulSoup as bs4

client = pymongo.MongoClient(config.database)
database = client['finances']['Currency']

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
        url = f'https://fx-rate.net/{self.currency}/'

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
        self.currency_info(name='currency_info')

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

        send = '\n'.join(map(str, send_list))

    def currency_info(self, name):
        global info
        
        path = "parser/currency_data.json"
        with open(path, "rb") as file:                
            file = json.load(file)
            info = file[name]

class Crypto: 
    def __init__(self, currency, crypto_list):
        global status_code
        global status
        global send

        self.currency = currency 
        self.crypto_list = crypto_list 
        self.day = str(time.strftime("%d/%m/%y"))
        self.time_now = int(time.strftime("%H"))


        for item in database.find({"_id":"Crypto"}):
            last_update = int(item[self.currency]['time'])
            date = item[self.currency]['date']
            rate = item[self.currency]['rate']

        next_update = last_update+1

        if (next_update <= self.time_now) or (date != self.day):
            self.main()

        else:
            status_code = True
            status = True
            send = rate 

    def main(self):
        global name 
        global url        

        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        name = "CoinMarketCap"
        
        headers = {
            'X-CMC_PRO_API_KEY':config.crypto_api_key,
            'Accepts':'application/json'
        }

        params = {
            'start':'1',
            'limit':'100',
            'convert': self.currency 
        }        

        self.response = requests.get(url, params=params, headers=headers)
        self.status_code()

    def status_code(self):
        global status_code        
        global status

        status = True
        status_code = self.response.status_code

        if status_code == 200:             
            self.data = json.loads(self.response.text)['data']
            self.write()

        else:
            status = False 

    def write(self):
        global send

        times = str(time.strftime("%H:%M:%S"))
        send_list = []
        self.currency_info(currency=self.currency)

        for coin in self.data:
            name = coin['symbol'] 

            if name in self.crypto_list:
                rate = round(
                    coin['quote'][self.currency]['price'], 4
                )
                add = f"💵 {name}\{self.currency} | {rate}{symbol}"

                if add not in send_list:
                    send_list.append(add)

        send = '\n'.join(map(str, send_list))

        database.update_many(
            {"_id":"Crypto"}, {'$set':{
                f"{self.currency}.date":self.day,
                f"{self.currency}.time":self.time_now,
                f"{self.currency}.rate":send
            }}
        )

    def currency_info(self, currency):
        global symbol
        
        file_name = "parser/currency_data.json"
        with open(file_name, "rb") as file:                
            file = json.load(file)
            symbol = file["symbol"][currency]

class Share:
    def __init__(self, company):
        self.day = str(time.strftime("%d.%m.%y"))
        self.time_now = int(time.strftime("%H"))
        self.company = company

        for item in database.find({"_id":"Shares"}):
            last_update = int(item['time'])
            date = item['date']
            self.send = item['data']

        next_update = last_update+1

        if (next_update <= self.time_now) or (date != self.day):
            self.get_data()
    
    def get_data(self):
        company = ','.join(self.company)
        url = f"https://financialmodelingprep.com/api/v3/quote/{company}?apikey={config.share_api_kay}"
        self.response = requests.get(url)

        if self.response.status_code == 200:             
            self.data = json.loads(self.response.text)
            self.write()

        else:
            self.send = False 

    def write(self):
        rate = []
        
        for info in self.data:
            text = f"💵 {info['symbol']} | {info['name']} = {info['price']}$"
            rate.append(text)

        self.send = "\n".join(rate)
        database.update_many(
            {"_id":"Shares"}, {'$set':{
                "date":self.day,
                "time":self.time_now,
                "data":self.send
            }}
        )
