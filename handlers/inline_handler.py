from re import findall
from types import NoneType
from telebot import types
from jsoncfg import load_config
from messages_handler import bot, client
from parser.parser_handler import CurrenciesHandler, CACHE
from functions.language import translate
from functions.text_processing import TextProcessing

database = client["Currency"]

@bot.inline_handler(lambda query: "stocks" in query.query)
class Stocks:
    def __init__(self, inline_query):
        self.inline_query = inline_query

        amount = findall(r"\d+\.*\d*", self.inline_query.query)
        self.amount = amount[0] if amount != [] else 1

        text = translate(self.inline_query, "inline mode")
        self.warning = text["warning"]
        self.warning_info = text["warning info"]

        self.publishing()

    def publishing(self):
        self.keypad = [
            types.InlineQueryResultArticle(
                1, self.warning, types.InputTextMessageContent(self.warning_info)
            )
        ]

        query = {"_id":"Shares"}
        self.data = [i for i in database.find(query)][0]
        self.create_button()
        
        bot.answer_inline_query(self.inline_query.id, self.keypad)

    def create_button(self):
        number = 1

        for key in self.data:   
            if key in config("company"):    
                symbol = self.data[key][0]
                price = float(self.data[key][2])
                price = round(price*float(self.amount), 4)

                number += 1
                item = f"💵 {symbol} {price}$"
                self.keypad.append(
                    types.InlineQueryResultArticle(
                        number, item, types.InputTextMessageContent(item)
                    )
                )

@bot.inline_handler(lambda query: "crypto" in query.query)
class Crypto:
    def __init__(self, inline_query: dict):
        self.inline_query = inline_query
        text = self.inline_query.query.split()

        if len(text) == 1 or not isinstance(text[1], str):
            warning = translate(self.inline_query, "inline mode")["warning crypto"]

            bot.answer_inline_query(self.inline_query.id, [
                types.InlineQueryResultArticle(
                    id='1', title=warning, description="USD, EUR, GBP, UAH, PLN, CZK",
                    input_message_content=types.InputTextMessageContent(warning)
                )
            ])
        
        else:
            self.text_handler()

    def text_handler(self):
        text = self.inline_query.query
        text_data = findall(r"\b[a-zA-Z]{3}\b", text)

        if text_data != []:
            self.currency = text_data[0].upper()

            if self.currency in config("convert_crypto"):
                amount = findall(r"\d+\.*\d*", self.inline_query.query)
                self.amount = amount[0] if amount != [] else 1

                self.publishing()
    
    def publishing(self):
        text = translate(self.inline_query, "inline mode")
        self.warning = text["warning"]
        self.warning_info = text["warning info"]

        self.keypad = [
            types.InlineQueryResultArticle(
                1, self.warning, types.InputTextMessageContent(self.warning_info)
            )
        ]

        self.create_button()
        
        bot.answer_inline_query(self.inline_query.id, self.keypad)

    def create_button(self):
        query = {"_id":"Crypto"}
        data = [i[self.currency] for i in database.find(query)][0]
        number = 1

        for key in data:   
            if key in config("crypto"):    
                name = data[key][0]
                price = float(data[key][1])
                price = round(price*float(self.amount), 4)
                symbol = data[key][2]

                number += 1
                item = f"💵 {name}/{self.currency} {price}{symbol}"
                
                self.keypad.append(
                    types.InlineQueryResultArticle(
                        number, item, types.InputTextMessageContent(item)
                    )
                )

@bot.inline_handler(func=lambda query: True)
class ExchangeRate:
    def __init__(self, inline_query: dict):
        self.inline_query = inline_query
        text = self.inline_query.query

        if text == "":
            data = translate(self.inline_query, "inline mode") 

            bot.answer_inline_query(self.inline_query.id, [
                types.InlineQueryResultArticle(
                    id='1', title=data["choose"], description=data["choose warning"],
                    input_message_content=types.InputTextMessageContent(
                        data["choose error"]
                    )
                )
            ])

        else: 
            self.text_handler()
    
    def text_handler(self):
        text = self.inline_query.query
        response = TextProcessing(text)
        self.currencis_data = response.get_results()
        currencis = response.get_codes()

        if self.currencis_data != []:
            try:
                self.currency = self.currencis_data[0][0]
                self.index = 1

                if any(i in ["BTC", "ETH"] for i in currencis):
                    self.index = 0

                self.request_data()
            
            except NoneType:
                pass

    def request_data(self):
        self.CACHE = CACHE
        currency_list = config("convert_currencies")
        request = CurrenciesHandler(
            self.currencis_data,
            currency_list, self.index
        )

        if request not in ["server error", "bad request"]:
            self.send_list = CACHE[self.currency]['inline']
            self.publishing()

        else:
            text = translate(self.inline_query, "inline mode")[request]
    
            keypad = types.InlineQueryResultArticle(
                '1', text, types.InputTextMessageContent(text)
            )

            bot.answer_inline_query(self.inline_query.id, [keypad])

    def publishing(self):
        translate_text = translate(self.inline_query, "inline mode")
        warning = translate_text["warning"]
        warning_info = translate_text["warning info"]

        number = 1
        keypad = [
            types.InlineQueryResultArticle(
                number, warning,
                types.InputTextMessageContent(warning_info)
            )
        ]
        
        data = self.CACHE[self.currency]["inline"]
        for i in data:
            number += 1
            item = types.InlineQueryResultArticle(
                number, i, types.InputTextMessageContent(i)
            )
            keypad.append(item)

        bot.answer_inline_query(self.inline_query.id, keypad)

def config(option: str) -> str:
    config = load_config("files/config.json")
    currencies_settings = config.currencies_settings
    value = [i.value for i in currencies_settings[option]]
    
    return value
