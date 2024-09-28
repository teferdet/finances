from email import message
from locale import currency
from re import findall
from urllib.request import CacheFTPHandler
from messages_handler import client, bot 
from functions.language import translate
from functions import database
from functions import keyboard
from jsoncfg import load_config

users_database = client["Users"]
groups_database = client["Groups"]
CACHE = {}

class Menu:
    def __init__(self, message: dict):
        self.message = message 
        self.text = translate(self.message, "settings")
        types = self.message.chat.type

        if types == 'private':
            self.publishing()
        
        else:
            bot.send_message(self.message.chat.id, self.text["local error"])
    
    def publishing(self):
        text = translate(self.message, "settings")["menu"] 
        ID = self.message.from_user.id
        CACHE[ID] = {}

        bot.send_message(
            self.message.chat.id, "".join(text),
            reply_markup=keyboard.settings_menu(self.message)
        )

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def back_menu(call):
    text = translate(call, "settings")["menu"] 
    ID = call.from_user.id
    CACHE[ID] = {}

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.settings_menu(call)
    )

# Settings handlers for groups
@bot.callback_query_handler(func=lambda call: call.data == "groups")
def choose_group(call: dict):
    ID = call.from_user.id
    groups = [i["Groups"] for i in users_database.find({'_id':ID})]

    if groups != [[]]:
        text = translate(call, "settings")["choose group"]
        keypad = keyboard.choose_group(call ,groups[0])

    else:
        text = translate(call, "settings")["error group list"]
        keypad = keyboard.invite_bot(call)

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text=text, reply_markup=keypad
    )

@bot.callback_query_handler(func=lambda call: call.data.split()[0] == "group")
def group_setting(call: dict):
    ID = call.from_user.id
    text = translate(call, "settings")["settings option"] 

    if CACHE[ID] == {}:
        CACHE[ID] = {
            "group": int(findall(r"-?\d+", call.data)[0]),
            "update data": [],
        }
    
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.group_setting(call)
    )

@bot.callback_query_handler(func=lambda call: call.data == "gruops_input")
def group_input(call: dict):
    text = translate(call, "settings")["input"] 

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.input_currencies(call, 0)
    )

@bot.callback_query_handler(func=lambda call: call.data == "gruops_output")
def group_output(call: dict):
    text = translate(call, "settings")["output"] 

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.output_currencies(call, 0)
    )

@bot.callback_query_handler(func=lambda call: call.data == "remove")
def remove(call: dict):
    text = translate(call, "settings")["remove"] 

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text=text,
        reply_markup=keyboard.group_remove(call)
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def confirm(call: dict):
    ID = call.from_user.id
    text = translate(call, "settings") 
    message = text["success remove"]
    database.remove(CACHE[ID]["group"])

    try:
        bot.leave_chat(CACHE[ID]["group"])
    except: 
        pass

    bot.answer_callback_query(call.id, message, show_alert=False)

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text=" ".join(text["menu"]),
        reply_markup=keyboard.settings_menu(call)
    )

@bot.callback_query_handler(func=lambda call: call.data == "bot")
def bot_settings(call: dict):
    ID = call.from_user.id
    text = translate(call, "settings")["settings option"] 

    if CACHE[ID] == {}:
        CACHE[ID] = {
            "update type":None,
            "update data": [],
        }
    
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.bot_settings(call)
    )

@bot.callback_query_handler(func=lambda call: call.data == "fiat")
def fiat_currency_settings(call: dict):
    ID = call.from_user.id 
    CACHE[ID]["update type"] = "Fiat currency"
    text = translate(call, "settings")["output"] 

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.output_currencies(call, 0)
    )

@bot.callback_query_handler(func=lambda call: call.data in ["settings_crypto", "stocks"])
def fiat_currency_settings(call: dict):
    ID = call.from_user.id 
    if call.data == "settings_crypto":
        CACHE[ID]["update type"] = "Crypto currency"
        option = "crypto"
    else:
        CACHE[ID]["update type"] = "Stocks"
        option = "company"

    text = translate(call, "settings")["output"] 

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.id,
        text="".join(text),
        reply_markup=keyboard.crypto_stocks_keypad(call, 0, option)
    )

@bot.callback_query_handler(func=lambda call: call.data.split()[0] in ["Output", "Input", "CSK"])
class DataProcessing:
    def __init__(self, call: dict):
        self.call = call
        self.option = call.data.split()[0]
        self.command = call.data.split()[1]
        self.text = translate(self.call, "settings")

        if self.command in ["save", "cancel"]:
            self.database_handler()
        elif self.command == "position":
            self.choose_list()
        elif self.option == "Output":
            self.output_commands_handler()
        elif self.option in ["Input", "CSK"]:
            self.input_commands_handler()

    def database_handler(self):
        ID = self.call.from_user.id 
        text = self.text["settings option"]
        
        if self.command == "save":            
            if "group" in list(CACHE[ID]):
                groups_database.update_one(
                    {"_id":CACHE[ID]["group"]}, 
                    {"$set":{self.option:CACHE[ID]["update data"]}}
                )

            else:
                update_type = CACHE[ID]["update type"]
                users_database.update_one(
                    {"_id":ID}, 
                    {"$set":{update_type:CACHE[ID]["update data"]}}
                )

            message = self.text["success"]

        elif self.command == "cancel":
            message = self.text["exit"]

        if "group" in list(CACHE[ID]):
            keypad = keyboard.group_setting(self.call)
        else:
            keypad = keyboard.bot_settings(self.call)

        bot.answer_callback_query(
            self.call.id, message, show_alert=False
        )

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=text,
            reply_markup=keypad
        )

        CACHE[ID]["update data"] = []
    
    def choose_list(self):
        point = int(self.call.data.split()[2])
        
        if self.option == "Input":
            self.keypad = keyboard.input_currencies(self.call, point)
        elif self.option == "CSK":
            option = self.call.data.split()[3]
            self.keypad = keyboard.crypto_stocks_keypad(self.call, point, option)
        else:
            self.keypad = keyboard.output_currencies(self.call, point)

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=self.call.message.text,
            reply_markup=self.keypad
        )
    
    def input_commands_handler(self):
        ID = self.call.from_user.id 
        data = CACHE[ID]["update data"]
        command = " ".join(self.call.data.split()[1::])

        if command in data:
            data.remove(command)
            bot.answer_callback_query(self.call.id, self.text["alert remove"], show_alert=False)    

        elif command not in data:
            bot.answer_callback_query(self.call.id, self.text["alert add"], show_alert=False)
            data.append(command)

    def output_commands_handler(self):
        ID = self.call.from_user.id 
        data = CACHE[ID]["update data"]
        currency = " ".join(self.call.data.split()[1::])

        if currency in data:
            data.remove(self.get_currencies())
            bot.answer_callback_query(self.call.id, self.text["alert remove"], show_alert=False)    

        elif currency not in data:
            bot.answer_callback_query(self.call.id, self.text["alert add"], show_alert=False)
            data.append(self.get_currencies())

    def get_currencies(self):
        config = load_config("files/config.json")["currencies_settings"]
        curensies = [i.value for i in config["convert_currencies"]]
    
        return findall("|".join(curensies), self.call.data)[0]
