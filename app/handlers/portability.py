"""
Data Portability handler - import and export CSV.
"""

from __future__ import annotations

import io
import csv
import math
import asyncio
import pandas as pd
from typing import Any


def sanitize_csv_field(value: Any) -> str:
    if value is None or value == "":
        return ""
    val_str = str(value)
    if val_str.startswith(("=", "+", "-", "@")):
        return f"'{val_str}"
    return val_str


from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from app.db import get_db
from app.i18n import I18n
from app.services.portfolio_service import (
    _get_current_usd_price,
    _get_fiat_usd_price,
    add_asset,
)

router = Router(name="portability")


@router.message(Command("export"))
async def cmd_export(message: Message, i18n: I18n, lang: str) -> None:
    """Generate and send CSV with user's portfolio."""
    from app.services.portfolio_service import _ensure_migrated

    user_id = message.from_user.id
    await _ensure_migrated(user_id)

    db = get_db()
    user = await db["Users"].find_one({"_id": user_id}, {"portfolio": 1})
    portfolio = (user or {}).get("portfolio", {})

    count = 0
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["asset_type", "ticker", "amount", "buy_price_usd"])

    for section in ("crypto", "stock", "fiat"):
        lots = portfolio.get(section, [])
        if isinstance(lots, list):
            for lot in lots:
                if isinstance(lot, dict):
                    writer.writerow(
                        [
                            sanitize_csv_field(section),
                            sanitize_csv_field(lot.get("ticker", "")),
                            sanitize_csv_field(lot.get("amount", 0)),
                            sanitize_csv_field(lot.get("buy_price_usd")),
                        ]
                    )
                    count += 1

    if count == 0:
        await message.answer(str(i18n.get("portfolio.empty", lang)))
        return

    csv_bytes = output.getvalue().encode("utf-8")
    file = BufferedInputFile(csv_bytes, filename="portfolio_export.csv")

    text = str(i18n.get("portability.export_success", lang)).format(count=count)

    await message.answer_document(document=file, caption=text)


@router.message(Command("import"))
async def cmd_import_prompt(message: Message, i18n: I18n, lang: str) -> None:
    """Send prompt for importing CSV."""
    text = str(i18n.get("portability.import_prompt", lang))
    await message.answer(text, parse_mode="HTML")


@router.message(F.document)
async def handle_document_import(message: Message, i18n: I18n, lang: str) -> None:
    """Handle incoming document (expecting CSV)."""
    doc = message.document
    if not doc:
        return

    if doc.mime_type not in ("text/csv", "application/csv") and not (doc.file_name and doc.file_name.endswith(".csv")):
        # Not a CSV, ignore
        return

    # Check size limit (max 2 MB)
    if doc.file_size and doc.file_size > 2 * 1024 * 1024:
        text = str(i18n.get("portability.file_too_large", lang))
        await message.answer(text)
        return

    file_in_memory = io.BytesIO()
    await message.bot.download(doc, destination=file_in_memory)
    file_in_memory.seek(0)

    msg_loading = str(i18n.get("portability.importing", lang))
    loading_message = await message.answer(msg_loading)

    try:

        def _parse_csv():
            return pd.read_csv(file_in_memory)

        df = await asyncio.to_thread(_parse_csv)

        if len(df) > 500:
            text_err = str(i18n.get("portability.file_too_large", lang))
            await loading_message.edit_text(text_err)
            return

        required_cols = {"asset_type", "ticker", "amount"}
        if not required_cols.issubset(df.columns):
            text_err = str(i18n.get("portability.invalid_format", lang))
            await loading_message.edit_text(text_err)
            return

        success_count = 0
        error_count = 0

        for _, row in df.iterrows():
            asset_type = str(row.get("asset_type")).lower()
            ticker = str(row.get("ticker")).upper()
            try:
                amount = float(row.get("amount"))
            except (ValueError, TypeError):
                error_count += 1
                continue

            buy_price_usd = row.get("buy_price_usd")
            if pd.isna(buy_price_usd) or buy_price_usd == "":
                buy_price_usd = None
            else:
                try:
                    buy_price_usd = float(buy_price_usd)
                    if math.isnan(buy_price_usd) or math.isinf(buy_price_usd):
                        buy_price_usd = None
                except (ValueError, TypeError):
                    buy_price_usd = None

            if asset_type not in ("crypto", "stock", "fiat"):
                error_count += 1
                continue

            if math.isnan(amount) or math.isinf(amount) or amount <= 0:
                error_count += 1
                continue

            # Validate ticker against db
            is_valid = False
            if asset_type in ("crypto", "stock"):
                price = await _get_current_usd_price(ticker)
                if price is not None:
                    is_valid = True
            elif asset_type == "fiat":
                price = await _get_fiat_usd_price(ticker)
                if price is not None:
                    is_valid = True

            if not is_valid:
                error_count += 1
                continue

            await add_asset(
                user_id=message.from_user.id,
                asset_type=asset_type,
                ticker=ticker,
                amount=amount,
                buy_price_usd=buy_price_usd,
            )
            success_count += 1

        text = str(i18n.get("portability.import_result", lang)).format(success=success_count, error=error_count)

        await loading_message.edit_text(text)

    except Exception as e:
        text_err = str(i18n.get("portability.parse_error", lang))
        await loading_message.edit_text(text_err)
