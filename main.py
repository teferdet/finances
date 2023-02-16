import config
import telebot
import sys

bot = telebot.TeleBot(config.token)

sys.path.append('translation')
sys.path.append('functions')
sys.path.append('parser')

import language
import inline_mode
import exchange_rate
import group_handler

import keyboard
import logs

@bot.message_handler(commands=["start"])
def start(message):
    language.Welcome(message)
    logs.Info(message)

@bot.message_handler(commands=["info"])
def info(message):
    language.info(message)

@bot.message_handler(commands=["help"])
def help(message):
    language.help(message)

@bot.message_handler(func=lambda message: True)
def function(message):
    if message.chat.type == 'private':
        exchange_rate.ExchangeRate(message)
        
    elif message.chat.type == "group":
        group_handler.GroupHandler(message)
    
    else:
        pass

if __name__ == '__main__':
    bot.polling(none_stop=True)
 