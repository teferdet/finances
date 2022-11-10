import time 
import __main__
import config
import parser
import language
import keyboard
import logs

main = __main__
bot = main.bot

currency_list = [
    'American Dollar', 'Euro', 'British Pound', 
    'Czech Koruna','Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Chinese Yuan Renminbi',
    'Ukraine Hryvnia'
]

crypto_list = [
    "BTC", 'ETH', "BNB", "SOL", 
    "USDT", "TRX", "TON", "LTC",
] 

class Main:
    def __init__(self, message):
        self.func(message)

        msg = bot.send_message(
            message.chat.id, 
            language.currency_choose, 
            reply_markup=keyboard.currency_keyboard
        )
        bot.register_next_step_handler(msg, self.currency)

    def func(self, message):
        language.course(message)
        keyboard.reply(message)

    def currency(self, message):
        self.func(message)

        if message.text in ["Повернутися ⬅️", "Back ⬅️"]:
            bot.send_message(
                message.chat.id,
                language.menu,
                reply_markup=keyboard.menu
            )

        elif message.text in ['💵 Crypto', '💵 Криптовалюта']:
            currency_name = "crypto"
            
            parser.Crypto("USD", crypto_list)
            self.status(message, currency_name)
                
        else:
            try:
                currency_name = message.text.split()[1]                
            
            except IndexError:
                currency_name = message.text

            code = 0 if currency_name.upper() in ['BTC', 'ETH'] else 1
            
            parser.Currency(currency_name, code, currency_list)
            self.status(message, currency_name.upper())

    def status(self, message, currency_name):
        day = time.strftime("%d/%m/%y")
        
        keyboard.alternative_currency_key(message, currency_name)
        markup = None if currency_name in ['BTC', 'ETH'] else keyboard.currency
        
        if parser.status_code == 200 and parser.status is True:
            msg = bot.send_message(
                message.chat.id, 
                f"{language.rate} {day}\n{parser.send}",
                reply_markup=markup
            )

        elif parser.status is False:
            msg = bot.send_message(message.chat.id, language.currency_user_error)

        else:
            log(message, parser.status_code, parser.url, parser.name)
            msg = bot.send_message(message.chat.id, language.server_error)
        
        bot.register_next_step_handler(msg, self.currency)

def alternative_currency(call, currency_name):
    language.course(message=call)

    if currency_name in ["c UAH", "c EUR", "c GBP"]:
        parser.Crypto(currency_name.split()[1], crypto_list)
        status_code = parser.status_code
        
        keyboard.alternative_currency_key(
            message=call, 
            currency_name=currency_name
        )
        
        markup = keyboard.currency

    else:
        parser.Currency(currency_name, 0, currency_list)
        markup = None

    if parser.status_code == 200:
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.id,
            text=f"{language.alternative}\n{parser.send}",
            reply_markup=markup 
        ) 

    else:
        log(message, parser.status_code, parser.url, parser.name)

        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.id,
            text=language.server_error
        )

def log(message, status_code, url, name):
    logs.server(
        message, 
        status_code=status_code,
        url=url,
        name=name
    )
