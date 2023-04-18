import pymongo
import telebot 
import time
import config
import parser
from telebot import types

bot = telebot.TeleBot(config.token)

client = pymongo.MongoClient(config.database)
users_db = client["finances"]["Users"]
groups_db = client["finances"]["Groups"]
settings = client["finances"]["Settings"]

class Info:
    def __init__(self, message):
        chat_type = message.chat.type

        if chat_type == "private":
            Users(message)
        
        elif chat_type in ["group", "supergroup"]:
            Groups(message)
        
        else:
            pass

class Users:
    def __init__(self, message):
        self.message = message
        self.ID = message.from_user.id
        self.name = '{0.first_name} {0.last_name}'.format(message.from_user)

        if self.name.split()[1] == "None":
            self.name = message.from_user.first_name
            
        self.data = {
            '_id':self.ID,
            'Name':self.name,
            'Username':self.message.from_user.username,
            'Language code':self.message.from_user.language_code,
            'Premium':self.message.from_user.is_premium,
            'Convert':0
        }

        self.add()
        
    def add(self):
        try:
            users_db.insert_one(self.data)

        except:
            pass

class Groups:
    def __init__(self, message):
        self.message = message
        self.ID = message.chat.id
        self.title = message.chat.title
        
        self.data = {
            "_id":self.ID,
            "Name":self.title,
            "Username":self.message.chat.username,
            "Currency output list":[
                'American Dollar', 'Euro', 'British Pound', 
                'Czech Koruna','Japanese Yen', 'Polish Zloty',
                'Swiss Franc', 'Chinese Yuan Renminbi',
                'Ukraine Hryvnia'
            ],
            "Currency input list":[
                'USD', 'EUR', "GBP", "CZK",
                "PLN", "CHF", "CNY", "UAH",
                "BTC", "ETH"
            ]
        }
        
        self.add()
    
    def add(self):
        try:
            groups_db.insert_one(self.data)

        except:
            pass

def server(status_code, url, name):
    date = time.strftime("%d.%m.%Y | %H:%M:%S")
    
    keypad = types.InlineKeyboardMarkup()
    keypad.add( types.InlineKeyboardButton(text=name, url=url))
    
    bot.send_message(
        chat_id=config.log_id,
        text=f"#Server | #Error\
            \nDate&time: {date} \
            \nName: {name}\
            \nStatus code: `{status_code}`",
        reply_markup=keypad,
        parse_mode='Markdown'
    )
