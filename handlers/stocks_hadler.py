from re import findall
from time import strftime
from messages_handler import bot, client
from functions.language import translate

users_database = client["Users"]
database = client["Currency"]

class StocksHandler:
    def __init__(self, message: dict):
        self.bot = bot
        self.value = []
        self.message = message
        self.ID = self.message.from_user.id

        amount = findall(r"\d+\.*\d*", self.message.text)
        self.amount = float(amount[0]) if amount != [] else 1

        self.data_processin()
    
    def data_processin(self):
        query = {"_id":"stocks"}
        data = [i for i in database.find(query)][0]
        user_data = users_database.find_one({"_id":self.ID})["Stocks"]

        for key in data:   
            if key in user_data:    
                price = float(data[key][2])
                price = round(price*self.amount, 4)
                symbol = data[key][0]

                item = f"💵 {symbol} {price}$"
                self.value.append(item)
        
        self.value = "\n".join(self.value)
        self.publishing()


    def publishing(self):
        day = strftime("%d.%m.%y")
        text = translate(self.message, "exchange rate")["sub rate"] 

        self.bot.send_message(
            self.message.chat.id, 
            text.format(day, self.value)
        )
