# finances
**finances — your financial assistant** 
Telegram bot that supports 3 modes, which allows you to use it conveniently and quickly in different situations. 

## Characteristics of the bot
<table>
  <tr>
    <th>Operating modes</th>
    <td>
        Groups, inline mode, private messages
    </td>
  </tr>
  <tr>
    <th>Bot interface languages</th>
    <td>
    English, Polish, Ukrainian
    </td>
  </tr>
  <tr>
    <th>Support fiat currencis</th>
    <td>
        Support for all currencies of the world
        Conversion to the following currencies: 
        USD, UAH, EUR, GPB, PLN, CZK, 
        ARS, AUD, BGN, CAD, CNY, DKK,
        EGP, ISK, INR, ILS, JPY, KNW,
        NOK, RON, SGD, SEK, CHF, TRY, 
        RUB
    </td>
  </tr>
  <tr>
    <th>Support cryptocurrencis</th>
    <td>
        BTC, ETH, USDT, BNB, SOL,
        USDC, XRP, DOGE, TON, ADA,
        AVAX, SHIB, DOT, LINK, TRX,
        BCH, NEAR, MATIC, UNI, LTC,
        PEPE, ICP, LEO, DAI, ETC, APT, 
        RNDR, HBAR, IMX, MNT, ATOM, 
        FIL, CRO, XLM, KAS, ARB, 
        FDUSD, GRT, WIF, TAO, OKB, 
        STX, OP, AR, XMR, MKR, 
        VET, SUI, INJ, BONK, THETA, 
        FTM, RUNE, LDO, FLOKI, FET, 
        CORE, ONDO, TIA, PYTH, ALGO, 
        BGB, JUP, SEI, AAVE, STRK, 
        FLOW, BEAM, ENA, GALA, AKT, 
        BSV, AGIX, BTT, AXS, DYDX, 
        QNT, FLR, NEO, EGLD, JASMY, 
        RON, CHZ, WLD, PENDLE, W, 
        SAND, XTZ, XEC, KCS, EOS,
        GNO, SNX, AIOZ, MINA, CFX
    </td>
  </tr>
  <tr>
    <th>Support stocks</th>
    <td>
        AAPL, MSFT, 2222.SR, GOOG,
        AMZN, NVDA, TSLA, META, BRK-B, 
        TSM, V, UNH, MC.PA, JPM, JNJ, 
        TCEHY, XOM, LLY, WMT, AVGO, MA, 
        PG, NVO, HD, BA, ADBE, PYPL,
        NESN.SW, ORCL, CVX, ASML, MRK, KO, 
        ABBV, PEP, BABA, BAC, OR.PA, ADBE, ROG.SW, 
        COST, IHC.AE, RMS.PA, TM, AZN, NVS, CRM, CSCO, 
        1398.HK, MCD, TMO, RELIANCE.NS, SHEL, ACN, PFE, 
        NFLX, ABT, LIN, AMD, CMCSA, DHR, 
        HDB, SAP, NKE, WFC, HSBC, 
        TMUS, DIS, TXN, UPS, CDI.PA, PRX.AS, BHP, 
        TCS.NS, PM, MS, INTC, CAT, QCOM, TTE, NEE,  
        INTU, COP, UNP, VZ, LOW, RY, UL, 
        SNY, IBM, SIE.DE, BMY, HON
    </td>
  </tr>
</table><br>
*Each currency will need to be selected in the settings for withdrawal

## How to run bot 
### Libraries and python version for work
```
  Python: 3.11
  pyTelegramBotAPI
  bs4
  requests
  pymongo
  json-cfg
```
### Step 1: Config
Enter the keys and tokens of the listed services in the fields below in the files/config.json file for the bot to work properly. Without this, some functionality will not work.
```
"telegram_token":"<Your Telegram API token>",
"database":"<Your CoinMarketCap API kay>",
"crypto_api_key":"<Your Financial Modeling Prep API kay>",
"stocks_api_key":"<MongoDB url>",
```
The config.json file has a large number of editable items that can be changed at any time at your request. One of these options is to set up automatic data updates: 
```
"update":{
    "automatic_update":true, — turn\off automatic currency update  
    "number_of_repeats":3, — number of cycles after which crypto and stocks should be updated 
    "sleep_time":3600 — time between cycles in seconds
},
```
In the urls section, enter your links to the services 
### Step 2: Installing libraries
To install all the libraries listed above, you need to run the command:
```
pip install -r requirements.txt
```
### Step 3: Bot run
Launching a bot:
```
python main.py
```

## Sources of information
  + Currencies: [fx-rate.net](https://fx-rate.net)
  + Cryptocurrencies: [CoinMarketCap](https://coinmarketcap.com/)
  + Stocks: [Financial Modeling Prep](https://site.financialmodelingprep.com/)