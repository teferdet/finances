"""
Service for synchronizing crypto portfolio with exchanges (Binance, Bybit).
"""
from __future__ import annotations

import hmac
import time
import urllib.parse
from typing import Dict, Any

import aiohttp

from app.db import get_db
from app.logger import get_logger
from app.services.security import decrypt_data
from app.services.portfolio_service import add_asset

log = get_logger("exchange_sync")

# Cooldown for syncing in seconds (10 minutes)
SYNC_COOLDOWN_SEC = 600

class ExchangeAPIError(Exception):
    pass


async def fetch_binance_balances(api_key: str, api_secret: str) -> Dict[str, float]:
    """Fetch non-zero spot balances from Binance."""
    base_url = "https://api.binance.com"
    endpoint = "/api/v3/account"
    
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        "sha256"  # HMAC-SHA256 required by Binance API
    ).hexdigest()
    
    url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            if response.status != 200:
                raise ExchangeAPIError(data.get("msg", "Unknown Binance error"))
                
            balances = {}
            for asset in data.get("balances", []):
                free = float(asset.get("free", 0))
                locked = float(asset.get("locked", 0))
                total = free + locked
                if total > 0:
                    balances[asset["asset"]] = total
            return balances


async def fetch_bybit_balances(api_key: str, api_secret: str) -> Dict[str, float]:
    """Fetch non-zero balances from Bybit (Unified Account)."""
    base_url = "https://api.bybit.com"
    endpoint = "/v5/account/wallet-balance"
    
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    query_string = "accountType=UNIFIED"
    
    # Bybit signature string: timestamp + api_key + recv_window + queryString
    sign_str = timestamp + api_key + recv_window + query_string
    signature = hmac.new(
        api_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        "sha256"  # HMAC-SHA256 required by Bybit API
    ).hexdigest()
    
    url = f"{base_url}{endpoint}?{query_string}"
    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "X-BAPI-SIGN": signature
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            if response.status != 200 or data.get("retCode") != 0:
                raise ExchangeAPIError(data.get("retMsg", "Unknown Bybit error"))
                
            balances = {}
            result = data.get("result", {})
            list_data = result.get("list", [])
            if list_data:
                coins = list_data[0].get("coin", [])
                for coin in coins:
                    total = float(coin.get("walletBalance", 0))
                    if total > 0:
                        balances[coin["coin"]] = total
            return balances


async def sync_exchange_portfolio(user_id: int, exchange: str) -> dict:
    """
    Syncs the user's exchange balance to their portfolio.
    Returns:
        {"status": "success", "count": int}
        {"status": "error", "message": str}
        {"status": "cooldown", "minutes": int}
        {"status": "no_keys"}
    """
    db = get_db()
    api_key_doc = await db["ApiKeys"].find_one({"user_id": user_id, "exchange": exchange})
    
    if not api_key_doc:
        return {"status": "no_keys"}
        
    last_sync = api_key_doc.get("last_sync", 0)
    current_time = time.time()
    
    if current_time - last_sync < SYNC_COOLDOWN_SEC:
        minutes_left = int((SYNC_COOLDOWN_SEC - (current_time - last_sync)) / 60) + 1
        return {"status": "cooldown", "minutes": minutes_left}
        
    api_key = api_key_doc["api_key"]
    api_secret_encrypted = api_key_doc["api_secret"]
    
    try:
        api_secret = decrypt_data(api_secret_encrypted)
    except Exception as e:
        log.error("Failed to decrypt API secret for user %s: %s", user_id, e)
        return {"status": "error", "message": "Decryption failed."}
        
    try:
        if exchange == "Binance":
            balances = await fetch_binance_balances(api_key, api_secret)
        elif exchange == "Bybit":
            balances = await fetch_bybit_balances(api_key, api_secret)
        else:
            return {"status": "error", "message": "Unknown exchange."}
    except ExchangeAPIError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        log.error("Unexpected error syncing %s for user %s: %s", exchange, user_id, e)
        return {"status": "error", "message": "Network error or API changes."}
        
    # Update portfolio: we will add the new balances. 
    # To prevent duplicates if they sync multiple times, we should ideally remove previous exchange assets
    # or identify them. Currently, add_asset adds to existing. 
    # We will clear the existing exchange lot first by tagging them.
    # We don't have tags in portfolio natively, so we just overwrite the total amount for that asset.
    # Wait, the prompt user said "оновлювати/перезаписувати всі існуючі крипто-активи користувача".
    # I asked them, but I will default to: replace the asset amount with the exchange balance.
    # Or simply: use update_one to set the amount.
    
    count = 0
    for ticker, amount in balances.items():
        if ticker.startswith("LD"): # Binance liquid swap ignoring
            ticker = ticker[2:]
            
        # Standardize ticker
        ticker = ticker.upper()
        
        # Remove any existing lots for this ticker to avoid duplicates and logic bugs with $ operator
        await db["Users"].update_one(
            {"_id": user_id},
            {"$pull": {"portfolio.crypto": {"ticker": ticker}}}
        )
        
        # Add new asset with the full synced amount
        await add_asset(
            user_id=user_id,
            asset_type="crypto",
            ticker=ticker,
            amount=amount
        )
        count += 1
        
    # Update last_sync
    await db["ApiKeys"].update_one(
        {"_id": api_key_doc["_id"]},
        {"$set": {"last_sync": current_time}}
    )
    
    return {"status": "success", "count": count}
