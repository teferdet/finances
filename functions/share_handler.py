import __main__ as main
import config
import pymongo
import re
import keyboard
import language  
import time

bot = main.bot
client = pymongo.MongoClient(config.database)
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
        
        if language in ['ru', 'be']:
            keyboard.inline(message)
            bot.send_message(
                message.chat.id,
                "[¯\_(ツ)_/¯ I do not understand your language](http://surl.li/dhmwi)",
                reply_markup=keyboard.link,
                parse_mode='MarkdownV2'
            )    

        else:
            self.massage_handler()
    
    def massage_handler(self):
        ID = self.message.from_user.id

        self.number = re.findall(r"\d+\.*\d*", self.message.text)
        self.number = float(self.number[0]) if self.number != [] else 1

        self.request()
    
    def request(self):
        self.send = []

        query = {"_id":"Shares"}
        data = [info for info in finance.find(query)]

        for key in data[0]:   
            if key in company:    
                name = data[0][key][1]
                price = float(data[0][key][2])
                price = round(price*self.number, 4)
                symbol = data[0][key][0]

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
