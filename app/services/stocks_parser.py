"""
Stocks parser — fetches stock data via yfinance.
Runs in a thread executor because yfinance is synchronous.
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Dict, Optional

from app.config import get_settings
from app.db import get_db
from app.logger import get_logger

log = get_logger("parser.stocks")


def _fetch_stocks_sync() -> Optional[dict]:
    """Synchronous yfinance fetch (runs in executor)."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        log.error("yfinance not installed")
        return None

    settings = get_settings()
    stocks_list = settings.company_list
    if not stocks_list:
        log.warning("No stocks configured in data.json")
        return None

    stocks_data: dict = {
        "update": [
            datetime.date.today().strftime("%B %d"),
            datetime.datetime.now().strftime("%H:%M"),
        ]
    }

    try:
        # Suppress noisy yfinance internal ERROR logs (e.g. "possibly delisted")
        import logging as _logging
        yf_logger = _logging.getLogger("yfinance")
        prev_level = yf_logger.level
        yf_logger.setLevel(_logging.CRITICAL)

        try:
            tickers_str = " ".join(stocks_list)
            data = yf.download(tickers_str, period="5d", group_by="ticker", threads=True)
        finally:
            yf_logger.setLevel(prev_level)

        is_multi = isinstance(data.columns, pd.MultiIndex)
        failed_tickers: list[str] = []

        for symbol in stocks_list:
            try:
                price = None
                if is_multi:
                    try:
                        ticker_data = data[symbol].dropna(subset=["Close"])
                        if not ticker_data.empty:
                            price = ticker_data["Close"].iloc[-1]
                    except KeyError:
                        failed_tickers.append(symbol)
                        continue
                else:
                    ticker_data = data.dropna(subset=["Close"])
                    if not ticker_data.empty and "Close" in ticker_data:
                        price = ticker_data["Close"].iloc[-1]

                if price is not None and not pd.isna(price):
                    stocks_data[symbol] = (symbol, symbol, float(price), "$")
                else:
                    failed_tickers.append(symbol)
            except Exception:
                failed_tickers.append(symbol)
                continue

        ok_count = len(stocks_data) - 1
        log.info("[Stocks] Fetched %d stocks", ok_count)
        if failed_tickers:
            log.warning("[Stocks] No price data for %d tickers: %s",
                        len(failed_tickers), ", ".join(failed_tickers))
    except Exception as exc:
        log.error("[Stocks] yfinance error: %s", exc)
        return None

    return stocks_data


async def fetch_stocks() -> Optional[dict]:
    """Async wrapper — runs yfinance in thread executor."""
    loop = asyncio.get_event_loop()
    stocks_data = await loop.run_in_executor(None, _fetch_stocks_sync)

    if not stocks_data:
        return None

    # Save to MongoDB
    db = get_db()
    try:
        doc = stocks_data.copy()
        doc["_id"] = "stocks"
        await db["Crypto&Stocks"].replace_one({"_id": "stocks"}, doc, upsert=True)
        log.info("[Stocks] Saved to MongoDB")

        # Sync flat price cache for portfolio P&L
        try:
            from app.services.portfolio_service import update_current_prices
            await update_current_prices()
        except Exception as exc:
            log.warning("[Stocks] Failed to sync current_prices: %s", exc)
    except Exception as exc:
        log.error("[Stocks] Failed to save to DB: %s", exc)

    return stocks_data
