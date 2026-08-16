"""
Dashboard FastAPI application — main entry point.

Endpoints:
  POST /api/auth/request-otp    — send OTP to admin via bot
  POST /api/auth/verify-otp     — verify OTP, set session cookie
  POST /api/auth/logout         — clear session cookie
  GET  /api/health              — liveness probe (no auth)
  GET  /api/stats/overview      — KPI metrics
  GET  /api/stats/activity      — DAU/requests time series
  GET  /api/stats/users         — user breakdown + top users
  GET  /api/stats/database      — MongoDB collections & sizes
  GET  /api/stats/bot           — systemd + CPU/RAM
  GET  /api/stats/parser        — parser health
  GET  /api/stats/alerts        — price alert stats
  GET  /api/stats/groups        — groups stats
  GET  /api/stats/errors        — error log (last 100 lines)
  GET  /api/config              — safe config read
  PATCH /api/config/features    — toggle a feature flag
  POST /api/actions/restart     — restart finances-bot.service
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from . import auth, queries

log = logging.getLogger("dashboard.api")


# ── Configuration ──────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "")
MONGO_DB = os.environ.get("MONGO_DATABASE", "finances")
ADMIN_IDS_RAW = os.environ.get("BOT_ADMIN_IDS", "[]")
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
try:
    ADMIN_IDS: list[int] = json.loads(ADMIN_IDS_RAW)
except Exception:
    ADMIN_IDS = []

COOKIE_NAME = "dash_session"
COOKIE_MAX_AGE = auth.JWT_EXPIRY_SECONDS

# ── Rate limiter (slowapi) ─────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])



# ── Database lifecycle ─────────────────────────────────────────────────────────

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client, _db

    # ── Sentry initialization ──────────────────────────────────────────────────
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,
        )
        log.info("Sentry initialized for dashboard")
    else:
        log.info("Sentry disabled (SENTRY_DSN not set)")

    try:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=3000,
            tlsAllowInvalidCertificates=True,
        )
        _db = _client[MONGO_DB]
    except Exception as e:
        log.error("MongoDB connection error: %s", e)
        _db = None

    # Periodic cleanup task (every 60 seconds)
    cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    cleanup_task.cancel()
    if _client:
        _client.close()



async def _cleanup_loop():
    while True:
        try:
            auth.cleanup_expired()
        except Exception:
            pass
        await asyncio.sleep(60)





def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise HTTPException(503, "Database not ready")
    return _db


# ── App factory ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Finances Dashboard API",
    version="1.0.0",
    docs_url=None,   # disable Swagger UI in production
    redoc_url=None,
    lifespan=lifespan,
)

# ── SlowAPI middleware (rate limiting) ─────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: only allow same-origin (dashboard served from same NGINX)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # NGINX already restricts external access
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)



# ── Auth helpers ───────────────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _require_auth(dash_session: str | None = Cookie(default=None)) -> int:
    if not dash_session:
        raise HTTPException(401, "Not authenticated")
    telegram_id = auth.verify_jwt(dash_session)
    if telegram_id is None:
        raise HTTPException(401, "Session expired or invalid")
    return telegram_id


# ── Pydantic models ────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    telegram_id: int


class OtpVerify(BaseModel):
    telegram_id: int
    otp: str


class FeaturePatch(BaseModel):
    feature: str
    value: bool


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/auth/request-otp")
@limiter.limit("10/minute")
async def request_otp(body: OtpRequest, request: Request) -> dict:
    ip = _get_client_ip(request)

    # Check MongoDB blacklist first
    if _db is not None:
        try:
            blacklisted = await _db["dash_blocked_ips"].find_one({"_id": ip})
            if blacklisted:
                raise HTTPException(403, "IP address is blacklisted by admin")
        except HTTPException:
            raise
        except Exception:
            pass

    if auth.is_ip_blocked(ip):
        raise HTTPException(429, "IP blocked — too many failed attempts")

    if not auth.check_rate_limit(ip, limit=10, window=60):
        raise HTTPException(429, "Rate limit exceeded")

    if body.telegram_id not in ADMIN_IDS:
        raise HTTPException(403, "Access denied")

    req_id, otp = auth.create_auth_request(body.telegram_id, ip)

    if _db is not None:
        try:
            await _db["dash_auth_requests"].update_one(
                {"_id": req_id},
                {"$set": {
                    "_id": req_id,
                    "telegram_id": body.telegram_id,
                    "otp": otp,
                    "ip": ip,
                    "status": "pending",
                    "created_at": queries.datetime.now(),
                }},
                upsert=True
            )
        except Exception:
            pass

    sent = await auth.send_otp_via_telegram(body.telegram_id, otp, req_id, ip)
    if not sent:
        raise HTTPException(503, "Failed to send OTP — check bot token configuration")

    return {"ok": True, "req_id": req_id, "message": "OTP & Approval buttons sent via Telegram"}


@app.get("/api/auth/check-status")
async def check_auth_status(req_id: str, request: Request, response: Response) -> dict:
    """Poll endpoint to check if login was approved/blocked via Telegram Inline buttons."""
    ip = _get_client_ip(request)

    # Check memory store first for instant response
    status = "pending"
    telegram_id = None

    mem_req = auth.get_auth_request(req_id)
    if mem_req:
        status = mem_req["status"]
        telegram_id = mem_req["telegram_id"]

    # Check MongoDB if still pending or if DB available
    if status == "pending" and _db is not None:
        try:
            req_doc = await _db["dash_auth_requests"].find_one({"_id": req_id})
            if req_doc:
                status = req_doc.get("status", "pending")
                telegram_id = req_doc.get("telegram_id")
                
            blacklisted = await _db["dash_blocked_ips"].find_one({"_id": ip})
            if blacklisted or status == "blocked":
                auth.block_ip(ip, permanent=True)
                return {"ok": False, "status": "blocked", "message": "IP address is blacklisted by admin"}
        except Exception:
            pass

    if status == "approved" and telegram_id:
        token = auth.create_jwt(telegram_id)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
        return {"ok": True, "status": "approved"}
    elif status == "blocked":
        return {"ok": False, "status": "blocked", "message": "IP address is blacklisted by admin"}

    return {"ok": True, "status": "pending"}


@app.post("/api/auth/verify-otp")
@limiter.limit("10/minute")
async def verify_otp(body: OtpVerify, request: Request, response: Response) -> dict:
    ip = _get_client_ip(request)

    if _db is not None:
        try:
            blacklisted = await _db["dash_blocked_ips"].find_one({"_id": ip})
            if blacklisted:
                raise HTTPException(403, "IP address is blacklisted by admin")
        except HTTPException:
            raise
        except Exception:
            pass

    if auth.is_ip_blocked(ip):
        raise HTTPException(429, "IP blocked — too many failed attempts")

    if not auth.check_rate_limit(ip, limit=10, window=60):
        raise HTTPException(429, "Rate limit exceeded")

    success, error, req_id = auth.verify_otp(body.telegram_id, body.otp.strip(), ip)
    if not success:
        raise HTTPException(401, error)

    if _db is not None and req_id:
        try:
            await _db["dash_auth_requests"].update_one(
                {"_id": req_id},
                {"$set": {"status": "approved"}}
            )
        except Exception:
            pass

    token = auth.create_jwt(body.telegram_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )
    return {"ok": True}


@app.post("/api/auth/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


# ── Health check (no auth) ────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# ── Stats endpoints (auth required) ───────────────────────────────────────────

@app.get("/api/stats/overview")
async def stats_overview(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    return await queries.get_overview(db)


@app.get("/api/stats/activity")
async def stats_activity(
    days: int = 30,
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    days = max(7, min(days, 90))
    return await queries.get_activity_chart(db, days)


@app.get("/api/stats/users")
async def stats_users(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    by_lang, top = await asyncio.gather(
        queries.get_users_by_language(db),
        queries.get_top_users(db, limit=20),
    )
    return {"by_language": by_lang, "top_users": top}


@app.get("/api/stats/database")
async def stats_database(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    return await queries.get_database_stats(db)


@app.get("/api/stats/bot")
async def stats_bot(uid: int = Depends(_require_auth)) -> dict[str, Any]:
    return await queries.get_bot_status()


@app.get("/api/stats/parser")
async def stats_parser(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    return await queries.get_parser_status(db)


@app.get("/api/stats/alerts")
async def stats_alerts(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    return await queries.get_alerts_stats(db)


@app.get("/api/stats/groups")
async def stats_groups(
    uid: int = Depends(_require_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    return await queries.get_groups_stats(db)


@app.get("/api/stats/errors")
async def stats_errors(uid: int = Depends(_require_auth)) -> dict[str, Any]:
    return {"errors": queries.get_error_log(lines=100)}


class ConfigUpdateModel(BaseModel):
    section: str
    settings: dict[str, Any]


@app.get("/api/config")
async def config_get(uid: int = Depends(_require_auth)) -> dict[str, Any]:
    return queries.get_config_safe()


@app.post("/api/config/update")
async def config_update_section(
    body: ConfigUpdateModel,
    uid: int = Depends(_require_auth),
) -> dict:
    if body.section == "api_keys" or body.section in ("bot.token", "database.mongo_uri", "security.fernet_key"):
        raise HTTPException(403, "Editing API keys and security tokens via dashboard is restricted")

    ok = queries.update_config_section(body.section, body.settings)
    if not ok:
        raise HTTPException(400, f"Failed to save section '{body.section}'")
    return {"ok": True, "section": body.section, "message": "Configuration saved successfully"}


@app.patch("/api/config/features")
async def config_patch_feature(
    body: FeaturePatch,
    uid: int = Depends(_require_auth),
) -> dict:
    ok = queries.update_config_section("features", {body.feature: body.value})
    if not ok:
        raise HTTPException(400, "Invalid feature key or write error")
    return {"ok": True, "feature": body.feature, "value": body.value}


# ── Actions ────────────────────────────────────────────────────────────────────

@app.post("/api/actions/restart")
async def action_restart(uid: int = Depends(_require_auth)) -> dict:
    """Restart the bot systemd service."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", "finances-bot.service"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise HTTPException(500, f"Restart failed: {result.stderr}")
        return {"ok": True, "message": "Bot restarted successfully"}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Restart command timed out")
    except Exception as e:
        raise HTTPException(500, str(e))
