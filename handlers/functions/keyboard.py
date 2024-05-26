from json import load
from telebot import types
from functions.language import translate
from messages_handler import bot

keys = ["delete", "er", "crypto", "q&a"]

main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.row(  
    types.KeyboardButton("🇺🇦 UAH"), 
    types.KeyboardButton("🇺🇸 USD"),
    types.KeyboardButton("🇬🇧 GBP")
) 
main_keyboard.row(  
    types.KeyboardButton("🇪🇺 EUR"),
    types.KeyboardButton("🇵🇱 PLN"), 
    types.KeyboardButton("🇨🇿 CZK")
)
main_keyboard.row(  
    types.KeyboardButton("🇨🇭 CHF"),
    types.KeyboardButton("🇧🇬 BGN"), 
    types.KeyboardButton("🇯🇵 JPY")
)

# Main keypads 
def er_keypad(message: object, currency: str, amount: float, index: int):
    if index == 0:
        text = f"{currency.upper()}/{translate(message, 'keyboard')['other']}"
    else:
        text = f"{translate(message, 'keyboard')['other']}/{currency.upper()}"

    callback_data = f"er {currency} {amount} {index}"

    keypad = types.InlineKeyboardMarkup()
    keypad.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))

    return keypad

def crypto_keypad(amount: float):
    keypad = types.InlineKeyboardMarkup()
    keypad.row(   
        types.InlineKeyboardButton(text="£", callback_data=f"crypto GBP {amount}"),
        types.InlineKeyboardButton(text="€", callback_data=f"crypto EUR {amount}"),
        types.InlineKeyboardButton(text="₴", callback_data=f"crypto UAH {amount}")
    )
    keypad.row(   
        types.InlineKeyboardButton(text="zł", callback_data=f"crypto PLN {amount}"),
        types.InlineKeyboardButton(text="Kč", callback_data=f"crypto CZK {amount}"),
    )

    return keypad

def about():
    keypad = types.InlineKeyboardMarkup()
    keypad.row(types.InlineKeyboardButton(
        text="Source", 
        url=urls()["github"]
    ))

    return keypad

def donate():
    url = urls()
    keypad = types.InlineKeyboardMarkup()
    keypad.row(
        types.InlineKeyboardButton(text="☕️ Buy me a coffee", url=url["buymeacoffee"]),    
        types.InlineKeyboardButton(text="❤️ Дяка", url=url["donatello"])
    )
    keypad.row(
        types.InlineKeyboardButton(text="🏦 Monobank", url=url["bank"]),
    )

    return keypad

def help(message: object, option: bool):
    text = translate(message, "keyboard")["help"]
    keypad = types.InlineKeyboardMarkup()
    if option:
        keypad.row(types.InlineKeyboardButton(text=text["q&a"], callback_data="q&a"))

    keypad.row(types.InlineKeyboardButton(
        text=text["communication"], url=urls()["communication"]
    ))

    return keypad

# Groups keypad
def group_keypad(message: object):
    text = translate(message, 'keyboard')['delete']
    keypad = types.InlineKeyboardMarkup()
    keypad.add(types.InlineKeyboardButton(text=text, callback_data="delete"))

    return keypad

# Settings keypads
def settings_menu(message: object):
    text = translate(message, "keyboard")["settings"]
    keypad = types.InlineKeyboardMarkup()
    keypad.row(
        types.InlineKeyboardButton(text=text["bot"],callback_data="bot"),
        types.InlineKeyboardButton(text=text["groups"], callback_data="groups")
    )
    return keypad

# Groups settings 
def invite_bot(call: object):
    text = translate(call, "keyboard")["settings"]

    keypad = types.InlineKeyboardMarkup()
    keypad.row(types.InlineKeyboardButton(text=text["add bot"], url=urls()["invite"]))
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data="menu"))

    return keypad

def choose_group(call: dict, groups: list):
    keypad = types.InlineKeyboardMarkup()
    buttons = []
    j = 1

    for i in groups:
        buttons.append( 
            types.InlineKeyboardButton(
            text=i["title"], 
            callback_data=f"group {i['id']}"
        )) 

        if j >= 3 or j == len(groups):
            keypad.row(*buttons)
            buttons = []
            j = 0
        
        j += 1

    text = translate(call, "keyboard")["settings"]["back"]
    keypad.row(types.InlineKeyboardButton(text=text, callback_data="menu"))

    return keypad

def group_setting(call: dict):
    keypad = types.InlineKeyboardMarkup()
    text = translate(call, "keyboard")["settings"]

    keypad.row(
        types.InlineKeyboardButton(text=text["input"], callback_data=f"gruops_input"),
        types.InlineKeyboardButton(text=text["output"], callback_data=f"gruops_output")
    )
    keypad.row(types.InlineKeyboardButton(text=text["remove"], callback_data=f"remove"))
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data=f"groups"))

    return keypad

def group_remove(call: dict):
    text = translate(call, "keyboard")["settings"]
    
    keypad = types.InlineKeyboardMarkup()
    keypad.row(types.InlineKeyboardButton(text=text["confirm"], callback_data=f"confirm"))
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data=f"group"))

    return keypad

def input_currencies(call: dict, point: int):
    curensies_data, convert_data = config()
    text = translate(call, "keyboard")["settings"]
    keypad = types.InlineKeyboardMarkup()
    navigation_buttons = [
        types.InlineKeyboardButton(text=text["save"], callback_data=f"Input save")
    ]
    buttons = []
    j, x = 1, 0

    if point == 0:
        navigation_buttons.append(types.InlineKeyboardButton(text=text["next list"], callback_data=f"Input position {15}"))
    
    elif point < 140:
        navigation_buttons.insert(
            0, (types.InlineKeyboardButton(text=text["back list"], callback_data=f"Input position {point-15}"))
        )
        navigation_buttons.append(
            (types.InlineKeyboardButton(text=text["next list"], callback_data=f"Input position {point+15}"))
        )

    else:
        navigation_buttons.insert(0, types.InlineKeyboardButton(text=text["back list"], callback_data=f"Input position {0}"))

    for i in curensies_data[point:]:
        buttons.append( 
            types.InlineKeyboardButton(text=f"{i['emoji']} {i['code']}", callback_data=f"Input {i['code']}")
        ) 

        if j > 4 or j == len(convert_data):
            keypad.row(*buttons)
            buttons = []
            j = 0

        if x == 15:
            break

        j += 1
        x += 1

    keypad.row(*navigation_buttons)
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data=f"Input cancel"))

    return keypad

# Bot settings
def bot_settings(call: dict):
    text = translate(call, "keyboard")["settings"]
    keypad = types.InlineKeyboardMarkup()
    keypad.row(
        types.InlineKeyboardButton(text=text["fiat"],callback_data="fiat"),
        types.InlineKeyboardButton(text=text["crypto"], callback_data="settings_crypto"),
    )
    keypad.row(types.InlineKeyboardButton(text=text["stocks"],callback_data="stocks"))
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data="menu"))

    return keypad

def crypto_stocks_keypad(call: dict, point: int, option: str):
    with open("parser/data.json", "rb") as f:
        crypto_list = load(f)[option]

    text = translate(call, "keyboard")["settings"]
    cycle = {
        "crypto":80,
        "company":70
    }
    
    keypad = types.InlineKeyboardMarkup()
    navigation_buttons = [
        types.InlineKeyboardButton(text=text["save"], callback_data=f"CSK save")
    ]
    buttons = []
    j, x = 1, 0

    if point == 0:
        navigation_buttons.append(
            types.InlineKeyboardButton(text=text["next list"], callback_data=f"CSK position {15} {option}")
        )

    elif point < cycle[option]:
        navigation_buttons.insert(
            0, (types.InlineKeyboardButton(text=text["back list"], callback_data=f"CSK position {point-15} {option}"))
        )
        navigation_buttons.append(
            (types.InlineKeyboardButton(text=text["next list"], callback_data=f"CSK position {point+15} {option}"))
        )

    else:
        navigation_buttons.append(
            types.InlineKeyboardButton(text=text["back list"], callback_data=f"CSK position {0} {option}")
        )

    for i in crypto_list[point:]:
        buttons.append(types.InlineKeyboardButton(text=i, callback_data=f"CSK {i}")) 

        if j > 4 or j == len(crypto_list):
            keypad.row(*buttons)
            buttons = []
            j = 0

        if x == 15:
            break

        j += 1
        x += 1

    keypad.row(*navigation_buttons)
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data=f"CSK cancel"))

    return keypad

# Universal functions
def output_currencies(call: dict, point: int):
    curensies_data, convert_data = config()
    text = translate(call, "keyboard")["settings"]
    keypad = types.InlineKeyboardMarkup()
    navigation_buttons = [
        types.InlineKeyboardButton(text=text["save"], callback_data=f"Output save")
    ]
    buttons = []
    j, x = 1, 0

    if point == 0:
        navigation_buttons.append(
            types.InlineKeyboardButton(text=text["next list"], callback_data=f"Output position {13}")
        )
    else:
        navigation_buttons.append(
            types.InlineKeyboardButton(text=text["back list"], callback_data=f"Output position {point-13}")
        )

    for currency in convert_data[point:]:
        for i in curensies_data:
            name = i["name"] 
            if currency == name:
                buttons.append( 
                    types.InlineKeyboardButton(
                    text=f"{i['emoji']} {i['code']}", 
                    callback_data=f"Output {currency}"
                )) 

                if j > 2 or j == len(convert_data):
                    keypad.row(*buttons)
                    buttons = []
                    j = 0
                
                if x == 15:
                    break

                x += 1
                j += 1
    
    keypad.row(*navigation_buttons)
    keypad.row(types.InlineKeyboardButton(text=text["back"], callback_data=f"Output cancel"))

    return keypad

# Keypads handler
@bot.callback_query_handler(func=lambda call: call.data.split()[0] in keys)
def InlineHandler(call: object):
    callback_data = call.data.split()
    message = call.message.json['chat']

    if call.data == "delete":
        try:
            bot.delete_message(message['id'], call.message.message_id)
        
        except:
            text = translate(call, 'keyboard')['error']
            bot.answer_callback_query(call.id, text, show_alert=False)

    elif call.data == "q&a":
        text = translate(call, "other")["help"]["q&a"]

        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.id,
            text="".join(text),
            reply_markup=help(call, False),
            parse_mode="HTML"
        )

    else:
        currency = callback_data[1]
        amount = float(callback_data[2])
        
        if callback_data[0] == "crypto":
            from crypto_handler import AlternativeConvert
            AlternativeConvert(call, currency, amount)

        else: 
            from er_handler import AlternativeConvert
            AlternativeConvert(call, currency, amount, int(callback_data[3]))

# Sun-functions
def urls() -> list:
    path = "files/config.json"
    with open(path, "rb") as file:
        file = load(file) 

    return file["urls"]

def config() -> list:
    path = "handlers/functions/currencies_data.json"
    with open(path, "rb") as f:
        curensies_data = load(f)

    path = "files/config.json"
    with open(path, "rb") as f:
        f = load(f)["currencies_settings"]
        convert_data = f["convert_currencies"]

    return curensies_data, convert_data
