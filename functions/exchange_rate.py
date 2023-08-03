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
    'British Pound','Bulgarian Lev', 'Chinese Yuan Renminbi',
    'Czech Koruna','Euro', 'Indian Rupee', 'American Dollar'
    'Israeli New Shekel', 'Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Turkish Lira', 'Ukraine Hryvnia'
]

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
        language.course(self.message)

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
            bot.send_message(self.message.chat.id, language.currency_user_error)
    
    def request(self):
        keyboard.alternative_currency_key(self.message, self.currency_name)

        if self.currency_name in ['BTC', 'ETH']:
            index = 0
            self.keypad = None 
        
        else:
            currency = self.currency_name
            self.keypad = keyboard.currency
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
        
        if parser.status_code == 200 and parser.status is True:
            bot.send_message(
                self.message.chat.id, 
                f"{language.rate}{day}\n{parser.send}",
                reply_markup=self.keypad
            )

        elif parser.status is False:
            bot.send_message(self.message.chat.id, language.currency_user_error)

        else:
            bot.send_message(self.message.chat.id, language.server_error)

class AlternativeCurrency:
    def __init__(self, call, currency_name):
        language.course(message=call)
        ID = call.from_user.id
        self.call = call 
        
        query = {'_id':ID}
        for number in user_db.find(query, {'_id':0, 'Convert':1}):
            number = number['Convert']
            
        parser.Currency(currency_name, 0, currency_list, number)
        self.keypad = None

        self.publishing()
        
    def publishing(self):
        day = time.strftime("%d.%m.%y")
        
        if parser.status_code == 200 or parser.status is True:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=f"{language.rate}{day}\n{parser.send}",
                reply_markup=self.keypad
            ) 

        else:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=language.server_error
            )
