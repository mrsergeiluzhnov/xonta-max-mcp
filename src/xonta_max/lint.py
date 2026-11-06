"""Static checks for MAX bot code and Telegram → MAX migration hints.

Regex-based on purpose: works for any language, gives line numbers, never runs the code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .knowledge import BASE_URL, CERT_PAGE, DOCS, VALIDATION, method_url


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str  # error | warning | info
    pattern: str
    message: str
    fix: str
    source: str
    flags: int = re.IGNORECASE


LINT_RULES: list[Rule] = [
    Rule("old-host", "error", r"platform-api\.max\.ru",
         "Старый адрес API. С 19.07.2026 обязателен platform-api2.max.ru.",
         f"Замените хост на {BASE_URL} и добавьте сертификат Минцифры в доверенные.", DOCS),
    Rule("wrong-host", "error", r"https?://(?:api|botapi|bot-api)\.max\.ru",
         "Такого адреса Bot API нет.", f"Используйте {BASE_URL}.", DOCS),
    Rule("token-in-query", "error", r"[?&](?:access_token|token)=",
         "Токен в query-параметре больше не принимается и попадает в логи.",
         "Передавайте токен в заголовке Authorization: <token>.", DOCS),
    Rule("bearer-prefix", "error", r"Authorization['\"]?\s*[:=,]\s*[`'\"f]*\s*Bearer",
         "MAX ждёт сырой токен без слова Bearer.", "Authorization: <token>", DOCS),
    Rule("tls-disabled", "error",
         r"verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*[=:]\s*['\"]?0|InsecureSkipVerify\s*:\s*true|rejectUnauthorized\s*:\s*false|curl\s+(?:[^\n]*\s)?-k\b|--insecure",
         "Проверка TLS отключена — это отключает её для всех хостов, не только для MAX.",
         "Добавьте корневой сертификат Минцифры (verify=путь, NODE_EXTRA_CA_CERTS, --cacert) вместо отключения проверки.", CERT_PAGE),
    Rule("get-chats", "error", r"(?:GET['\"]?\s*,?\s*['\"`]?|get\(\s*['\"`][^'\"`]*?)/chats['\"`?]|getAllChats|get_all_chats|\.getChats\(",
         "GET /chats удалён в июне 2026.",
         "Храните chat_id сами по обновлениям bot_added / bot_removed / bot_started; для одного чата — GET /chats/{chatId}.", DOCS),
    Rule("add-members", "error", r"/chats/[^/\s'\"`]+/members['\"`]\s*,?\s*(?:json|data|body)|addChatMembers|add_chat_members|addMembers\(",
         "POST /chats/{chatId}/members ограничен с 09.09.2026.", "Не стройте логику на добавлении участников ботом.",
         method_url("POST", "/chats/{chatId}/members")),
    Rule("upload-photo-type", "error", r"uploads\?type=photo|['\"]type['\"]\s*:\s*['\"]photo['\"]",
         "type=photo больше не принимается.", "Используйте type=image.", method_url("POST", "/uploads")),
    Rule("webhook-endpoint", "error", r"/webhook['\"`]\s*,?\s*(?:json|data|body)|setWebhook|set_webhook",
         "Вебхук в MAX подключается не так.", "POST /subscriptions {url, update_types, secret}.", method_url("POST", "/subscriptions")),
    Rule("webhook-port", "error", r"https?://[^\s'\"`/]+:(?:80|88|8080|8443)\b",
         "MAX доставляет вебхуки только на порт 443.", "Уберите порт из адреса, поставьте прокси на 443 с доверенным сертификатом.",
         method_url("POST", "/subscriptions")),
    Rule("http-webhook", "error", r"['\"]url['\"]\s*:\s*['\"]http://",
         "Вебхук по HTTP отклоняется с 25.05.2026.", "Нужен https:// на 443 с доверенным сертификатом.", method_url("POST", "/subscriptions")),
    Rule("link-preview-in-body", "warning", r"['\"]disable_link_preview['\"]\s*:",
         "disable_link_preview — query-параметр, в теле он игнорируется.", "Передайте ?disable_link_preview=true в URL.",
         method_url("POST", "/messages")),
    Rule("secret-plain-compare", "warning", r"(?:x-max-bot-api-secret|X-Max-Bot-Api-Secret)['\"]?\s*\)?\s*(?:\]|\))?\s*(?:===?|!==?)",
         "Секрет вебхука сравнивается обычным ==, это утечка по времени.",
         "hmac.compare_digest (Python), crypto.timingSafeEqual (Node), subtle.ConstantTimeCompare (Go).", method_url("POST", "/subscriptions")),
    Rule("initdata-direct-key", "warning", r"hmac\.new\(\s*(?:bot_)?token\b|createHmac\(\s*['\"]sha256['\"]\s*,\s*(?:bot)?[Tt]oken\s*\)\s*\.update\(\s*(?:data_check|check|launch)",
         "Похоже, initData подписывается прямо токеном.", "Сначала secret = HMAC_SHA256(\"WebAppData\", token), потом HMAC_SHA256(secret, строка).", VALIDATION),
    Rule("init-data-unsafe", "warning", r"initDataUnsafe",
         "initDataUnsafe не подписан — для авторизации не годится.", "Передайте на сервер window.WebApp.initData и проверьте подпись.", VALIDATION),
    Rule("hardcoded-upload-host", "warning", r"https?://[a-z0-9.-]*(?:vu|iu|upload)[a-z0-9.-]*\.(?:okcdn|mycdn|max)\.(?:ru|me)",
         "Адрес загрузки зашит в код.", "Берите url из ответа POST /uploads для каждого файла.", method_url("POST", "/uploads")),
    Rule("long-polling-prod", "info", r"/updates\b|getUpdates|get_updates|startPolling|start_polling|mode\s*:\s*['\"]polling",
         "Long polling в MAX — только для разработки.", "В продакшне используйте вебхук.", method_url("GET", "/updates")),
    Rule("no-attachment-retry", "info", r"/uploads",
         "После загрузки отправка может вернуть attachment.not.ready.", "Повторяйте отправку с паузой 0.5→1→2→4 с.", method_url("POST", "/uploads")),
    Rule("text-4096", "warning", r"\b4096\b",
         "Лимит текста в MAX — 4000 символов, не 4096 как в Telegram.", "Режьте длинный текст по 4000 символов.", method_url("POST", "/messages")),
]


# Telegram constructs → MAX equivalents
TELEGRAM_RULES: list[Rule] = [
    Rule("tg-host", "error", r"api\.telegram\.org(?:/bot)?|/bot\{?\$?\{?\w*[Tt]oken\}?/",
         "Адрес Telegram Bot API, токен в пути.", f"{BASE_URL}/<метод>, токен в заголовке Authorization.", DOCS),
    Rule("tg-sendMessage", "error", r"\bsend_?[Mm]essage\b",
         "sendMessage → POST /messages.", "chat_id в query (?chat_id= или ?user_id= для личных), текст в теле {text, format}.", method_url("POST", "/messages")),
    Rule("tg-media", "error", r"\bsend_?(?:[Pp]hoto|[Vv]ideo|[Dd]ocument|[Aa]udio|[Vv]oice|[Aa]nimation|[Mm]edia_?[Gg]roup)\b",
         "Отдельных методов для медиа нет.", "POST /uploads?type=…, загрузка на выданный url, затем POST /messages с attachments. Фото можно по внешнему url.", method_url("POST", "/uploads")),
    Rule("tg-sticker", "warning", r"\bsend_?[Ss]ticker\b", "Стикеры отправляются вложением sticker {code}.", "attachments: [{type: sticker, payload: {code}}] — единственное вложение.", method_url("POST", "/messages")),
    Rule("tg-location", "info", r"\bsend_?[Ll]ocation\b", "sendLocation → вложение location.", "attachments: [{type: location, latitude, longitude}].", method_url("POST", "/messages")),
    Rule("tg-contact", "info", r"\bsend_?[Cc]ontact\b", "sendContact → вложение contact.", "attachments: [{type: contact, payload: {name, contact_id | vcf_info}}].", method_url("POST", "/messages")),
    Rule("tg-edit", "error", r"\bedit_?[Mm]essage_?(?:[Tt]ext|[Cc]aption|[Rr]eply_?[Mm]arkup|[Mm]edia)\b",
         "Правка сообщения → PUT /messages?message_id=…", "Только свои сообщения и только 24 часа. attachments: null оставляет вложения.", method_url("PUT", "/messages")),
    Rule("tg-delete", "warning", r"\bdelete_?[Mm]essages?\b", "deleteMessage → DELETE /messages?message_id=…", "Работает 24 часа.", method_url("DELETE", "/messages")),
    Rule("tg-answer-callback", "error", r"\banswer_?[Cc]allback_?[Qq]uery\b",
         "answerCallbackQuery → POST /answers?callback_id=…", "В теле notification (тост) и/или message (новая версия сообщения) — правка и ответ одним запросом. Не чаще 2/с на чат.", method_url("POST", "/answers")),
    Rule("tg-callback-update", "error", r"\bcallback_query\b|CallbackQuery|callback_data",
         "В MAX нажатие приходит как update_type=message_callback.", "Читайте update.callback.payload и update.callback.callback_id; у кнопки поле payload вместо callback_data.", f"{DOCS}/objects/Update"),
    Rule("tg-reply-markup", "error", r"\breply_markup\b|InlineKeyboardMarkup|inline_keyboard\s*=",
         "Клавиатура в MAX — вложение, а не reply_markup.", "attachments: [{type: inline_keyboard, payload: {buttons: [[{type: callback, text, payload}]]}}].", method_url("POST", "/messages")),
    Rule("tg-reply-keyboard", "warning", r"ReplyKeyboardMarkup|KeyboardButton\b|resize_keyboard|one_time_keyboard|ReplyKeyboardRemove",
         "Обычной reply-клавиатуры в MAX нет.", "Используйте inline-кнопки типа message (отправляют свой текст в чат).", method_url("POST", "/messages")),
    Rule("tg-unsupported-buttons", "warning", r"\bpay\s*=\s*True|login_url|switch_inline_query|callback_game|web_app\s*=\s*WebAppInfo",
         "У этой кнопки нет прямого аналога в MAX.", "pay/login_url/switch_inline_query/game — нет; WebApp → кнопка open_app с web_app=<имя бота>.", method_url("POST", "/messages")),
    Rule("tg-parse-mode", "warning", r"\bparse_mode\b|ParseMode\.|MarkdownV2",
         "parse_mode → поле format: \"markdown\" | \"html\".", "Синтаксис отличается: подчёркивание ++текст++, спойлеров нет. Проверьте max_convert_formatting.", DOCS),
    Rule("tg-mention", "warning", r"tg://user\?id=", "Упоминание в MAX — max://user/<id>.", "[Имя Фамилия](max://user/123) или <a href=\"max://user/123\">…</a>.", DOCS),
    Rule("tg-update-detect", "warning", r"update\.message\b|update\[['\"]message['\"]\]|update\.edited_message|my_chat_member|chat_member\b",
         "В MAX тип события — явное поле update_type.", "message_created, message_edited, message_callback, bot_added, bot_removed, user_added, bot_started и др.", f"{DOCS}/objects/Update"),
    Rule("tg-start-param", "info", r"/start\s|CommandStart|start_parameter|deep_link",
         "Старт бота в MAX — событие bot_started.", "Параметр диплинка ?start= приходит в bot_started.payload (до 128 символов).", f"{DOCS}/objects/Update"),
    Rule("tg-chat-action", "info", r"\bsend_?[Cc]hat_?[Aa]ction\b", "sendChatAction → POST /chats/{chatId}/actions.", "action: typing_on, sending_photo и др.", method_url("POST", "/chats/{chatId}/actions")),
    Rule("tg-pin", "info", r"\b(?:un)?pin_?[Cc]hat_?[Mm]essage\b", "Закреп → PUT/DELETE /chats/{chatId}/pin.", "", method_url("PUT", "/chats/{chatId}/pin")),
    Rule("tg-commands", "info", r"\bset_?[Mm]y_?[Cc]ommands\b", "setMyCommands → PATCH /me/commands.", "До 32 команд.", method_url("PATCH", "/me/commands")),
    Rule("tg-get-me", "info", r"\bget_?[Mm]e\b", "getMe → GET /me.", "", method_url("GET", "/me")),
    Rule("tg-get-chat", "info", r"\bget_?[Cc]hat\b(?!_?[Mm]ember)", "getChat → GET /chats/{chatId}.", "", method_url("GET", "/chats/{chatId}")),
    Rule("tg-members", "info", r"\bget_?[Cc]hat_?(?:[Aa]dministrators|[Mm]embers?(?:_?[Cc]ount)?)\b|ban_?[Cc]hat_?[Mm]ember|kick_?[Cc]hat_?[Mm]ember",
         "Участники → /chats/{chatId}/members и /members/admins.", "Удаление: DELETE /chats/{chatId}/members?user_id=…&block=true.", method_url("GET", "/chats/{chatId}/members")),
    Rule("tg-forward", "info", r"\bforward_?[Mm]essages?\b|\bcopy_?[Mm]essage\b", "Пересылка → поле link {type: forward, mid} в POST /messages.", "", method_url("POST", "/messages")),
    Rule("tg-reply", "info", r"reply_to_message_id|reply_parameters", "Ответ на сообщение → link {type: reply, mid}.", "", method_url("POST", "/messages")),
    Rule("tg-no-equivalent", "warning",
         r"\bsend_?(?:[Pp]oll|[Dd]ice|[Ii]nvoice|[Gg]ame|[Vv]ideo_?[Nn]ote)\b|answer_?[Ii]nline_?[Qq]uery|set_?[Mm]essage_?[Rr]eaction|create_?[Ff]orum_?[Tt]opic|answer_?[Pp]re_?[Cc]heckout",
         "Аналога в MAX нет (опросы, кубик, платежи, игры, кружки, инлайн-режим, реакции, темы форума).", "Нужен обходной сценарий: кнопки, внешняя ссылка, мини-приложение.", DOCS),
    Rule("tg-webapp-js", "error", r"telegram-web-app\.js|window\.Telegram\.WebApp|Telegram\.WebApp",
         "Мини-приложение: другой скрипт и объект.", "<script src=\"https://st.max.ru/js/max-web-app.js\">, объект window.WebApp.", "https://dev.max.ru/docs/webapps/bridge"),
    Rule("tg-webapp-missing", "warning", r"MainButton|SecondaryButton|themeParams|CloudStorage|onEvent\(|setHeaderColor|expand\(\)",
         "В MAX Bridge этого нет.", "MainButton — своя кнопка в вёрстке; тему не получить; CloudStorage → DeviceStorage/SecureStorage (не работают в вебе) или свой бэкенд.", "https://dev.max.ru/docs/webapps/bridge"),
    Rule("tg-webapp-link", "info", r"t\.me/[\w_]+(?:/\w+)?\?startapp=|t\.me/[\w_]+\?start=", "Ссылки t.me → max.ru.", "https://max.ru/<бот>?start=… (до 128), ?startapp=… (до 512, A-Za-z0-9_-).", "https://dev.max.ru/docs/webapps/introduction"),
    Rule("tg-libs", "info", r"\b(?:aiogram|telebot|python-telegram-bot|telegram\.ext|telegraf|grammy|node-telegram-bot-api|go-telegram-bot-api|tgbotapi)\b",
         "Библиотека Telegram.", "TS: @maxhub/max-bot-api (похож на Telegraf); Go: max-bot-api-client-go/v2; Python: прямые запросы httpx (официальной библиотеки нет).", DOCS),
]

TELEGRAM_MAP: list[dict] = [
    {"telegram": "getMe", "max": "GET /me"},
    {"telegram": "sendMessage", "max": "POST /messages?chat_id=|user_id= {text, format, attachments}"},
    {"telegram": "sendPhoto / sendVideo / sendDocument / sendAudio / sendMediaGroup", "max": "POST /uploads?type=… → загрузка → POST /messages с attachments (до 12 фото+видео)"},
    {"telegram": "sendSticker", "max": "attachment sticker {code}"},
    {"telegram": "sendLocation / sendContact", "max": "attachment location / contact"},
    {"telegram": "editMessageText / editMessageReplyMarkup", "max": "PUT /messages?message_id= (24 ч)"},
    {"telegram": "deleteMessage", "max": "DELETE /messages?message_id= (24 ч)"},
    {"telegram": "answerCallbackQuery (+ editMessageText)", "max": "POST /answers?callback_id= {notification, message} одним запросом"},
    {"telegram": "forwardMessage / copyMessage", "max": "POST /messages с link {type: forward, mid}"},
    {"telegram": "reply_to_message_id", "max": "link {type: reply, mid}"},
    {"telegram": "sendChatAction", "max": "POST /chats/{chatId}/actions"},
    {"telegram": "getChat / setChatTitle / setChatDescription", "max": "GET / PATCH /chats/{chatId}"},
    {"telegram": "pinChatMessage / unpinChatMessage", "max": "PUT / DELETE /chats/{chatId}/pin"},
    {"telegram": "getChatAdministrators / promoteChatMember", "max": "GET / POST /chats/{chatId}/members/admins"},
    {"telegram": "banChatMember / kickChatMember", "max": "DELETE /chats/{chatId}/members?user_id=&block=true"},
    {"telegram": "leaveChat", "max": "DELETE /chats/{chatId}/members/me"},
    {"telegram": "setMyCommands", "max": "PATCH /me/commands"},
    {"telegram": "setWebhook / deleteWebhook / getWebhookInfo", "max": "POST / DELETE / GET /subscriptions"},
    {"telegram": "getUpdates", "max": "GET /updates (только разработка)"},
    {"telegram": "update.message", "max": "update_type = message_created, update.message"},
    {"telegram": "update.edited_message", "max": "update_type = message_edited"},
    {"telegram": "update.callback_query", "max": "update_type = message_callback, update.callback"},
    {"telegram": "update.my_chat_member", "max": "bot_added / bot_removed"},
    {"telegram": "/start с параметром", "max": "update_type = bot_started, payload"},
    {"telegram": "reply_markup InlineKeyboardMarkup", "max": "attachment inline_keyboard {buttons: [[…]]}"},
    {"telegram": "callback_data", "max": "button.payload (до 1024)"},
    {"telegram": "ReplyKeyboardMarkup", "max": "нет; inline-кнопки типа message"},
    {"telegram": "parse_mode", "max": "format: markdown | html"},
    {"telegram": "tg://user?id=", "max": "max://user/<id>"},
    {"telegram": "Telegram.WebApp", "max": "window.WebApp (st.max.ru/js/max-web-app.js)"},
    {"telegram": "t.me/<bot>?start= / ?startapp=", "max": "max.ru/<bot>?start= / ?startapp="},
    {"telegram": "sendPoll, sendDice, sendInvoice, sendGame, sendVideoNote, inline mode, reactions, forum topics", "max": "нет аналога"},
]


def _scan(code: str, rules: list[Rule]) -> list[dict]:
    lines = code.splitlines()
    found: list[dict] = []
    for rule in rules:
        rx = re.compile(rule.pattern, rule.flags)
        hits = []
        for i, line in enumerate(lines, 1):
            m = rx.search(line)
            if m:
                hits.append({"line": i, "match": m.group(0)[:80], "code": line.strip()[:160]})
        if hits:
            found.append({
                "rule": rule.id, "severity": rule.severity, "message": rule.message,
                "fix": rule.fix, "source": rule.source, "occurrences": hits[:20], "count": len(hits),
            })
    order = {"error": 0, "warning": 1, "info": 2}
    found.sort(key=lambda f: (order[f["severity"]], f["occurrences"][0]["line"]))
    return found


def lint(code: str) -> dict:
    findings = _scan(code, LINT_RULES)
    # info-level reminders only make sense when there is no matching handling
    if any(f["rule"] == "no-attachment-retry" for f in findings) and "attachment.not.ready" in code:
        findings = [f for f in findings if f["rule"] != "no-attachment-retry"]
    uses_max = bool(re.search(r"max\.ru|max-bot-api|maxbot|@maxhub|window\.WebApp", code))
    tg = _scan(code, TELEGRAM_RULES) if re.search(r"telegram|t\.me/|tg://|aiogram|telebot|telegraf|grammy", code, re.I) else []
    return {
        "errors": sum(f["severity"] == "error" for f in findings),
        "warnings": sum(f["severity"] == "warning" for f in findings),
        "findings": findings,
        "telegram_leftovers": tg,
        "looks_like_max_code": uses_max,
    }


def migrate(code: str) -> dict:
    tg = _scan(code, TELEGRAM_RULES)
    mx = _scan(code, LINT_RULES)
    no_equiv = [f for f in tg if f["rule"] in ("tg-no-equivalent", "tg-unsupported-buttons", "tg-webapp-missing", "tg-reply-keyboard")]
    total = sum(f["count"] for f in tg)
    return {
        "telegram_usages": total,
        "items": tg,
        "max_issues_already_present": mx,
        "features_without_equivalent": [o["match"] for f in no_equiv for o in f["occurrences"]],
        "effort": "низкая" if total <= 10 else "средняя" if total <= 40 else "высокая",
        "plan": [
            "Вынесите все запросы к API в один модуль клиента: хост platform-api2.max.ru, заголовок Authorization, сертификат Минцифры.",
            "Перепишите разбор обновлений на update_type (message_created, message_callback, bot_started, bot_added…).",
            "Клавиатуры — во вложение inline_keyboard; callback_data → payload; ответы на нажатия — POST /answers.",
            "Разметка: parse_mode → format, проверьте подчёркивание, упоминания, спойлеры (max_convert_formatting).",
            "Медиа: двухшаговая загрузка через POST /uploads и повтор при attachment.not.ready.",
            "Лимиты: текст 4000, правка и удаление только 24 часа, 30 запросов/с, 2 сообщения/с на чат.",
            "Вебхук: HTTPS на 443 с доверенным сертификатом, секрет в X-Max-Bot-Api-Secret, переподписка после 8 ч простоя.",
            "Решите, чем заменить функции без аналога (см. features_without_equivalent).",
        ],
    }
