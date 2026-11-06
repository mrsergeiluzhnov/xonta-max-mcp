"""MAX deep links: bot start, mini-app startapp, share-to-MAX, user mention."""

from __future__ import annotations

import html
import re
from urllib.parse import quote

from .i18n import tr

BOT_NAME = re.compile(r"^[A-Za-z0-9_]{3,64}$")
STARTAPP = re.compile(r"^[A-Za-z0-9_-]*$")


def _bot(bot_name: str) -> str:
    b = bot_name.strip().removeprefix("https://max.ru/").removeprefix("max.ru/").lstrip("@").split("?")[0]
    if not BOT_NAME.match(b):
        raise ValueError(tr("Имя бота: латиница, цифры и _, как в ссылке max.ru/<имя>", "Bot name: Latin letters, digits and _, as in max.ru/<name>"))
    return b


def build(kind: str, bot_name: str | None = None, payload: str | None = None, text: str | None = None,
          user_id: int | None = None, button_label: str | None = None) -> dict:
    button_label = button_label or tr("Отправить в MAX", "Share to MAX")
    warnings: list[str] = []
    if kind == "start":
        b = _bot(bot_name or "")
        url = f"https://max.ru/{b}"
        if payload:
            if len(payload) > 128:
                raise ValueError(tr(f"payload {len(payload)} символов: для ?start= максимум 128, иначе он не дойдёт до бота", f"payload is {len(payload)} characters: ?start= allows 128, longer never reaches the bot"))
            if not re.fullmatch(r"[A-Za-z0-9_-]+", payload):
                warnings.append(tr("Безопаснее держать payload в A-Za-z0-9_- — другие символы будут закодированы", "Keep payload to A-Za-z0-9_- — other characters get encoded"))
            url += "?start=" + quote(payload, safe="")
        return {"url": url, "arrives_as": tr("событие bot_started, поле payload", "update bot_started, field payload"), "warnings": warnings}

    if kind == "startapp":
        b = _bot(bot_name or "")
        url = f"https://max.ru/{b}?startapp"
        if payload:
            if len(payload) > 512 or not STARTAPP.match(payload):
                raise ValueError(tr("payload для ?startapp= — до 512 символов и только A-Za-z0-9_-; иначе MAX молча его отбросит", "?startapp= payload: up to 512 characters, A-Za-z0-9_- only; otherwise MAX silently drops it"))
            url += "=" + payload
        return {"url": url, "arrives_as": tr("initData.start_param в мини-приложении", "initData.start_param in the mini-app"), "warnings": warnings}

    if kind == "share":
        if not text:
            raise ValueError(tr("Для share нужен text", "share needs text"))
        url = "https://max.ru/:share?text=" + quote(text, safe="")
        if len(url) > 8000:
            warnings.append(tr("Очень длинная ссылка — часть браузеров и клиентов её обрежет; лучше поделиться ссылкой на страницу", "Very long link — some browsers and clients will cut it; share a page link instead"))
        esc = html.escape(url, quote=True)
        widget = (
            f'<a href="{esc}" target="_blank" rel="noopener" '
            'style="display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;'
            'background:#0077ff;color:#fff;font:600 15px/1 system-ui,sans-serif;text-decoration:none">'
            f"{html.escape(button_label)}</a>"
        )
        js = (
            "function shareToMax(text){window.open('https://max.ru/:share?text='+encodeURIComponent(text),'_blank','noopener');}"
        )
        return {
            "url": url, "html_button": widget, "js_helper": js,
            "note": tr("Бот не нужен. Открывает выбор чата в MAX с готовым текстом. В мини-приложении вместо ссылки используйте WebApp.shareMaxContent({text}).", "No bot needed. Opens the MAX chat picker with the text filled in. Inside a mini-app use WebApp.shareMaxContent({text}) instead."),
            "warnings": warnings,
        }

    if kind == "mention":
        if not user_id:
            raise ValueError(tr("Для mention нужен user_id", "mention needs user_id"))
        name = text or tr("Имя Фамилия", "First Last")
        return {
            "markdown": f"[{name}](max://user/{user_id})",
            "html": f'<a href="max://user/{user_id}">{html.escape(name)}</a>',
            "note": tr("В тексте ссылки — полное имя из профиля MAX. В комментариях упоминания не работают.", "Use the full name from the MAX profile as link text. Mentions don't work in comments."),
            "warnings": warnings,
        }

    raise ValueError("kind: start | startapp | share | mention")
