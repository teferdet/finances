import sqlite3
import json
import time
import __main__
import config
import keyboard
import parser
import logs

main = __main__
bot = main.bot

en = json.load(open('translation/english.json', 'rb'))
pl = json.load(open('translation/polish.json', 'rb'))
uk = json.load(open('translation/ukrainian.json', 'rb'))

def welcome(message):
    name = "{0.first_name} {0.last_name}".format(message.from_user)
    language = message.from_user.language_code

    date = int(time.strftime("%H"))

    if (date >= 6) and (date <= 11): 
        times = 'morning'
    elif (date >= 12) and (date <= 18):
        times = "day"
    elif (date >= 19) and (date <= 21): 
        times = "evening"
    else:   
        times = "night"
    
    if language == "ru":
        keyboard.inline(message)
        reboot = bot.send_message(
            message.chat.id,
            "Your interface language is russian, please change it",
            reply_markup = keyboard.link
        )    
        bot.register_next_step_handler(reboot, main.start)
        
    else:
        if name.split()[1] == 'None':
            name = "{0.first_name}".format(message.from_user)
        else:
            pass

        keyboard.reply(message)

        if language == "uk":
            bot.send_message(message.chat.id, f"{uk['time'][times]} {name} 👋")
            bot.send_message(message.chat.id, uk['menu'], reply_markup = keyboard.menu)
        
        elif language == "pl":
            bot.send_message(message.chat.id, f"{pl['time'][times]} {name} 👋")
            bot.send_message(message.chat.id, pl['menu'], reply_markup = keyboard.menu)

        else:
            bot.send_message(message.chat.id, f"{en['time'][times]} {name} 👋")
            bot.send_message(message.chat.id, en['menu'], reply_markup = keyboard.menu)

def translate(message, data):
    global language
    
    try:
        language = message.from_user.language_code
    
    except:
        language = call.from_user.language_code
    
    if language == "uk":
        language = uk[data]
    elif language == "pol": 
        language = pol[data]
    else: 
        language = en[data]

def course(message):
    global menu
    global rate
    global shares_user_error
    global currency_user_error
    global currency_choose
    global shares_choose
    global server_error
    global technical_error
    global alternative

    translate(message, data = 'exchange rate and shares')
    
    menu = language["menu"]
    currency_choose = language["currency choose"]
    shares_choose = language['shares choose']
    shares_user_error = language["shares user error"]
    currency_user_error = language["currency user error"]
    server_error = language["server error"]
    rate = language["rate"]
    alternative = language["alternative"]

def converter(message):
    global menu
    global choose
    global currency
    global to_choose
    global server_error
    global user_error
    global code_error
    global change
    global during
    
    translate(message, data = 'converter')
    
    menu = language['menu']
    choose = language['choose']
    to_choose = language['to choose']
    currency = language['currency']
    server_error = language['server error']
    user_error = language['user error']
    code_error = language['code error']
    change = language['change']
    during = language['during']

def back(message):
    translate(message, data = 'back')
    keyboard.reply(message)

    bot.send_message(
        message.chat.id, language,
        reply_markup = keyboard.menu
    )

def info(message):
    translate(message, data = 'bot info')
    keyboard.inline(message)

    bot.send_message(
        message.chat.id, 
        f"{language} {config.version}",
        reply_markup = keyboard.info_link
    )

def help(message):
    translate(message, data = "help")
    keyboard.inline(message)

    bot.send_message(
        message.chat.id, language,
        reply_markup = keyboard.link
    )
