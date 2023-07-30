import re 
import pymongo
import random
import time 
import __main__ as main
import config
import parser
import language
import keyboard
import logs

bot = main.bot

currency_list = [
    'British Pound','Bulgarian Lev', 'Chinese Yuan Renminbi',
    'Czech Koruna','Euro', 'Indian Rupee', 'American Dollar'
    'Israeli New Shekel', 'Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Turkish Lira', 'Ukraine Hryvnia'
]

crypto_list = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC",
] 

client = pymongo.MongoClient(config.database)
user_db = client["finances"]["Users"]
settings = client["finances"]["Settings"]

class ExchangeRate:
    def __init__(self, message):
        self.message = message
        language = message.from_user.language_code
        keyboard.inline(message)
        
        if language in ['ru', 'be']:
            bot.send_message(
                message.chat.id,
                "¯\_(ツ)_/¯ I do not understand your language",
                reply_markup=keyboard.link
            )    

        else:
            self.main()
                
    def main(self):
        ID = self.message.from_user.id
        language.course(self.message)
        
        if self.message.text in ['💵 Crypto', '💵 Криптовалюта']:
            self.crypto_status()
                
        else:
            self.currency_name = re.findall(r"\b[a-zA-Z]{3}\b", self.message.text)
            self.number = re.findall(r"\d+\.*\d*", self.message.text)

            if self.currency_name != []:
                self.currency_name = self.currency_name[0].upper()
                self.number = self.number[0] if self.number != [] else 1

                user_db.update_one({'_id':ID}, {'$set':{"Convert":self.number}})
                self.message_data()

            else: 
                bot.send_message(self.message.chat.id, language.currency_user_error)

    def message_data(self):
        index = 0 if self.currency_name.upper() in ['BTC', 'ETH'] else 1
        
        query = {'_id':0}
        for block_currency_list in settings.find(query, {'_id':0, 'block currency list':1}):
            block_currency_list = block_currency_list['block currency list']
        
        if self.currency_name.upper() in block_currency_list: 
            self.block()            
            
        else:
            parser.Currency(self.currency_name, index, currency_list, self.number)
            self.currency_status(self.currency_name)
        
    def currency_status(self, currency):
        day = time.strftime("%d.%m.%y")
        
        keyboard.alternative_currency_key(self.message, currency)
        if currency in ['BTC', 'ETH']:
            keypad = None 
        
        else:
            keypad = keyboard.currency
        
        if parser.status_code == 200 and parser.status is True:
            bot.send_message(
                self.message.chat.id, 
                f"{language.rate}{day}\n{parser.send}",
                reply_markup=keypad
            )

        elif parser.status is False:
            bot.send_message(self.message.chat.id, language.currency_user_error)

        else:
            bot.send_message(self.message.chat.id, language.server_error)

    def crypto_status(self):
        day = time.strftime("%d.%m.%y")
        parser.Crypto("USD", crypto_list)
        
        keyboard.alternative_currency_key(self.message, "crypto")
        if parser.status is True: 
            bot.send_message(
                self.message.chat.id, 
                f"{language.rate}{day}\n{parser.send}",
                reply_markup=keyboard.currency
            )
        
        else:
            bot.send_message(self.message.chat.id, language.server_error)
        
    def block(self):
        block_message = random.randrange(1, 4)
        query = {'_id':0}
        
        for file in settings.find(query, {'_id':0, 'file id':1}):
            glory_to_Ukraine = file['file id']['glory to Ukraine']
            anthem_of_Ukraine = file['file id']['anthem of Ukraine']
    
        if block_message == 1:
            bot.send_video(self.message.chat.id, glory_to_Ukraine) 

        elif block_message == 2:
            bot.send_audio(self.message.chat.id, anthem_of_Ukraine)
        
        else: 
            parser.Currency("UAH", 1, currency_list, 1)
            self.currency_status("UAH")
                  
class AlternativeCurrency:
    def __init__(self, call, currency_name):
        language.course(message=call)
        ID = call.from_user.id
        self.call = call 
        
        if currency_name.split()[0] in ["c"]:
            parser.Crypto(currency_name.split()[1], crypto_list)
            keyboard.alternative_currency_key(
                message=self.call, 
                currency_name=currency_name
            )

            self.keypad = keyboard.currency

        else:
            query = {'_id':ID}
            for number in user_db.find(query, {'_id':0, 'Convert':1}):
                number = number['Convert']
                
            parser.Currency(currency_name, 0, currency_list, number)
            self.keypad = None

        self.status()
        
    def status(self):
        day = time.strftime("%d.%m.%y")
        
        if parser.status_code == 200 or parser.status is True:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=f"{language.rate}{day}\n{parser.send}",
                reply_markup=self.keypad
            ) 

        else:
            logs.server(parser.status_code, parser.url, parser.name)
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=language.server_error
            )
