import requests, json, config

ubank = requests.get(config.nbu)
headers = {'X-CMC_PRO_API_KEY' : config.api_crypto_key, 'Accepts': 'application/json'}
params = {'start':'1','limit':'25','convert':'USD'}
crypto_data = requests.get(config.crypto, params=params, headers=headers)

if ubank.status_code == 200:
    nbu_data = json.loads(ubank.text)
    usd_in_uah = filter(lambda x: x.get("r030") == 840, nbu_data)
    for usd_info in usd_in_uah:
        usd_r = usd_info['rate']
        usd = round(usd_info['rate'], 2)
    
    eur_in_uah = filter(lambda x: x.get("r030") == 978, nbu_data)
    for eur_info in eur_in_uah:
        eur_r = eur_info['rate']
        eur = round(eur_info['rate'], 2)
    
    gbp_in_uah = filter(lambda x: x.get("r030") == 826, nbu_data)
    for gbp_info in gbp_in_uah:
        gbp_r = gbp_info['rate']
        gbp = round(gbp_info['rate'], 2)
    
    pln_in_uah = filter(lambda x: x.get("r030") == 985, nbu_data)
    for pln_info in pln_in_uah:
        pln_r = pln_info['rate']
        pln = round(pln_info['rate'], 2)
    
    czk_in_uah = filter(lambda x: x.get("r030") == 203, nbu_data)
    for czk_info in czk_in_uah:
        czk_r = czk_info['rate']
        czk = round(czk_info['rate'], 2)
    
    jpy_in_uah = filter(lambda x: x.get("r030") == 	392, nbu_data)
    for jpy_info in jpy_in_uah:
        jpy = round(jpy_info['rate'], 2)

    uah_send = f"🇺🇸 USD = {usd}₴\n🇪🇺 EUR = {eur}₴\n🇬🇧 GBP = {gbp}₴\n🇵🇱 PLN = {pln}₴\n🇨🇿 CZK = {czk}₴\n🇯🇵 JPY = {jpy}₴"

else:
    pass

if crypto_data.status_code == 200:
    crypto_info = json.loads(crypto_data.text)
    coin = crypto_info['data']
    
    for btc in coin:
        if btc['symbol'] == 'BTC':
            btc_m = round(btc['quote']['USD']['price'], 4)
    
    for eth in coin:
        if eth['symbol'] == 'ETH':
            eth_m = round(eth['quote']['USD']['price'], 4)
    
    for usdt in coin:
        if usdt['symbol'] == "USDT":
            usdt_m = round(usdt['quote']['USD']['price'], 4)
    
    for bnb in coin:
        if bnb['symbol'] == "BNB":
            bnb_m = round(bnb['quote']['USD']['price'], 4)
    
    for sol in coin:
        if sol['symbol'] == "SOL":
            sol_m = round(sol['quote']['USD']['price'], 4)
    
    for trx in coin:
        if trx['symbol'] == "TRX":
            trx_m = round(trx['quote']['USD']['price'], 4)

    crypto_send = f"💵 BTC = {btc_m}$\n💵 ETH = {eth_m}$\n💵 BNB = {bnb_m}$\n💵 SOL = {sol_m}$\n💵 USDT = {usdt_m}$\n💵 TRX = {trx_m}$"

else:
    pass