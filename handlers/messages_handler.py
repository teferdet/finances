from time import strftime
from telebot import TeleBot 
from pymongo import MongoClient, UpdateOne
from jsoncfg import load_config
 
config = load_config("files/config.json")
bot = TeleBot(config.telegram_token.value)
client = MongoClient(config.database.value)["finances"]

import inline_handler
import settings_handler
from functions import keyboard, database
from functions.language import translate
from crypto_handler import CryptoHandler
from stocks_hadler import StocksHandler
from er_handler import ExchangeRate
from groups_handlers import GroupsHandler

@bot.message_handler(commands=["start"])
class Start:
    def __init__(self, message: dict):
        self.message = message
        self.language = message.from_user.language_code
    
        user_name = self.message.from_user
        self.name = f"{user_name.first_name} {user_name.last_name}"
        if self.name.split()[1] == "None":
            self.name = user_name.first_name

        self.publishing()
    
    def publishing(self):
        hello = translate(self.message, "time")[self.time()]
        menu_translate = translate(self.message, "menu")

        if self.message.chat.type == "private":
            menu = menu_translate["private"]
            keypad = keyboard.main_keyboard

        else:
            menu = menu_translate["group"]
            keypad = None

        bot.send_message(self.message.chat.id, f"{hello} {self.name} 👋") 
        bot.send_message(
            self.message.chat.id, "".join(menu),
            reply_markup=keypad,
            parse_mode="HTML"
        )
        
        database.User(self.message)

    def time(self) -> str:
        date = int(strftime("%H"))
        
        if 6 <= date <= 11:
            time = "morning"
        elif 12 <= date <= 18:
            time = "day"
        elif 19 <= date <= 21:
            time = "evening"
        else:
            time = "night"

        return time

@bot.message_handler(commands=["settings"])
def settings(message: dict):
    settings_handler.Menu(message)

@bot.message_handler(commands=["about"])
def about(message: dict):
    text = translate(message, "other")["info"]
    version = config.version.value

    bot.send_message(
        message.chat.id, text.format(version),
        reply_markup=keyboard.about()
    )

@bot.message_handler(commands=["expense_manager"])
def about(message: dict):
    if message.from_user.id == 1693890078:
        bot.send_message(
            message.chat.id, "finances: Expense manager",
            reply_markup=keyboard.mini_app()
        )
    
    else:
        bot.send_message(
            message.chat.id, "Sorry, this feature is not available for you now",
        )

@bot.message_handler(commands=["donate"])
def donate(message: dict):
    text = translate(message, "other")["donate"]

    bot.send_message(
        message.chat.id, "".join(text),
        reply_markup=keyboard.donate(),
        parse_mode="HTML"
    )

@bot.message_handler(commands=["privacy"])
def privacy(message: dict):
    contant =translate(message, "other")["privacy"]
    version = config.privacy_update.value

    privacy_text = "".join(contant['text'])
    update = contant['update']

    text = f"{privacy_text}\n\n{update}".format(version)

    bot.send_message(
        message.chat.id, text,
        parse_mode="HTML"
    )

@bot.message_handler(commands=["help"])
def help(message: dict):
    text = translate(message, "other")["help"]["main"]

    bot.send_message(
        message.chat.id, "".join(text),
        reply_markup=keyboard.help(message, True),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: True)
def all_massages(message: dict):
    command = message.text.split()[0]

    if message.chat.type == "private":
        if command == "/stocks":
            StocksHandler(message)
        elif command == "/crypto":
            CryptoHandler(message)
        else:
            ExchangeRate(message)
    else:
        GroupsHandler(message)
