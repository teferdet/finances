"""
Digest service — weekly portfolio digest for all users.

Runs as asyncio background task started from __main__.py.
Sends a weekly summary of portfolio performance to each user.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.db import get_db
from app.logger import get_logger
from app.services.alert_service import _send_batched

log = get_logger("digest.service")

# ── Weekly Digest Scheduler ────────────────────────────────────────

DIGEST_DAY = 6   # Sunday (0=Monday, 6=Sunday)
DIGEST_HOUR = 10  # 10:00 UTC


async def run_digest_scheduler() -> None:
    """
    Background loop that sends weekly portfolio digests.
    Runs every hour, checks if it's time to send the digest.
    """
    log.info("Digest scheduler starting (day=%d, hour=%d UTC)...", DIGEST_DAY, DIGEST_HOUR)

    # Wait for initial startup
    await asyncio.sleep(60)

    while True:
        try:
            now = datetime.now(timezone.utc)

            # Check if it's the right day and hour
            if now.weekday() == DIGEST_DAY and now.hour == DIGEST_HOUR:
                # Check if we already sent today
                if not await _already_sent_today():
                    log.info("Sending weekly digest...")
                    await _send_weekly_digest()
                    await _mark_digest_sent()

        except asyncio.CancelledError:
            log.info("Digest scheduler cancelled — shutting down")
            break
        except Exception as exc:
            log.error("Digest scheduler error: %s", exc)

        # Check every 30 minutes
        await asyncio.sleep(1800)


async def _already_sent_today() -> bool:
    """Check if the weekly digest was already sent today."""
    db = get_db()
    doc = await db["Status"].find_one(
        {"_id": "digest_status"}, {"last_digest_sent": 1}
    )
    if not doc or "last_digest_sent" not in doc:
        return False

    last_sent = doc["last_digest_sent"]
    if isinstance(last_sent, (int, float)):
        from datetime import datetime as dt
        last_dt = dt.fromtimestamp(last_sent, tz=timezone.utc)
    else:
        last_dt = last_sent
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return (now - last_dt) < timedelta(hours=20)


async def _mark_digest_sent() -> None:
    """Record that the digest was sent."""
    db = get_db()
    await db["Status"].update_one(
        {"_id": "digest_status"},
        {"$set": {"last_digest_sent": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def _send_weekly_digest() -> None:
    """
    Build and send weekly portfolio digest to all users who have a portfolio.
    """
    db = get_db()

    # Find users with portfolios
    users = await db["Users"].find(
        {"portfolio": {"$exists": True, "$ne": {}}},
        {"_id": 1, "portfolio": 1, "BaseCurrency": 1, "Name": 1},
    ).to_list(length=10000)

    if not users:
        log.info("No users with portfolios — skipping digest")
        return

    log.info("Building digest for %d users...", len(users))

    # Fetch current prices
    current_prices: dict[str, float] = {}
    cursor = db["current_prices"].find({}, {"price_usd": 1})
    async for doc in cursor:
        current_prices[doc["_id"]] = float(doc.get("price_usd", 0))

    # Get 7-day-ago snapshot for comparison
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    old_snap = await db["price_history"].find_one(
        {"timestamp": {"$lte": week_ago}},
        sort=[("timestamp", -1)],
    )
    old_prices = old_snap.get("prices", {}) if old_snap else {}

    # Build per-user digest
    notifications: list[tuple[int, str]] = []

    for user in users:
        text = _build_user_digest(
            user, current_prices, old_prices
        )
        if text:
            notifications.append((user["_id"], text))

    if notifications:
        sent, failed = await _send_batched(notifications)
        log.info("Weekly digest: %d sent, %d failed", sent, failed)
    else:
        log.info("No digest messages to send (all portfolios empty)")


def _build_user_digest(
    user: dict,
    current_prices: dict[str, float],
    old_prices: dict[str, float],
) -> Optional[str]:
    """Build a digest message for a single user."""
    portfolio = user.get("portfolio", {})
    name = user.get("Name", "User")

    holdings: list[dict] = []
    total_value = 0.0
    total_old_value = 0.0
    has_old_data = bool(old_prices)

    for section in ("crypto", "stock", "fiat"):
        lots = portfolio.get(section, [])
        if not isinstance(lots, list):
            continue
        for lot in lots:
            if not isinstance(lot, dict):
                continue
            ticker = lot.get("ticker", "")
            amount = float(lot.get("amount", 0))
            if not ticker or amount <= 0:
                continue

            cur_price = current_prices.get(ticker, 0)
            old_price = old_prices.get(ticker, 0)

            value = cur_price * amount
            old_value = old_price * amount if old_price else 0

            total_value += value
            total_old_value += old_value

            pct = 0.0
            if old_price and cur_price:
                pct = ((cur_price - old_price) / old_price) * 100

            holdings.append({
                "ticker": ticker,
                "amount": amount,
                "value": value,
                "pct": pct,
                "has_history": old_price > 0,
            })

    if not holdings:
        return None

    # Sort by value descending
    holdings.sort(key=lambda x: x["value"], reverse=True)

    lines = [
        "📊 <b>Weekly Portfolio Digest</b>",
        f"Hello, {name}! Here's your weekly summary:\n",
    ]

    # Top holdings
    lines.append("<b>Your Holdings:</b>")
    for h in holdings[:8]:
        emoji = "📈" if h["pct"] > 0 else ("📉" if h["pct"] < 0 else "➖")
        pct_str = f" ({h['pct']:+.1f}%)" if h["has_history"] else ""
        lines.append(
            f"• <b>{h['ticker']}</b>: ${h['value']:,.2f}{pct_str} {emoji}"
        )

    # Total
    lines.append(f"\n💰 <b>Total Value: ${total_value:,.2f}</b>")

    if has_old_data and total_old_value > 0:
        total_pct = ((total_value - total_old_value) / total_old_value) * 100
        change_emoji = "📈" if total_pct > 0 else ("📉" if total_pct < 0 else "➖")
        lines.append(f"📊 Weekly Change: {total_pct:+.1f}% {change_emoji}")
    elif not has_old_data:
        lines.append("<i>Weekly comparison will be available next week.</i>")

    # Top movers
    movers = [h for h in holdings if h["has_history"] and abs(h["pct"]) > 0]
    if movers:
        movers.sort(key=lambda x: abs(x["pct"]), reverse=True)
        top = movers[0]
        direction = "Gainer" if top["pct"] > 0 else "Decliner"
        lines.append(f"\n🏆 Top {direction}: <b>{top['ticker']}</b> ({top['pct']:+.1f}%)")

    lines.append(f"\n<i>Next digest: next Sunday at {DIGEST_HOUR}:00 UTC</i>")

    return "\n".join(lines)
