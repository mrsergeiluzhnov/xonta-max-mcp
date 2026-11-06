"""Every tool answers fully in English with lang='en' and in Russian with lang='ru'."""

import importlib
import json
import re

import httpx
import pytest

from xonta_max import knowledge, lint, scaffold

CYR = re.compile("[А-Яа-яЁё]")

TG_CODE = """
from aiogram import Bot
await bot.send_message(chat_id, "<b>hi</b>", parse_mode="HTML", reply_markup=kb)
await bot.answer_callback_query(cq.id)
await bot.send_poll(chat_id, "q", ["a"])
r = requests.get("https://platform-api.max.ru/chats?access_token=x", verify=False)
"""

# every tool with arguments that exercise its text paths, including errors
CALLS = [
    ("max_api_reference", {}),
    ("max_api_reference", {"query": "webhook certificate"}),
    ("max_api_reference", {"query": "zzzz-nothing"}),
    *[("max_api_reference", {"topic": t}) for t in knowledge.TOPICS],
    ("max_endpoint_info", {}),
    ("max_endpoint_info", {"verb": "GET", "path": "/chats"}),
    ("max_endpoint_info", {"verb": "POST", "path": "/nope"}),
    *[("max_endpoint_info", {"verb": e["verb"], "path": e["path"]}) for e in knowledge.ENDPOINTS],
    ("max_limits", {}),
    ("max_changelog", {}),
    ("max_lint_code", {"code": TG_CODE}),
    ("max_lint_code", {"code": 'base = "https://platform-api2.max.ru"'}),
    ("max_migrate_from_telegram", {"code": TG_CODE}),
    ("max_migrate_from_telegram", {}),
    ("max_scaffold_bot", {"language": "python"}),
    ("max_scaffold_bot", {"language": "typescript"}),
    ("max_scaffold_bot", {"language": "go"}),
    ("max_validate_message", {"body": {
        "chat_id": 1, "disable_link_preview": True, "parse_mode": "HTML", "text": "x" * 4001, "format": "bad",
        "link": {"type": "x"}, "notify": False,
        "attachments": [
            {"type": "photo", "payload": {}}, {"type": "zzz"}, "str",
            {"type": "file", "payload": {}}, {"type": "file", "payload": {}},
            {"type": "audio", "payload": {}}, {"type": "sticker", "payload": {}}, {"type": "location", "payload": {}},
            *[{"type": "image", "payload": {"url": "u"}} for _ in range(13)],
            {"type": "inline_keyboard", "payload": {"buttons": [[{"type": "link", "text": "", "url": "ftp://x" + "x" * 2050}] * 4, [], "row",
                                                                [{"type": "open_app", "text": "a", "web_app": "b", "payload": "bad payload"},
                                                                 {"type": "callback", "text": "c", "callback_data": "x", "payload": "p" * 1100},
                                                                 {"type": "unknown", "text": "u"}, "notdict"]] + [[{"type": "message", "text": "m"}]] * 30}},
            {"type": "inline_keyboard", "payload": {"buttons": []}},
        ]}, "chat_type": "channel"}),
    ("max_validate_message", {"body": {"text": "**md** - item\n||sp||", "format": "markdown"}}),
    ("max_validate_message", {"body": {"text": "**raw**"}}),
    ("max_validate_message", {"body": {}}),
    ("max_validate_message", {"body": {"text": "[l](https://x) ", "attachments": [{"type": "image"}], "link": {"type": "forward", "mid": "m"}}, "target": "comment"}),
    ("max_validate_message", {"body": {"text": "v", "attachments": [{"type": "video", "payload": {"token": "t"}}, {"type": "contact", "payload": {}}]}}),
    ("max_build_message", {"text": "Order ready", "buttons": [[{"text": "Pay", "url": "https://x.ru"}]]}),
    ("max_split_text", {"text": "word " * 2000}),
    ("max_convert_formatting", {"text": "*b* __u__ ||s|| [m](tg://user?id=1)\n**>q", "source": "telegram_markdownv2"}),
    ("max_convert_formatting", {"text": "<b>b</b><tg-spoiler>s</tg-spoiler><tg-emoji emoji-id='1'>x</tg-emoji>", "source": "telegram_html"}),
    ("max_convert_formatting", {"text": "- a\n|t|t|\n---\n![i](u)\n```a\nb```" + "x" * 4100, "source": "markdown", "target": "max_html"}),
    ("max_deeplink", {"kind": "start", "bot_name": "b_bot", "payload": "a b"}),
    ("max_deeplink", {"kind": "start", "bot_name": "b_bot", "payload": "x" * 200}),
    ("max_deeplink", {"kind": "start", "bot_name": "!!"}),
    ("max_deeplink", {"kind": "startapp", "bot_name": "b_bot", "payload": "a b"}),
    ("max_deeplink", {"kind": "startapp", "bot_name": "b_bot", "payload": "ok"}),
    ("max_deeplink", {"kind": "share", "text": "hello " * 2000}),
    ("max_deeplink", {"kind": "share"}),
    ("max_deeplink", {"kind": "mention", "user_id": 5}),
    ("max_deeplink", {"kind": "mention"}),
    *[("max_mock_update", {"update_type": t, "webhook_url": "http://localhost/h", "secret": "abcde"}) for t in knowledge.UPDATE_TYPES],
    ("max_mock_update", {"update_type": "nope"}),
    ("max_mock_init_data", {"start_param": "p"}),
    ("max_mock_init_data", {"start_param": "bad param"}),
    ("max_bridge_mock", {"test_bot_token": "t"}),
    ("max_bridge_mock", {}),
    ("max_check_webhook_secret", {}),
    ("max_check_webhook_secret", {"secret": "a"}),
    ("server_status", {}),
    ("max_verify_signature", {"kind": "init_data", "init_data": "a=1&hash=x", "bot_token": "t"}),
    ("max_verify_signature", {"kind": "init_data", "init_data": "auth_date=1&hash=x%2525", "bot_token": "t"}),
    ("max_verify_signature", {"kind": "init_data", "init_data": "auth_date=z&hash=x", "bot_token": "t"}),
    ("max_verify_signature", {"kind": "phone", "bot_token": "t"}),
    ("max_verify_signature", {"kind": "contact", "bot_token": "t"}),
    ("max_verify_signature", {"kind": "contact", "bot_token": "t", "hash": "x", "vcf_info": "A\\r\\nB"}),
    ("max_verify_signature", {"kind": "init_data"}),
]

OPERATOR_CALLS = [
    ("max_bot_info", {}),
    ("max_send_message", {"text": "hi"}),
    ("max_send_message", {"text": "x" * 4001, "chat_id": 1}),
    ("max_send_message", {"text": "hi", "chat_id": 1}),
    ("max_get_messages", {"chat_id": 1}),
    ("max_get_chat", {"chat_id": 1}),
    ("max_set_commands", {"commands": [{"name": "a", "description": "b"}] * 33}),
    ("max_set_commands", {"commands": [{"name": "", "description": "b"}]}),
    ("max_webhook", {"action": "subscribe", "url": "http://x.ru"}),
    ("max_webhook", {"action": "subscribe", "url": "https://x.ru:8443/h"}),
    ("max_webhook", {"action": "subscribe", "url": "https://x.ru/h", "secret": "a"}),
    ("max_webhook", {"action": "subscribe", "url": "https://x.ru/h"}),
    ("max_get_updates", {}),
    ("max_api_request", {"verb": "GET", "path": "/chats"}),
    ("max_api_request", {"verb": "POST", "path": "/webhook"}),
    ("max_api_request", {"verb": "POST", "path": "/sendMessage"}),
    ("max_api_request", {"verb": "POST", "path": "/chats/1/members", "body": {"user_ids": [1]}}),
    ("max_api_request", {"verb": "GET", "path": "/chats/1"}),
    ("max_api_request", {"verb": "GET", "path": "/me"}),
]


def _out(res):
    if isinstance(res, tuple):
        res = res[1] if isinstance(res[1], dict) else res[0]
    if isinstance(res, dict):
        return res.get("result", res)
    return json.loads(res[0].text) if isinstance(res, list) else json.loads(res.content[0].text)


def _russian_bits(obj, path="$"):
    """Yield (path, text) for every string that has Cyrillic."""
    if isinstance(obj, str):
        if CYR.search(obj):
            yield path, obj[:160]
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _russian_bits(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _russian_bits(v, f"{path}[{i}]")


@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("MAX_BOT_TOKEN", "tok")
    monkeypatch.delenv("XONTA_MAX_HOSTED", raising=False)
    from xonta_max import client
    import xonta_max.server as srv

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/me":
            return httpx.Response(200, json={"user_id": 1, "first_name": "Bot", "is_bot": True})
        if req.url.path == "/chats/1":
            return httpx.Response(404, json={"code": "not.found", "message": "Chat not found"})
        if req.url.path == "/chats/1/members":
            return httpx.Response(200, json={"success": True})
        if req.url.path == "/messages" and req.method == "GET":
            return httpx.Response(401, json={"code": "verify.token", "message": "Invalid access_token"})
        return httpx.Response(200, json={"success": True})

    monkeypatch.setattr(client, "_TRANSPORT", httpx.MockTransport(handler))
    mod = importlib.reload(srv)
    yield mod.mcp
    monkeypatch.delenv("MAX_BOT_TOKEN")
    importlib.reload(srv)


@pytest.mark.asyncio
async def test_english_has_no_russian(server):
    problems = []
    for name, args in CALLS + OPERATOR_CALLS:
        res = _out(await server.call_tool(name, {**args, "lang": "en"}))
        for path, text in _russian_bits(res):
            problems.append(f"{name} {path}: {text}")
    assert not problems, "\n".join(problems[:40])


@pytest.mark.asyncio
async def test_russian_default_and_explicit(server):
    for lang in (None, "ru"):
        args = {"code": TG_CODE} | ({"lang": lang} if lang else {})
        res = _out(await server.call_tool("max_lint_code", args))
        assert CYR.search(res["summary"])
        assert CYR.search(res["findings"][0]["message"])
    ref = _out(await server.call_tool("max_api_reference", {"topic": "tls"}))
    assert "Минцифры" in ref["text"]
    en = _out(await server.call_tool("max_api_reference", {"topic": "tls", "lang": "en"}))
    assert "Russian Trusted Root CA" in en["text"] and en["title"] == "Russian Trusted Root CA"


@pytest.mark.asyncio
async def test_language_does_not_leak_between_calls(server):
    a = _out(await server.call_tool("max_changelog", {"lang": "en"}))
    b = _out(await server.call_tool("max_changelog", {}))
    assert not CYR.search(a["changes"][0]["change"]) and CYR.search(b["changes"][0]["change"])


def test_every_bilingual_field_is_filled():
    for e in knowledge.ENDPOINTS:
        assert e["summary_en"] and not CYR.search(e["summary_en"])
        if any(CYR.search(v) for v in e["query"].values()):
            assert "query_en" in e, e["path"]
    for group in (knowledge.LIMITS, knowledge.ERRORS, knowledge.CHANGELOG, list(knowledge.TOPICS.values()),
                  list(knowledge.UPDATE_TYPES.values()), list(knowledge.BUTTON_TYPES.values()), lint.TELEGRAM_MAP):
        for item in group:
            for k, v in item.items():
                if isinstance(v, str) and CYR.search(v):
                    assert not CYR.search(item.get(f"{k}_en", "Я")), (k, v[:60])
    for r in lint.LINT_RULES + lint.TELEGRAM_RULES:
        assert not CYR.search(r.message_en + r.fix_en), r.id


def test_scaffold_english_has_no_russian():
    for language in ("python", "typescript", "go"):
        for name, content in scaffold.scaffold(language, "en").items():
            assert not CYR.search(content), (language, name, CYR.search(content))


def test_env_default_language():
    import os
    import subprocess
    import sys
    code = "from xonta_max import server; r = server.max_changelog(); print(r['changes'][0]['change'])"
    out = subprocess.run([sys.executable, "-c", code], env={**os.environ, "XONTA_MAX_LANG": "en"},
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() and not CYR.search(out)


def test_english_scaffold_strings_stay_valid():
    # TS template uses single-quoted strings: an apostrophe in a replacement would break it
    for ru, en in scaffold.EN:
        if ru in scaffold.TS_BOT:
            assert "'" not in en, en
    compile(scaffold.scaffold("python", "en")["bot.py"], "bot.py", "exec")
