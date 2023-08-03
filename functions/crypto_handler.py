import re 
import pymongo
import random
import time 
import __main__ as main
import config
import parser
import language
import keyboard

bot = main.bot
client = pymongo.MongoClient(config.database)
finance = client["finances"]["Currency"]

crypto_currency = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC"
]

class Crypto:
    def __init__(self, message):
        self.message = message
        language = message.from_user.language_code
        
        if language in ['ru', 'be']:
            keyboard.inline(message)
            bot.send_message(
                message.chat.id,
                "[¯\_(ツ)_/¯ I do not understand your language](http://surl.li/dhmwi)",
                reply_markup=keyboard.link,
                parse_mode='MarkdownV2'
            )    

        else:
            self.request()
    
    def request(self):
        self.send = []

        query = {"_id":"Crypto"}
        data = {"_id":0, "USD":1}

        for info in finance.find(query, data):
            data = info['USD']
        
        for key in data:   
            if key in crypto_currency:
                name = data[key][0]
                price = data[key][1]
                symbol = data[key][2]

                add = f"💵 {name}/USD | {price}{symbol}"
                self.send.append(add)

        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        language.course(self.message)
        keyboard.alternative_currency_key(self.message, "crypto")

        bot.send_message(
            self.message.chat.id, 
            f"{language.rate}{day}\n{self.send}",
            reply_markup=keyboard.currency
        )

class AlternativeCrypto:
    def __init__(self, call, currency):
        self.call = call
        self.currency = currency.split()[1]
        self.send = []

        query = {"_id":"Crypto"}
        data = {"_id":0, self.currency:1}

        for info in finance.find(query, data):
            data = info[self.currency]
        
        for key in data:   
            if key in crypto_currency:
                name = data[key][0]
                price = data[key][1]
                symbol = data[key][2]

                add = f"💵 {name}/{self.currency} | {price}{symbol}"
                self.send.append(add)

        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        language.course(self.call)
        keyboard.alternative_currency_key(self.call, "crypto")

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=f"{language.rate}{day}\n{self.send}",
            reply_markup=keyboard.currency
        ) 
