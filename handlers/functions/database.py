from jsoncfg import load_config
from time import strftime
from messages_handler import bot, client, UpdateOne

users_database = client["Users"]
groups_database = client["Groups"]
bot_id = bot.get_me().id

# Class "User" is database handler for managment users
class User:
    def __init__(self, message: dict):
        self.message = message
        self.ID = message.from_user.id
        users = [i["_id"] for i in users_database.find()]

        if self.ID not in users:
            self.add_user()
    
    def add_user(self):
        curencies = config()
        name = "{0.first_name} {0.last_name}".format(self.message.from_user)
        sing_up = strftime('%d.%m.%y %H:%M:%S')

        if self.message.from_user.last_name == "None":
            name = self.message.from_user.first_name

        data = {
            "_id":self.ID,
            "Name":name,
            "Username":self.message.from_user.username,
            "Password":None,
            "Language":self.message.from_user.language_code,
            "Premium":self.message.from_user.is_premium,
            "Sign up":sing_up,
            "Fiat currency":[i.value for i in curencies.small_convert_currencies],
            "Crypto currency":[i.value for i in curencies.crypto],
            "Stocks":[i.value for i in curencies.company],
            "Groups":[],
        }

        users_database.insert_one(data)

# class "Uppend", and functions "deactivate", "remove" need for groups managment
@bot.message_handler(content_types=["new_chat_members"])
class Uppend:
    def __init__(self, message: dict):
        self.message = message
        members = self.message.new_chat_members

        if any(member.id == bot_id for member in members):
            self.ID = self.message.chat.id
            groups = [item["_id"] for item in groups_database.find()]
        
            if self.ID not in groups:
                self.add_admins()
                self.add_group()
            
            else:
                self.update_status()

    def add_admins(self):
        self.title = self.message.chat.title
        self.admins = []
        self.update = []

        for item in bot.get_chat_administrators(self.ID):
            admin_ID = item.user.id
            is_bot = item.user.is_bot

            if is_bot is False:
                User(self.message)

                self.update.append(UpdateOne(
                    {"_id":admin_ID}, 
                    {"$push":{"Groups":{
                        "id":self.ID,
                        "title":self.title,
                    }}},
                    upsert=True                        
                ))
                self.admins.append(item.user.id)

    def add_group(self):
        data = {
            "_id":self.ID,
            "Title":self.title,
            "Username":self.message.chat.username,
            "Admins":self.admins,
            "Status":"Active",
            "Output":[
                "American Dollar", "Euro", "British Pound", 
                "Japanese Yen", "Polish Zloty",
                "Swiss Franc", "Ukraine Hryvnia"
            ],
            "Input":[
                "USD", "EUR", "GBP", "CZK",
                "PLN", "CHF", "CNY", "UAH",
                "BTC", "ETH"
            ]
        }
    
        groups_database.insert_one(data)
        users_database.bulk_write(self.update)
    
    def update_status(self):
        groups_database.update_one(
            {"_id":self.ID}, 
            {"$set":{"Status":"Active"}},
        )

# This is not an important function, it's for bot usage statistics
@bot.message_handler(content_types=["left_chat_member"])
def deactivate(message: dict):
    member = message.left_chat_member
    if member.id == bot_id:
        groups_database.update_one(
            {"_id":message.chat.id},
            {"$set":{"Status":"Deactivate"}}
        )

def remove(chat_id: int):
    group = [i for i in groups_database.find({"_id":chat_id})]

    for admin_id in group[0]["Admins"]:
        users_database.update_one(
            {"_id":admin_id}, 
            {"$pull":{"Groups": {"id": chat_id}}}
        )

    groups_database.delete_one({"_id":chat_id})

# Sub-function 
def config() -> list:
    config = load_config("files/config.json")
    currencies_settings = config.currencies_settings
    return currencies_settings
