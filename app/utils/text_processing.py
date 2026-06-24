"""
Enhanced Text Processing with better parsing and validation.
Supports more currency formats and provides detailed extraction.
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
    - Cryptocurrency detection
    - Validation against known currencies
    - Fuzzy matching for currency names
    - Number format handling (1,000.00, 1.000,00)
    - Standalone currency codes (defaults to 1.0)
    """

    # Dynamic currency data - loaded from currencies_data.json
    _currencies_data_loaded = False
    _fiat_codes_from_file = set()
    _alias_map_from_file = {}
    _symbol_map_from_file = {}

    @classmethod
    def _load_currencies_from_file(cls):
        """Load currency codes and aliases from currencies_data.json."""
        if cls._currencies_data_loaded:
            return

        try:
            # From app/utils -> app -> project_root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            path = os.path.join(project_root, "config", "currencies_data.json")

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for currency in data:
                code = currency.get("code", "").upper()
                if code:
                    cls._fiat_codes_from_file.add(code)

                    # Add text aliases
                    for alias in currency.get("text", []):
                        cls._alias_map_from_file[alias.upper()] = code

                    # Add symbol mapping
                    symbol = currency.get("symbol", "")
                    if symbol and len(symbol) <= 3:
                        cls._symbol_map_from_file[symbol] = code

            cls._currencies_data_loaded = True
        except Exception as e:
            print(f"Warning: Could not load currencies_data.json: {e}")

    # Fallback hardcoded codes (used if file not loaded)
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
<<<<<<< HEAD
=======

>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        # Ukrainian
        "ДОЛАР": "USD",
        "ДОЛАРИ": "USD",
        "ДОЛАРІВ": "USD",
        "БАКСІВ": "USD",
        "БАКС": "USD",
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
<<<<<<< HEAD
=======

>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        # Russian
        "ДОЛЛАР": "USD",
        "ДОЛЛАРОВ": "USD",
        "РУБЛЬ": "RUB",
        "РУБЛЕЙ": "RUB",
        "РУБ": "RUB",
        "ЛАРИ": "GEL",
    }

    # Conversion keywords (triggers conversion detection)
    CONVERSION_KEYWORDS = {
        # Ukrainian
<<<<<<< HEAD
        "В",
        "НА",
        "ДО",
        # English
        "TO",
        "INTO",
        "IN",
=======
        "В", "НА", "ДО",
        # English
        "TO", "INTO", "IN",
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        # Symbols
        "→",
        "->",
        "=>",
    }

    # Number parsing patterns
    NUMBER_PATTERNS = [
        r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)",  # 1,000.50
        r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)",  # 1.000,50 (European)
        r"(\d+(?:\.\d+)?)",  # 1000.50
        r"(\d+(?:,\d+)?)",  # 1000,50
    ]

    def __init__(self, text: str = ""):
        """
        Initialize text processor.

        Args:
            text: Text to process
        """
        # Load currencies from file on first use
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
            # From app/utils -> app -> project_root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "config", "currencies_data.json")

            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                self._currencies_data = {c["code"]: c for c in data}
                return self._currencies_data
        except Exception:
            return {}

    def _parse(self) -> None:
        """Parse text and extract currencies."""
        # First try to detect conversion requests ("100 USD to UAH")
        self._parse_conversion_request()

        # If no conversion found, try standard parsing
        if not self.results:
            self._parse_code_amount()
            self._parse_symbol_amount()
            self._parse_amount_code()

            # Parse aliases (e.g., "100 dollars")
            self._parse_alias_amount()

            # Catch standalone codes (e.g., "USD")
            self._parse_standalone_codes()

            # Catch standalone aliases (e.g., "dollar")
            self._parse_standalone_aliases()

        # Deduplicate results based on span and code
        unique_results = {}
        for res in self.results:
            key = (res.span, res.code)
            # If overlap with existing better confidence match, skip?
            # For now just strict deduplication
            if key not in unique_results:
                unique_results[key] = res

        self.results = list(unique_results.values())

        # Populate codes list
        self.codes = list(set(r.code for r in self.results))

    def _resolve_currency(self, text: str) -> Optional[str]:
        """Resolve currency code from text (code, symbol, or alias)."""
        text_upper = text.upper().strip()

        # Check dynamic fiat codes from file first
        if self._fiat_codes_from_file and text_upper in self._fiat_codes_from_file:
            return text_upper

        # Check if it's a direct code (fallback)
        if text_upper in self.FIAT_CODES or text_upper in self.CRYPTO_CODES:
            return text_upper

        # Check dynamic aliases from file first
        if self._alias_map_from_file and text_upper in self._alias_map_from_file:
            return self._alias_map_from_file[text_upper]

        # Check fallback aliases
        if text_upper in self.ALIAS_MAP:
            return self.ALIAS_MAP[text_upper]

        # Check dynamic symbols from file
        if self._symbol_map_from_file and text in self._symbol_map_from_file:
            return self._symbol_map_from_file[text]

        # Check fallback symbols
        if text in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[text]

        return None

    def _parse_conversion_request(self) -> None:
        """
        Parse conversion requests like:
        - "100 USD to UAH" / "100 USD в UAH"
        - "100 долларів в гривні"
        - "скільки буде 100 EUR в гривнях"
        - "конвертувати 50$ в євро"
        - "50€ -> ₴"
        """
        text = self.text
        original = self.original_text

        # Patterns for conversion requests
        conversion_patterns = [
            # Amount + Currency + keyword + Target Currency
            # "100 USD to UAH", "100 долларів в гривні"
            r"(\d+(?:[,.\s]\d+)?)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)\s*(?:В|НА|ДО|TO|INTO|IN|→|->|=>)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",
<<<<<<< HEAD
            # "скільки буде 100 USD в UAH" / "сколько будет 100 долларов в гривнах"
            r"(?:СКІЛЬКИ|СКОЛЬКО|HOW\s+MUCH)(?:\s+БУДЕ|\s+БУДЕТ|\s+IS)?\s*(\d+(?:[,.\s]\d+)?)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)\s*(?:В|НА|ДО|TO|INTO|IN)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",
            # "конвертувати 100 USD в UAH" / "обменять 100 долларов на гривны"
            r"(?:КОНВЕРТ|CONVERT|ОБМІН|ОБМЕН|CHANGE)(?:\w*)\s*(\d+(?:[,.\s]\d+)?)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)\s*(?:В|НА|ДО|TO|INTO|IN)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",
=======

            # "скільки буде 100 USD в UAH" / "сколько будет 100 долларов в гривнах"
            r"(?:СКІЛЬКИ|СКОЛЬКО|HOW\s+MUCH)(?:\s+БУДЕ|\s+БУДЕТ|\s+IS)?\s*(\d+(?:[,.\s]\d+)?)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)\s*(?:В|НА|ДО|TO|INTO|IN)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",

            # "конвертувати 100 USD в UAH" / "обменять 100 долларов на гривны"
            r"(?:КОНВЕРТ|CONVERT|ОБМІН|ОБМЕН|CHANGE)(?:\w*)\s*(\d+(?:[,.\s]\d+)?)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)\s*(?:В|НА|ДО|TO|INTO|IN)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",

>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
            # Symbol before amount: "$100 to UAH"
            r"([$€£₴¥₿])\s*(\d+(?:[,.\s]\d+)?)\s*(?:В|НА|ДО|TO|INTO|IN|→|->|=>)\s*([A-ZА-ЯІЇЄҐ$€£₴¥₿]+)",
        ]

        for pattern in conversion_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                # Handle different group configurations
                if len(groups) == 3:
                    # Check if first group is a symbol (like $)
                    if groups[0] in self.SYMBOL_MAP:
                        # Pattern: symbol, amount, target
                        source_code = self.SYMBOL_MAP[groups[0]]
                        amount = self._parse_number(groups[1])
                        target_text = groups[2]
                    else:
                        # Pattern: amount, source, target
                        amount = self._parse_number(groups[0])
                        source_text = groups[1]
                        target_text = groups[2]
                        source_code = self._resolve_currency(source_text)

                    if amount is None:
                        continue

                    target_code = self._resolve_currency(target_text)

                    if source_code and target_code and source_code != target_code:
                        self.results.append(
                            ParsedCurrency(
                                code=source_code,
                                amount=amount,
                                is_crypto=source_code in self.CRYPTO_CODES,
                                original_text=match.group(0),
                                span=match.span(),
                                confidence=0.95,
                                target_currency=target_code,
                            )
                        )
                        return  # Found a conversion, stop looking

        # Also check for simple arrow patterns with symbols
        arrow_patterns = [
            # "100$ → ₴" or "$100 -> €"
            r"([$€£₴¥₿]?)(\d+(?:[,.\s]\d+)?)([$€£₴¥₿]?)\s*(?:→|->|=>|=)\s*([$€£₴¥₿])",
        ]

        for pattern in arrow_patterns:
            matches = re.finditer(pattern, original)
            for match in matches:
                groups = match.groups()
                pre_symbol, amount_str, post_symbol, target_symbol = groups

                # Determine source currency from pre or post symbol
                source_symbol = pre_symbol if pre_symbol else post_symbol
                if not source_symbol or source_symbol not in self.SYMBOL_MAP:
                    continue
                if target_symbol not in self.SYMBOL_MAP:
                    continue

                amount = self._parse_number(amount_str)
                if amount is None:
                    continue

                source_code = self.SYMBOL_MAP[source_symbol]
                target_code = self.SYMBOL_MAP[target_symbol]

                if source_code != target_code:
                    self.results.append(
                        ParsedCurrency(
                            code=source_code,
                            amount=amount,
                            symbol=source_symbol,
                            is_crypto=source_code in self.CRYPTO_CODES,
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
        """Parse a number from various formats."""
        text = text.strip()

        # Remove spaces
        text = text.replace(" ", "")

        # Determine format (1,234.56 vs 1.234,56)
        if "," in text and "." in text:
            # Check which is the decimal separator
            if text.rfind(",") > text.rfind("."):
                # European format: 1.234,56
                text = text.replace(".", "").replace(",", ".")
            else:
                # US format: 1,234.56
                text = text.replace(",", "")
        elif "," in text:
            # Could be thousand separator or decimal
            parts = text.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Likely decimal (100,50)
                text = text.replace(",", ".")
            else:
                # Likely thousands (1,000)
                text = text.replace(",", "")

        try:
            return float(text)
        except ValueError:
            return None

    def _parse_code_amount(self) -> None:
        """Parse patterns like 'USD 100' or 'USD100'."""
        pattern = r"([A-Z]{3})\s*(\d[\d,.\s]*)"

        for match in re.finditer(pattern, self.text):
            code = match.group(1)
            amount_str = match.group(2)

            if self._is_valid_currency(code):
                amount = self._parse_number(amount_str)
                if amount is not None:
<<<<<<< HEAD
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )
=======
                    self.results.append(ParsedCurrency(
                        code=code,
                        amount=amount,
                        is_crypto=code in self.CRYPTO_CODES,
                        original_text=match.group(0),
                        span=match.span()
                    ))
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

    def _parse_amount_code(self) -> None:
        """Parse patterns like '100 USD' or '100USD'."""
        pattern = r"(\d[\d,.\s]*)\s*([A-Z]{3})"

        for match in re.finditer(pattern, self.text):
            amount_str = match.group(1)
            code = match.group(2)

            if self._is_valid_currency(code):
                amount = self._parse_number(amount_str)
                if amount is not None:
<<<<<<< HEAD
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )
=======
                    self.results.append(ParsedCurrency(
                        code=code,
                        amount=amount,
                        is_crypto=code in self.CRYPTO_CODES,
                        original_text=match.group(0),
                        span=match.span()
                    ))
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

    def _parse_symbol_amount(self) -> None:
        """Parse patterns like '$100' or '€50'."""
        for symbol, code in self.SYMBOL_MAP.items():
            # Symbol before amount: $100
            pattern1 = re.escape(symbol) + r"\s*(\d[\d,.\s]*)"
            for match in re.finditer(pattern1, self.original_text):
                amount = self._parse_number(match.group(1))
                if amount is not None:
<<<<<<< HEAD
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            symbol=symbol,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )
=======
                    self.results.append(ParsedCurrency(
                        code=code,
                        amount=amount,
                        symbol=symbol,
                        is_crypto=code in self.CRYPTO_CODES,
                        original_text=match.group(0),
                        span=match.span()
                    ))
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

            # Symbol after amount: 100$
            pattern2 = r"(\d[\d,.\s]*)\s*" + re.escape(symbol)
            for match in re.finditer(pattern2, self.original_text):
                amount = self._parse_number(match.group(1))
                if amount is not None:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            symbol=symbol,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=match.span(),
                        )
                    )

    def _parse_alias_amount(self) -> None:
        """Parse aliases like '100 dollars' or 'dollars 100'."""
        # Merge maps for iteration
        all_aliases = self.ALIAS_MAP.copy()
        if self._alias_map_from_file:
            all_aliases.update(self._alias_map_from_file)

        # Keep track of matched spans to prevent overlaps within alias parsing
        matched_spans = []

        for alias, code in all_aliases.items():
            # Amount before alias: 100 dollars
            pattern1 = r"(\d[\d,.\s]*)\s*" + re.escape(alias)
            for match in re.finditer(pattern1, self.text):
                span = match.span()
                # Check overlap
                if any(max(span[0], s[0]) < min(span[1], s[1]) for s in matched_spans):
                    continue

                amount = self._parse_number(match.group(1))
                if amount is not None:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    matched_spans.append(span)

            # Alias before amount: dollars 100
            pattern2 = re.escape(alias) + r"\s*(\d[\d,.\s]*)"
            for match in re.finditer(pattern2, self.text):
                span = match.span()
                # Check overlap
                if any(max(span[0], s[0]) < min(span[1], s[1]) for s in matched_spans):
                    continue

                amount = self._parse_number(match.group(1))
                if amount is not None:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=amount,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    matched_spans.append(span)

    def _parse_standalone_aliases(self) -> None:
        """Parse standalone aliases like 'dollar' (default to 1.0)."""
        # Collect existing spans
        existing_spans = [r.span for r in self.results]

        # Merge maps
        all_aliases = self.ALIAS_MAP.copy()
        if self._alias_map_from_file:
            all_aliases.update(self._alias_map_from_file)

        # Check for each alias as a whole word
        for alias, code in all_aliases.items():
            pattern = r"\b" + re.escape(alias) + r"\b"

            for match in re.finditer(pattern, self.text):
                span = match.span()

                # Check overlap
<<<<<<< HEAD
                is_overlap = any(max(span[0], s[0]) < min(span[1], s[1]) for s in existing_spans)
=======
                is_overlap = any(
                    max(span[0], s[0]) < min(span[1], s[1])
                    for s in existing_spans
                )
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

                if not is_overlap:
                    self.results.append(
                        ParsedCurrency(
                            code=code,
                            amount=1.0,
                            is_crypto=code in self.CRYPTO_CODES,
                            original_text=match.group(0),
                            span=span,
                        )
                    )
                    existing_spans.append(span)

    def _parse_standalone_codes(self) -> None:
        """Parse standalone codes like 'EUR' (default to 1.0)."""
        # Collect existing spans to avoid overlap
        existing_spans = [r.span for r in self.results]

        # Match any 3-letter word that is a valid currency
        pattern = r"\b([A-Z]{3})\b"

        for match in re.finditer(pattern, self.text):
            code = match.group(1)
            span = match.span()

            # Check overlap
<<<<<<< HEAD
            is_overlap = any(max(span[0], s[0]) < min(span[1], s[1]) for s in existing_spans)

            if not is_overlap and self._is_valid_currency(code):
                self.results.append(
                    ParsedCurrency(
                        code=code,
                        amount=1.0,
                        is_crypto=code in self.CRYPTO_CODES,
                        original_text=match.group(0),
                        span=span,
                    )
                )
=======
            is_overlap = any(
                max(span[0], s[0]) < min(span[1], s[1])
                for s in existing_spans
            )

            if not is_overlap and self._is_valid_currency(code):
                self.results.append(ParsedCurrency(
                    code=code,
                    amount=1.0,
                    is_crypto=code in self.CRYPTO_CODES,
                    original_text=match.group(0),
                    span=span
                ))
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

    def _is_valid_currency(self, code: str) -> bool:
        """Check if code is a valid currency."""
        # Check dynamic codes from file first
        if self._fiat_codes_from_file and code in self._fiat_codes_from_file:
            return True
        # Fallback to hardcoded
        return code in self.FIAT_CODES or code in self.CRYPTO_CODES

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
        # Remove control characters
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        # Limit length
        text = text[:500]
        return text.strip()

    @staticmethod
    def extract_command(text: str) -> Tuple[Optional[str], str]:
        """Extract bot command from text."""
        match = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)", text, re.DOTALL)
        if match:
            return match.group(1).lower(), match.group(2).strip()
        return None, text
