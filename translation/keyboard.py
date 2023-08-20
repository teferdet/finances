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
client = pymongo.MongoClient(config.database)
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

def translate(code):
    language = code.from_user.language_code    
    
    if language not in ['uk', 'pl']:
        language = 'en'

    path = f'translation/{language}.json'
    with open(path, "rb") as file:
        file = json.load(file)
        translate = file["keyboard"]
    
    return translate

def cancel(call):
    cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel.add(types.KeyboardButton(translate(call)['cancel']))

    return cancel

def inline(message):
    global link
    global info_link
    global donate_link

    database()
    
    link = types.InlineKeyboardMarkup()
    link.row(   
        types.InlineKeyboardButton(
            text=translate(message)["communication"],
            url=call
        )
    )

    info_link = types.InlineKeyboardMarkup()
    info_link.row(
        types.InlineKeyboardButton(text=translate(message)["news"], url=news),
        types.InlineKeyboardButton(text='ℹ️ GitHub', url=github)            
    )

    donate_link = types.InlineKeyboardMarkup()
    donate_link.row(types.InlineKeyboardButton(text="☕️ Buy me a coffee", url=buymeacoffee))
    donate_link.row(types.InlineKeyboardButton(text='❤️ Дяка', url=thanks))

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

def groups_keypad(admin_access):
    groups_keypad = types.InlineKeyboardMarkup()
    for name, ID  in admin_access[0].items():
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
