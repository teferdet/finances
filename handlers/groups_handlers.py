from time import strftime
from json import load
from messages_handler import bot, client
from parser.parser_handler import CurrenciesHandler
from functions.text_processing import TextProcessing
from functions.language import translate
from functions.keyboard import group_keypad

database = client["Groups"]

class GroupsHandler:
    def __init__(self, message: dict):
        self.message = message
        self.chat = message.chat.id

        response = TextProcessing(self.message.text)
        self.curensies = response.get_codes()
        self.results = response.get_results()
        
        if self.results:
            for item in database.find({"_id":self.chat}):
                self.output_currenies = item["Output"]
                input_currenies = item["Input"]
            
            if any(i in input_currenies for i in self.curensies): 
                self.request()

    def request(self):        
        index = 1
        if any(i in ["BTC", "ETH"] for i in self.curensies):
            index = 0

        self.parser = CurrenciesHandler(
            self.results, self.output_currenies, index
        )
        
        self.publishing()

    def publishing(self):
        day = strftime("%d.%m.%y")

        if self.parser not in ["server error", "bad request"]:
            text = translate(self.message, "exchange rate")["main rate"] 
            text = text.format(day, self.info(), self.parser)

            bot.send_message(
                self.chat, text, 
                reply_markup=group_keypad(self.message)
            )

    def info(self) -> str:
        info = []

        path = "handlers/functions/currencies_data.json"
        with open(path, encoding="utf-8") as f:
            data = load(f)

        for currency in self.results:
            for j in data:
                code = j['code']

                if currency[0] == code:
                    emoji = j['emoji']
                    symbol = j['symbol']

                    info.append(f"{emoji} {code} {currency[1]}{symbol}")

        return ", ".join(info)
