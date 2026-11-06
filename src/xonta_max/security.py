"""MAX signatures: mini-app initData, requestContact phone hash, request_contact vcf hash, webhook secret.

Algorithms from https://dev.max.ru/docs/webapps/validation and the Bot API docs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import parse_qsl, quote, urlencode

from .i18n import tr

WEBHOOK_SECRET = re.compile(r"^[\w-]{5,256}$", re.ASCII)


def _hex(key: bytes, msg: str) -> str:
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _check_string(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(sorted(f"{k}={v}" for k, v in pairs))


def verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600, now: int | None = None) -> dict:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    hashes = [v for k, v in pairs if k == "hash"]
    if len(hashes) != 1:
        return {"valid": False, "reason": tr("hash должен встречаться ровно один раз", "hash must appear exactly once")}
    rest = [(k, v) for k, v in pairs if k != "hash"]
    expected = _hex(_secret_key(bot_token), _check_string(rest))
    sig_ok = hmac.compare_digest(expected, hashes[0].lower())
    data = dict(rest)
    age = None
    fresh = True
    if "auth_date" in data:
        try:
            age = (now or int(time.time())) - int(data["auth_date"])
            fresh = age <= max_age_seconds
        except ValueError:
            return {"valid": False, "reason": tr("auth_date не число", "auth_date is not a number")}
    parsed = {}
    for k, v in data.items():
        if v.startswith("{"):
            try:
                parsed[k] = json.loads(v)
                continue
            except ValueError:
                pass
        parsed[k] = v
    if not sig_ok:
        reason = tr("подпись не совпала: другой токен, строку изменили или декодировали дважды", "signature mismatch: different token, the string was changed, or it was decoded twice")
        if re.search(r"%25[0-9A-Fa-f]{2}", init_data):
            reason += tr(" (похоже на двойное кодирование — передавайте window.WebApp.initData как есть)", " (looks double-encoded — pass window.WebApp.initData as is)")
        return {"valid": False, "reason": reason, "age_seconds": age}
    if not fresh:
        return {"valid": False, "reason": tr(f"auth_date устарел: {age} с при допустимых {max_age_seconds}", f"auth_date is stale: {age} s, allowed {max_age_seconds}"), "age_seconds": age, "data": parsed}
    return {"valid": True, "age_seconds": age, "data": parsed}


def sign_init_data(bot_token: str, user: dict | None = None, chat: dict | None = None, start_param: str | None = None,
                   auth_date: int | None = None, query_id: str | None = None) -> dict:
    """Build a correctly signed initData string for tests (use a test token, never production)."""
    user = user or {"id": 100500, "first_name": tr("Тест", "Test"), "last_name": tr("Пользователь", "User"), "username": "test_user",
                    "language_code": "ru", "photo_url": ""}
    chat = chat or {"id": 100500, "type": "DIALOG"}
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": query_id or secrets.token_hex(8),
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "chat": json.dumps(chat, ensure_ascii=False, separators=(",", ":")),
    }
    if start_param:
        if not re.fullmatch(r"[\w-]{1,512}", start_param, re.ASCII):
            raise ValueError(tr("start_param: до 512 символов, только A-Za-z0-9_-", "start_param: up to 512 characters, A-Za-z0-9_- only"))
        fields["start_param"] = start_param
    h = _hex(_secret_key(bot_token), _check_string(list(fields.items())))
    s = urlencode({**fields, "hash": h}, quote_via=quote)
    return {"init_data": s, "hash": h, "fields": fields}


def _phone_msg(auth_date: str, phone: str, user_id: str) -> str:
    return "\n".join([f"authDate={auth_date}", f"phone={phone.lstrip('+')}", f"userId={user_id}"])


def sign_phone(auth_date: str, phone: str, user_id: str, bot_token: str) -> str:
    return _hex(bot_token.encode(), _phone_msg(auth_date, phone, user_id))


def verify_phone(auth_date: str, phone: str, user_id: str, hash_: str, bot_token: str) -> dict:
    msg = _phone_msg(auth_date, phone, user_id)
    ok = hmac.compare_digest(_hex(bot_token.encode(), msg), hash_.lower())
    return {"valid": ok, "checked_string": msg.replace("\n", "\\n")}


def verify_contact(vcf_info: str, hash_: str, bot_token: str) -> dict:
    ok = hmac.compare_digest(_hex(bot_token.encode(), vcf_info), hash_.lower())
    hint = None
    if not ok and "\\r\\n" in vcf_info:
        hint = tr("В vcf_info буквальные \\r\\n — передайте строку после JSON-декодирования, с настоящими переводами строк", "vcf_info has literal \\r\\n — pass the JSON-decoded string with real line breaks")
    return {"valid": ok, "hint": hint}


def check_webhook_secret(secret: str) -> dict:
    ok = bool(WEBHOOK_SECRET.match(secret))
    return {"valid": ok, "rule": tr("5-256 символов, A-Z a-z 0-9 _ -", "5-256 characters, A-Z a-z 0-9 _ -"), "suggestion": None if ok else secrets.token_urlsafe(32)}
