import __main__
import re
import pymongo
import logs
import parser
import keyboard 
import language 
import config
import time

bot = __main__.bot

client = pymongo.MongoClient(config.data(["database"]))
user = client["finances"]["Users"]
group = client['finances']['Groups']
settings = client["finances"]["Settings"]
data = 'exchange rate'

class GroupHandler:
    def __init__(self, message): 
        self.message = message
        self.ID = message.from_user.id
        self.chat = message.chat.id
        language = message.from_user.language_code

        if language not in config.data(['block language']):
            logs.Users(self.message)
            self.message_data()
    
    def message_data(self):
        for item in group.find({"_id":self.chat}):
            currency = '|'.join(item['Currency input list'])
            self.output = item['Currency output list'] 
    
        pattern = r"(\d+\.*\d*)?\s*\b(" + currency + r")\b\s*(\d+\.*\d*)?"
        message_text = self.message.text.upper()
        text = re.findall(pattern, message_text)

        if text != []:
            data = text[0]
            self.currency_name = data[1].upper()

            for item in data:
                try: 
                    self.number = float(item)
                    break

                except ValueError:
                    self.number = 1

            self.processing()

    def processing(self):
        user.update_one({'_id':self.ID}, {'$set':{"Convert":self.number}})
        
        if self.currency_name not in config.data(["block currency"]): 
            self.index = 0 if self.currency_name in ['BTC', 'ETH'] else 1
            self.keypad()

    def keypad(self):
        keyboard.group_keypad_handler(self.message, self.currency_name)

        if self.index == 0:
            self.keypad = keyboard.delete
        
        else:
            self.keypad = keyboard.delete_and_rate
        
        self.server_status()

    def server_status(self):
        day = time.strftime("%d.%m.%y")
        keypad = None

        parser = parser.CurrencyHandler(self.currency_name, self.number, self.output, self.index)

        if parser == "server error":
            text = language.translate(self.message, data, "server error")

        elif parser == "bad request":
            text = language.translate(self.message, data, "currency user error")

        else:
            rate = language.translate(self.message, data, 'rate') 
            text = f"{rate}{day}\n{parser}",
            keypad = self.keypad
        
        bot.send_message(
            self.message.chat.id, 
            text, reply_markup=self.keypad
        )

class AlternativeCurrency:
    def __init__(self, call, currency_name):
        keyboard.group_keypad_handler(call, currency_name)

        ID = call.from_user.id
        group_ID = call.message.chat.id
        self.call = call 
        self.keypad = keyboard.delete
        
        for x, y in zip(user.find({'_id':ID}), group.find({'_id':group_ID})):
            number = x['Convert']
            output = y['Currency output list']

        parser.CurrencyHandler(currency_name, number, output, 0)
        self.status()
        
    def status(self):
        day = time.strftime("%d/%m/%y")
        
        if parser.status_code == 200 or parser.status is True:
            rate = language.translate(self.call, data, 'rate') 
            text = f"{rate}{day}\n{parser.send}"

        else:
            text = language.translate(self.call, data, "server error")

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=text, reply_markup=keyboard.delete
        )
