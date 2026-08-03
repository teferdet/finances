"""
Enhanced Text Processing with better parsing, multi-language jargon/slang support,
multiplier suffix handling, and flexible currency conversion extraction.
"""

import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import json
import os


@dataclass
class ParsedCurrency:
    """Represents a parsed currency from text."""

    code: str
    amount: float
    symbol: Optional[str] = None
    is_crypto: bool = False
    original_text: str = ""
    confidence: float = 1.0
    span: Tuple[int, int] = (0, 0)
    target_currency: Optional[str] = None  # Target currency for conversion requests


class TextProcessing:
    """
    Enhanced text processing for currency extraction.

    Features:
    - Multi-format support (100 USD, $100, 100$, USD 100)
    - Multiplier suffix support (10k, 2.5к, 1m, 5 лямів, 100кк, 10 тис)
    - Slang / jargon & inflections across EN, UK, PL, CS, SK, DE, FR, RU
    - Dynamic currency and cryptocurrency loading from currencies_data.json
    - Unicode word boundary matching for Cyrillic and Latin script
    - Flexible currency conversion request extraction
    - Standalone currency detection (defaults amount to 1.0)
    """

    # Dynamic currency data - loaded from currencies_data.json
    _currencies_data_loaded = False
    _fiat_codes_from_file = set()
    _crypto_codes_from_file = set()
    _alias_map_from_file = {}
    _symbol_map_from_file = {}
    _sorted_aliases_cache = None
    _alias_regex_pattern_cache = None

    # Unicode word boundaries for scripts including Cyrillic & Latin
    BOUND_L = r"(?<![a-zA-Z0-9а-яА-ЯіІїЇєЄґҐ_])"
    BOUND_R = r"(?![a-zA-Z0-9а-яА-ЯіІїЇєЄґҐ_])"

    # Multiplier suffixes mapping
    MULTIPLIER_MAP = {
        # Thousands
        "K": 1_000,
        "К": 1_000,
        "KILO": 1_000,
        "КИЛО": 1_000,
        "ТИС": 1_000,
        "ТИЩ": 1_000,
        "ТЫС": 1_000,
        "ТИСЯЧ": 1_000,
        "ТЫСЯЧ": 1_000,
        "ТИСЯЧІ": 1_000,
        "ТЫСЯЧИ": 1_000,
        # Millions
        "KK": 1_000_000,
        "КК": 1_000_000,
        "M": 1_000_000,
        "М": 1_000_000,
        "МЛН": 1_000_000,
        "ЛЯМ": 1_000_000,
        "ЛЯМИ": 1_000_000,
        "ЛЯМІВ": 1_000_000,
        "ЛЯМІВИ": 1_000_000,
        "ЛЯМОВ": 1_000_000,
        "МІЛЬЙОН": 1_000_000,
        "МІЛЬЙОНИ": 1_000_000,
        "МІЛЬЙОНІВ": 1_000_000,
        "МИЛЛИОН": 1_000_000,
        "МИЛЛИОНЫ": 1_000_000,
        "МИЛЛИОНОВ": 1_000_000,
        # Billions
        "B": 1_000_000_000,
        "Б": 1_000_000_000,
        "МЛРД": 1_000_000_000,
        "МІЛЬЯРД": 1_000_000_000,
        "МІЛЬЯРДИ": 1_000_000_000,
        "МІЛЬЯРДІВ": 1_000_000_000,
        "МИЛЛИАРД": 1_000_000_000,
        "МИЛЛИАРДЫ": 1_000_000_000,
        "МИЛЛИАРДОВ": 1_000_000_000,
    }

    # Regex multiplier suffix group pattern (case-insensitive via re.IGNORECASE)
    MULT_PAT = (
        r"(?:\s*(?:kk|кк|k|к|kilo|кило|тис|тищ|тыс|тисяч|тисячі|тысячи|"
        r"m|м|млн|лям|лями|лямов|ляміви|лямів|мільйон|мільйони|мільйонів|миллион|миллионы|миллионов|"
        r"b|б|млрд|мільярд|мільярди|мільярдів|миллиард|миллиарды|миллиардов))?"
    )

    @classmethod
    def _load_currencies_from_file(cls):
        """Load currency codes and aliases from currencies_data.json."""
        if cls._currencies_data_loaded:
            return

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            path = os.path.join(project_root, "config", "currencies_data.json")

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for currency in data:
                code = currency.get("code", "").upper()
                if code:
                    if code in cls.CRYPTO_CODES or currency.get("is_crypto", False):
                        cls._crypto_codes_from_file.add(code)
                    else:
                        cls._fiat_codes_from_file.add(code)

                    # Add text aliases
                    for alias in currency.get("text", []):
                        alias_clean = alias.strip().upper()
                        if alias_clean:
                            cls._alias_map_from_file[alias_clean] = code

                    # Add symbol mapping
                    symbol = currency.get("symbol", "")
                    if symbol and len(symbol) <= 4:
                        cls._symbol_map_from_file[symbol] = code

            cls._currencies_data_loaded = True
        except Exception as e:
            print(f"Warning: Could not load currencies_data.json: {e}")

    # Fallback hardcoded codes
    FIAT_CODES = {
        "USD",
        "EUR",
        "GBP",
        "UAH",
        "PLN",
        "CZK",
        "CHF",
        "JPY",
        "CNY",
        "CAD",
        "AUD",
        "NZD",
        "SEK",
        "NOK",
        "DKK",
        "RUB",
        "TRY",
        "INR",
        "BRL",
        "MXN",
        "ZAR",
        "SGD",
        "HKD",
        "KRW",
        "THB",
        "IDR",
        "MYR",
        "PHP",
        "VND",
        "EGP",
        "AED",
        "SAR",
        "ILS",
        "RON",
        "BGN",
        "HUF",
        "ISK",
        "ARS",
        "CLP",
        "COP",
        "PEN",
        "TWD",
        "GEL",
        "KZT",
        "MDL",
        "AMD",
        "AZN",
        "BYN",
        "KGS",
        "TJS",
        "TMT",
        "UZS",
        "XOF",
    }

    CRYPTO_CODES = {
        "BTC",
        "ETH",
        "USDT",
        "BNB",
        "SOL",
        "USDC",
        "XRP",
        "DOGE",
        "TON",
        "ADA",
        "AVAX",
        "SHIB",
        "DOT",
        "LINK",
        "TRX",
        "MATIC",
        "LTC",
        "UNI",
    }

    # Symbol to currency mapping (fallback)
    SYMBOL_MAP = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "₴": "UAH",
        "zł": "PLN",
        "Kč": "CZK",
        "¥": "JPY",
        "₿": "BTC",
        "Ξ": "ETH",
        "₾": "GEL",
        "₮": "USDT",
        "Ð": "DOGE",
    }

    # Common Aliases (fallback - file takes priority)
    ALIAS_MAP = {
        # English
        "DOLLAR": "USD",
        "DOLLARS": "USD",
        "BUCKS": "USD",
        "BUCK": "USD",
        "EURO": "EUR",
        "EUROS": "EUR",
        "POUND": "GBP",
        "POUNDS": "GBP",
        "QUID": "GBP",
        "YEN": "JPY",
        "FRANC": "CHF",
        "FRANCS": "CHF",
        "HRYVNIA": "UAH",
        "HRYVNIAS": "UAH",
        "ZLOTY": "PLN",
        "ZLOTYS": "PLN",
        "LARI": "GEL",
        # Ukrainian
        "ДОЛАР": "USD",
        "ДОЛАРИ": "USD",
        "ДОЛАРІВ": "USD",
        "БАКСІВ": "USD",
        "БАКС": "USD",
        "БАКСИ": "USD",
        "ЗЕЛЕНІ": "USD",
        "ЄВРО": "EUR",
        "ГРИВНЯ": "UAH",
        "ГРИВНІ": "UAH",
        "ГРИВЕНЬ": "UAH",
        "ГРН": "UAH",
        "ФУНТ": "GBP",
        "ФУНТІВ": "GBP",
        "ЗЛОТИЙ": "PLN",
        "ЗЛОТИХ": "PLN",
        "ЗЛ": "PLN",
        "ЛАРІ": "GEL",
        "БІТОК": "BTC",
        "БІТКОЇН": "BTC",
        "ЕФІР": "ETH",
        "КЕФІР": "ETH",
        "ТЕЗЕР": "USDT",
        "ЮСДТ": "USDT",
        # Russian
        "ДОЛЛАР": "USD",
        "ДОЛЛАРОВ": "USD",
        "РУБЛЬ": "RUB",
        "РУБЛЕЙ": "RUB",
        "РУБ": "RUB",
        "ЛАРИ": "GEL",
        "БИТОК": "BTC",
        "ЭФИР": "ETH",
    }

    # Conversion keywords
    CONVERSION_KEYWORDS = {"В", "НА", "ДО", "ВІД", "TO", "INTO", "IN", "FOR", "→", "->", "=>", "="}

    def __init__(self, text: str = ""):
        """
        Initialize text processor.

        Args:
            text: Text to process
        """
        self._load_currencies_from_file()

        self.original_text = text
        self.text = text.upper() if text else ""
        self.results: List[ParsedCurrency] = []
        self.codes: List[str] = []
        self._currencies_data: Optional[Dict] = None

        if text:
            self._parse()

    def _load_currencies_data(self) -> Dict:
        """Load currency metadata from JSON file."""
        if self._currencies_data is not None:
            return self._currencies_data

        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "config", "currencies_data.json")

            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                self._currencies_data = {c["code"]: c for c in data}
                return self._currencies_data
        except Exception:
            return {}

    @classmethod
    def _get_sorted_aliases(cls) -> List[Tuple[str, str]]:
        """Get all aliases sorted by length descending to match composite phrases first."""
        if cls._sorted_aliases_cache is not None:
            return cls._sorted_aliases_cache

        all_aliases = cls.ALIAS_MAP.copy()
        if cls._alias_map_from_file:
            all_aliases.update(cls._alias_map_from_file)

        cls._sorted_aliases_cache = sorted(all_aliases.items(), key=lambda x: len(x[0]), reverse=True)
        return cls._sorted_aliases_cache

    @classmethod
    def _get_alias_regex_pattern(cls) -> str:
        """Get combined regex pattern of all aliases for high performance parsing."""
        if cls._alias_regex_pattern_cache is not None:
            return cls._alias_regex_pattern_cache

        aliases = [a for a, c in cls._get_sorted_aliases()]
        cls._alias_regex_pattern_cache = "|".join(re.escape(a) for a in aliases)
        return cls._alias_regex_pattern_cache

    def _is_crypto(self, code: str) -> bool:
        """Check if currency code is a cryptocurrency."""
        code_upper = code.upper()
        return code_upper in self.CRYPTO_CODES or code_upper in self._crypto_codes_from_file

    def _parse(self) -> None:
        """Parse text and extract currencies."""
        # First try to detect conversion requests ("10k баксів в грн", "100 USD to UAH")
        self._parse_conversion_request()

        # If no conversion found, try standard parsing
        if not self.results:
            self._parse_code_amount()
            self._parse_symbol_amount()
            self._parse_amount_code()
            self._parse_alias_amount()
            self._parse_standalone_codes()
            self._parse_standalone_aliases()

        # Deduplicate results based on span and code
        unique_results = {}
        for res in self.results:
            key = (res.span, res.code)
            if key not in unique_results:
                unique_results[key] = res

        self.results = list(unique_results.values())
        self.codes = list(set(r.code for r in self.results))

    def _resolve_currency(self, text: str) -> Optional[str]:
        """Resolve currency code from text (code, symbol, or alias)."""
        if not text:
            return None
        text_clean = text.strip()
        text_upper = text_clean.upper()

        # Check fallback symbols first for core symbols ($ -> USD, € -> EUR, etc.)
        if text_clean in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[text_clean]

        # Check dynamic codes from file
        if text_upper in self._fiat_codes_from_file or text_upper in self._crypto_codes_from_file:
            return text_upper

        # Check direct fallback codes
        if text_upper in self.FIAT_CODES or text_upper in self.CRYPTO_CODES:
            return text_upper

        # Check dynamic aliases from file
        if self._alias_map_from_file and text_upper in self._alias_map_from_file:
            return self._alias_map_from_file[text_upper]

        # Check fallback aliases
        if text_upper in self.ALIAS_MAP:
            return self.ALIAS_MAP[text_upper]

        # Check dynamic symbols from file
        if self._symbol_map_from_file and text_clean in self._symbol_map_from_file:
            return self._symbol_map_from_file[text_clean]

        return None

    def _parse_conversion_request(self) -> None:
        """
        Parse conversion requests like:
        - "100 USD to UAH" / "100 USD в UAH"
        - "10k баксів в грн" / "5 лямів євро -> $"
        - "100$ -> ₴" / "100$ в євро"
        - "скільки буде 100 EUR в гривнях"
        - "конвертувати 50$ в євро"
        """
        text = self.text
        original = self.original_text

        KEYWORD_PAT = r"(?:(?<![a-zA-Z0-9а-яА-ЯіІїЇєЄґҐ_])(?:В|НА|ДО|ВІД|TO|INTO|IN|FOR)|→|->|=>|=)"

        # Patterns for conversion requests
        conversion_patterns = [
            # Amount + Currency/Alias + Keyword + Target Currency/Alias
            r"(\d[\d,.]*"
            + self.MULT_PAT
            + r")\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)\s*"
            + KEYWORD_PAT
            + r"\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)",
            # "скільки буде 100 USD в UAH"
            r"(?:СКІЛЬКИ|СКОЛЬКО|HOW\s+MUCH)(?:\s+БУДЕ|\s+БУДЕТ|\s+IS)?\s*(\d[\d,.]*"
            + self.MULT_PAT
            + r")\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)\s*"
            + KEYWORD_PAT
            + r"\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)",
            # "конвертувати 100 USD в UAH"
            r"(?:КОНВЕРТ|CONVERT|ОБМІН|ОБМЕН|CHANGE)(?:\w*)\s*(\d[\d,.]*"
            + self.MULT_PAT
            + r")\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)\s*"
            + KEYWORD_PAT
            + r"\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)",
            # Symbol before amount: "$100 to UAH", "$10k in EUR"
            r"([$€£₴¥₿])\s*(\d[\d,.]*"
            + self.MULT_PAT
            + r")\s*"
            + KEYWORD_PAT
            + r"\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿a-zA-Zа-яА-ЯіІїЇєЄґҐ]+)",
        ]

        for pattern in conversion_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                if len(groups) == 3:
                    if groups[0] in self.SYMBOL_MAP:
                        # Symbol before amount
                        source_code = self.SYMBOL_MAP[groups[0]]
                        amount = self._parse_number(groups[1])
                        target_text = groups[2]
                    else:
                        amount = self._parse_number(groups[0])
                        source_text = groups[1]
                        target_text = groups[2]
                        source_code = self._resolve_currency(source_text)

                    if amount is None or amount <= 0:
                        continue

                    target_code = self._resolve_currency(target_text)

                    if source_code and target_code and source_code != target_code:
                        self.results.append(
                            ParsedCurrency(
                                code=source_code,
                                amount=amount,
                                is_crypto=self._is_crypto(source_code),
                                original_text=match.group(0),
                                span=match.span(),
                                confidence=0.95,
                                target_currency=target_code,
                            )
                        )
                        return  # Found a conversion, stop looking

        # Arrow patterns with symbols ("100$ → ₴" or "$100 -> €")
        arrow_patterns = [
            r"([$€£₴¥₿]?)(\d[\d,.]*" + self.MULT_PAT + r")([$€£₴¥₿]?)\s*(?:→|->|=>|=)\s*([$€£₴¥₿])",
        ]

        for pattern in arrow_patterns:
            matches = re.finditer(pattern, original, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                pre_symbol, amount_str, post_symbol, target_symbol = groups

                source_symbol = pre_symbol if pre_symbol else post_symbol
                if not source_symbol or source_symbol not in self.SYMBOL_MAP:
                    continue
                if target_symbol not in self.SYMBOL_MAP:
                    continue

                amount = self._parse_number(amount_str)
                if amount is None or amount <= 0:
                    continue

                source_code = self.SYMBOL_MAP[source_symbol]
                target_code = self.SYMBOL_MAP[target_symbol]

                if source_code != target_code:
                    self.results.append(
                        ParsedCurrency(
                            code=source_code,
                            amount=amount,
                            symbol=source_symbol,
                            is_crypto=self._is_crypto(source_code),
                            original_text=match.group(0),
                            span=match.span(),
                            confidence=0.9,
                            target_currency=target_code,
                        )
                    )
                    return

    def has_conversion_target(self) -> bool:
        """Check if any parsed currency has a conversion target."""
        return any(r.target_currency is not None for r in self.results)

    def get_conversion_pair(self) -> Optional[Tuple[str, str, float]]:
        """
        Get the first conversion pair if available.

        Returns:
            Tuple of (source_code, target_code, amount) or None
        """
        for result in self.results:
            if result.target_currency:
                return (result.code, result.target_currency, result.amount)
        return None

    def _parse_number(self, text: str) -> Optional[float]:
        """Parse a number from various formats, supporting multiplier suffixes (k, m, b, лям, млн, etc.)."""
        if not text:
            return None
        text_clean = text.strip()
        text_upper = text_clean.upper()

        multiplier = 1.0
        # Check multiplier suffix sorted by length descending
        for suffix, mult in sorted(self.MULTIPLIER_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if text_upper.endswith(suffix):
                prefix = text_clean[: -len(suffix)].strip()
                if prefix and any(c.isdigit() for c in prefix):
                    multiplier = mult
                    text_clean = prefix
                    break

        # Remove spaces in numeric part
        text_clean = text_clean.replace(" ", "")

        # Determine decimal/thousand separator (1,234.56 vs 1.234,56)
        if "," in text_clean and "." in text_clean:
            if text_clean.rfind(",") > text_clean.rfind("."):
                text_clean = text_clean.replace(".", "").replace(",", ".")
            else:
                text_clean = text_clean.replace(",", "")
        elif "," in text_clean:
            parts = text_clean.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                text_clean = text_clean.replace(",", ".")
            else:
                text_clean = text_clean.replace(",", "")

        try:
            val = float(text_clean)
            return val * multiplier
        except ValueError:
            return None

    def _parse_code_amount(self) -> None:
        """Parse patterns like 'USD 100' or 'USD 10k'."""
        pattern = r"([A-Z]{3})\s*(\d[\d,.]*" + self.MULT_PAT + r")"

        for match in re.finditer(pattern, self.text, re.IGNORECASE):
            code = match.group(1).upper()
            amount_str = match.group(2)

            if self._is_valid_currency(code):
                amount = self._parse_number(amount_str)
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )

    def _parse_amount_code(self) -> None:
        """Parse patterns like '100 USD' or '10k USD'."""
        pattern = self.BOUND_L + r"(\d[\d,.]*" + self.MULT_PAT + r")\s*([A-Z]{3})" + self.BOUND_R

        for match in re.finditer(pattern, self.text, re.IGNORECASE):
            amount_str = match.group(1)
            code = match.group(2).upper()

            if self._is_valid_currency(code):
                amount = self._parse_number(amount_str)
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )

    def _parse_symbol_amount(self) -> None:
        """Parse patterns like '$100', '€50', '$10k'."""
        for symbol, code in self.SYMBOL_MAP.items():
            # Symbol before amount: $100
            pattern1 = re.escape(symbol) + r"\s*(\d[\d,.]*" + self.MULT_PAT + r")"
            for match in re.finditer(pattern1, self.original_text, re.IGNORECASE):
                amount = self._parse_number(match.group(1))
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            symbol=symbol,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )

            # Symbol after amount: 100$
            pattern2 = r"(\d[\d,.]*" + self.MULT_PAT + r")\s*" + re.escape(symbol)
            for match in re.finditer(pattern2, self.original_text, re.IGNORECASE):
                amount = self._parse_number(match.group(1))
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            symbol=symbol,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )

    def _parse_alias_amount(self) -> None:
        """Parse aliases like '100 dollars', '10k баксів', '5 лямів євро'."""
        matched_spans = [r.span for r in self.results]
        alias_pattern = self._get_alias_regex_pattern()

        # Amount before alias: 100 dollars, 10k баксів
        pattern1 = (
            self.BOUND_L
            + r"(\d[\d,.]*"
            + self.MULT_PAT
            + r")\s*"
            + self.BOUND_L
            + r"("
            + alias_pattern
            + r")"
            + self.BOUND_R
        )
        for match in re.finditer(pattern1, self.text, re.IGNORECASE):
            span = match.span()
            if any(max(span[0], s[0]) < min(span[1], s[1]) for s in matched_spans):
                continue

            amount_str = match.group(1)
            alias_matched = match.group(2)
            code = self._resolve_currency(alias_matched)
            if code:
                amount = self._parse_number(amount_str)
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    matched_spans.append(span)

        # Alias before amount: dollars 100
        pattern2 = (
            self.BOUND_L
            + r"("
            + alias_pattern
            + r")"
            + self.BOUND_R
            + r"\s*(\d[\d,.]*"
            + self.MULT_PAT
            + r")"
            + self.BOUND_R
        )
        for match in re.finditer(pattern2, self.text, re.IGNORECASE):
            span = match.span()
            if any(max(span[0], s[0]) < min(span[1], s[1]) for s in matched_spans):
                continue

            alias_matched = match.group(1)
            amount_str = match.group(2)
            code = self._resolve_currency(alias_matched)
            if code:
                amount = self._parse_number(amount_str)
                if amount is not None and amount > 0:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    matched_spans.append(span)

    def _parse_standalone_aliases(self) -> None:
        """Parse standalone aliases like 'dollar', 'бакси', 'євро' (default to 1.0)."""
        existing_spans = [r.span for r in self.results]
        alias_pattern = self._get_alias_regex_pattern()
        pattern = self.BOUND_L + r"(" + alias_pattern + r")" + self.BOUND_R

        for match in re.finditer(pattern, self.text, re.IGNORECASE):
            span = match.span()
            is_overlap = any(max(span[0], s[0]) < min(span[1], s[1]) for s in existing_spans)

            if not is_overlap:
                alias_matched = match.group(1)
                code = self._resolve_currency(alias_matched)
                if code:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=1.0,
                            is_crypto=self._is_crypto(code),
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    existing_spans.append(span)

    def _parse_standalone_codes(self) -> None:
        """Parse standalone codes like 'EUR' (default to 1.0)."""
        existing_spans = [r.span for r in self.results]
        pattern = self.BOUND_L + r"([A-Z]{3})" + self.BOUND_R

        for match in re.finditer(pattern, self.text, re.IGNORECASE):
            code = match.group(1).upper()
            span = match.span()

            is_overlap = any(max(span[0], s[0]) < min(span[1], s[1]) for s in existing_spans)

            if not is_overlap and self._is_valid_currency(code):
                self.results.append(
                    ParsedCurrency(
                        code=code,
                        amount=1.0,
                        is_crypto=self._is_crypto(code),
                        original_text=match.group(0),
                        span=span,
                    )
                )
                existing_spans.append(span)

    def _is_valid_currency(self, code: str) -> bool:
        """Check if code is a valid currency."""
        code_upper = code.upper()
        if self._fiat_codes_from_file and code_upper in self._fiat_codes_from_file:
            return True
        if self._crypto_codes_from_file and code_upper in self._crypto_codes_from_file:
            return True
        return code_upper in self.FIAT_CODES or code_upper in self.CRYPTO_CODES

    def get_results(self) -> List[Tuple[str, float]]:
        """
        Get parsed results in legacy format.

        Returns:
            List of (code, amount) tuples
        """
        return [(r.code, r.amount) for r in self.results]

    def get_codes(self) -> List[str]:
        """Get list of currency codes found."""
        return self.codes

    def get_parsed_currencies(self) -> List[ParsedCurrency]:
        """Get list of parsed currency objects."""
        return self.results

    def has_crypto(self) -> bool:
        """Check if any cryptocurrency was found."""
        return any(r.is_crypto for r in self.results)

    def has_fiat(self) -> bool:
        """Check if any fiat currency was found."""
        return any(not r.is_crypto for r in self.results)

    def get_total_by_currency(self) -> Dict[str, float]:
        """Get total amounts grouped by currency."""
        totals = {}
        for result in self.results:
            if result.code in totals:
                totals[result.code] += result.amount
            else:
                totals[result.code] = result.amount
        return totals

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate parsed results.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.results:
            return False, "No currencies found in text"

        for result in self.results:
            if result.amount <= 0:
                return False, f"Invalid amount for {result.code}: {result.amount}"
            if result.amount > 1e15:
                return False, f"Amount too large for {result.code}: {result.amount}"

        return True, None

    def format_for_display(self) -> str:
        """Format results for user display."""
        if not self.results:
            return ""

        currencies_data = self._load_currencies_data()
        parts = []

        for result in self.results:
            info = currencies_data.get(result.code, {})
            emoji = info.get("emoji", "💰")
            symbol = info.get("symbol", "")

            parts.append(f"{emoji} {result.code} {result.amount}{symbol}")

        return ", ".join(parts)


class TextValidator:
    """Utility class for text validation."""

    @staticmethod
    def is_valid_currency_code(code: str) -> bool:
        """Check if code is a valid currency code."""
        return code.upper() in TextProcessing.FIAT_CODES | TextProcessing.CRYPTO_CODES

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input."""
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        text = text[:500]
        return text.strip()

    @staticmethod
    def extract_command(text: str) -> Tuple[Optional[str], str]:
        """Extract bot command from text."""
        match = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)", text, re.DOTALL)
        if match:
            return match.group(1).lower(), match.group(2).strip()
        return None, text


def strip_html(text: str) -> str:
    """Remove HTML tags from text for plain-text contexts like Telegram callback alerts."""
    if not text:
        return ""
    return re.sub(r"<[^>]*>", "", text)
