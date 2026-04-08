from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


_CURRENCY_RE = re.compile(r"[^0-9.\-]")


def normalize_whitespace(value: str) -> str:
    return " ".join((value or "").strip().split())


def parse_amount(value: str) -> float | None:
    s = normalize_whitespace(value)
    if not s:
        return None
    s = _CURRENCY_RE.sub("", s)
    if not s:
        return None
    try:
        return float(Decimal(s))
    except InvalidOperation:
        return None


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d %Y",
    "%b %d %Y",
]


def parse_date_iso(value: str) -> str | None:
    s = normalize_whitespace(value)
    if not s:
        return None
    # Handle YYYYMMDD
    if re.fullmatch(r"\d{8}", s):
        try:
            dt = datetime.strptime(s, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_category(value: str, allowed: list[str]) -> str | None:
    s = normalize_whitespace(value).lower()
    if not s:
        return None
    s = s.replace(" ", "_")
    aliases = {
        "equip": "equipment",
        "equipment": "equipment",
        "sw": "software",
        "software": "software",
        "meal": "meals",
        "meals": "meals",
        "office": "office_supplies",
        "office_supplies": "office_supplies",
        "office-supplies": "office_supplies",
        "training": "training",
        "travel": "travel",
        "other": "other",
    }
    candidate = aliases.get(s, s)
    if candidate in allowed:
        return candidate
    # last-ditch: casefold compare
    allowed_lower = {a.lower(): a for a in allowed}
    if candidate.lower() in allowed_lower:
        return allowed_lower[candidate.lower()]
    return candidate  # return candidate so API can reject w/ reason


@dataclass(frozen=True)
class DeterministicNormalizedRow:
    date: str | None
    description: str | None
    amount: str | None
    category: str | None
    invoice_reference: str | None
    needs_llm: bool
    issues: list[str]


def deterministic_normalize_row(
    row: dict[str, str],
    *,
    allowed_categories: list[str],
) -> DeterministicNormalizedRow:
    # Map a variety of possible header names onto our canonical fields.
    def get(*keys: str) -> str:
        for k in keys:
            if k in row:
                return row.get(k, "")
        # fallback: case-insensitive match
        lower = {kk.lower(): kk for kk in row.keys()}
        for k in keys:
            if k.lower() in lower:
                return row.get(lower[k.lower()], "")
        return ""

    raw_date = get("date")
    raw_desc = get("description", "desc", "item")
    raw_amount = get("amount", "amt", "total")
    raw_category = get("category", "cat", "type")
    raw_invoice = get(
        "invoice_reference", "invoice", "invoice_ref", "invoice id", "reference"
    )

    issues: list[str] = []

    date_iso = parse_date_iso(raw_date)
    if not date_iso:
        issues.append("could not parse date")

    desc = normalize_whitespace(raw_desc)
    if not desc:
        issues.append("missing description")

    amt = parse_amount(raw_amount)
    if amt is None:
        issues.append("could not parse amount")

    cat = normalize_category(raw_category, allowed_categories)
    if not cat:
        issues.append("missing category")

    inv = normalize_whitespace(raw_invoice) or None

    needs_llm = any(
        [
            date_iso is None,
            amt is None,
            cat is None,
            desc == "",
        ]
    )

    return DeterministicNormalizedRow(
        date=date_iso,
        description=desc or None,
        amount=str(amt) if amt is not None else None,
        category=cat,
        invoice_reference=inv,
        needs_llm=needs_llm,
        issues=issues,
    )
