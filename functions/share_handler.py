import __main__ as main
import config
import pymongo
import re
import keyboard
import language  
import time

bot = main.bot
client = pymongo.MongoClient(config.data(["database"]))
finance = client["finances"]["Currency"]
company = [
    'APPL', 'META', 'AMZN', 'ADBE',
    'PYPL', 'GOOGL', 'INTC', 'AMD',
    'NFLX', 'MSFT', 'ORCL', 'NVDA'
] 
data = 'exchange rate'

class ShareHandler:
    def __init__(self, message):
        self.message = message
        language = message.from_user.language_code
        
        if language in config.data(['block language']):
            bot.send_message(
                message.chat.id,
                "¯\_(ツ)_/¯ I do not understand your language",
                reply_markup=keyboard.communication_link(message),
                parse_mode='MarkdownV2'
            )    

        else:
            self.massage_handler()
    
    def massage_handler(self):
        self.number = re.findall(r"\d+\.*\d*", self.message.text)
        self.number = float(self.number[0]) if self.number != [] else 1

        self.request()
    
    def request(self):
        self.send = []

        query = {"_id":"Shares"}
        data = [info for info in finance.find(query)][0]

        for key in data:   
            if key in company:    
                price = float(data[key][2])
                price = round(price*self.number, 4)
                symbol = data[key][0]

                add = f"💵 {symbol} | {price}$"
                self.send.append(add)
        
        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        rate = language.translate(self.message, data, 'rate') 

        bot.send_message(
            self.message.chat.id, 
            f"{rate}{day}\n{self.send}"
        )
