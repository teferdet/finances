import time
import config
import __main__
import language
import keyboard
import parser 

main = __main__
bot = main.bot

class Main:
    def __init__(self, message):
        self.func(message)

        msg = bot.send_message(
            message.chat.id,
            language.shares_choose, 
            reply_markup=keyboard.keyboard_shares
        )
        
        bot.register_next_step_handler(msg, self.shares)
    
    def func(self, message):
        language.course(message)
        keyboard.reply(message)

    def shares(self, message):
        self.func(message)

        if message.text in ["Повернутися ⬅️", "Back ⬅️"]:
            bot.send_message(
                message.chat.id,
                language.menu,
                reply_markup=keyboard.menu
            )

        elif message.text in ["🌐 IT"]:
            shares_list = [
                "GOOGL", "META", "AMZN",
                "PAYPL", "MSFT",
                ]
            self.status(message, shares_list)

        elif message.text in ["🛠 Technologies", "🛠 Технтології"]:
            shares_list = [
                "TSLA", "NVDA", "AMZN",
                "AMD", "INTC",
            ]
            self.status(message, shares_list)

        else:
            msg = bot.send_message(message.chat.id, language.shares_user_error)
            bot.register_next_step_handler(msg, self.shares)

    def status(self, message, shares_list):
        day = time.strftime("%d/%m/%y")
        parser.Shares(shares_list)                

        if parser.status_code == 200:
            msg = bot.send_message(
            message.chat.id, 
            f"{language.rate} {day}\n{parser.send}"
            )

            html = open("index.html", 'rb')
            bot.send_document(message.chat.id, document=html)
            
        else:
            msg = bot.send_message(message.chat.id, server_error)
        
        bot.register_next_step_handler(msg, self.shares)
