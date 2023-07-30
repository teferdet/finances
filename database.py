import config
import pymongo 

client = pymongo.MongoClient(config.database)
group = client['finances']['Groups']
users = client['finances']['Users']
settings = client['finances']['Settings']
currency = client['finances']['Currency']

setting = {
    "_id":0,
    "links":[
        "https://github.com/teferdet/finances",
        "https://t.me/teferdet",
        "https://t.me/ershar_speak",
        "https://www.buymeacoffee.com/teferdet",
        "https://teferdet.diaka.ua/teferdet"
    ],
    "block currency list":["RUB", "BYR", "HUF", "RSD"],
    "file id":{
        "anthem of Ukraine":"",
        "glory to Ukraine":""
    },
    "version":"3.4"
}

crypto = {
    "_id":"Crypto",
    "USD":{
        "date":"",
        "rate":"",
        "time":0
    },
    "GBP":{
        "date":"",
        "rate":"",
        "time":0
    },
    "EUR":{
        "date":"",
        "rate":"",
        "time":0
    },
    "UAH":{
        "date":"",
        "rate":"",
        "time":0
    },
    "PLN":{
        "date":"",
        "rate":"",
        "time":0
    },
    "CZK":{
        "date":"",
        "rate":"",
        "time":0
    },
}

share = {
    "_id":"Shares",
    "data":"",
    "time":0,
    "date":""
}

settings.insert_one(setting)
currency.insert_one(crypto)
currency.insert_one(share)

print('The database has been created')