"""MAX Bot API and Mini Apps facts, checked against dev.max.ru and the official OpenAPI schema.

Every entry carries a source so an agent can show where a fact comes from.
When the live docs disagree with this file, the live docs win: run `max_api_reference`
with topic "sources" to get the links.
"""

from __future__ import annotations

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


def method_url(verb: str, path: str) -> str:
    """Docs page for one method: /docs-api/methods/<VERB>/<path with {x} as -x->."""
    p = path.strip("/").replace("{", "-").replace("}", "-")
    return f"{DOCS}/methods/{verb.upper()}/{p}"


# ---------------------------------------------------------------- endpoints

ENDPOINTS: list[dict] = [
    {"verb": "GET", "path": "/me", "group": "bots", "summary": "Информация о боте (BotInfo)", "query": {}, "body": None},
    {"verb": "PATCH", "path": "/me/commands", "group": "bots", "summary": "Добавить, изменить или удалить команды бота (до 32 команд; пустой массив удаляет все)",
     "query": {}, "body": "BotCommandsPatch {commands: [{name 1-64, description 1-128}]}", "since": "2026-07"},
    {"verb": "GET", "path": "/chats/{chatId}", "group": "chats", "summary": "Информация о группе или канале", "query": {}, "body": None},
    {"verb": "PATCH", "path": "/chats/{chatId}", "group": "chats", "summary": "Изменить название, иконку, описание, закреп",
     "query": {}, "body": "ChatPatch {icon?, title? 1-200, description? <=16000 (с 2026-08), pin?, notify?}"},
    {"verb": "POST", "path": "/chats/{chatId}/actions", "group": "chats", "summary": "Действие бота в чате (typing_on, sending_photo, mark_seen и др.)", "query": {}, "body": "ActionRequestBody {action}"},
    {"verb": "GET", "path": "/chats/{chatId}/pin", "group": "chats", "summary": "Закреплённое сообщение", "query": {}, "body": None},
    {"verb": "PUT", "path": "/chats/{chatId}/pin", "group": "chats", "summary": "Закрепить сообщение", "query": {}, "body": "PinMessageBody {message_id, notify?}"},
    {"verb": "DELETE", "path": "/chats/{chatId}/pin", "group": "chats", "summary": "Открепить сообщение", "query": {}, "body": None},
    {"verb": "GET", "path": "/chats/{chatId}/members/me", "group": "chats", "summary": "Членство самого бота и его права", "query": {}, "body": None},
    {"verb": "DELETE", "path": "/chats/{chatId}/members/me", "group": "chats", "summary": "Бот выходит из чата или канала", "query": {}, "body": None},
    {"verb": "GET", "path": "/chats/{chatId}/members/admins", "group": "chats", "summary": "Список администраторов", "query": {}, "body": None},
    {"verb": "POST", "path": "/chats/{chatId}/members/admins", "group": "chats", "summary": "Назначить администратора. Работает как полная замена прав, несмотря на POST",
     "query": {}, "body": "ChatAdminsList {admins: [{user_id, permissions[]}]}"},
    {"verb": "DELETE", "path": "/chats/{chatId}/members/admins/{userId}", "group": "chats", "summary": "Снять права администратора", "query": {}, "body": None},
    {"verb": "GET", "path": "/chats/{chatId}/members", "group": "chats", "summary": "Участники чата", "query": {"user_ids": "csv", "marker": "int64", "count": "1-100, по умолчанию 20"}, "body": None},
    {"verb": "POST", "path": "/chats/{chatId}/members", "group": "chats", "summary": "Добавить участников. ОГРАНИЧЕН с 2026-09-09, не строить на нём",
     "query": {}, "body": "UserIdsList {user_ids: <=100}", "deprecated": True},
    {"verb": "DELETE", "path": "/chats/{chatId}/members", "group": "chats", "summary": "Удалить участника", "query": {"user_id": "обязателен", "block": "bool, по умолчанию false"}, "body": None},
    {"verb": "GET", "path": "/subscriptions", "group": "subscriptions", "summary": "Список вебхук-подписок", "query": {}, "body": None},
    {"verb": "POST", "path": "/subscriptions", "group": "subscriptions", "summary": "Подписать URL на обновления (вебхук)",
     "query": {}, "body": "SubscriptionRequestBody {url https://, update_types?[], secret? 5-256 [A-Za-z0-9_-]}"},
    {"verb": "DELETE", "path": "/subscriptions", "group": "subscriptions", "summary": "Отписать URL", "query": {"url": "обязателен"}, "body": None},
    {"verb": "GET", "path": "/updates", "group": "subscriptions", "summary": "Long polling (только для разработки и тестов)",
     "query": {"limit": "1-1000, по умолчанию 100", "timeout": "0-90 с, по умолчанию 30", "marker": "int64", "types": "csv"}, "body": None},
    {"verb": "POST", "path": "/uploads", "group": "upload", "summary": "Получить адрес для загрузки файла", "query": {"type": "image | video | audio | file (photo больше не принимается)"}, "body": None},
    {"verb": "GET", "path": "/messages", "group": "messages", "summary": "Сообщения чата (новые сначала) или по id",
     "query": {"chat_id": "int64", "message_ids": "csv", "before": "int64", "after": "int64", "count": "1-100, по умолчанию 50"}, "body": None},
    {"verb": "POST", "path": "/messages", "group": "messages", "summary": "Отправить сообщение",
     "query": {"user_id": "int64, личный диалог", "chat_id": "int64, чат или канал", "disable_link_preview": "bool"}, "body": "NewMessageBody {text? <=4000, attachments?, link?, notify?, format?}"},
    {"verb": "PUT", "path": "/messages", "group": "messages", "summary": "Изменить своё сообщение (в течение 24 ч). attachments: null оставляет вложения, [] удаляет",
     "query": {"message_id": "обязателен"}, "body": "NewMessageBody"},
    {"verb": "DELETE", "path": "/messages", "group": "messages", "summary": "Удалить сообщение (в течение 24 ч)", "query": {"message_id": "обязателен"}, "body": None},
    {"verb": "GET", "path": "/messages/{messageId}", "group": "messages", "summary": "Одно сообщение", "query": {}, "body": None},
    {"verb": "GET", "path": "/videos/{videoToken}", "group": "messages", "summary": "Ссылки на видео (mp4 1080…144, hls) и метаданные", "query": {}, "body": None},
    {"verb": "POST", "path": "/answers", "group": "messages", "summary": "Ответ на нажатие callback-кнопки: тост и/или правка исходного сообщения. Не чаще 2 раз в секунду на чат",
     "query": {"callback_id": "обязателен", "disable_link_preview": "bool (с 2026-08)"}, "body": "CallbackAnswer {message?: NewMessageBody, notification?: string}"},
    {"verb": "GET", "path": "/messages/{messageId}/comments", "group": "comments", "summary": "Комментарии к посту канала", "query": {"comment_ids": "csv", "before": "int64", "after": "int64", "count": "1-100"}, "body": None, "since": "2026-08"},
    {"verb": "POST", "path": "/messages/{messageId}/comments", "group": "comments", "summary": "Оставить комментарий (без вложений, без ссылок и упоминаний)",
     "query": {"disable_link_preview": "bool"}, "body": "NewCommentBody {text, link?, format?}", "since": "2026-08"},
    {"verb": "PUT", "path": "/messages/{messageId}/comments", "group": "comments", "summary": "Изменить комментарий", "query": {"comment_id": "обязателен"}, "body": "NewCommentBody", "since": "2026-08"},
    {"verb": "DELETE", "path": "/messages/{messageId}/comments", "group": "comments", "summary": "Удалить комментарий", "query": {"comment_id": "обязателен"}, "body": None, "since": "2026-08"},
    {"verb": "GET", "path": "/messages/{messageId}/comments/{commentId}", "group": "comments", "summary": "Один комментарий", "query": {}, "body": None, "since": "2026-08"},
]

REMOVED_ENDPOINTS = {
    ("GET", "/chats"): "Удалён в июне 2026. Список чатов ведите сами по обновлениям bot_added / bot_removed / bot_started; один чат: GET /chats/{chatId}.",
    ("POST", "/webhook"): "Такого метода нет. Вебхук подключается через POST /subscriptions.",
}


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

LIMITS: list[dict] = [
    {"what": "Текст сообщения или комментария", "value": "до 4000 символов (символов, не байт; разметка и эмодзи считаются)", "source": method_url("POST", "/messages")},
    {"what": "Запросы к API", "value": "30 в секунду на platform-api2.max.ru", "source": "https://dev.max.ru/docs/chatbots/bots-coding/prepare"},
    {"what": "Сообщения в один чат", "value": "не больше 2 в секунду в один диалог, группу или канал", "source": method_url("POST", "/messages")},
    {"what": "Ответы на callback (POST /answers)", "value": "не больше 2 в секунду на чат", "source": method_url("POST", "/answers")},
    {"what": "Long polling", "value": "пауза между вызовами от 300 мс; timeout 0-90 с; limit 1-1000", "source": method_url("GET", "/updates")},
    {"what": "Правка и удаление своих сообщений", "value": "в течение 24 часов", "source": method_url("PUT", "/messages")},
    {"what": "Вложения в одном сообщении", "value": "до 12 фото и видео суммарно + 1 inline_keyboard; file — только один и максимум с 1 клавиатурой; audio, sticker, contact — единственное вложение", "source": method_url("POST", "/messages")},
    {"what": "Клавиатура", "value": "до 210 кнопок, до 30 рядов, до 7 кнопок в ряду; до 3 в ряду, если в нём link, open_app, request_geo_location или request_contact", "source": method_url("POST", "/messages")},
    {"what": "Текст кнопки", "value": "1-128 символов; для полного отображения около 20 при 1 кнопке в ряду, 10 при 2, 5 при 3, 3 при 4", "source": method_url("POST", "/messages")},
    {"what": "payload callback- и clipboard-кнопки", "value": "до 1024 символов", "source": method_url("POST", "/messages")},
    {"what": "url link-кнопки и ссылки в разметке", "value": "до 2048 символов", "source": method_url("POST", "/messages")},
    {"what": "payload open_app-кнопки", "value": "до 512 символов, только A-Z a-z 0-9 _ -", "source": SCHEMA},
    {"what": "Диплинк бота ?start=", "value": "payload до 128 символов, длиннее — не доходит до бота", "source": "https://dev.max.ru/docs/chatbots/bots-coding/prepare"},
    {"what": "Диплинк мини-приложения ?startapp=", "value": "payload до 512 символов, только A-Z a-z 0-9 _ -; иначе молча отбрасывается", "source": "https://dev.max.ru/docs/webapps/introduction"},
    {"what": "Команды бота", "value": "до 32; name 1-64, description 1-128", "source": method_url("PATCH", "/me/commands")},
    {"what": "Секрет вебхука", "value": "5-256 символов, A-Z a-z 0-9 _ -", "source": method_url("POST", "/subscriptions")},
    {"what": "Вебхук", "value": "только HTTPS на порту 443, сертификат доверенного УЦ или Минцифры (самоподписанные и HTTP отклоняются с 2026-05-25); ответ 200 за 30 с; до 10 повторов (60 с, ×2.5); через 8 ч без 200 подписка снимается", "source": method_url("POST", "/subscriptions")},
    {"what": "Размер файлов", "value": "фото до 50 МБ и до 7680×7680; видео до 250 МБ; аудио до 256 МБ и 60 мин; файл до 4 ГБ", "source": method_url("POST", "/uploads")},
    {"what": "Название чата", "value": "1-200 символов; описание до 16000", "source": method_url("PATCH", "/chats/{chatId}")},
    {"what": "Боты на профиль", "value": "организация или ИП — 5, самозанятый — 2", "source": "https://dev.max.ru/docs/chatbots/bots-coding/prepare"},
    {"what": "initData мини-приложения", "value": "рекомендуемый срок годности auth_date — 1 час", "source": VALIDATION},
    {"what": "URL мини-приложения", "value": "только https://, до 1024 символов", "source": "https://dev.max.ru/docs/webapps/introduction"},
    {"what": "SecureStorage мини-приложения", "value": "до 10 ключей на бота и пользователя, не работает в веб-версии", "source": BRIDGE},
]

# ---------------------------------------------------------------- updates

UPDATE_TYPES: dict[str, dict] = {
    "message_created": {"fields": "message, user_locale?", "note": "новое сообщение"},
    "message_callback": {"fields": "callback {callback_id, payload, user, timestamp}, message?, user_locale?", "note": "нажатие callback-кнопки; ответьте POST /answers"},
    "message_edited": {"fields": "message", "note": "сообщение изменено"},
    "message_removed": {"fields": "message_id, chat_id, user_id", "note": "сообщение удалено"},
    "comment_created": {"fields": "message", "note": "комментарий к посту канала (с 2026-08)"},
    "comment_edited": {"fields": "message", "note": "с 2026-08"},
    "comment_removed": {"fields": "message_id, chat_id, user_id, post_id", "note": "с 2026-08"},
    "bot_added": {"fields": "chat_id, user, is_channel", "note": "бота добавили в чат или канал — запомните chat_id"},
    "bot_removed": {"fields": "chat_id, user, is_channel", "note": "бота удалили"},
    "user_added": {"fields": "chat_id, user, is_channel, inviter_id?", "note": ""},
    "user_removed": {"fields": "chat_id, user, is_channel, admin_id?", "note": ""},
    "bot_started": {"fields": "chat_id, user, payload?, user_locale?", "note": "пользователь нажал «Начать»; payload — из диплинка ?start="},
    "bot_stopped": {"fields": "chat_id, user, user_locale?", "note": "пользователь остановил бота"},
    "dialog_cleared": {"fields": "chat_id, user, user_locale?", "note": ""},
    "dialog_removed": {"fields": "chat_id, user, user_locale?", "note": ""},
    "dialog_muted": {"fields": "chat_id, user, muted_until, user_locale?", "note": ""},
    "dialog_unmuted": {"fields": "chat_id, user, user_locale?", "note": ""},
    "chat_title_changed": {"fields": "chat_id, user, title", "note": ""},
    "bot_admin_permissions_changed": {"fields": "chat_id, user_id, bot_id, is_channel, is_admin, permissions?", "note": "с 2026-10; только через вебхук, в long polling пока нет"},
}

BUTTON_TYPES: dict[str, dict] = {
    "callback": {"required": ["payload"], "note": "payload до 1024; нажатие приходит как message_callback"},
    "link": {"required": ["url"], "note": "url до 2048"},
    "message": {"required": [], "note": "отправляет текст кнопки в чат от имени пользователя"},
    "request_contact": {"required": [], "note": "запрос контакта; в ответ contact с hash для проверки"},
    "request_geo_location": {"required": [], "note": "quick: true — без подтверждения пользователя"},
    "open_app": {"required": ["web_app"], "note": "web_app — публичное имя бота с мини-приложением; payload до 512, A-Za-z0-9_-; contact_id?"},
    "clipboard": {"required": ["payload"], "note": "payload до 1024 — копируется в буфер"},
}
WIDE_BUTTONS = {"link", "open_app", "request_geo_location", "request_contact"}

ATTACHMENT_TYPES = ["image", "video", "audio", "file", "sticker", "contact", "inline_keyboard", "location", "share"]

CHAT_ADMIN_PERMISSIONS = [
    "read_all_messages", "add_remove_members", "add_admins", "change_chat_info", "pin_message",
    "edit_link", "write", "edit", "delete", "can_call", "view_stats",
]

ERRORS: list[dict] = [
    {"code": "attachment.not.ready", "http": 400, "meaning": "Файл ещё обрабатывается после загрузки. Повторите отправку с паузой (экспоненциально)."},
    {"code": "chat.denied", "http": 403, "meaning": "Пересылка из этого чата или канала запрещена."},
    {"code": "add.participant.privacy", "http": None, "meaning": "Настройки приватности не дают добавить участника."},
    {"code": "add.participant.not.found", "http": None, "meaning": "Пользователь не найден."},
    {"code": "File extension is forbidden", "http": None, "meaning": "Недопустимое расширение файла при загрузке (это текст сообщения, а не code)."},
    {"code": "HTTP 429", "http": 429, "meaning": "Превышен лимит запросов. Держите не больше 30 запросов в секунду и 2 сообщений в секунду на чат."},
    {"code": "x509 / CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate", "http": None,
     "meaning": "В системе нет корневого сертификата Минцифры. Добавьте его в доверенные, не отключайте проверку TLS."},
]

CHANGELOG: list[dict] = [
    {"date": "2026-11", "change": "Уточнено поведение notify в POST /messages и PUT /messages."},
    {"date": "2026-10", "change": "Новое обновление bot_admin_permissions_changed — только через вебхук."},
    {"date": "2026-09-09", "change": "POST /chats/{chatId}/members ограничен; не используйте."},
    {"date": "2026-09", "change": "Опубликована OpenAPI-спецификация: github.com/max-messenger/api-schema."},
    {"date": "2026-08", "change": "Комментарии к постам каналов: методы /messages/{messageId}/comments и события comment_*; description в PATCH /chats/{chatId}; disable_link_preview в POST /answers."},
    {"date": "2026-07-19", "change": "Обязательный переход на platform-api2.max.ru и сертификат Минцифры."},
    {"date": "2026-07", "change": "Новый метод PATCH /me/commands."},
    {"date": "2026-06-15", "change": "Платформа для партнёров открыта самозанятым (до 2 ботов, 1 публичный канал)."},
    {"date": "2026-06", "change": "GET /chats удалён; лимиты размера в POST /uploads."},
    {"date": "2026-05-25", "change": "Вебхуки только по HTTPS с доверенным сертификатом; самоподписанные отклоняются."},
]

# ---------------------------------------------------------------- articles

TOPICS: dict[str, dict] = {
    "auth": {
        "title": "Адрес API и авторизация",
        "text": (
            f"Базовый адрес {BASE_URL} (обязателен с 2026-07-19, старый {OLD_BASE_URL} устарел). "
            "Токен передаётся в заголовке `Authorization: <token>` без слова Bearer. "
            "Токен в query-параметре больше не принимается. Токен берут на business.max.ru → Чат-боты → бот → ⋮ → Настройки "
            "или командой «Получить токен» в боте «MAX для бизнеса». Утёкший токен перевыпустите."
        ),
        "source": DOCS,
    },
    "tls": {
        "title": "Сертификат Минцифры",
        "text": (
            "platform-api2.max.ru подписан Russian Trusted Root CA (Минцифры). Стандартные образы Docker, Node и Python "
            "ему не доверяют: ошибки `x509: certificate signed by unknown authority`, `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, "
            f"`CERTIFICATE_VERIFY_FAILED`. Скачайте PEM ({CERT_PEM}, страница {CERT_PAGE}) и добавьте: "
            "Python — `verify=путь` в requests/httpx или `SSL_CERT_FILE`; Node — `NODE_EXTRA_CA_CERTS=путь`; "
            "Debian/Ubuntu — положить .crt в /usr/local/share/ca-certificates и выполнить update-ca-certificates; curl — `--cacert`. "
            "Никогда не отключайте проверку (verify=False, NODE_TLS_REJECT_UNAUTHORIZED=0, InsecureSkipVerify, curl -k)."
        ),
        "source": CERT_PAGE,
    },
    "webhook": {
        "title": "Вебхуки и long polling",
        "text": (
            "Продакшн — вебхук: POST /subscriptions {url, update_types?, secret?}. Только HTTPS на 443 (порт в url не указывать), "
            "сертификат доверенного УЦ или Минцифры, полная цепочка. Отвечайте 200 быстрее 30 с, тяжёлую работу делайте в фоне. "
            "Секрет приходит в заголовке X-Max-Bot-Api-Secret — сравнивайте за постоянное время (hmac.compare_digest). "
            "До 10 повторов (60 с, 150 с, 375 с…), через 8 ч без успешной доставки подписка снимается молча — следите и переподписывайтесь. "
            "Long polling (GET /updates) — только для разработки; вебхук и polling одновременно не работают. "
            "Обновления могут приходить повторно — делайте обработку идемпотентной."
        ),
        "source": method_url("POST", "/subscriptions"),
    },
    "messages": {
        "title": "Отправка сообщений",
        "text": (
            "POST /messages?chat_id=… (или ?user_id=… для личного диалога). Получатель — в query, не в теле. "
            "Тело NewMessageBody: text (до 4000), format (markdown | html), attachments, link {type: reply|forward, mid}, notify. "
            "disable_link_preview — query-параметр. Вставить картинку между абзацами нельзя: вложения идут отдельным массивом, "
            "для чередования шлите несколько сообщений. Отложенной отправки нет — свой планировщик. "
            "Правка (PUT) и удаление (DELETE) своих сообщений — только 24 часа. В каналах notify всегда true."
        ),
        "source": method_url("POST", "/messages"),
    },
    "keyboard": {
        "title": "Кнопки",
        "text": (
            "Клавиатура — это вложение {type: inline_keyboard, payload: {buttons: [[…]]}}, не reply_markup. "
            "Типы кнопок: callback (payload), link (url), message, request_contact, request_geo_location (quick), "
            "open_app (web_app — имя бота, payload), clipboard (payload). До 210 кнопок, 30 рядов, 7 в ряду, "
            "3 в ряду с link/open_app/request_*. Нажатие callback приходит как message_callback, ответ — POST /answers?callback_id=… "
            "с notification и/или message (правка исходного сообщения одним запросом). Нет аналогов pay, login_url, switch_inline_query "
            "и обычной reply-клавиатуры."
        ),
        "source": method_url("POST", "/messages"),
    },
    "formatting": {
        "title": "Форматирование текста",
        "text": (
            "Markdown: **жирный** или __жирный__, *курсив* или _курсив_, ~~зачёркнутый~~, ++подчёркнутый++, `код`, "
            "^^выделение^^, > цитата, # заголовок, [ссылка](https://…), упоминание [Имя Фамилия](max://user/<id>). "
            "HTML: b/strong, i/em, s/del, u/ins, code/pre, a href, mark, blockquote, h1-h6, <a href=\"max://user/<id>\">. "
            "Списков, таблиц, горизонтальных линий и спойлеров нет. В блоке кода переносы строк превращаются в пробелы. "
            "В комментариях нельзя ссылки и упоминания. Пользовательский текст очищайте от *, _, `, <, > перед вставкой в разметку."
        ),
        "source": DOCS,
    },
    "uploads": {
        "title": "Загрузка файлов",
        "text": (
            "1) POST /uploads?type=image|video|audio|file → {url, token?}. 2) Загрузите файл на ЭТОТ url (multipart, поле data) — "
            "хосты загрузки не постоянны, не зашивайте их. 3) Вложите {type, payload: {token}} в сообщение. "
            "Если при отправке пришло attachment.not.ready — файл ещё обрабатывается, повторите с паузой. "
            "Картинку можно отправить без загрузки: {type: image, payload: {url: \"https://…\"}}. type=photo больше не принимается."
        ),
        "source": method_url("POST", "/uploads"),
    },
    "chats": {
        "title": "Чаты без GET /chats",
        "text": (
            "Списка чатов в API больше нет (удалён в июне 2026). Храните chat_id сами: добавляйте по bot_added и bot_started, "
            "убирайте по bot_removed. Один чат: GET /chats/{chatId}. Добавлять участников ботом нельзя с 2026-09-09. "
            "Для правки и удаления чужих сообщений бот должен быть админом с правом read_all_messages плюс edit/delete/write."
        ),
        "source": DOCS,
    },
    "mini_apps": {
        "title": "Мини-приложения и MAX Bridge",
        "text": (
            "Подключите <script src=\"https://st.max.ru/js/max-web-app.js\"></script>, объект — window.WebApp "
            "(не window.Telegram.WebApp). Мини-приложение привязано к боту: business.max.ru → бот → Настройки → URL (только https). "
            "Есть: initData/initDataUnsafe, platform, BackButton, DeviceStorage, SecureStorage (10 ключей), BiometricManager, "
            "HapticFeedback, NfcManager (Android), ScreenCapture, requestContact, openLink, openMaxLink, downloadFile, "
            "shareContent, shareMaxContent, openCodeReader, enable/disableClosingConfirmation. "
            "Нет: MainButton, themeParams, CloudStorage, событий onEvent. Хранилища не работают в веб-версии. "
            "React-компоненты в стиле MAX — @maxhub/max-ui."
        ),
        "source": BRIDGE,
    },
    "init_data": {
        "title": "Проверка initData",
        "text": (
            "Проверяйте только на сервере и только сырую строку window.WebApp.initData, не initDataUnsafe. "
            "Алгоритм: разобрать query-строку (один раз декодировать), вынуть hash, остальные пары key=value отсортировать и склеить через \\n; "
            "secret = HMAC_SHA256(key=\"WebAppData\", msg=bot_token); hash = hex(HMAC_SHA256(key=secret, msg=строка)); "
            "сравнить за постоянное время и проверить, что auth_date не старше часа. "
            "Телефон из requestContact() проверяется иначе: HMAC_SHA256(key=bot_token, msg=\"authDate=…\\nphone=…\\nuserId=…\"), телефон без +. "
            "Контакт от кнопки request_contact: HMAC_SHA256(key=bot_token, msg=vcf_info)."
        ),
        "source": VALIDATION,
    },
    "deeplinks": {
        "title": "Диплинки",
        "text": (
            "Бот: https://max.ru/<bot>?start=<payload> — payload до 128 символов, приходит в bot_started.payload. "
            "Мини-приложение: https://max.ru/<bot>?startapp=<payload> — до 512, только A-Za-z0-9_-, приходит в initData.start_param. "
            "Поделиться текстом без бота: https://max.ru/:share?text=<url-encoded текст> — открывает выбор чата. "
            "Упоминание пользователя в тексте: max://user/<id>. Нужны клиенты iOS ≥ 2.7.0, Android ≥ 2.9.0."
        ),
        "source": "https://dev.max.ru/docs/webapps/introduction",
    },
    "access": {
        "title": "Кто может создать бота",
        "text": (
            "Бота, канал и мини-приложение создают на платформе «MAX для партнёров» (business.max.ru) после верификации: "
            "организации и ИП (до 5 ботов), с 2026-06-15 — самозанятые через Госуслуги (до 2 ботов и 1 публичного канала). "
            "Физлица без статуса и нерезиденты бота создать не могут. Бот проходит модерацию."
        ),
        "source": "https://dev.max.ru/docs/chatbots/bots-coding/prepare",
    },
    "libraries": {
        "title": "Официальные библиотеки и спецификация",
        "text": (
            "TypeScript: @maxhub/max-bot-api (Node ≥ 20.19, только ESM), github.com/max-messenger/max-bot-api-client-ts. "
            "Go: github.com/max-messenger/max-bot-api-client-go/v2 и фреймворк github.com/max-messenger/maxbot. "
            "OpenAPI: github.com/max-messenger/api-schema (schema.yaml) — из неё можно сгенерировать клиент на Python, PHP, Java, Kotlin и др. "
            "Официальной библиотеки для Python нет — используйте httpx/requests напрямую или сгенерированный клиент. "
            "UI мини-приложений: @maxhub/max-ui."
        ),
        "source": DOCS,
    },
    "sources": {
        "title": "Первоисточники",
        "text": (
            f"Методы и лимиты: {DOCS}. Изменения: {CHANGELOG_URL}. Схема: {SCHEMA}. Мини-приложения: {BRIDGE}, проверка данных: {VALIDATION}. "
            f"Сертификат: {CERT_PAGE}. При расхождении верьте dev.max.ru, затем схеме, затем коду официальных клиентов."
        ),
        "source": DOCS,
    },
}


def search(query: str, limit: int = 8) -> list[dict]:
    """Plain keyword search over topics, endpoints, limits, errors and update types."""
    words = [w for w in query.lower().replace("/", " / ").split() if len(w) > 1]
    if not words:
        return []
    hits: list[tuple[int, dict]] = []

    def score(text: str) -> int:
        t = text.lower()
        return sum(t.count(w) for w in words)

    for key, t in TOPICS.items():
        s = score(key + " " + t["title"] + " " + t["text"]) + (5 if key in words else 0)
        if s:
            hits.append((s, {"kind": "topic", "topic": key, "title": t["title"], "text": t["text"], "source": t["source"]}))
    for ep in ENDPOINTS:
        s = score(f'{ep["verb"]} {ep["path"]} {ep["group"]} {ep["summary"]} {ep.get("body") or ""}')
        if s:
            hits.append((s, {"kind": "endpoint", "verb": ep["verb"], "path": ep["path"], "summary": ep["summary"], "source": method_url(ep["verb"], ep["path"])}))
    for lim in LIMITS:
        s = score(lim["what"] + " " + lim["value"])
        if s:
            hits.append((s, {"kind": "limit", **lim}))
    for err in ERRORS:
        s = score(err["code"] + " " + err["meaning"])
        if s:
            hits.append((s, {"kind": "error", **err}))
    for name, u in UPDATE_TYPES.items():
        s = score(name + " " + u["fields"] + " " + u["note"])
        if s:
            hits.append((s, {"kind": "update_type", "update_type": name, **u, "source": f"{DOCS}/objects/Update"}))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:limit]]
