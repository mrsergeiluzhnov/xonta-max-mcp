"""Build and validate MAX message bodies, keyboards and formatted text."""

from __future__ import annotations

import html
import re

from .knowledge import ATTACHMENT_TYPES, BUTTON_TYPES, WIDE_BUTTONS

TEXT_LIMIT = 4000
OPEN_APP_PAYLOAD = re.compile(r"^[\w-]*$", re.ASCII)


def validate_button(b: dict, where: str) -> list[str]:
    errs: list[str] = []
    if not isinstance(b, dict):
        return [f"{where}: кнопка должна быть объектом"]
    t = b.get("type")
    if t not in BUTTON_TYPES:
        return [f"{where}: неизвестный type={t!r}; допустимо: {', '.join(BUTTON_TYPES)}"]
    text = b.get("text")
    if not isinstance(text, str) or not (1 <= len(text) <= 128):
        errs.append(f"{where}: text обязателен, 1-128 символов")
    for f in BUTTON_TYPES[t]["required"]:
        if not b.get(f):
            errs.append(f"{where}: для {t} нужно поле {f}")
    if t in ("callback", "clipboard") and isinstance(b.get("payload"), str) and len(b["payload"]) > 1024:
        errs.append(f"{where}: payload длиннее 1024")
    if t == "link":
        url = b.get("url", "")
        if isinstance(url, str) and len(url) > 2048:
            errs.append(f"{where}: url длиннее 2048")
        if isinstance(url, str) and url and not re.match(r"^(https?://|max://)", url):
            errs.append(f"{where}: url должен начинаться с https:// или http://")
    if t == "open_app":
        p = b.get("payload")
        if p is not None and (len(p) > 512 or not OPEN_APP_PAYLOAD.match(p)):
            errs.append(f"{where}: payload open_app — до 512 символов, только A-Za-z0-9_-")
    if "callback_data" in b:
        errs.append(f"{where}: callback_data — это Telegram; в MAX поле называется payload")
    return errs


def validate_keyboard(buttons) -> list[str]:
    if not isinstance(buttons, list) or not buttons:
        return ["inline_keyboard: buttons — непустой массив рядов"]
    errs: list[str] = []
    if len(buttons) > 30:
        errs.append(f"inline_keyboard: {len(buttons)} рядов, максимум 30")
    total = 0
    for r, row in enumerate(buttons):
        if not isinstance(row, list) or not row:
            errs.append(f"ряд {r + 1}: должен быть непустым массивом кнопок")
            continue
        total += len(row)
        wide = any(isinstance(b, dict) and b.get("type") in WIDE_BUTTONS for b in row)
        cap = 3 if wide else 7
        if len(row) > cap:
            errs.append(f"ряд {r + 1}: {len(row)} кнопок, максимум {cap}" + (" (в ряду есть link/open_app/request_*)" if wide else ""))
        for c, b in enumerate(row):
            errs += validate_button(b, f"ряд {r + 1}, кнопка {c + 1}")
    if total > 210:
        errs.append(f"inline_keyboard: {total} кнопок, максимум 210")
    return errs


def validate_body(body: dict, *, is_comment: bool = False, chat_type: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(body, dict):
        return {"valid": False, "errors": ["Тело сообщения должно быть JSON-объектом"], "warnings": []}

    for k in ("chat_id", "user_id"):
        if k in body:
            errors.append(f"{k} передаётся в query (?{k}=…), а не в теле")
    if "disable_link_preview" in body:
        errors.append("disable_link_preview — query-параметр, в теле игнорируется")
    for tg in ("parse_mode", "reply_markup", "reply_to_message_id"):
        if tg in body:
            errors.append(f"{tg} — поле Telegram. В MAX: parse_mode → format, reply_markup → attachments inline_keyboard, reply_to_message_id → link {{type: reply, mid}}")

    text = body.get("text")
    if text is not None:
        if not isinstance(text, str):
            errors.append("text должен быть строкой")
        elif len(text) > TEXT_LIMIT:
            errors.append(f"text: {len(text)} символов, максимум {TEXT_LIMIT}. Разбейте через max_split_text.")
    fmt = body.get("format")
    if fmt is not None and fmt not in ("markdown", "html"):
        errors.append("format: только \"markdown\" или \"html\"")
    if isinstance(text, str) and fmt is None and re.search(r"\*\*|__|<b>|<i>|\[[^\]]+\]\(", text):
        warnings.append("В тексте есть разметка, но format не указан — пользователь увидит символы как есть")
    if isinstance(text, str) and fmt == "markdown" and re.search(r"^\s*(?:[-*+]|\d+[.)])\s", text, re.M):
        warnings.append("Списков в разметке MAX нет — строки уйдут как обычный текст")
    if isinstance(text, str) and fmt == "markdown" and "||" in text:
        warnings.append("Спойлеров (||…||) в MAX нет")

    link = body.get("link")
    if link is not None:
        if not isinstance(link, dict) or link.get("type") not in ("reply", "forward") or not link.get("mid"):
            errors.append("link: {type: \"reply\" | \"forward\", mid: \"<id сообщения>\"}")
        elif is_comment and link.get("type") == "forward":
            errors.append("В комментариях поддерживается только link.type = reply")

    if chat_type == "channel" and body.get("notify") is False:
        errors.append("В каналах notify нельзя выключить — уберите поле или поставьте true")

    atts = body.get("attachments")
    if is_comment and atts:
        errors.append("Комментарии не поддерживают вложения")
    if is_comment and isinstance(text, str) and re.search(r"\]\(|<a\s|max://user", text):
        errors.append("В комментариях нельзя ссылки и упоминания")
    if atts is not None and not is_comment:
        if not isinstance(atts, list):
            errors.append("attachments — массив")
        else:
            counts: dict[str, int] = {}
            for i, a in enumerate(atts):
                if not isinstance(a, dict):
                    errors.append(f"вложение {i + 1}: объект {{type, payload}}")
                    continue
                t = a.get("type")
                if t == "photo":
                    errors.append(f"вложение {i + 1}: type=photo устарел, используйте image")
                    t = "image"
                if t not in ATTACHMENT_TYPES:
                    errors.append(f"вложение {i + 1}: неизвестный type={t!r}")
                    continue
                counts[t] = counts.get(t, 0) + 1
                p = a.get("payload") or {}
                if t == "inline_keyboard":
                    errors += validate_keyboard(p.get("buttons"))
                elif t == "image":
                    keys = [k for k in ("url", "token", "photos") if p.get(k)]
                    if len(keys) != 1:
                        errors.append(f"вложение {i + 1}: image — ровно одно из url, token, photos")
                elif t in ("video", "audio", "file"):
                    if not p.get("token"):
                        errors.append(f"вложение {i + 1}: {t} — нужен token из POST /uploads")
                elif t == "sticker":
                    if not p.get("code"):
                        errors.append(f"вложение {i + 1}: sticker — нужен code")
                elif t == "location":
                    lat = a.get("latitude", p.get("latitude"))
                    lon = a.get("longitude", p.get("longitude"))
                    if lat is None or lon is None:
                        errors.append(f"вложение {i + 1}: location — нужны latitude и longitude")
            media = counts.get("image", 0) + counts.get("video", 0)
            if media > 12:
                errors.append(f"{media} фото и видео, максимум 12")
            if counts.get("inline_keyboard", 0) > 1:
                errors.append("Не больше одной inline_keyboard на сообщение")
            if counts.get("file", 0) > 1:
                errors.append("Только один file на сообщение")
            if counts.get("file") and (media or counts.get("audio") or counts.get("sticker") or counts.get("contact")):
                errors.append("file сочетается только с одной inline_keyboard")
            for solo in ("audio", "sticker", "contact"):
                if counts.get(solo) and sum(counts.values()) - (counts.get("inline_keyboard", 0) if solo == "contact" else 0) > 1:
                    errors.append(f"{solo} должен быть единственным вложением" + (" (допустима 1 клавиатура)" if solo == "contact" else ""))
            if (counts.get("video") or counts.get("audio") or counts.get("file")):
                warnings.append("После загрузки файл может быть не готов: при attachment.not.ready повторите отправку с паузой")

    if text in (None, "") and not atts:
        errors.append("Пустое сообщение: нужен text или attachments")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "text_length": len(text) if isinstance(text, str) else 0}


def build_keyboard(rows: list[list[dict]]) -> dict:
    """rows of simplified buttons → inline_keyboard attachment."""
    out = []
    for row in rows:
        r = []
        for b in row:
            b = dict(b)
            if "callback_data" in b and "payload" not in b:
                b["payload"] = b.pop("callback_data")
            if "type" not in b:
                b["type"] = "link" if "url" in b else "open_app" if "web_app" in b else "callback" if "payload" in b else "message"
            r.append(b)
        out.append(r)
    return {"type": "inline_keyboard", "payload": {"buttons": out}}


def split_text(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    """Split by paragraphs, then lines, then sentences, then hard cut. Keeps every chunk <= limit."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        window = rest[:limit]
        cut = -1
        for sep in ("\n\n", "\n", ". ", "! ", "? ", " "):
            pos = window.rfind(sep)
            if pos > limit * 0.3:
                cut = pos + len(sep)
                break
        if cut <= 0:
            cut = limit
        parts.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    if rest:
        parts.append(rest)
    return parts


# ---------------------------------------------------------------- formatting conversion

def _md2_unescape(s: str) -> str:
    return re.sub(r"\\([_*\[\]()~`>#+\-=|{}.!\\])", r"\1", s)


def convert_formatting(text: str, source: str, target: str) -> dict:
    """Convert Telegram MarkdownV2 / Telegram HTML / generic Markdown into MAX markdown or HTML."""
    notes: list[str] = []
    t = text
    if source == "telegram_html":
        if "<tg-spoiler>" in t or 'class="tg-spoiler"' in t:
            notes.append("Спойлеры убраны: в MAX их нет")
            t = re.sub(r"</?tg-spoiler>", "", t)
            t = re.sub(r'<span class="tg-spoiler">(.*?)</span>', r"\1", t, flags=re.S)
        if "<tg-emoji" in t:
            notes.append("Кастомные эмодзи заменены обычными")
            t = re.sub(r"<tg-emoji[^>]*>(.*?)</tg-emoji>", r"\1", t, flags=re.S)
        t = re.sub(r"tg://user\?id=(\d+)", r"max://user/\1", t)
        t = re.sub(r"<blockquote expandable>", "<blockquote>", t)
        if target == "max_html":
            return {"text": t, "format": "html", "notes": notes, "length": len(t)}
        # html → max markdown
        conv = [
            (r"<(?:b|strong)>(.*?)</(?:b|strong)>", r"**\1**"), (r"<(?:i|em)>(.*?)</(?:i|em)>", r"_\1_"),
            (r"<(?:u|ins)>(.*?)</(?:u|ins)>", r"++\1++"), (r"<(?:s|strike|del)>(.*?)</(?:s|strike|del)>", r"~~\1~~"),
            (r"<pre>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>", r"```\1```"), (r"<code>(.*?)</code>", r"`\1`"),
            (r'<a href="([^"]+)">(.*?)</a>', r"[\2](\1)"), (r"<blockquote>(.*?)</blockquote>", r"> \1"),
        ]
        for a, b in conv:
            t = re.sub(a, b, t, flags=re.S)
        t = html.unescape(t)
        return {"text": t, "format": "markdown", "notes": notes, "length": len(t)}

    if source == "telegram_markdownv2":
        # order matters: underline __x__ in MarkdownV2 is underline, not bold
        if "||" in t:
            notes.append("Спойлеры убраны: в MAX их нет")
            t = re.sub(r"\|\|(.+?)\|\|", r"\1", t, flags=re.S)
        t = re.sub(r"(?<![\\_])__(.+?)__", r"++\1++", t, flags=re.S)
        t = re.sub(r"(?<![\\*])\*(?!\*)(.+?)(?<!\\)\*", r"**\1**", t, flags=re.S)
        t = re.sub(r"(?<![\\_])_(?!_)(.+?)(?<!\\)_", r"_\1_", t, flags=re.S)
        t = re.sub(r"(?<!\\)~(.+?)(?<!\\)~", r"~~\1~~", t, flags=re.S)
        t = re.sub(r"tg://user\?id=(\d+)", r"max://user/\1", t)
        if re.search(r"^\*\*>|^>.*\|\|$", t, re.M):
            notes.append("Раскрывающиеся цитаты стали обычными")
            t = re.sub(r"^\*\*>", ">", t, flags=re.M)
        t = re.sub(r"!\[([^\]]*)\]\(tg://emoji\?id=\d+\)", r"\1", t)
        t = _md2_unescape(t)
        if target == "max_html":
            return convert_formatting(t, "markdown", "max_html") | {"notes": notes}
        return {"text": t, "format": "markdown", "notes": notes, "length": len(t)}

    if source == "markdown":
        lists = re.findall(r"^\s*(?:[-*+]|\d+[.)])\s+", t, re.M)
        if lists:
            notes.append("Списков в MAX нет: маркеры заменены на «•», нумерация оставлена текстом")
            t = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", t, flags=re.M)
        if re.search(r"^\|.+\|\s*$", t, re.M):
            notes.append("Таблиц в MAX нет — таблица осталась текстом, лучше переписать строками")
        if re.search(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", t, re.M):
            notes.append("Горизонтальные линии убраны")
            t = re.sub(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$\n?", "", t, flags=re.M)
        if re.search(r"!\[[^\]]*\]\([^)]+\)", t):
            notes.append("Картинки в тексте не отображаются — отправьте их вложением image {url}")
        if "```" in t and re.search(r"```[^`]*\n[^`]*```", t):
            notes.append("В блоке кода переносы строк превратятся в пробелы")
        if target == "max_markdown":
            return {"text": t, "format": "markdown", "notes": notes, "length": len(t)}
        h = html.escape(t, quote=False)
        conv = [
            (r"\*\*(.+?)\*\*", r"<b>\1</b>"), (r"__(.+?)__", r"<b>\1</b>"), (r"\+\+(.+?)\+\+", r"<u>\1</u>"),
            (r"~~(.+?)~~", r"<s>\1</s>"), (r"\^\^(.+?)\^\^", r"<mark>\1</mark>"),
            (r"(?<![\w*])\*(?!\*)(.+?)\*", r"<i>\1</i>"), (r"(?<!\w)_(?!_)(.+?)_(?!\w)", r"<i>\1</i>"),
            (r"```(.+?)```", r"<pre>\1</pre>"), (r"`([^`]+)`", r"<code>\1</code>"),
            (r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>'),
            (r"^#{1,6}\s+(.+)$", r"<h1>\1</h1>"), (r"^&gt;\s?(.+)$", r"<blockquote>\1</blockquote>"),
        ]
        for a, b in conv:
            t2 = re.sub(a, b, h, flags=re.M | re.S)
            h = t2
        return {"text": h, "format": "html", "notes": notes, "length": len(h)}

    raise ValueError("source: telegram_markdownv2 | telegram_html | markdown")
