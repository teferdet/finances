"""
Bot + Dispatcher factory — creates and wires everything together.
"""

from __future__ import annotations
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import get_settings
from app.middlewares.i18n import I18nMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.error import ErrorMiddleware
from app.handlers import (
    start,
    exchange,
    exchange_api,
    crypto,
    stocks,
    settings,
    language,
    admin,
    groups,
    portfolio,
    inline_query,
    portability,
    alerts,
    my_data,
    admin_groups,
    guest,
)
from app.logger import get_logger

log = get_logger("bot")


def create_bot() -> Bot:
    s = get_settings()
    return Bot(
        token=s.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Register middlewares (outer → runs for every update type)
    s = get_settings()

    dp.message.outer_middleware(ErrorMiddleware())
    dp.callback_query.outer_middleware(ErrorMiddleware())
    dp.inline_query.outer_middleware(ErrorMiddleware())
    dp.my_chat_member.outer_middleware(ErrorMiddleware())

    dp.message.outer_middleware(I18nMiddleware())
    dp.callback_query.outer_middleware(I18nMiddleware())
    dp.inline_query.outer_middleware(I18nMiddleware())
    dp.my_chat_member.outer_middleware(I18nMiddleware())

    rate_limit = RateLimitMiddleware(
        limit=s.security.rate_limit_requests,
        window=s.security.rate_limit_window_sec,
        admin_ids=s.bot.admin_ids,
    )
    dp.message.outer_middleware(rate_limit)
    dp.callback_query.outer_middleware(rate_limit)

    # Register routers (order matters — first match wins)
    dp.include_router(start.router)
    dp.include_router(admin_groups.router)
    dp.include_router(admin.router)
    dp.include_router(language.router)
    dp.include_router(crypto.router)
    dp.include_router(stocks.router)
    dp.include_router(settings.router)
    dp.include_router(portfolio.router)
    dp.include_router(exchange_api.router)
    dp.include_router(alerts.router)
    dp.include_router(my_data.router)
    dp.include_router(portability.router)
    dp.include_router(exchange.router)
    dp.include_router(guest.router)  # Handles guest_message mentions
    dp.include_router(groups.router)
    dp.include_router(inline_query.router)

    log.info("Dispatcher configured with %d routers", len(dp.sub_routers))
    return dp
