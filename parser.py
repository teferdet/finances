import requests, json, config, time

def uah_course():
    global usd_r, usd, eur_r, eur, gbp, gbp_r, pln, pln_r, czk, czk_r, jpy
    global ubank, uah_send

    ubank = requests.get(config.nbu)

    if ubank.status_code == 200:
        nbu_data = json.loads(ubank.text)
        for coin in nbu_data:
            if coin['cc'] == "USD":
                usd_r = coin["rate"]
                usd = round(coin["rate"], 2)

            elif coin['cc'] == "EUR":
                eur_r = coin["rate"]
                eur = round(coin["rate"], 2)
            
            elif coin['cc'] == "GBP":
                gbp_r = coin["rate"] 
                gbp = round(coin["rate"], 2)
        
            elif coin['cc'] == "PLN":
                pln_r = coin["rate"]
                pln = round(coin["rate"], 2)

            elif coin['cc'] == "CZK":
                czl_r = coin["rate"]
                czk = round(coin["rate"], 2)

            elif coin['cc'] == "JPY":
                jpy = round(coin["rate"], 2)
    
        uah_send = f"🇺🇸 USD = {usd}₴\n🇪🇺 EUR = {eur}₴\n🇬🇧 GBP = {gbp}₴\n🇵🇱 PLN = {pln}₴\n🇨🇿 CZK = {czk}₴\n🇯🇵 JPY = {jpy}₴"
    
    else: pass
    
def crypto_course():
    global crypto_send, crypto_data
    
    headers = {'X-CMC_PRO_API_KEY' : config.api_crypto_key, 'Accepts': 'application/json'}
    params = {'start':'1','limit':'25','convert':'USD'}
    crypto_data = requests.get(config.crypto, params=params, headers=headers)

    if crypto_data.status_code == 200:
        crypto_info = json.loads(crypto_data.text)
        coin = crypto_info['data']

        for x in coin:
            if x['symbol'] == "BTC":
                btc = round(x['quote']['USD']['price'], 4)
            
            elif x['symbol'] == "ETH":
                eth = round(x['quote']['USD']['price'], 4)

            elif x['symbol'] == "BNB":
                bnb = round(x['quote']['USD']['price'], 4)
            
            elif x['symbol'] == "SOL":
                sol = round(x['quote']['USD']['price'], 4)

            elif x['symbol'] == "USDT":
                usdt = round(x['quote']['USD']['price'], 4)
            
            elif x['symbol'] == "TRX":
                trx = round(x['quote']['USD']['price'], 4)
            
        crypto_send = f"💵 BTC = {btc}$\n💵 ETH = {eth}$\n💵 BNB = {bnb}$\n💵 SOL = {sol}$\n💵 USDT = {usdt}$\n💵 TRX = {trx}$"

    else: pass
