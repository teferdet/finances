import telebot, config, json, __main__
from telebot import types

main = __main__
s = open('translation.json', 'rb')
translation = json.load(s)

def translate():
    global menu, conv_keyboard, number, exchange_rate, link
    
    if main.user_language == "uk":
        x = translation['uk']["keyboard"]
    else:
        x = translation['en']["keyboard"]
    
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.row(types.KeyboardButton(x["exchange rate"]))
    menu.row(types.KeyboardButton(x["converter"]))

    conv_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    conv_keyboard.row( types.KeyboardButton("USD/UAH"), types.KeyboardButton("EUR/UAH"), types.KeyboardButton("GBP/UAH"))
    conv_keyboard.row( types.KeyboardButton("PLN/UAH"), types.KeyboardButton("CZK/UAH"))
    conv_keyboard.row( types.KeyboardButton(x["back"]))

    number = types.ReplyKeyboardMarkup(resize_keyboard=True)
    number.row( types.KeyboardButton("5"), types.KeyboardButton("10"))
    number.row( types.KeyboardButton("25"), types.KeyboardButton("50"), types.KeyboardButton('100'))
    number.row( types.KeyboardButton(x["menu"]), types.KeyboardButton(x["back"]))

    exchange_rate = types.ReplyKeyboardMarkup(resize_keyboard=True)
    exchange_rate.row(types.KeyboardButton(x["UAH"]), types.KeyboardButton(x['crypto']))
    exchange_rate.row(types.KeyboardButton(x["back"]))

    link = types.InlineKeyboardMarkup()
    link.row(types.InlineKeyboardButton(text=x["communication"], url=config.telegram))