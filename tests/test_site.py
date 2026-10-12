"""サイトのスモークテスト。 実行: pip install pytest playwright && playwright install chromium && pytest tests/
(事前に python3 scripts/build_site.py を実行しておく)"""

import re, json, pathlib, threading, http.server, functools
import pytest
from playwright.sync_api import sync_playwright

R = pathlib.Path(__file__).resolve().parent.parent
S = R / "site"
PAGES = ["index", "explorer", "similarity", "latest", "international", "about", "guide", "glossary"]


def site_headers():
    """site/_headers(Cloudflare の形式)を読み、[(パスの正規表現, [(名前, 値)])] にする"""
    rules = []
    for line in (S / "_headers").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            pat = "^" + re.escape(line.strip()).replace(r"\*", ".*") + "$"
            rules.append((re.compile(pat), []))
        else:
            k, v = line.strip().split(":", 1)
            rules[-1][1].append((k.strip(), v.strip()))
    return rules


class Handler(http.server.SimpleHTTPRequestHandler):
    """本番と同じヘッダー(CSP など)を付けて返すローカルサーバー"""

    rules = []

    def end_headers(self):
        path = self.path.split("?")[0]
        for pat, hs in self.rules:
            if pat.match(path):
                for k, v in hs:
                    self.send_header(k, v)
        super().end_headers()

    def log_message(self, *a, **k):
        pass


@pytest.fixture(scope="session")
def base():
    Handler.rules = site_headers()
    h = functools.partial(Handler, directory=str(S))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        yield b
        b.close()


def open_page(browser, base, name):
    pg = browser.new_page(viewport={"width": 1300, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # CSP に止められた読み込み・実行もエラーとして数える
    pg.on(
        "console",
        lambda m: errs.append(m.text) if "Content Security Policy" in m.text else None,
    )
    pg.goto(f"{base}/{name}.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(1200)
    return pg, errs


# ---- 静的チェック(ブラウザ不要)
@pytest.mark.parametrize("name", PAGES)
def test_page_has_seo(name):
    h = (S / f"{name}.html").read_text(encoding="utf-8")
    assert "<title>" in h and 'rel="canonical"' in h and "og:title" in h


def test_internal_links_resolve():
    for name in PAGES:
        h = (S / f"{name}.html").read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#:]+\.html)"', h):
            assert (S / href).exists(), f"{name}.html -> {href}"


def test_sitemap_matches_pages():
    sm = (S / "sitemap.xml").read_text()
    paths = re.findall(r"keizai-atlas\.com(/[\w/]*)</loc>", sm)
    assert len(paths) == len(set(paths))
    for p in paths:
        assert (S / (("index" if p == "/" else p[1:]) + ".html")).exists(), p
    assert {
        "/",
        "/explorer",
        "/similarity",
        "/latest",
        "/international",
        "/about",
        "/industries",
        "/guide",
        "/glossary",
    } <= set(paths)
    assert sum(p.startswith("/industry/") for p in paths) == 145


def test_index_cards_have_distinct_targets():
    h = (S / "index.html").read_text(encoding="utf-8")
    hrefs = re.findall(r'<a\s+href="([^"]+)"\s+class="card\s', h)  # 改行を挟む整形にも対応
    assert len(hrefs) >= 4 and len(hrefs) == len(set(hrefs))


def test_data_sanity():
    d = json.loads((R / "data/similarity_map.json").read_text())
    assert len(d["nodes"]) == 108 and 0.3 < d["rho"] < 1
    e = json.loads((R / "data/explorer_data.json").read_text())
    assert len(e["nodes"]) == 37 and len(e["edges"]) > 100


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


def test_pipeline_scripts_compile():
    import py_compile

    for f in sorted((R / "pipeline").glob("*.py")):
        py_compile.compile(str(f), doraise=True)


def test_shared_charts_js_and_palette():
    js = (S / "charts.js").read_text(encoding="utf-8")
    assert js.startswith("var KA={pal:") and re.search(r"KA\.line\s*=", js)
    for name in ("international", "latest", "similarity"):
        assert '<script src="charts.js">' in (S / f"{name}.html").read_text(encoding="utf-8")
    # 折れ線チャートの色はパレット経由(ページ本文に折れ線用の直書き色を残さない)
    for name in ("international", "latest"):
        assert not re.search(r'c:"#[0-9a-f]{6}"', (R / "pages" / f"{name}.html").read_text(encoding="utf-8"))


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


# ---- データ整合
def test_explorer_data_consistency():
    e = json.loads((R / "data/explorer_data.json").read_text())
    tot = sum(n["out"] for n in e["nodes"])
    assert 800 < tot < 1100, tot  # 兆円: 国内生産額の合計は約1,000兆円
    ids = {n["id"] for n in e["nodes"]}
    assert all(
        x["s"] in ids and x["t"] in ids and max(x.get("v") or 0, x.get("v20") or 0, x.get("v22") or 0) > 0
        for x in e["edges"]
    )
    assert all(0 <= n["grp"] < len(e["groups"]) for n in e["nodes"])


def test_chart_data_aligned():
    n2 = json.loads((R / "data/nowcast2_chart.json").read_text())
    for k, v in n2["meti"].items():
        assert len(v) == len(n2["months"]), k
    n1 = json.loads((R / "data/nowcast_chart.json").read_text())
    for k, v in n1["sppi"].items():
        assert len(v) == len(n1["months"]), k
    ic = json.loads((R / "data/icio_chart.json").read_text())
    for key in ("out", "dig", "digimp", "en", "enimp"):
        for c, v in ic[key].items():
            assert len(v) == len(ic["years"]) and all(0 <= x <= 100 for x in v), (key, c)


def test_similarity_groups_exist():
    d = json.loads((R / "data/similarity_map.json").read_text())
    codes = {n["c"] for n in d["nodes"]}
    for g, v in d["groups"].items():
        assert set(v["codes"]) <= codes, g
    assert set(d["coh"]) == set(d["groups"])


def test_explorer_header_hamburger_on_mobile(browser, base):
    for w, links, menu in ((390, "none", "block"), (1200, "flex", "none")):
        pg = browser.new_page(viewport={"width": w, "height": 700})
        pg.goto(f"{base}/explorer.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(800)
        assert pg.evaluate("getComputedStyle(document.querySelector('header nav > span')).display") == links
        assert pg.evaluate("getComputedStyle(document.querySelector('header nav .dropdown')).display") == menu
        pg.close()


def test_index_finding_links_hit_existing_anchors():
    h = (S / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'href="([a-z]+\.html)#([\w-]+)"', h)
    assert len(links) >= 6
    for page, anchor in links:
        assert f'id="{anchor}"' in (S / page).read_text(encoding="utf-8"), (page, anchor)


def test_no_unrendered_placeholders():
    for name in PAGES:
        assert "{{" not in (S / f"{name}.html").read_text(encoding="utf-8"), name


def test_derived_metrics_sane():
    import sys

    sys.path.insert(0, str(R / "scripts"))
    from derive import metrics

    M = metrics()
    assert 0 < float(M["sppi_avg_0"]) < 300 and float(M["fuel_peak"]) > float(M["fuel_0"])
    assert M["sppi_last"].endswith("月") and M["meti_last"].endswith("月")


# ---- 個別産業ページ
def _industry_files():
    return sorted((S / "industry").glob("*.html"))


def test_industry_pages_complete_and_valid():
    fs = _industry_files()
    assert len(fs) == 145  # 108産業 + 37部門
    titles = set()
    for f in fs:
        h = f.read_text(encoding="utf-8")
        assert "<h1" in h and 'rel="canonical"' in h and re.search(r'<base href="/"\s*/?>', h), f.name
        assert not re.search(r"\bnan\b|None|{{", h), f.name
        t = re.search(r"<title>(.*?)</title>", h).group(1)
        assert t not in titles, t
        titles.add(t)
        assert f'/industry/{f.stem}"' in h  # canonical
        for href in re.findall(r'href="(industry/[\w]+\.html)"', h):
            assert (S / href).exists(), (f.name, href)


def test_industries_index_links_all():
    h = (S / "industries.html").read_text(encoding="utf-8")
    for f in _industry_files():
        assert f'href="industry/{f.name}"' in h, f.name


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


def test_guide_faq_matches_ldjson():
    import json, re

    h = (S / "guide.html").read_text(encoding="utf-8")
    m = re.search(r'"@type":\s*"FAQPage".*?</script>', h, re.S)
    assert m, "FAQPage JSON-LD missing"
    faq = json.loads((R / "pages/guide_faq.json").read_text(encoding="utf-8"))
    for item in faq:
        q = item.get("q") or item.get("question")
        assert q and q in h


def test_glossary_anchors():

    h = (S / "glossary.html").read_text(encoding="utf-8")
    assert "__GLOSSARY__" not in h and "__FAQ" not in (S / "guide.html").read_text(encoding="utf-8")
    assert h.count("<dt") >= 20


def test_glossary_links_resolve():
    gl = json.loads((R / "pages/glossary.json").read_text(encoding="utf-8"))
    ids = {t["id"] for g in gl for t in g["terms"]}
    n = 0
    for f in S.glob("*.html"):
        for i in re.findall(r'href="glossary\.html#([a-z0-9-]+)"', f.read_text(encoding="utf-8")):
            assert i in ids, (f.name, i)
            n += 1
    assert n >= 10


def test_og_images_exist():
    from PIL import Image

    seen = set()
    for f in S.rglob("*.html"):
        m = re.search(r'og:image" content="https://keizai-atlas\.com/([^"]+)"', f.read_text(encoding="utf-8"))
        assert m, f
        seen.add(m.group(1))
    assert len(seen) >= 146
    for rel in seen:
        assert (S / rel).exists(), rel
        assert Image.open(S / rel).size == (1200, 630), rel


def test_feed_valid():
    import xml.etree.ElementTree as ET

    t = ET.parse(S / "feed.xml").getroot()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    es = t.findall("a:entry", ns)
    assert len(es) >= 4
    ids = [e.find("a:id", ns).text for e in es]
    assert len(set(ids)) == len(ids)
    for f in S.rglob("*.html"):
        assert 'type="application/atom+xml"' in f.read_text(encoding="utf-8"), f


def test_prefecture_pages_and_balance():
    d = json.loads((R / "data/pref_37.json").read_text(encoding="utf-8"))
    assert {
        "tokyo",
        "aichi",
        "osaka",
        "kanagawa",
        "saitama",
        "chiba",
        "hyogo",
        "okinawa",
        "fukuoka",
        "hokkaido",
        "tochigi",
        "yamanashi",
        "kyoto",
        "wakayama",
        "shiga",
        "kumamoto",
        "niigata",
        "toyama",
        "okayama",
        "mie",
        "kagoshima",
        "gunma",
        "tottori",
        "fukui",
    } <= set(d)
    known = {
        "tokyo": 209.8,
        "aichi": 80.0,
        "osaka": 72.1,
        "kanagawa": 61.5,
        "chiba": 43.5,
        "okinawa": 6.9,
        "fukuoka": 37.1,
        "hokkaido": 36.2,
        "shiga": 13.4,
        "kyoto": 18.0,
        "tochigi": 17.2,
        "niigata": 16.2,
        "kumamoto": 11.1,
        "mie": 18.7,
    }  # 各県の公表値(兆円)
    for k, p in d.items():
        assert k not in known or abs(p["total_out"] / 1e6 - known[k]) < 0.1, (k, p["total_out"])
        for o in p["sectors"]:
            assert abs(o["dom_dummy"] if False else (o["dem"] + o["exp"] - o["imp"] - o["out"])) <= max(
                2, o["out"] * 1e-6
            )
        assert (S / "prefecture" / f"{k}.html").exists()
    sm = (S / "sitemap.xml").read_text(encoding="utf-8")
    assert "/prefectures" in sm and "/prefecture/aichi" in sm


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


def test_weekly_report_runs_without_keys():
    """キーが無くても最後まで動き、各節に「取得できませんでした」が出ること(書き間違いで落ちないことの確認)"""
    import subprocess, os

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CF_API_TOKEN", "CF_ACCOUNT_ID", "GSC_SA_JSON", "FEEDBACK_KEY")
    }
    r = subprocess.run(
        ["python3", str(R / "scripts/weekly_report.py")], capture_output=True, text=True, env=env, timeout=60
    )
    assert r.returncode == 0 and r.stdout.count("取得できませんでした") == 3, (r.stdout, r.stderr)
    r = subprocess.run(
        ["python3", str(R / "scripts/weekly_report.py"), "--check"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert "NameError" not in r.stdout and "未設定" in r.stdout, (r.stdout, r.stderr)


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


CSP_PAGES = [
    "index",
    "explorer",
    "prefecture-map",
    "prefecture/tokyo",
    "industry/66",
    "fx",
    "changelog",
    "similarity",
]


@pytest.mark.parametrize("name", CSP_PAGES)
def test_csp_does_not_block(browser, base, name):
    """本番と同じ CSP の下で、ページの読み込み・描画が止められないこと"""
    pg, errs = open_page(browser, base, name)
    pg.mouse.wheel(0, 2000)
    pg.wait_for_timeout(800)
    assert errs == []
    pg.close()


def test_security_headers_served(base):
    import urllib.request

    h = urllib.request.urlopen(f"{base}/index.html").headers
    csp = h["Content-Security-Policy"]
    assert "object-src 'none'" in csp and "frame-ancestors 'none'" in csp
    assert h["X-Content-Type-Options"] == "nosniff"


def test_data_checks_pass():
    """scripts/check_data.py の形の検査が通ること(比較元なし)"""
    import subprocess, sys

    p = subprocess.run([sys.executable, str(R / "scripts/check_data.py")], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-2000:]


# ---- アクセシビリティ(axe-core)。npm install で入る node_modules/axe-core を使う
def _axe_source():
    import os

    for p in (
        R / "node_modules/axe-core/axe.min.js",
        pathlib.Path(os.environ.get("AXE_PATH", "/nonexistent")),
    ):
        if p.exists():
            return p.read_text(encoding="utf-8")
    if os.environ.get("CI"):
        raise AssertionError("axe-core がありません(npm install を先に実行)")
    pytest.skip("axe-core が無いのでスキップ(AXE_PATH で場所を指定できる)")


A11Y_PAGES = [
    "index",
    "explorer",
    "prefecture-map",
    "prefectures",
    "prefecture/tokyo",
    "industries",
    "industry/66",
    "fx",
    "latest",
    "similarity",
    "international",
    "changelog",
    "glossary",
    "guide",
    "about",
]


@pytest.mark.parametrize("theme", ["night", "nord"])
def test_accessibility(browser, base, theme):
    """WCAG の自動検査(コントラスト・ラベル・見出しの順序など)で違反がないこと。両テーマで確認"""
    axe = _axe_source()
    found = []
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    pg.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
    for name in A11Y_PAGES:
        pg.goto(f"{base}/{name}.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(900)
        pg.add_script_tag(content=axe)
        res = pg.evaluate(
            """async () => {
              const r = await axe.run(document, { resultTypes: ["violations"] });
              return r.violations.map((v) => v.id + " ×" + v.nodes.length + " " + v.nodes[0].target.join(" "));
            }"""
        )
        found += [f"{name}: {v}" for v in res]
    pg.close()
    assert found == [], "\n".join(found)


# ---- ページの重さ(gzip 後。HTML + そのページが読む同一サイトの JS/CSS)
BUDGET_KB = {"explorer": 300}  # 3D ライブラリを読むページだけ別枠
DEFAULT_BUDGET_KB = 80


def test_page_weight_budget():
    import gzip

    over = []
    for f in sorted(S.rglob("*.html")):
        s = f.read_text(encoding="utf-8")
        size = len(gzip.compress(s.encode()))
        refs = re.findall(r'<script[^>]*\ssrc="([^"]+)"', s) + re.findall(r'<link[^>]*href="([^"]+\.css)"', s)
        for r in refs:
            p = S / r.lstrip("/")
            if not r.startswith("http") and p.exists():
                size += len(gzip.compress(p.read_bytes()))
        name = str(f.relative_to(S))[:-5]
        limit = BUDGET_KB.get(name, DEFAULT_BUDGET_KB)
        if size > limit * 1024:
            over.append(f"{name}: {size / 1024:.0f}KB > {limit}KB")
    assert over == [], "\n".join(over)
