import pymongo
import telebot 
import time
import config
import parser
from telebot import types

bot = telebot.TeleBot(config.token)
client = pymongo.MongoClient(config.database)
db = client["finances"]["Users"]

class UserInfo:
    def __init__(self, message):     
        ID = message.from_user.id
        name = '{0.first_name} {0.last_name}'.format(message.from_user)

        if name.split()[1] == "None":
            name = message.from_user.first_name
        
        data = {
            '_id':ID,
            'Name':name,
            'Username':message.from_user.username,
            'Language_code':message.from_user.language_code,
            'Premium':message.from_user.is_premium,
            'Convert':0
        }
        
        self.add(ID, data, message)

    def add(self, ID, data, message):
        try:
            db.insert_one(data)
            self.about_user(data, message)

        except:
            pass
        
    def about_user(self, data, message):
        date = time.strftime("%d.%m.%Y | %H:%M:%S")
        username = message.from_user.username
        markup = types.InlineKeyboardMarkup()
        
        if username != "None":
            markup.add(   
                types.InlineKeyboardButton(text=username, url=f"t.me/{username}")
            )
            
        else:
            markup = None

        bot.send_message(
            chat_id=config.log_id,
            text=f"#finances | #user\
                \nDate&time: {date}\
                \nID: `{data['_id']}`\
                \nName: {data['Name']}\
                \nPremium: {data['Premium']}\
                \nLanguage: {data['Language_code']}",
            reply_markup=markup,
            parse_mode='Markdown'
        )

def server(status_code, url, name):
    date = time.strftime("%d.%m.%Y | %H:%M:%S")
    
    markup = types.InlineKeyboardMarkup()
    markup.add( types.InlineKeyboardButton(text=name, url=url))
    
    bot.send_message(
        chat_id=config.log_id,
        text=f"#Server | #Error\
            \nDate&time: {date} \
            \nName: {name}\
            \nStatus code: `{status_code}`",
        reply_markup=markup,
        parse_mode='Markdown'
    )
