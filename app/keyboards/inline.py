"""
Inline keyboards used across handlers.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import get_settings
from app.i18n import I18n


# ── Exchange Rate ───────────────────────────────────────────────────


def er_keypad(
    i18n: I18n,
    lang: str,
    currency: str,
    amount: float,
    index: int,
) -> InlineKeyboardMarkup:
    if index == 0:
        text = i18n.get("keyboard.direct_rate", lang) or "🔄 Прямий курс"
    else:
        text = i18n.get("keyboard.reverse_rate", lang) or "🔄 Зворотній курс"
    cb = f"er {currency} {amount} {index}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=cb)]])


def crypto_keypad(amount: float, active_currency: str = "USD") -> InlineKeyboardMarkup:
    currencies = [("USD", "$"), ("GBP", "£"), ("EUR", "€"), ("UAH", "₴"), ("PLN", "zł"), ("CZK", "Kč")]

    buttons = []
    for code, symbol in currencies:
        if code != active_currency:
            buttons.append(InlineKeyboardButton(text=symbol, callback_data=f"crypto {code} {amount}"))

    # We expect 5 buttons. Let's group them 3 in first row, 2 in second
    inline_keyboard = []
    if len(buttons) >= 3:
        inline_keyboard.append(buttons[:3])
        inline_keyboard.append(buttons[3:])
    else:
        inline_keyboard.append(buttons)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# ── Settings ────────────────────────────────────────────────────────


def settings_menu(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    s = i18n.get_section("keyboard.settings", lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=s.get("fiat", "💶 Fiat"), callback_data="fiat"),
                InlineKeyboardButton(text=s.get("crypto", "💵 Crypto"), callback_data="settings_crypto"),
            ],
            [
                InlineKeyboardButton(text=s.get("stocks", "📑 Stocks"), callback_data="stocks"),
                InlineKeyboardButton(text=s.get("main_menu", "📱 Main Menu"), callback_data="settings_main_menu"),
            ],
            [
                InlineKeyboardButton(
                    text=s.get("base_currency", "💱 Default Currency"), callback_data="settings_base_currency"
                ),
                InlineKeyboardButton(text=s.get("big_buttons", "📏 Big Buttons"), callback_data="toggle_big_buttons"),
            ],
            [
                InlineKeyboardButton(text=s.get("groups", "👥 Groups"), callback_data="groups"),
                InlineKeyboardButton(text=s.get("language", "🌐 Language"), callback_data="settings_language"),
            ],
            [
                InlineKeyboardButton(text=s.get("my_data", "📋 My Data"), callback_data="my_data_view"),
                InlineKeyboardButton(text=s.get("about", "ℹ️ About"), callback_data="about"),
            ],
        ]
    )


def back_button(i18n: I18n, lang: str, callback: str = "menu") -> InlineKeyboardMarkup:
    text = i18n.get("keyboard.settings.back", lang) or "◀️ Back"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback)]])


def about_keyboard(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    text_back = i18n.get("keyboard.settings.back", lang) or "◀️ Back"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="GitHub Repository", url="https://github.com/teferdet/finances")],
            [InlineKeyboardButton(text=text_back, callback_data="menu")],
        ]
    )


# ── Donate ──────────────────────────────────────────────────────────


def donate_keyboard() -> InlineKeyboardMarkup:
    s = get_settings().urls
    rows = []
    btns = []
    if s.buymeacoffee:
        btns.append(InlineKeyboardButton(text="☕️ Buy me a coffee", url=s.buymeacoffee))
    if s.donatello:
        btns.append(InlineKeyboardButton(text="❤️ Donatello", url=s.donatello))
    if btns:
        rows.append(btns)
    if s.bank:
        rows.append([InlineKeyboardButton(text="💳 Google Pay / Apple Pay", url=s.bank)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Help ────────────────────────────────────────────────────────────


def help_keyboard(i18n: I18n, lang: str, show_qa: bool = True) -> InlineKeyboardMarkup:
    h = i18n.get_section("keyboard.help", lang)
    s = get_settings().urls
    rows = []
    if show_qa:
        rows.append([InlineKeyboardButton(text=h.get("q&a", "💬 Q&A"), callback_data="q&a")])
    if s.communication:
        rows.append([InlineKeyboardButton(text=h.get("communication", "🔗 Contact"), url=s.communication)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Language ────────────────────────────────────────────────────────

LANGUAGE_INFO = {
    "en": {"flag": "🇬🇧", "native": "English"},
    "uk": {"flag": "🇺🇦", "native": "Українська"},
    "pl": {"flag": "🇵🇱", "native": "Polski"},
    "cs": {"flag": "🇨🇿", "native": "Čeština"},
    "sk": {"flag": "🇸🇰", "native": "Slovenčina"},
    "de": {"flag": "🇩🇪", "native": "Deutsch"},
    "fr": {"flag": "🇫🇷", "native": "Français"},
}


def language_keyboard(supported: list[str], back_cb: str = "lang_cancel") -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for code in supported:
        info = LANGUAGE_INFO.get(code, {"flag": "", "native": code})
        row.append(
            InlineKeyboardButton(
                text=f"{info['flag']} {info['native']}",
                callback_data=f"lang_set_{code}",
            )
        )
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Back", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Groups ──────────────────────────────────────────────────────────


def group_delete_kb(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    text = i18n.get("keyboard.delete", lang) or "🗑 Delete"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="delete")]])


def user_groups_list_kb(groups: list[dict], bot_username: str, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for g in groups:
        title = g.get("title", f"Group {g.get('id')}")
        builder.row(InlineKeyboardButton(text=title, callback_data=f"user_group:{g.get('id')}"))
        
    ug_text = i18n.get_section("settings.user_groups", lang)
    add_group_text = ug_text.get("add_group_btn", "➕ Add group")
    builder.row(InlineKeyboardButton(text=add_group_text, url=f"https://t.me/{bot_username}?startgroup=botstart"))
        
    back_text = i18n.get("keyboard.settings.back", lang) or "◀️ Back"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="menu"))
    return builder.as_markup()


def user_group_settings_kb(chat_id: int, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    s = i18n.get_section("keyboard.settings", lang)
    ug_text = i18n.get_section("settings.user_groups", lang)
    in_text = s.get("input_currencies", "📥 Input Currencies")
    out_text = s.get("output_currencies", "📤 Output Currencies")
    delete_text = ug_text.get("delete_btn", "🗑 Remove Group")
    back_text = s.get("back", "◀️ Back")
    
    builder.row(InlineKeyboardButton(text=in_text, callback_data=f"user_group:input:{chat_id}"))
    builder.row(InlineKeyboardButton(text=out_text, callback_data=f"user_group:output:{chat_id}"))
    builder.row(InlineKeyboardButton(text=delete_text, callback_data=f"user_group:delete:{chat_id}"))
    builder.row(InlineKeyboardButton(text=back_text, callback_data="groups"))
    
    return builder.as_markup()


def user_group_delete_confirm_kb(chat_id: int, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    confirm_text = str(i18n.get("keyboard.settings.confirm", lang) or "✅ Confirm")
    back_text = str(i18n.get("keyboard.settings.back", lang) or "◀️ Back")

    builder.row(
        InlineKeyboardButton(text=confirm_text, callback_data=f"user_group:confirm_delete:{chat_id}"),
        InlineKeyboardButton(text=back_text, callback_data=f"user_group:{chat_id}"),
    )
    return builder.as_markup()


# ── Paginated Currency Selector ─────────────────────────────────────


def paginated_currency_keyboard(
    currencies_data: list[dict],
    page: int,
    prefix: str,  # "Output", "Input", "MainMenu", etc.
    i18n: I18n,
    lang: str,
    page_size: int = 15,
    selected: list[str] | None = None,
) -> InlineKeyboardMarkup:
    """Generic paginated currency selector used by settings handlers."""
    if selected is None:
        selected = []
    s = i18n.get_section("keyboard.settings", lang)
    start = page * page_size
    end = min(start + page_size, len(currencies_data))
    page_items = currencies_data[start:end]

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for item in page_items:
        code = item.get("code", "")
        emoji = item.get("emoji", "")
        mark = "✅ " if code in selected else ""
        row.append(
            InlineKeyboardButton(
                text=f"{mark}{emoji} {code}".strip(),
                callback_data=f"{prefix} {code}",
            )
        )
        if len(row) >= 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Navigation
    nav: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text=s.get("save", "💾 Save"), callback_data=f"{prefix} save")
    ]
    if page > 0:
        nav.insert(
            0,
            InlineKeyboardButton(
                text=s.get("back list", "◀️"),
                callback_data=f"{prefix} position {page - 1}",
            ),
        )
    if end < len(currencies_data):
        nav.append(
            InlineKeyboardButton(
                text=s.get("next list", "▶️"),
                callback_data=f"{prefix} position {page + 1}",
            )
        )
    rows.append(nav)

    # Back
    rows.append(
        [
            InlineKeyboardButton(
                text=s.get("back", "◀️ Back"),
                callback_data=f"{prefix} cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
