import __main__
import re

bot = __main__.bot

currency_list = [
    'American Dollar', 'Euro', 'British Pound', 
    'Czech Koruna','Japanese Yen', 'Polish Zloty',
    'Swiss Franc', 'Chinese Yuan Renminbi',
    'Ukraine Hryvnia'
]

input_currency_list = ['UAH', 'USD', "EUR", 'GBP']

class GroupHandler:
    def __init__(self, message):
        pass