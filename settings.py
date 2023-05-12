import __main__ 
import keyboard 
import language 
import re
import pymongo 
import config 

bot = __main__.bot 

client = pymongo.MongoClient(config.database)
group = client['finances']['Groups']
users = client['finances']['Users']

output_currency = {
    'ARS':'Argentine Peso', 'AUD':'Australian Dollar',
    'GBP':'British Pound', 'BGN':'Bulgarian Lev',
    'CAD':'Canadian Dollar', 'CNY':'Chinese Yuan Renminbi',
    'CZK':'Czech Koruna','DKK':'Danish Krone',
    'EGP':'Egyptian Pound', 'EUR':'Euro',
    'ISK':'Iceland Krona', 'INR':'Indian Rupee',
    'ILS':'Israeli New Shekel', 'JPY':'Japanese Yen',
    'KRW':'Korean Won', 'NOK':'Norwegian Krone',
    'PLN':'Polish Zloty', 'RON':'Romanian Leu',
    'SGD':'Singapore Dollar', 'SEK':'Swedish Krona',
    'CHF':'Swiss Franc', 'TRY':'Turkish Lira',
    'UAH':'Ukraine Hryvnia', 'USD':'American Dollar'
}

currency_code = [
    'ARS','GBP', 'CAD', 'CZK', 'EGP', 'ISK',
    'ILS', 'KRW', 'PLN', 'SGD','CHF', 'UAH',
    'AUD', 'BGN', 'CNY', 'DKK', 'EUR', 'INR', 
    'JPY', 'NOK', 'RON', 'SEK', 'TRY', 'USD'
]

class Settings:
    def __init__(self, call):
        data = call.data.split()[1::]
        
        if data[0] == 'group': 
            GroupSettingsHandler(call, data)  

class GroupSettingsHandler:
    def __init__(self, call, data):
        self.call = call 
        self.data = data
        self.ID = self.call.from_user.id  
    
        language.settings_data(call)

        if self.data[0] == 'group' and len(self.data) == 1:
            self.get_admins_data() 
        
        elif len(self.data) == 2:
            self.group_setup()
        
        else: 
            self.edit_group_settings()

    def get_admins_data(self):
        admin_access = [
            item['Admin groups'] 
            for item in users.find({'_id':self.ID})
        ]
        
        if admin_access != [{}]:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=language.choose_group,
                reply_markup=keyboard.groups_keypad(admin_access)
            )

        else:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=language.error_group_list,
                reply_markup=None
            )           

    def group_setup(self):
        group_ID = self.call.data.split()[2]

        bot.edit_message_text(
            chat_id=self.call.message.chat.id, 
            message_id=self.call.message.id,
            text=language.group_item,
            reply_markup=keyboard.group_settings(self.call, group_ID)
        ) 

    def edit_group_settings(self):
        keyboard.reply(self.call)
        self.ID = int(self.call.data.split()[4])

        if self.data[1] == 'input':
            text = language.write_input
            function = self.input_currency_input
    
            bot.delete_message(
                self.call.message.json['chat']['id'], 
                self.call.message.message_id
            )

        else:
            bot.edit_message_text(
                chat_id=self.call.message.chat.id, 
                message_id=self.call.message.id,
                text=f"{language.warning} {' '.join(map(str, currency_code))}",
                reply_markup=None
            ) 
            
            text = language.write_output
            function = self.input_currency_output

        msg = bot.send_message(
            chat_id=self.call.message.chat.id, 
            text=text,
            reply_markup=keyboard.cancel 
        ) 

        bot.register_next_step_handler(msg, function)

    def input_currency_input(self, msg):
        keyboard.reply(self.call)
    
        if msg.text.split()[0] == '❌':
            text = language.exit
        
        else:  
            text = re.findall(r"\b[a-zA-Z]{3}\b", msg.text)
            group.update_one(
                {'_id':self.ID},
                {'$set':{"Currency input list":text}}
            )

            text = language.success

        bot.send_message(
            chat_id=self.call.message.chat.id, 
            text=text,
            reply_markup=keyboard.currency_keyboard 
        )
    
    def input_currency_output(self, msg):
        keyboard.reply(self.call)
        export = []

        if msg.text.split()[0] == '❌':
            text = language.exit
        
        else:  
            text = re.findall(r"\b[a-zA-Z]{3}\b", msg.text)
            
            for item in text:
                item = item.upper()

                if item in currency_code:
                    export.append(output_currency[item])

                else: 
                    bot.answer_callback_query(
                        self.call.id, 
                        f"{item} {language.item_error}",
                        show_alert=False
                    )                
            
            if export != []:
                group.update_one(
                    {'_id':self.ID},
                    {'$set':{"Currency output list":export}}
                )
                text = language.success

            else:
                text = "Error"

        bot.send_message(
            chat_id=self.call.message.chat.id, 
            text=text,
            reply_markup=keyboard.currency_keyboard 
        )

class Publishing:
    def __init__(self, message):
        self.message = message 
        types = self.message.chat.type
        language.settings_data(message)

        if types == 'private':
            self.publishing()
        
        else:
            bot.send_message(
                self.message.chat.id,
                language.settings_local_error
            )

    def publishing(self):
        keyboard.setting_keyboard(self.message)

        bot.send_message(
            self.message.chat.id, language.settings_menu,
            reply_markup=keyboard.settings_menu
        )

