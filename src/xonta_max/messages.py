"""Build and validate MAX message bodies, keyboards and formatted text."""

from __future__ import annotations

import html
import re

from .i18n import tr
from .knowledge import ATTACHMENT_TYPES, BUTTON_TYPES, WIDE_BUTTONS

TEXT_LIMIT = 4000
OPEN_APP_PAYLOAD = re.compile(r"^[\w-]*$", re.ASCII)


def validate_button(b: dict, where: str) -> list[str]:
    errs: list[str] = []
    if not isinstance(b, dict):
        return [tr(f"{where}: кнопка должна быть объектом", f"{where}: a button must be an object")]
    t = b.get("type")
    if t not in BUTTON_TYPES:
        return [tr(f"{where}: неизвестный type={t!r}; допустимо: {', '.join(BUTTON_TYPES)}", f"{where}: unknown type={t!r}; allowed: {', '.join(BUTTON_TYPES)}")]
    text = b.get("text")
    if not isinstance(text, str) or not (1 <= len(text) <= 128):
        errs.append(tr(f"{where}: text обязателен, 1-128 символов", f"{where}: text is required, 1-128 characters"))
    for f in BUTTON_TYPES[t]["required"]:
        if not b.get(f):
            errs.append(tr(f"{where}: для {t} нужно поле {f}", f"{where}: {t} needs the {f} field"))
    if t in ("callback", "clipboard") and isinstance(b.get("payload"), str) and len(b["payload"]) > 1024:
        errs.append(tr(f"{where}: payload длиннее 1024", f"{where}: payload longer than 1024"))
    if t == "link":
        url = b.get("url", "")
        if isinstance(url, str) and len(url) > 2048:
            errs.append(tr(f"{where}: url длиннее 2048", f"{where}: url longer than 2048"))
        if isinstance(url, str) and url and not re.match(r"^(https?://|max://)", url):
            errs.append(tr(f"{where}: url должен начинаться с https:// или http://", f"{where}: url must start with https:// or http://"))
    if t == "open_app":
        p = b.get("payload")
        if p is not None and (len(p) > 512 or not OPEN_APP_PAYLOAD.match(p)):
            errs.append(tr(f"{where}: payload open_app — до 512 символов, только A-Za-z0-9_-", f"{where}: open_app payload — up to 512 characters, A-Za-z0-9_- only"))
    if "callback_data" in b:
        errs.append(tr(f"{where}: callback_data — это Telegram; в MAX поле называется payload", f"{where}: callback_data is Telegram; in MAX the field is payload"))
    return errs


def validate_keyboard(buttons) -> list[str]:
    if not isinstance(buttons, list) or not buttons:
        return [tr("inline_keyboard: buttons — непустой массив рядов", "inline_keyboard: buttons must be a non-empty array of rows")]
    errs: list[str] = []
    if len(buttons) > 30:
        errs.append(tr(f"inline_keyboard: {len(buttons)} рядов, максимум 30", f"inline_keyboard: {len(buttons)} rows, max 30"))
    total = 0
    for r, row in enumerate(buttons):
        if not isinstance(row, list) or not row:
            errs.append(tr(f"ряд {r + 1}: должен быть непустым массивом кнопок", f"row {r + 1}: must be a non-empty array of buttons"))
            continue
        total += len(row)
        wide = any(isinstance(b, dict) and b.get("type") in WIDE_BUTTONS for b in row)
        cap = 3 if wide else 7
        if len(row) > cap:
            errs.append(tr(f"ряд {r + 1}: {len(row)} кнопок, максимум {cap}", f"row {r + 1}: {len(row)} buttons, max {cap}")
                        + (tr(" (в ряду есть link/open_app/request_*)", " (the row has link/open_app/request_*)") if wide else ""))
        for c, b in enumerate(row):
            errs += validate_button(b, tr(f"ряд {r + 1}, кнопка {c + 1}", f"row {r + 1}, button {c + 1}"))
    if total > 210:
        errs.append(tr(f"inline_keyboard: {total} кнопок, максимум 210", f"inline_keyboard: {total} buttons, max 210"))
    return errs


def validate_body(body: dict, *, is_comment: bool = False, chat_type: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(body, dict):
        return {"valid": False, "errors": [tr("Тело сообщения должно быть JSON-объектом", "The message body must be a JSON object")], "warnings": []}

    for k in ("chat_id", "user_id"):
        if k in body:
            errors.append(tr(f"{k} передаётся в query (?{k}=…), а не в теле", f"{k} goes in the query (?{k}=…), not in the body"))
    if "disable_link_preview" in body:
        errors.append(tr("disable_link_preview — query-параметр, в теле игнорируется", "disable_link_preview is a query parameter; ignored in the body"))
    for tg in ("parse_mode", "reply_markup", "reply_to_message_id"):
        if tg in body:
            errors.append(tr(f"{tg} — поле Telegram. В MAX: parse_mode → format, reply_markup → attachments inline_keyboard, reply_to_message_id → link {{type: reply, mid}}", f"{tg} is a Telegram field. In MAX: parse_mode → format, reply_markup → inline_keyboard attachment, reply_to_message_id → link {{type: reply, mid}}"))

    text = body.get("text")
    if text is not None:
        if not isinstance(text, str):
            errors.append(tr("text должен быть строкой", "text must be a string"))
        elif len(text) > TEXT_LIMIT:
            errors.append(tr(f"text: {len(text)} символов, максимум {TEXT_LIMIT}. Разбейте через max_split_text.", f"text: {len(text)} characters, max {TEXT_LIMIT}. Split it with max_split_text."))
    fmt = body.get("format")
    if fmt is not None and fmt not in ("markdown", "html"):
        errors.append(tr("format: только \"markdown\" или \"html\"", "format: \"markdown\" or \"html\" only"))
    if isinstance(text, str) and fmt is None and re.search(r"\*\*|__|<b>|<i>|\[[^\]]+\]\(", text):
        warnings.append(tr("В тексте есть разметка, но format не указан — пользователь увидит символы как есть", "The text has markup but no format — users will see the raw symbols"))
    if isinstance(text, str) and fmt == "markdown" and re.search(r"^\s*(?:[-*+]|\d+[.)])\s", text, re.M):
        warnings.append(tr("Списков в разметке MAX нет — строки уйдут как обычный текст", "MAX markup has no lists — the lines go out as plain text"))
    if isinstance(text, str) and fmt == "markdown" and "||" in text:
        warnings.append(tr("Спойлеров (||…||) в MAX нет", "MAX has no spoilers (||…||)"))

    link = body.get("link")
    if link is not None:
        if not isinstance(link, dict) or link.get("type") not in ("reply", "forward") or not link.get("mid"):
            errors.append(tr("link: {type: \"reply\" | \"forward\", mid: \"<id сообщения>\"}", "link: {type: \"reply\" | \"forward\", mid: \"<message id>\"}"))
        elif is_comment and link.get("type") == "forward":
            errors.append(tr("В комментариях поддерживается только link.type = reply", "Comments support only link.type = reply"))

    if chat_type == "channel" and body.get("notify") is False:
        errors.append(tr("В каналах notify нельзя выключить — уберите поле или поставьте true", "notify can't be turned off in channels — drop the field or set true"))

    atts = body.get("attachments")
    if is_comment and atts:
        errors.append(tr("Комментарии не поддерживают вложения", "Comments don't support attachments"))
    if is_comment and isinstance(text, str) and re.search(r"\]\(|<a\s|max://user", text):
        errors.append(tr("В комментариях нельзя ссылки и упоминания", "Comments can't contain links or mentions"))
    if atts is not None and not is_comment:
        if not isinstance(atts, list):
            errors.append(tr("attachments — массив", "attachments must be an array"))
        else:
            counts: dict[str, int] = {}
            for i, a in enumerate(atts):
                if not isinstance(a, dict):
                    errors.append(tr(f"вложение {i + 1}: объект {{type, payload}}", f"attachment {i + 1}: must be an object {{type, payload}}"))
                    continue
                t = a.get("type")
                if t == "photo":
                    errors.append(tr(f"вложение {i + 1}: type=photo устарел, используйте image", f"attachment {i + 1}: type=photo is outdated, use image"))
                    t = "image"
                if t not in ATTACHMENT_TYPES:
                    errors.append(tr(f"вложение {i + 1}: неизвестный type={t!r}", f"attachment {i + 1}: unknown type={t!r}"))
                    continue
                counts[t] = counts.get(t, 0) + 1
                p = a.get("payload") or {}
                if t == "inline_keyboard":
                    errors += validate_keyboard(p.get("buttons"))
                elif t == "image":
                    keys = [k for k in ("url", "token", "photos") if p.get(k)]
                    if len(keys) != 1:
                        errors.append(tr(f"вложение {i + 1}: image — ровно одно из url, token, photos", f"attachment {i + 1}: image needs exactly one of url, token, photos"))
                elif t in ("video", "audio", "file"):
                    if not p.get("token"):
                        errors.append(tr(f"вложение {i + 1}: {t} — нужен token из POST /uploads", f"attachment {i + 1}: {t} needs a token from POST /uploads"))
                elif t == "sticker":
                    if not p.get("code"):
                        errors.append(tr(f"вложение {i + 1}: sticker — нужен code", f"attachment {i + 1}: sticker needs code"))
                elif t == "location":
                    lat = a.get("latitude", p.get("latitude"))
                    lon = a.get("longitude", p.get("longitude"))
                    if lat is None or lon is None:
                        errors.append(tr(f"вложение {i + 1}: location — нужны latitude и longitude", f"attachment {i + 1}: location needs latitude and longitude"))
            media = counts.get("image", 0) + counts.get("video", 0)
            if media > 12:
                errors.append(tr(f"{media} фото и видео, максимум 12", f"{media} images and videos, max 12"))
            if counts.get("inline_keyboard", 0) > 1:
                errors.append(tr("Не больше одной inline_keyboard на сообщение", "At most one inline_keyboard per message"))
            if counts.get("file", 0) > 1:
                errors.append(tr("Только один file на сообщение", "Only one file per message"))
            if counts.get("file") and (media or counts.get("audio") or counts.get("sticker") or counts.get("contact")):
                errors.append(tr("file сочетается только с одной inline_keyboard", "file can only be combined with one inline_keyboard"))
            for solo in ("audio", "sticker", "contact"):
                if counts.get(solo) and sum(counts.values()) - (counts.get("inline_keyboard", 0) if solo == "contact" else 0) > 1:
                    errors.append(tr(f"{solo} должен быть единственным вложением", f"{solo} must be the only attachment")
                                  + (tr(" (допустима 1 клавиатура)", " (1 keyboard allowed)") if solo == "contact" else ""))
            if (counts.get("video") or counts.get("audio") or counts.get("file")):
                warnings.append(tr("После загрузки файл может быть не готов: при attachment.not.ready повторите отправку с паузой", "An uploaded file may not be ready yet: on attachment.not.ready retry with a delay"))

    if text in (None, "") and not atts:
        errors.append(tr("Пустое сообщение: нужен text или attachments", "Empty message: needs text or attachments"))
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
            notes.append(tr("Спойлеры убраны: в MAX их нет", "Spoilers removed: MAX has none"))
            t = re.sub(r"</?tg-spoiler>", "", t)
            t = re.sub(r'<span class="tg-spoiler">(.*?)</span>', r"\1", t, flags=re.S)
        if "<tg-emoji" in t:
            notes.append(tr("Кастомные эмодзи заменены обычными", "Custom emoji replaced with regular ones"))
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
            notes.append(tr("Спойлеры убраны: в MAX их нет", "Spoilers removed: MAX has none"))
            t = re.sub(r"\|\|(.+?)\|\|", r"\1", t, flags=re.S)
        t = re.sub(r"(?<![\\_])__(.+?)__", r"++\1++", t, flags=re.S)
        t = re.sub(r"(?<![\\*])\*(?!\*)(.+?)(?<!\\)\*", r"**\1**", t, flags=re.S)
        t = re.sub(r"(?<![\\_])_(?!_)(.+?)(?<!\\)_", r"_\1_", t, flags=re.S)
        t = re.sub(r"(?<!\\)~(.+?)(?<!\\)~", r"~~\1~~", t, flags=re.S)
        t = re.sub(r"tg://user\?id=(\d+)", r"max://user/\1", t)
        if re.search(r"^\*\*>|^>.*\|\|$", t, re.M):
            notes.append(tr("Раскрывающиеся цитаты стали обычными", "Expandable quotes became regular quotes"))
            t = re.sub(r"^\*\*>", ">", t, flags=re.M)
        t = re.sub(r"!\[([^\]]*)\]\(tg://emoji\?id=\d+\)", r"\1", t)
        t = _md2_unescape(t)
        if target == "max_html":
            return convert_formatting(t, "markdown", "max_html") | {"notes": notes}
        return {"text": t, "format": "markdown", "notes": notes, "length": len(t)}

    if source == "markdown":
        lists = re.findall(r"^\s*(?:[-*+]|\d+[.)])\s+", t, re.M)
        if lists:
            notes.append(tr("Списков в MAX нет: маркеры заменены на «•», нумерация оставлена текстом", "MAX has no lists: bullets replaced with •, numbering kept as text"))
            t = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", t, flags=re.M)
        if re.search(r"^\|.+\|\s*$", t, re.M):
            notes.append(tr("Таблиц в MAX нет — таблица осталась текстом, лучше переписать строками", "MAX has no tables — the table stays as text, better rewrite it as lines"))
        if re.search(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", t, re.M):
            notes.append(tr("Горизонтальные линии убраны", "Horizontal rules removed"))
            t = re.sub(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$\n?", "", t, flags=re.M)
        if re.search(r"!\[[^\]]*\]\([^)]+\)", t):
            notes.append(tr("Картинки в тексте не отображаются — отправьте их вложением image {url}", "Images in text are not shown — send them as an image {url} attachment"))
        if "```" in t and re.search(r"```[^`]*\n[^`]*```", t):
            notes.append(tr("В блоке кода переносы строк превратятся в пробелы", "Line breaks inside a code block will become spaces"))
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
