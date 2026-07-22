[← Back to docs index](README.md)

# External API Reference

The bot integrates with several external services and Telegram Bot API features to provide real-time financial market data, guest query responses, and portfolio synchronization.

## 1. Telegram Bot API 10.x Guest Queries & Communities

### Target: Telegram Bot API (`answerGuestQuery`)
- **Module:** `app/handlers/guest.py`
- **Mechanism:** `aiogram 3.x` handler (`@router.guest_message(F.guest_query_id)`).
- **Functionality:** Handles mentions of `@bot` in non-member chats. The bot receives `guest_message` updates containing a `guest_query_id` and must respond using `message.answer_guest_query(result=InlineQueryResultArticle(...))`.

### Target: Telegram Communities (Bot API 10.2)
- **Module:** `app/repositories/communities.py`
- **Functionality:** Maps parent community entities to associated supergroups and channels in MongoDB.

## 2. Fiat Exchange Rates

### Target: `fx-rate.net`
- **Module:** `app/services/fiat_parser.py`
- **Mechanism:** Web scraping using BeautifulSoup4.
- **Security Bypass:** `fx-rate.net` is protected by strict Cloudflare Anti-DDoS challenges. To bypass this headlessly, the bot utilizes `curl_cffi` passing the `impersonate="chrome120"` argument.
- **Flow:** Reads HTML tables looking for `.c_parameter` classes and `data-rate` attributes, standardizes country flags to emojis, and outputs directly into MongoDB.

## 3. Cryptocurrency Market Data

### Target: CoinMarketCap API (`pro-api.coinmarketcap.com`)
- **Module:** `app/services/crypto_parser.py`
- **Mechanism:** `aiohttp` async request.
- **Endpoint:** `/v1/cryptocurrency/listings/latest`
- **Authentication:** Requires `X-CMC_PRO_API_KEY` header loaded from `settings.json`.
- **Query Params:** Paginates using `start=1&limit=100`, converting against user-defined base currencies.

## 4. Stock Market Data

### Target: Yahoo Finance
- **Module:** `app/services/stocks_parser.py`
- **Mechanism:** `yfinance` Python library.
- **Implementation Note:** Because `yfinance` makes synchronous blocking calls, it is wrapped in an `asyncio.to_thread` / `run_in_executor` to prevent blocking the main asyncio event loop.

## 5. Exchange Portfolio Synchronization

Users can link their exchange accounts to the bot for automatic portfolio population. The bot handles secret management securely (`app/services/security.py`).

### Binance
- **Module:** `app/services/exchange_sync.py` -> `fetch_binance_balances`
- **Endpoint:** `https://api.binance.com/api/v3/account`
- **Authentication:** Requires an HMAC-SHA256 signature appended to the query string, signed with the user's decrypted API Secret, and an `X-MBX-APIKEY` header.

### Bybit
- **Module:** `app/services/exchange_sync.py` -> `fetch_bybit_balances`
- **Endpoint:** `https://api.bybit.com/v5/account/wallet-balance` (Requires Unified Trading Account).
- **Authentication:** Requires headers: `X-BAPI-API-KEY`, `X-BAPI-TIMESTAMP`, `X-BAPI-RECV-WINDOW`, and an `X-BAPI-SIGN` header which is an HMAC-SHA256 hash of the concatenated payload string.

---

*Last updated: 2026-07-22*

