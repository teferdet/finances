from calendar import c
from re import findall
from time import strftime
from functions.language import translate
from functions.keyboard import crypto_keypad
from messages_handler import bot, client

users_database = client["Users"]
database = client["Currency"]

class CryptoHandler:
    def __init__(self, message: dict):
        self.message = message
        ID = message.from_user.id 

        amount_data = findall(r"\d+\.*\d*", self.message.text)
        self.amount = float(amount_data[0]) if amount_data != [] else 1
        
        self.value = GetCurrencyData("USD", self.amount, ID)
        self.publishing()

    def publishing(self):
        day = strftime("%d.%m.%y")
        text = translate(self.message, "exchange rate")["sub rate"] 
        keypad = crypto_keypad(self.amount)

        bot.send_message(
            self.message.chat.id, 
            text.format(day, self.value),
            reply_markup=keypad
        )

class AlternativeConvert:
    def __init__(self, call: dict, currency: str, amount: float):
        self.call = call
        self.amount = amount
        ID = call.from_user.id 
        
        self.value = GetCurrencyData(currency, self.amount, ID)
        self.publishing()

    def publishing(self):
        day = strftime("%d.%m.%y")
        text = translate(self.call, "exchange rate")["sub rate"] 
        keypad = crypto_keypad(self.amount)

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=text.format(day, self.value),
            reply_markup=keypad
        ) 

class GetCurrencyData:
    def __init__(self, currency: str, amount: float, ID: int):
        self.amount = amount
        self.currency = currency
        self.value = []
        self.ID = ID

        query = {"_id":"Crypto"}
        self.data = [i[self.currency] for i in database.find(query)][0]

        self.data_processin()

    def data_processin(self):
        user_data = users_database.find_one({"_id":self.ID})["Crypto currency"]
        for key in self.data:   
            if key in user_data:
                name = self.data[key][0]
                price = float(self.data[key][1])
                price = round(price*self.amount, 4)
                symbol = self.data[key][2]

                item = f"💵 {name}/{self.currency.upper()} {price}{symbol}"
                self.value.append(item)

        self.__str__()

    def __str__(self) -> str:
        return "\n".join(self.value)
