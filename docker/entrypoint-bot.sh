#!/bin/bash
# entrypoint-bot.sh — Generates config/settings.json from environment variables, then starts the bot.
# This mirrors what deploy.yml step "Generate Settings" does on the VPS.
set -e

CONFIG_DIR="/app/config"
SETTINGS_FILE="$CONFIG_DIR/settings.json"

mkdir -p /app/logs /app/config 2>/dev/null || true

if [ -s "$SETTINGS_FILE" ]; then
  echo "==> $SETTINGS_FILE already exists, skipping generation."
else
  echo "==> Generating settings.json from environment..."

python3 - <<PYEOF
import json, os

def env_list(key, default="[]"):
    try:
        return json.loads(os.environ.get(key, default))
    except:
        return json.loads(default)

settings = {
    "bot": {
        "token": os.environ.get("BOT_TOKEN", ""),
        "admin_ids": env_list("BOT_ADMIN_IDS", "[]"),
        "backup_enabled": os.environ.get("BACKUP_ENABLED", "false").lower() == "true",
        "version": "finances 6.6.0",
    },
    "database": {
        "mongo_uri": os.environ.get("MONGO_URI", ""),
        "mongo_database": os.environ.get("MONGO_DATABASE", "finances"),
        "pool_min": int(os.environ.get("DB_POOL_MIN", "5")),
        "pool_max": int(os.environ.get("DB_POOL_MAX", "50")),
    },
    "api_keys": {
        "crypto": os.environ.get("CRYPTO_API_KEY", ""),
        "stocks": os.environ.get("STOCKS_API_KEY", ""),
    },
    "urls": {
        "github": os.environ.get("URL_GITHUB", ""),
        "communication": os.environ.get("URL_COMMUNICATION", ""),
        "invite": os.environ.get("URL_INVITE", ""),
        "buymeacoffee": os.environ.get("URL_BUYMEACOFFEE", ""),
        "donatello": os.environ.get("URL_DONATELLO", ""),
        "bank": os.environ.get("URL_BANK", ""),
        "mini_app": os.environ.get("URL_MINI_APP", ""),
    },
    "i18n": {
        "supported_languages": ["en", "uk"],
        "default_language": "en",
    },
    "security": {
        "rate_limit_requests": int(os.environ.get("RATE_LIMIT_REQUESTS", "30")),
        "rate_limit_window_sec": int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60")),
        "fernet_key": os.environ.get("FERNET_KEY", ""),
    },
    "features": {
        "mini_app_enabled": os.environ.get("MINI_APP_ENABLED", "false").lower() == "true",
        "groups_enabled": os.environ.get("GROUPS_ENABLED", "true").lower() == "true",
        "inline_mode_enabled": os.environ.get("INLINE_MODE_ENABLED", "true").lower() == "true",
    },
    "redis": {
        "url": os.environ.get("REDIS_URL", ""),
    },
    "draft": {
        "enabled": False,
        "loading_threshold_sec": 0.05,
        "animation_interval_sec": 0.25,
        "preview_delay_sec": 0.15,
    },
}

with open("$SETTINGS_FILE", "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

print("settings.json written successfully")
PYEOF
fi

echo "==> Starting finances bot..."
exec python -m app "$@"
