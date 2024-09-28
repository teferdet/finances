import os
import sys
from threading import Thread
from time import sleep

sys.path.append("handlers")
sys.path.append("parser")
os.environ["PYTHONWARNINGS"] = "ignore:::atexit"

from logs_handler import logger
from messages_handler import bot
from parser_handler import Updater

updater_instance = Updater()
option = True

def bot_run():
    global option
    logger.info(f"[BOT] Start work")

    while option:
        #try:
            bot.polling(none_stop=True)
            break

        #except Exception as e:
            #logger.error(f"[Bot Error] {e}")
            #sleep(5)
            #continue


if __name__ == "__main__":
    parser_handler = Thread(target=updater_instance.start, name="Parser")
    bot_handler = Thread(target=bot_run, name="Bot")

    try:
        bot_handler.start()
        parser_handler.start()

        bot_handler.join()
        parser_handler.join()

    except KeyboardInterrupt:
        logger.info(f"[BOT] Stop working...")

        bot.stop_polling()
        option = False
        updater_instance.stop()
