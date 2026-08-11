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
            success = False
            for attempt in range(1, 4):
                try:
                    async with session.get(CMC_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            log.warning("CMC HTTP %d for %s (attempt %d/3)", resp.status, currency, attempt)
                            if attempt < 3:
                                import asyncio
                                await asyncio.sleep(2 * attempt)
                            continue

                        data = await resp.json()
                        coins = data.get("data", [])
                        target_symbol = symbol_map.get(currency.upper(), "$")

                        currency_entries: Dict[str, list] = {}
                        for coin in coins:
                            name = coin.get("symbol")
                            price = coin.get("quote", {}).get(currency, {}).get("price")
                            if name and price is not None:
                                currency_entries[name] = [
                                    name,
                                    round(float(price), 4),
                                    target_symbol,
                                ]

                        crypto_data[currency] = currency_entries
                        log.info("[Crypto] %s: %d coins fetched", currency, len(currency_entries))
                        from app.services.error_tracking import clear_source_error

                        await clear_source_error("crypto_cmc")
                        success = True
                        break

                except Exception as exc:
                    log.warning("[Crypto] Error fetching %s (attempt %d/3): %s", currency, attempt, exc)
                    if attempt < 3:
                        import asyncio
                        await asyncio.sleep(2 * attempt)

            if not success:
                log.error("[Crypto] Failed to fetch %s after 3 attempts", currency)
                crypto_data[currency] = {}
                from app.services.error_tracking import report_source_error

                await report_source_error("crypto_cmc", f"Max retries exceeded for {currency}")

    # Save to MongoDB
    db = get_db()
    try:
        doc = crypto_data.copy()
        doc["_id"] = "crypto"
        await db["Crypto&Stocks"].replace_one({"_id": "crypto"}, doc, upsert=True)
        log.info("[Crypto] Saved to MongoDB")

        # Sync flat price cache for portfolio P&L
        # Build {ticker: price_usd} from the USD section of crypto_data
        try:
            from app.services.portfolio_service import update_prices_from_exchange

            usd_section = crypto_data.get("USD", {})
            prices_map: dict[str, float] = {}
            for ticker, entry in usd_section.items():
                if isinstance(entry, list) and len(entry) >= 2:
                    try:
                        prices_map[ticker] = float(entry[1])
                    except (TypeError, ValueError):
                        pass
            if prices_map:
                await update_prices_from_exchange(prices_map)
                log.debug("[Crypto] Synced %d prices to current_prices", len(prices_map))
        except Exception as exc:
            log.warning("[Crypto] Failed to sync current_prices: %s", exc)
    except Exception as exc:
        log.error("[Crypto] Failed to save to DB: %s", exc)

    return crypto_data
