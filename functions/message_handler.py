import __main__ as main 
import pymongo
import time
import config

bot = main.bot

import exchange_rate
import group_handler
import share_handler
import crypto_handler

import keyboard
import language

import settings
import logs

client = pymongo.MongoClient(config.database)
settings_db = client["finances"]["Settings"]
commands = ['share', 'settings', "crypto"]

@bot.message_handler(commands=['start'])
class Start:
    def __init__(self, message):        
        self.message = message
        self.language = message.from_user.language_code

        if self.language in ['ru', 'be']:
            keyboard.inline(message)
            bot.send_message(
                message.chat.id,
                "[¯\_(ツ)_/¯ I do not understand your language](http://surl.li/dhmwi)",
                reply_markup=keyboard.link,
                parse_mode='MarkdownV2'
            )    

        else:
            self.data()
    
    def data(self):
        date = int(time.strftime("%H"))
        
        if (date >= 6) and (date <= 11): 
            self.times = 'morning'
        elif (date >= 12) and (date <= 18):
            self.times = "day"
        elif (date >= 19) and (date <= 21): 
            self.times = "evening"
        else:   
            self.times = "night"
        
        if self.message.chat.type == "private":
            self.keypad = keyboard.currency_keyboard
            self.index = "in bot"
        
        else:
            self.keypad = None
            self.index = "in group"

        self.name = f"{self.message.from_user.first_name} {self.message.from_user.last_name}"

        if self.name.split()[1] == 'None':
            self.name = self.message.from_user.first_name

        self.publishing()
    
    def publishing(self):
        hello = language.translate(self.message, "time", self.times)
        menu = language.translate(self.message, 'menu', self.index)
    
        bot.send_message(self.message.chat.id, f"{hello} {self.name} 👋") 
        bot.send_message(self.message.chat.id, menu, reply_markup=self.keypad)
        
        logs.Info(self.message)

@bot.message_handler(commands=['info'])
def info(message):
    keyboard.inline(message)
    text = language.translate(message, "bot info", None)
    version = [data for data in settings_db.find({'_id':0})][0]['version']

    bot.send_message(
        message.chat.id, 
        f"{text} {version}",
        reply_markup=keyboard.info_link
    )

@bot.message_handler(commands=['donate'])
def donate(message):
    keyboard.inline(message)
    text = language.translate(message, 'donate', None)
    
    bot.send_message(
        message.chat.id, text,
        reply_markup=keyboard.donate_link
    )

@bot.message_handler(commands=['help'])
def help(message):
    keyboard.inline(message)
    text = language.translate(message, 'help', None)
    
    bot.send_message(
        message.chat.id, text,
        reply_markup=keyboard.link
    )

@bot.message_handler(commands)
def commands(message):
    text = message.text.split()[0][1:]
    if text == "start":
        language.Welcome(message)
        logs.Info(message)

    elif text == "settings":
        settings.Publishing(message)

    elif text == "share":
        share_handler.ShareHandler(message)

    elif text == "crypto":
        crypto_handler.Crypto(message)

@bot.message_handler(func=lambda message: True)
def function(message):
    if message.chat.type == 'private':
        exchange_rate.ExchangeRate(message)
        
    elif message.chat.type in ["group", "supergroup"]:
        group_handler.GroupHandler(message)
    
    else:
        pass
