import config
import telebot
import threading
import sys
import time

bot = telebot.TeleBot(config.data(["token"]))

sys.path.append('parser')
sys.path.append('translation')
sys.path.append('functions')
sys.path.append('settings')

import parser
import message_handler
import inline_mode

def work():
    while True:
        try:
            bot.polling(none_stop=True)
        
        except Exception as e:
            print(f"\nWARNING: {e}")
            time.sleep(5)
            continue

if __name__ == '__main__':
    threading.Thread(target=work).start()
    threading.Thread(target=parser.refreshed).start()
