import telebot 
import sqlite3
import time
import config
import parser
from telebot import types

bot = telebot.TeleBot(config.token)

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

class UserInfo:
    def __init__(self, message):
        self.ID = message.from_user.id
        self.name = '{0.first_name} {0.last_name}'.format(message.from_user)
        self.username = message.from_user.username
        self.language = message.from_user.language_code

        if self.name.split()[1] == "None":
            self.name = message.from_user.first_name

        self.add(
            self.ID, self.name,
            self.username, self.language
        )

    def add(self, ID, name, username, language):
        cursor.execute(f"SELECT id FROM user_data WHERE id = {ID}")
        data = cursor.fetchone()

        info = [name, username, ID, language, 0]

        if data is None:
            new = True
            
            cursor.execute("""INSERT INTO user_data VALUES(?, ?, ?, ?, ?)""", info)
            connect.commit()
            
        else:
            new = False
        
        self.about_user(ID, name, username, language, new)
    
    def about_user(self, ID, name, username, language, new):
        date = time.strftime("%d.%m.%Y | %H:%M:%S")
        
        markup = types.InlineKeyboardMarkup()
        if username != "None":
            markup.add(   
                types.InlineKeyboardButton(text=username, url=f"t.me/{username}")
            )
        else:
            markup = None

        if new is True:
            bot.send_message(
                chat_id=config.log_id,
                text=f"#finances | #user\
                    \nDate&time: {date}\
                    \nID: `{ID}`\
                    \nName: {name}\
                    \nLanguage: {language.upper()}",
                reply_markup=markup,
                parse_mode='Markdown'
            )

class SendDataBase:
    def __init__(self, message):
        ID = message.from_user.id
        name = '{0.first_name} {0.last_name}'.format(message.from_user)
        username = message.from_user.username

        if name.split()[1] == "None":
            name = message.from_user.first_name   
        else:
            pass
        
        self.who_request(ID, name, username)
        
    def who_request(self, ID, name, username):
        date = time.strftime("%d.%m.%Y | %H:%M:%S")
        
        if ID == config.ID:
            self.send_database(ID)
            
        else:
            bot.send_message(
                chat_id=config.log_id,
                text=f"#finances | #database\
                    \nDatabase request\
                    \nDate&time: {date}\
                    \nID: `{ID}`\
                    \nName: {name}\
                    \nUsername: {username}"
            )

    def send_database(self, ID):
        date = time.strftime("%d.%m.%Y | %H:%M:%S")
        
        try:
            with open(f"{config.database}", "rb") as db:
                bot.send_document(
                    chat_id=config.log_id,
                    document=db,
                    caption=f"#finances | #database\
                    \nDate&time: {date}"
                )
            
            bot.send_message(
                chat_id=ID, 
                text="Database sent successfully!"
            )
            
        except Exception as error:
            bot.send_message(
                chat_id=config.log_id, 
                text=error
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
        
def work_status(status):
    bot.send_message(
        chat_id=config.log_id,
        text=status
    )
