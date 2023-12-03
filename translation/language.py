import json

def translate(code, data, text):
    language = code.from_user.language_code    
    
    if language not in ['uk', 'pl']:
        language = 'en'

    path = f'translation/{language}.json'
    with open(path, "rb") as file:
        file = json.load(file)
        translate = file[data]

    if text is not None:
        translate = translate[text]
    
    return translate
