"""Minimal MAX Bot API client for the operator tools (runs with the user's own token, locally)."""

from __future__ import annotations

import os
import ssl

import httpx

from .knowledge import BASE_URL, REMOVED_ENDPOINTS, find_endpoint


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
        raise MaxError("MAX_BOT_TOKEN не задан в окружении MCP-сервера")
    verb = verb.upper()
    path = "/" + path.lstrip("/")
    key = (verb, path.split("?")[0].rstrip("/"))
    if key in REMOVED_ENDPOINTS:
        raise MaxError(REMOVED_ENDPOINTS[key])
    ep = find_endpoint(verb, path)
    if not ep:
        raise MaxError(f"{verb} {path} нет среди документированных методов MAX — проверьте max_api_reference")
    params = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in (params or {}).items() if v is not None}
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers={"Authorization": tok}, timeout=40, verify=_verify(), transport=_TRANSPORT) as c:
            r = await c.request(verb, path, params=params, json=body)
    except httpx.ConnectError as e:
        msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in msg:
            raise MaxError("TLS: нет сертификата Минцифры. Укажите MAX_CA_FILE=путь к russian_trusted_root_ca.pem") from e
        raise MaxError(f"Нет соединения с {BASE_URL}: {msg}") from e
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {"raw": r.text[:500]}
    if r.status_code >= 400:
        hint = {401: "токен неверный или отозван", 403: "нет прав (бот не админ или действие запрещено)",
                404: "объект не найден или бот не состоит в чате", 429: "превышен лимит запросов, подождите"}.get(r.status_code, "")
        raise MaxError(f"HTTP {r.status_code} {hint}: {data}")
    if ep.get("deprecated"):
        data = {"warning": ep["summary"], "result": data}
    return data
