"""
Dashboard Auth — OTP generation + Telegram Inline 2FA approval + JWT session management.

Security model:
- Admin inputs Telegram ID → verified against admin_ids list
- 6-digit OTP + Telegram Inline Buttons [Accept / Block IP] sent to admin's Telegram
- If admin clicks [Accept] in Telegram → Web app auto-logs in!
- If admin clicks [Block IP] in Telegram → Requester IP is permanently blacklisted!
- On success → signed JWT in httpOnly cookie (8h lifetime)
- Rate limit: 10 req/min per IP on /api/auth/*
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

import httpx
import jwt

# ── Configuration ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 8 * 3600  # 8 hours
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

OTP_TTL = 300          # 5 minutes
OTP_MAX_ATTEMPTS = 5   # per OTP request
IP_BLOCK_DURATION = 900  # 15 minutes temporary block

# ── In-memory stores ───────────────────────────────────────────────────────────

# {req_id: {"telegram_id": int, "otp": str, "ip": str, "expires_at": float, "attempts": int, "status": "pending"|"approved"|"blocked"}}
_auth_requests: dict[str, dict] = {}

# {telegram_id: req_id}
_user_latest_req: dict[int, str] = {}

# {ip: {"count": int, "window_start": float}}
_rate_store: dict[str, dict] = {}

# {ip: float}  — temporary blocks
_block_store: dict[str, float] = {}

# Permanent blacklisted IPs
_blacklisted_ips: set[str] = set()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Cryptographically secure 6-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _now() -> float:
    return time.monotonic()


def _wall_now() -> float:
    return time.time()


# ── Rate & Blacklist limiting ──────────────────────────────────────────────────

def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = _now()
    entry = _rate_store.get(ip)
    if entry is None or now - entry["window_start"] > window:
        _rate_store[ip] = {"count": 1, "window_start": now}
        return True
    if entry["count"] >= limit:
        return False
    entry["count"] += 1
    return True


def is_ip_blocked(ip: str) -> bool:
    """Return True if IP is blocked (permanently blacklisted or temporarily blocked)."""
    if ip in _blacklisted_ips:
        return True
    blocked_until = _block_store.get(ip, 0)
    if _now() < blocked_until:
        return True
    _block_store.pop(ip, None)
    return False


def block_ip(ip: str, permanent: bool = False) -> None:
    """Block an IP address."""
    if permanent:
        _blacklisted_ips.add(ip)
    else:
        _block_store[ip] = _now() + IP_BLOCK_DURATION


# ── OTP & Auth Request lifecycle ───────────────────────────────────────────────

def create_auth_request(telegram_id: int, client_ip: str) -> tuple[str, str]:
    """
    Generate a fresh auth request with a req_id and OTP.
    Returns (req_id, otp).
    """
    req_id = f"req_{secrets.token_hex(6)}"
    otp = _generate_otp()
    
    req_data = {
        "req_id": req_id,
        "telegram_id": telegram_id,
        "otp": otp,
        "ip": client_ip,
        "status": "pending",  # "pending", "approved", "blocked"
        "expires_at": _now() + OTP_TTL,
        "attempts": 0,
    }
    
    _auth_requests[req_id] = req_data
    _user_latest_req[telegram_id] = req_id
    return req_id, otp


def get_auth_request(req_id: str) -> Optional[dict]:
    """Retrieve auth request by req_id."""
    req = _auth_requests.get(req_id)
    if not req:
        return None
    if _now() > req["expires_at"]:
        _auth_requests.pop(req_id, None)
        return None
    return req


def set_auth_status(req_id: str, status: str) -> None:
    """Update status of auth request ('approved' or 'blocked')."""
    req = _auth_requests.get(req_id)
    if req:
        req["status"] = status
        if status == "blocked":
            block_ip(req["ip"], permanent=True)


def verify_otp(telegram_id: int, provided: str, client_ip: str) -> tuple[bool, str, Optional[str]]:
    """
    Verify the OTP manually.
    Returns (success: bool, error_message: str, req_id: str|None).
    """
    req_id = _user_latest_req.get(telegram_id)
    if not req_id or req_id not in _auth_requests:
        return False, "No active login request for this Telegram ID", None

    entry = _auth_requests[req_id]
    if entry["status"] == "blocked":
        block_ip(client_ip, permanent=True)
        return False, "Login request blocked — IP added to blacklist", None

    if _now() > entry["expires_at"]:
        _auth_requests.pop(req_id, None)
        return False, "OTP expired", None

    entry["attempts"] += 1
    if entry["attempts"] > OTP_MAX_ATTEMPTS:
        _auth_requests.pop(req_id, None)
        block_ip(client_ip)
        return False, "Too many attempts — IP temporarily blocked for 15 minutes", None

    expected = entry["otp"].encode()
    provided_b = provided.encode()
    if not hmac.compare_digest(expected, provided_b):
        remaining = OTP_MAX_ATTEMPTS - entry["attempts"]
        return False, f"Invalid OTP — {remaining} attempts remaining", None

    # Success — mark approved
    entry["status"] = "approved"
    return True, "", req_id


# ── JWT tokens ─────────────────────────────────────────────────────────────────

def create_jwt(telegram_id: int) -> str:
    payload = {
        "sub": str(telegram_id),
        "iat": int(_wall_now()),
        "exp": int(_wall_now()) + JWT_EXPIRY_SECONDS,
        "type": "dashboard_session",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> Optional[int]:
    """Decode JWT → returns telegram_id (int) or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "dashboard_session":
            return None
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        return None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


# ── Telegram OTP & Inline 2FA sender ──────────────────────────────────────────

async def send_otp_via_telegram(telegram_id: int, otp: str, req_id: str, client_ip: str) -> bool:
    """
    Send verification code & Inline Buttons [✅ Approve / ⛔ Block IP] to admin Telegram.
    """
    if not BOT_TOKEN:
        return False

    text = (
        "🔐 *Dashboard Login Request*\n\n"
        f"📍 *IP Address:* `{client_ip}`\n"
        f"🔑 *Verification Code:* `{otp}`\n\n"
        "_Enter this code on the web page to login\\. Valid for 5 minutes\\._"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": "MarkdownV2",
            })
            return resp.status_code == 200
    except Exception:
        return False


# ── Cleanup ────────────────────────────────────────────────────────────────────

# ── Telegram Inline Button Poller ──────────────────────────────────────────────




def cleanup_expired() -> None:
    now = _now()
    expired = [rid for rid, e in _auth_requests.items() if now > e["expires_at"]]
    for rid in expired:
        _auth_requests.pop(rid, None)
