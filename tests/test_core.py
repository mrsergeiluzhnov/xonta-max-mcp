import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, quote, urlencode

import pytest

from xonta_max import deeplinks, knowledge, lint, messages, mocks, scaffold, security

TG_BOT = """
import aiogram
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
API = "https://api.telegram.org/bot{token}/sendMessage"

async def start(message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Да", callback_data="yes")]])
    await bot.send_message(message.chat.id, "<b>Hi</b> <a href='tg://user?id=42'>you</a>", parse_mode="HTML", reply_markup=kb)
    await bot.send_photo(message.chat.id, photo)
    await bot.send_poll(message.chat.id, "Q?", ["a", "b"])

async def on_cb(callback_query):
    await bot.answer_callback_query(callback_query.id, "ok")
    await bot.edit_message_text("done", chat_id=1, message_id=2)
"""

BAD_MAX = """
import requests
r = requests.get("https://platform-api.max.ru/chats?access_token=" + TOKEN, verify=False)
requests.post("https://platform-api2.max.ru/uploads?type=photo", headers={"Authorization": f"Bearer {TOKEN}"})
if request.headers["X-Max-Bot-Api-Secret"] == SECRET:
    pass
body = {"text": "x", "disable_link_preview": True}
requests.post("https://platform-api2.max.ru/subscriptions", json={"url": "http://bot.example.ru:8443/hook"})
"""


def test_lint_finds_known_mistakes():
    res = lint.lint(BAD_MAX)
    rules = {f["rule"] for f in res["findings"]}
    for r in ["old-host", "token-in-query", "tls-disabled", "bearer-prefix", "upload-photo-type",
              "secret-plain-compare", "link-preview-in-body", "webhook-port", "http-webhook"]:
        assert r in rules, r
    first = next(f for f in res["findings"] if f["rule"] == "old-host")
    assert first["occurrences"][0]["line"] == 3


def test_lint_clean_code_is_clean():
    good = 'httpx.AsyncClient(base_url="https://platform-api2.max.ru", headers={"Authorization": token}, verify=ca)\n'
    res = lint.lint(good)
    assert res["errors"] == 0 and res["warnings"] == 0


def test_migration_report():
    res = lint.migrate(TG_BOT)
    rules = {i["rule"] for i in res["items"]}
    assert {"tg-host", "tg-sendMessage", "tg-media", "tg-answer-callback", "tg-reply-markup", "tg-edit",
            "tg-parse-mode", "tg-mention", "tg-no-equivalent", "tg-libs", "tg-callback-update"} <= rules
    assert any("send_poll" in x for x in res["features_without_equivalent"])
    assert res["plan"]


def test_validate_body_limits_and_combos():
    ok = {"text": "hi", "format": "markdown",
          "attachments": [{"type": "inline_keyboard", "payload": {"buttons": [[{"type": "callback", "text": "A", "payload": "a"}]]}}]}
    assert messages.validate_body(ok)["valid"]

    long = messages.validate_body({"text": "я" * 4001})
    assert not long["valid"] and "4000" in long["errors"][0]

    row = [{"type": "link", "text": f"L{i}", "url": "https://x.ru"} for i in range(4)]
    kb = messages.validate_body({"text": "x", "attachments": [{"type": "inline_keyboard", "payload": {"buttons": [row]}}]})
    assert any("максимум 3" in e for e in kb["errors"])

    eight = [{"type": "callback", "text": str(i), "payload": "p"} for i in range(8)]
    assert any("максимум 7" in e for e in messages.validate_body({"attachments": [messages.build_keyboard([eight])]})["errors"])

    combo = messages.validate_body({"attachments": [{"type": "file", "payload": {"token": "t"}}, {"type": "image", "payload": {"url": "https://x/1.png"}}]})
    assert any("file сочетается" in e for e in combo["errors"])

    tg = messages.validate_body({"text": "x", "parse_mode": "HTML", "chat_id": 1})
    assert len(tg["errors"]) >= 2

    media = messages.validate_body({"attachments": [{"type": "image", "payload": {"url": f"https://x/{i}.png"}} for i in range(13)]})
    assert any("максимум 12" in e for e in media["errors"])

    comment = messages.validate_body({"text": "[a](https://x.ru)", "attachments": [{"type": "image", "payload": {"url": "u"}}]}, is_comment=True)
    assert not comment["valid"]

    channel = messages.validate_body({"text": "x", "notify": False}, chat_type="channel")
    assert not channel["valid"]


def test_build_keyboard_short_form():
    kb = messages.build_keyboard([[{"text": "Да", "payload": "yes"}, {"text": "Сайт", "url": "https://xonta.ru"}],
                                  [{"text": "App", "web_app": "my_bot", "payload": "p1"}],
                                  [{"text": "Old", "callback_data": "x"}]])
    b = kb["payload"]["buttons"]
    assert b[0][0]["type"] == "callback" and b[0][1]["type"] == "link"
    assert b[1][0]["type"] == "open_app"
    assert b[2][0] == {"text": "Old", "payload": "x", "type": "callback"}
    assert messages.validate_keyboard(b) == []


def test_split_text():
    text = ("Абзац номер один. " * 150 + "\n\n") * 4
    parts = messages.split_text(text)
    assert all(len(p) <= 4000 for p in parts)
    assert "".join(parts).replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")


def test_convert_formatting():
    md2 = messages.convert_formatting(r"*bold* __under__ _it_ ~st~ ||spoiler|| [me](tg://user?id=7) 1\.5", "telegram_markdownv2", "max_markdown")
    assert md2["text"] == "**bold** ++under++ _it_ ~~st~~ spoiler [me](max://user/7) 1.5"
    assert md2["notes"]

    html_ = messages.convert_formatting('<b>Hi</b> <u>u</u> <a href="tg://user?id=5">x</a> <tg-spoiler>s</tg-spoiler>', "telegram_html", "max_html")
    assert html_["text"] == '<b>Hi</b> <u>u</u> <a href="max://user/5">x</a> s'
    to_md = messages.convert_formatting('<b>Hi</b> <u>u</u>', "telegram_html", "max_markdown")
    assert to_md["text"] == "**Hi** ++u++"

    llm = messages.convert_formatting("# Title\n- one\n- two\n---\n**b**", "markdown", "max_markdown")
    assert "• one" in llm["text"] and "---" not in llm["text"]
    h = messages.convert_formatting("**b** and `c` [l](https://x.ru)", "markdown", "max_html")
    assert h["text"] == '<b>b</b> and <code>c</code> <a href="https://x.ru">l</a>'


def _reference_validate(init_data: str, token: str) -> bool:
    """Independent implementation of the documented algorithm (as in the official TS sample)."""
    params = parse_qsl(init_data, keep_blank_values=True)
    received = dict(params)["hash"]
    check = "\n".join(sorted(f"{k}={v}" for k, v in params if k != "hash"))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, check.encode(), hashlib.sha256).hexdigest() == received


def test_init_data_roundtrip_and_failures():
    tok = "test-token-123"
    s = security.sign_init_data(tok, start_param="promo_1")
    assert _reference_validate(s["init_data"], tok)
    ok = security.verify_init_data(s["init_data"], tok)
    assert ok["valid"] and ok["data"]["user"]["first_name"] == "Тест" and ok["data"]["start_param"] == "promo_1"

    assert not security.verify_init_data(s["init_data"], "other")["valid"]
    old = security.sign_init_data(tok, auth_date=int(time.time()) - 7200)
    r = security.verify_init_data(old["init_data"], tok)
    assert not r["valid"] and "устарел" in r["reason"]
    double = s["init_data"].replace("%", "%25")
    r = security.verify_init_data(double, tok)
    assert not r["valid"] and "двойное" in r["reason"]

    with pytest.raises(ValueError):
        security.sign_init_data(tok, start_param="bad param!")


def test_init_data_matches_values_with_special_chars():
    tok = "t"
    fields = {"auth_date": str(int(time.time())), "query_id": "q", "user": json.dumps({"id": 1, "first_name": "Tom&Jerry=%"})}
    check = "\n".join(sorted(f"{k}={v}" for k, v in fields.items()))
    secret = hmac.new(b"WebAppData", tok.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    s = urlencode({**fields, "hash": h}, quote_via=quote)
    assert security.verify_init_data(s, tok)["valid"]


def test_phone_and_contact_hashes():
    tok = "abc"
    h = security.sign_phone("1700000000", "+79990000000", "42", tok)
    assert security.verify_phone("1700000000", "+79990000000", "42", h, tok)["valid"]
    assert security.verify_phone("1700000000", "79990000000", "42", h, tok)["valid"]
    assert not security.verify_phone("1700000000", "79990000001", "42", h, tok)["valid"]
    vcf = "BEGIN:VCARD\r\nVERSION:3.0\r\nTEL:+7999\r\nEND:VCARD"
    ch = hmac.new(tok.encode(), vcf.encode(), hashlib.sha256).hexdigest()
    assert security.verify_contact(vcf, ch, tok)["valid"]
    assert security.check_webhook_secret("abc")["valid"] is False
    assert security.check_webhook_secret("abc")["suggestion"]
    assert security.check_webhook_secret("good_secret-123")["valid"]


def test_deeplinks():
    assert deeplinks.build("start", "my_bot", "ref_42")["url"] == "https://max.ru/my_bot?start=ref_42"
    assert deeplinks.build("startapp", "https://max.ru/my_bot", "promo")["url"] == "https://max.ru/my_bot?startapp=promo"
    with pytest.raises(ValueError):
        deeplinks.build("start", "my_bot", "x" * 129)
    with pytest.raises(ValueError):
        deeplinks.build("startapp", "my_bot", "has space")
    sh = deeplinks.build("share", text="Привет мир & co")
    assert sh["url"] == "https://max.ru/:share?text=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%BC%D0%B8%D1%80%20%26%20co"
    assert "<a href=" in sh["html_button"]
    m = deeplinks.build("mention", user_id=7, text="Иван Петров")
    assert m["markdown"] == "[Иван Петров](max://user/7)"


def test_mock_updates_cover_all_types():
    for t in knowledge.UPDATE_TYPES:
        u = mocks.make_update(t)
        assert u["update_type"] == t and u["timestamp"]
    cb = mocks.make_update("message_callback", payload="buy:1")
    assert cb["callback"]["payload"] == "buy:1" and cb["callback"]["callback_id"]
    curl = mocks.curl_for(cb, "http://localhost:8080/max/webhook", "s3cret_xx")
    assert "X-Max-Bot-Api-Secret: s3cret_xx" in curl
    over = mocks.make_update("message_created", overrides={"message": {"body": {"text": "zzz"}}})
    assert over["message"]["body"]["text"] == "zzz" and over["message"]["body"]["mid"]


def test_knowledge_search_and_endpoints():
    assert knowledge.find_endpoint("PUT", "/chats/-123/pin")["path"] == "/chats/{chatId}/pin"
    assert knowledge.find_endpoint("GET", "/chats") is None
    assert knowledge.find_endpoint("DELETE", "/chats/1/members/admins/5")["path"].endswith("{userId}")
    hits = knowledge.search("attachment.not.ready")
    assert hits and any(h["kind"] == "error" for h in hits)
    assert knowledge.search("вебхук сертификат")[0]["kind"] in ("topic", "limit")


def test_scaffold_python_compiles():
    files = scaffold.scaffold("python")
    compile(files["bot.py"], "bot.py", "exec")
    assert "platform-api2.max.ru" in files["bot.py"] and "compare_digest" in files["bot.py"]
    for lang in ("typescript", "go"):
        f = scaffold.scaffold(lang)
        assert lint.lint("\n".join(f.values()))["errors"] == 0, lang
    assert lint.lint(files["bot.py"])["errors"] == 0
