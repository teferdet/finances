"""
Parser orchestrator — runs as asyncio background tasks inside the bot process.

Responsibilities:
1. Initial population of critical currencies on first startup
2. Periodic refresh of critical fiat currencies (1-hour TTL)
3. Periodic refresh of crypto + stocks (3-hour interval)
4. On-demand fetch for non-critical currencies

This replaces the old parser_controller.py + parser_handler.py.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import get_settings, get_currencies_data
from app.db import get_db
from app.cache import cache
from app.logger import get_logger
from app.services.fiat_parser import FiatParser
from app.services.crypto_parser import fetch_crypto
from app.services.stocks_parser import fetch_stocks

log = get_logger("parser.service")


# ── Staleness check ────────────────────────────────────────────────


async def is_currency_stale(code: str, ttl_hours: int = 5) -> bool:
    """Check if a currency's data in MongoDB is older than ttl_hours."""
    db = get_db()
    doc = await db["fiat_rates"].find_one({"currency": code.upper()}, {"updated_at": 1})
    if not doc or "updated_at" not in doc:
        return True
    updated = doc["updated_at"]
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - updated) > timedelta(hours=ttl_hours)


# ── On-demand fetch (called from handlers) ─────────────────────────

_fetch_locks: dict[str, asyncio.Lock] = {}


async def ensure_currency(code: str, force: bool = False) -> bool:
    """
    Ensure fresh data for a currency is available.
    Uses per-currency locks to prevent duplicate fetches.
    """
    code = code.upper()
    if not force and not await is_currency_stale(code):
        return True

    # Per-currency lock to avoid concurrent fetches for same currency
    if code not in _fetch_locks:
        _fetch_locks[code] = asyncio.Lock()

    async with _fetch_locks[code]:
        # Double-check after acquiring lock
        if not force and not await is_currency_stale(code):
            return True

        parser = FiatParser()
        try:
            result = await parser.fetch_rates(code)
            return result
        finally:
            await parser.close()


# ── Query helpers (used by handlers) ───────────────────────────────


async def get_fiat_rate(base: str, target: str) -> Optional[dict]:
    """Get exchange rate dict from MongoDB."""
    base = base.upper()
    target = target.upper()
    # Trigger background fetch if stale (non-blocking)
    asyncio.create_task(_bg_ensure(base))

    db = get_db()
    doc = await db["fiat_rates"].find_one({"currency": base}, {"rates": 1})
    if doc and "rates" in doc:
        return doc["rates"].get(target)
    return None


async def _bg_ensure(code: str) -> None:
    """Background ensure — swallow errors."""
    try:
        await ensure_currency(code)
    except Exception as exc:
        log.debug("Background fetch failed for %s: %s", code, exc)


async def get_currencies_info() -> list[dict]:
    """Get list of all known currencies from MongoDB fiat_rates."""
    # Use cache
    cached = await cache.get("currencies_info")
    if cached:
        return cached

    db = get_db()
    cursor = db["fiat_rates"].find({}, {"currency": 1, "rates": 1})
    docs = await cursor.to_list(length=500)

    metadata: dict[str, dict] = {}
    base_set: set[str] = set()

    for doc in docs:
        base_set.add(doc.get("currency", ""))
        for code, data in doc.get("rates", {}).items():
            if code not in metadata:
                metadata[code] = {
                    "name": data.get("name", code),
                    "emoji": data.get("emoji", ""),
                    "symbol": data.get("symbol", ""),
                }
            elif not metadata[code]["emoji"] and data.get("emoji"):
                metadata[code]["emoji"] = data["emoji"]

    result = []
    for doc in docs:
        bc = doc.get("currency")
        meta = metadata.get(bc)
        result.append(
            {
                "code": bc,
                "name": meta["name"] if meta else bc,
                "emoji": meta["emoji"] if meta else "",
                "symbol": meta["symbol"] if meta else "",
            }
        )

    for code, meta in metadata.items():
        if code not in base_set:
            result.append({"code": code, **meta})

    result.sort(key=lambda x: x["code"])
    await cache.set("currencies_info", result, ttl=3600)
    return result


async def convert_currencies(
    currencies_data: list[tuple[str, float]],
    output_currencies: list[str],
    index: int = 1,
) -> str:
    """
    Perform currency conversion.
    index=1: Direct (base → targets)
    index=0: Reverse (targets → base)
    """
    db = get_db()
    collection = db["fiat_rates"]

    # Build name→code map
    all_info = await get_currencies_info()
    name_to_code: dict[str, str] = {}
    settings = get_settings()

    # From currencies_info in data.json
    for name, info_list in settings.currencies_info.items():
        if len(info_list) > 1:
            name_to_code[name] = info_list[1]

    # From DB info
    for info in all_info:
        name_to_code[info["name"]] = info["code"]
        name_to_code[info["code"]] = info["code"]

    # Hardcoded fixes
    name_to_code["Ukraine Hryvnia"] = "UAH"

    # Build code → emoji/symbol fallback from currencies_data.json
    _cd_map: dict[str, dict] = {}
    for entry in get_currencies_data():
        c = entry.get("code", "")
        if c:
            _cd_map[c] = {
                "emoji": entry.get("emoji", ""),
                "symbol": entry.get("symbol", ""),
            }

    results: list[str] = []

    if index == 1:
        # Direct mode: base → targets
        for currency_code, amount in currencies_data:
            code = currency_code.upper()
            await ensure_currency(code, force=False)

            doc = await collection.find_one({"currency": code}, {"rates": 1})
            if not doc or "rates" not in doc:
                continue
            rates = doc["rates"]

            for out_name in output_currencies:
                target_code = name_to_code.get(out_name)
                if not target_code and out_name in rates:
                    target_code = out_name
                if not target_code or target_code not in rates:
                    continue

                rate_info = rates[target_code]
                try:
                    rate = float(rate_info.get("rate", 0))
                    if rate == 0:
                        continue
                    converted = round(amount * rate, 4)
                    symbol = rate_info.get("symbol", "")
                    emoji = rate_info.get("emoji", "")
                    # Fallback to currencies_data.json
                    if not emoji:
                        emoji = _cd_map.get(target_code, {}).get("emoji", "")
                    if not symbol:
                        symbol = _cd_map.get(target_code, {}).get("symbol", "")
                    results.append(f"{emoji} {target_code}: {converted}{symbol}")
                except (ValueError, TypeError):
                    continue

    else:
        # Reverse mode: targets → base
        target_code = currencies_data[0][0].upper()
        amount_target = currencies_data[0][1]

        base_codes = [name_to_code.get(n) for n in output_currencies]
        base_codes = [c for c in base_codes if c]
        if not base_codes:
            return "bad request"

        base_docs = await collection.find({"currency": {"$in": base_codes}}, {"currency": 1, "rates": 1}).to_list(
            length=100
        )
        base_map = {d["currency"]: d for d in base_docs}

        # Fetch missing
        for code in base_codes:
            if code not in base_map:
                await ensure_currency(code, force=True)
        if any(c not in base_map for c in base_codes):
            new_docs = await collection.find(
                {"currency": {"$in": [c for c in base_codes if c not in base_map]}}, {"currency": 1, "rates": 1}
            ).to_list(length=100)
            for d in new_docs:
                base_map[d["currency"]] = d

        for code in base_codes:
            doc = base_map.get(code)
            if not doc or "rates" not in doc:
                continue
            if target_code not in doc["rates"]:
                continue

            rate_data = doc["rates"][target_code]
            try:
                rate = float(rate_data.get("rate", 0))
                if rate == 0:
                    continue
                converted_val = amount_target * rate
                # Smart rounding
                if converted_val < 0.01:
                    converted = round(converted_val, 6)
                elif converted_val < 1:
                    converted = round(converted_val, 4)
                else:
                    converted = round(converted_val, 2)

                emoji = ""
                for info in all_info:
                    if info["code"] == code:
                        emoji = info.get("emoji", "")
                        break
                # Fallback to currencies_data.json
                if not emoji:
                    emoji = _cd_map.get(code, {}).get("emoji", "")

                target_symbol = rate_data.get("symbol", "")
                if not target_symbol:
                    target_symbol = _cd_map.get(code, {}).get("symbol", "")
                results.append(f"{emoji} {code}: {converted}{target_symbol}")
            except Exception:
                continue

    if results:
        return "\n".join(results)
    return "bad request"


# ── Background scheduler ───────────────────────────────────────────


async def run_parser_loop() -> None:
    """Main parser loop — runs as background asyncio task."""
    log.info("Parser service starting...")

    # Initial population
    await _initial_population()

    cycle = 0
    while True:
        try:
            settings = get_settings()
            cfg = settings.parser

            if not cfg.auto_update:
                await asyncio.sleep(30)
                continue

            cycle += 1
            log.info("=== Parser cycle #%d ===", cycle)
            start = time.monotonic()

            # Update stale critical currencies
            updated, skipped, failed = await _update_critical()
            log.info("Critical: %d updated, %d fresh, %d failed", updated, skipped, failed)

            # Crypto & stocks on 3-hour interval
            await _maybe_update_markets()

            elapsed = time.monotonic() - start
            sleep_time = max(60, cfg.update_interval_sec - elapsed)
            log.info("Cycle done in %.1fs. Next in %.0fs", elapsed, sleep_time)
            await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            log.info("Parser loop cancelled - shutting down")
            break
        except Exception as exc:
            log.error("Parser cycle error: %s", exc)
            await asyncio.sleep(60)


async def _initial_population() -> None:
    db = get_db()
    count = await db["fiat_rates"].count_documents({})
    cfg = get_settings().parser
    if count < len(cfg.critical_currencies) // 2:
        log.info("Initial population needed...")
        parser = FiatParser()
        try:
            for code in cfg.critical_currencies:
                await parser.fetch_rates(code)
                await asyncio.sleep(0.5)
        finally:
            await parser.close()
    else:
        log.info("%d currencies in DB - skipping initial population", count)


async def _update_critical() -> tuple[int, int, int]:
    cfg = get_settings().parser
    updated = skipped = failed = 0
    parser = FiatParser()
    try:
        for code in cfg.critical_currencies:
            if not await is_currency_stale(code, ttl_hours=1):
                skipped += 1
                continue
            if await parser.fetch_rates(code):
                updated += 1
            else:
                failed += 1
            await asyncio.sleep(0.5)
    finally:
        await parser.close()
    return updated, skipped, failed


async def _maybe_update_markets() -> None:
    db = get_db()
    cfg = get_settings().parser

    try:
        doc = await db["Status"].find_one({"_id": "parser_status"}, {"last_crypto_stocks_update": 1})
        last_update = doc.get("last_crypto_stocks_update", 0) if doc else 0
        if time.time() - last_update < cfg.crypto_stocks_interval_sec:
            return
    except Exception:
        pass

    log.info("Updating crypto and stocks...")
    crypto_ok = await fetch_crypto() is not None
    stocks_ok = await fetch_stocks() is not None

    if crypto_ok or stocks_ok:
        try:
            await db["Status"].update_one(
                {"_id": "parser_status"},
                {"$set": {"last_crypto_stocks_update": time.time()}},
                upsert=True,
            )
        except Exception as exc:
            log.error("Failed to save parser status: %s", exc)

        # Save price snapshot for volatility tracking
        try:
            from app.services.alert_service import save_price_snapshot

            await save_price_snapshot()
        except Exception as exc:
            log.warning("Failed to save price snapshot: %s", exc)
