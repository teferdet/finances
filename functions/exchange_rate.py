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
user_db = client["finances"]["Users"]
settings = client["finances"]["Settings"]

currency_list = [
    'American Dollar', 'British Pound','Bulgarian Lev',
    'Chinese Yuan Renminbi', 'Czech Koruna', 'Euro', 'Indian Rupee', 
    'Israeli New Shekel', 'Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Turkish Lira', 'Ukraine Hryvnia'    
]
data = 'exchange rate'

class ExchangeRate:
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
            self.message_handler()
    
    def message_handler(self):
        ID = self.message.from_user.id

        self.currency_name = re.findall(r"\b[a-zA-Z]{3}\b", self.message.text)
        self.number = re.findall(r"\d+\.*\d*", self.message.text)

        if self.currency_name != []:
            self.currency_name = self.currency_name[0].upper()
            self.number = self.number[0] if self.number != [] else 1

            user_db.update_one(
                {'_id':ID}, 
                {'$set':{"Convert":self.number}}
            )
            self.request()

        else:
            text = language.translate(self.message, data, "currency user error")
            bot.send_message(self.message.chat.id, text)
    
    def request(self):
        self.keypad = keyboard.alternative_currency_keyboard(self.message, self.currency_name)

        if self.currency_name in ['BTC', 'ETH']:
            index = 0
            self.keypad = None 
        
        else:
            currency = self.currency_name
            index = 1

        query = {'_id':0}
        for data in settings.find(query, {'_id':0, 'block currency list':1}):
            block_currency_list = data['block currency list']
        
        if self.currency_name.upper() in block_currency_list: 
            bot.send_message(self.message.chat.id, "❌")           
            
        else:
            parser.Currency(
                self.currency_name, index, 
                currency_list, self.number
            )
            self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        keypad = None

        if parser.status_code == 200 and parser.status is True:
            rate = language.translate(self.message, data, 'rate') 
            text = f"{rate}{day}\n{parser.send}",
            keypad = self.keypad

        elif parser.status is False:
            text = language.translate(self.message, data, "currency user error")

        else:
            text = language.translate(self.message, data, "server error")
        
        bot.send_message(
            self.message.chat.id, 
            text, reply_markup=self.keypad
        )

class AlternativeCurrency:
    def __init__(self, call, currency_name):
        ID = call.from_user.id
        self.call = call 
        
        query = {'_id':ID}
        for number in user_db.find(query, {'_id':0, 'Convert':1}):
            number = number['Convert']
            
        parser.Currency(currency_name, 0, currency_list, number)
        self.publishing()
        
    def publishing(self):
        day = time.strftime("%d.%m.%y")
        
        if parser.status_code == 200 or parser.status is True:
            rate = language.translate(self.call, data, 'rate') 
            text = f"{rate}{day}\n{parser.send}"

        else:
            text = language.translate(self.call, data, "server error")

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=text
        )
