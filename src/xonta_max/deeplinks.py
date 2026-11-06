"""MAX deep links: bot start, mini-app startapp, share-to-MAX, user mention."""

from __future__ import annotations

import html
import re
from urllib.parse import quote

BOT_NAME = re.compile(r"^[A-Za-z0-9_]{3,64}$")
STARTAPP = re.compile(r"^[A-Za-z0-9_-]*$")


def _bot(bot_name: str) -> str:
    b = bot_name.strip().removeprefix("https://max.ru/").removeprefix("max.ru/").lstrip("@").split("?")[0]
    if not BOT_NAME.match(b):
        raise ValueError("Имя бота: латиница, цифры и _, как в ссылке max.ru/<имя>")
    return b


def build(kind: str, bot_name: str | None = None, payload: str | None = None, text: str | None = None,
          user_id: int | None = None, button_label: str = "Отправить в MAX") -> dict:
    warnings: list[str] = []
    if kind == "start":
        b = _bot(bot_name or "")
        url = f"https://max.ru/{b}"
        if payload:
            if len(payload) > 128:
                raise ValueError(f"payload {len(payload)} символов: для ?start= максимум 128, иначе он не дойдёт до бота")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", payload):
                warnings.append("Безопаснее держать payload в A-Za-z0-9_- — другие символы будут закодированы")
            url += "?start=" + quote(payload, safe="")
        return {"url": url, "arrives_as": "update bot_started.payload", "warnings": warnings}

    if kind == "startapp":
        b = _bot(bot_name or "")
        url = f"https://max.ru/{b}?startapp"
        if payload:
            if len(payload) > 512 or not STARTAPP.match(payload):
                raise ValueError("payload для ?startapp= — до 512 символов и только A-Za-z0-9_-; иначе MAX молча его отбросит")
            url += "=" + payload
        return {"url": url, "arrives_as": "initData.start_param в мини-приложении", "warnings": warnings}

    if kind == "share":
        if not text:
            raise ValueError("Для share нужен text")
        url = "https://max.ru/:share?text=" + quote(text, safe="")
        if len(url) > 8000:
            warnings.append("Очень длинная ссылка — часть браузеров и клиентов её обрежет; лучше поделиться ссылкой на страницу")
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
            "note": "Бот не нужен. Открывает выбор чата в MAX с готовым текстом. В мини-приложении вместо ссылки используйте WebApp.shareMaxContent({text}).",
            "warnings": warnings,
        }

    if kind == "mention":
        if not user_id:
            raise ValueError("Для mention нужен user_id")
        name = text or "Имя Фамилия"
        return {
            "markdown": f"[{name}](max://user/{user_id})",
            "html": f'<a href="max://user/{user_id}">{html.escape(name)}</a>',
            "note": "В тексте ссылки — полное имя из профиля MAX. В комментариях упоминания не работают.",
            "warnings": warnings,
        }

    raise ValueError("kind: start | startapp | share | mention")
