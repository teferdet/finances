import pymongo
import json
import config
import exchange_rate
import group_handler
import __main__ as main
import settings
import crypto_handler
from telebot import types

bot = main.bot
client = pymongo.MongoClient(config.data(["database"]))
settings_db = client["finances"]["Settings"]

currency_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
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
currency_keyboard.row(  
    types.KeyboardButton("🇨🇭 CHF"),
    types.KeyboardButton("🇧🇬 BGN"), 
    types.KeyboardButton("🇯🇵 JPY")
)

def database():
    for links in settings_db.find({'_id':0}):
        return links

def translate(code):
    language = code.from_user.language_code    
    
    if language not in config.data(["languages"]):
        language = 'en'

    path = f'files/languages/{language}.json'
    with open(path, "rb") as file:
        file = json.load(file)
        translate = file["keyboard"]
    
    return translate

#settings
def cancel(call):
    cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel.add(types.KeyboardButton(translate(call)['cancel']))

    return cancel

def setting_keyboard(message):
    settings_menu = types.InlineKeyboardMarkup()
    settings_menu.row(types.InlineKeyboardButton(text=translate(message)['groups'], callback_data='settings group '))

    return settings_menu

def group_settings(call, ID):
    group_settings = types.InlineKeyboardMarkup()
    group_settings.row(
        types.InlineKeyboardButton(
            text=translate(call)['input'], callback_data=f'settings group input list {ID}'
        ))
    group_settings.row(
        types.InlineKeyboardButton(
            text=translate(call)['output'], callback_data=f'settings group output list {ID}'
        ))

    return group_settings

#group
def groups_keypad(admin_access):
    groups_keypad = types.InlineKeyboardMarkup()
    for ID, name  in admin_access[0].items():
        groups_keypad.row(
            types.InlineKeyboardButton(
                text=name, callback_data=f'settings group {ID}'
        ))

    return groups_keypad

def group_keypad_handler(message, currency_name):
    global delete
    global delete_and_rate

    delete_and_rate =types.InlineKeyboardMarkup()
    delete_and_rate.row( 
        types.InlineKeyboardButton( 
            text=f"{currency_name.upper()}/{translate(message)['other']}",
            callback_data=currency_name
        )
    )
    delete_and_rate.row(
        types.InlineKeyboardButton(text=translate(message)['delete'], callback_data='delete')
    )

    delete = types.InlineKeyboardMarkup()
    delete.add(
        types.InlineKeyboardButton(text=translate(message)['delete'], callback_data='delete')
    )


#in bot
def communication_link(message):
    urls = database()['links']
    
    link = types.InlineKeyboardMarkup().row(   
        types.InlineKeyboardButton(
            text=translate(message)["communication"],
            url=urls[1]
        )
    )

    return link

def info_link(message):
    urls = database()['links']

    link = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton(text=translate(message)["news"], url=urls[2]),
        types.InlineKeyboardButton(text='ℹ️ GitHub', url=urls[0])            
    )

    return link 

def donate_link(message):
    urls = database()['links']

    link = types.InlineKeyboardMarkup()
    link.row(types.InlineKeyboardButton(text="☕️ Buy me a coffee", url=urls[3]))
    link.row(types.InlineKeyboardButton(text='❤️ Дяка', url=urls[4]))
    
    return link 

def add_bot(message):
    urls = database()['links']
    
    link = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton(
            text=translate(message)["add bots"],
            url=urls[5]
        )
    )

    return link

def alternative_currency_keyboard(message, currency_name):
    currency = types.InlineKeyboardMarkup()    
    
    if currency_name.split()[0] in ["crypto"] or currency_name == "crypto":
        currency.row(   
            types.InlineKeyboardButton(text="£", callback_data='crypto GBP'),
            types.InlineKeyboardButton(text="€", callback_data='crypto EUR'),
            types.InlineKeyboardButton(text="₴", callback_data='crypto UAH')
        )
        currency.row(   
            types.InlineKeyboardButton(text="zł‎", callback_data='crypto PLN'),
            types.InlineKeyboardButton(text="Kč", callback_data='crypto CZK'),
        )

    else:
        currency.add( 
            types.InlineKeyboardButton( 
                text=f"{currency_name.upper()}/{translate(message)['other']}",
                callback_data=currency_name
            )
        )

    return currency

@bot.callback_query_handler(func=lambda call: True)
def call_handler(call):
    data = call.message.json['chat']

    if call.data == "delete":
        try:
            bot.delete_message(data['id'], call.message.message_id)
        
        except:
            bot.answer_callback_query(call.id, ">_< Error", show_alert=False)

    elif call.data.split()[0] in ['settings']:
        settings.Settings(call)
    
    elif call.data.split()[0] in ['crypto']:
        crypto_handler.AlternativeCrypto(call, currency=call.data)

    else:
        handler = group_handler if data['type'] in ["group", "supergroup"] else exchange_rate
        handler.AlternativeCurrency(call, currency_name=call.data)
