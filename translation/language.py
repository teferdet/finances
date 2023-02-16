import json
import time
import pymongo
import __main__
import config
import keyboard
import logs

main = __main__
bot = main.bot

client = pymongo.MongoClient(config.database)
settings = client["finances"]["Settings"]

class Welcome:
    def __init__(self, message):
        self.message = message
        self.language = message.from_user.language_code
        
        keyboard.inline(message)
        if self.language in ['ru', 'be']:
            bot.send_message(
                message.chat.id,
                "¯\_(ツ)_/¯ I do not understand your language",
                reply_markup=keyboard.link
            )    

        else:
            self.data()
    
    def data(self):
        date = int(time.strftime("%H"))
        
        if (date >= 6) and (date <= 11): 
            times = 'morning'
        elif (date >= 12) and (date <= 18):
            times = "day"
        elif (date >= 19) and (date <= 21): 
            times = "evening"
        else:   
            times = "night"
        
        name = f"{self.message.from_user.first_name} {self.message.from_user.last_name}"

        if name.split()[1] == 'None':
            name = self.message.from_user.first_name
            
        else:
            pass
        
        if self.message.chat.type == "private":
            keyboard.reply(self.message)
            keypad = keyboard.currency_keyboard
        
        else:
            keypad = None
            
        self.send(times, name, keypad)
    
    def send(self, times, name, keypad):
        keyboard.reply(self.message)
        
        if self.language in ['uk', 'pl']:
            pass
        else:
            language = "en" 
        
        file_name = f'translation/{self.language}.json'
        
        with open(file_name, "rb") as file:
            file = json.load(file)
            
        hello = file['time'][times]
        menu = file['menu']
        
        bot.send_message(self.message.chat.id, f"{hello} {name} 👋")
        bot.send_message(self.message.chat.id, menu, reply_markup=keypad)

def translate(code, data):
    global language
    
    language = code.from_user.language_code    
    
    if language in ['uk', 'pl']:
        pass
    
    else:
        language = "en"   

    file_name = f'translation/{language}.json'
        
    with open(file_name, "rb") as file:
        file = json.load(file)
        language = file[data]

def course(message):
    global rate
    global currency_user_error
    global server_error

    translate(code=message, data='exchange rate')
    
    currency_user_error = language["currency user error"]
    server_error = language["server error"]
    rate = language["rate"]

def inline(inline_query):
    global user_error
    global server_error
    global choose
    global warning
    global warning_info
    global choose_error 
    
    translate(code=inline_query, data='inline mode')

    warning = language['warning']
    choose_error = language['choose error']
    warning_info = language['warning info']
    user_error = language["user error"]
    server_error = language['server error']
    choose = language["choose"]

def info(message):
    translate(code=message, data='bot info')
    keyboard.inline(message)

    query = {'_id':0}
    for version in settings.find(query, {'_id':0, 'version':1}):
        version = version['version']
    
    bot.send_message(
        message.chat.id, 
        f"{language} {version}",
        reply_markup=keyboard.info_link
    )

def help(message):
    translate(code=message, data='help')
    keyboard.inline(message)

    bot.send_message(
        message.chat.id, language,
        reply_markup=keyboard.link
    )
