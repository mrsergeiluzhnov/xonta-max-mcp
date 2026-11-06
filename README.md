# Xonta MAX

MCP server for building bots and mini-apps for the MAX messenger (max.ru).
Free and open source.

<!-- mcp-name: ru.xonta/max -->

[Русская версия ниже](#xonta-max--по-русски)

## Why

MAX changed a lot in 2026: the API moved to `platform-api2.max.ru` behind the Минцифры root certificate,
`GET /chats` was removed, adding members was restricted, webhooks became HTTPS-only, comments arrived.
Language models still write the old API. This server gives an AI agent current facts and tools that
check, generate and test MAX code, so the result works on the first try.

You don't need your own bot for most of it. Only the operator tools need a token.

## Tools

| Tool | What it does |
|---|---|
| `max_api_reference` | Current Bot API and Mini Apps facts by topic or free-text search, each with a dev.max.ru link |
| `max_endpoint_info` | One method: query, body, limits, gotchas, curl. Says when a method was removed |
| `max_limits` | Every limit in one place: text, rate, keyboard, attachments, files, deep links, webhook |
| `max_changelog` | Dated 2026 changes that break old code |
| `max_lint_code` | Finds old host, token in query, `Bearer`, disabled TLS, removed methods, webhook mistakes, unsafe secret compare, wrong initData HMAC, Telegram leftovers. Line numbers and fixes |
| `max_migrate_from_telegram` | Maps every Telegram API call in your code to MAX, lists what has no equivalent, gives a plan |
| `max_scaffold_bot` | Ready bot in Python, TypeScript or Go: polling + webhook, certificate in Dockerfile, chat tracking, callbacks |
| `max_build_message` | Message JSON with keyboard and images, validated, plus curl |
| `max_validate_message` | Checks a body: 4000 chars, 210/30/7 keyboard, 3 per row for link/open_app, attachment combinations |
| `max_split_text` | Splits long text into ≤4000-char messages at paragraph boundaries |
| `max_convert_formatting` | Telegram MarkdownV2/HTML or LLM Markdown → MAX markup, reports what MAX can't show |
| `max_deeplink` | `?start=`, `?startapp=`, mention, and a **"Send to MAX" share link and button for any website, no bot needed** |
| `max_mock_update` | Realistic webhook updates for all 19 types, plus curl to your local endpoint |
| `max_mock_init_data` | Correctly signed mini-app initData for backend tests |
| `max_bridge_mock` | `window.WebApp` emulator to build mini-apps in a normal browser on localhost |
| `max_check_webhook_secret` | Checks or generates a webhook secret |
| `max_verify_signature` | Local only. Verifies initData, requestContact phone hash, request_contact vcf hash |
| `max_bot_info`, `max_send_message`, `max_get_messages`, `max_get_chat`, `max_set_commands`, `max_webhook`, `max_get_updates`, `max_api_request` | Local only, with `MAX_BOT_TOKEN`. Act as your bot. Bodies are validated before sending, removed methods are refused |

## Connect

### Hosted (no install)

```
https://mcp.xonta.ru/max/mcp
```

```json
{
  "mcpServers": {
    "xonta-max": { "url": "https://mcp.xonta.ru/max/mcp" }
  }
}
```

The hosted server never accepts bot tokens: tools that need one are switched off there.

### Local (stdio), with operator tools

```json
{
  "mcpServers": {
    "xonta-max": {
      "command": "uvx",
      "args": ["xonta-max-mcp"],
      "env": {
        "MAX_BOT_TOKEN": "your token",
        "MAX_CA_FILE": "/path/to/russian_trusted_root_ca.pem"
      }
    }
  }
}
```

Get the certificate at https://www.gosuslugi.ru/crt. Without `MAX_BOT_TOKEN` the server runs fine,
just without the operator tools.

## Try it

- "Check this bot for MAX problems" + paste code
- "Port my aiogram bot to MAX, what breaks?"
- "Make a MAX bot in TypeScript with a webhook"
- "Add a 'Send to MAX' button to my site's article pages"
- "Give me a signed initData and a test for my FastAPI validator"

## Sources

Facts are checked against dev.max.ru, the official OpenAPI schema
(github.com/max-messenger/api-schema) and the official Go and TypeScript clients.
The official MAX agent skill (github.com/max-messenger/max-agents-skill, Apache-2.0) was used as a cross-check.
Every answer says the date it is current for. If dev.max.ru says otherwise, dev.max.ru wins:
open an issue and I'll update.

Creating a bot on MAX requires a verified profile on business.max.ru (organisation, sole proprietor,
or since June 2026 self-employed). This server doesn't change that, it helps whoever builds the bot.

## License

MIT

---

# Xonta MAX — по-русски

MCP-сервер для разработки ботов и мини-приложений для мессенджера MAX (max.ru).
Бесплатный, с открытым кодом.

## Зачем

В 2026 году MAX сильно поменялся: API переехал на `platform-api2.max.ru` с сертификатом Минцифры,
`GET /chats` удалили, добавление участников ограничили, вебхуки теперь только по HTTPS, появились комментарии.
Нейросети до сих пор пишут под старый API. Сервер даёт ИИ-агенту свежие факты и инструменты, которые
проверяют, генерируют и тестируют код под MAX, чтобы всё заработало с первого раза.

Для большинства инструментов свой бот не нужен. Токен нужен только инструментам управления ботом.

## Инструменты

| Инструмент | Что делает |
|---|---|
| `max_api_reference` | Актуальные факты по Bot API и мини-приложениям по теме или поиску, со ссылкой на dev.max.ru |
| `max_endpoint_info` | Один метод: параметры, тело, лимиты, подводные камни, curl. Сообщает, если метод удалён |
| `max_limits` | Все лимиты в одном месте: текст, частота запросов, кнопки, вложения, файлы, диплинки, вебхук |
| `max_changelog` | Изменения 2026 года с датами, которые ломают старый код |
| `max_lint_code` | Находит старый хост, токен в адресе, `Bearer`, отключённый TLS, удалённые методы, ошибки вебхука, небезопасное сравнение секрета, неверный HMAC для initData, остатки Telegram. С номерами строк и исправлениями |
| `max_migrate_from_telegram` | Сопоставляет каждый вызов Telegram API в коде с MAX, перечисляет, чему нет аналога, даёт план |
| `max_scaffold_bot` | Готовый бот на Python, TypeScript или Go: polling и вебхук, сертификат в Dockerfile, учёт чатов, кнопки |
| `max_build_message` | JSON сообщения с кнопками и картинками, с проверкой и командой curl |
| `max_validate_message` | Проверяет тело: 4000 символов, клавиатура 210/30/7, по 3 в ряду для link/open_app, сочетания вложений |
| `max_split_text` | Режет длинный текст на сообщения до 4000 символов по абзацам |
| `max_convert_formatting` | Telegram MarkdownV2/HTML или Markdown от нейросети → разметка MAX, сообщает, что MAX не покажет |
| `max_deeplink` | `?start=`, `?startapp=`, упоминания и **ссылка и кнопка «Отправить в MAX» для любого сайта, без бота** |
| `max_mock_update` | Правдоподобные события вебхука всех 19 типов и curl для отправки на ваш локальный адрес |
| `max_mock_init_data` | Правильно подписанные initData для тестов бэкенда |
| `max_bridge_mock` | Эмулятор `window.WebApp`, чтобы делать мини-приложение в обычном браузере на localhost |
| `max_check_webhook_secret` | Проверяет или генерирует секрет вебхука |
| `max_verify_signature` | Только локально. Проверяет initData, хеш телефона из requestContact, хеш контакта от кнопки request_contact |
| `max_bot_info`, `max_send_message`, `max_get_messages`, `max_get_chat`, `max_set_commands`, `max_webhook`, `max_get_updates`, `max_api_request` | Только локально, с `MAX_BOT_TOKEN`. Работают от имени вашего бота. Тело проверяется до отправки, удалённые методы не вызываются |

## Подключение

### Готовый сервер (без установки)

```
https://mcp.xonta.ru/max/mcp
```

```json
{
  "mcpServers": {
    "xonta-max": { "url": "https://mcp.xonta.ru/max/mcp" }
  }
}
```

Общий сервер не принимает токены ботов: инструменты, которым нужен токен, там выключены.

### Локально (stdio), с управлением ботом

```json
{
  "mcpServers": {
    "xonta-max": {
      "command": "uvx",
      "args": ["xonta-max-mcp"],
      "env": {
        "MAX_BOT_TOKEN": "ваш токен",
        "MAX_CA_FILE": "/путь/russian_trusted_root_ca.pem"
      }
    }
  }
}
```

Сертификат — на https://www.gosuslugi.ru/crt. Без `MAX_BOT_TOKEN` сервер работает,
просто без инструментов управления ботом.

## Что спросить

- «Проверь этого бота на проблемы с MAX» + код
- «Перенеси моего бота на aiogram в MAX, что сломается?»
- «Сделай бота для MAX на TypeScript с вебхуком»
- «Добавь кнопку „Отправить в MAX“ на страницы статей моего сайта»
- «Дай подписанные initData и тест для моего валидатора на FastAPI»

## Источники

Факты сверены с dev.max.ru, официальной OpenAPI-схемой (github.com/max-messenger/api-schema)
и официальными клиентами на Go и TypeScript. Для перекрёстной проверки использован официальный
навык MAX для агентов (github.com/max-messenger/max-agents-skill, Apache-2.0).
В каждом ответе указана дата актуальности. Если на dev.max.ru написано иначе, прав dev.max.ru:
заведите issue, обновлю.

Создать бота в MAX можно только с подтверждённым профилем на business.max.ru (организация, ИП,
с июня 2026 — самозанятый). Сервер этого не обходит, он помогает тому, кто делает бота.

## Лицензия

MIT
