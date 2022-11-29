import random
import sqlite3
import time 
import __main__
import config
import parser
import language
import keyboard
import logs

main = __main__
bot = main.bot

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

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
            if message.text.split()[0].isalpha():
                try:
                    currency_name = message.text.split()[0]
                    number = message.text.split()[1]
                    
                except:
                    currency_name = message.text
                    number = 1
                
            elif message.text.split()[1].isalpha():
                currency_name = message.text.split()[1]
                number = message.text.split()[0]
                
            else:       
                currency_name = message.text.split()[1]
                number = 1
            
            cursor.execute(f"UPDATE user_data SET convert = '{number}' WHERE id = {ID}")
            connect.commit()
            
            self.message_data(currency_name, number, message)
        
    def message_data(self, currency_name, number, message):
        code = 0 if currency_name.upper() in ['BTC', 'ETH'] else 1
        ID = message.from_user.id
        
        cursor.execute(f"SELECT convert FROM user_data WHERE id = '{ID}'")
        number = cursor.fetchall()[0][0]
        
        if currency_name.upper() in config.block_currency_list: 
            self.block(message, currency_name)            
        
        else:
            parser.Currency(currency_name, code, currency_list, number)
            self.currency_status(message, currency_name.upper())

    def currency_status(self, message, currency_name):
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

        cursor.execute(f"SELECT convert FROM user_data WHERE id = '{ID}'")
        number = cursor.fetchall()[0][0]

        if currency_name in ["c UAH", "c EUR", "c GBP"]:
            parser.Crypto(currency_name.split()[1], crypto_list)
            keyboard.alternative_currency_key(
                message=call, 
                currency_name=currency_name
            )

            markup = keyboard.currency

        else:
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
