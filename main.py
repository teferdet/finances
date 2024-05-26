import os
import sys
from threading import Thread
from time import sleep, strftime

sys.path.append("handlers")
sys.path.append("parser")
os.environ["PYTHONWARNINGS"] = "ignore:::atexit"

from messages_handler import bot
from parser_handler import Updater

updater_instance = Updater()
option = True

def bot_run():
    global option
    print(f"[BOT] {strftime('%d.%m.%y %H:%M:%S')}: Start work")

    while option:
        try:
            bot.polling(none_stop=True)

        except Exception as e:
            print(f"[Bot Error] {strftime('%d.%m.%y %H:%M%S')}: {e}")
            sleep(5)
            continue

if __name__ == "__main__":
    parser_handler = Thread(target=updater_instance.start, name="Parser")    
    bot_handler = Thread(target=bot_run, name="Bot")

    try:
        bot_handler.start()
        parser_handler.start()

        bot_handler.join()
        parser_handler.join()

    except KeyboardInterrupt:
        print(f"[BOT] {strftime('%d.%m.%y %H:%M:%S')}: Stop working...")

        bot.stop_polling()
        option = False
        updater_instance.stop()
    
