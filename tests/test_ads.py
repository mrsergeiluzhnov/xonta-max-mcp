import pytest

from xonta_max import ads, mocks

ORG = "Реклама. ООО «Ромашка», ИНН 7701234567\n"


def test_slug_and_tracking_links():
    assert ads.slug("Канал про косметику") == "kanal_pro_kosmetiku"
    assert ads.slug("https://max.ru/beauty_news") == "beauty_news"
    assert ads.slug("@Шуб и ёлки!") == "shub_i_elki"

    res = ads.tracking_links("Чёрная пятница", [{"name": "Канал про косметику", "cost": 5000, "erid": "2VtzAbc123"},
                                                {"name": "Канал про косметику"}, {"name": "https://max.ru/beauty_news"}],
                             bot_name="@shop_bot", mini_app_bot="shop_bot", site_url="https://shop.ru/sale?x=1&utm_source=old")
    rows = res["placements"]
    assert [r["id"] for r in rows] == ["chernaya_pyatnitsa_kanal_pro_kosmetiku", "chernaya_pyatnitsa_kanal_pro_kosmetiku_2",
                                       "chernaya_pyatnitsa_beauty_news"]
    assert rows[0]["bot_link"] == "https://max.ru/shop_bot?start=chernaya_pyatnitsa_kanal_pro_kosmetiku"
    assert rows[0]["mini_app_link"].endswith("?startapp=chernaya_pyatnitsa_kanal_pro_kosmetiku")
    assert rows[0]["site_link"] == ("https://shop.ru/sale?x=1&utm_source=max&utm_medium=seeding&utm_campaign=chernaya_pyatnitsa"
                                    "&utm_content=kanal_pro_kosmetiku&erid=2VtzAbc123")
    assert "erid" not in rows[1]["site_link"]
    assert len(res["warnings"]) == 2  # two placements without erid
    assert len({r["promo_code"] for r in rows}) == 3
    for r in rows:
        payload = r["bot_link"].split("start=")[1]
        assert len(payload) <= 128 and all(c.isalnum() or c in "_-" for c in payload)
    assert res["media_plan_csv"].splitlines()[0].startswith("placement;id;cost;bot_link")

    long = ads.tracking_links("x" * 100, [{"name": "y" * 100}], bot_name="b_bot")
    assert len(long["placements"][0]["bot_link"].split("start=")[1]) <= 128

    with pytest.raises(ValueError):
        ads.tracking_links("c", [{"name": "a"}])
    with pytest.raises(ValueError):
        ads.tracking_links("c", [], bot_name="b")


def test_count_starts_from_mock_updates():
    events = [mocks.make_update("bot_started", payload="bf_a") for _ in range(3)]
    events += [mocks.make_update("bot_started", payload="bf_b"), mocks.make_update("bot_started"),
               mocks.make_update("message_created"), {"payload": "bf_b"}, "bf_a", "other_x"]
    assert ads.count_starts(events, "bf") == {"bf_a": 4, "bf_b": 2}
    assert ads.count_starts(events)["other_x"] == 1


def test_poisson_interval_matches_exact_values():
    lo, hi = ads.poisson_ci(12)
    assert abs(lo - 6.20) < 0.05 and abs(hi - 20.96) < 0.05  # exact Garwood interval
    lo0, hi0 = ads.poisson_ci(0)
    assert lo0 == 0 and abs(hi0 - 3.69) < 0.05


def test_ad_report_metrics_and_caution():
    res = ads.ad_report([
        {"name": "A", "id": "bf_a", "cost": 5000, "views": 10000, "orders": 12, "revenue": 60000, "margin_pct": 40},
        {"name": "B", "id": "bf_b", "cost": 3000, "views": 6000, "starts": 120, "orders": 3, "revenue": 9000},
        {"name": "C", "cost": 1000, "clicks": 50, "orders": 0},
    ], events=["bf_a"] * 300)
    a, b, c = res["placements"]
    assert a["starts"] == 300 and a["cpm"] == 500 and a["cost_per_order"] == 416.67 and a["roas"] == 12
    assert a["gross_profit_after_ads"] == 19000 and a["romi_pct"] == 380
    assert a["conversion_pct"] == 4 and a["conversion_95ci_pct"][0] < 4 < a["conversion_95ci_pct"][1]
    assert b["low_data"] and "romi_pct" not in b
    assert c["orders"] == 0 and "cost_per_order" not in c
    assert res["total"]["cost"] == 9000 and res["total"]["orders"] == 15
    text = " ".join(res["findings"])
    assert "«A»" in text and "случайной" in text and "C" in text

    clear = ads.ad_report([{"name": "A", "cost": 5000, "orders": 100}, {"name": "B", "cost": 5000, "orders": 20}])
    assert "не случайна" in clear["findings"][-1]

    with pytest.raises(ValueError):
        ads.ad_report([{"name": "A"}])


def test_check_ad_post():
    good = ads.check_ad_post(ORG + "Скидка 30%: https://shop.ru/sale?erid=2VtzqAbc123")
    assert good["looks_compliant"] and not good["warnings"]

    bad = ads.check_ad_post("Лучший крем! https://shop.ru/sale", channel_subscribers=20000, channel_has_a_plus=False)
    assert not bad["looks_compliant"] and len(bad["errors"]) == 4

    late = ads.check_ad_post("Отличный крем. " * 12 + ORG + "erid: 2VtzqAbc123")
    assert late["looks_compliant"] and any("начало" in w for w in late["warnings"])

    two = ads.check_ad_post(ORG + "erid: AAAAAA111 https://x.ru/?erid=BBBBBB222")
    assert any("Несколько" in w for w in two["warnings"])

    partial = ads.check_ad_post(ORG + "https://a.ru/?erid=AAAAAA111 и https://b.ru/", )
    assert any("Не во всех" in w for w in partial["warnings"])

    site = ads.check_ad_post("Реклама\nКрем https://shop.ru/?erid=AAAAAA111", advertiser_site="https://shop.ru/about")
    assert site["looks_compliant"]

    unknown_a_plus = ads.check_ad_post(ORG + "erid: AAAAAA111", channel_subscribers=50000)
    assert any("A+" in w for w in unknown_a_plus["warnings"])

    long = ads.check_ad_post(ORG + "erid: AAAAAA111 " + "x" * 4000)
    assert any("4000" in e for e in long["errors"])
