"""
Portfolio service.
Manages adding/removing assets and computing P&L.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import UpdateOne
from app.db import get_db, get_fiat_collection_name
from app.config import get_currencies_data

log = logging.getLogger("portfolio")


# ── Data Migration ──────────────────────────────────────────────────


async def _ensure_migrated(user_id: int) -> None:
    """
    Ensure the user's portfolio uses the array format.
    Old dict format: {"BTC": amount, "ETH": amount}
    New array format:
      {"crypto": [{"ticker": "BTC", "amount": amount, ...}], ...}
    """
    db = get_db()
    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1, "stocks": 1})
    if not user:
        return

    updates = {}

    # Migrate old crypto dict
    old_port = user.get("portfolio", {})
    if isinstance(old_port, dict) and not any(k in old_port for k in ("crypto", "stock", "fiat")):
        new_crypto = [{"ticker": k.upper(), "amount": float(v)} for k, v in old_port.items()]
        updates["portfolio.crypto"] = new_crypto

    # Migrate old stocks dict
    old_stocks = user.get("stocks", {})
    if isinstance(old_stocks, dict) and old_stocks:
        new_stocks = [{"ticker": k.upper(), "amount": float(v)} for k, v in old_stocks.items()]
        updates["portfolio.stock"] = new_stocks
        updates["stocks"] = ""  # clear old field

    if updates:
        # If we modified portfolio.crypto/stock, make sure we aren't blowing away root
        # This is safe because we use dotted notation in $set
        await db["Users"].update_one({"_id": user_id}, {"$set": updates})
        log.info("Migrated portfolio for user %s: %s", user_id, updates)


# ── Modifying Portfolio ───────────────────────────────────────────


async def add_asset(
    user_id: int,
    asset_type: str,
    ticker: str,
    amount: float,
    buy_price_usd: float | None = None,
) -> float | None:
    """
    Add or add to an asset in the user's portfolio.
    If the asset already exists, it averages the cost basis (if prices are known).
    If buy_price_usd is not provided, attempts to fetch current market price.
    Returns the buy_price_usd that was used (or None if totally unknown).
    """
    await _ensure_migrated(user_id)
    db = get_db()

    ticker = ticker.upper()
    asset_type = asset_type.lower()
    if asset_type not in ("crypto", "stock", "fiat"):
        asset_type = "crypto"

    # Fetch current price if buy_price not provided
    used_price = buy_price_usd
    if used_price is None:
        if asset_type == "fiat":
            used_price = await _get_fiat_usd_price(ticker)
        else:
            doc = await db["current_prices"].find_one({"_id": ticker}, {"price_usd": 1})
            if doc and "price_usd" in doc:
                used_price = float(doc["price_usd"])

    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})
    section = portfolio.get(asset_type, []) if isinstance(portfolio, dict) else []

    if not isinstance(section, list):
        section = []

    # Check if we already have this asset
    existing_idx = None
    for i, lot in enumerate(section):
        if isinstance(lot, dict) and lot.get("ticker") == ticker:
            existing_idx = i
            break

    if existing_idx is not None:
        # We hold this already. Add amounts. Average the cost basis if possible.
        old_lot = section[existing_idx]
        old_amount = float(old_lot.get("amount", 0.0))
        old_price = old_lot.get("buy_price_usd")

        new_amount = old_amount + amount

        # Average cost basis
        if old_price is not None and used_price is not None:
            avg_price = ((old_price * old_amount) + (used_price * amount)) / new_amount
        elif used_price is not None:
            # We didn't have a price before, but we do now.
            avg_price = used_price
        else:
            # Still don't know the price
            avg_price = old_price

        section[existing_idx]["amount"] = new_amount
        section[existing_idx]["buy_price_usd"] = avg_price
        # Update date to latest addition
        section[existing_idx]["buy_date"] = datetime.now(timezone.utc).isoformat()
    else:
        # Brand new asset
        new_lot = {
            "ticker": ticker,
            "amount": amount,
            "buy_price_usd": used_price,
            "buy_date": datetime.now(timezone.utc).isoformat(),
        }
        section.append(new_lot)

    # Save back
    await db["Users"].update_one(
        {"_id": user_id},
        {"$set": {f"portfolio.{asset_type}": section}},
        upsert=True,
    )
    return used_price


async def remove_asset(user_id: int, ticker: str) -> bool:
    """
    Remove an asset completely from the user's portfolio.
    Returns True if removed, False if not found.
    """
    await _ensure_migrated(user_id)
    db = get_db()

    ticker = ticker.upper()
    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})
    if not isinstance(portfolio, dict):
        return False

    removed = False
    updates = {}
    for asset_type in ("crypto", "stock", "fiat"):
        section = portfolio.get(asset_type, [])
        if not isinstance(section, list):
            continue

        new_section = [lot for lot in section if isinstance(lot, dict) and lot.get("ticker") != ticker]
        if len(new_section) != len(section):
            removed = True
            updates[f"portfolio.{asset_type}"] = new_section

    if updates:
        await db["Users"].update_one({"_id": user_id}, {"$set": updates})

    return removed


async def clear_portfolio(user_id: int) -> None:
    """Delete all portfolio data for a user."""
    db = get_db()
    await db["Users"].update_one(
        {"_id": user_id},
        {"$unset": {"portfolio": "", "stocks": ""}},
    )


# ── Exchange Sync (Binance) ────────────────────────────────────────


async def sync_exchange_balances(user_id: int, balances: list[dict[str, Any]]) -> int:
    """
    Sync balances from an exchange. This overwrites the 'crypto' section
    for tickers that exist in the balances list. Tickers not in the list remain.
    Optionally, we can fetch their current prices to act as 'buy_price_usd'
    if we don't have one, but typically exchange sync just tracks balances.
    """
    await _ensure_migrated(user_id)
    db = get_db()

    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})
    crypto_section = portfolio.get("crypto", []) if isinstance(portfolio, dict) else []
    if not isinstance(crypto_section, list):
        crypto_section = []

    # Map current crypto by ticker
    crypto_map = {}
    for lot in crypto_section:
        if isinstance(lot, dict) and "ticker" in lot:
            crypto_map[lot["ticker"]] = lot

    # Update with exchange balances
    updated_count = 0
    all_tickers = [b["asset"] for b in balances]

    # Pre-fetch prices for new assets
    prices_map = {}
    if all_tickers:
        cursor = db["current_prices"].find(
            {"_id": {"$in": all_tickers}},
            {"price_usd": 1},
        )
        async for doc in cursor:
            prices_map[doc["_id"]] = float(doc.get("price_usd", 0))

    for bal in balances:
        ticker = bal["asset"]
        amount = bal["free"] + bal["locked"]
        if amount <= 0:
            continue

        if ticker in crypto_map:
            crypto_map[ticker]["amount"] = amount
        else:
            crypto_map[ticker] = {
                "ticker": ticker,
                "amount": amount,
                "buy_price_usd": prices_map.get(ticker),  # snapshot current price as basis
                "buy_date": datetime.now(timezone.utc).isoformat(),
            }
        updated_count += 1

    new_crypto_section = list(crypto_map.values())
    await db["Users"].update_one(
        {"_id": user_id},
        {"$set": {"portfolio.crypto": new_crypto_section}},
        upsert=True,
    )

    # Update current_prices with the exchange prices too if provided
    # The balances dict might not contain price, this is handled via main parser.
    return updated_count


async def update_prices_from_exchange(prices: dict[str, float]) -> int:
    """Update current_prices collection with live prices from an exchange."""
    db = get_db()
    ops = []
    for ticker, price in prices.items():
        if price > 0:
            ops.append(
                UpdateOne(
                    {"_id": ticker},
                    {"$set": {"price_usd": price, "updated_at": datetime.now(timezone.utc)}},
                    upsert=True,
                )
            )

    if ops:
        result = await db["current_prices"].bulk_write(ops)
        log.info(
            "Updated current_prices: %d upserted, %d modified",
            result.upserted_count,
            result.modified_count,
        )
    else:
        log.warning("No prices to update in current_prices")

    return len(ops)


# ── P&L Aggregation Pipeline ──────────────────────────────────────


async def get_portfolio_with_pnl(
    user_id: int,
    base_currency: str = "USD",
) -> dict[str, Any]:
    """
    Compute P&L for all portfolio positions using MongoDB aggregation.
    Formats the data exactly as required by portfolio.py.
    """
    await _ensure_migrated(user_id)
    db = get_db()

    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})

    if not portfolio:
        return _empty_result(base_currency)

    # Get USD -> base_currency rate
    usd_to_base = await _get_usd_to_base_rate(base_currency)

    # Find the base currency symbol
    curr_data = get_currencies_data()
    base_sym = next(
        (c.get("symbol", base_currency) for c in curr_data if c.get("code") == base_currency), base_currency
    )

    # Build result using aggregation-style lookup
    all_tickers: set[str] = set()
    for section in ("crypto", "stock", "fiat"):
        lots = portfolio.get(section, [])
        if isinstance(lots, list):
            for lot in lots:
                if isinstance(lot, dict) and "ticker" in lot:
                    all_tickers.add(lot["ticker"])

    # Batch fetch current prices
    prices_map: dict[str, float] = {}
    if all_tickers:
        cursor = db["current_prices"].find(
            {"_id": {"$in": list(all_tickers)}},
            {"price_usd": 1},
        )
        async for doc in cursor:
            prices_map[doc["_id"]] = float(doc.get("price_usd", 0))

    # For fiat tickers, try to get from fiat_rates if not in current_prices
    for section in ("fiat",):
        lots = portfolio.get(section, [])
        if isinstance(lots, list):
            for lot in lots:
                if isinstance(lot, dict):
                    ticker = lot.get("ticker", "")
                    if ticker and ticker not in prices_map:
                        fiat_price = await _get_fiat_usd_price(ticker)
                        if fiat_price is not None:
                            prices_map[ticker] = fiat_price

    # Compute P&L
    sections_result: dict[str, list] = {}
    total_value_usd = 0.0
    total_cost_usd = 0.0

    for section in ("crypto", "stock", "fiat"):
        lots = portfolio.get(section, [])
        if not isinstance(lots, list):
            continue

        section_lots = []
        for lot in lots:
            if not isinstance(lot, dict):
                continue

            ticker = lot.get("ticker", "")
            amount = float(lot.get("amount", 0))
            buy_price = lot.get("buy_price_usd")
            current_price = prices_map.get(ticker)

            value_usd = (current_price or 0) * amount
            cost_usd = (buy_price or 0) * amount if buy_price else None

            pnl_abs = None
            pnl_pct = None
            if buy_price and current_price:
                pnl_abs = (current_price - buy_price) * amount
                pnl_pct = ((current_price - buy_price) / buy_price) * 100

            total_value_usd += value_usd
            if cost_usd is not None:
                total_cost_usd += cost_usd

            pnl_abs_base = (pnl_abs * usd_to_base) if pnl_abs is not None else None

            section_lots.append(
                {
                    "symbol": ticker,
                    "asset_type": section,
                    "amount": amount,
                    "current_val_base": value_usd * usd_to_base,
                    "pnl_abs_base": pnl_abs_base,
                    "pnl_pct": pnl_pct,
                }
            )

        if section_lots:
            sections_result[section] = section_lots

    total_pnl_abs = total_value_usd - total_cost_usd if total_cost_usd > 0 else None
    total_pnl_pct = (total_pnl_abs / total_cost_usd * 100) if (total_cost_usd and total_pnl_abs is not None) else None

    # Format sections as a list for the handler
    sections_list = []
    for sec_name in ("crypto", "stock", "fiat"):
        if sec_name in sections_result:
            lots = sections_result[sec_name]
            sec_val_base = sum(
                (lot["current_val_base"] for lot in lots if lot.get("current_val_base") is not None), 0.0
            )
            sections_list.append(
                {
                    "type": sec_name,
                    "count": len(lots),
                    "items": lots,
                    "total_val_base": sec_val_base,
                }
            )

    grand_total_base = total_value_usd * usd_to_base
    grand_pnl_abs_base = (total_pnl_abs * usd_to_base) if total_pnl_abs is not None else None

    return {
        "sections": sections_list,
        "base_currency": base_currency,
        "base_symbol": base_sym,
        "grand_total_base": grand_total_base,
        "grand_pnl_abs_base": grand_pnl_abs_base,
        "grand_pnl_pct": total_pnl_pct,
    }


def _empty_result(base_currency: str) -> dict[str, Any]:
    curr_data = get_currencies_data()
    base_sym = next(
        (c.get("symbol", base_currency) for c in curr_data if c.get("code") == base_currency), base_currency
    )
    return {
        "sections": [],
        "base_currency": base_currency,
        "base_symbol": base_sym,
        "grand_total_base": 0.0,
        "grand_pnl_abs_base": None,
        "grand_pnl_pct": None,
    }


async def _get_usd_to_base_rate(base_currency: str) -> float:
    """Get conversion rate from USD to the target base currency."""
    if base_currency == "USD":
        return 1.0

    db = get_db()

    # Try USD -> base_currency
    fiat_doc = await db[get_fiat_collection_name()].find_one({"currency": "USD"})
    if fiat_doc and "rates" in fiat_doc:
        rate_obj = fiat_doc["rates"].get(base_currency)
        if isinstance(rate_obj, dict) and "rate" in rate_obj:
            return float(rate_obj["rate"])
        elif isinstance(rate_obj, (int, float)):
            return float(rate_obj)

    # Fallback: cross rate
    base_doc = await db[get_fiat_collection_name()].find_one({"currency": base_currency})
    if base_doc and "rates" in base_doc:
        usd_rate_obj = base_doc["rates"].get("USD")
        if isinstance(usd_rate_obj, dict) and "rate" in usd_rate_obj:
            if float(usd_rate_obj["rate"]) > 0:
                return 1.0 / float(usd_rate_obj["rate"])
        elif isinstance(usd_rate_obj, (int, float)):
            if float(usd_rate_obj) > 0:
                return 1.0 / float(usd_rate_obj)

    return 1.0


async def _get_fiat_usd_price(fiat_currency: str) -> float | None:
    """Get the price of 1 unit of fiat_currency in USD."""
    fiat_currency = fiat_currency.upper()
    if fiat_currency == "USD":
        return 1.0

    db = get_db()

    # We want fiat_currency -> USD
    doc = await db[get_fiat_collection_name()].find_one({"currency": fiat_currency})
    if doc and "rates" in doc:
        rate_obj = doc["rates"].get("USD")
        if isinstance(rate_obj, dict) and "rate" in rate_obj:
            return float(rate_obj["rate"])
        elif isinstance(rate_obj, (int, float)):
            return float(rate_obj)

    # Reverse
    usd_doc = await db[get_fiat_collection_name()].find_one({"currency": "USD"})
    if usd_doc and "rates" in usd_doc:
        rate_obj = usd_doc["rates"].get(fiat_currency)
        if isinstance(rate_obj, dict) and "rate" in rate_obj:
            if float(rate_obj["rate"]) > 0:
                return 1.0 / float(rate_obj["rate"])
        elif isinstance(rate_obj, (int, float)):
            if float(rate_obj) > 0:
                return 1.0 / float(rate_obj)

    return None


async def _get_current_usd_price(ticker: str) -> float | None:
    """Get the current USD price of a crypto/stock asset."""
    db = get_db()
    doc = await db["current_prices"].find_one({"_id": ticker.upper()})
    if doc and "price_usd" in doc:
        return float(doc["price_usd"])
    return None
