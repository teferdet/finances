import telebot, requests, sqlite3, json
import config, keyboard, language, parser
from telebot import types

bot = telebot.TeleBot(config.token)

connect = sqlite3.connect('User_Info.db', check_same_thread=False)
cursor = connect.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS user_data(first_name TEXT, username TEXT, id INTEGER, language_code TEXT, a REAL, b REAL)""")
connect.commit()

@bot.message_handler(commands=['start'])
def start(message):
    global user_id, user_language, user_name, mes
    
    mes = message
    user_id = '{0.id}'.format(message.from_user)
    user_name = '{0.first_name}'.format(message.from_user)
    username = '{0.username}'.format(message.from_user)
    user_language = '{0.language_code}'.format(message.from_user)

    cursor.execute(f"SELECT id FROM user_data WHERE id = {user_id}")
    data = cursor.fetchone()

    info = [user_name, username, user_id, user_language, 0, 0]

    if data is None:
        cursor.execute("""INSERT INTO user_data VALUES(?, ?, ?, ?, ?, ?)""", info)
        connect.commit()

    else: pass

    language.welcome()

@bot.message_handler(func=lambda message: message.text == "📊 Курс валют" or message.text == "📊 Exchange rate")
def exchange(message):
    global user_language
    user_language = "{0.language_code}".format(message.from_user)
    
    language.exchange_rate()
    keyboard.translate()
    
    next_handler = bot.send_message(message.chat.id, language.choose, reply_markup=keyboard.exchange_rate)
    bot.register_next_step_handler(next_handler, exchange_rate)

def exchange_rate(message):
    global user_language 
    user_language = "{0.language_code}".format(message.from_user)

    keyboard.translate()
    language.exchange_rate()

    if message.text == "Повернутися ⬅️" or message.text == "Back ⬅️":
        bot.send_message(message.chat.id, language.menu, reply_markup=keyboard.menu)
    else:
        if message.text == "UAH" or message.text == "Гривня":
            language.uah_course()
            reboot = bot.send_message(message.chat.id, language.uah)
        elif message.text == "Crypto" or message.text == "Криптовалюта":
            language.crypto_course()
            reboot = bot.send_message(message.chat.id, language.crypto)
        else:
            reboot = bot.send_message(message.chat.id, language.user_error)
        bot.register_next_step_handler(reboot, exchange_rate)

@bot.message_handler(func=lambda message: message.text == "💱 Конвертор" or message.text == "💱 Converter")
def converter(message):
    global user_language
    
    language.converter()
    keyboard.translate()
    
    next_handler = bot.send_message(message.chat.id, language.choose, reply_markup=keyboard.conv_keyboard)
    bot.register_next_step_handler(next_handler, currency)

def currency(message):
    global user_language

    user_language = '{0.language_code}'.format(message.from_user)
    user_id = '{0.id}'.format(message.from_user) 
    
    user_message = message.text
    
    language.converter()
    keyboard.translate()

    if user_message == "Повернутися ⬅️" or user_message == "Back ⬅️" :
        next_handler = bot.send_message(message.chat.id, "Меню", reply_markup=keyboard.menu)
    else:
        parser.uah_course()
        if user_message == 'USD/UAH':
            x = parser.usd_r
            y = parser.usd
        elif user_message == "EUR/UAH":
            x = parser.eur_r
            y = parser.eur
        elif user_message == 'GBP/UAH':
            x = parser.gbp_r
            y = parser.gbp
        elif user_message == 'PLN/UAH':
            x = parser.pln_r
            y = parser.pln
        elif user_message == 'CZK/UAH':
            x = parser.czk_r
            y = parser.czk
        else: 
            x = 0
            y = 0

        cursor.execute(f"UPDATE user_data SET (a, b) = ('{x}', '{y}') WHERE id = {user_id}")
        connect.commit()
        
        next_handler = bot.send_message(message.chat.id, f'{user_message}, {language.currency}', reply_markup=keyboard.number)
        bot.register_next_step_handler(next_handler, convert)

def convert(message):
    global user_language

    user_language = '{0.language_code}'.format(message.from_user)
    user_id = '{0.id}'.format(message.from_user)
    
    cursor.execute(f"SELECT a, b FROM user_data WHERE id = '{user_id}'")
    number = cursor.fetchall()

    language.converter()
    keyboard.translate()

    user_message = message.text

    if user_message == "Повернутися ⬅️"  or user_message ==  "Back ⬅️":
        next_handler = bot.send_message(message.chat.id, language.choose, reply_markup=keyboard.conv_keyboard)
        bot.register_next_step_handler(next_handler, currency)
    
    elif user_message == "Меню ⏭" or user_message == "Menu ⏭":
        bot.clear_step_handler
        bot.send_message(message.chat.id, language.menu, reply_markup=keyboard.menu)
    
    else:
        try:
            if parser.ubank.status_code == 200:
                conversion = round(float(user_message)*float(number[0][0]), 2)

                reboot = bot.reply_to(message, f'{conversion}₴, {language.during} {number[0][1]}₴', reply_markup=keyboard.number)
                bot.register_next_step_handler(reboot, convert)
            
            else:
                bot.send_message(message.chat.id, language.server_error , reply_markup=keyboard.menu)
        except:
            reboot = bot.send_message(message.chat.id, language.user_error, reply_markup=keyboard.number)
            bot.register_next_step_handler(reboot, convert)

@bot.message_handler(func=lambda message: 
message.text == "Повернутися ⬅️"  or message.text ==  "Back ⬅️" or message.text == "Меню ⏭" or message.text == "Menu ⏭")
def back(message):
    global user_language, mes

    mes = message
    user_language = '{0.language_code}'.format(message.from_user)

    language.back()

@bot.message_handler(commands=['help'])
def help(message):
    global user_language, mes
    
    mes = message
    user_language = "{0.language_code}".format(message.from_user)

    language.help()

@bot.message_handler(commands=['github'])
def github(message):
    global user_language, mes

    user_language = '{0.language_code}'.format(message.from_user)
    mes = message
    
    language.github()

if __name__ == "__main__":
    bot.polling(none_stop=True)