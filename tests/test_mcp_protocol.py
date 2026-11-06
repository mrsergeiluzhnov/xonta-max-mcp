"""End-to-end over real MCP stdio, plus operator tools against a fake MAX API."""

import importlib
import json
import os
import sys

import httpx
import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.asyncio

PUBLIC = {
    "max_api_reference", "max_endpoint_info", "max_limits", "max_changelog", "max_lint_code",
    "max_migrate_from_telegram", "max_scaffold_bot", "max_validate_message", "max_build_message",
    "max_split_text", "max_convert_formatting", "max_deeplink", "max_mock_update", "max_mock_init_data",
    "max_bridge_mock", "max_check_webhook_secret", "server_status",
    "max_tracking_links", "max_ad_report", "max_check_ad_post",
}
OPERATOR = {"max_bot_info", "max_send_message", "max_get_messages", "max_get_chat", "max_set_commands",
            "max_webhook", "max_get_updates", "max_api_request"}


def _payload(res):
    assert not res.is_error, res
    if res.structured_content is not None:
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


def _params(**env):
    e = {k: v for k, v in os.environ.items() if k not in ("MAX_BOT_TOKEN", "XONTA_MAX_HOSTED")}
    e.update(env)
    return StdioServerParameters(command=sys.executable, args=["-m", "xonta_max.server"], env=e)


async def test_hosted_mode_over_stdio():
    async with stdio_client(_params(XONTA_MAX_HOSTED="1", MAX_BOT_TOKEN="should-be-ignored")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name: t for t in (await s.list_tools()).tools}
            assert set(tools) == PUBLIC  # no token-taking tools on the public server
            for t in tools.values():
                assert t.description and len(t.description) > 40
                assert t.annotations.read_only_hint is True

            ref = _payload(await s.call_tool("max_api_reference", {"topic": "tls"}))
            assert "Минцифры" in ref["text"]
            ep = _payload(await s.call_tool("max_endpoint_info", {"verb": "GET", "path": "/chats"}))
            assert ep["exists"] is False and "bot_added" in ep["note"]

            lint = _payload(await s.call_tool("max_lint_code", {"code": 'url = "https://platform-api.max.ru/me?access_token=x"'}))
            assert lint["errors"] >= 2

            msg = _payload(await s.call_tool("max_build_message", {
                "text": "**Заказ** готов", "format": "markdown", "chat_id": -1,
                "buttons": [[{"text": "Оплатить", "url": "https://xonta.ru/pay"}, {"text": "Отмена", "payload": "cancel"}]],
            }))
            assert msg["validation"]["valid"] and "chat_id=-1" in msg["curl"]

            link = _payload(await s.call_tool("max_deeplink", {"kind": "startapp", "bot_name": "shop_bot", "payload": "bad payload"}))
            assert link["error"] == "ValueError"

            upd = _payload(await s.call_tool("max_mock_update", {"update_type": "bot_started", "payload": "ref_1",
                                                                  "webhook_url": "http://localhost:8080/max/webhook", "secret": "abcde"}))
            assert upd["update"]["payload"] == "ref_1" and "curl" in upd

            bridge = _payload(await s.call_tool("max_bridge_mock", {"platform": "web", "test_bot_token": "t", "start_param": "x1"}))
            assert "window.WebApp" in bridge["content"] and '"start_param": "x1"' in bridge["content"]

            files = _payload(await s.call_tool("max_scaffold_bot", {"language": "go"}))
            assert "main.go" in files["files"]

            st = _payload(await s.call_tool("server_status", {}))
            assert st["hosted"] is True and st["operator_tools"] is False


async def test_local_mode_has_signature_tool():
    async with stdio_client(_params()) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            assert names == PUBLIC | {"max_verify_signature"}
            init = _payload(await s.call_tool("max_mock_init_data", {"test_bot_token": "tok", "start_param": "p"}))
            ver = _payload(await s.call_tool("max_verify_signature", {"kind": "init_data", "init_data": init["init_data"], "bot_token": "tok"}))
            assert ver["valid"] is True
            bad = _payload(await s.call_tool("max_verify_signature", {"kind": "init_data", "init_data": init["init_data"], "bot_token": "nope"}))
            assert bad["valid"] is False


@pytest.fixture()
def operator_server(monkeypatch):
    monkeypatch.setenv("MAX_BOT_TOKEN", "tok-123")
    monkeypatch.delenv("XONTA_MAX_HOSTED", raising=False)
    from xonta_max import client, server
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert req.headers["authorization"] == "tok-123"
        assert req.url.host == "platform-api2.max.ru"
        if req.url.path == "/me":
            return httpx.Response(200, json={"user_id": 1, "first_name": "Bot", "is_bot": True})
        if req.url.path == "/messages" and req.method == "POST":
            return httpx.Response(200, json={"message": {"body": {"mid": "m1", "text": json.loads(req.content)["text"]}}})
        if req.url.path == "/subscriptions":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404, json={"code": "not.found", "message": "nope"})

    monkeypatch.setattr(client, "_TRANSPORT", httpx.MockTransport(handler))
    srv = importlib.reload(server)
    yield srv.mcp, calls
    monkeypatch.delenv("MAX_BOT_TOKEN")
    importlib.reload(server)


async def test_operator_tools(operator_server):
    mcp, calls = operator_server
    names = {t.name for t in await mcp.list_tools()}
    assert OPERATOR <= names

    def out(res):
        if isinstance(res, tuple):
            res = res[1] if isinstance(res[1], dict) else res[0]
        if isinstance(res, dict):
            return res.get("result", res)
        return json.loads(res[0].text) if isinstance(res, list) else json.loads(res.content[0].text)

    me = out(await mcp.call_tool("max_bot_info", {}))
    assert me["first_name"] == "Bot"

    sent = out(await mcp.call_tool("max_send_message", {"text": "hi", "chat_id": -5, "buttons": [[{"text": "A", "payload": "a"}]]}))
    assert sent["message"]["body"]["mid"] == "m1"
    req = calls[-1]
    assert req.url.params["chat_id"] == "-5"
    body = json.loads(req.content)
    assert body["attachments"][0]["type"] == "inline_keyboard" and "chat_id" not in body

    bad = out(await mcp.call_tool("max_send_message", {"text": "x" * 4001, "chat_id": 1}))
    assert bad["error"] == "invalid_body"

    hook = out(await mcp.call_tool("max_webhook", {"action": "subscribe", "url": "https://bot.example.ru:8443/hook"}))
    assert hook["error"] == "bad_port"
    hook = out(await mcp.call_tool("max_webhook", {"action": "subscribe", "url": "https://bot.example.ru/hook", "update_types": ["message_created"]}))
    assert hook["secret"] and json.loads(calls[-1].content)["secret"] == hook["secret"]

    removed = out(await mcp.call_tool("max_api_request", {"verb": "GET", "path": "/chats"}))
    assert "июне 2026" in removed["message"]
    unknown = out(await mcp.call_tool("max_api_request", {"verb": "POST", "path": "/sendMessage"}))
    assert unknown["error"] == "MaxError"
    nf = out(await mcp.call_tool("max_api_request", {"verb": "GET", "path": "/chats/77"}))
    assert "404" in nf["message"]
