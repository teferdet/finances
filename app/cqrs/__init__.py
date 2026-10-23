"""
CQRS layer for the finances bot.

Layout:
    bus.py          — Live: in-process event bus (UserChanged, PricesUpdated, FiatUpdated)
    interceptor.py  — Write side: DB proxy that turns every write into a domain event
    write/          — Write side: write-behind buffers (activity tracking)
    read/           — Read side: cached read models (UserView, PriceSnapshot, FiatRates)
    tasks.py        — Tasks: background task supervisor + safe fire-and-forget spawn
    resilience.py   — Failures: transient retry, circuit breaker

Mongo schema is unchanged — this is purely an access-layer optimisation.
"""
