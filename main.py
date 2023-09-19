import config
import telebot
import threading
import sys

bot = telebot.TeleBot(config.token)

sys.path.append('translation')
sys.path.append('functions')
sys.path.append('parser')

import parser
import message_handler
import inline_mode

params = {
    "timeout": 10,
    "long_polling_timeout": 5
}

if __name__ == '__main__':
    threading.Thread(target=bot.infinity_polling, kwargs=params).start()
    threading.Thread(target=parser.main).start()
