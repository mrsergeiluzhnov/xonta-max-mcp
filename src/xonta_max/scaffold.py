"""Bot project templates for MAX: Python (httpx), TypeScript (@maxhub/max-bot-api), Go (official client)."""

from __future__ import annotations

CERT_URL = "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"

ENV_EXAMPLE = """# Токен: business.max.ru → Чат-боты → бот → ⋮ → Настройки
MAX_BOT_TOKEN=
# Только для режима webhook: публичный https-адрес на порту 443 (порт не указывать)
WEBHOOK_URL=https://bot.example.ru/max/webhook
# TypeScript-шаблон: только домен, путь SDK выберет сам
WEBHOOK_DOMAIN=bot.example.ru
# 5-256 символов: A-Z a-z 0-9 _ -
WEBHOOK_SECRET=
# Путь к корневому сертификату Минцифры (скачивается в Dockerfile)
MAX_CA_FILE=/usr/local/share/ca-certificates/russian_trusted_root_ca.crt
"""

GITIGNORE = ".env\n__pycache__/\n.venv/\nnode_modules/\ndist/\nchats.json\n"

DOCKER_CERT = f"""RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \\
 && curl -fsSL {CERT_URL} -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \\
 && update-ca-certificates && rm -rf /var/lib/apt/lists/*"""

# ---------------------------------------------------------------- python

PY_BOT = r'''"""MAX bot: long polling for development, webhook for production.

python bot.py            # polling
python bot.py webhook    # webhook server on :8080 behind an HTTPS proxy on 443
"""

import asyncio
import hmac
import json
import os
import sys
import time
from pathlib import Path

import httpx

API = "https://platform-api2.max.ru"
TOKEN = os.environ["MAX_BOT_TOKEN"]
CA_FILE = os.environ.get("MAX_CA_FILE")  # корневой сертификат Минцифры; не отключайте проверку TLS
CHATS_FILE = Path(os.environ.get("CHATS_FILE", "chats.json"))
TEXT_LIMIT = 4000


class Max:
    """Thin Bot API client: token header, 30 rps cap, 2 msg/s per chat, retry on 429 and attachment.not.ready."""

    def __init__(self) -> None:
        self.http = httpx.AsyncClient(base_url=API, headers={"Authorization": TOKEN}, timeout=40, verify=CA_FILE or True)
        self._global = asyncio.Semaphore(25)
        self._last_send: dict[int, float] = {}

    async def call(self, method: str, path: str, *, params=None, json_body=None):
        for attempt in range(6):
            async with self._global:
                r = await self.http.request(method, path, params=params, json=json_body)
            if r.status_code == 429:
                await asyncio.sleep(1 + attempt)
                continue
            if r.status_code == 400 and "attachment.not.ready" in r.text:
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            r.raise_for_status()
            return r.json() if r.content else {}
        r.raise_for_status()

    async def send(self, chat_id: int, text: str, *, buttons=None, fmt: str | None = "markdown"):
        parts = split(text)
        for i, part in enumerate(parts):
            wait = 0.5 - (time.monotonic() - self._last_send.get(chat_id, 0))
            if wait > 0:
                await asyncio.sleep(wait)  # не больше 2 сообщений в секунду в один чат
            body = {"text": part}
            if fmt:
                body["format"] = fmt
            if buttons and i == len(parts) - 1:
                body["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]
            await self.call("POST", "/messages", params={"chat_id": chat_id}, json_body=body)
            self._last_send[chat_id] = time.monotonic()

    async def answer(self, callback_id: str, notification: str | None = None, message: dict | None = None):
        body = {k: v for k, v in {"notification": notification, "message": message}.items() if v}
        await self.call("POST", "/answers", params={"callback_id": callback_id}, json_body=body)


def split(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    out = []
    while len(text) > limit:
        cut = max(text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
        cut = cut if cut > limit // 3 else limit
        out.append(text[:cut])
        text = text[cut:].lstrip()
    return out + [text] if text else out


def load_chats() -> set[int]:
    try:
        return set(json.loads(CHATS_FILE.read_text()))
    except (OSError, ValueError):
        return set()


def save_chats(chats: set[int]) -> None:
    CHATS_FILE.write_text(json.dumps(sorted(chats)))


bot = Max()
chats = load_chats()  # GET /chats удалён — список чатов ведём сами


async def handle(update: dict) -> None:
    kind = update.get("update_type")
    try:
        if kind == "bot_started":
            chats.add(update["chat_id"]); save_chats(chats)
            await bot.send(update["chat_id"], "**Привет!** Я бот на MAX.", buttons=[[{"type": "callback", "text": "Что умеешь?", "payload": "help"}]])
        elif kind == "bot_added":
            chats.add(update["chat_id"]); save_chats(chats)
        elif kind == "bot_removed":
            chats.discard(update["chat_id"]); save_chats(chats)
        elif kind == "message_created":
            msg = update["message"]
            chat_id = msg["recipient"]["chat_id"]
            text = (msg["body"].get("text") or "").strip()
            if text == "/help":
                await bot.send(chat_id, "Команды: /help")
            elif text:
                await bot.send(chat_id, text, fmt=None)  # эхо без разметки: пользовательский текст не парсим
        elif kind == "message_callback":
            cb = update["callback"]
            if cb.get("payload") == "help":
                await bot.answer(cb["callback_id"], notification="Отвечаю на сообщения и кнопки")
            else:
                await bot.answer(cb["callback_id"], notification="Готово")
    except Exception as e:  # одно плохое обновление не должно ронять бота
        print("update failed:", kind, repr(e), file=sys.stderr)


async def polling() -> None:
    marker = None
    print("polling… (только для разработки)")
    while True:
        params = {"timeout": 30, "limit": 100}
        if marker is not None:
            params["marker"] = marker
        try:
            data = await bot.call("GET", "/updates", params=params)
        except httpx.HTTPError as e:
            print("poll error:", e, file=sys.stderr)
            await asyncio.sleep(3)
            continue
        marker = data.get("marker", marker)
        for u in data.get("updates", []):
            asyncio.create_task(handle(u))
        await asyncio.sleep(0.3)


def webhook_app():
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Route

    secret = os.environ["WEBHOOK_SECRET"]

    async def receive(request: Request) -> Response:
        got = request.headers.get("x-max-bot-api-secret", "")
        if not hmac.compare_digest(got, secret):
            return Response(status_code=401)
        update = await request.json()
        asyncio.create_task(handle(update))  # отвечаем 200 сразу, MAX ждёт не больше 30 с
        return Response(status_code=200)

    async def startup() -> None:
        await bot.call("POST", "/subscriptions", json_body={
            "url": os.environ["WEBHOOK_URL"], "secret": secret,
            "update_types": ["message_created", "message_callback", "bot_started", "bot_added", "bot_removed"],
        })
        print("webhook subscribed:", os.environ["WEBHOOK_URL"])

    return Starlette(routes=[Route("/max/webhook", receive, methods=["POST"])], on_startup=[startup])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "webhook":
        import uvicorn
        uvicorn.run(webhook_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
    else:
        asyncio.run(polling())
'''

PY_REQ = "httpx>=0.27\nstarlette>=0.37\nuvicorn>=0.30\n"

PY_DOCKER = f"""FROM python:3.12-slim
{DOCKER_CERT}
ENV MAX_CA_FILE=/etc/ssl/certs/ca-certificates.crt
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py", "webhook"]
"""

# ---------------------------------------------------------------- typescript

TS_BOT = r"""import { Bot, Keyboard } from '@maxhub/max-bot-api';
import { readFileSync, writeFileSync } from 'node:fs';

// Запуск: NODE_EXTRA_CA_CERTS=/путь/russian_trusted_root_ca.crt node --env-file=.env dist/bot.js
const token = process.env.MAX_BOT_TOKEN;
if (!token) throw new Error('MAX_BOT_TOKEN is empty');

const bot = new Bot(token);

// GET /chats удалён: храним чаты сами
const CHATS = 'chats.json';
const chats = new Set<number>((() => { try { return JSON.parse(readFileSync(CHATS, 'utf8')); } catch { return []; } })());
const saveChats = () => writeFileSync(CHATS, JSON.stringify([...chats]));

bot.api.setMyCommands([{ name: 'help', description: 'Что умеет бот' }]);

bot.on('bot_started', (ctx) => {
  if (ctx.chatId != null) { chats.add(ctx.chatId); saveChats(); }
  return ctx.reply('**Привет!** Я бот на MAX.', {
    format: 'markdown',
    attachments: [Keyboard.inlineKeyboard([[Keyboard.button.callback('Что умеешь?', 'help')]])],
  });
});
bot.on('bot_added', (ctx) => { if (ctx.chatId != null) { chats.add(ctx.chatId); saveChats(); } });
bot.on('bot_removed', (ctx) => { if (ctx.chatId != null) { chats.delete(ctx.chatId); saveChats(); } });

bot.command('help', (ctx) => ctx.reply('Команды: /help'));

bot.action('help', (ctx) => ctx.answerOnCallback({ message: { text: 'Отвечаю на сообщения и кнопки' } }));

bot.on('message_created', (ctx) => {
  if (ctx.chatId == null) return undefined;
  return ctx.reply(ctx.message?.body?.text ?? '');
});

bot.catch((err) => console.error('update failed:', err)); // одно плохое обновление не роняет бота

if (process.env.MODE === 'webhook') {
  // HTTPS на 443 обеспечивает прокси (nginx), бот слушает 3000
  bot.start({
    mode: 'webhook',
    options: {
      domain: process.env.WEBHOOK_DOMAIN!,
      port: 3000,
      secret: process.env.WEBHOOK_SECRET!,
      allowedUpdates: ['message_created', 'message_callback', 'bot_started', 'bot_added', 'bot_removed'],
    },
  });
} else {
  bot.start(); // long polling — только для разработки
}
"""

TS_PACKAGE = """{
  "name": "max-bot",
  "private": true,
  "type": "module",
  "engines": { "node": ">=20.19" },
  "scripts": {
    "build": "tsc",
    "dev": "tsc && NODE_EXTRA_CA_CERTS=$MAX_CA_FILE node --env-file=.env dist/bot.js",
    "start": "node dist/bot.js"
  },
  "dependencies": { "@maxhub/max-bot-api": "^0.3.1" },
  "devDependencies": { "typescript": "^5.6.0", "@types/node": "^22.0.0" }
}
"""

TS_CONFIG = """{
  "compilerOptions": {
    "target": "ES2022", "module": "NodeNext", "moduleResolution": "NodeNext",
    "outDir": "dist", "strict": true, "skipLibCheck": true
  },
  "include": ["bot.ts"]
}
"""

TS_DOCKER = f"""FROM node:22-slim
{DOCKER_CERT}
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/russian_trusted_root_ca.crt MODE=webhook
WORKDIR /app
COPY package.json tsconfig.json bot.ts ./
RUN npm install && npx tsc
CMD ["node", "dist/bot.js"]
"""

# ---------------------------------------------------------------- go

GO_BOT = r"""package main

import (
	"context"
	"crypto/subtle"
	"crypto/tls"
	"crypto/x509"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"

	maxbot "github.com/max-messenger/max-bot-api-client-go/v2"
	"github.com/max-messenger/max-bot-api-client-go/v2/model"
)

// httpClient trusts the system store plus the Минцифры root from MAX_CA_FILE.
func httpClient() *http.Client {
	pool, err := x509.SystemCertPool()
	if err != nil {
		pool = x509.NewCertPool()
	}
	if path := os.Getenv("MAX_CA_FILE"); path != "" {
		pem, err := os.ReadFile(path)
		if err != nil || !pool.AppendCertsFromPEM(pem) {
			log.Fatalf("cannot load MAX_CA_FILE %q", path)
		}
	}
	return &http.Client{Timeout: 60 * time.Second, Transport: &http.Transport{TLSClientConfig: &tls.Config{RootCAs: pool}}}
}

func handle(ctx context.Context, api *maxbot.Api, u model.Update) {
	switch u.UpdateType {
	case model.UpdateBotStarted:
		kb := model.NewKeyboard()
		kb.AddRow().AddCallBack("Что умеешь?", "help")
		msg := maxbot.NewMessage().SetChat(u.ChatID).SetFormat(model.FormatMarkdown).
			SetText("**Привет!** Я бот на MAX.").AddKeyboard(kb)
		if _, err := api.Messages.Send(ctx, msg); err != nil {
			log.Printf("send: %v", err)
		}
	case model.UpdateMessageCreated:
		text := u.GetMessage().Body.Text
		if text == "" {
			return
		}
		if _, err := api.Messages.Send(ctx, maxbot.NewMessage().SetChat(u.ChatID).SetText(text)); err != nil {
			log.Printf("send: %v", err)
		}
	case model.UpdateMessageCallback:
		cb := u.GetCallback()
		note := "Готово"
		if cb.Payload == "help" {
			note = "Отвечаю на сообщения и кнопки"
		}
		if _, err := api.Messages.AnswerOnCallback(ctx, cb.CallbackID, model.CallbackAnswer{Notification: &note}); err != nil {
			log.Printf("answer: %v", err)
		}
	}
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	api, err := maxbot.NewApi(os.Getenv("MAX_BOT_TOKEN"), maxbot.WithHTTPClient(httpClient()))
	if err != nil {
		log.Fatalf("init: %v", err)
	}

	if os.Getenv("MODE") == "webhook" {
		secret := os.Getenv("WEBHOOK_SECRET")
		types := []string{"message_created", "message_callback", "bot_started"}
		if _, err := api.Subscriptions.Subscribe(ctx, os.Getenv("WEBHOOK_URL"), secret, types, "1"); err != nil {
			log.Fatalf("subscribe: %v", err)
		}
		inner := api.GetHandler(func(c context.Context, u model.Update) { go handle(context.Background(), api, u) }, secret)
		http.HandleFunc("/max/webhook", func(w http.ResponseWriter, r *http.Request) {
			// GetHandler compares the secret with plain !=, so check it in constant time first
			if subtle.ConstantTimeCompare([]byte(r.Header.Get("X-Max-Bot-Api-Secret")), []byte(secret)) != 1 {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}
			inner(w, r)
		})
		log.Fatal(http.ListenAndServe(":8080", nil)) // HTTPS 443 на прокси перед ботом
	}

	log.Println("polling… (только для разработки)")
	var marker int64
	for ctx.Err() == nil {
		updates, next, err := api.Subscriptions.GetUpdates(ctx, marker)
		if err != nil {
			log.Printf("get updates: %v", err)
			select {
			case <-ctx.Done():
				return
			case <-time.After(time.Second):
			}
			continue
		}
		marker = next
		for _, u := range updates {
			handle(ctx, api, u)
		}
	}
}
"""

GO_MOD = """module maxbot-example

go 1.24

require github.com/max-messenger/max-bot-api-client-go/v2 v2.4.0
"""

GO_DOCKER = f"""FROM golang:1.24 AS build
WORKDIR /src
COPY go.mod main.go ./
RUN go mod tidy && CGO_ENABLED=0 go build -o /bot .

FROM debian:12-slim
{DOCKER_CERT}
COPY --from=build /bot /bot
ENV MODE=webhook
CMD ["/bot"]
"""

README = """# Бот для MAX

Сгенерировано Xonta MAX MCP. Перед запуском:

1. Создайте бота на business.max.ru (нужен профиль организации, ИП или самозанятого) и возьмите токен.
2. Скачайте корневой сертификат Минцифры: {cert}
   и укажите путь в MAX_CA_FILE. Не отключайте проверку TLS.
3. Скопируйте `.env.example` в `.env` и заполните.

Разработка — long polling, продакшн — вебхук: HTTPS на 443 с доверенным сертификатом,
бот за прокси слушает внутренний порт, путь `/max/webhook`.

{run}

Что уже учтено: адрес platform-api2.max.ru, токен в заголовке, учёт чатов без GET /chats,
ответ на нажатия через POST /answers, секрет вебхука с проверкой за постоянное время.
"""

RUN = {
    "python": "```bash\npip install -r requirements.txt\nset -a; . ./.env; set +a\npython bot.py           # polling\npython bot.py webhook   # вебхук\n```",
    "typescript": "```bash\nnpm install\nnpm run dev                      # polling\nMODE=webhook npm start           # вебхук\n```",
    "go": "```bash\ngo mod tidy\nset -a; . ./.env; set +a\ngo run .                 # polling\nMODE=webhook go run .    # вебхук\n```",
}


def scaffold(language: str) -> dict[str, str]:
    lang = language.lower()
    if lang in ("py", "python"):
        files = {"bot.py": PY_BOT, "requirements.txt": PY_REQ, "Dockerfile": PY_DOCKER}
        lang = "python"
    elif lang in ("ts", "typescript", "node", "js", "javascript"):
        files = {"bot.ts": TS_BOT, "package.json": TS_PACKAGE, "tsconfig.json": TS_CONFIG, "Dockerfile": TS_DOCKER}
        lang = "typescript"
    elif lang in ("go", "golang"):
        files = {"main.go": GO_BOT, "go.mod": GO_MOD, "Dockerfile": GO_DOCKER}
        lang = "go"
    else:
        raise ValueError("language: python | typescript | go")
    files[".env.example"] = ENV_EXAMPLE
    files[".gitignore"] = GITIGNORE
    files["README.md"] = README.format(cert=CERT_URL, run=RUN[lang])
    return files
