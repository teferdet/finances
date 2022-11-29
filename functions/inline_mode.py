import __main__
import logs 
import parser
import time
import config
import keyboard
import language 
from telebot import types 

bot = __main__.bot

currency_list = [
    'American Dollar', 'Euro', 'British Pound', 
    'Czech Koruna','Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Chinese Yuan Renminbi',
    'Ukraine Hryvnia', 'Bulgarian Lev', 'Israeli New Shekel',
    'Swedish Krona','Norwegian Krone'
]

@bot.inline_handler(func=lambda query: True)
class InlineMode:
    def __init__(self, inline_query):
        language_code = inline_query.from_user.language_code
        wait = "¯\_(ツ)_/¯ I do not understand your language"
        
        if language_code in ["ru", "be"]:
            markup = types.InlineQueryResultArticle(
                "1", wait,
                types.InputTextMessageContent(wait)
            )
            bot.answer_inline_query(inline_query.id, [markup])
            
        else:
            self.main_menu(inline_query)
    
    def main_menu(self, inline_query):
        language.inline(inline_query)
        
        if inline_query.query == '': 
            markup = types.InlineQueryResultArticle(
               '1', language.choose,
                types.InputTextMessageContent(language.choose_error)
            )
            bot.answer_inline_query(inline_query.id, [markup])

        else:
            self.message_data(inline_query)
    
    def message_data(self, inline_query):
        if inline_query.query.split()[0].isalpha():
            try:
                currency_name = inline_query.query.split()[0]
                number = inline_query.query.split()[1]
    
            except:
                currency_name = inline_query.query.split()[0]
                number = 1
        
        else:
            try:
                currency_name = inline_query.query.split()[1]
                number = inline_query.query.split()[0]

            except:
                currency_name = ''
                number = 0
        
        if currency_name.upper() in config.block_currency_list: 
            self.block(inline_query)
        
        elif currency_name.upper() in ['BTC', 'ETH']:
            parser.Currency(currency_name, 0, currency_list, number)
            self.server_status(inline_query)
        
        else:
            parser.Currency(currency_name, 1, currency_list, number)
            self.server_status(inline_query)
        
    def server_status(self, inline_query):
        language.inline(inline_query)
        
        if parser.status_code == 200 and parser.status is True:
            self.send_list = parser.send_list
            self.send(inline_query, self.send_list)
        
        elif parser.status is False:
            markup = types.InlineQueryResultArticle(
                '1', language.user_error,
                types.InputTextMessageContent(language.user_error)
            )
            bot.answer_inline_query(inline_query.id, [markup])
            
        else:
            markup = types.InlineQueryResultArticle(
                '1', language.server_error, 
                types.InputTextMessageContent(language.server_error,)
            )
            logs.server(parser.status_code, parser.url, parser.name)
            bot.answer_inline_query(inline_query.id, [markup])
    
    def send(self, inline_query, send_list):
        language.inline(inline_query)
        
        number = 1
        markup = [
            types.InlineQueryResultArticle(
                number, language.warning,
                types.InputTextMessageContent(language.warning_info)
            )
        ]
        
        for inline in self.send_list:
            number += 1
            add = types.InlineQueryResultArticle(
                number, inline,
                types.InputTextMessageContent(inline)
            )
            markup.append(add)
            
        bot.answer_inline_query(inline_query.id, markup)
        
    def block(self, inline_query):
        markup = types.InlineQueryResultArticle(
           '1', "Слава Україні",
            types.InputTextMessageContent("Слава Україні\nГероям Слава")
        )
        bot.answer_inline_query(inline_query.id, [markup])
