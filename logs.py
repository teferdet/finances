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

class Users:
    def __init__(self, message):
        self.message = message
        self.ID = message.chat.id
        users = [item['_id'] for item in users_db.find()]

        if self.ID not in users:
            self.data_collection()
    
    def data_collection(self):
        self.name = '{0.first_name} {0.last_name}'.format(self.message.from_user)

        if self.name.split()[1] == "None":
            self.name = self.message.from_user.first_name
            
        self.data = {
            '_id':self.ID,
            'Name':self.name,
            'Username':self.message.from_user.username,
            'Language code':self.message.from_user.language_code,
            'Premium':self.message.from_user.is_premium,
            'Convert':0,
            'Admin groups':{},
            'Inline currency list':[
                'American Dollar', 'Euro', 'British Pound', 
                'Czech Koruna','Japanese Yen', 'Polish Zloty',
                'Swiss Franc', 'Chinese Yuan Renminbi',
                'Ukraine Hryvnia', 'Bulgarian Lev', 'Israeli New Shekel',
                'Swedish Krona','Norwegian Krone'
            ],
            'Personal currency list':[
                'American Dollar', 'Euro', 'British Pound', 
                'Czech Koruna','Japanese Yen', 'Polish Zloty',
                'Swiss Franc', 'Chinese Yuan Renminbi',
                'Ukraine Hryvnia'
            ],
            'Crypto list':[
                "BTC", 'ETH', "BNB", "SOL", 
                "USDT", "TRX", "TON", "LTC",
            ],
            'Share list':[
                'APPL', 'META', 'AMZN', 'ADBE',
                'PYPL', 'GOOGL', 'INTC', 'AMD',
                'NFLX', 'MSFT'
            ] 
        }

        users_db.insert_one(self.data)

class Groups:
    def __init__(self, message):
        self.message = message
        self.ID = message.chat.id
        groups = [item['_id'] for item in groups_db.find()]

        if self.ID not in groups:
            self.data_collection()

    def data_collection(self):
        self.title = self.message.chat.title
        self.admins = []

        for item in bot.get_chat_administrators(self.message.chat.id):
            if item.user.is_bot is False:
                self.admins.append(item.user.id)

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
    
        self.share_access()

    def share_access(self):
        groups_db.insert_one(self.data)

        for ID in self.admins:
            users_db.update_one(
                {'_id':ID}, 
                {'$set':{f"Admin groups.{self.title}":self.ID}}
            )
