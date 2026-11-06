"""Minimal MAX Bot API client for the operator tools (runs with the user's own token, locally)."""

from __future__ import annotations

import os
import ssl

import httpx

from .i18n import tr
from .knowledge import BASE_URL, find_endpoint, removed_note


class MaxError(Exception):
    pass


_TRANSPORT: httpx.AsyncBaseTransport | None = None  # tests inject a mock transport here


def _verify() -> ssl.SSLContext | bool:
    ca = os.environ.get("MAX_CA_FILE")
    ctx = ssl.create_default_context()
    if ca:
        ctx.load_verify_locations(ca)
    return ctx


def token() -> str | None:
    return os.environ.get("MAX_BOT_TOKEN") or None


async def request(verb: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    tok = token()
    if not tok:
        raise MaxError(tr("MAX_BOT_TOKEN не задан в окружении MCP-сервера", "MAX_BOT_TOKEN is not set in the MCP server environment"))
    verb = verb.upper()
    path = "/" + path.lstrip("/")
    note = removed_note(verb, path)
    if note:
        raise MaxError(note)
    ep = find_endpoint(verb, path)
    if not ep:
        raise MaxError(tr(f"{verb} {path} нет среди документированных методов MAX — проверьте max_api_reference", f"{verb} {path} is not a documented MAX method — check max_api_reference"))
    params = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in (params or {}).items() if v is not None}
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers={"Authorization": tok}, timeout=40, verify=_verify(), transport=_TRANSPORT) as c:
            r = await c.request(verb, path, params=params, json=body)
    except httpx.ConnectError as e:
        msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in msg:
            raise MaxError(tr("TLS: нет сертификата Минцифры. Укажите MAX_CA_FILE=путь к russian_trusted_root_ca.pem", "TLS: the Russian Trusted Root CA is missing. Set MAX_CA_FILE=path to russian_trusted_root_ca.pem")) from e
        raise MaxError(tr(f"Нет соединения с {BASE_URL}: {msg}", f"Can't connect to {BASE_URL}: {msg}")) from e
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {"raw": r.text[:500]}
    if r.status_code >= 400:
        hint = {401: tr("токен неверный или отозван", "token is wrong or revoked"),
                403: tr("нет прав (бот не админ или действие запрещено)", "forbidden (bot is not an admin or the action is not allowed)"),
                404: tr("объект не найден или бот не состоит в чате", "not found, or the bot is not in the chat"),
                429: tr("превышен лимит запросов, подождите", "rate limit exceeded, wait")}.get(r.status_code, "")
        raise MaxError(f"HTTP {r.status_code} {hint}: {data}")
    if ep.get("deprecated"):
        data = {"warning": tr(ep["summary"], ep["summary_en"]), "result": data}
    return data
