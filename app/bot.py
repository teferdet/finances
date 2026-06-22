"""
Bot + Dispatcher factory — creates and wires everything together.
"""
from __future__ import annotations
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import get_settings
from app.middlewares.i18n import I18nMiddleware
from app.middlewares.throttle import ThrottleMiddleware
from app.middlewares.error import ErrorMiddleware
from app.handlers import start, exchange, exchange_api, crypto, stocks, settings, language, admin, groups, portfolio, inline_query, portability, alerts, my_data
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
    dp.message.outer_middleware(ErrorMiddleware())
    dp.callback_query.outer_middleware(ErrorMiddleware())
    dp.inline_query.outer_middleware(ErrorMiddleware())
    dp.message.outer_middleware(ThrottleMiddleware())
    dp.message.outer_middleware(I18nMiddleware())
    dp.callback_query.outer_middleware(I18nMiddleware())
    dp.inline_query.outer_middleware(I18nMiddleware())

    # Register routers (order matters — first match wins)
    dp.include_router(start.router)
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
    dp.include_router(groups.router)
    dp.include_router(inline_query.router)

    log.info("Dispatcher configured with %d routers", len(dp.sub_routers))
    return dp
