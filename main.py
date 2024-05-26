import os
import sys
from signal import signal, SIGINT
from threading import Thread
from time import sleep, strftime

sys.path.append("handlers")
sys.path.append("parser")
os.environ["PYTHONWARNINGS"] = "ignore:::atexit"

from messages_handler import bot
from parser_handler import Updater

def signal_handler(sig, frame):
    print('Stopping...')
    updater_instance.stop()
    parser_handler.join()
    bot.stop_polling()
    sys.exit(0)

signal(SIGINT, signal_handler)
    
if __name__ == "__main__":
    global updater_instance, parser_handler
    
    print(f"[BOT] {strftime('%d.%m.%y %H:%M:%S')}: Start work")
    
    updater_instance = Updater()
    parser_handler = Thread(target=updater_instance.start, name="Parser")
    parser_handler.start()
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=30)

        except Exception as e:
            print(f"[BOT ERROR] {strftime('%d.%m.%y %H:%M:%S')}: {e}")
            sleep(5)
            bot.stop_polling()
