import __main__ as main 

bot = main.bot

import exchange_rate
import group_handler
import share_handler
import crypto_handler

import keyboard
import language

import settings
import logs

commands = [
    "start", "info", "donate", 
    'share', 'settings', "help",
    "crypto"
]

@bot.message_handler(commands)
def commands(message):
    text = message.text[1:]

    if text == "start":
        language.Welcome(message)
        logs.Info(message)

    elif text == "info":
        language.info(message)

    elif text == "donate":
        language.donate(message)

    elif text == "help":
        language.help(message)

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
