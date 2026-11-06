"""MAX Bot API and Mini Apps facts, checked against dev.max.ru and the official OpenAPI schema.

Every entry carries a source so an agent can show where a fact comes from.
Text fields come in pairs: `x` (Russian) and `x_en` (English); i18n.loc() picks one.
When the live docs disagree with this file, the live docs win.
"""

from __future__ import annotations

from .i18n import loc

VERIFIED_ON = "2026-11-06"

BASE_URL = "https://platform-api2.max.ru"
OLD_BASE_URL = "https://platform-api.max.ru"

DOCS = "https://dev.max.ru/docs-api"
SCHEMA = "https://github.com/max-messenger/api-schema"
BRIDGE = "https://dev.max.ru/docs/webapps/bridge"
VALIDATION = "https://dev.max.ru/docs/webapps/validation"
CHANGELOG_URL = "https://dev.max.ru/docs-api/changelog-api"
CERT_PAGE = "https://www.gosuslugi.ru/crt"
CERT_PEM = "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"
PREPARE = "https://dev.max.ru/docs/chatbots/bots-coding/prepare"
WEBAPPS = "https://dev.max.ru/docs/webapps/introduction"


def method_url(verb: str, path: str) -> str:
    """Docs page for one method: /docs-api/methods/<VERB>/<path with {x} as -x->."""
    p = path.strip("/").replace("{", "-").replace("}", "-")
    return f"{DOCS}/methods/{verb.upper()}/{p}"


REQ_RU, REQ_EN = "обязателен", "required"


def _ep(verb, path, group, ru, en, query=None, query_en=None, body=None, **extra):
    e = {"verb": verb, "path": path, "group": group, "summary": ru, "summary_en": en,
         "query": query or {}, "body": body}
    if query_en:
        e["query_en"] = query_en
    e.update(extra)
    return e


# ---------------------------------------------------------------- endpoints

ENDPOINTS: list[dict] = [
    _ep("GET", "/me", "bots", "Информация о боте (BotInfo)", "Bot info (BotInfo)"),
    _ep("PATCH", "/me/commands", "bots", "Добавить, изменить или удалить команды бота (до 32; пустой массив удаляет все)",
        "Add, change or delete bot commands (up to 32; an empty array removes all)",
        body="BotCommandsPatch {commands: [{name 1-64, description 1-128}]}", since="2026-07"),
    _ep("GET", "/chats/{chatId}", "chats", "Информация о группе или канале", "Group chat or channel info"),
    _ep("PATCH", "/chats/{chatId}", "chats", "Изменить название, иконку, описание, закреп", "Change title, icon, description, pinned message",
        body="ChatPatch {icon?, title? 1-200, description? <=16000 (2026-08+), pin?, notify?}"),
    _ep("POST", "/chats/{chatId}/actions", "chats", "Действие бота в чате (typing_on, sending_photo, mark_seen и др.)",
        "Bot action in a chat (typing_on, sending_photo, mark_seen, etc.)", body="ActionRequestBody {action}"),
    _ep("GET", "/chats/{chatId}/pin", "chats", "Закреплённое сообщение", "Pinned message"),
    _ep("PUT", "/chats/{chatId}/pin", "chats", "Закрепить сообщение", "Pin a message", body="PinMessageBody {message_id, notify?}"),
    _ep("DELETE", "/chats/{chatId}/pin", "chats", "Открепить сообщение", "Unpin a message"),
    _ep("GET", "/chats/{chatId}/members/me", "chats", "Членство самого бота и его права", "The bot's own membership and permissions"),
    _ep("DELETE", "/chats/{chatId}/members/me", "chats", "Бот выходит из чата или канала", "The bot leaves the chat or channel"),
    _ep("GET", "/chats/{chatId}/members/admins", "chats", "Список администраторов", "List admins"),
    _ep("POST", "/chats/{chatId}/members/admins", "chats", "Назначить администратора. Работает как полная замена прав, несмотря на POST",
        "Assign an admin. Fully replaces the permission set despite the POST verb",
        body="ChatAdminsList {admins: [{user_id, permissions[]}]}"),
    _ep("DELETE", "/chats/{chatId}/members/admins/{userId}", "chats", "Снять права администратора", "Revoke admin rights"),
    _ep("GET", "/chats/{chatId}/members", "chats", "Участники чата", "Chat members",
        query={"user_ids": "csv", "marker": "int64", "count": "1-100, по умолчанию 20"},
        query_en={"user_ids": "csv", "marker": "int64", "count": "1-100, default 20"}),
    _ep("POST", "/chats/{chatId}/members", "chats", "Добавить участников. ОГРАНИЧЕН с 2026-09-09, не стройте на нём логику",
        "Add members. RESTRICTED since 2026-09-09, do not build on it",
        body="UserIdsList {user_ids: <=100}", deprecated=True),
    _ep("DELETE", "/chats/{chatId}/members", "chats", "Удалить участника", "Remove a member",
        query={"user_id": REQ_RU, "block": "bool, по умолчанию false"}, query_en={"user_id": REQ_EN, "block": "bool, default false"}),
    _ep("GET", "/subscriptions", "subscriptions", "Список вебхук-подписок", "List webhook subscriptions"),
    _ep("POST", "/subscriptions", "subscriptions", "Подписать URL на обновления (вебхук)", "Subscribe a URL to updates (webhook)",
        body="SubscriptionRequestBody {url https://, update_types?[], secret? 5-256 [A-Za-z0-9_-]}"),
    _ep("DELETE", "/subscriptions", "subscriptions", "Отписать URL", "Unsubscribe a URL", query={"url": REQ_RU}, query_en={"url": REQ_EN}),
    _ep("GET", "/updates", "subscriptions", "Long polling (только для разработки и тестов)", "Long polling (development and testing only)",
        query={"limit": "1-1000, по умолчанию 100", "timeout": "0-90 с, по умолчанию 30", "marker": "int64", "types": "csv"},
        query_en={"limit": "1-1000, default 100", "timeout": "0-90 s, default 30", "marker": "int64", "types": "csv"}),
    _ep("POST", "/uploads", "upload", "Получить адрес для загрузки файла", "Get an upload URL for a file",
        query={"type": "image | video | audio | file (photo больше не принимается)"},
        query_en={"type": "image | video | audio | file (photo is no longer accepted)"}),
    _ep("GET", "/messages", "messages", "Сообщения чата (новые сначала) или по id", "Chat messages (newest first) or by id",
        query={"chat_id": "int64", "message_ids": "csv", "before": "int64", "after": "int64", "count": "1-100, по умолчанию 50"},
        query_en={"chat_id": "int64", "message_ids": "csv", "before": "int64", "after": "int64", "count": "1-100, default 50"}),
    _ep("POST", "/messages", "messages", "Отправить сообщение", "Send a message",
        query={"user_id": "int64, личный диалог", "chat_id": "int64, чат или канал", "disable_link_preview": "bool"},
        query_en={"user_id": "int64, private dialog", "chat_id": "int64, chat or channel", "disable_link_preview": "bool"},
        body="NewMessageBody {text? <=4000, attachments?, link?, notify?, format?}"),
    _ep("PUT", "/messages", "messages", "Изменить своё сообщение (в течение 24 ч). attachments: null оставляет вложения, [] удаляет",
        "Edit your own message (within 24 h). attachments: null keeps attachments, [] removes them",
        query={"message_id": REQ_RU}, query_en={"message_id": REQ_EN}, body="NewMessageBody"),
    _ep("DELETE", "/messages", "messages", "Удалить сообщение (в течение 24 ч)", "Delete a message (within 24 h)",
        query={"message_id": REQ_RU}, query_en={"message_id": REQ_EN}),
    _ep("GET", "/messages/{messageId}", "messages", "Одно сообщение", "One message"),
    _ep("GET", "/videos/{videoToken}", "messages", "Ссылки на видео (mp4 1080…144, hls) и метаданные", "Video URLs (mp4 1080…144, hls) and metadata"),
    _ep("POST", "/answers", "messages", "Ответ на нажатие callback-кнопки: тост и/или правка исходного сообщения. Не чаще 2 раз в секунду на чат",
        "Answer a callback button press: a toast and/or an edit of the original message. At most 2 per second per chat",
        query={"callback_id": REQ_RU, "disable_link_preview": "bool (2026-08+)"}, query_en={"callback_id": REQ_EN, "disable_link_preview": "bool (2026-08+)"},
        body="CallbackAnswer {message?: NewMessageBody, notification?: string}"),
    _ep("GET", "/messages/{messageId}/comments", "comments", "Комментарии к посту канала", "Comments on a channel post",
        query={"comment_ids": "csv", "before": "int64", "after": "int64", "count": "1-100"}, since="2026-08"),
    _ep("POST", "/messages/{messageId}/comments", "comments", "Оставить комментарий (без вложений, без ссылок и упоминаний)",
        "Post a comment (no attachments, links or mentions)", query={"disable_link_preview": "bool"},
        body="NewCommentBody {text, link?, format?}", since="2026-08"),
    _ep("PUT", "/messages/{messageId}/comments", "comments", "Изменить комментарий", "Edit a comment",
        query={"comment_id": REQ_RU}, query_en={"comment_id": REQ_EN}, body="NewCommentBody", since="2026-08"),
    _ep("DELETE", "/messages/{messageId}/comments", "comments", "Удалить комментарий", "Delete a comment",
        query={"comment_id": REQ_RU}, query_en={"comment_id": REQ_EN}, since="2026-08"),
    _ep("GET", "/messages/{messageId}/comments/{commentId}", "comments", "Один комментарий", "One comment", since="2026-08"),
]

REMOVED_ENDPOINTS = {
    ("GET", "/chats"): {
        "note": "Удалён в июне 2026. Список чатов ведите сами по обновлениям bot_added / bot_removed / bot_started; один чат: GET /chats/{chatId}.",
        "note_en": "Removed in June 2026. Keep your own chat list from bot_added / bot_removed / bot_started updates; one chat: GET /chats/{chatId}.",
    },
    ("POST", "/webhook"): {
        "note": "Такого метода нет. Вебхук подключается через POST /subscriptions.",
        "note_en": "There is no such method. Webhooks are set with POST /subscriptions.",
    },
}


def removed_note(verb: str, path: str) -> str | None:
    r = REMOVED_ENDPOINTS.get((verb.upper(), "/" + path.split("?")[0].strip("/")))
    return loc(r)["note"] if r else None


def find_endpoint(verb: str, path: str) -> dict | None:
    """Match a concrete path like /chats/123/pin against the templates."""
    verb = verb.upper()
    parts = [p for p in path.split("?")[0].strip("/").split("/") if p]
    for ep in ENDPOINTS:
        if ep["verb"] != verb:
            continue
        tpl = [p for p in ep["path"].strip("/").split("/") if p]
        if len(tpl) != len(parts):
            continue
        if all(t.startswith("{") or t == p for t, p in zip(tpl, parts)):
            return ep
    return None


# ---------------------------------------------------------------- limits

def _lim(ru, ru_v, en, en_v, source):
    return {"what": ru, "what_en": en, "value": ru_v, "value_en": en_v, "source": source}


LIMITS: list[dict] = [
    _lim("Текст сообщения или комментария", "до 4000 символов (символов, не байт; разметка и эмодзи считаются)",
         "Message or comment text", "up to 4000 characters (characters, not bytes; markup and emoji count)", method_url("POST", "/messages")),
    _lim("Запросы к API", "30 в секунду на platform-api2.max.ru", "API requests", "30 per second to platform-api2.max.ru", PREPARE),
    _lim("Сообщения в один чат", "не больше 2 в секунду в один диалог, группу или канал",
         "Messages to one chat", "at most 2 per second to one dialog, group or channel", method_url("POST", "/messages")),
    _lim("Ответы на callback (POST /answers)", "не больше 2 в секунду на чат", "Callback answers (POST /answers)", "at most 2 per second per chat", method_url("POST", "/answers")),
    _lim("Long polling", "пауза между вызовами от 300 мс; timeout 0-90 с; limit 1-1000",
         "Long polling", "at least 300 ms between calls; timeout 0-90 s; limit 1-1000", method_url("GET", "/updates")),
    _lim("Правка и удаление своих сообщений", "в течение 24 часов", "Editing and deleting your own messages", "within 24 hours", method_url("PUT", "/messages")),
    _lim("Вложения в одном сообщении",
         "до 12 фото и видео суммарно + 1 inline_keyboard; file — только один и максимум с 1 клавиатурой; audio, sticker, contact — единственное вложение",
         "Attachments in one message",
         "up to 12 images and videos in total + 1 inline_keyboard; file — only one, with at most 1 keyboard; audio, sticker, contact — the only attachment",
         method_url("POST", "/messages")),
    _lim("Клавиатура", "до 210 кнопок, до 30 рядов, до 7 кнопок в ряду; до 3 в ряду, если в нём link, open_app, request_geo_location или request_contact",
         "Keyboard", "up to 210 buttons, 30 rows, 7 buttons per row; 3 per row if the row has link, open_app, request_geo_location or request_contact",
         method_url("POST", "/messages")),
    _lim("Текст кнопки", "1-128 символов; для полного отображения около 20 при 1 кнопке в ряду, 10 при 2, 5 при 3, 3 при 4",
         "Button text", "1-128 characters; to show in full about 20 with 1 button per row, 10 with 2, 5 with 3, 3 with 4", method_url("POST", "/messages")),
    _lim("payload callback- и clipboard-кнопки", "до 1024 символов", "callback and clipboard button payload", "up to 1024 characters", method_url("POST", "/messages")),
    _lim("url link-кнопки и ссылки в разметке", "до 2048 символов", "link button url and markup links", "up to 2048 characters", method_url("POST", "/messages")),
    _lim("payload open_app-кнопки", "до 512 символов, только A-Z a-z 0-9 _ -", "open_app button payload", "up to 512 characters, A-Z a-z 0-9 _ - only", SCHEMA),
    _lim("Диплинк бота ?start=", "payload до 128 символов, длиннее — не доходит до бота",
         "Bot deep link ?start=", "payload up to 128 characters, longer never reaches the bot", PREPARE),
    _lim("Диплинк мини-приложения ?startapp=", "payload до 512 символов, только A-Z a-z 0-9 _ -; иначе молча отбрасывается",
         "Mini-app deep link ?startapp=", "payload up to 512 characters, A-Z a-z 0-9 _ - only; otherwise silently dropped", WEBAPPS),
    _lim("Команды бота", "до 32; name 1-64, description 1-128", "Bot commands", "up to 32; name 1-64, description 1-128", method_url("PATCH", "/me/commands")),
    _lim("Секрет вебхука", "5-256 символов, A-Z a-z 0-9 _ -", "Webhook secret", "5-256 characters, A-Z a-z 0-9 _ -", method_url("POST", "/subscriptions")),
    _lim("Вебхук",
         "только HTTPS на порту 443, сертификат доверенного УЦ или Минцифры (самоподписанные и HTTP отклоняются с 2026-05-25); ответ 200 за 30 с; до 10 повторов (60 с, ×2.5); через 8 ч без 200 подписка снимается",
         "Webhook",
         "HTTPS on port 443 only, certificate from a trusted CA or the Russian Ministry of Digital Development (self-signed and HTTP rejected since 2026-05-25); reply 200 within 30 s; up to 10 retries (60 s, ×2.5); after 8 h without a 200 the subscription is removed",
         method_url("POST", "/subscriptions")),
    _lim("Размер файлов", "фото до 50 МБ и до 7680×7680; видео до 250 МБ; аудио до 256 МБ и 60 мин; файл до 4 ГБ",
         "File sizes", "image up to 50 MB and 7680×7680; video up to 250 MB; audio up to 256 MB and 60 min; file up to 4 GB", method_url("POST", "/uploads")),
    _lim("Название чата", "1-200 символов; описание до 16000", "Chat title", "1-200 characters; description up to 16000", method_url("PATCH", "/chats/{chatId}")),
    _lim("Боты на профиль", "организация или ИП — 5, самозанятый — 2", "Bots per profile",
         "organisation or sole proprietor — 5, self-employed — 2", PREPARE),
    _lim("initData мини-приложения", "рекомендуемый срок годности auth_date — 1 час", "Mini-app initData", "recommended auth_date validity — 1 hour", VALIDATION),
    _lim("URL мини-приложения", "только https://, до 1024 символов", "Mini-app URL", "https:// only, up to 1024 characters", WEBAPPS),
    _lim("SecureStorage мини-приложения", "до 10 ключей на бота и пользователя, не работает в веб-версии",
         "Mini-app SecureStorage", "up to 10 keys per bot and user, not available in the web client", BRIDGE),
]

# ---------------------------------------------------------------- updates

def _u(fields, ru="", en=""):
    return {"fields": fields, "note": ru, "note_en": en}


UPDATE_TYPES: dict[str, dict] = {
    "message_created": _u("message, user_locale?", "новое сообщение", "new message"),
    "message_callback": _u("callback {callback_id, payload, user, timestamp}, message?, user_locale?",
                           "нажатие callback-кнопки; ответьте POST /answers", "callback button press; answer with POST /answers"),
    "message_edited": _u("message", "сообщение изменено", "message edited"),
    "message_removed": _u("message_id, chat_id, user_id", "сообщение удалено", "message deleted"),
    "comment_created": _u("message", "комментарий к посту канала (с 2026-08)", "comment on a channel post (2026-08+)"),
    "comment_edited": _u("message", "с 2026-08", "2026-08+"),
    "comment_removed": _u("message_id, chat_id, user_id, post_id", "с 2026-08", "2026-08+"),
    "bot_added": _u("chat_id, user, is_channel", "бота добавили в чат или канал — запомните chat_id", "bot added to a chat or channel — store chat_id"),
    "bot_removed": _u("chat_id, user, is_channel", "бота удалили", "bot removed"),
    "user_added": _u("chat_id, user, is_channel, inviter_id?"),
    "user_removed": _u("chat_id, user, is_channel, admin_id?"),
    "bot_started": _u("chat_id, user, payload?, user_locale?", "пользователь нажал «Начать»; payload — из диплинка ?start=",
                      "user pressed Start; payload comes from the ?start= deep link"),
    "bot_stopped": _u("chat_id, user, user_locale?", "пользователь остановил бота", "user stopped the bot"),
    "dialog_cleared": _u("chat_id, user, user_locale?"),
    "dialog_removed": _u("chat_id, user, user_locale?"),
    "dialog_muted": _u("chat_id, user, muted_until, user_locale?"),
    "dialog_unmuted": _u("chat_id, user, user_locale?"),
    "chat_title_changed": _u("chat_id, user, title"),
    "bot_admin_permissions_changed": _u("chat_id, user_id, bot_id, is_channel, is_admin, permissions?",
                                        "с 2026-10; только через вебхук, в long polling пока нет", "2026-10+; webhook only, not yet in long polling"),
}


def _b(required, ru, en):
    return {"required": required, "note": ru, "note_en": en}


BUTTON_TYPES: dict[str, dict] = {
    "callback": _b(["payload"], "payload до 1024; нажатие приходит как message_callback", "payload up to 1024; the press arrives as message_callback"),
    "link": _b(["url"], "url до 2048", "url up to 2048"),
    "message": _b([], "отправляет текст кнопки в чат от имени пользователя", "sends the button text to the chat on behalf of the user"),
    "request_contact": _b([], "запрос контакта; в ответ contact с hash для проверки", "asks for the contact; a contact with a verifiable hash comes back"),
    "request_geo_location": _b([], "quick: true — без подтверждения пользователя", "quick: true — without user confirmation"),
    "open_app": _b(["web_app"], "web_app — публичное имя бота с мини-приложением; payload до 512, A-Za-z0-9_-; contact_id?",
                   "web_app — public name of the bot with the mini-app; payload up to 512, A-Za-z0-9_-; contact_id?"),
    "clipboard": _b(["payload"], "payload до 1024 — копируется в буфер", "payload up to 1024 — copied to the clipboard"),
}
WIDE_BUTTONS = {"link", "open_app", "request_geo_location", "request_contact"}

ATTACHMENT_TYPES = ["image", "video", "audio", "file", "sticker", "contact", "inline_keyboard", "location", "share"]

CHAT_ADMIN_PERMISSIONS = [
    "read_all_messages", "add_remove_members", "add_admins", "change_chat_info", "pin_message",
    "edit_link", "write", "edit", "delete", "can_call", "view_stats",
]


def _e(code, http, ru, en):
    return {"code": code, "http": http, "meaning": ru, "meaning_en": en}


ERRORS: list[dict] = [
    _e("attachment.not.ready", 400, "Файл ещё обрабатывается после загрузки. Повторите отправку с паузой (экспоненциально).",
       "The file is still being processed after upload. Retry sending with exponential backoff."),
    _e("chat.denied", 403, "Пересылка из этого чата или канала запрещена.", "Forwarding from this chat or channel is not allowed."),
    _e("add.participant.privacy", None, "Настройки приватности не дают добавить участника.", "Privacy settings prevent adding the participant."),
    _e("add.participant.not.found", None, "Пользователь не найден.", "User not found."),
    _e("File extension is forbidden", None, "Недопустимое расширение файла при загрузке (это текст сообщения, а не code).",
       "Forbidden file extension on upload (a message string, not a code)."),
    _e("HTTP 429", 429, "Превышен лимит запросов. Держите не больше 30 запросов в секунду и 2 сообщений в секунду на чат.",
       "Rate limit exceeded. Stay under 30 requests per second and 2 messages per second per chat."),
    _e("x509 / CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate", None,
       "В системе нет корневого сертификата Минцифры. Добавьте его в доверенные, не отключайте проверку TLS.",
       "The Russian Trusted Root CA (Ministry of Digital Development) is missing. Add it to the trust store, do not disable TLS verification."),
]


def _c(date, ru, en):
    return {"date": date, "change": ru, "change_en": en}


CHANGELOG: list[dict] = [
    _c("2026-11", "Уточнено поведение notify в POST /messages и PUT /messages.", "notify behaviour in POST /messages and PUT /messages clarified."),
    _c("2026-10", "Новое обновление bot_admin_permissions_changed — только через вебхук.", "New update bot_admin_permissions_changed — webhook only."),
    _c("2026-09-09", "POST /chats/{chatId}/members ограничен; не используйте.", "POST /chats/{chatId}/members restricted; do not use it."),
    _c("2026-09", "Опубликована OpenAPI-спецификация: github.com/max-messenger/api-schema.", "OpenAPI spec published: github.com/max-messenger/api-schema."),
    _c("2026-08", "Комментарии к постам каналов: методы /messages/{messageId}/comments и события comment_*; description в PATCH /chats/{chatId}; disable_link_preview в POST /answers.",
       "Channel post comments: /messages/{messageId}/comments methods and comment_* updates; description in PATCH /chats/{chatId}; disable_link_preview in POST /answers."),
    _c("2026-07-19", "Обязательный переход на platform-api2.max.ru и сертификат Минцифры.",
       "Mandatory move to platform-api2.max.ru and the Russian Trusted Root CA."),
    _c("2026-07", "Новый метод PATCH /me/commands.", "New method PATCH /me/commands."),
    _c("2026-06-15", "Платформа для партнёров открыта самозанятым (до 2 ботов, 1 публичный канал).",
       "Partner platform opened to self-employed people (up to 2 bots, 1 public channel)."),
    _c("2026-06", "GET /chats удалён; лимиты размера в POST /uploads.", "GET /chats removed; size limits in POST /uploads."),
    _c("2026-05-25", "Вебхуки только по HTTPS с доверенным сертификатом; самоподписанные отклоняются.",
       "Webhooks only over HTTPS with a trusted certificate; self-signed rejected."),
]

# ---------------------------------------------------------------- articles

TOPICS: dict[str, dict] = {
    "auth": {
        "title": "Адрес API и авторизация", "title_en": "API host and auth",
        "text": (
            f"Базовый адрес {BASE_URL} (обязателен с 2026-07-19, старый {OLD_BASE_URL} устарел). "
            "Токен передаётся в заголовке `Authorization: <token>` без слова Bearer. "
            "Токен в query-параметре больше не принимается. Токен берут на business.max.ru → Чат-боты → бот → ⋮ → Настройки "
            "или командой «Получить токен» в боте «MAX для бизнеса». Утёкший токен перевыпустите."
        ),
        "text_en": (
            f"Base URL {BASE_URL} (mandatory since 2026-07-19, the old {OLD_BASE_URL} is deprecated). "
            "Send the token in the `Authorization: <token>` header, without Bearer. "
            "A token in the query string is no longer accepted. Get the token at business.max.ru → Chat bots → your bot → ⋮ → Settings, "
            "or with the Get token command in the MAX for Business bot. Reissue a leaked token."
        ),
        "source": DOCS,
    },
    "tls": {
        "title": "Сертификат Минцифры", "title_en": "Russian Trusted Root CA",
        "text": (
            "platform-api2.max.ru подписан Russian Trusted Root CA (Минцифры). Стандартные образы Docker, Node и Python "
            "ему не доверяют: ошибки `x509: certificate signed by unknown authority`, `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, "
            f"`CERTIFICATE_VERIFY_FAILED`. Скачайте PEM ({CERT_PEM}, страница {CERT_PAGE}) и добавьте: "
            "Python — `verify=путь` в requests/httpx или `SSL_CERT_FILE`; Node — `NODE_EXTRA_CA_CERTS=путь`; "
            "Debian/Ubuntu — положить .crt в /usr/local/share/ca-certificates и выполнить update-ca-certificates; curl — `--cacert`. "
            "Никогда не отключайте проверку (verify=False, NODE_TLS_REJECT_UNAUTHORIZED=0, InsecureSkipVerify, curl -k)."
        ),
        "text_en": (
            "platform-api2.max.ru is signed by the Russian Trusted Root CA (Ministry of Digital Development). Stock Docker, Node and Python "
            "images don't trust it: errors `x509: certificate signed by unknown authority`, `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, "
            f"`CERTIFICATE_VERIFY_FAILED`. Download the PEM ({CERT_PEM}, page {CERT_PAGE}) and add it: "
            "Python — `verify=path` in requests/httpx or `SSL_CERT_FILE`; Node — `NODE_EXTRA_CA_CERTS=path`; "
            "Debian/Ubuntu — put the .crt into /usr/local/share/ca-certificates and run update-ca-certificates; curl — `--cacert`. "
            "Never disable verification (verify=False, NODE_TLS_REJECT_UNAUTHORIZED=0, InsecureSkipVerify, curl -k)."
        ),
        "source": CERT_PAGE,
    },
    "webhook": {
        "title": "Вебхуки и long polling", "title_en": "Webhooks and long polling",
        "text": (
            "Продакшн — вебхук: POST /subscriptions {url, update_types?, secret?}. Только HTTPS на 443 (порт в url не указывать), "
            "сертификат доверенного УЦ или Минцифры, полная цепочка. Отвечайте 200 быстрее 30 с, тяжёлую работу делайте в фоне. "
            "Секрет приходит в заголовке X-Max-Bot-Api-Secret — сравнивайте за постоянное время (hmac.compare_digest). "
            "До 10 повторов (60 с, 150 с, 375 с…), через 8 ч без успешной доставки подписка снимается молча — следите и переподписывайтесь. "
            "Long polling (GET /updates) — только для разработки; вебхук и polling одновременно не работают. "
            "Обновления могут приходить повторно — делайте обработку идемпотентной."
        ),
        "text_en": (
            "Production uses a webhook: POST /subscriptions {url, update_types?, secret?}. HTTPS on 443 only (no port in the url), "
            "certificate from a trusted CA or the Ministry, full chain. Reply 200 within 30 s and do heavy work in the background. "
            "The secret arrives in the X-Max-Bot-Api-Secret header — compare it in constant time (hmac.compare_digest). "
            "Up to 10 retries (60 s, 150 s, 375 s…); after 8 h without a successful delivery the subscription is silently removed — monitor and resubscribe. "
            "Long polling (GET /updates) is for development only; webhook and polling don't work at the same time. "
            "Updates can be delivered twice — make handling idempotent."
        ),
        "source": method_url("POST", "/subscriptions"),
    },
    "messages": {
        "title": "Отправка сообщений", "title_en": "Sending messages",
        "text": (
            "POST /messages?chat_id=… (или ?user_id=… для личного диалога). Получатель — в query, не в теле. "
            "Тело NewMessageBody: text (до 4000), format (markdown | html), attachments, link {type: reply|forward, mid}, notify. "
            "disable_link_preview — query-параметр. Вставить картинку между абзацами нельзя: вложения идут отдельным массивом, "
            "для чередования шлите несколько сообщений. Отложенной отправки нет — свой планировщик. "
            "Правка (PUT) и удаление (DELETE) своих сообщений — только 24 часа. В каналах notify всегда true."
        ),
        "text_en": (
            "POST /messages?chat_id=… (or ?user_id=… for a private dialog). The recipient goes in the query, not the body. "
            "Body NewMessageBody: text (up to 4000), format (markdown | html), attachments, link {type: reply|forward, mid}, notify. "
            "disable_link_preview is a query parameter. You can't put an image between paragraphs: attachments are a separate array, "
            "send several messages to interleave. There is no scheduled sending — use your own scheduler. "
            "Editing (PUT) and deleting (DELETE) your own messages works for 24 hours only. In channels notify is always true."
        ),
        "source": method_url("POST", "/messages"),
    },
    "keyboard": {
        "title": "Кнопки", "title_en": "Buttons",
        "text": (
            "Клавиатура — это вложение {type: inline_keyboard, payload: {buttons: [[…]]}}, не reply_markup. "
            "Типы кнопок: callback (payload), link (url), message, request_contact, request_geo_location (quick), "
            "open_app (web_app — имя бота, payload), clipboard (payload). До 210 кнопок, 30 рядов, 7 в ряду, "
            "3 в ряду с link/open_app/request_*. Нажатие callback приходит как message_callback, ответ — POST /answers?callback_id=… "
            "с notification и/или message (правка исходного сообщения одним запросом). Нет аналогов pay, login_url, switch_inline_query "
            "и обычной reply-клавиатуры."
        ),
        "text_en": (
            "A keyboard is an attachment {type: inline_keyboard, payload: {buttons: [[…]]}}, not reply_markup. "
            "Button types: callback (payload), link (url), message, request_contact, request_geo_location (quick), "
            "open_app (web_app — bot name, payload), clipboard (payload). Up to 210 buttons, 30 rows, 7 per row, "
            "3 per row with link/open_app/request_*. A callback press arrives as message_callback; answer with POST /answers?callback_id=… "
            "with notification and/or message (edits the original message in the same request). There is no equivalent of pay, login_url, "
            "switch_inline_query or a regular reply keyboard."
        ),
        "source": method_url("POST", "/messages"),
    },
    "formatting": {
        "title": "Форматирование текста", "title_en": "Text formatting",
        "text": (
            "Markdown: **жирный** или __жирный__, *курсив* или _курсив_, ~~зачёркнутый~~, ++подчёркнутый++, `код`, "
            "^^выделение^^, > цитата, # заголовок, [ссылка](https://…), упоминание [Имя Фамилия](max://user/<id>). "
            "HTML: b/strong, i/em, s/del, u/ins, code/pre, a href, mark, blockquote, h1-h6, <a href=\"max://user/<id>\">. "
            "Списков, таблиц, горизонтальных линий и спойлеров нет. В блоке кода переносы строк превращаются в пробелы. "
            "В комментариях нельзя ссылки и упоминания. Пользовательский текст очищайте от *, _, `, <, > перед вставкой в разметку."
        ),
        "text_en": (
            "Markdown: **bold** or __bold__, *italic* or _italic_, ~~strikethrough~~, ++underline++, `code`, "
            "^^highlight^^, > quote, # heading, [link](https://…), mention [First Last](max://user/<id>). "
            "HTML: b/strong, i/em, s/del, u/ins, code/pre, a href, mark, blockquote, h1-h6, <a href=\"max://user/<id>\">. "
            "No lists, tables, horizontal rules or spoilers. Line breaks inside a code block become spaces. "
            "Comments can't contain links or mentions. Strip *, _, `, <, > from user text before putting it into markup."
        ),
        "source": DOCS,
    },
    "uploads": {
        "title": "Загрузка файлов", "title_en": "Uploading files",
        "text": (
            "1) POST /uploads?type=image|video|audio|file → {url, token?}. 2) Загрузите файл на ЭТОТ url (multipart, поле data) — "
            "хосты загрузки не постоянны, не зашивайте их. 3) Вложите {type, payload: {token}} в сообщение. "
            "Если при отправке пришло attachment.not.ready — файл ещё обрабатывается, повторите с паузой. "
            "Картинку можно отправить без загрузки: {type: image, payload: {url: \"https://…\"}}. type=photo больше не принимается."
        ),
        "text_en": (
            "1) POST /uploads?type=image|video|audio|file → {url, token?}. 2) Upload the file to THAT url (multipart, field data) — "
            "upload hosts change, don't hardcode them. 3) Attach {type, payload: {token}} to the message. "
            "If sending returns attachment.not.ready, the file is still processing — retry with a delay. "
            "An image can be sent without uploading: {type: image, payload: {url: \"https://…\"}}. type=photo is no longer accepted."
        ),
        "source": method_url("POST", "/uploads"),
    },
    "chats": {
        "title": "Чаты без GET /chats", "title_en": "Chats without GET /chats",
        "text": (
            "Списка чатов в API больше нет (удалён в июне 2026). Храните chat_id сами: добавляйте по bot_added и bot_started, "
            "убирайте по bot_removed. Один чат: GET /chats/{chatId}. Добавлять участников ботом нельзя с 2026-09-09. "
            "Для правки и удаления чужих сообщений бот должен быть админом с правом read_all_messages плюс edit/delete/write."
        ),
        "text_en": (
            "The API no longer lists chats (removed in June 2026). Store chat_id yourself: add on bot_added and bot_started, "
            "remove on bot_removed. One chat: GET /chats/{chatId}. Bots can't add members since 2026-09-09. "
            "To edit or delete other people's messages the bot must be an admin with read_all_messages plus edit/delete/write."
        ),
        "source": DOCS,
    },
    "mini_apps": {
        "title": "Мини-приложения и MAX Bridge", "title_en": "Mini-apps and MAX Bridge",
        "text": (
            "Подключите <script src=\"https://st.max.ru/js/max-web-app.js\"></script>, объект — window.WebApp "
            "(не window.Telegram.WebApp). Мини-приложение привязано к боту: business.max.ru → бот → Настройки → URL (только https). "
            "Есть: initData/initDataUnsafe, platform, BackButton, DeviceStorage, SecureStorage (10 ключей), BiometricManager, "
            "HapticFeedback, NfcManager (Android), ScreenCapture, requestContact, openLink, openMaxLink, downloadFile, "
            "shareContent, shareMaxContent, openCodeReader, enable/disableClosingConfirmation. "
            "Нет: MainButton, themeParams, CloudStorage, событий onEvent. Хранилища не работают в веб-версии. "
            "React-компоненты в стиле MAX — @maxhub/max-ui."
        ),
        "text_en": (
            "Load <script src=\"https://st.max.ru/js/max-web-app.js\"></script>; the object is window.WebApp "
            "(not window.Telegram.WebApp). A mini-app belongs to a bot: business.max.ru → bot → Settings → URL (https only). "
            "Available: initData/initDataUnsafe, platform, BackButton, DeviceStorage, SecureStorage (10 keys), BiometricManager, "
            "HapticFeedback, NfcManager (Android), ScreenCapture, requestContact, openLink, openMaxLink, downloadFile, "
            "shareContent, shareMaxContent, openCodeReader, enable/disableClosingConfirmation. "
            "Not available: MainButton, themeParams, CloudStorage, onEvent events. Storages don't work in the web client. "
            "MAX-style React components — @maxhub/max-ui."
        ),
        "source": BRIDGE,
    },
    "init_data": {
        "title": "Проверка initData", "title_en": "Validating initData",
        "text": (
            "Проверяйте только на сервере и только сырую строку window.WebApp.initData, не initDataUnsafe. "
            "Алгоритм: разобрать query-строку (один раз декодировать), вынуть hash, остальные пары key=value отсортировать и склеить через \\n; "
            "secret = HMAC_SHA256(key=\"WebAppData\", msg=bot_token); hash = hex(HMAC_SHA256(key=secret, msg=строка)); "
            "сравнить за постоянное время и проверить, что auth_date не старше часа. "
            "Телефон из requestContact() проверяется иначе: HMAC_SHA256(key=bot_token, msg=\"authDate=…\\nphone=…\\nuserId=…\"), телефон без +. "
            "Контакт от кнопки request_contact: HMAC_SHA256(key=bot_token, msg=vcf_info)."
        ),
        "text_en": (
            "Validate on the server only, and only the raw window.WebApp.initData string, never initDataUnsafe. "
            "Algorithm: parse the query string (decode once), take out hash, sort the remaining key=value pairs and join them with \\n; "
            "secret = HMAC_SHA256(key=\"WebAppData\", msg=bot_token); hash = hex(HMAC_SHA256(key=secret, msg=string)); "
            "compare in constant time and check that auth_date is not older than an hour. "
            "The phone from requestContact() uses another formula: HMAC_SHA256(key=bot_token, msg=\"authDate=…\\nphone=…\\nuserId=…\"), phone without +. "
            "A contact from a request_contact button: HMAC_SHA256(key=bot_token, msg=vcf_info)."
        ),
        "source": VALIDATION,
    },
    "deeplinks": {
        "title": "Диплинки", "title_en": "Deep links",
        "text": (
            "Бот: https://max.ru/<bot>?start=<payload> — payload до 128 символов, приходит в bot_started.payload. "
            "Мини-приложение: https://max.ru/<bot>?startapp=<payload> — до 512, только A-Za-z0-9_-, приходит в initData.start_param. "
            "Поделиться текстом без бота: https://max.ru/:share?text=<url-encoded текст> — открывает выбор чата. "
            "Упоминание пользователя в тексте: max://user/<id>. Нужны клиенты iOS ≥ 2.7.0, Android ≥ 2.9.0."
        ),
        "text_en": (
            "Bot: https://max.ru/<bot>?start=<payload> — payload up to 128 characters, arrives in bot_started.payload. "
            "Mini-app: https://max.ru/<bot>?startapp=<payload> — up to 512, A-Za-z0-9_- only, arrives in initData.start_param. "
            "Share text without a bot: https://max.ru/:share?text=<url-encoded text> — opens the chat picker. "
            "User mention in text: max://user/<id>. Needs iOS client ≥ 2.7.0, Android ≥ 2.9.0."
        ),
        "source": WEBAPPS,
    },
    "access": {
        "title": "Кто может создать бота", "title_en": "Who can create a bot",
        "text": (
            "Бота, канал и мини-приложение создают на платформе «MAX для партнёров» (business.max.ru) после верификации: "
            "организации и ИП (до 5 ботов), с 2026-06-15 — самозанятые через Госуслуги (до 2 ботов и 1 публичного канала). "
            "Физлица без статуса и нерезиденты бота создать не могут. Бот проходит модерацию."
        ),
        "text_en": (
            "Bots, channels and mini-apps are created on the MAX for Partners platform (business.max.ru) after verification: "
            "Russian organisations and sole proprietors (up to 5 bots), and since 2026-06-15 self-employed people via Gosuslugi "
            "(up to 2 bots and 1 public channel). Individuals without a status and non-residents can't create bots. Bots go through moderation. "
            "Anyone can still build and test bot code; publishing needs an eligible profile."
        ),
        "source": PREPARE,
    },
    "libraries": {
        "title": "Официальные библиотеки и спецификация", "title_en": "Official libraries and spec",
        "text": (
            "TypeScript: @maxhub/max-bot-api (Node ≥ 20.19, только ESM), github.com/max-messenger/max-bot-api-client-ts. "
            "Go: github.com/max-messenger/max-bot-api-client-go/v2 и фреймворк github.com/max-messenger/maxbot. "
            "OpenAPI: github.com/max-messenger/api-schema (schema.yaml) — из неё можно сгенерировать клиент на Python, PHP, Java, Kotlin и др. "
            "Официальной библиотеки для Python нет — используйте httpx/requests напрямую или сгенерированный клиент. "
            "UI мини-приложений: @maxhub/max-ui."
        ),
        "text_en": (
            "TypeScript: @maxhub/max-bot-api (Node ≥ 20.19, ESM only), github.com/max-messenger/max-bot-api-client-ts. "
            "Go: github.com/max-messenger/max-bot-api-client-go/v2 and the framework github.com/max-messenger/maxbot. "
            "OpenAPI: github.com/max-messenger/api-schema (schema.yaml) — generate a client in Python, PHP, Java, Kotlin, etc. "
            "There is no official Python library — use httpx/requests directly or a generated client. "
            "Mini-app UI: @maxhub/max-ui."
        ),
        "source": DOCS,
    },
    "sources": {
        "title": "Первоисточники", "title_en": "Primary sources",
        "text": (
            f"Методы и лимиты: {DOCS}. Изменения: {CHANGELOG_URL}. Схема: {SCHEMA}. Мини-приложения: {BRIDGE}, проверка данных: {VALIDATION}. "
            f"Сертификат: {CERT_PAGE}. При расхождении верьте dev.max.ru, затем схеме, затем коду официальных клиентов."
        ),
        "text_en": (
            f"Methods and limits: {DOCS}. Changes: {CHANGELOG_URL}. Schema: {SCHEMA}. Mini-apps: {BRIDGE}, data validation: {VALIDATION}. "
            f"Certificate: {CERT_PAGE}. When they disagree, trust dev.max.ru, then the schema, then the official clients' code. "
            "The docs are in Russian."
        ),
        "source": DOCS,
    },
}


def search(query: str, limit: int = 8) -> list[dict]:
    """Keyword search over topics, endpoints, limits, errors and update types, in both languages."""
    words = [w for w in query.lower().replace("/", " / ").split() if len(w) > 1]
    if not words:
        return []
    hits: list[tuple[int, dict]] = []

    def score(*parts: str | None) -> int:
        t = " ".join(p for p in parts if p).lower()
        return sum(t.count(w) for w in words)

    for key, t in TOPICS.items():
        s = score(key, t["title"], t["title_en"], t["text"], t["text_en"]) + (5 if key in words else 0)
        if s:
            lt = loc(t)
            hits.append((s, {"kind": "topic", "topic": key, "title": lt["title"], "text": lt["text"], "source": t["source"]}))
    for ep in ENDPOINTS:
        s = score(ep["verb"], ep["path"], ep["group"], ep["summary"], ep["summary_en"], ep.get("body"))
        if s:
            hits.append((s, {"kind": "endpoint", "verb": ep["verb"], "path": ep["path"], "summary": loc(ep)["summary"],
                             "source": method_url(ep["verb"], ep["path"])}))
    for lim in LIMITS:
        s = score(lim["what"], lim["what_en"], lim["value"], lim["value_en"])
        if s:
            hits.append((s, {"kind": "limit", **loc(lim)}))
    for err in ERRORS:
        s = score(err["code"], err["meaning"], err["meaning_en"])
        if s:
            hits.append((s, {"kind": "error", **loc(err)}))
    for name, u in UPDATE_TYPES.items():
        s = score(name, u["fields"], u["note"], u["note_en"])
        if s:
            hits.append((s, {"kind": "update_type", "update_type": name, **loc(u), "source": f"{DOCS}/objects/Update"}))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:limit]]
