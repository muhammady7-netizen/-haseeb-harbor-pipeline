"""Shared ``Label: value`` reader for ``pdf.find_labeled_value`` and
``md.find_labeled_value``.

A labelled figure is a label stem (matched case-insensitively, plus up to two
following words and an optional bracketed unit such as ``(USD)``), an optional
separator (``:``, ``=``, a dash), then a number written the way people write
numbers in reports:

* thousands separators and decimals: ``1,200``, ``1,200.50``;
* currency before or after: ``$1,200``, ``US$ 55``, ``USD 55``, ``55 USD``,
  ``€12``; the unit is reported, not required;
* percent: ``12%`` (the value is 12, the unit ``%``);
* accounting negatives: ``(1,200)`` is -1200; ``-5`` and ``−5`` are -5;
* scale words: ``1.2 million``, ``3.5M``, ``40k``, ``2bn`` are multiplied out.

Figures written as words ("twelve") are not read. A hedge after the value on
the same line (``8 or 9``, ``8 (possibly 9)``, ``about 9``) is returned as an
alternative so a check can refuse a hedged answer.
"""

from __future__ import annotations

import re
from typing import Any

_CURRENCY_CODES = r"USD|EUR|GBP|JPY|CHF|CAD|AUD|INR|CNY|NZD|SGD|HKD|SEK|NOK|DKK|ZAR|MXN|BRL"
_CURRENCY_SIGNS = r"US\$|A\$|C\$|NZ\$|HK\$|S\$|\$|€|£|¥|₹"
_SCALE = r"thousand|million|billion|mn|bn|k|K|M"
_SCALE_FACTORS = {
    "thousand": 1e3, "k": 1e3,
    "million": 1e6, "mn": 1e6, "m": 1e6,
    "billion": 1e9, "bn": 1e9,
}

# One number as written. Groups: neg_paren (accounting brackets), prefix
# (currency before), sign, digits, scale, suffix (% or currency after).
NUMBER = (
    r"(?P<open>\()?[ \t]*"
    r"(?P<prefix>(?:" + _CURRENCY_SIGNS + r")|(?:(?:" + _CURRENCY_CODES + r")[ \t]?))?[ \t]*"
    r"(?P<sign>[-−+])?[ \t]*"
    r"(?P<prefix2>" + _CURRENCY_SIGNS + r")?"
    r"(?<![\d.])(?P<digits>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?![\d,]*\d)"
    r"(?:[ \t]?(?P<scale>" + _SCALE + r")\b)?"
    r"(?P<suffix>[ \t]?%|[ \t]?(?:" + _CURRENCY_CODES + r")\b|[ \t]?\((?:" + _CURRENCY_CODES + r"|" + _CURRENCY_SIGNS + r")\))?"
    r"(?(open)[ \t]*\))"
)

_NUMBER_RE = re.compile(NUMBER)
_HEDGE_RE = re.compile(
    r"(?i)\s*\(?\s*(?:or|possibly|alternatively|either|maybe|perhaps|~|about|approx\.?|approximately|roughly)\s+"
    + NUMBER
)
# A number followed by a rate or denominator ("about 3.6 per entry", "or 2 a
# week", "roughly 1 in 5") describes a different quantity, not a competing
# value for the label, so it is not an alternative.
_RATE_AFTER_RE = re.compile(
    r"(?i)^[ \t\u00a0]*(?:per|each|every|a|an|in|out[ \t]+of|/|x|×|times)(?![\w])"
)


def number_from_match(match: re.Match[str]) -> tuple[float, str | None]:
    """The value and unit of a ``NUMBER`` match."""
    value = float(match.group("digits").replace(",", ""))
    scale = match.group("scale")
    if scale:
        value *= _SCALE_FACTORS.get(scale.lower(), 1.0)
        value = round(value, 6)
    negative = bool(match.group("open")) or match.group("sign") in {"-", "−"}
    if negative:
        value = -value
    unit = None
    suffix = (match.group("suffix") or "").strip().strip("()")
    prefix = (match.group("prefix") or match.group("prefix2") or "").strip()
    if suffix:
        unit = suffix
    elif prefix:
        unit = prefix
    return value, unit


def number_text(match: re.Match[str]) -> str:
    """The number exactly as written (currency, sign, brackets included)."""
    starts = [
        match.start(group)
        for group in ("open", "prefix", "sign", "prefix2", "digits")
        if match.group(group) is not None
    ]
    return match.string[min(starts):match.end()].strip()


def parse_number(text: str) -> tuple[float, str | None] | None:
    """Parse ``text`` when it is exactly one number as written, else None."""
    match = _NUMBER_RE.fullmatch(text.strip())
    if match is None:
        return None
    return number_from_match(match)


# Horizontal space as renderers write it: runs of spaces, tabs and NBSP
# (ReportLab justification and narrow columns widen the gaps).
_SP = "[ \\t\u00a0]"


def _stem(label_stem: str, *, wrap: bool) -> str:
    """The label's own words, any run of horizontal space between them (and,
    when ``wrap``, one line break, as a narrow PDF column wraps a label)."""
    gap = _SP + "*\\n?" + _SP + "*" if wrap else _SP + "+"
    words = [re.escape(word) for word in label_stem.split()]
    if wrap:
        return "(?:" + gap.join(words) + ")" if len(words) > 1 else words[0]
    return gap.join(words)


def label_pattern(label_stem: str, *, anchored: bool) -> re.Pattern[str]:
    """``<stem>…<up to 2 words>[ (unit)] [sep] <number>``.

    ``anchored`` requires the label to open its line (after optional list,
    quote or emphasis markup, which the caller strips for Markdown). Spaces,
    tabs and NBSP are interchangeable and may repeat anywhere in the label and
    around the separator; an unanchored (PDF) label may also wrap once
    between its own words.
    """
    start = r"(?im)^" + _SP + "*" if anchored else r"(?i)\b"
    return re.compile(
        start
        + r"(?P<label>" + _stem(label_stem, wrap=not anchored) + r"\w*(?:" + _SP + r"+[A-Za-z][\w'’]*){0,2}?)"
        + r"(?:" + _SP + r"*\((?P<label_unit>[^()\n]{1,20})\))?"
        + _SP + r"*[:=\-\u2013\u2014]?" + _SP + r"*\n?" + _SP + "*"
        + NUMBER
    )


def tail_pattern(label_stem: str) -> re.Pattern[str]:
    """A block or line that ends with the label and its separator."""
    return re.compile(
        r"(?i)\b" + _stem(label_stem, wrap=True)
        + r"\w*(?:" + _SP + r"+[A-Za-z][\w'’]*){0,2}?(?:" + _SP + r"*\([^()\n]{1,20}\))?" + _SP + r"*[:=]\s*$"
    )


HEAD_NUMBER_RE = re.compile(r"^\s*" + NUMBER)


def find_hits(text: str, pattern: re.Pattern[str], location: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    """Every labelled number in ``text`` with its hedged alternatives."""
    hits: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        line_start = text.rfind("\n", 0, match.start("label")) + 1
        line_end = text.find("\n", match.end())
        line_end = len(text) if line_end < 0 else line_end
        value, unit = number_from_match(match)
        unit = unit or (match.group("label_unit") or "").strip() or None
        tail = text[match.end():line_end]
        alternatives = [
            number_from_match(hedge)[0]
            for hedge in _HEDGE_RE.finditer(tail)
            if not _RATE_AFTER_RE.match(tail[hedge.end():])
        ]
        hits.append({
            **location,
            "label": match.group("label").strip(),
            "value": value,
            "value_text": number_text(match),
            "unit": unit,
            "alternatives": alternatives,
            "line": text[line_start:line_end].strip()[: limit or 500],
        })
    return hits


def summarize(hits: list[dict[str, Any]], location_keys: tuple[str, ...]) -> dict[str, Any]:
    """The ``find_labeled_value`` output: first hit plus consistency facts."""
    first = hits[0] if hits else None
    distinct = sorted({hit["value"] for hit in hits})
    summary = {
        "found": bool(hits),
        "label": first["label"] if first else None,
        "value": first["value"] if first else None,
        "value_text": first["value_text"] if first else None,
        "unit": first["unit"] if first else None,
        "alternatives": sorted({alt for hit in hits for alt in hit["alternatives"]}),
        "line": first["line"] if first else None,
        "occurrences": len(hits),
        "consistent": len(distinct) <= 1,
        "all_values": distinct,
    }
    for key in location_keys:
        summary[key] = first[key] if first else None
    return summary
