"""
Configuration loader — reads config/settings.json and provides typed access.

Usage:
    from app.config import get_settings
    settings = get_settings()
    print(settings.bot.token)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    backup_enabled: bool = True  # Enable local daily backups
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
    critical_currencies: List[str] = field(
        default_factory=lambda: [
            "USD",
            "EUR",
            "GBP",
            "UAH",
            "PLN",
            "CZK",
            "CHF",
            "CNY",
            "JPY",
            "CAD",
            "AUD",
            "SEK",
            "NOK",
            "DKK",
            "SGD",
            "INR",
            "ILS",
            "KRW",
            "TRY",
            "RON",
            "BGN",
            "ISK",
            "EGP",
            "ARS",
            "RUB",
        ]
    )
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
    groups_enabled: bool = True
    inline_mode_enabled: bool = True


@dataclass(frozen=True)
class DraftSettings:
    enabled: bool = True  # Set to False to disable sendMessageDraft animation entirely
    loading_threshold_sec: float = 0.05
    animation_interval_sec: float = 0.25
    preview_delay_sec: float = 0.15


@dataclass(frozen=True)
class RedisSettings:
    """
    Redis configuration.
    If url is empty — Redis is disabled, the bot falls back to MemoryCache.
    Example url: redis://localhost:6379/0
    """
    url: str = ""  # empty = disabled
    max_connections: int = 10
    socket_timeout: float = 2.0
    socket_connect_timeout: float = 2.0


@dataclass(frozen=True)
class SentrySettings:
    """
    Sentry error tracking configuration.
    If dsn is empty — Sentry is disabled (no-op).
    Add SENTRY_DSN to settings.json or deploy env secrets to enable.
    """
    dsn: str = ""  # empty = disabled
    environment: str = "production"
    traces_sample_rate: float = 0.1  # 10% of transactions traced
    profiles_sample_rate: float = 0.0  # profiling disabled by default
    send_default_pii: bool = False


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
    draft: DraftSettings = field(default_factory=DraftSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    sentry: SentrySettings = field(default_factory=SentrySettings)

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
        return self._data_json.get("small_convert_currencies", ["USD", "EUR", "GBP", "PLN", "CZK", "UAH"])

    @property
    def default_crypto(self) -> list:
        return self._data_json.get("default_crypto", ["BTC", "ETH"])

    @property
    def default_stocks(self) -> list:
        return self._data_json.get("default_stocks", ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA"])


from dataclasses import dataclass, field, fields


def _from_dict(cls, data: dict):
    if not isinstance(data, dict):
        return cls()
    known_fields = {f.name for f in fields(cls)}
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return cls(**filtered)


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_settings(raw: dict, data_json: dict) -> Settings:
    return Settings(
        bot=_from_dict(BotSettings, raw.get("bot", {})),
        database=_from_dict(DatabaseSettings, raw.get("database", {})),
        api_keys=_from_dict(ApiKeysSettings, raw.get("api_keys", {})),
        urls=_from_dict(UrlsSettings, raw.get("urls", {})),
        i18n=_from_dict(I18nSettings, raw.get("i18n", {})),
        parser=_from_dict(ParserSettings, raw.get("parser", {})),
        security=_from_dict(SecuritySettings, raw.get("security", {})),
        features=_from_dict(FeaturesSettings, raw.get("features", {})),
        draft=_from_dict(DraftSettings, raw.get("draft", {})),
        redis=_from_dict(RedisSettings, raw.get("redis", {})),
        sentry=_from_dict(SentrySettings, raw.get("sentry", {})),
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
