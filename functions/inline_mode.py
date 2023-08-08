import __main__
import logs 
import parser
import pymongo
import re 
import time
import config
import keyboard
import language 
from telebot import types 

bot = __main__.bot

client = pymongo.MongoClient(config.database)
settings = client["finances"]["Settings"]

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
data = 'inline mode'

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
            self.menu()
    
    def menu(self): 
        if self.inline_query.query == '': 
            choose = language.translate(self.inline_query, data, "choose")
            choose_error = language.translate(self.inline_query, data, 'choose error') 
            
            keypad = types.InlineQueryResultArticle(
               '1', choose,
                types.InputTextMessageContent(choose_error)
            )
            bot.answer_inline_query(self.inline_query.id, [keypad])

        else:
            self.message_data()
    
    def message_data(self):
        self.currency_name = re.findall(r"\b[a-zA-Z]{3}\b", self.inline_query.query)
        self.number = re.findall(r"\d+\.*\d*", self.inline_query.query)

        if self.currency_name != []:
            self.currency_name = self.currency_name[0].upper()
            self.number = self.number[0] if self.number != [] else 1

            self.processing()

        else:
            user_error = language.translate(self.inline_query, data, "user error")

            keypad = types.InlineQueryResultArticle(
                '1', user_error,
                types.InputTextMessageContent(user_error)
            )
            bot.answer_inline_query(self.inline_query.id, [keypad])

    def processing(self):
        for item in settings.find({'_id':0}):
            block_list = item['block currency list']
        
        if self.currency_name in block_list: 
            self.block()
        
        else:
            self.index = 0 if self.currency_name.upper() in ['BTC', 'ETH'] else 1
            self.server_status()
        
    def server_status(self):
        parser.Currency(self.currency_name, self.index, currency_list, self.number)

        if parser.status_code == 200 and parser.status is True:
            self.send_list = parser.send_list
            self.publishing()
        
        else:
            if parser.status is False:
                text = language.translate(self.inline_query, data, "user error")
                
            else:
                text = language.translate(self.inline_query, data, 'server error'
                )

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
        keypad = types.InlineQueryResultArticle(
           '1', "Слава Україні",
            types.InputTextMessageContent("Слава Україні\nГероям Слава")
        )
        bot.answer_inline_query(self.inline_query.id, [keypad])
