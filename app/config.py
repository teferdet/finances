"""
Configuration loader — reads config/settings.json and provides typed access.

Usage:
    from app.config import get_settings
    settings = get_settings()
    print(settings.bot.token)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List


# ── Resolve project root (parent of app/) ──────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LOCALES_DIR = PROJECT_ROOT / "locales"
LOGS_DIR = PROJECT_ROOT / "logs"


# ── Dataclasses ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BotSettings:
    token: str
    admin_ids: List[int]
    version: str = "finances 6.0"


@dataclass(frozen=True)
class DatabaseSettings:
    mongo_uri: str
    mongo_database: str = "finances"
    pool_min: int = 5
    pool_max: int = 50


@dataclass(frozen=True)
class ApiKeysSettings:
    crypto: str = ""
    stocks: str = ""


@dataclass(frozen=True)
class UrlsSettings:
    github: str = ""
    communication: str = ""
    invite: str = ""
    buymeacoffee: str = ""
    donatello: str = ""
    bank: str = ""
    mini_app: str = ""


@dataclass(frozen=True)
class I18nSettings:
    supported_languages: List[str] = field(default_factory=lambda: ["en", "uk"])
    default_language: str = "en"


@dataclass(frozen=True)
class ParserSettings:
    auto_update: bool = True
    update_interval_sec: int = 3600
    fiat_source_url: str = "https://fx-rate.net"
    retry_attempts: int = 3
    retry_delay_sec: int = 5
    request_delay_min_sec: int = 3
    request_delay_max_sec: int = 7
    critical_currencies: List[str] = field(default_factory=lambda: [
        "USD", "EUR", "GBP", "UAH", "PLN", "CZK", "CHF", "CNY", "JPY",
        "CAD", "AUD", "SEK", "NOK", "DKK", "SGD", "INR", "ILS", "KRW",
        "TRY", "RON", "BGN", "ISK", "EGP", "ARS", "RUB",
    ])
    on_demand_cache_ttl_hours: int = 5
    crypto_stocks_interval_sec: int = 10800


@dataclass(frozen=True)
class SecuritySettings:
    rate_limit_requests: int = 30
    rate_limit_window_sec: int = 60
    max_message_length: int = 1000
    fernet_key: str = ""


@dataclass(frozen=True)
class FeaturesSettings:
    mini_app_enabled: bool = False


@dataclass(frozen=True)
class Settings:
    bot: BotSettings
    database: DatabaseSettings
    api_keys: ApiKeysSettings
    urls: UrlsSettings
    i18n: I18nSettings
    parser: ParserSettings
    security: SecuritySettings
    features: FeaturesSettings

    # ── Currency data helpers (loaded from data.json) ───────────────────
    _data_json: dict = field(default_factory=dict, repr=False)

    @property
    def currencies_info(self) -> dict:
        return self._data_json.get("currencies_info", {})

    @property
    def symbol_map(self) -> dict:
        return self._data_json.get("symbol", {})

    @property
    def convert_currencies(self) -> list:
        return self._data_json.get("convert_currencies", [])

    @property
    def convert_crypto(self) -> list:
        return self._data_json.get("convert_crypto", [])

    @property
    def crypto_list(self) -> list:
        return self._data_json.get("crypto", [])

    @property
    def company_list(self) -> list:
        return self._data_json.get("company", [])

    @property
    def small_convert_currencies(self) -> list:
        return self._data_json.get(
            "small_convert_currencies",
            ["USD", "EUR", "GBP", "PLN", "CZK", "UAH"]
        )

    @property
    def default_crypto(self) -> list:
        return self._data_json.get("default_crypto", ["BTC", "ETH"])

    @property
    def default_stocks(self) -> list:
        return self._data_json.get("default_stocks", ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA"])


# ── Loader ──────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_settings(raw: dict, data_json: dict) -> Settings:
    return Settings(
        bot=BotSettings(**raw.get("bot", {})),
        database=DatabaseSettings(**raw.get("database", {})),
        api_keys=ApiKeysSettings(**raw.get("api_keys", {})),
        urls=UrlsSettings(**raw.get("urls", {})),
        i18n=I18nSettings(**raw.get("i18n", {})),
        parser=ParserSettings(**raw.get("parser", {})),
        security=SecuritySettings(**raw.get("security", {})),
        features=FeaturesSettings(**raw.get("features", {})),
        _data_json=data_json,
    )


_settings_cache: Settings | None = None
_last_settings_mtime: float = 0.0


def get_settings() -> Settings:
    """
    Load settings.json + data.json and return a Settings object.
    Cached based on file modification time — automatically reloads if files change.
    """
    global _settings_cache, _last_settings_mtime

    settings_path = CONFIG_DIR / "settings.json"
    data_path = CONFIG_DIR / "data.json"

    try:
        mtime1 = settings_path.stat().st_mtime if settings_path.exists() else 0
        mtime2 = data_path.stat().st_mtime if data_path.exists() else 0
        current_mtime = max(mtime1, mtime2)
    except Exception:
        current_mtime = 0

    if _settings_cache is not None and current_mtime == _last_settings_mtime:
        return _settings_cache

    raw = _load_json(settings_path) if settings_path.exists() else {}
    data = _load_json(data_path) if data_path.exists() else {}

    _settings_cache = _build_settings(raw, data)
    _last_settings_mtime = current_mtime
    return _settings_cache


def get_currencies_data() -> list:
    """Load currencies_data.json (list of dicts with code/emoji/symbol/text)."""
    path = CONFIG_DIR / "currencies_data.json"
    if not path.exists():
        return []
    return _load_json(path)


def save_settings(settings: Settings) -> None:
    """Save the settings object back to settings.json."""
    import dataclasses
    path = CONFIG_DIR / "settings.json"
    raw = dataclasses.asdict(settings)
    # _data_json is not stored in settings.json
    raw.pop("_data_json", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
