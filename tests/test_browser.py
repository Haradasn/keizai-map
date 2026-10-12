"""ブラウザ(Playwright)で開いて確かめるテスト"""

import pytest
from conftest import R, PAGES, open_page


# ---- ブラウザ
@pytest.mark.parametrize("name", PAGES)
def test_no_js_errors(browser, base, name):
    pg, errs = open_page(browser, base, name)
    assert errs == []
    pg.close()


def test_explorer_flow_button_shows_svg(browser, base):
    pg, errs = open_page(browser, base, "explorer")
    pg.click("#v-fl")
    pg.wait_for_timeout(500)
    assert pg.evaluate("getComputedStyle(document.getElementById('flow')).display") != "none"
    assert pg.evaluate("document.getElementById('flow').childElementCount") > 20
    pg.click("#v-3d")
    pg.wait_for_timeout(300)
    assert pg.evaluate("getComputedStyle(document.getElementById('flow')).display") == "none"
    assert errs == []
    pg.close()


def test_explorer_3d_not_blocked_by_overlay(browser, base):
    pg, _ = open_page(browser, base, "explorer")
    # 3D表示のとき、ステージ中央の要素がSVGオーバーレイではない(ドラッグを妨げない)
    assert pg.evaluate("document.elementFromPoint(650,450).closest('#flow')===null")
    pg.close()


def test_similarity_page(browser, base):
    pg, errs = open_page(browser, base, "similarity")
    assert pg.locator("#sm circle").count() == 108
    assert pg.locator("#coh tr").count() == 4
    f0 = pg.locator("#sm circle").first.get_attribute("fill")
    pg.click("[data-m=bo]")
    f1 = pg.locator("#sm circle").first.get_attribute("fill")
    assert f0 != f1
    pg.hover('#sm circle[data-i="10"]')
    assert "取引の相手が似ている" in pg.inner_text("#info")
    assert errs == []
    pg.close()


def test_latest_charts_rendered(browser, base):
    pg, _ = open_page(browser, base, "latest")
    for i in ["n-sppi", "n-bp", "n-cg", "n-meti", "n-tq", "n-tp"]:
        assert pg.locator(f"#{i} svg").count() == 1, i
    pg.close()


def test_theme_toggle(browser, base):
    pg, _ = open_page(browser, base, "index")
    t0 = pg.evaluate("document.documentElement.dataset.theme")
    pg.click("[aria-label*=テーマ],#thm,label.swap,button:has-text('◐')", timeout=3000)
    assert pg.evaluate("document.documentElement.dataset.theme") != t0
    pg.close()


# ---- スマホ幅・ライトテーマ
@pytest.mark.parametrize("name", PAGES)
def test_no_horizontal_overflow_on_mobile(browser, base, name):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    pg.goto(f"{base}/{name}.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(1000)
    sw = pg.evaluate("document.documentElement.scrollWidth")
    assert sw <= 392, f"{name}: scrollWidth={sw}"
    pg.close()


@pytest.mark.parametrize("name", PAGES)
def test_light_theme_renders(browser, base, name):
    ctx = browser.new_context(viewport={"width": 1200, "height": 800})
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script("try{localStorage.setItem('theme','nord')}catch(e){}")
    pg.goto(f"{base}/{name}.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(800)
    assert pg.evaluate("document.documentElement.dataset.theme") == "nord"
    lum = pg.evaluate(
        "(()=>{const m=getComputedStyle(document.body).backgroundColor.match(/\\d+/g).map(Number);return (m[0]+m[1]+m[2])/3})()"
    )
    assert lum > 150, f"{name}: light theme background too dark ({lum})"
    assert errs == []
    ctx.close()


def test_explorer_header_hamburger_on_mobile(browser, base):
    for w, links, menu in ((390, "none", "block"), (1200, "flex", "none")):
        pg = browser.new_page(viewport={"width": w, "height": 700})
        pg.goto(f"{base}/explorer.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(800)
        assert pg.evaluate("getComputedStyle(document.querySelector('header nav > span')).display") == links
        assert pg.evaluate("getComputedStyle(document.querySelector('header nav .dropdown')).display") == menu
        pg.close()


def test_industry_page_browser(browser, base):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/industry/663.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(600)
    assert "自動車整備" in pg.inner_text("h1") and pg.evaluate("document.documentElement.scrollWidth") <= 392
    pg.click("table a >> nth=0")
    pg.wait_for_timeout(300)
    assert "/industry/" in pg.url  # 内部リンクで別の産業ページへ
    assert errs == []
    pg.close()


def test_prefecture_browser(browser, base):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/prefecture/tokyo.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392 and not errs
    assert "東京都" in pg.inner_text("h1")
    pg.close()


def test_prefecture_3d_map(browser, base):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/prefecture-map.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392 and not errs, errs
    assert pg.locator("#pm-list tbody tr").count() >= 20  # 表(WebGLがなくても読める)
    pg.select_option("#pm-ind", "20")
    pg.wait_for_timeout(300)
    assert "化学製品" in pg.inner_text("#pm-list caption")
    pg.close()


def test_index_insight_hero(browser, base):
    pg = browser.new_page(viewport={"width": 390, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/index.html", wait_until="load")
    pg.wait_for_timeout(2500)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392 and not errs, errs
    assert "日本経済" in pg.inner_text("h1")
    assert pg.locator(".ins-slide").count() >= 4
    assert "倍" in pg.locator(".ins-slide").first.inner_text()  # 県別データから計算した集中度
    on = lambda: pg.evaluate(
        "[...document.querySelectorAll('.ins-slide')].findIndex(s=>s.classList.contains('is-on'))"
    )
    a = on()
    pg.click("#ins-next")
    pg.wait_for_timeout(300)
    assert on() != a and on() >= 0
    pg.close()


def test_index_connect_slide(browser, base):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/index.html", wait_until="load")
    pg.wait_for_timeout(1500)
    for _ in range(4):
        pg.click("#ins-next")
        pg.wait_for_timeout(200)
    txt = pg.inner_text(".ins-slide.is-on")
    assert "本" in txt and "対事業所サービス" in txt and not errs, (txt, errs)  # 件数と産業名はデータから計算
    assert "explorer.html?sel=" in pg.get_attribute(".ins-slide.is-on .ins-more", "href")
    pg.close()


def test_feedback_block(browser, base):
    for path in ("index.html", "explorer.html", "industry/66.html", "prefecture/tokyo.html"):
        pg = browser.new_page(viewport={"width": 390, "height": 800})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{base}/{path}", wait_until="load")
        pg.wait_for_timeout(300)
        assert pg.locator("#fb-like").count() == 1 and pg.locator("#fb-body").count() == 1, (
            path
        )  # 反応の欄が各ページにある
        assert pg.evaluate("document.documentElement.scrollWidth") <= 392 and not errs, (path, errs)
        pg.close()


def test_fx_page(browser, base):
    import json

    ic = json.loads((R / "data/import_content_37.json").read_text())
    assert len(ic["rows"]) == 37 and all(0 <= r["direct"] <= r["total"] < 1 for r in ic["rows"])
    fx = json.loads((R / "data/fx_chart.json").read_text())
    assert fx["months"][0] == "202001" and len(fx["yen"]) == len(fx["contract"]) == len(fx["fx"])
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{base}/fx.html", wait_until="load")
    pg.wait_for_timeout(500)
    assert (
        pg.locator("#fx-line svg").count() == 1
        and pg.locator("#ic-bars svg").count() == 1
        and pg.locator("#ic-table tbody tr").count() == 37
    )
    assert (
        "{{" not in pg.content() and pg.evaluate("document.documentElement.scrollWidth") <= 392 and not errs
    ), errs
    pg.close()
