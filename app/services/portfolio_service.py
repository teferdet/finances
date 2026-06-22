"""
Portfolio service — manages cost-basis lots and computes P&L.

Responsibilities:
1. Lazy migration of legacy {ticker: amount} → lot-array format
2. CRUD for portfolio lots (add / remove / clear)
3. Maintaining a flat `current_prices` collection for aggregation
4. MongoDB Aggregation Pipeline that computes P&L server-side
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db
from app.logger import get_logger

log = get_logger("portfolio.service")


# ── Lazy migration ─────────────────────────────────────────────────

async def migrate_user_portfolio(user_id: int) -> bool:
    """
    Migrate legacy portfolio format from dict to lot-array.

    Old: {"crypto": {"BTC": 0.5, "ETH": 2.0}, ...}
    New: {"crypto": [{"ticker":"BTC","amount":0.5,"buy_price_usd":null,"buy_date":null}, ...], ...}

    Returns True if migration was performed, False if already migrated or empty.
    """
    db = get_db()
    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio")

    if not portfolio:
        return False

    needs_migration = False
    for section in ("crypto", "stock", "fiat"):
        data = portfolio.get(section)
        if isinstance(data, dict):
            needs_migration = True
            break

    if not needs_migration:
        return False

    new_portfolio: dict[str, list] = {}
    for section in ("crypto", "stock", "fiat"):
        data = portfolio.get(section)
        if isinstance(data, dict):
            lots = []
            for ticker, amount in data.items():
                if isinstance(amount, (int, float)) and amount > 0:
                    lots.append({
                        "ticker": ticker,
                        "amount": float(amount),
                        "buy_price_usd": None,
                        "buy_date": None,
                    })
            new_portfolio[section] = lots
        elif isinstance(data, list):
            # Already migrated
            new_portfolio[section] = data
        else:
            new_portfolio[section] = []

    await db["Users"].update_one(
        {"_id": user_id},
        {"$set": {"portfolio": new_portfolio}},
    )
    log.info("Migrated portfolio for user %d", user_id)
    return True


async def _ensure_migrated(user_id: int) -> None:
    """Ensure user portfolio is in the new format."""
    await migrate_user_portfolio(user_id)


# ── Add asset ──────────────────────────────────────────────────────

async def add_asset(
    user_id: int,
    asset_type: str,
    ticker: str,
    amount: float,
    buy_price_usd: float | None = None,
) -> float | None:
    """
    Add a lot to the user's portfolio.

    If buy_price_usd is None, the current market price is fetched
    automatically from cached data.

    Returns the buy_price_usd actually used (useful when auto-detected).
    """
    await _ensure_migrated(user_id)
    db = get_db()

    # Auto-detect price if not provided
    auto_price = False
    if buy_price_usd is None:
        buy_price_usd = await _get_current_usd_price(ticker)
        auto_price = True

    lot = {
        "ticker": ticker,
        "amount": amount,
        "buy_price_usd": buy_price_usd,
        "buy_date": datetime.now(timezone.utc),
    }

    await db["Users"].update_one(
        {"_id": user_id},
        {"$push": {f"portfolio.{asset_type}": lot}},
        upsert=True,
    )

    log.info(
        "Added %s %s (@ %s USD) for user %d",
        amount, ticker, buy_price_usd, user_id,
    )
    return buy_price_usd


async def _get_current_usd_price(ticker: str) -> float | None:
    """
    Try to get the current USD price from the current_prices collection,
    falling back to Crypto&Stocks raw data.
    """
    db = get_db()

    # 1. Try flat cache first
    doc = await db["current_prices"].find_one({"_id": ticker})
    if doc and doc.get("price_usd"):
        return float(doc["price_usd"])

    # 2. Fallback: Crypto&Stocks
    cs_doc = await db["Crypto&Stocks"].find_one({"_id": "crypto"}) or {}
    if ticker in cs_doc and isinstance(cs_doc[ticker], list) and len(cs_doc[ticker]) >= 3:
        return float(cs_doc[ticker][1])

    stocks_doc = await db["Crypto&Stocks"].find_one({"_id": "stocks"}) or {}
    if ticker in stocks_doc and isinstance(stocks_doc[ticker], (list, tuple)) and len(stocks_doc[ticker]) >= 4:
        return float(stocks_doc[ticker][2])

    return None


# ── Remove asset ───────────────────────────────────────────────────

async def remove_asset(
    user_id: int,
    ticker: str,
    asset_type: str | None = None,
) -> bool:
    """
    Remove all lots of a given ticker from the portfolio.
    If asset_type is None, searches all sections.
    Returns True if anything was removed.
    """
    await _ensure_migrated(user_id)
    db = get_db()

    if asset_type:
        sections = [asset_type]
    else:
        sections = ["crypto", "stock", "fiat"]

    removed = False
    for section in sections:
        result = await db["Users"].update_one(
            {"_id": user_id},
            {"$pull": {f"portfolio.{section}": {"ticker": ticker}}},
        )
        if result.modified_count > 0:
            removed = True

    return removed


# ── Clear portfolio ────────────────────────────────────────────────

async def clear_portfolio(user_id: int) -> None:
    """Clear entire portfolio for a user."""
    db = get_db()
    await db["Users"].update_one(
        {"_id": user_id},
        {"$unset": {"portfolio": ""}},
    )


# ── Current prices sync ───────────────────────────────────────────

async def update_current_prices() -> int:
    """
    Rebuild the flat `current_prices` collection from Crypto&Stocks data.
    Each document: { _id: "BTC", price_usd: 65000.0, updated_at: ... }

    Returns count of prices updated.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    ops = []

    # Crypto (prices in the USD entry, or top-level keyed by symbol)
    cs_doc = await db["Crypto&Stocks"].find_one({"_id": "crypto"}) or {}
    # The crypto doc stores data per convert_currency. The USD entries have raw prices.
    # Structure: { "BTC": ["BTC", 65000.1234, "$"], ... } at top level (for default currency)
    # Or per-currency: { "USD": { "BTC": ["BTC", 65000, "$"] } }
    # Based on crypto_parser.py, the doc has {currency: {symbol: [name, price, symbol_char]}}
    # But it also stores at top level when saved with _id. Let's handle both.

    # Check for per-currency structure (e.g., cs_doc["USD"]["BTC"])
    usd_data = cs_doc.get("USD", {})
    if isinstance(usd_data, dict) and usd_data:
        for symbol, data in usd_data.items():
            if isinstance(data, list) and len(data) >= 3 and symbol != "_id":
                ops.append({
                    "_id": symbol,
                    "price_usd": float(data[1]),
                    "updated_at": now,
                    "source": "crypto",
                })
    else:
        # Top-level structure
        for symbol, data in cs_doc.items():
            if isinstance(data, list) and len(data) >= 3 and symbol not in ("_id", "update"):
                ops.append({
                    "_id": symbol,
                    "price_usd": float(data[1]),
                    "updated_at": now,
                    "source": "crypto",
                })

    # Stocks
    stocks_doc = await db["Crypto&Stocks"].find_one({"_id": "stocks"}) or {}
    for symbol, data in stocks_doc.items():
        if isinstance(data, (list, tuple)) and len(data) >= 4 and symbol not in ("_id", "update"):
            ops.append({
                "_id": symbol,
                "price_usd": float(data[2]),
                "updated_at": now,
                "source": "stock",
            })

    # Bulk upsert
    if ops:
        from pymongo import ReplaceOne
        bulk = [
            ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
            for doc in ops
        ]
        result = await db["current_prices"].bulk_write(bulk, ordered=False)
        log.info(
            "Updated current_prices: %d upserted, %d modified",
            result.upserted_count, result.modified_count,
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

    Returns:
    {
        "sections": {
            "crypto": [
                {
                    "ticker": "BTC", "amount": 0.5,
                    "buy_price_usd": 60000, "buy_date": ...,
                    "current_price_usd": 65000,
                    "value_usd": 32500,
                    "cost_usd": 30000,
                    "pnl_abs_usd": 2500,
                    "pnl_pct": 8.33,
                },
                ...
            ],
            "stock": [...],
            "fiat": [...],
        },
        "total_value_usd": 100000,
        "total_cost_usd": 90000,
        "total_pnl_abs_usd": 10000,
        "total_pnl_pct": 11.11,
        "base_currency": "USD",
        "usd_to_base_rate": 1.0,
    }
    """
    await _ensure_migrated(user_id)
    db = get_db()

    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})

    if not portfolio:
        return _empty_result(base_currency)

    # Get USD → base_currency rate
    usd_to_base = await _get_usd_to_base_rate(base_currency)

    # Build result using aggregation-style lookup
    # We do a client-side join because the portfolio is embedded in Users,
    # not in a separate collection, so $lookup doesn't apply directly.
    # Instead, we batch-fetch all needed prices from current_prices.

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
            buy_date = lot.get("buy_date")
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

            section_lots.append({
                "ticker": ticker,
                "amount": amount,
                "buy_price_usd": buy_price,
                "buy_date": buy_date,
                "current_price_usd": current_price,
                "value_usd": value_usd,
                "cost_usd": cost_usd,
                "pnl_abs_usd": pnl_abs,
                "pnl_pct": pnl_pct,
            })

        if section_lots:
            sections_result[section] = section_lots

    total_pnl_abs = total_value_usd - total_cost_usd if total_cost_usd > 0 else None
    total_pnl_pct = (total_pnl_abs / total_cost_usd * 100) if (total_cost_usd and total_pnl_abs is not None) else None

    return {
        "sections": sections_result,
        "total_value_usd": total_value_usd,
        "total_cost_usd": total_cost_usd if total_cost_usd > 0 else None,
        "total_pnl_abs_usd": total_pnl_abs,
        "total_pnl_pct": total_pnl_pct,
        "base_currency": base_currency,
        "usd_to_base_rate": usd_to_base,
    }


def _empty_result(base_currency: str) -> dict[str, Any]:
    return {
        "sections": {},
        "total_value_usd": 0,
        "total_cost_usd": None,
        "total_pnl_abs_usd": None,
        "total_pnl_pct": None,
        "base_currency": base_currency,
        "usd_to_base_rate": 1.0,
    }


async def _get_usd_to_base_rate(base_currency: str) -> float:
    """Get conversion rate from USD to the target base currency."""
    if base_currency == "USD":
        return 1.0

    db = get_db()

    # Try USD → base_currency
    fiat_doc = await db["fiat_rates"].find_one({"currency": "USD"})
    if fiat_doc and "rates" in fiat_doc:
        rate_info = fiat_doc["rates"].get(base_currency)
        if rate_info:
            try:
                return float(rate_info.get("rate", 1.0))
            except (ValueError, TypeError):
                pass

    # Try inverse: base_currency → USD
    fiat_doc2 = await db["fiat_rates"].find_one({"currency": base_currency})
    if fiat_doc2 and "rates" in fiat_doc2:
        usd_info = fiat_doc2["rates"].get("USD")
        if usd_info:
            try:
                return 1.0 / float(usd_info.get("rate", 1.0))
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    return 1.0


async def _get_fiat_usd_price(currency_code: str) -> float | None:
    """Get the USD value of 1 unit of a fiat currency."""
    db = get_db()

    # Try: USD rates doc, look for currency_code
    fiat_doc = await db["fiat_rates"].find_one({"currency": "USD"})
    if fiat_doc and "rates" in fiat_doc:
        rate_info = fiat_doc["rates"].get(currency_code)
        if rate_info:
            try:
                rate = float(rate_info.get("rate", 0))
                if rate > 0:
                    return 1.0 / rate  # 1 unit of currency_code in USD
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    # Try inverse: currency_code rates doc, look for USD
    fiat_doc2 = await db["fiat_rates"].find_one({"currency": currency_code})
    if fiat_doc2 and "rates" in fiat_doc2:
        usd_info = fiat_doc2["rates"].get("USD")
        if usd_info:
            try:
                rate = float(usd_info.get("rate", 0))
                if rate > 0:
                    return rate  # 1 unit of currency_code = rate USD
            except (ValueError, TypeError):
                pass

    return None
