# finances
**finances — Telegram bot for viewing and converting fiat and cryptocurrencies, with the ability to view the share price**
**Libraries and python version**
  + Python: 3.11
  + requests
  + pyTelegramBotAPI
  + bs4
  + pymongo
## Bot run
To run the bot, you need to enter the necessary data into the config.py file:
### Config
```
# Token, API keys, database
token = "<Your Telegram API token>"
share_api_kay = '<Your Financial Modeling Prep API kay>'
database = "<MongoDB url>"
```
>You can change other information: list of blocked currencies, version, database name, Telegram file id in database 
### Database 
To create a database, run this file. It will automatically do all the work for you
```
python database.py
```
### Bot run
```
pip install -r requirements.txt
```
>If you need to download the libraries above
```
python main.py
```
>Run bot
## Characteristics of the bot
| Function | Support |
| ------------- | ------------- |
| Language  | English, Ukrainian and Polish |
| Currencies | All currencies of the world (conversion to 9-13) |
| Cryptocurrency | BTC, ETH, USDT, LTC, TRX, SOL, TON |
| Chat function | Inline mode and groups |

## Sources of information
  + Currencies: [fx-rate.net](https://fx-rate.net)
  + Crypto currencies: [CoinMarketCap](https://coinmarketcap.com/)
  + Share: [Financial Modeling Prep](https://site.financialmodelingprep.com/)
