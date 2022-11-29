# finances

**Libraries and python version**
  + Python - 3.11
  + requests
  + pyTelegramBotAPI
  + bs4

**finances** - Telegram bot for viewing and converting currencies.

**Bot run**
To run the bot, you need to keep the necessary data in "config.py" and run it

Config
```
# Token, API key
token = "Telegram bot token"
api_crypto_key = "CoinMarketCap API kay"

# ID
log_id = "<Telegram channel ID>"
ID = "<Your Telegram ID>"
```
You can change other information: list of blocked currencies, version, database name, Telegram file id

Bot run
```
python main.py
```
If you need to download the libraries above:
```
pip install -r requirements.txt
```

**Characteristics of the bot**
| Function | Support |
| ------------- | ------------- |
| Language  | English, Ukrainian and Polish |
| Currencies | All currencies of the world (conversion to 9-13) |
| Cryptocurrency | BTC, ETH, USDT, LTC, TRX, SOL, TON |
| Chat function | Inline mode |

**Sources of information** 

For currencies - [fx-rate.net](https://fx-rate.net)

For crypto currencies - [CoinMarketCap](https://coinmarketcap.com/)
