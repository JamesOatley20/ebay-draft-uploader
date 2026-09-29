"""The six listing fields this app can send to an eBay draft."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import re

from . import AppError


def read_json(content: str) -> dict:
    """Read a small JSON object, rejecting duplicate keys and non-JSON numbers."""
    if len(content.encode("utf-8")) > 256_000:
        raise AppError("JSON file is too large (maximum 256 KB).")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AppError(f"JSON contains the same field twice: {key}.")
            result[key] = value
        return result

    def invalid(value):
        raise AppError(f"JSON contains an invalid number: {value}.")

    try:
        data = json.loads(content, object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, RecursionError) as error:
        raise AppError("This is not a readable JSON file. Ask ChatGPT to prepare it again.") from error
    if not isinstance(data, dict):
        raise AppError("JSON must contain one object, not a list.")
    return data


def text(value, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise AppError(f"{name} must contain between 1 and {limit} characters.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise AppError(f"{name} contains an unsupported control character.")
    return value.strip()


@dataclass(frozen=True)
class Listing:
    title: str
    category_id: str
    description: str
    price_gbp: Decimal | None = None
    condition_id: int | None = None
    quantity: int = 1

    @classmethod
    def parse(cls, data: dict) -> "Listing":
        if not isinstance(data, dict):
            raise AppError("Listing data must be one JSON object.")
        required = {"title", "category_id", "description"}
        allowed = required | {"price_gbp", "condition_id", "quantity"}
        if required - data.keys():
            raise AppError("Missing listing fields: " + ", ".join(sorted(required - data.keys())) + ".")
        if data.keys() - allowed:
            raise AppError("Unsupported listing fields: " + ", ".join(sorted(data.keys() - allowed))
                           + ". Use the six-field project contract; keep private notes in output.txt.")
        title = text(data["title"], "Title", 80)
        if title[0] in "=+-@" or any(c in title for c in "\r\n\t"):
            raise AppError("Title must be one line and cannot start with =, +, - or @.")
        category = data["category_id"]
        if not isinstance(category, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", category):
            raise AppError("A current eBay UK category ID is needed; ask ChatGPT to find it.")
        description = text(data["description"], "Description", 20_000)
        if re.search(r"<[^>]+>|```||\b(?:input\.txt|output\.txt|as an ai|system prompt|"
                     r"assumed condition|please confirm|seller should|according to the prompt)\b",
                     description, re.I):
            raise AppError("Description contains markup or preparation instructions. Ask for clean buyer-facing copy.")
        price = data.get("price_gbp")
        if price is not None:
            if not isinstance(price, str) or not re.fullmatch(r"\d{1,9}(?:\.\d{1,2})?", price):
                raise AppError('Price must be a GBP string such as "29.95", or null when unknown.')
            try:
                price = Decimal(price)
            except InvalidOperation as error:
                raise AppError("Price is not a valid amount.") from error
            if not Decimal("0.10") <= price <= Decimal("999999999"):
                raise AppError("Price must be at least GBP 0.10 and at most GBP 999999999.")
        condition = data.get("condition_id")
        if condition is not None and (type(condition) is not int or not 0 < condition < 10000):
            raise AppError("Condition ID must be a category-appropriate integer, or null when unverified.")
        quantity = data.get("quantity", 1)
        if type(quantity) is not int or not 1 <= quantity <= 100000:
            raise AppError("Quantity must be a whole number between 1 and 100000.")
        return cls(title, category, description, price, condition, quantity)

    def as_dict(self) -> dict:
        return {
            "title": self.title, "category_id": self.category_id,
            "price_gbp": f"{self.price_gbp:.2f}" if self.price_gbp is not None else None,
            "condition_id": self.condition_id, "description": self.description,
            "quantity": self.quantity,
        }
