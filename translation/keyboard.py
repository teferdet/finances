import pymongo
import json
import config
import language
import exchange_rate
import group_handler
import __main__
import parser
import logs
from telebot import types

main = __main__
bot = main.bot

client = pymongo.MongoClient(config.database)
settings = client["finances"]["Settings"]

def database():
    global github
    global call
    global news    
    global buymeacoffee
    global thanks
    
    for links in settings.find({'_id':0}):
        github = links['links'][0]
        call = links['links'][1]
        news = links['links'][2]
        buymeacoffee = links['links'][3]
        thanks = links['links'][4]

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
    global donate_link

    database()
    translate(message)
    
    link = types.InlineKeyboardMarkup()
    link.row(   
        types.InlineKeyboardButton(
            text=language["communication"],
            url=call
        )
    )

    info_link = types.InlineKeyboardMarkup()
    info_link.row(
        types.InlineKeyboardButton(text=language["news"], url=news),
        types.InlineKeyboardButton(text='ℹ️ GitHub', url=github)            
    )

    donate_link = types.InlineKeyboardMarkup()
    donate_link.row(
        types.InlineKeyboardButton(text="☕️ Buy me a coffee", url=buymeacoffee),
        types.InlineKeyboardButton(text='❤️ Дяка', url=thanks)            
    )

def group_keypad_handler(message, currency_name):
    global delete
    global delete_and_rate

    translate(message)

    delete_and_rate =types.InlineKeyboardMarkup()
    delete_and_rate.row( 
        types.InlineKeyboardButton( 
            text=f"{currency_name.upper()}/{language['other']}",
            callback_data=currency_name
        )
    )
    delete_and_rate.row(
        types.InlineKeyboardButton(text=language['delete'], callback_data='delete')
    )

    delete = types.InlineKeyboardMarkup()
    delete.add(
        types.InlineKeyboardButton(text=language['delete'], callback_data='delete')
    )

def alternative_currency_key(message, currency_name):
    global currency

    currency = types.InlineKeyboardMarkup()    
    if currency_name.split()[0] in ["c"] or currency_name == "crypto":
        currency.row(   
            types.InlineKeyboardButton(text="£", callback_data='c GBP'),
            types.InlineKeyboardButton(text="€", callback_data='c EUR'),
            types.InlineKeyboardButton(text="₴", callback_data='c UAH')
        )
        currency.row(   
            types.InlineKeyboardButton(text="zł‎", callback_data='c PLN'),
            types.InlineKeyboardButton(text="Kč", callback_data='c CZK'),
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
def call_handler(call):
    data = call.message.json['chat']

    if call.data == "delete":
        bot.delete_message(data['id'], call.message.message_id)
    
    else:
        handler = group_handler if data['type'] in ["group", "supergroup"] else exchange_rate
        handler.AlternativeCurrency(call, currency_name=call.data)