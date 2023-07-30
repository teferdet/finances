import __main__ as main
import parser 
import keyboard
import language  
import time

bot = main.bot
company = [
    'APPL', 'META', 'AMZN', 'ADBE',
    'PYPL', 'GOOGL', 'INTC', 'AMD',
    'NFLX', 'MSFT'
] 

class ShareHandler:
    def __init__(self, message):
        self.message = message
        language = message.from_user.language_code
        keyboard.inline(message)
        
        if language in ['ru', 'be']:
            bot.send_message(
                message.chat.id,
                "¯\_(ツ)_/¯ I do not understand your language",
                reply_markup=keyboard.link
            )    

        else:
            self.publishing()
    
    def publishing(self):
        data = parser.Share(company).send
        day = str(time.strftime("%d.%m.%y"))
        language.course(self.message)

        if data is not False: 
            text = f"{language.rate}{day}\n{data}"
        else:
            text = language.server_error

        bot.send_message(self.message.chat.id, text) 
