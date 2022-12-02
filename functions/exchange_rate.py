import pymongo
import random
import time 
import __main__
import config
import parser
import language
import keyboard
import logs

main = __main__
bot = main.bot

currency_list = [
    'American Dollar', 'Euro', 'British Pound', 
    'Czech Koruna','Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Chinese Yuan Renminbi',
    'Ukraine Hryvnia'
]

crypto_list = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC",
] 

client = pymongo.MongoClient(config.database)
db = client["finances"]["Users"]

class ExchangeRate:
    def __init__(self, message):
        language = message.from_user.language_code
        
        keyboard.inline(message)
        if language in ['ru', 'be']:
            bot.send_message(
                message.chat.id,
                "¯\_(ツ)_/¯ I do not understand your language",
                reply_markup=keyboard.link
            )    

        else:
            self.main(message)
                
    def main(self, message):
        ID = message.from_user.id
        language.course(message)
        
        if message.text in ['💵 Crypto', '💵 Криптовалюта']:
            self.crypto_status(message)
                
        else:
            if len(message.text.split()) == 2:
                text = message.text.split()
                
                if text[0].isalnum() is False:
                    currency_name = text[1]
                    number = 1

                elif text[0].isalpha():
                    currency_name = text[0]
                    number = text[1]

                else:
                    currency_name = text[1]
                    number = text[0]

            else:
                currency_name = message.text
                number = 1                

            db.update_one({'_id':ID}, {'$set':{"Convert":number}})
            self.message_data(currency_name, number, message)
        
    def message_data(self, currency_name, number, message):
        code = 0 if currency_name.upper() in ['BTC', 'ETH'] else 1
        
        if currency_name.upper() in config.block_currency_list: 
            self.block(message, currency_name)            
        
        else:
            parser.Currency(currency_name, code, currency_list, number)
            self.currency_status(message, currency_name.upper(), number)

    def currency_status(self, message, currency_name, number):
        day = time.strftime("%d.%m.%y")
        
        keyboard.alternative_currency_key(message, currency_name)
        markup = None if currency_name in ['BTC', 'ETH'] else keyboard.currency
        
        if parser.status_code == 200 and parser.status is True:
            bot.send_message(
                message.chat.id, 
                f"{language.rate}{day}\n{parser.send}",
                reply_markup=markup
            )

        elif parser.status is False:
            bot.send_message(message.chat.id, language.currency_user_error)

        else:
            logs.server(parser.status_code, parser.url, parser.name)
            bot.send_message(message.chat.id, language.server_error)

    def crypto_status(self, message):
        day = time.strftime("%d.%m.%y")
        parser.Crypto("USD", crypto_list)
        
        keyboard.alternative_currency_key(message, "crypto")
        if parser.status is True: 
            bot.send_message(
                message.chat.id, 
                f"{language.rate}{day}\n{parser.send}",
                reply_markup=keyboard.currency
            )
        
        else:
            logs.server(parser.status_code, parser.url, parser.name)
            bot.send_message(message.chat.id, language.server_error)
        
    def block(self, message, currency_name):
        block_message = random.randrange(1, 4)

        if block_message == 1:
            bot.send_video(message.chat.id, config.glory_to_Ukraine) 

        elif block_message == 2:
            parser.Currency("UAH", 1, currency_list, 1)
            self.currency_status(message, "UAH")
        
        else:
            bot.send_audio(message.chat.id, config.anthem_of_Ukraine) 
                  
class AlternativeCurrency:
    def __init__(self, call, currency_name):
        language.course(message=call)
        ID = call.from_user.id

        if currency_name in ["c UAH", "c EUR", "c GBP"]:
            parser.Crypto(currency_name.split()[1], crypto_list)
            keyboard.alternative_currency_key(
                message=call, 
                currency_name=currency_name
            )

            markup = keyboard.currency

        else:
            query = {'_id':ID}
            for number in db.find(query, {'_id':0, 'Convert':1}):
                number = number['Convert']
                
            parser.Currency(currency_name, 0, currency_list, number)
            markup = None

        self.status(call, markup)
        
    def status(self, call, markup):
        day = time.strftime("%d/%m/%y")
        
        if parser.status_code == 200 or parser.status is True:
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.id,
                text=f"{language.rate}{day}\n{parser.send}",
                reply_markup=markup 
            ) 

        else:
            logs.server(parser.status_code, parser.url, parser.name)
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.id,
                text=language.server_error
            )
