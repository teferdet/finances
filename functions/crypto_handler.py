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
user_db = client["finances"]["Users"]

crypto_currency = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC"
]
data = 'exchange rate'

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
            self.massage_handler()
    
    def massage_handler(self):
        ID = self.message.from_user.id

        self.number = re.findall(r"\d+\.*\d*", self.message.text)
        self.number = float(self.number[0]) if self.number != [] else 1

        user_db.update_one(
            {'_id':ID}, 
            {'$set':{"Convert":self.number}}
        )
        self.request()

    def request(self):
        self.send = []

        query = {"_id":"Crypto"}
        info =  {"_id":0, "USD":1}

        data = [info for info in finance.find(query, info)]

        for key in data[0]['USD']:   
            if key in crypto_currency:
                name = data[0]['USD'][key][0]
                price = float(data[0]['USD'][key][1])
                price = round(price*self.number, 4)
                symbol = data[0]['USD'][key][2]

                add = f"💵 {name}/USD | {price}{symbol}"
                self.send.append(add)

        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        rate = language.translate(self.message, data, 'rate') 
        keypad = keyboard.alternative_currency_keyboard(self.message, "crypto")

        bot.send_message(
            self.message.chat.id, 
            f"{rate}{day}\n{self.send}",
            reply_markup=keypad
        )

class AlternativeCrypto:
    def __init__(self, call, currency):
        self.call = call
        self.currency = currency.split()[1]
        self.send = []
        ID = call.from_user.id
        
        for number in user_db.find({'_id':ID}):
            number = float(number['Convert'])

        query = {"_id":"Crypto"}
        info =  {"_id":0, self.currency:1}

        data = [info for info in finance.find(query, info)]

        for key in data[0][self.currency]:   
            if key in crypto_currency:
                name = data[0][self.currency][key][0]
                price = float(data[0][self.currency][key][1])
                price = round(price*number, 4)
                symbol = data[0][self.currency][key][2]

                add = f"💵 {name}/{self.currency} | {price}{symbol}"
                self.send.append(add)

        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        rate = language.translate(self.call, data, 'rate') 
        keypad = keyboard.alternative_currency_keyboard(self.call, "crypto")

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=f"{rate}{day}\n{self.send}",
            reply_markup=keypad
        ) 
