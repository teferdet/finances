import json
import config
import language
import exchange_rate
import __main__
import parser
import logs
from telebot import types

main = __main__
bot = main.bot

def translate(message):
    global language

    language = message.from_user.language_code    
    if language in ['uk', 'pl']:
        pass
    else:
        language = "en"   

    file_name = f'translation/{language}.json'
    
    with open(file_name, "rb") as file:
        file = json.load(file)
        language = file["keyboard"]

def reply(message):
    translate(message)

    global currency_keyboard
    currency_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    currency_keyboard.row(  types.KeyboardButton(language['crypto']))
    currency_keyboard.row(  
        types.KeyboardButton("🇺🇦 UAH"), 
        types.KeyboardButton("🇺🇸 USD"),
        types.KeyboardButton("🇬🇧 GBP")
    ) 
    currency_keyboard.row(  
        types.KeyboardButton("🇪🇺 EUR"),
        types.KeyboardButton("🇵🇱 PLN"), 
        types.KeyboardButton("🇨🇿 CZK")
    )

def inline(message):
    global link
    global info_link

    translate(message)

    link = types.InlineKeyboardMarkup()
    link.row(   
        types.InlineKeyboardButton(
            text=language["communication"],
            url=config.telegram
        )
    )

    info_link = types.InlineKeyboardMarkup()
    info_link.row(
        types.InlineKeyboardButton(text=language["news"], url=config.news),
        types.InlineKeyboardButton(text='ℹ️ GitHub', url=config.github)            
    )

def alternative_currency_key(message, currency_name):
    global currency

    currency = types.InlineKeyboardMarkup()    
    if currency_name in ["c UAH", "c EUR", "c GBP", "crypto"]:
        currency.add(   
            types.InlineKeyboardButton(text="£", callback_data='c GBP'),
            types.InlineKeyboardButton(text="€", callback_data='c EUR'),
            types.InlineKeyboardButton(text="₴", callback_data='c UAH')
        )

    else:
        translate(message)
        currency.add( 
            types.InlineKeyboardButton( 
                text=f"{currency_name.upper()}/{language['other']}",
                callback_data=currency_name
            )
        )

@bot.callback_query_handler(func=lambda call: True)
def key_handler(call):
    exchange_rate.AlternativeCurrency(call, currency_name=call.data)
