"""Answer language for tool output: Russian or English.

Each tool sets the language for its call; library code calls tr(ru, en) or loc(entry)
and never needs to know where the language came from.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any, Literal

Lang = Literal["ru", "en"]

DEFAULT: Lang = "en" if os.environ.get("XONTA_MAX_LANG", "").lower() == "en" else "ru"
_lang: ContextVar[Lang] = ContextVar("xonta_max_lang", default=DEFAULT)


def set_lang(lang: str | None) -> Lang:
    value: Lang = "en" if (lang or DEFAULT) == "en" else "ru"
    _lang.set(value)
    return value


def get_lang() -> Lang:
    return _lang.get()


def tr(ru: str, en: str) -> str:
    return en if _lang.get() == "en" else ru


def loc(entry: Any) -> Any:
    """Pick language-specific fields: for a key `k` with a sibling `k_en`, return one `k` in the current language."""
    if isinstance(entry, list):
        return [loc(e) for e in entry]
    if not isinstance(entry, dict):
        return entry
    en = _lang.get() == "en"
    out = {}
    for k, v in entry.items():
        if k.endswith("_en"):
            continue
        if en and f"{k}_en" in entry:
            v = entry[f"{k}_en"]
        out[k] = loc(v)
    return out
