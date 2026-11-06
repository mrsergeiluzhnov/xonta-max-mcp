# Как запустить Xonta MAX и добавить в каталоги

Имя в реестрах: **`ru.xonta/max`**
Публичный адрес: **`https://mcp.xonta.ru/max/mcp`**
Пакет PyPI: **`xonta-max-mcp`**
Репозиторий: **`github.com/mrsergeiluzhnov/xonta-max-mcp`**

Порядок тот же, что у Xonta Customs RU: GitHub → PyPI → официальный реестр → VPS → каталоги.
Ключ для реестра тот же: домен xonta.ru уже подтверждён, повторно размещать файл не нужно.

## 1. GitHub, PyPI, реестр

```bash
cd xonta-max-mcp
git init -b main
git add .
git commit -m "MCP server for MAX messenger bots and mini-apps"
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

## 3. Каталоги

Те же шаги 5–8 из PUBLISHING.md у customs: Glama (Add Server → Claim), Smithery (по публичному URL),
PulseMCP, mcp.so, MCP Market, LobeHub, mcpservers.org, Cline, Docker MCP Catalog.

Строка для `punkpeye/awesome-mcp-servers`, раздел **💬 Communication**, по алфавиту:

```markdown
- [mrsergeiluzhnov/xonta-max-mcp](https://github.com/mrsergeiluzhnov/xonta-max-mcp) [![mrsergeiluzhnov/xonta-max-mcp MCP server](https://glama.ai/mcp/servers/mrsergeiluzhnov/xonta-max-mcp/badges/score.svg)](https://glama.ai/mcp/servers/mrsergeiluzhnov/xonta-max-mcp) 🐍 ☁️ 🏠 🍎 🪟 🐧 - Build bots and mini-apps for the MAX messenger (max.ru): current Bot API facts, linting for outdated API usage, Telegram → MAX migration, bot scaffolding, deep links and a share-to-MAX button, signed initData and a MAX Bridge emulator for tests. Hosted `https://mcp.xonta.ru/max/mcp` or `uvx xonta-max-mcp`.
```

## 4. Русскоязычная аудитория — здесь главный трафик

- Пост в Xonta Live и карточка в AgentRadar.
- Хабр: «MCP-сервер для MAX: нейросеть перестанет писать ботов под старый API». Показать живой пример:
  бот на aiogram → `max_migrate_from_telegram` → `max_scaffold_bot` → `max_lint_code` без ошибок.
- vc.ru и чаты разработчиков ботов: перенос с Telegram сейчас самая горячая тема.
- Агентства и конструкторы ботов под MAX (Bothelp, Chatforma и т.п.) — им полезна проверка кода и кнопка «Отправить в MAX».

## При обновлении

Поднимите версию в `pyproject.toml`, `src/xonta_max/__init__.py` и `server.json` (в двух местах),
обновите `VERIFIED_ON` и факты в `src/xonta_max/knowledge.py` по журналу https://dev.max.ru/docs-api/changelog-api,
прогоните `pytest` и запустите `scripts/publish.sh`. На VPS: `sudo bash deploy_vps.sh`.
