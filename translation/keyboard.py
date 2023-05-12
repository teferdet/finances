import pymongo
import json
import config
import language
import exchange_rate
import group_handler
import __main__
import settings
import parser
import logs
from telebot import types

main = __main__
bot = main.bot

client = pymongo.MongoClient(config.database)
settings_db = client["finances"]["Settings"]

def database():
    global github
    global call
    global news    
    global buymeacoffee
    global thanks
    
    for links in settings_db.find({'_id':0}):
        github = links['links'][0]
        call = links['links'][1]
        news = links['links'][2]
        buymeacoffee = links['links'][3]
        thanks = links['links'][4]

def translate(data):
    global language
    
    language = data.from_user.language_code    
    if language not in ['uk', 'pl']:
        language = 'en'

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

    global cancel
    cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel.add(types.KeyboardButton(language['cancel']))

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
    donate_link.row(types.InlineKeyboardButton(text="☕️ Buy me a coffee", url=buymeacoffee))
    donate_link.row(types.InlineKeyboardButton(text='❤️ Дяка', url=thanks))

def setting_keyboard(message):
    global settings_menu 

    translate(message)
    settings_menu = types.InlineKeyboardMarkup()
    settings_menu.row(types.InlineKeyboardButton(text=language['groups'], callback_data='s group '))

def group_settings(call, ID):
    translate(call)
    group_settings = types.InlineKeyboardMarkup()
    group_settings.row(
        types.InlineKeyboardButton(
            text=language['input'], callback_data=f's group input list {ID}'
        ))
    group_settings.row(
        types.InlineKeyboardButton(
            text=language['output'], callback_data=f's group output list {ID}'
        ))

    return group_settings

def groups_keypad(admin_access):
    keypad = []

    groups_keypad = types.InlineKeyboardMarkup()
    for name, ID  in admin_access[0].items():
        item =  groups_keypad.row(
            types.InlineKeyboardButton(
                text=name, callback_data=f's group {ID}'
        ))
        keypad.append(item)

    return groups_keypad

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
        try:
            bot.delete_message(data['id'], call.message.message_id)
        
        except:
            bot.answer_callback_query(call.id, ">_< Error", show_alert=False)

    elif call.data.split()[0] in ['s']:
        settings.Settings(call)

    else:
        handler = group_handler if data['type'] in ["group", "supergroup"] else exchange_rate
        handler.AlternativeCurrency(call, currency_name=call.data)