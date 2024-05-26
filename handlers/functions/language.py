import json 

def translate(lang: object, option:str) -> dict:
    user_language = lang.from_user.language_code
    
    if user_language not in config():
        user_language = "en"

    path = f"files/languages/{user_language}.json"
    with open(path, encoding="utf-8") as file:
        file = json.load(file)
        translate = file[option]
    
    return translate

def config() -> list:
    with open("files/config.json", encoding="utf-8") as file:
        file = json.load(file)
        return file["languages"]
