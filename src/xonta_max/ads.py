"""Advertising in MAX: placement tracking links, ROI report, ad post marking check.

Pure calculations and text checks. Nothing here touches ad cabinets, budgets or third-party data.
"""

from __future__ import annotations

import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .i18n import tr

# ---------------------------------------------------------------- slugs

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slug(name: str, max_len: int = 32) -> str:
    s = "".join(_TRANSLIT.get(c, c) for c in name.lower().strip().lstrip("@"))
    s = re.sub(r"https?://(www\.)?max\.ru/", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return (s or "p")[:max_len].rstrip("_")


def _with_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in params]
    q += [(k, v) for k, v in params.items() if v]
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(q), parts.fragment))


# ---------------------------------------------------------------- tracking links

def tracking_links(campaign: str, placements: list[dict], bot_name: str | None = None, mini_app_bot: str | None = None,
                   site_url: str | None = None, utm_medium: str = "seeding", promo_codes: bool = True) -> dict:
    if not placements:
        raise ValueError(tr("Нужен хотя бы один канал в placements", "placements needs at least one channel"))
    if not (bot_name or mini_app_bot or site_url):
        raise ValueError(tr("Укажите куда вести: bot_name, mini_app_bot или site_url", "Say where links lead: bot_name, mini_app_bot or site_url"))
    if site_url and not site_url.startswith(("https://", "http://")):
        raise ValueError(tr("site_url должен начинаться с https://", "site_url must start with https://"))
    camp = slug(campaign, 24)
    used: set[str] = set()
    rows: list[dict] = []
    warnings: list[str] = []
    for i, p in enumerate(placements, 1):
        name = str(p.get("name") or p.get("channel") or f"p{i}")
        s = slug(name, 40)
        base, n = s, 2
        while s in used:
            s = f"{base[:37]}_{n}"
            n += 1
        used.add(s)
        pid = f"{camp}_{s}"
        row: dict = {"placement": name, "id": pid}
        if p.get("cost") is not None:
            row["cost"] = p["cost"]
        if bot_name:
            payload = pid[:128]
            row["bot_link"] = f"https://max.ru/{bot_name.lstrip('@')}?start={payload}"
            row["arrives_as"] = f"bot_started.payload = {payload}"
        if mini_app_bot:
            row["mini_app_link"] = f"https://max.ru/{mini_app_bot.lstrip('@')}?startapp={pid[:512]}"
        if site_url:
            row["site_link"] = _with_query(site_url, {
                "utm_source": "max", "utm_medium": utm_medium, "utm_campaign": camp, "utm_content": s,
                "erid": str(p.get("erid") or ""),
            })
            if not p.get("erid"):
                warnings.append(tr(f"{name}: нет erid — добавьте токен ОРД в ссылку или текст поста до публикации",
                                   f"{name}: no erid — add the ad-data operator token to the link or post text before publishing"))
        if promo_codes:
            row["promo_code"] = (re.sub(r"[^A-Z0-9]", "", s.upper())[:10] or f"P{i}") + str(10 + i)
        rows.append(row)
    csv_cols = ["placement", "id", "cost", "bot_link", "mini_app_link", "site_link", "promo_code"]
    present = [c for c in csv_cols if any(c in r for r in rows)]
    csv = ";".join(present) + "\n" + "\n".join(";".join(str(r.get(c, "")) for c in present) for r in rows)
    return {
        "campaign": camp, "placements": rows, "media_plan_csv": csv, "warnings": warnings,
        "how_to_count": [
            tr("Бот: в обработчике bot_started сохраняйте payload — он совпадает с id размещения. Шаблоны max_scaffold_bot уже пишут его в starts.jsonl.",
               "Bot: store the payload in your bot_started handler — it equals the placement id. max_scaffold_bot templates already write it to starts.jsonl."),
            tr("Сайт: смотрите utm_content в Метрике или CRM.", "Site: read utm_content in your analytics or CRM."),
            tr("Промокоды: считайте заказы с каждым кодом — так видно продажи, даже если человек купил не сразу.",
               "Promo codes: count orders per code — this catches sales even when people buy later."),
            tr("Потом передайте цифры в max_ad_report.", "Then pass the numbers to max_ad_report."),
        ],
    }


def count_starts(events: list, campaign: str | None = None) -> dict[str, int]:
    """Count bot_started payloads (raw updates, {'payload': ...} or plain strings) per placement id."""
    prefix = (slug(campaign, 24) + "_") if campaign else ""
    out: dict[str, int] = {}
    for e in events:
        if isinstance(e, dict):
            if e.get("update_type") not in (None, "bot_started"):
                continue
            payload = e.get("payload")
        else:
            payload = e
        if not payload or not isinstance(payload, str):
            continue
        if prefix and not payload.startswith(prefix):
            continue
        out[payload] = out.get(payload, 0) + 1
    return out


# ---------------------------------------------------------------- ROI report

def _num(x) -> float | None:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def wilson(successes: float, trials: float, z: float = 1.96) -> tuple[float, float] | None:
    if not trials or trials <= 0:
        return None
    p = successes / trials
    d = 1 + z * z / trials
    c = (p + z * z / (2 * trials)) / d
    h = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    return max(0.0, c - h), min(1.0, c + h)


def poisson_ci(k: float, z: float = 1.96) -> tuple[float, float]:
    """95% interval for a count (Byar's approximation)."""
    lo = 0.0 if k <= 0 else k * (1 - 1 / (9 * k) - z / (3 * math.sqrt(k))) ** 3
    k1 = k + 1
    hi = k1 * (1 - 1 / (9 * k1) + z / (3 * math.sqrt(k1))) ** 3
    return max(lo, 0.0), hi


def _r(x: float | None, nd: int = 2) -> float | None:
    return None if x is None else round(x, nd)


def ad_report(placements: list[dict], events: list | None = None, campaign: str | None = None, min_orders: int = 5) -> dict:
    if not placements:
        raise ValueError(tr("Нужен хотя бы один канал в placements", "placements needs at least one channel"))
    starts = count_starts(events or [], campaign) if events else {}
    rows = []
    notes: list[str] = []
    for i, p in enumerate(placements, 1):
        name = str(p.get("name") or p.get("id") or f"p{i}")
        cost = _num(p.get("cost"))
        if cost is None or cost < 0:
            raise ValueError(tr(f"{name}: нужен cost — сколько заплатили за размещение", f"{name}: cost is required — what the placement cost"))
        views, clicks, leads = _num(p.get("views")), _num(p.get("clicks")), _num(p.get("leads"))
        st = _num(p.get("starts"))
        if st is None and p.get("id") in starts:
            st = float(starts[p["id"]])
        orders, revenue = _num(p.get("orders")), _num(p.get("revenue"))
        margin = _num(p.get("margin_pct"))
        traffic = st if st is not None else clicks
        row: dict = {"placement": name, "cost": cost}
        for k, v in (("views", views), ("clicks", clicks), ("starts", st), ("leads", leads), ("orders", orders), ("revenue", revenue)):
            if v is not None:
                row[k] = v
        row["cpm"] = _r(cost / views * 1000) if views else None
        row["cost_per_click_or_start"] = _r(cost / traffic) if traffic else None
        row["cost_per_lead"] = _r(cost / leads) if leads else None
        row["cost_per_order"] = _r(cost / orders) if orders else None
        if orders:
            lo, hi = poisson_ci(orders)
            row["cost_per_order_95ci"] = [_r(cost / hi), _r(cost / lo) if lo > 0 else None]
        row["roas"] = _r(revenue / cost) if revenue is not None and cost else None
        if revenue is not None and margin is not None:
            profit = revenue * margin / 100 - cost
            row["gross_profit_after_ads"] = _r(profit)
            row["romi_pct"] = _r(profit / cost * 100, 1) if cost else None
        if traffic and orders is not None:
            row["conversion_pct"] = _r(orders / traffic * 100)
            ci = wilson(orders, traffic)
            row["conversion_95ci_pct"] = [_r(ci[0] * 100), _r(ci[1] * 100)] if ci else None
        if orders is not None and orders < min_orders:
            row["low_data"] = True
        rows.append({k: v for k, v in row.items() if v is not None})

    total_cost = sum(r["cost"] for r in rows)
    tot = {"cost": total_cost}
    for k in ("views", "clicks", "starts", "leads", "orders", "revenue"):
        vals = [r[k] for r in rows if k in r]
        if vals:
            tot[k] = sum(vals)
    if tot.get("orders"):
        tot["cost_per_order"] = _r(total_cost / tot["orders"])
    if "revenue" in tot and total_cost:
        tot["roas"] = _r(tot["revenue"] / total_cost)
    if tot.get("views"):
        tot["cpm"] = _r(total_cost / tot["views"] * 1000)

    with_orders = [r for r in rows if r.get("orders")]
    ranked = sorted(with_orders, key=lambda r: r["cost_per_order"])
    findings: list[str] = []
    if ranked:
        best = ranked[0]
        findings.append(tr(f"Дешевле всего заказ в «{best['placement']}»: {best['cost_per_order']} за заказ.",
                           f"Cheapest order: \"{best['placement']}\" at {best['cost_per_order']} per order."))
        if len(ranked) > 1:
            worst = ranked[-1]
            findings.append(tr(f"Дороже всего в «{worst['placement']}»: {worst['cost_per_order']} за заказ.",
                               f"Most expensive: \"{worst['placement']}\" at {worst['cost_per_order']} per order."))
            b, w = best["cost_per_order_95ci"], worst["cost_per_order_95ci"]
            if b[1] is None or b[1] >= w[0]:
                findings.append(tr("Но 95%-интервалы стоимости заказа пересекаются: разница может быть случайной. Нужно больше заказов, прежде чем переносить бюджет.",
                                   "But the 95% intervals of cost per order overlap: the difference may be chance. Get more orders before moving budget."))
            else:
                findings.append(tr("Интервалы стоимости заказа не пересекаются: разница, скорее всего, не случайна.",
                                   "The cost-per-order intervals don't overlap: the difference is likely real."))
    zero = [r["placement"] for r in rows if r.get("orders") == 0]
    if zero:
        findings.append(tr(f"Без заказов: {', '.join(zero)}. Проверьте, что ссылка или промокод работали, и учтите отложенные покупки.",
                           f"No orders: {', '.join(zero)}. Check the link or promo code worked, and allow for delayed purchases."))
    if any(r.get("low_data") for r in rows):
        notes.append(tr(f"Где меньше {min_orders} заказов, выводы ненадёжны.", f"Where there are fewer than {min_orders} orders, conclusions are unreliable."))
    if not any("revenue" in r for r in rows):
        notes.append(tr("Нет выручки — ROAS не посчитать. Добавьте revenue, а для прибыли ещё margin_pct.",
                        "No revenue — ROAS can't be computed. Add revenue, and margin_pct for profit."))
    notes.append(tr("Учтите возвраты и покупки позже периода отчёта. Решение о бюджете — за вами.",
                    "Account for returns and purchases after the report period. Budget decisions are yours."))
    return {"placements": rows, "total": tot, "findings": findings, "notes": notes,
            "starts_from_events": starts or None}


# ---------------------------------------------------------------- ad post check

ERID_RX = re.compile(r"erid[=:\s]+([A-Za-z0-9]{6,64})", re.I)
LABEL_RX = re.compile(r"\b(?:Реклама|реклама|РЕКЛАМА)\b")
ADVERTISER_RX = re.compile(r"\b(?:ИНН|ОГРН(?:ИП)?)\s*:?\s*\d{10,15}\b|\b(?:ООО|ОАО|ПАО|АО|ЗАО|ИП)\s+[«\"]?[А-ЯЁA-Z]", re.U)


def check_ad_post(text: str, links: list[str] | None = None, channel_subscribers: int | None = None,
                  channel_has_a_plus: bool | None = None, advertiser_site: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []
    all_links = list(links or []) + re.findall(r"https?://[^\s)\]>\"']+", text)

    label = LABEL_RX.search(text)
    if not label:
        errors.append(tr("Нет пометки «Реклама».", "No «Реклама» (advertisement) label."))
    elif label.start() > 120:
        warnings.append(tr("Пометка «Реклама» должна быть видна до основного текста — поставьте её в начало.",
                           "The «Реклама» label must be seen before the main text — move it to the top."))
    else:
        ok.append(tr("Пометка «Реклама» есть.", "«Реклама» label present."))

    if ADVERTISER_RX.search(text) or advertiser_site:
        ok.append(tr("Сведения о рекламодателе есть.", "Advertiser details present."))
    else:
        errors.append(tr("Нет сведений о рекламодателе: название и ИНН/ОГРН или ссылка на сайт, где они указаны.",
                         "No advertiser details: name and INN/OGRN, or a link to a site showing them."))

    plain = re.sub(r"https?://[^\s)\]>\"']+", " ", text)  # erid written in the post itself, not inside a link
    text_erids = set(m.group(1) for m in ERID_RX.finditer(plain))
    erids = set(text_erids)
    for link in all_links:
        q = dict(parse_qsl(urlsplit(link).query))
        if q.get("erid"):
            erids.add(q["erid"])
    if not erids:
        errors.append(tr("Нет токена erid ни в ссылке, ни в тексте. Получите его в ОРД до публикации.",
                         "No erid token in the link or text. Get it from an ad-data operator (ORD) before publishing."))
    elif len(erids) > 1:
        warnings.append(tr(f"Несколько разных erid ({', '.join(sorted(erids))}) — у одного креатива должен быть один токен.",
                           f"Several different erids ({', '.join(sorted(erids))}) — one creative should have one token."))
    else:
        ok.append(tr(f"erid найден: {next(iter(erids))}. Его подлинность здесь не проверить — сверьте в ОРД.",
                     f"erid found: {next(iter(erids))}. Authenticity can't be checked here — confirm with your ORD."))
    missing = [l for l in all_links if "erid=" not in l and "max.ru" not in l]
    if erids and missing and not text_erids:
        warnings.append(tr("Не во всех внешних ссылках есть erid — добавьте его в каждую ссылку или в текст поста.",
                           "Not every external link carries the erid — add it to each link or to the post text."))

    if channel_subscribers is not None and channel_subscribers > 10_000 and channel_has_a_plus is False:
        errors.append(tr("Канал больше 10 000 подписчиков без отметки A+ (реестр РКН): размещать рекламу там нельзя.",
                         "Channel over 10,000 subscribers without the A+ mark (RKN registry): ads must not be placed there."))
    elif channel_subscribers is not None and channel_subscribers > 10_000 and channel_has_a_plus is None:
        warnings.append(tr("Канал больше 10 000 подписчиков: убедитесь, что у него есть отметка A+.",
                           "Channel over 10,000 subscribers: make sure it has the A+ mark."))

    if len(text) > 4000:
        errors.append(tr(f"Текст {len(text)} символов — больше 4000.", f"Text is {len(text)} characters — over 4000."))

    return {
        "looks_compliant": not errors, "errors": errors, "warnings": warnings, "ok": ok,
        "disclaimer": tr(
            "Подсказка по 38-ФЗ, не юридическое заключение. Регистрацию креатива в ОРД и ЕРИР этот инструмент не проверяет.",
            "A hint based on Russian advertising law (38-FZ), not legal advice. It does not check ORD/ERIR registration."),
    }
