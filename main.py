import telebot
import sqlite3
import sys

import config

bot = telebot.TeleBot(config.token)

sys.path.append('translation')
sys.path.append('functions')
sys.path.append('parser')

import language
import inline_mode
import exchange_rate

import keyboard
import logs

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

cursor.execute(
    """  
    CREATE TABLE IF NOT EXISTS user_data(
        user TEXT, username TEXT, 
        id INTEGER, language TEXT,
        convert REAL
    )
    """
)
connect.commit()

@bot.message_handler(commands=["start"])
def start(message):
    language.Welcome(message)
    logs.UserInfo(message)

@bot.message_handler(commands=["info"])
def info(message):
    language.info(message)

@bot.message_handler(commands=["help"])
def help(message):
    language.help(message)

@bot.message_handler(commands=["db"])
def database(message):
    logs.SendDataBase(message)

@bot.message_handler(func=lambda message: True)
def function(message):
    if message.chat.type == 'private':
        exchange_rate.ExchangeRate(message)
    else:
        pass    

if __name__ == '__main__':
    try:
        logs.work_status("#Work | #Start\nThe bot is running")
    
    except Exception as error:
        logs.work_status(
            f"#Work | #Error\nThe bot has stopped working:\n{error}"
        )
    
    bot.polling(none_stop=True)
 