import json
import re

class TextProcessing:
    def __init__(self, text: str):
        self.results = []
        self.currencies_code = []
        self.text = text 

        for currency in self.data():
            self.code = currency["code"]
            names = currency["text"]
            symbol = re.escape(currency["symbol"])

            word_pattern = r"|".join(r"\b" + word + r"\b" for word in names)
                
            if re.match(r"^\w+$", symbol):
                symbol = rf"\b{symbol}\b"
                
            self.pattern = rf"{word_pattern}|{symbol}"
            self.matches = re.findall(self.pattern , self.text, re.IGNORECASE) 

            if self.matches:
                self.currencies_code.append(self.code)
                self.find_amount()

    def find_amount(self):
        amount_pattern = rf"(\b\d+(\.\d+)?\b\s*)?({self.pattern})(\s*\b\d+(\.\d+)?\b)?"
        amount_matches = re.finditer(amount_pattern, self.text, re.IGNORECASE)

        for match in amount_matches:
            pre_amount, post_amount = match.group(1), match.group(4)
            amount = float(pre_amount or post_amount or "1")
            
            self.results.append([self.code, amount])

    def data(self) -> dict:
        path = "handlers/functions/currencies_data.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_codes(self) -> list:
        return self.currencies_code

    def get_results(self) -> list:
        if self.currencies_code:
            return self.results
        else:
            return None
