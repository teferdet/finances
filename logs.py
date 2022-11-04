import telebot 
import sqlite3
import time
import config
import parser
from telebot import types

bot = telebot.TeleBot(config.token)

connect = sqlite3.connect(config.database, check_same_thread=False)
cursor = connect.cursor()

def start_log(message):
    date = time.strftime("%d.%m.%Y | %H:%M:%S")
    
    ID = message.from_user.id
    name = '{0.first_name} {0.last_name}'.format(message.from_user)
    username = message.from_user.username
    language = message.from_user.language_code

    cursor.execute(f"SELECT id FROM user_data WHERE id = {ID}")
    data = cursor.fetchone()

    if name.split()[1] == "None":
        name = "{0.first_name}".format(message.from_user)   
    else:
        pass

    info = [name, username, ID, language, 0, 0]

    if data is None:
        cursor.execute("""INSERT INTO user_data VALUES(?, ?, ?, ?, ?, ?)""", info)
        connect.commit()
    
    else:
        pass

    markup = types.InlineKeyboardMarkup()

    if username == None:
        markup.add(   
            types.InlineKeyboardButton(
                text = name, 
                url = f"web.telegram.org/#{ID}"
            )
        )

    else:
        markup.add(   
            types.InlineKeyboardButton(text = username, url = f"t.me/{username}")
        )

    bot.send_message(
        chat_id = config.log_id,
        text = f"#finances | #user\
        \nDate&time: {date}\
        \nID: `{ID}`\
        \nName: {name}\
        \nLanguage: {language.upper()}",
        reply_markup = markup,
        parse_mode = 'Markdown'
    )

def server(message, status_code, url, name):
    markup = types.InlineKeyboardMarkup()
    markup.add( types.InlineKeyboardButton(text = "URL", url = url))

    bot.send_message(
        chat_id = config.log_id, 
        text = f"#finaces | #server\
            \nName: {name}\
            \nStatus code: {status_code}",
        reply_markup = markup
    )

def add_in_database(message):
    ID = message.from_user.id

    cursor.execute(f"SELECT id FROM user_data WHERE id = {ID}")
    data = cursor.fetchone()

    name = '{0.first_name} {0.last_name}'.format(message.from_user)
    username = message.from_user.username
    language = message.from_user.language_code

    if name.split()[1] == "None":
        name = "{0.first_name}".format(message.from_user)   
    else:
        pass

    info = [name, username, ID, language, 0, 0]

    if data is None:
        cursor.execute("""INSERT INTO user_data VALUES(?, ?, ?, ?, ?, ?)""", info)
        connect.commit()
    
    else:
        pass

def send_database(message):
    date = time.strftime("%d.%m.%Y | %H:%M:%S")
    
    ID = message.from_user.id
    name = '{0.first_name} {0.last_name}'.format(message.from_user)
    username = message.from_user.username

    if name.split()[1] == "None":
        name = "{0.first_name}".format(message.from_user)   
    else:
        pass

    if ID == config.ID:
        try:
            with open(config.database, 'rb') as db:
                bot.send_document(
                    chat_id = config.log_id,
                    document = db,
                    caption = f"#finances | #database\
                        \nDate&time: {date}"
                )

                bot.send_message(
                    chat_id = ID, 
                    text = "Database sent successfully!"
                )

        except:
            bot.send_message(
                chat_id = config.ID, 
                text = "Error send database"
            )
    else:
        bot.send_message(
            chat_id = config.log_id,
            text = f"#finances | #database\
                \nDatabase request\
                \nDate&time: {date}\
                \nID: `{ID}`\
                \nName: {name}\
                \nUsername: {username}"
        )
