import __main__ as main
import config
import pymongo
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
            self.request()
    
    def request(self):
        self.send = []

        query = {"_id":"Shares"}
        data = [info for info in finance.find(query)]
            
        for key in data[0]:   
            if key in company:    
                name = data[0][key][1]
                price = data[0][key][2]
                symbol = data[0][key][0]

                add = f"💵 {symbol} | {price}$"
                self.send.append(add)
        
        self.send = "\n".join(self.send)
        self.publishing()

    def publishing(self):
        day = time.strftime("%d.%m.%y")
        language.course(self.message)

        bot.send_message(
            self.message.chat.id, 
            f"{language.rate}{day}\n{self.send}"
        )
