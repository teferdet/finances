import config
import requests 
import json 
import time
from bs4 import BeautifulSoup as bs4

class Currency:
    global name_list

    name_list = {
        "American Dollar":["🇺🇸", "USD", "$"],
        "Euro":["🇪🇺", "EUR", "€"],
        "British Pound":["🇬🇧", "GBP", "£"],
        "Czech Koruna":["🇨🇿", "CZK", "Kč"],
        "Japanese Yen":["🇯🇵", "JPY", "¥"],
        "Polish Zloty":["🇵🇱", "PLN", "zł"],
        "Swiss Franc":["🇨🇭", "CHF", "₣"],
        "Chinese Yuan Renminbi":["🇨🇳", "CNY", "¥"],
        "Ukraine Hryvnia":["🇺🇦", "UAH", "₴"]
    }

    def __init__(self, currency, rate_index, currency_list):
        global status_code
        global url
        global name

        name = "fx-rate"
        url = f'https://fx-rate.net/{currency}/'
        
        request = requests.get(url)
        status_code = request.status_code
        self.currency_list = currency_list
        self.currency = currency

        if status_code == 200:
            self.index = rate_index  

            self.request = request.text
            self.parser_data(self.request)
        
        else:
            pass
    
    def parser_data(self, request):
        global status 

        try:
            status = True
            soup = bs4(self.request, "html.parser")
            self.main = soup.find_all("tbody")[1]
            self.symbol = soup.find( "div", class_="c_symbols").get_text(strip=True)

            self.parser(self.index, self.main)

        except Exception as error:
            status = False

    def parser(self, index, main):
        global rate
        
        self.currency_name = []
        self.rate = []

        for info in self.main:
            try:
                name = info.find("td")

                if name.get_text(strip=True) in self.currency_list:
                    rate = info.find_all("a")[self.index].text
                    
                    self.currency_name.append(name.get_text(strip=True))
                    self.rate.append(rate)

            except AttributeError:
                pass
            
            except Exception as error:
                print("78:", error)

        self.printed( 
            self.currency_name, self.rate, self.symbol,
            self.index, self.currency
        )
    
    def printed(
        self, currency_name, rate,
        symbol, index, currency
    ):
        global send
        send = []

        for name, rate in zip(self.currency_name, self.rate):
            if self.index == 1:
                symbol = self.symbol  
                currency = f"{name_list[name][1]}/{self.currency}"
            
            else:
                symbol = name_list[name][2]
                currency = f"{self.currency}/{name_list[name][1]}"

            add = f"{name_list[name][0]} {currency.upper()} = {rate}{symbol}"
            send.append(add)

        send = '\n'.join(map(str, send))

class Crypto:
    global symbol    

    symbol = {
        "USD":"$", "EUR":"€",
        "GBP":"£", "UAH":"₴"
    }

    def __init__(self, currency, crypto_list):
        global status_code
        global status
        global name 
        global url
        
        status = True
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        name = "CoinMarketCap"

        headers = {
            'X-CMC_PRO_API_KEY' : config.api_crypto_key,
            'Accepts':'application/json'
        }
        params = {
            'start':'1',
            'limit':'100',
            'convert': currency}

        request = requests.get(url, params=params, headers=headers)

        if request.status_code == 200: 
            status_code = request.status_code
            self.currency = currency
            self.crypto_list = crypto_list
            self.request = request.text
            self.printed(self.request, self.currency, self.crypto_list)

        else:
            pass

    def printed(self, request, currency, crypto_list):
        global rate
        global send

        send = []
        data = json.loads(request)['data']

        for coin in data:
            name = coin['symbol'] 
            
            if name in self.crypto_list:
                rate = coin['quote'][self.currency]['price']
                add = f"💵 {name}\{self.currency} = {round(rate, 4)}{symbol[self.currency]}"
                
                if add not in send:
                    send.append(add)
                    
        send = '\n'.join(map(str, send))

class Convert:
    def __init__(self, a, b):
        global status_code
        global status
        global url
        global name

        url = f"https://www.google.com/search?q={a}+in+{b}" 
        name = "Google finance"

        self.finance = requests.get(url)
        status_code = finance.status_code
        status = False

        if status_code == 200:
            status = True
            self.parser(self.finance)

    def parser(self, main):
        global rate
                
        soup = bs4(finance.text, "html.parser")
        rate = float(
            soup.find("span", class_='DFlfde SwHCTb').text
        )

class Shares:
    def __init__(self, shares_list):
        global url
        global status_code
           
        url = 'https://www.google.com/finance'
        name = "Google finance"
        
        session = requests.Session() 
        request = session.get(url, headers=headers)
        
        status_code = request.status_code

        if status_code == 200:
            soup = bs4(request.text, "html.parser")
            self.main = soup.find_all("li")
            self.printed(self.main, shares_list, request)

        else:
            print(status_code)

    def printed(self, main, shares_list, request):
        global send
        
        send = []

        for data in self.main:
            teg = data.find("div", class_="COaKTb").text
            rate = (data.find("div", class_="YMlKec").text).replace('$', '')
            add_rate = (data.find("div", class_="BAftM").text).replace('$', '')        
            
            if teg in shares_list:
                info = f"💸 {teg} | {rate}$ | {add_rate}$"
                send.append(info)
        
        send = '\n'.join(map(str, send))
