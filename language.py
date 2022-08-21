import json, time
import __main__, parser, keyboard

main = __main__

s = open('translation.json', 'rb')
translation = json.load(s)

date = time.strftime("%d/%m/%y")
time = int(time.strftime("%H"))

def welcome():
    bot = main.bot
    message = main.mes

    if (time >= 6) and (time <= 11):
        uk = translation["uk"]["time"]["morning"]
        en = translation['en']["time"]['morning']

    elif (time >= 12) and (time <= 18):
        uk = translation["uk"]["time"]["day"]
        en = translation["en"]["time"]["day"]

    elif (time >= 19) and (time <= 21):
        uk = translation["uk"]["time"]["evening"]
        en = translation["en"]["time"]["evening"]

    else:
        uk = translation["uk"]["time"]["night"]
        en = translation["en"]["time"]["night"]
    
    keyboard.translate()
    
    if main.user_language == "uk":
        bot.send_message(message.chat.id, f'{uk}, {main.user_name} 👋')
        bot.send_message(message.chat.id, translation['uk']['menu'], reply_markup=keyboard.menu)
        
    elif main.user_language == "ru":   
        reboot = bot.send_message(message.chat.id, f"{translation['uk']['warning']}\n\n{translation['en']['warning']}")
        bot.register_next_step_handler(reboot, main.start)

    else:
        bot.send_message(message.chat.id, f'{en}, {main.user_name} 👋')
        bot.send_message(message.chat.id, translation['en']['menu'], reply_markup=keyboard.menu)

def exchange_rate():
    global uah, crypto, choose, user_error, menu

    if main.user_language == "uk":
        x = translation['uk']['exchange rate']
    else:
        x = translation['en']['exchange rate']

    menu = x["menu"]
    info = x['course']
    choose = x["choose"]
    user_error = x["user_error"]
    server_error = x["server_error"]

    if parser.ubank.status_code == 200:
        uah = f"{info} {date} \n{parser.uah_send}"
    else:
        uah = server_error
        
    if parser.crypto_data.status_code == 200:
        crypto = f"{info} {date} \n{parser.crypto_send}"
    else:
        crypto = server_error

def converter():
    global menu, choose, currency, server_error, user_error, during

    if main.user_language == 'uk':
        x = translation['uk']['converter']
    else:
        x = translation['en']['converter']
    
    menu = x['menu']
    choose = x['choose']
    currency = x['currency']
    server_error = x['server_error']
    user_error = x['user_error']
    during = x['during']

def help():
    bot = main.bot
    message = main.mes

    keyboard.translate()
    if main.user_language == "uk":
        bot.send_message(message.chat.id, translation['uk']['help'], reply_markup=keyboard.link)
    else:
        bot.send_message(message.chat.id, translation["en"]["help"], reply_markup=keyboard.link)
