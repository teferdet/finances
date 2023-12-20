import config
import json

def translate(code, data, text):
    language = code.from_user.language_code    
    
    if language not in config.data(["languages"]):
        language = 'en'

    path = f'files/languages/{language}.json'
    with open(path, "rb") as file:
        file = json.load(file)
        translate = file[data]

    if text is not None:
        translate = translate[text]
    
    return translate
