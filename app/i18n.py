"""
Unified internationalisation (i18n) — loads all locale JSON files once,
provides a single get_text() function used everywhere.

Usage:
    from app.i18n import I18n
    i18n = I18n()                        # loads at import
    text = i18n.get("menu.private", "uk")
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from app.config import LOCALES_DIR, get_settings
from app.logger import get_logger

log = get_logger("i18n")


class I18n:
    """
    Loads all locale/*.json files and provides dot-path access.

    • Supports nested keys via dot notation: ``"exchange rate.main rate"``
    • Falls back to default language if key is missing in requested locale.
    • Thread-safe (read-only after __init__).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.default_lang: str = settings.i18n.default_language
        self.supported: List[str] = list(settings.i18n.supported_languages)
        self._data: Dict[str, dict] = {}
        self._load_all()

    # ── Loading ─────────────────────────────────────────────────────

    def _load_all(self) -> None:
        for lang in self.supported:
            path = LOCALES_DIR / f"{lang}.json"
            if not path.exists():
                log.warning("Locale file missing: %s", path)
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data[lang] = json.load(f)
                log.debug("Loaded locale: %s", lang)
            except (json.JSONDecodeError, OSError) as exc:
                log.error("Failed to load locale %s: %s", lang, exc)

        log.info(
            "i18n loaded %d locales: %s",
            len(self._data),
            ", ".join(self._data.keys()),
        )

    # ── Accessors ───────────────────────────────────────────────────

    def _resolve(self, data: dict, key: str) -> Any:
        """Walk dot-separated key path. Returns None if not found."""
        parts = key.split(".")
        node = data
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return None
            if node is None:
                return None
        return node

    def get(
        self,
        key: str,
        lang: str | None = None,
        default: Any = None,
        **kwargs: Any,
    ) -> Any:
        """
        Get translated value by dot-path key.

        Falls back: requested lang → default lang → default argument (if given) → key string.
        If the result is a string and kwargs are provided, formats it.
        """
        requested_lang = lang if lang in self._data else self.default_lang
        value = self._resolve(self._data.get(requested_lang, {}), key)

        # Fallback to default language
        if value is None and requested_lang != self.default_lang:
            value = self._resolve(self._data.get(self.default_lang, {}), key)

        # Last resort: use provided default or key itself
        if value is None:
            value = default if default is not None else key

        # Format strings if kwargs provided
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except (KeyError, IndexError):
                pass

        return value

    def get_section(self, key: str, lang: str | None = None) -> dict:
        """Get a whole dict section (e.g. 'keyboard.settings')."""
        result = self.get(key, lang)
        return result if isinstance(result, dict) else {}


# ── Module-level singleton ──────────────────────────────────────────


@lru_cache(maxsize=1)
def get_i18n() -> I18n:
    return I18n()
