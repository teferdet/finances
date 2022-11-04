import telebot
import sqlite3
import sys

import config

bot = telebot.TeleBot(config.token)

sys.path.append('translation')
sys.path.append('functions')

import converter
import exchange_rate
import shares

import language

import keyboard
import logs

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

cursor.execute("""  CREATE TABLE IF NOT EXISTS user_data(
                    user TEXT, username TEXT, id INTEGER, language TEXT,
                    currency TEXT, to_currency TEXT)""")
connect.commit()

@bot.message_handler(commands = ["start"])
def start(message):
    language.welcome(message)
    logs.start_log(message)

@bot.message_handler(func = lambda message: message.text in ["📊 Курс валют", "📊 Exchange rate"])
def rate(message):
    exchange_rate.Main(message)

@bot.message_handler(func = lambda message: message.text in ["💱 Конвертор", "💱 Converter"])
def convert(message):
    converter.Main(message)

@bot.message_handler(func = lambda message: message.text in ["📑 Акції", "📑 Shares"])
def share(message):
    shares.Main(message)

@bot.message_handler(commands = ["info"])
def info(message):
    language.info(message)

@bot.message_handler(commands = ["help"])
def help(message):
    language.help(message)

@bot.message_handler(commands = ["db"])
def database(message):
    logs.send_database(message)

@bot.message_handler(func = lambda message: True)
def back(message):
    language.back(message)

if __name__ == '__main__':
    bot.polling(none_stop = True)
