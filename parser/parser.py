import config
import requests 
import json 
import time
from bs4 import BeautifulSoup as bs4

crypto_rate = {
    "update date":"",
    "USD":"",
    "GBP":"",
    "EUR":"",
    "UAH":""
}

class Currency:
    def __init__(self, currency, rate_index, currency_list, number):
        global url
        global name

        name = "fx-rate"
        url = f'https://fx-rate.net/{currency}/'
        
        response = requests.get(url)
        self.status(response, currency, rate_index, currency_list, number)
        
    def status(self, response, currency, rate_index, currency_list, number):
        global status_code
    
        status_code = response.status_code
        self.number = number
        self.currency_list = currency_list
        self.currency = currency

        if status_code == 200:
            self.index = rate_index  
            self.response = response.text
            
            self.parser_data(self.response)
        
        else:
            pass
    
    def parser_data(self, response):
        global status 

        try:
            status = True
            soup = bs4(self.response, "html.parser")
            self.main = soup.find_all("tbody")[1]
            self.symbol = soup.find("div", class_="c_symbols").get_text(strip=True)

            self.parser(self.index, self.main, self.number)

        except Exception as error:
            status = False

    def parser(self, index, main, number):
        self.rate = []
        self.currency_name = []
        number = float(self.number)
        
        for info in self.main:
            try:
                name = info.find("td")

                if name.get_text(strip=True) in self.currency_list:
                    add = float(info.find_all("a")[self.index].text)
                    convert = round(add*number, 4)
                    
                    self.rate.append(convert)
                    self.currency_name.append(name.get_text(strip=True))

            except AttributeError:
                pass
            
            except Exception as error:
                print(error)

        self.printed( 
            self.currency_name, self.rate, self.symbol,
            self.index, self.currency, 
        )
    
    def printed(self, currency_name, rate, symbol, index, currency):
        global send_list
        global send
        
        self.data(name='currency_info')
        send_list = []
        
        for name, rate in zip(self.currency_name, self.rate):
            if self.index == 1:
                symbol = self.symbol
                currency = f"{info[name][1]}/{self.currency}"
                
            else:
                symbol = info[name][2]                
                currency = f"{self.currency}/{info[name][1]}"

            add = f"{info[name][0]} {currency.upper()} | {rate}{symbol}"
            send_list.append(add)

        send = '\n'.join(map(str, send_list))

    def data(self, name):
        global info
        
        file_name = "parser/currency_data.json"
        with open(file_name, "rb") as file:                
            file = json.load(file)
            info = file[name]

class Crypto:
    def __init__(self, currency, crypto_list):
        global status
        global send
        
        day = str(time.strftime("%d/%m/%y"))
        times = str(time.strftime("%H:%M"))
        update_time = ["0:00", "6:00", "12:00", "18:00"]
        
        if times in update_time or crypto_rate[currency] == "":
            crypto_rate["update date"] = day
            self.data(currency, crypto_list)

        elif crypto_rate["update date"] != day:
            crypto_rate["update date"] = day
            self.data(currency, crypto_list)

        else:
            status = True
            send = crypto_rate[currency]

    def data(self, currency, crypto_list):
        global name
        global url
        
        crypto_rate[currency] = ""
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        name = "CoinMarketCap"
        
        headers = {
            'X-CMC_PRO_API_KEY' : config.api_crypto_key,
            'Accepts':'application/json'
        }

        params = {
            'start':'1',
            'limit':'100',
            'convert': currency 
        }
        
        response = requests.get(url, params=params, headers=headers)
        self.status_code(response, currency, crypto_list)
        
    def status_code(self, response, currency, crypto_list):
        global status_code        
        global status

        status = True
        status_code = response.status_code

        if status_code == 200: 
            self.currency = currency
            self.crypto_list = crypto_list
            self.response = response.text

            self.printed(self.response, self.currency, self.crypto_list)
        
        else:
            status = False 
        
    def printed(self, request, currency, crypto_list):
        global send
        
        send_list = []
        data = json.loads(request)['data']
        self.symbol(currency)
        
        for coin in data:
            name = coin['symbol'] 

            if name in self.crypto_list:
                rate = coin['quote'][self.currency]['price']
                round_rate = round(rate, 4)
                
                add = f"💵 {name}\{self.currency} = {round_rate}{symbol}"

                if add not in send_list:
                    send_list.append(add)

        send = '\n'.join(map(str, send_list))
        crypto_rate[currency] = send        
    
    def symbol(self, currency):
        global symbol
        
        file_name = "parser/currency_data.json"
        with open(file_name, "rb") as file:                
            file = json.load(file)
            symbol = file["symbol"][currency]
