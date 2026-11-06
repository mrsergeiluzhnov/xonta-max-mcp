# Publishing Xonta MAX

[Русская версия ниже](#публикация-xonta-max)

Registry name: **`ru.xonta/max`**
Public endpoint: **`https://mcp.xonta.ru/max/mcp`**
PyPI package: **`xonta-max-mcp`**
Repository: **`github.com/mrsergeiluzhnov/xonta-max-mcp`**

Same order as Xonta Customs RU: GitHub → PyPI → official registry → VPS → catalogs.
The registry key is the same one: the xonta.ru domain is already verified, no need to publish the auth file again.

## 1. GitHub, PyPI, registry

The archive already has a git repository with the first commit. From the unpacked folder:

```bash
cd xonta-max-mcp
bash scripts/publish.sh
```

The script creates the public repository, uploads the package to PyPI (asks for the token) and publishes
`server.json` to the official registry. Log in to the registry once before that, with the same key as for customs:

```bash
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')"
mcp-publisher login http --domain xonta.ru --private-key "${PRIVATE_KEY}"
```

## 2. VPS (next to customs, port 8766)

```bash
curl -O https://raw.githubusercontent.com/mrsergeiluzhnov/xonta-max-mcp/main/scripts/deploy_vps.sh
sudo bash deploy_vps.sh
```

The script installs the package into `/opt/xonta-max`, creates the `xmax` user and the `xonta-max` service
with `XONTA_MAX_HOSTED=1`, so tools that take a bot token are off on the shared server.
No token is needed on the VPS, don't put one there.

Then add the block from `deploy/nginx-mcp.xonta.ru.conf` to the mcp.xonta.ru server block, next to `/customs/`:

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -s https://mcp.xonta.ru/max/health
curl -s -X POST https://mcp.xonta.ru/max/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 300
```

Answers are in Russian by default. Agents pass `lang: "en"` themselves when the user writes in English.
To make English the default on a server, add `Environment=XONTA_MAX_LANG=en` to the service.

## 3. Catalogs

Same as steps 5–8 in the customs PUBLISHING.md: Glama (Add Server → Claim), Smithery (by public URL),
PulseMCP, mcp.so, MCP Market, LobeHub, mcpservers.org, Cline, Docker MCP Catalog.

Line for `punkpeye/awesome-mcp-servers`, section **💬 Communication**, in alphabetical order:

```markdown
- [mrsergeiluzhnov/xonta-max-mcp](https://github.com/mrsergeiluzhnov/xonta-max-mcp) [![mrsergeiluzhnov/xonta-max-mcp MCP server](https://glama.ai/mcp/servers/mrsergeiluzhnov/xonta-max-mcp/badges/score.svg)](https://glama.ai/mcp/servers/mrsergeiluzhnov/xonta-max-mcp) 🐍 ☁️ 🏠 🍎 🪟 🐧 - Build bots and mini-apps for the MAX messenger (max.ru), in English or Russian: current Bot API facts, linting for outdated API usage, Telegram → MAX migration, bot scaffolding, deep links and a share-to-MAX button, signed initData and a MAX Bridge emulator for tests. Hosted `https://mcp.xonta.ru/max/mcp` or `uvx xonta-max-mcp`.
```

## 4. Audience

- Russian-speaking: a post in Xonta Live and a card in AgentRadar; a Habr article with a live example
  (aiogram bot → `max_migrate_from_telegram` → `max_scaffold_bot` → `max_lint_code` with no errors);
  vc.ru and bot developer chats, where moving off Telegram is the hot topic; MAX bot agencies and builders.
- International: the official dev.max.ru docs are Russian only, so English answers are a real advantage.
  Post on dev.to or Medium ("Building bots for MAX, Russia's new national messenger, with an AI agent"),
  r/mcp and the MCP Discord, and the catalogs above, which are mostly read in English.

## On every update

Bump the version in `pyproject.toml`, `src/xonta_max/__init__.py` and `server.json` (two places).
Update `VERIFIED_ON` and the facts in `src/xonta_max/knowledge.py` from https://dev.max.ru/docs-api/changelog-api,
in both languages: every Russian field needs its `_en` pair, and `tests/test_i18n.py` fails if one is missing
or if any English answer still contains Russian. Run `pytest`, then `scripts/publish.sh`. On the VPS: `sudo bash deploy_vps.sh`.

---

# Публикация Xonta MAX

Имя в реестрах: **`ru.xonta/max`**
Публичный адрес: **`https://mcp.xonta.ru/max/mcp`**
Пакет PyPI: **`xonta-max-mcp`**
Репозиторий: **`github.com/mrsergeiluzhnov/xonta-max-mcp`**

Порядок тот же, что у Xonta Customs RU: GitHub → PyPI → официальный реестр → VPS → каталоги.
Ключ для реестра тот же: домен xonta.ru уже подтверждён, повторно размещать файл не нужно.

## 1. GitHub, PyPI, реестр

В архиве уже есть git-репозиторий с первым коммитом. Из распакованной папки:

```bash
cd xonta-max-mcp
bash scripts/publish.sh
```

Скрипт создаст публичный репозиторий, выложит пакет на PyPI (спросит токен) и опубликует
`server.json` в официальном реестре. Перед этим один раз войдите в реестр тем же ключом, что и для customs:

```bash
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')"
mcp-publisher login http --domain xonta.ru --private-key "${PRIVATE_KEY}"
```

## 2. VPS (рядом с customs, порт 8766)

```bash
curl -O https://raw.githubusercontent.com/mrsergeiluzhnov/xonta-max-mcp/main/scripts/deploy_vps.sh
sudo bash deploy_vps.sh
```

Скрипт ставит пакет в `/opt/xonta-max`, создаёт пользователя `xmax` и сервис `xonta-max`
с `XONTA_MAX_HOSTED=1` — на общем сервере выключены инструменты, которые принимают токен бота.
Токен на VPS не нужен и класть его туда не надо.

Потом добавьте блок из `deploy/nginx-mcp.xonta.ru.conf` в server для mcp.xonta.ru рядом с `/customs/`:

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -s https://mcp.xonta.ru/max/health
curl -s -X POST https://mcp.xonta.ru/max/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 300
```

По умолчанию ответы на русском. Агенты сами передают `lang: "en"`, когда пользователь пишет по-английски.
Чтобы сделать английский языком по умолчанию на сервере, добавьте в сервис `Environment=XONTA_MAX_LANG=en`.

## 3. Каталоги

Те же шаги 5–8 из PUBLISHING.md у customs: Glama (Add Server → Claim), Smithery (по публичному URL),
PulseMCP, mcp.so, MCP Market, LobeHub, mcpservers.org, Cline, Docker MCP Catalog.

Строка для `punkpeye/awesome-mcp-servers`, раздел **💬 Communication**, по алфавиту — в английской части выше.
Каталоги англоязычные, поэтому строка на английском.

## 4. Аудитория

- Русскоязычная: пост в Xonta Live и карточка в AgentRadar; статья на Хабре с живым примером
  (бот на aiogram → `max_migrate_from_telegram` → `max_scaffold_bot` → `max_lint_code` без ошибок);
  vc.ru и чаты разработчиков ботов, где перенос с Telegram сейчас главная тема; агентства и конструкторы ботов под MAX.
- Зарубежная: официальная документация dev.max.ru есть только на русском, поэтому ответы на английском — реальное преимущество.
  Пост на dev.to или Medium («Building bots for MAX, Russia's new national messenger, with an AI agent»),
  r/mcp и Discord-сообщество MCP, плюс каталоги выше — их в основном читают по-английски.

## При каждом обновлении

Поднимите версию в `pyproject.toml`, `src/xonta_max/__init__.py` и `server.json` (в двух местах).
Обновите `VERIFIED_ON` и факты в `src/xonta_max/knowledge.py` по журналу https://dev.max.ru/docs-api/changelog-api —
на обоих языках: у каждого русского поля должна быть пара `_en`, а `tests/test_i18n.py` упадёт, если её нет
или если в английском ответе остался русский текст. Прогоните `pytest`, затем `scripts/publish.sh`. На VPS: `sudo bash deploy_vps.sh`.
