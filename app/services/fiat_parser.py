"""
Fiat currency parser — fetches rates from fx-rate.net using curl_cffi
to bypass Cloudflare protection on headless servers.

All data is written directly to MongoDB.
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

from app.config import get_settings, get_currencies_data
from app.db import get_db
from app.logger import get_logger

log = get_logger("parser.fiat")


class FiatParser:
    """Async fiat currency parser with Cloudflare bypass."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._parser_cfg = self._settings.parser
        self._currencies_info = self._settings.currencies_info
        self._session: Optional[AsyncSession] = None

        # Build code → {emoji, symbol} fallback from currencies_data.json
        self._code_info: dict[str, dict] = {}
        for entry in get_currencies_data():
            code = entry.get("code", "")
            if code:
                self._code_info[code] = {
                    "emoji": entry.get("emoji", ""),
                    "symbol": entry.get("symbol", ""),
                }

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(impersonate="chrome120")
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    # ── Public API ──────────────────────────────────────────────────

    async def fetch_rates(self, currency_code: str) -> bool:
        """
        Fetch exchange rates for a single currency and save to MongoDB.
        Returns True on success.
        """
        code = currency_code.upper()
        url = f"{self._parser_cfg.fiat_source_url}/{code}/"
        log.info("Fetching rates for %s …", code)

        # Random delay to avoid rate limiting
        delay = random.uniform(
            self._parser_cfg.request_delay_min_sec,
            self._parser_cfg.request_delay_max_sec,
        )
        await asyncio.sleep(delay)

        session = await self._get_session()

        for attempt in range(1, self._parser_cfg.retry_attempts + 1):
            try:
                resp = await session.get(url, timeout=30)

                if resp.status_code == 403:
                    log.warning("[%s] HTTP 403 — rate limited (attempt %d)", code, attempt)
                    await asyncio.sleep(self._parser_cfg.retry_delay_sec * attempt)
                    continue

                if resp.status_code != 200:
                    log.error("[%s] HTTP %d (attempt %d)", code, resp.status_code, attempt)
                    await asyncio.sleep(self._parser_cfg.retry_delay_sec * attempt)
                    continue

                html = resp.text

                # Cloudflare challenge page check
                if "Checking your browser" in html or "DDoS protection by Cloudflare" in html:
                    log.warning("[%s] Cloudflare challenge detected (attempt %d)", code, attempt)
                    await asyncio.sleep(5)
                    continue

                rates = self._parse_html(code, html)
                if rates:
                    await self._save_to_db(code, rates)
                    log.info("[%s] ✓ %d rates parsed and saved", code, len(rates))
                    return True
                else:
                    log.warning("[%s] No rates parsed from HTML", code)

            except Exception as exc:
                log.error("[%s] Error (attempt %d): %s", code, attempt, exc)
                await asyncio.sleep(self._parser_cfg.retry_delay_sec)

        return False

    # ── HTML parsing ────────────────────────────────────────────────

    def _parse_html(self, base_code: str, html: str) -> Dict[str, dict]:
        soup = BeautifulSoup(html, "html.parser")
        rate_items = soup.find_all("div", class_="c_parameter", attrs={"data-rate": True})

        if not rate_items:
            return {}

        rates: Dict[str, dict] = {}
        for item in rate_items:
            try:
                rate = float(item.get("data-rate", 0))
                if rate == 0:
                    continue

                parent_td = item.parent
                if not parent_td or parent_td.name != "td":
                    continue
                parent_tr = parent_td.parent
                if not parent_tr or parent_tr.name != "tr":
                    continue

                img = parent_td.find("img", alt=True)
                currency_name = img.get("alt", "") if img else ""
                if not currency_name:
                    continue

                link = parent_tr.find("a", href=True)
                if not link:
                    continue
                parts = link.get("href", "").strip("/").split("/")
                if len(parts) < 2:
                    continue
                target_code = parts[1].upper()

                reverse_rate = 1 / rate if rate != 0 else 0
                info = self._currencies_info.get(currency_name, ["", "", ""])

                # Special fix for UAH name mismatch
                if target_code == "UAH" and (not info or not info[0]):
                    info = ["🇺🇦", "UAH", "₴"]

                emoji = info[0] if len(info) > 0 else ""
                symbol = info[2] if len(info) > 2 else ""

                # Fallback to currencies_data.json if emoji is missing
                if not emoji and target_code in self._code_info:
                    emoji = self._code_info[target_code].get("emoji", "")
                if not symbol and target_code in self._code_info:
                    symbol = self._code_info[target_code].get("symbol", "")

                rates[target_code] = {
                    "rate": rate,
                    "reverse_rate": reverse_rate,
                    "name": currency_name,
                    "emoji": emoji,
                    "symbol": symbol,
                }
            except (ValueError, TypeError):
                continue

        return rates

    # ── MongoDB persistence ─────────────────────────────────────────

    async def _save_to_db(self, code: str, rates: dict) -> None:
        db = get_db()
        doc = {
            "currency": code,
            "rates": rates,
            "metadata": {
                "total_currencies": len(rates),
                "source": self._parser_cfg.fiat_source_url,
                "success": True,
            },
            "updated_at": datetime.now(timezone.utc),
        }
        await db["fiat_rates"].update_one(
            {"currency": code},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
