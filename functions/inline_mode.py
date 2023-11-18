import re 
import time 
import pymongo
import config
import __main__ as main 
import logs
import parser
import keyboard
import language 
from telebot import types 

bot = main.bot 
client = pymongo.MongoClient(config.database)
currency = client['finances']['Currency']
settings = client['finances']['Settings']

data = 'inline mode'
currency_list = [
    'Argentine Peso', 'Australian Dollar', 'British Pound',
    'Bulgarian Lev', 'Canadian Dollar', 'Chinese Yuan Renminbi',
    'Czech Koruna', 'Danish Krone', 'Egyptian Pound',
    'Euro', 'Iceland Krona', 'Indian Rupee',
    'Israeli New Shekel', 'Japanese Yen', 'Korean Won',
    'Norwegian Krone', 'Polish Zloty', 'Romanian Leu',
    'Singapore Dollar', 'Swedish Krona', 'Swiss Franc',
    'Turkish Lira', 'Ukraine Hryvnia', 'American Dollar'
]
crypto_list = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC"
]
currency_for_crypto = [
    'USD', "EUR", "GBP",
    "UAH", "PLN", "CZK"
]
company = [
    'APPL', 'META', 'AMZN', 'ADBE',
    'PYPL', 'GOOGL', 'INTC', 'AMD',
    'NFLX', 'MSFT', 'ORCL', 'NVDA'
] 

@bot.inline_handler(func=lambda query: True)
class InlineMode: 
    def __init__(self, inline_query):
        self.inline_query = inline_query
        language_code = self.inline_query.from_user.language_code
        
        wait = "¯\_(ツ)_/¯ I do not understand your language"
        
        if language_code in ["ru", "be"]:
            keypad = types.InlineQueryResultArticle(
                "1", wait, types.InputTextMessageContent(wait)
            )
            bot.answer_inline_query(self.inline_query.id, [keypad])
            
        else:
            self.message_handler()
    
    def message_handler(self):
        text = self.inline_query.query
        currency_name = re.findall(r"\b[a-zA-Z]{3}\b", text)

        if text != '':
            if text.split()[0] == "!":
                CryptoHandler(self.inline_query, currency_name)
            
            elif text.split()[0] == "share":
                ShareHandler(self.inline_query)

            elif currency_name != []:
                CurrencyHandler(self.inline_query, currency_name)

            else:
                user_error = language.translate(self.inline_query, data, "user error")

                bot.answer_inline_query(self.inline_query.id, [
                    types.InlineQueryResultArticle(
                        '1', user_error,
                        types.InputTextMessageContent(user_error)
                    )
                ])

        else:
            choose = language.translate(self.inline_query, data, "choose")
            choose_error = language.translate(self.inline_query, data, 'choose error')
            choose_warning = language.translate(self.inline_query, data, 'choose warning')

            bot.answer_inline_query(self.inline_query.id, [
                types.InlineQueryResultArticle(
                    id='1', title=choose, description=choose_warning,
                    input_message_content=types.InputTextMessageContent(choose_error)
                )
            ])

class CurrencyHandler: 
    def __init__(self, inline_query, currency_name):
        self.inline_query = inline_query
        
        self.currency_name = currency_name[0].upper()
        self.number = re.findall(r"\d+\.*\d*", self.inline_query.query)
        self.number = self.number[0] if self.number != [] else 1

        self.processing()

    def processing(self):
        block_list = [
            item['block currency list']
            for item in settings.find({'_id':0})
        ]

        if self.currency_name in block_list[0]:
            self.block()
        
        else:
            self.index = 0 if self.currency_name.upper() in ['BTC', 'ETH'] else 1
            self.request()
    
    def request(self):
        answer = parser.CurrencyHandler(
            self.currency_name, self.number,
            currency_list, self.index
        )

        if answer != "server error" and answer != "bad request":
            self.send_list = parser.cash['currency'][self.currency_name]['inline']
            self.publishing()

        else:
            if answer == "server error":
                text = language.translate(self.inline_query, data, 'server error')

            elif answer == "bad request":
                text = language.translate(self.inline_query, data, "user error")
    
            keypad = types.InlineQueryResultArticle(
                '1', text, 
                types.InputTextMessageContent(text)
            )

            bot.answer_inline_query(self.inline_query.id, [keypad])
    
    def publishing(self):
        warning = language.translate(self.inline_query, data, 'warning')
        warning_info = language.translate(self.inline_query, data, 'warning info')

        number = 1
        keypad = [
            types.InlineQueryResultArticle(
                number, warning,
                types.InputTextMessageContent(warning_info)
            )
        ]
        
        for item in self.send_list:
            number += 1
            add = types.InlineQueryResultArticle(
                number, item,
                types.InputTextMessageContent(item)
            )
            keypad.append(add)

        bot.answer_inline_query(self.inline_query.id, keypad)

    def block(self):
        bot.answer_inline_query(self.inline_query.id, [
            types.InlineQueryResultArticle(
                '1', "Слава Україні",
                types.InputTextMessageContent("Слава Україні\nГероям Слава")
            )
        ])

class CryptoHandler:
    def __init__(self, inline_query, currency_name):
        self.inline_query = inline_query
        self.currency_name = currency_name

        warning = language.translate(self.inline_query, data, "warning crypto")

        bot.answer_inline_query(self.inline_query.id, [
            types.InlineQueryResultArticle(
                id='1', title=warning, description="USD, EUR, GBP, UAH, PLN, CZK",
                input_message_content=types.InputTextMessageContent(warning)
            )
        ])

        self.message_handler()

    def message_handler(self):
        if self.currency_name != []: 
            self.currency_name = self.currency_name[0].upper()

            if self.currency_name in currency_for_crypto:
                self.number = re.findall(r"\d+\.*\d*", self.inline_query.query)
                self.number = self.number[0] if self.number != [] else 1

                self.publishing()

    def publishing(self):
        number = 1
        warning = language.translate(self.inline_query, data, 'warning')
        warning_info = language.translate(self.inline_query, data, 'warning info')

        self.keypad = [
            types.InlineQueryResultArticle(
                number, warning,
                types.InputTextMessageContent(warning_info)
            )
        ]

        query = {"_id":"Crypto"}
        info =  {"_id":0, self.currency_name:1}

        for info in currency.find(query, info):
            database = info[self.currency_name]

        for key in database:   
            if key in crypto_list:
                name = database[key][0]
                price = float(database[key][1])
                price = round(price*float(self.number), 4)
                symbol = database[key][2]

                number += 1
                add = f"💵 {name}/{self.currency_name} | {price}{symbol}"
                
                self.keypad.append(
                    types.InlineQueryResultArticle(
                        number, add,
                        types.InputTextMessageContent(add)
                    )
                )
        
        bot.answer_inline_query(self.inline_query.id, self.keypad)

class ShareHandler:
    def __init__(self, inline_query):
        self.inline_query = inline_query

        self.number = re.findall(r"\d+\.*\d*", self.inline_query.query)
        self.number = self.number[0] if self.number != [] else 1
        
        self.publishing()

    def publishing(self):
        number = 1
        warning = language.translate(self.inline_query, data, 'warning')
        warning_info = language.translate(self.inline_query, data, 'warning info')

        self.keypad = [
            types.InlineQueryResultArticle(
                number, warning,
                types.InputTextMessageContent(warning_info)
            )
        ]

        query = {"_id":"Shares"}
        info = [info for info in currency.find(query)][0]
    
        for key in info:   
            if key in company:    
                symbol = info[key][0]
                price = float(info[key][2])
                price = round(price*float(self.number), 4)

                number += 1
                add = f"💵 {symbol} | {price}$"
                self.keypad.append(
                    types.InlineQueryResultArticle(
                        number, add,
                        types.InputTextMessageContent(add)
                    )
                )
        
        bot.answer_inline_query(self.inline_query.id, self.keypad)

