import time
from messages_handler import client, UpdateOne
from jsoncfg import load_config
from parser.currency import Currency
from parser.crypto import Crypto 
from parser.stocks import Stocks
from logs_handler import logger

config = load_config("files/config.json")
database = client['Currency']
CACHE = {}

class CurrenciesHandler:
    def __init__(self, convert_data, convert_currencies: list, index: int):
        self.convert_data = convert_data
        self.convert_currencies = convert_currencies
        self.time_now = int(time.strftime("%H"))
        self.date = time.strftime("%m.%d")
        self.index = index
        self.publishing = []
        
        for data in self.convert_data:
            self.currency = data[0].upper()
            self.amount = data[1]

            self.get_currency_data()

    def get_currency_data(self):
        if self.currency not in list(CACHE) or self.update():
            Currency([self.currency])
        
        self.CACHE = CACHE[self.currency]
        self.status()

    def update(self):
        try:    
            update = CACHE[self.currency].get('update', {})
            times = int(update.get('time', 0)) + 3
            day = update.get('day', '')

            return times <= self.time_now or day != self.date

        except (KeyError, AttributeError):
            return True

    def status(self) -> str:
        if self.CACHE["status"] != "good":
            return self.CACHE["status"]

        else:
            self.print_processing()

    def print_processing(self):
        currency_data = []

        for item in self.convert_currencies:
            if item in list(self.CACHE):
                info = self.CACHE[item]
                convert, symbol, currency = self.calculate_conversion(info)

                data = f"{info[2]} {currency.upper()} {convert}{symbol}"
                currency_data.append(data)

        self.CACHE['inline'] = currency_data 
        self.publishing.append("\n".join(map(str, currency_data)))

    def calculate_conversion(self, info):
        if self.index == 0:
            symbol = info[4]
            currency = f"{self.currency}/{info[3]}"
        
        else:        
            symbol = self.CACHE['symbol']
            currency = f"{info[3]}/{self.currency}"
        
        convert = round(info[self.index]*self.amount, 2)
        if convert <= 0.01:
            convert = round(info[self.index]*self.amount, 4)

        return convert, symbol, currency

    def __str__(self) -> str:
        if len(self.publishing) > 1:
            border = "\n===============\n"
            return border.join(self.publishing)
        
        else:
            return self.publishing[0]

class Updater:
    def __init__(self) -> None: 
        global config

        self.number_of_repeats = config.update.number_of_repeats.value
        self.repeat = self.number_of_repeats
        self.option = True

    def start(self):
        while self.option:
            self.config = load_config("files/config.json")
            if self.config.update.automatic_update.value:                
                self.update()
            else:
                time.sleep(5)

    def update(self):
        self.number_of_repeats = self.config.update.number_of_repeats.value
        sleep_time = self.config.update.sleep_time.value
        text = " "

        if self.number_of_repeats == self.repeat :
            currencies_settings = self.config.currencies_settings
            
            currencies = [i.value for i in currencies_settings.currencies]
            Currency(currencies)
            
            text = " currencies and "
            self.repeat = 0
            
        self.database()
        logger.info(f"[Parser] Update of all cryptocurrencies,{text}stocks are completed")

        self.repeat += 1
        time.sleep(sleep_time)

    def database(self):
        crypto_data = Crypto(self.config).return_data()
        stocks_data = Stocks(self.config).return_data()

        database.bulk_write([
            UpdateOne({"_id": "stocks"}, {"$set": stocks_data}, upsert=True),
            UpdateOne({"_id": "Crypto"}, {"$set": crypto_data}, upsert=True)
        ])
    
    def stop(self):
        self.option = False
