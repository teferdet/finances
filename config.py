import json 

def data(option: list):
    data = []

    for item in option:
        path = "files/config.json"
    
        with open(path, "rb") as file:
            if len(option) != 1:
                data.append(json.load(file)[item]) 

            else:
                data = json.load(file)[item]

    return data
