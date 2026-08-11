"""
Alert service — background workers for price alert checking and volatility monitoring.

Runs as asyncio background tasks started from __main__.py.

Responsibilities:
1. Check untriggered price alerts against current market data (every 60s)
2. Track price history and detect volatile moves (hourly comparison)
3. Send notifications with batched message delivery (25 msg/sec max)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot

from app.db import get_db, get_fiat_collection_name
from app.i18n import get_i18n
from app.logger import get_logger

log = get_logger("alert.service")

# ── Module-level bot reference (set from __main__) ─────────────────
_bot: Optional[Bot] = None


def set_bot(bot: Bot) -> None:
    """Set the bot instance for sending notifications."""
    global _bot
    _bot = bot


def get_bot() -> Optional[Bot]:
    return _bot


# ── i18n + user language helpers ───────────────────────────────────


async def _get_user_lang(user_id: int) -> str:
    """Fetch user's language from DB, fallback to 'en'."""
    db = get_db()
    doc = await db["Users"].find_one({"_id": user_id}, {"Language": 1})
    if doc and doc.get("Language"):
        return doc["Language"]
    return "en"


async def _get_users_langs(user_ids: list[int]) -> dict[int, str]:
    """Batch-fetch languages for multiple users."""
    db = get_db()
    cursor = db["Users"].find({"_id": {"$in": user_ids}}, {"Language": 1})
    result: dict[int, str] = {}
    async for doc in cursor:
        result[doc["_id"]] = doc.get("Language") or "en"
    # Fill missing with default
    for uid in user_ids:
        if uid not in result:
            result[uid] = "en"
    return result


# ── Batched message sender ─────────────────────────────────────────


async def _send_batched(
    messages: list[tuple[int, str]],
    batch_size: int = 25,
) -> tuple[int, int]:
    """
    Send messages in batches to avoid Telegram FloodWait.

    Args:
        messages: list of (user_id, text) tuples
        batch_size: max messages per second (Telegram limit ~30/sec)

    Returns:
        (sent_count, failed_count)
    """
    bot = get_bot()
    if not bot:
        log.error("Bot not set — cannot send notifications")
        return 0, len(messages)

    sent = 0
    failed = 0

    for i in range(0, len(messages), batch_size):
        chunk = messages[i : i + batch_size]
        for user_id, text in chunk:
            try:
                await bot.send_message(user_id, text, parse_mode="HTML")
                sent += 1
            except Exception as exc:
                log.debug("Failed to send to %d: %s", user_id, exc)
                failed += 1

        # Wait 1 second between batches to respect Telegram rate limits
        if i + batch_size < len(messages):
            await asyncio.sleep(1.0)

    return sent, failed


# ── Price fetching helpers ─────────────────────────────────────────


async def _get_pair_price(currency_from: str, currency_to: str) -> Optional[float]:
    """
    Get the exchange rate for a currency pair.
    Supports crypto, stocks (via current_prices), and fiat (via fiat_rates).
    """
    db = get_db()

    # Case 1: Both are in current_prices (crypto/stocks quoted in USD)
    if currency_to == "USD":
        doc = await db["current_prices"].find_one({"_id": currency_from})
        if doc and doc.get("price_usd"):
            return float(doc["price_usd"])

    # Case 2: currency_from is in current_prices, currency_to is fiat
    from_doc = await db["current_prices"].find_one({"_id": currency_from})
    if from_doc and from_doc.get("price_usd"):
        from_usd = float(from_doc["price_usd"])
        if currency_to == "USD":
            return from_usd
        # Convert USD → currency_to
        to_rate = await _get_fiat_rate("USD", currency_to)
        if to_rate:
            return from_usd * to_rate

    # Case 3: Fiat pair
    rate = await _get_fiat_rate(currency_from, currency_to)
    if rate:
        return rate

    return None


async def _get_fiat_rate(base: str, target: str) -> Optional[float]:
    """Get fiat exchange rate from fiat_rates collection."""
    db = get_db()
    doc = await db[get_fiat_collection_name()].find_one({"currency": base}, {"rates": 1})
    if doc and "rates" in doc:
        rate_info = doc["rates"].get(target)
        if rate_info:
            try:
                return float(rate_info.get("rate", 0))
            except (ValueError, TypeError):
                pass
    return None


# ── Alert Checker Loop ─────────────────────────────────────────────


async def run_alert_checker(check_interval: int = 60) -> None:
    """
    Background loop that checks price alerts every `check_interval` seconds.
    """
    log.info("Alert checker starting (interval=%ds)...", check_interval)

    # Wait for initial startup to complete
    await asyncio.sleep(10)

    while True:
        try:
            triggered = await _check_alerts()
            if triggered:
                log.info("Triggered %d alert(s)", triggered)
        except asyncio.CancelledError:
            log.info("Alert checker cancelled — shutting down")
            break
        except Exception as exc:
            log.error("Alert checker error: %s", exc)

        await asyncio.sleep(check_interval)


async def _check_alerts() -> int:
    """
    Check all untriggered alerts against current prices.
    Returns number of triggered alerts.
    """
    db = get_db()
    i18n = get_i18n()

    # Fetch all untriggered alerts
    alerts = await db["Alerts"].find({"triggered": False}).to_list(length=1000)
    if not alerts:
        return 0

    # Group by pair for batch price lookup
    pairs: set[tuple[str, str]] = set()
    for a in alerts:
        pairs.add((a["currency_from"], a["currency_to"]))

    # Fetch prices for all pairs
    prices: dict[tuple[str, str], float] = {}
    for cf, ct in pairs:
        price = await _get_pair_price(cf, ct)
        if price is not None:
            prices[(cf, ct)] = price

    # Batch-fetch user languages for all alert owners
    user_ids = list({a["user_id"] for a in alerts})
    user_langs = await _get_users_langs(user_ids)

    # Check conditions
    notifications: list[tuple[int, str]] = []
    triggered_ids = []
    now = datetime.now(timezone.utc)

    for a in alerts:
        pair = (a["currency_from"], a["currency_to"])
        current = prices.get(pair)
        if current is None:
            continue

        target = a["target_price"]
        condition = a["condition"]
        triggered = False

        if condition == "above" and current >= target:
            triggered = True
        elif condition == "below" and current <= target:
            triggered = True

        if triggered:
            triggered_ids.append(a["_id"])

            # Build notification via i18n
            lang = user_langs.get(a["user_id"], "en")

            def t(k):
                return str(i18n.get(f"alerts.{k}", lang))

            cond_emoji = "📈" if condition == "above" else "📉"
            text = (
                t("notification_body")
                .replace("{pair}", f"{a['currency_from']}/{a['currency_to']}")
                .replace("{target_label}", t("notification_target"))
                .replace("{target_price}", str(target))
                .replace("{current_label}", t("notification_current"))
                .replace("{current_price}", f"{current:.6g}")
                .replace("{cond_emoji}", cond_emoji)
                .replace("{condition_label}", t("notification_condition_met"))
                .replace("{condition}", t(condition))
                .replace("{time}", now.strftime("%Y-%m-%d %H:%M UTC"))
            )
            notifications.append((a["user_id"], text))

    # Mark as triggered in DB
    if triggered_ids:
        await db["Alerts"].update_many(
            {"_id": {"$in": triggered_ids}},
            {"$set": {"triggered": True, "triggered_at": now}},
        )

    # Send notifications (batched)
    if notifications:
        sent, failed = await _send_batched(notifications)
        log.info("Alert notifications: %d sent, %d failed", sent, failed)

    return len(triggered_ids)


# ── Price History & Volatility Monitor ─────────────────────────────


async def save_price_snapshot() -> None:
    """
    Save current prices to price_history collection for volatility tracking.
    Called after each price fetch cycle in parser_service.
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    # Only save once per hour (check last snapshot time)
    last_snap = await db["price_history"].find_one(
        sort=[("timestamp", -1)],
    )
    if last_snap:
        last_ts = last_snap.get("timestamp")
        if last_ts and last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        if last_ts and (now - last_ts) < timedelta(minutes=50):
            return  # Skip — too recent

    # Fetch all current prices
    cursor = db["current_prices"].find({}, {"price_usd": 1})
    prices = {}
    async for doc in cursor:
        prices[doc["_id"]] = float(doc.get("price_usd", 0))

    if not prices:
        return

    snapshot = {
        "timestamp": now,
        "prices": prices,
    }
    await db["price_history"].insert_one(snapshot)
    log.debug("Price snapshot saved: %d tickers", len(prices))

    # Cleanup old snapshots (keep 7 days)
    cutoff = now - timedelta(days=7)
    result = await db["price_history"].delete_many({"timestamp": {"$lt": cutoff}})
    if result.deleted_count > 0:
        log.debug("Cleaned up %d old price snapshots", result.deleted_count)


async def run_volatility_monitor(check_interval: int = 300) -> None:
    """
    Background loop that checks for volatile price moves every 5 minutes.
    Compares current prices with 1-hour-ago snapshot.
    """
    log.info("Volatility monitor starting (interval=%ds)...", check_interval)

    # Wait for initial startup
    await asyncio.sleep(30)

    while True:
        try:
            await _check_volatility()
        except asyncio.CancelledError:
            log.info("Volatility monitor cancelled — shutting down")
            break
        except Exception as exc:
            log.error("Volatility monitor error: %s", exc)

        await asyncio.sleep(check_interval)


async def _check_volatility() -> None:
    """
    Compare current prices with 1-hour-ago snapshot.
    Notify users whose holdings have volatile tickers.
    """
    db = get_db()
    i18n = get_i18n()
    now = datetime.now(timezone.utc)

    # Get snapshot from ~1 hour ago
    target_time = now - timedelta(hours=1)
    old_snap = await db["price_history"].find_one(
        {"timestamp": {"$lte": target_time}},
        sort=[("timestamp", -1)],
    )
    if not old_snap:
        return  # No historical data yet

    old_prices = old_snap.get("prices", {})
    if not old_prices:
        return

    # Get current prices
    cursor = db["current_prices"].find({}, {"price_usd": 1})
    current_prices: dict[str, float] = {}
    async for doc in cursor:
        current_prices[doc["_id"]] = float(doc.get("price_usd", 0))

    # Find volatile tickers
    volatile_tickers: dict[str, dict] = {}  # ticker -> {old, new, pct_change}
    for ticker, old_price in old_prices.items():
        if old_price <= 0:
            continue
        new_price = current_prices.get(ticker)
        if new_price is None or new_price <= 0:
            continue

        pct_change = ((new_price - old_price) / old_price) * 100
        if abs(pct_change) >= 3.0:  # Pre-filter: only check users if >= 3%
            volatile_tickers[ticker] = {
                "old": old_price,
                "new": new_price,
                "pct": pct_change,
            }

    if not volatile_tickers:
        return

    log.info("Volatile tickers detected: %s", list(volatile_tickers.keys()))

    # Find users who hold these tickers
    ticker_list = list(volatile_tickers.keys())

    users = (
        await db["Users"]
        .find(
            {
                "$or": [
                    {"portfolio.crypto.ticker": {"$in": ticker_list}},
                    {"portfolio.stock.ticker": {"$in": ticker_list}},
                ]
            },
            {"_id": 1, "portfolio": 1, "volatility_threshold_pct": 1, "VolatilityThreshold": 1, "Language": 1},
        )
        .to_list(length=5000)
    )

    if not users:
        return

    # Build per-user notifications
    notifications: list[tuple[int, str]] = []

    for user in users:
        v_thresh = user.get("VolatilityThreshold")
        if v_thresh is None:
            v_thresh = user.get("volatility_threshold_pct", 5.0)
        threshold = float(v_thresh)
        if threshold <= 0:
            continue  # User disabled volatility notifications
        lang = user.get("Language") or "en"

        def t(k, _lang=lang):
            return str(i18n.get(f"alerts.{k}", _lang))

        user_tickers: list[str] = []

        # Collect user's tickers
        portfolio = user.get("portfolio", {})
        for section in ("crypto", "stock"):
            lots = portfolio.get(section, [])
            if isinstance(lots, list):
                for lot in lots:
                    if isinstance(lot, dict):
                        tk = lot.get("ticker", "")
                        if tk in volatile_tickers:
                            user_tickers.append(tk)

        if not user_tickers:
            continue

        # Filter by user's threshold
        lines = []
        for ticker in set(user_tickers):
            data = volatile_tickers[ticker]
            if abs(data["pct"]) >= threshold:
                emoji = "📈" if data["pct"] > 0 else "📉"
                lines.append(
                    f"• <b>{ticker}</b>: ${data['old']:.2f} → ${data['new']:.2f} ({data['pct']:+.1f}%) {emoji}"
                )

        if not lines:
            continue

        text = (
            t("volatility_title")
            + "\n\n"
            + t("volatility_message")
            + "\n\n"
            + "\n".join(lines)
            + "\n\n"
            + t("volatility_threshold_info").replace("{pct}", str(threshold))
        )
        notifications.append((user["_id"], text))

    if notifications:
        sent, failed = await _send_batched(notifications)
        log.info(
            "Volatility notifications: %d sent, %d failed (volatile: %s)",
            sent,
            failed,
            list(volatile_tickers.keys()),
        )
