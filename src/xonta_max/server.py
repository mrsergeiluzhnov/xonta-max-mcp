"""Xonta MAX — MCP server for building bots and mini-apps for the MAX messenger (max.ru)."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import time
from typing import Annotated, Any, Literal

from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, ads, client, deeplinks, knowledge, lint, messages, mocks, scaffold, security
from .i18n import loc, set_lang, tr
from .knowledge import VERIFIED_ON

HOSTED = os.environ.get("XONTA_MAX_HOSTED") == "1"
OPERATOR = bool(os.environ.get("MAX_BOT_TOKEN")) and not HOSTED

LangParam = Annotated[Literal["ru", "en"] | None, Field(
    description="Answer language: 'en' English, 'ru' Russian. Pick the user's language; default ru (or XONTA_MAX_LANG)")]


def _actual() -> str:
    return tr(f"актуально на {VERIFIED_ON}; первоисточник — dev.max.ru", f"current as of {VERIFIED_ON}; primary source — dev.max.ru")


INSTRUCTIONS = """Tools for building bots and mini-apps for the MAX messenger (max.ru, dev.max.ru).
Every tool takes lang='en' or lang='ru' — answer in the user's language.
Knowledge: max_api_reference, max_endpoint_info, max_limits, max_changelog — current Bot API facts with sources.
Code: max_lint_code finds outdated hosts, TLS mistakes, removed methods and Telegram leftovers;
max_migrate_from_telegram plans a port from Telegram Bot API; max_scaffold_bot generates a working project.
Messages: max_build_message, max_validate_message, max_split_text, max_convert_formatting.
Links: max_deeplink (bot start, mini-app startapp, share-to-MAX without a bot, user mention).
Testing: max_mock_update (webhook payloads + curl), max_mock_init_data and max_bridge_mock (window.WebApp emulator).
Ads: max_api_reference topic='ads' (where to buy, channel monetization, marking), max_tracking_links (a link per placement),
max_ad_report (cost per order, ROAS, ROMI with confidence intervals), max_check_ad_post (marking check).
When the server runs locally with MAX_BOT_TOKEN, operator tools (max_send_message etc.) act as that bot.
Always use platform-api2.max.ru and never suggest disabling TLS verification."""

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
GEN = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False)
NET_RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
NET_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
NET_DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)

mcp = MCPServer(
    name="xonta-max",
    title="Xonta MAX",
    description="Build bots and mini-apps for the MAX messenger: Bot API facts, code checks, Telegram migration, deep links, test fixtures. English and Russian",
    instructions=INSTRUCTIONS,
    website_url="https://xonta.ru",
    version=__version__,
)

TOPIC = Literal["auth", "tls", "webhook", "messages", "keyboard", "formatting", "uploads", "chats",
                "mini_apps", "init_data", "deeplinks", "access", "libraries", "ads", "sources"]


def _err(e: Exception) -> dict:
    return {"error": type(e).__name__, "message": str(e)}


# ================================================================ knowledge

@mcp.tool(annotations=RO)
def max_api_reference(
    query: Annotated[str | None, Field(description="Free text in English or Russian, e.g. 'webhook certificate', 'callback answer', 'initData', 'GET /chats', 'attachment.not.ready'")] = None,
    topic: Annotated[TOPIC | None, Field(description="Return one whole topic instead of searching")] = None,
    lang: LangParam = None,
) -> dict:
    """Look up current facts about the MAX Bot API and Mini Apps (MAX Bridge) with links to dev.max.ru.

    Covers base URL and auth, the Russian Trusted Root CA, advertising in MAX (topic 'ads'), webhooks vs long polling, sending messages,
    inline keyboards and callbacks, formatting, uploads, chat tracking without GET /chats, mini-apps,
    initData validation, deep links, who may create bots, official libraries. Language models usually know an
    outdated API (platform-api.max.ru, token in query, GET /chats) — use this before writing MAX code.
    With no arguments returns the list of topics.
    """
    set_lang(lang)
    if topic:
        t = loc(knowledge.TOPICS[topic])
        return {"topic": topic, **t, "note": _actual()}
    if query:
        hits = knowledge.search(query)
        return {"query": query, "results": hits, "count": len(hits), "note": _actual(),
                "hint": None if hits else tr("Ничего не нашлось — попробуйте topic или max_endpoint_info",
                                             "Nothing found — try a topic or max_endpoint_info")}
    return {"topics": {k: loc(v)["title"] for k, v in knowledge.TOPICS.items()}, "base_url": knowledge.BASE_URL, "note": _actual()}


@mcp.tool(annotations=RO)
def max_endpoint_info(
    verb: Annotated[str | None, Field(description="HTTP method: GET, POST, PUT, PATCH, DELETE. Omit to list all endpoints")] = None,
    path: Annotated[str | None, Field(description="Path like '/messages', '/chats/{chatId}/pin' or a concrete one '/chats/-123/pin'")] = None,
    lang: LangParam = None,
) -> dict:
    """Details of one MAX Bot API method (query params, body, limits, gotchas, docs link) or the full method list.

    Also tells when a method was removed or restricted (GET /chats, POST /chats/{chatId}/members).
    """
    set_lang(lang)
    if not verb or not path:
        return {
            "base_url": knowledge.BASE_URL,
            "auth": tr("Authorization: <token> (без Bearer)", "Authorization: <token> (no Bearer)"),
            "endpoints": [{"verb": e["verb"], "path": e["path"], "summary": loc(e)["summary"],
                           **({"deprecated": True} if e.get("deprecated") else {})} for e in knowledge.ENDPOINTS],
            "removed": [{"verb": v, "path": p, "note": loc(n)["note"]} for (v, p), n in knowledge.REMOVED_ENDPOINTS.items()],
            "note": _actual(),
        }
    note = knowledge.removed_note(verb, path)
    if note:
        return {"verb": verb.upper(), "path": "/" + path.strip("/"), "exists": False, "note": note}
    ep = knowledge.find_endpoint(verb, path)
    if not ep:
        same = [f'{e["verb"]} {e["path"]}' for e in knowledge.ENDPOINTS if e["path"].split("/")[1:2] == path.strip("/").split("/")[:1]]
        return {"exists": False, "message": tr(f"{verb.upper()} {path} не найден в документации MAX", f"{verb.upper()} {path} is not in the MAX docs"),
                "similar": same}
    return {
        **loc(ep), "exists": True, "url": knowledge.BASE_URL + ep["path"],
        "docs": knowledge.method_url(ep["verb"], ep["path"]),
        "example_curl": f'curl -X {ep["verb"]} "{knowledge.BASE_URL}{ep["path"]}" -H "Authorization: $MAX_BOT_TOKEN"'
                        + (' -H "Content-Type: application/json" -d \'{...}\'' if ep.get("body") else ""),
        "note": _actual(),
    }


@mcp.tool(annotations=RO)
def max_limits(lang: LangParam = None) -> dict:
    """All MAX platform limits in one table: text length, rate limits, keyboard size, attachments, file sizes,
    deep link payloads, webhook rules, bots per profile — each with a source link. Also update types, button types, errors."""
    set_lang(lang)
    return {"limits": loc(knowledge.LIMITS), "update_types": loc(knowledge.UPDATE_TYPES), "button_types": loc(knowledge.BUTTON_TYPES),
            "admin_permissions": knowledge.CHAT_ADMIN_PERMISSIONS, "errors": loc(knowledge.ERRORS), "note": _actual()}


@mcp.tool(annotations=RO)
def max_changelog(lang: LangParam = None) -> dict:
    """Dated MAX platform changes in 2026 that break old code: host move to platform-api2, removed GET /chats,
    restricted member adding, HTTPS-only webhooks, comments API, self-employed access."""
    set_lang(lang)
    return {"changes": loc(knowledge.CHANGELOG), "source": knowledge.CHANGELOG_URL, "note": _actual()}


# ================================================================ code

@mcp.tool(annotations=RO)
def max_lint_code(
    code: Annotated[str, Field(description="Source code of a MAX bot or mini-app (any language), or a config / curl snippet")],
    lang: LangParam = None,
) -> dict:
    """Check MAX bot or mini-app code for known mistakes, with line numbers and fixes.

    Finds: old host platform-api.max.ru, token in query string, 'Bearer' prefix, disabled TLS verification,
    removed GET /chats, restricted member adding, type=photo uploads, wrong webhook setup (port, HTTP, /webhook),
    disable_link_preview in body, plain == comparison of the webhook secret, initData signed directly with the token,
    trusting initDataUnsafe, hardcoded upload hosts, Telegram leftovers. Static, never runs the code.
    """
    set_lang(lang)
    res = lint.lint(code)
    clean = not res["errors"] and not res["warnings"] and not res["telegram_leftovers"]
    res["summary"] = (
        tr("Ошибок не найдено.", "No problems found.") if clean
        else tr(f'Ошибок: {res["errors"]}, предупреждений: {res["warnings"]}, остатков Telegram: {len(res["telegram_leftovers"])}',
                f'Errors: {res["errors"]}, warnings: {res["warnings"]}, Telegram leftovers: {len(res["telegram_leftovers"])}')
    )
    res["note"] = _actual()
    return res


@mcp.tool(annotations=RO)
def max_migrate_from_telegram(
    code: Annotated[str | None, Field(description="Telegram bot source (aiogram, python-telegram-bot, telebot, Telegraf, grammY, raw HTTP…). Omit to get only the method map")] = None,
    lang: LangParam = None,
) -> dict:
    """Plan a port of a Telegram bot or Web App to MAX.

    With code: every Telegram API usage with line number and the MAX replacement, features with no MAX equivalent,
    effort estimate and a step-by-step plan. Without code: the full Telegram → MAX method map.
    """
    set_lang(lang)
    out: dict[str, Any] = {"telegram_to_max": lint.telegram_map(), "note": _actual()}
    if code:
        out = lint.migrate(code) | out
    return out


@mcp.tool(annotations=GEN)
def max_scaffold_bot(
    language: Annotated[Literal["python", "typescript", "go"], Field(description="python (httpx, no official SDK), typescript (@maxhub/max-bot-api) or go (official client v2)")] = "python",
    lang: LangParam = None,
) -> dict:
    """Generate a ready MAX bot project: polling for dev, webhook for prod, the Russian Trusted Root CA in the Dockerfile,
    chat tracking without GET /chats, callback answers, constant-time secret check, rate limits and text splitting (Python).
    lang sets the language of comments, README and the bot's replies.

    Returns a map of file name → content. Write the files as they are. Creating the bot itself and getting a token
    requires a verified profile on business.max.ru.
    """
    l = set_lang(lang)
    files = scaffold.scaffold(language, l)
    return {"language": language, "files": files, "next_steps": [
        tr("Создайте бота на business.max.ru и получите токен", "Create the bot at business.max.ru and get the token"),
        tr("Заполните .env по .env.example", "Fill in .env from .env.example"),
        tr("Для разработки запустите в режиме polling, для продакшна — webhook за HTTPS-прокси на 443",
           "Run in polling mode for development, webhook behind an HTTPS proxy on 443 for production"),
        tr("Прогоните код через max_lint_code после правок", "Run max_lint_code after your changes"),
    ], "note": _actual()}


# ================================================================ messages

@mcp.tool(annotations=RO)
def max_validate_message(
    body: Annotated[dict, Field(description="NewMessageBody JSON: {text, format, attachments, link, notify}")],
    target: Annotated[Literal["message", "comment"], Field(description="message — POST /messages, comment — POST /messages/{id}/comments")] = "message",
    chat_type: Annotated[Literal["dialog", "chat", "channel"] | None, Field(description="Where it goes, for channel-specific rules")] = None,
    lang: LangParam = None,
) -> dict:
    """Validate a message body before sending to MAX: 4000-char text, format, keyboard limits (210/30/7, 3 per row
    with link/open_app/request_*), button fields and lengths, attachment combinations (≤12 media, file only with a keyboard,
    audio/sticker/contact alone), comment restrictions, Telegram fields left in the body."""
    set_lang(lang)
    return messages.validate_body(body, is_comment=target == "comment", chat_type=chat_type)


@mcp.tool(annotations=RO)
def max_build_message(
    text: Annotated[str | None, Field(description="Message text, up to 4000 characters")] = None,
    format: Annotated[Literal["markdown", "html"] | None, Field(description="Text markup")] = None,
    buttons: Annotated[list[list[dict]] | None, Field(description="Rows of buttons. Short form: {text, payload} → callback, {text, url} → link, {text, web_app, payload?} → open_app; or full {type, text, ...}")] = None,
    image_urls: Annotated[list[str] | None, Field(description="External image URLs to attach without uploading")] = None,
    reply_to_mid: Annotated[str | None, Field(description="Reply to this message id")] = None,
    chat_id: Annotated[int | None, Field(description="For the curl example")] = None,
    user_id: Annotated[int | None, Field(description="For the curl example, private dialog")] = None,
    disable_link_preview: bool = False,
    lang: LangParam = None,
) -> dict:
    """Build a correct POST /messages request for MAX: JSON body with inline keyboard and images, validation result
    and a ready curl command. Use it instead of hand-writing keyboard JSON."""
    set_lang(lang)
    body: dict[str, Any] = {}
    if text is not None:
        body["text"] = text
    if format:
        body["format"] = format
    atts: list[dict] = [{"type": "image", "payload": {"url": u}} for u in (image_urls or [])]
    if buttons:
        atts.append(messages.build_keyboard(buttons))
    if atts:
        body["attachments"] = atts
    if reply_to_mid:
        body["link"] = {"type": "reply", "mid": reply_to_mid}
    check = messages.validate_body(body)
    q = []
    if chat_id is not None:
        q.append(f"chat_id={chat_id}")
    elif user_id is not None:
        q.append(f"user_id={user_id}")
    else:
        q.append("chat_id=$CHAT_ID")
    if disable_link_preview:
        q.append("disable_link_preview=true")
    payload = json.dumps(body, ensure_ascii=False).replace("'", "'\\''")
    curl = (f'curl -X POST "{knowledge.BASE_URL}/messages?{"&".join(q)}" -H "Authorization: $MAX_BOT_TOKEN" '
            f"-H \"Content-Type: application/json\" -d '{payload}'")
    return {"body": body, "query": "&".join(q), "validation": check, "curl": curl}


@mcp.tool(annotations=RO)
def max_split_text(
    text: Annotated[str, Field(description="Long text to send")],
    limit: Annotated[int, Field(ge=100, le=4000, description="Max characters per message")] = 4000,
    lang: LangParam = None,
) -> dict:
    """Split text into MAX messages of at most 4000 characters, cutting at paragraphs, lines or sentences."""
    set_lang(lang)
    parts = messages.split_text(text, limit)
    return {"parts": parts, "count": len(parts), "lengths": [len(p) for p in parts]}


@mcp.tool(annotations=RO)
def max_convert_formatting(
    text: Annotated[str, Field(description="Formatted text")],
    source: Annotated[Literal["telegram_markdownv2", "telegram_html", "markdown"], Field(description="Where the text comes from; 'markdown' = ordinary Markdown (e.g. LLM output)")],
    target: Annotated[Literal["max_markdown", "max_html"], Field(description="MAX format to produce")] = "max_markdown",
    lang: LangParam = None,
) -> dict:
    """Convert formatted text to MAX markup: Telegram MarkdownV2 (underline __x__ → ++x++, unescape), Telegram HTML
    (tg://user → max://user, spoilers dropped) or ordinary Markdown from an LLM (lists → bullets, rules removed).
    Reports what MAX cannot show (spoilers, tables, lists, inline images). Use the returned format value in the body."""
    set_lang(lang)
    try:
        res = messages.convert_formatting(text, source, target)
    except ValueError as e:
        return _err(e)
    if res["length"] > messages.TEXT_LIMIT:
        res["notes"].append(tr(f'Длина {res["length"]} > 4000 — разбейте через max_split_text',
                               f'Length {res["length"]} > 4000 — split it with max_split_text'))
    return res


# ================================================================ links

@mcp.tool(annotations=RO)
def max_deeplink(
    kind: Annotated[Literal["start", "startapp", "share", "mention"], Field(description="start — open bot with payload; startapp — open mini-app; share — 'send to MAX' link for any site, no bot needed; mention — user mention markup")],
    bot_name: Annotated[str | None, Field(description="Bot public name as in max.ru/<name> (start, startapp)")] = None,
    payload: Annotated[str | None, Field(description="start: ≤128 chars; startapp: ≤512, A-Za-z0-9_- only")] = None,
    text: Annotated[str | None, Field(description="share: text to prefill; mention: display name")] = None,
    user_id: Annotated[int | None, Field(description="mention: MAX user id")] = None,
    button_label: Annotated[str | None, Field(description="share: label for the generated HTML button; default depends on lang")] = None,
    lang: LangParam = None,
) -> dict:
    """Build and validate MAX deep links. 'share' gives a link, an HTML button and a JS helper that open
    MAX's chat picker with prefilled text — works on any website or AI agent output without owning a bot.
    Payload limits are checked, because MAX silently drops payloads that are too long or have bad characters."""
    set_lang(lang)
    try:
        return deeplinks.build(kind, bot_name, payload, text, user_id, button_label)
    except ValueError as e:
        return _err(e)


# ================================================================ testing

@mcp.tool(annotations=GEN)
def max_mock_update(
    update_type: Annotated[str, Field(description="message_created, message_callback, bot_started, bot_added, bot_removed, message_edited, message_removed, user_added, user_removed, comment_created, chat_title_changed, dialog_muted, bot_admin_permissions_changed, …")],
    text: Annotated[str | None, Field(description="Message text (message_created/edited, comments) or new title")] = None,
    payload: Annotated[str | None, Field(description="Callback payload or bot_started deep link payload")] = None,
    chat_type: Annotated[Literal["dialog", "chat", "channel"], Field(description="Where it happens")] = "dialog",
    chat_id: Annotated[int | None, Field(description="Chat id; default is generated")] = None,
    overrides: Annotated[dict | None, Field(description="Deep-merge into the generated update")] = None,
    webhook_url: Annotated[str | None, Field(description="If set, also returns a curl command that POSTs the update there")] = None,
    secret: Annotated[str | None, Field(description="Webhook secret to put into X-Max-Bot-Api-Secret")] = None,
    lang: LangParam = None,
) -> dict:
    """Generate a realistic MAX webhook Update for tests, shaped like the official schema, plus a curl command to
    send it to your local webhook. Lets you test a bot before it passes moderation or without a token."""
    set_lang(lang)
    try:
        upd = mocks.make_update(update_type, text=text, payload=payload, chat_type=chat_type,
                                chat_id=chat_id if chat_id is not None else -70000000000001, overrides=overrides)
    except ValueError as e:
        return _err(e)
    out: dict[str, Any] = {"update": upd}
    if webhook_url:
        out["curl"] = mocks.curl_for(upd, webhook_url, secret)
    out["note"] = tr("В реальной доставке MAX ждёт HTTP 200 не дольше 30 с", "In real delivery MAX waits at most 30 s for HTTP 200")
    return out


def _test_user(user_id: int, first_name: str | None) -> dict:
    return {"id": user_id, "first_name": first_name or tr("Тест", "Test"), "last_name": "", "username": "",
            "language_code": tr("ru", "en"), "photo_url": ""}


@mcp.tool(annotations=GEN)
def max_mock_init_data(
    test_bot_token: Annotated[str | None, Field(description="A TEST token to sign with. Omit to generate a random one. Never pass a production token to a hosted server")] = None,
    user_id: int = 100500,
    first_name: str | None = None,
    chat_type: Annotated[Literal["DIALOG", "CHAT", "CHANNEL"], Field(description="Where the mini-app was opened")] = "DIALOG",
    start_param: Annotated[str | None, Field(description="Value from ?startapp=")] = None,
    age_seconds: Annotated[int, Field(ge=0, description="Make auth_date this many seconds old, to test expiry")] = 0,
    lang: LangParam = None,
) -> dict:
    """Produce a correctly signed MAX mini-app initData string (two-step HMAC with 'WebAppData') for backend tests,
    with the token used, so you can check your validator end to end."""
    set_lang(lang)
    tok = test_bot_token or "test_" + secrets.token_urlsafe(24)
    try:
        signed = security.sign_init_data(tok, user=_test_user(user_id, first_name), chat={"id": user_id, "type": chat_type},
                                         start_param=start_param, auth_date=int(time.time()) - age_seconds)
    except ValueError as e:
        return _err(e)
    return {"init_data": signed["init_data"], "test_bot_token": tok, "fields": signed["fields"],
            "algorithm": loc(knowledge.TOPICS["init_data"])["text"]}


@mcp.tool(annotations=GEN)
def max_bridge_mock(
    platform: Annotated[Literal["ios", "android", "desktop", "web"], Field(description="Platform to emulate: limits which Bridge features work")] = "android",
    start_param: Annotated[str | None, Field(description="Emulated ?startapp= value")] = None,
    test_bot_token: Annotated[str | None, Field(description="TEST token: initData and requestContact hash will be validly signed with it")] = None,
    user_id: int = 100500,
    first_name: str | None = None,
    phone: str = "79990000000",
    entry_point: Literal["default", "tabbar"] = "default",
    lang: LangParam = None,
) -> dict:
    """Generate max-bridge-mock.js: a window.WebApp emulator to develop MAX mini-apps in a normal browser on localhost.

    Emulates initData/initDataUnsafe (signed if a test token is given), BackButton (Esc), DeviceStorage and
    SecureStorage (localStorage, 10-key cap), BiometricManager, HapticFeedback, NfcManager, ScreenCapture,
    requestContact with a valid hash, openLink/downloadFile/shareMaxContent click requirements and per-platform
    restrictions. Logs every call. Use only on localhost."""
    set_lang(lang)
    user = _test_user(user_id, first_name)
    chat = {"id": user_id, "type": "DIALOG"}
    now = int(time.time())
    if test_bot_token:
        init_data = security.sign_init_data(test_bot_token, user=user, chat=chat, start_param=start_param, auth_date=now)["init_data"]
        contact = {"phone": phone, "authDate": str(now), "hash": security.sign_phone(str(now), phone, str(user_id), test_bot_token)}
    else:
        init_data = f"auth_date={now}&hash=unsigned"
        contact = {"phone": phone, "authDate": str(now), "hash": "unsigned"}
    unsafe = {"query_id": "mock", "auth_date": now, "hash": "", "user": user, "chat": chat, "start_param": start_param or ""}
    cfg = {"platform": platform, "initData": init_data, "initDataUnsafe": unsafe, "contact": contact,
           "entryPoint": entry_point, "signed": bool(test_bot_token),
           "text": {"sharePhone": tr("[MAX mock] Поделиться номером", "[MAX mock] Share phone number"),
                    "qr": tr("[MAX mock] Содержимое QR-кода:", "[MAX mock] QR code content:")}}
    js = mocks.BRIDGE_MOCK_JS.replace("__CONFIG__", json.dumps(cfg, ensure_ascii=False))
    loader = ('<script src="max-bridge-mock.js"></script>\n'
              + tr("<!-- в продакшне: ", "<!-- in production: ") + '<script src="https://st.max.ru/js/max-web-app.js"></script> -->')
    return {"filename": "max-bridge-mock.js", "content": js, "html": loader,
            "note": tr("Не выкладывайте mock в продакшн. Тему и MainButton он не эмулирует — их нет и в настоящем MAX Bridge.",
                       "Don't ship the mock to production. It doesn't emulate theme or MainButton — real MAX Bridge has neither.")}


@mcp.tool(annotations=RO)
def max_check_webhook_secret(
    secret: Annotated[str | None, Field(description="Secret to check; omit to generate a new one")] = None,
    lang: LangParam = None,
) -> dict:
    """Check a MAX webhook secret against the rules (5-256 chars, A-Z a-z 0-9 _ -) or generate a strong one."""
    set_lang(lang)
    if not secret:
        return {"secret": secrets.token_urlsafe(32), "valid": True, "header": "X-Max-Bot-Api-Secret"}
    return security.check_webhook_secret(secret) | {"header": "X-Max-Bot-Api-Secret"}


@mcp.tool(annotations=RO)
def server_status(lang: LangParam = None) -> dict:
    """Server version, facts date, mode (hosted or local), languages and whether operator tools are active."""
    set_lang(lang)
    return {
        "version": __version__, "facts_verified_on": VERIFIED_ON, "hosted": HOSTED, "languages": ["ru", "en"],
        "operator_tools": OPERATOR, "signature_tools": not HOSTED,
        "operator_hint": None if OPERATOR else (
            tr("Инструменты управления ботом работают только при локальном запуске с MAX_BOT_TOKEN",
               "Bot operator tools work only when the server runs locally with MAX_BOT_TOKEN") if not HOSTED
            else tr("На общем сервере токены не принимаются. Запустите локально: uvx xonta-max-mcp с MAX_BOT_TOKEN",
                    "The shared server never takes bot tokens. Run locally: uvx xonta-max-mcp with MAX_BOT_TOKEN")),
        "ca_file": bool(os.environ.get("MAX_CA_FILE")),
        "sources": [knowledge.DOCS, knowledge.SCHEMA, knowledge.BRIDGE],
    }


# ================================================================ ads

@mcp.tool(annotations=RO)
def max_tracking_links(
    campaign: Annotated[str, Field(description="Campaign name, e.g. 'black friday'")],
    placements: Annotated[list[dict], Field(description="Channels where the ad goes: [{name, cost?, erid?}]. name may be a title or max.ru link")],
    bot_name: Annotated[str | None, Field(description="Your bot's public name: each placement gets max.ru/<bot>?start=<id>")] = None,
    mini_app_bot: Annotated[str | None, Field(description="Bot with your mini-app: each placement gets ?startapp=<id>")] = None,
    site_url: Annotated[str | None, Field(description="Landing page: each placement gets UTM tags and its erid")] = None,
    utm_medium: str = "seeding",
    promo_codes: Annotated[bool, Field(description="Also make one promo code per placement")] = True,
    lang: LangParam = None,
) -> dict:
    """Make a separate tracking link (and promo code) for every channel where an ad is placed in MAX, so you can
    see which placement brought users and sales. Bot links use ?start=<id>: the id arrives in bot_started.payload,
    which works even for clicks that never leave the messenger. Returns a media plan as CSV.
    Then feed the counts to max_ad_report."""
    set_lang(lang)
    try:
        return ads.tracking_links(campaign, placements, bot_name, mini_app_bot, site_url, utm_medium, promo_codes)
    except ValueError as e:
        return _err(e)


@mcp.tool(annotations=RO)
def max_ad_report(
    placements: Annotated[list[dict], Field(description="Per placement: {name, id?, cost, views?, clicks?, starts?, leads?, orders?, revenue?, margin_pct?}")],
    events: Annotated[list | None, Field(description="Optional bot_started updates, {'payload': …} objects or payload strings; starts are counted per placement id")] = None,
    campaign: Annotated[str | None, Field(description="Only count payloads of this campaign")] = None,
    min_orders: Annotated[int, Field(ge=1, description="Below this many orders a placement is flagged as low data")] = 5,
    lang: LangParam = None,
) -> dict:
    """Compare ad placements in MAX by real results: CPM, cost per click or bot start, cost per lead and per order,
    ROAS, profit after ads and ROMI (with margin), conversion with a 95% confidence interval.
    Says when a difference between channels may be chance and when there is too little data.
    A calculator only: it does not touch ad accounts or move money."""
    set_lang(lang)
    try:
        return ads.ad_report(placements, events, campaign, min_orders)
    except ValueError as e:
        return _err(e)


@mcp.tool(annotations=RO)
def max_check_ad_post(
    text: Annotated[str, Field(description="Ad post text as it will be published")],
    links: Annotated[list[str] | None, Field(description="Links used in buttons or elsewhere, if not in the text")] = None,
    channel_subscribers: Annotated[int | None, Field(description="Subscribers of the channel where it goes")] = None,
    channel_has_a_plus: Annotated[bool | None, Field(description="Whether the channel has the A+ mark (RKN registry)")] = None,
    advertiser_site: Annotated[str | None, Field(description="Site with the advertiser's details, if they are not in the text")] = None,
    lang: LangParam = None,
) -> dict:
    """Check an ad post for MAX against Russian ad marking rules: the 'Реклама' label at the top, advertiser details
    (name and INN/OGRN or a site), an erid token in the link or text, the A+ mark for channels over 10,000 subscribers,
    and the 4000-character limit. A hint, not legal advice; ORD registration is not checked."""
    set_lang(lang)
    return ads.check_ad_post(text, links, channel_subscribers, channel_has_a_plus, advertiser_site)


# ================================================================ local-only: signatures with a real token

if not HOSTED:

    @mcp.tool(annotations=RO)
    def max_verify_signature(
        kind: Annotated[Literal["init_data", "phone", "contact"], Field(description="init_data — mini-app launch data; phone — Bridge requestContact() result; contact — contact attachment from a request_contact button")],
        init_data: Annotated[str | None, Field(description="init_data: raw window.WebApp.initData string")] = None,
        hash: Annotated[str | None, Field(description="phone/contact: the hash to check")] = None,
        phone: str | None = None,
        auth_date: Annotated[str | None, Field(description="phone: authDate from requestContact()")] = None,
        user_id: Annotated[str | None, Field(description="phone: MAX user id")] = None,
        vcf_info: Annotated[str | None, Field(description="contact: vcf_info exactly as received, JSON-decoded")] = None,
        max_age_seconds: Annotated[int, Field(ge=0, description="init_data freshness window")] = 3600,
        bot_token: Annotated[str | None, Field(description="Bot token; defaults to MAX_BOT_TOKEN from the environment")] = None,
        lang: LangParam = None,
    ) -> dict:
        """Verify a MAX signature locally: mini-app initData (two-step HMAC), requestContact phone hash, or the hash of a
        contact shared through a request_contact button. Explains why a check failed (wrong formula, double decoding, stale auth_date).
        Available only when the server runs on your machine."""
        set_lang(lang)
        tok = bot_token or client.token()
        if not tok:
            return {"error": "no_token", "message": tr("Передайте bot_token или задайте MAX_BOT_TOKEN", "Pass bot_token or set MAX_BOT_TOKEN")}
        if kind == "init_data":
            if not init_data:
                return {"error": "need_init_data"}
            return security.verify_init_data(init_data, tok, max_age_seconds)
        if kind == "phone":
            if not (hash and phone and auth_date and user_id):
                return {"error": "need_fields", "message": tr("Нужны hash, phone, auth_date, user_id", "Needs hash, phone, auth_date, user_id")}
            return security.verify_phone(auth_date, phone, user_id, hash, tok)
        if not (hash and vcf_info):
            return {"error": "need_fields", "message": tr("Нужны hash и vcf_info", "Needs hash and vcf_info")}
        return security.verify_contact(vcf_info, hash, tok)


# ================================================================ local-only: operator (acts as the user's bot)

if OPERATOR:

    async def _call(verb: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        try:
            return await client.request(verb, path, params, body)
        except client.MaxError as e:
            return _err(e)

    @mcp.tool(annotations=NET_RO)
    async def max_bot_info(lang: LangParam = None) -> dict:
        """Info about the bot whose token is in MAX_BOT_TOKEN (GET /me): id, name, username, commands."""
        set_lang(lang)
        return await _call("GET", "/me")

    @mcp.tool(annotations=NET_WRITE)
    async def max_send_message(
        text: Annotated[str, Field(description="Message text, up to 4000 chars")],
        chat_id: Annotated[int | None, Field(description="Group chat or channel id")] = None,
        user_id: Annotated[int | None, Field(description="User id for a private dialog")] = None,
        format: Literal["markdown", "html"] | None = None,
        buttons: Annotated[list[list[dict]] | None, Field(description="Rows of buttons, same short form as max_build_message")] = None,
        disable_link_preview: bool = False,
        notify: bool = True,
        lang: LangParam = None,
    ) -> dict:
        """Send a message as your bot (POST /messages). Validates the body first and refuses to send an invalid one."""
        set_lang(lang)
        if (chat_id is None) == (user_id is None):
            return {"error": "recipient", "message": tr("Укажите ровно одно: chat_id или user_id", "Give exactly one of chat_id or user_id")}
        body: dict[str, Any] = {"text": text, "notify": notify}
        if format:
            body["format"] = format
        if buttons:
            body["attachments"] = [messages.build_keyboard(buttons)]
        check = messages.validate_body(body)
        if not check["valid"]:
            return {"error": "invalid_body", "validation": check}
        return await _call("POST", "/messages", {"chat_id": chat_id, "user_id": user_id, "disable_link_preview": disable_link_preview or None}, body)

    @mcp.tool(annotations=NET_RO)
    async def max_get_messages(
        chat_id: int,
        count: Annotated[int, Field(ge=1, le=100)] = 20,
        lang: LangParam = None,
    ) -> dict:
        """Recent messages in a chat the bot belongs to (GET /messages), newest first."""
        set_lang(lang)
        return await _call("GET", "/messages", {"chat_id": chat_id, "count": count})

    @mcp.tool(annotations=NET_RO)
    async def max_get_chat(chat_id: int, lang: LangParam = None) -> dict:
        """Info about one chat or channel (GET /chats/{chatId}) and the bot's own membership and permissions."""
        set_lang(lang)
        chat = await _call("GET", f"/chats/{chat_id}")
        me = await _call("GET", f"/chats/{chat_id}/members/me")
        return {"chat": chat, "bot_membership": me}

    @mcp.tool(annotations=NET_WRITE)
    async def max_set_commands(
        commands: Annotated[list[dict], Field(description="[{name, description}], up to 32; empty list removes all")],
        lang: LangParam = None,
    ) -> dict:
        """Replace the bot's command list shown to users (PATCH /me/commands)."""
        set_lang(lang)
        if len(commands) > 32:
            return {"error": "too_many", "message": tr("Максимум 32 команды", "At most 32 commands")}
        for c in commands:
            n, d = str(c.get("name", "")).lstrip("/"), str(c.get("description", ""))
            if not (1 <= len(n) <= 64 and 1 <= len(d) <= 128):
                return {"error": "bad_command", "message": f"name 1-64, description 1-128: {c}"}
            c["name"] = n
        return await _call("PATCH", "/me/commands", body={"commands": commands})

    @mcp.tool(annotations=NET_DESTRUCTIVE)
    async def max_webhook(
        action: Annotated[Literal["list", "subscribe", "unsubscribe"], Field(description="list current subscriptions, subscribe a URL, or unsubscribe it")],
        url: Annotated[str | None, Field(description="https URL on port 443")] = None,
        secret: Annotated[str | None, Field(description="subscribe: 5-256 chars A-Za-z0-9_-; generated if omitted")] = None,
        update_types: Annotated[list[str] | None, Field(description="subscribe: which update types; omit for all")] = None,
        lang: LangParam = None,
    ) -> dict:
        """Manage the bot's webhook subscription (GET/POST/DELETE /subscriptions). Checks the URL against MAX rules
        (https, port 443) before subscribing. Subscribing stops long polling from working."""
        set_lang(lang)
        if action == "list":
            return await _call("GET", "/subscriptions")
        if not url:
            return {"error": "need_url"}
        if action == "unsubscribe":
            return await _call("DELETE", "/subscriptions", {"url": url})
        if not url.startswith("https://"):
            return {"error": "bad_url", "message": tr("Только https://", "https:// only")}
        host = url.split("/")[2]
        if ":" in host and not host.endswith(":443"):
            return {"error": "bad_port", "message": tr("MAX доставляет только на порт 443 — уберите порт из адреса",
                                                       "MAX delivers to port 443 only — drop the port from the URL")}
        bad = [t for t in (update_types or []) if t not in knowledge.UPDATE_TYPES]
        if bad:
            return {"error": "bad_update_types", "unknown": bad}
        secret = secret or secrets.token_urlsafe(32)
        if not security.WEBHOOK_SECRET.match(secret):
            return {"error": "bad_secret", "message": tr("5-256 символов, A-Z a-z 0-9 _ -", "5-256 characters, A-Z a-z 0-9 _ -")}
        body: dict[str, Any] = {"url": url, "secret": secret}
        if update_types:
            body["update_types"] = update_types
        res = await _call("POST", "/subscriptions", body=body)
        return {"result": res, "secret": secret,
                "remember": tr("Проверяйте заголовок X-Max-Bot-Api-Secret за постоянное время",
                               "Check the X-Max-Bot-Api-Secret header in constant time")}

    @mcp.tool(annotations=NET_RO)
    async def max_get_updates(
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        timeout: Annotated[int, Field(ge=0, le=30, description="Seconds to wait for new updates")] = 0,
        marker: int | None = None,
        lang: LangParam = None,
    ) -> dict:
        """Fetch pending updates by long polling (GET /updates) to see what the bot receives. Development only;
        does not work while a webhook is subscribed. Pass the returned marker next time to acknowledge."""
        set_lang(lang)
        return await _call("GET", "/updates", {"limit": limit, "timeout": timeout, "marker": marker})

    @mcp.tool(annotations=NET_DESTRUCTIVE)
    async def max_api_request(
        verb: Annotated[Literal["GET", "POST", "PUT", "PATCH", "DELETE"], Field(description="HTTP method")],
        path: Annotated[str, Field(description="Documented path, e.g. /chats/-123/pin, /messages")],
        query: Annotated[dict | None, Field(description="Query parameters")] = None,
        body: Annotated[dict | None, Field(description="JSON body")] = None,
        lang: LangParam = None,
    ) -> dict:
        """Call any documented MAX Bot API method as your bot (edit or delete messages, pin, manage admins, comments…).
        Only methods present in the docs are allowed; removed ones are refused with the replacement."""
        set_lang(lang)
        if verb in ("POST", "PUT") and path.rstrip("/") == "/messages" and body:
            check = messages.validate_body(body)
            if not check["valid"]:
                return {"error": "invalid_body", "validation": check}
        return await _call(verb, path, query, body)


# ================================================================ HTTP extras

@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "version": __version__})


@mcp.custom_route("/.well-known/mcp/server-card.json", methods=["GET"], include_in_schema=False)
async def server_card(_: Request) -> JSONResponse:
    tools = await mcp.list_tools()
    return JSONResponse({
        "serverInfo": {"name": "xonta-max", "title": "Xonta MAX", "version": __version__},
        "description": "Build bots and mini-apps for the MAX messenger (max.ru). English and Russian",
        "transport": {"type": "streamable-http", "url": "https://mcp.xonta.ru/max/mcp"},
        "tools": [{"name": t.name, "description": (t.description or "").split("\n")[0]} for t in tools],
        "repository": "https://github.com/mrsergeiluzhnov/xonta-max-mcp",
    })


def main() -> None:
    ap = argparse.ArgumentParser(prog="xonta-max-mcp")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8766")))
    args = ap.parse_args()
    if args.http and OPERATOR and args.host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Operator tools act as your bot: with MAX_BOT_TOKEN set, serve HTTP only on 127.0.0.1, "
                         "or set XONTA_MAX_HOSTED=1 to run the public server without them.")
    if not args.http:
        mcp.run("stdio")
        return

    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
    security_cfg = (
        TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts + ["127.0.0.1:*", "localhost:*"])
        if hosts else TransportSecuritySettings(enable_dns_rebinding_protection=False)
    )
    app = mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True,
                                  transport_security=security_cfg, host=args.host)
    from .web import BrowserCard

    app = BrowserCard(app, os.environ.get("PUBLIC_MCP_URL", "https://mcp.xonta.ru/max/mcp"))
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
