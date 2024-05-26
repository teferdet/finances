from time import strftime
from json import load
from messages_handler import bot, client
from functions.text_processing import TextProcessing
from functions.language import translate
from functions.keyboard import er_keypad

users_database = client["Users"]

class ExchangeRate:
    def __init__(self, message: dict):
        self.message = message
        response = TextProcessing(self.message.text)
        self.currencis_data = response.get_results()
        self.currencis = response.get_codes()

        if self.currencis_data:
            self.request()

        else:
            text = translate(self.message, "exchange rate")["input error"] 
            bot.send_message(self.message.chat.id, text)

    def request(self):
        from parser.parser_handler import CurrenciesHandler

        ID = self.message.from_user.id        
        self.keypad = None
        index = 1        

        if any(i in ["BTC", "ETH"] for i in self.currencis):
            index = 0
        
        elif len(self.currencis) == 1:
            index = 1
            self.keypad = er_keypad(
                self.message, self.currencis_data[0][0], 
                self.currencis_data[0][1], 0
            )
           
        self.parser = CurrenciesHandler(
            self.currencis_data, convert_currencies(ID), index
        )
        
        self.publishing()
            
    def publishing(self):
        day = strftime("%d.%m.%y")

        if self.parser in ["server error", "bad request"]:
            text = translate(self.message, "exchange rate")[self.parser] 
        
        else:
            text = translate(self.message, "exchange rate")["main rate"] 
            text = text.format(day, self.info(), self.parser)

        bot.send_message(
            self.message.chat.id, text, 
            reply_markup=self.keypad
        )

    def info(self) -> str:
        info = []

        for currency in self.currencis_data:
            for j in currencies_information():
                code = j['code']

                if currency[0] == code:
                    emoji = j['emoji']
                    symbol = j['symbol']

                    info.append(f"{emoji} {code} {currency[1]}{symbol}")

        return ", ".join(info)

class AlternativeConvert:
    def __init__(self, call:dict, currency:str, amount:float, index:int):
        from parser.parser_handler import CurrenciesHandler

        self.call = call
        self.currency = currency
        self.amount = amount 
        ID = self.call.from_user.id 

        self.parser = CurrenciesHandler(
            [[self.currency, self.amount]],
            convert_currencies(ID), index
        )
        
        if index == 1: self.index = 0
        elif index == 0: self.index = 1

        self.publishing()
        
    def publishing(self):
        day = strftime("%d.%m.%y")
        
        if self.parser == "server error":
            text = translate(self.call, "exchange rate")["server error"]
            keypad = None

        else:
            for i in currencies_information():
                code = i['code']
                if code == self.currency:
                    emoji = i['emoji']
                    symbol = i['symbol']

                    info = f"{emoji} {code} {self.amount}{symbol}"

            text = translate(self.call, "exchange rate")["main rate"] 
            text = text.format(day, info, self.parser)
            keypad = er_keypad(self.call, self.currency, self.amount, self.index)

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=text,
            reply_markup=keypad
        )

def currencies_information() -> dict:
    path = "handlers/functions/currencies_data.json"
    with open(path, encoding="utf-8") as f:
        return load(f)

def convert_currencies(ID: int) -> list:
    for i in users_database.find({"_id":ID}):
        return i["Fiat currency"]