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
            message.chat.id, language.shares_choose, 
            reply_markup = keyboard.keyboard_shares
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
                reply_markup = keyboard.menu
            )
            main.bot.clear_step_handler(message)

        elif message.text in ["🌐 IT"]:
            shares_list = [
                "GOOGL", "META",
                "PAYPL", "MSFT",
                "AMZN"
                ]
            self.test(message, shares_list)

        elif message.text in ["🛠 Technologies","🛠 Технтології"]:
            shares_list = [
                "TSLA", "NVDA",
                "AMD", "INTC",
                "AMZN"
            ]
            self.test(message, shares_list)

        else:
            msg = bot.send_message(message.chat.id, language.shares_user_error)
            bot.register_next_step_handler(msg, self.shares)

    def test(self, message, shares_list):
        global msg
        
        day = time.strftime("%d/%m/%y")
        parser.Shares(shares_list)                

        if parser.status_code == 200:
            msg = bot.send_message(
            message.chat.id, 
            f"{language.rate} {day}\n{parser.send}"
            )

        else:
            msg = bot.send_message(message.chat.id, server_error)
        
        bot.register_next_step_handler(msg, self.shares)
"""
def shares(message):
    global server
    
    day = time.strftime("%d/%m/%y")
    
    language.course(message)
    keyboard.translate(message)

    if message.text == "Повернутися ⬅️" or message.text == "Back ⬅️":
        bot.send_message(message.chat.id, language.menu, reply_markup=keyboard.menu)
        main.bot.clear_step_handler(message)
    
    else:
        try:
            parser.rate_list()
            url = "gf shares"
            status_code = parser.status_code

            if message.text == "🌐 IT":
                send = parser.tey

            elif message.text == "🛠 Technologies" or message.text == "🛠 Технтології":
                send = parser.tex
        
            if status_code == 200:
                reboot = bot.send_message(
                    message.chat.id, 
                    f"{language.course} {day}\n{send}"
                )
            
            else:
                logs.server(url)
                reboot = bot.send_message(message.chat.id, server_error)

        except:
            reboot = bot.send_message(message.chat.id, language.user_error)
        
        bot.register_next_step_handler(reboot, shares)
"""
