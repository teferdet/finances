import __main__ as main
import keyboard 
import language  
import groups_handler

bot = main.bot 
data = "settings"

class Settings:
    def __init__(self, call):
        data = call.data.split()[1::]
        
        if data[0] == 'group': 
            groups_handler.GroupSettingsHandler(call, data)  

class Publishing:
    def __init__(self, message):
        self.message = message 
        types = self.message.chat.type

        if types == 'private':
            self.publishing()
        
        else:
            error = language.translate(self.message, data, 'settings local error')
            bot.send_message(self.message.chat.id, error)

    def publishing(self):
        text = language.translate(self.message, data, "menu")

        bot.send_message(
            self.message.chat.id, text,
            reply_markup=keyboard.setting_keyboard(self.message)
        )

