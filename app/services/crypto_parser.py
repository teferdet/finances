"""
Crypto parser — fetches cryptocurrency data from CoinMarketCap API.
"""

from __future__ import annotations

import datetime
from typing import Dict, Optional

import aiohttp

from app.config import get_settings
from app.db import get_db
from app.logger import get_logger

log = get_logger("parser.crypto")

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"


async def fetch_crypto() -> Optional[dict]:
    """
    Fetch crypto data from CoinMarketCap for all configured fiat currencies.
    Returns the full crypto dict or None on failure.
    """
    settings = get_settings()
    api_key = settings.api_keys.crypto
    if not api_key or len(api_key) < 5:
        log.error("CoinMarketCap API key not configured")
        return None

    convert_currencies = settings.convert_crypto
    if not convert_currencies:
        log.warning("No convert_crypto currencies configured")
        return None

    headers = {"X-CMC_PRO_API_KEY": api_key, "Accepts": "application/json"}
    symbol_map = settings.symbol_map

    crypto_data: dict = {
        "update": [
            datetime.date.today().strftime("%B %d"),
            datetime.datetime.now().strftime("%H:%M"),
        ]
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for currency in convert_currencies:
            params = {"start": "1", "limit": "100", "convert": currency}
            try:
                async with session.get(CMC_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        log.error("CMC HTTP %d for %s", resp.status, currency)
                        crypto_data[currency] = {}
                        continue
                    data = await resp.json()
                    coins = data.get("data", [])
                    target_symbol = symbol_map.get(currency.upper(), "$")

                    currency_entries: Dict[str, list] = {}
                    for coin in coins:
                        name = coin.get("symbol")
                        price = coin.get("quote", {}).get(currency, {}).get("price")
                        if name and price is not None:
                            currency_entries[name] = [name, round(float(price), 4), target_symbol]

                    crypto_data[currency] = currency_entries
                    log.info("[Crypto] %s: %d coins fetched", currency, len(currency_entries))

            except Exception as exc:
                log.error("[Crypto] Error fetching %s: %s", currency, exc)
                crypto_data[currency] = {}

    # Save to MongoDB
    db = get_db()
    try:
        doc = crypto_data.copy()
        doc["_id"] = "crypto"
        await db["Crypto&Stocks"].replace_one({"_id": "crypto"}, doc, upsert=True)
        log.info("[Crypto] Saved to MongoDB")

        # Sync flat price cache for portfolio P&L
        try:
            from app.services.portfolio_service import update_current_prices

            await update_current_prices()
        except Exception as exc:
            log.warning("[Crypto] Failed to sync current_prices: %s", exc)
    except Exception as exc:
        log.error("[Crypto] Failed to save to DB: %s", exc)

    return crypto_data
