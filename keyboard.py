import json
import sqlite3
import config
import language
import exchange_rate
import __main__
import parser
import logs
from telebot import types

main = __main__
bot = main.bot

english = json.load(open('translation/english.json', 'rb'))
ukrainian = json.load(open('translation/ukrainian.json', 'rb'))
pol = json.load(open('translation/polish.json', 'rb'))

def translate(message):
    global language

    language = message.from_user.language_code
    
    if language == "uk":
        language = ukrainian['keyboard']     
    
    elif language == "pol":
        language = polish['keyboard']
    
    else:
        language = english['keyboard']

def reply(message):
    translate(message)

    global menu
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.row(   types.KeyboardButton(language['shares']))
    menu.row(   types.KeyboardButton(language["exchange rate"]))
    menu.row(   types.KeyboardButton(language["converter"]))

    global converter
    converter = types.ReplyKeyboardMarkup(resize_keyboard=True)
    converter.row(  types.KeyboardButton("USD"), 
                    types.KeyboardButton("EUR"), 
                    types.KeyboardButton("GBP"))
    converter.row(  types.KeyboardButton("CHF"), 
                    types.KeyboardButton("JPY"))
    converter.row(  types.KeyboardButton(language["back"]))

    global to_converter
    to_converter = types.ReplyKeyboardMarkup(resize_keyboard=True)
    to_converter.row(   types.KeyboardButton("UAH"), 
                        types.KeyboardButton("PLN"), 
                        types.KeyboardButton("CZK"))
    to_converter.row(   types.KeyboardButton(language["menu"]), 
                        types.KeyboardButton(language["back"]))

    global number
    number = types.ReplyKeyboardMarkup(resize_keyboard=True)
    number.row( types.KeyboardButton(language['change']))
    number.row( types.KeyboardButton("5"), 
                types.KeyboardButton("10"))
    number.row( types.KeyboardButton("25"), 
                types.KeyboardButton("50"), 
                types.KeyboardButton('100'))
    number.row( types.KeyboardButton(language["menu"]), 
                types.KeyboardButton(language["back"]))

    global currency_keyboard
    currency_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    currency_keyboard.row(  types.KeyboardButton(language['crypto']))
    currency_keyboard.row(  types.KeyboardButton("🇺🇦 UAH"), 
                            types.KeyboardButton("🇺🇸 USD"),
                            types.KeyboardButton("🇬🇧 GBP")) 
    currency_keyboard.row(  types.KeyboardButton("🇪🇺 EUR"),
                            types.KeyboardButton("🇵🇱 PLN"), 
                            types.KeyboardButton("🇨🇿 CZK"))
    currency_keyboard.row(  types.KeyboardButton(language["back"]))

    global keyboard_shares
    keyboard_shares = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_shares.row(    types.KeyboardButton(language['IT']), 
                            types.KeyboardButton(language['technologies']))
    keyboard_shares.row(    types.KeyboardButton(language['back']))

def inline(message):
    global link
    global info_link

    translate(message)

    link = types.InlineKeyboardMarkup()
    link.row(   types.InlineKeyboardButton(
                text = language["communication"], 
                url = config.telegram
                )
    )

    info_link = types.InlineKeyboardMarkup()
    info_link.row(  types.InlineKeyboardButton(
                    text = 'ℹ️ GitHub', url = config.github),
                    types.InlineKeyboardButton(
                    text = language['news'], url = config.news
                    )
    )

def convert(message, finance):
    global info_data
    translate(message)

    info_data = types.InlineKeyboardMarkup()
    info_data.add(  types.InlineKeyboardButton(text = language['more'], url = finance))

def alternative_currency_key(message, currency_name):
    global currency

    translate(message)

    currency = types.InlineKeyboardMarkup()    
    if currency_name in ["c UAH", "c EUR", "c GBP", "crypto"]:
        currency.add(   types.InlineKeyboardButton( text = "£", callback_data = 'c GBP'),
                        types.InlineKeyboardButton( text = "€", callback_data = 'c EUR'),
                        types.InlineKeyboardButton( text = "₴", callback_data = 'c UAH'))

    else:
        currency.add( types.InlineKeyboardButton( 
            text = f"{currency_name.upper()}/{language['other']}",
            callback_data = currency_name)
        )

@bot.callback_query_handler(func = lambda call: True)
def key_handler(call):
    if call.data in ["c UAH", "c EUR", "c GBP"]:
        exchange_rate.alternative_currency(call, currency_name = call.data)
    
    else:
        exchange_rate.alternative_currency(call, currency_name = call.data)
