import json
import sqlite3
import __main__
import config
import parser
import language
import keyboard
import logs

main = __main__
bot = main.bot

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

class Main:
    def __init__(self, message):
        logs.add_in_database(message)
        self.func(message)
        
        msg = bot.send_message(
            message.chat.id,
            language.choose,
            reply_markup=keyboard.converter
        )
        bot.register_next_step_handler(msg, self.currency)

    def func(self, message):
        global ID
        global text

        ID = message.from_user.id
        text = message.text.upper()

        language.converter(message)
        keyboard.reply(message)

    def currency(self, message):
        self.func(message)

        if message.text in ["Повернутися ⬅️", "Back ⬅️"]:
            msg = bot.send_message(
                message.chat.id,
                language.menu,
                reply_markup=keyboard.menu
            )

        else:
            cursor.execute(f"UPDATE user_data SET currency = '{text}' WHERE id = {ID}")
            connect.commit()

            msg = bot.send_message(
                message.chat.id,
                language.to_choose, 
                reply_markup=keyboard.to_converter
            )

            bot.register_next_step_handler(msg, self.to_currency)

    def to_currency(self, message): 
        self.func(message)

        if message.text in ["Повернутися ⬅️", "Back ⬅️"]:
            msg = bot.send_message(
                message.chat.id, 
                language.to_choose,
                reply_markup=keyboard.converter
            )
            bot.register_next_step_handler(msg, self.currency)

        elif message.text in ["Меню ⏭", "Menu ⏭"]:
            bot.send_message(
                message.chat.id, 
                language.menu, 
                reply_markup=keyboard.menu
            )

        else:
            cursor.execute(f"UPDATE user_data SET to_currency = '{text}' WHERE id = {ID}")
            connect.commit()
            
            self.status(message)
    
    def status(self, message):
        self.func(message)

        cursor.execute(f"SELECT currency, to_currency FROM user_data WHERE id = '{ID}'")
        currency = cursor.fetchall()[0]

        parser.Convert(currency[0], currency[1])

        if parser.status is True:
            msg = bot.send_message(
                message.chat.id,
                language.currency, 
                reply_markup=keyboard.number
            )
            bot.register_next_step_handler(msg, self.convert)

        else: 
            self.log(message, status_code, url, name)
            
            msg = bot.send_message(
                message.chat.id, 
                language.code_error, 
                reply_markup=keyboard.converter
            )
            bot.register_next_step_handler(msg, self.currency)

    def convert(self, message):
        self.func(message)

        cursor.execute(f"SELECT currency, to_currency FROM user_data WHERE id = '{ID}'")
        currency = cursor.fetchall()[0]

        if message.text in ["Повернутися ⬅️", "Back ⬅️"]:
            msg = bot.send_message(
                message.chat.id, 
                language.to_choose, 
                reply_markup=keyboard.to_converter
            )
            bot.register_next_step_handler(msg, self.to_currency)
        
        elif message.text in ["Меню ⏭", "Menu ⏭"]:
            bot.send_message(
                message.chat.id, 
                language.menu, 
                reply_markup=keyboard.menu
            )

        elif message.text in ["🔁 Змінити", "🔁 Change"]:
            cursor.execute(
                f"UPDATE user_data SET (currency, to_currency) = ('{currency[1]}', '{currency[0]}') WHERE id = {ID}"
            )
            connect.commit()

            msg = bot.send_message(
                message.chat.id, 
                f"{language.change} {currency[1]}/{currency[0]}", 
                reply_markup=keyboard.number
            )
            bot.register_next_step_handler(msg, self.convert)

        else:
            try:
                parser.Convert(currency[0], currency[1])

                keyboard.convert(
                    message, finance=parser.url
                )

                conversion = round(float(message.text)*parser.rate, 4)
                conversion = f'{conversion}, {language.during} {parser.rate}'

                msg = bot.send_message(
                    message.chat.id,
                    conversion,
                    reply_markup=keyboard.info_data
                )
                bot.register_next_step_handler(msg, self.convert)

            except ValueError as error:
                print("161: ", error)

                msg = bot.send_message(message.chat.id, language.user_error)
                bot.register_next_step_handler(msg, self.convert)
        
            except Exception as error:
                print("167: ", error)
                
                self.log(message, status_code, url, name)
                
                bot.send_message(
                    message.chat.id, 
                    language.server_error, 
                    reply_markup = keyboard.menu
                )

    def log(self, message, status_code, url, name):
        logs.server(
                message, 
                status_code=parser.status_code,
                url=parser.url,
                name=parser.name
            )
        