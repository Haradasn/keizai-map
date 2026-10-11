"""サイトのスモークテスト。 実行: pip install pytest playwright && playwright install chromium && pytest tests/
(事前に python3 scripts/build_site.py を実行しておく)"""
import re,json,pathlib,threading,http.server,functools
import pytest
from playwright.sync_api import sync_playwright
R=pathlib.Path(__file__).resolve().parent.parent; S=R/"site"
PAGES=["index","explorer","similarity","latest","international","about"]

@pytest.fixture(scope="session")
def base():
    h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(S))
    h.log_message=lambda *a,**k:None
    srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b=p.chromium.launch(args=["--use-gl=swiftshader","--enable-unsafe-swiftshader"]); yield b; b.close()

def open_page(browser,base,name):
    pg=browser.new_page(viewport={"width":1300,"height":900}); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(f"{base}/{name}.html",wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
    return pg,errs

# ---- 静的チェック(ブラウザ不要)
@pytest.mark.parametrize("name",PAGES)
def test_page_has_seo(name):
    h=(S/f"{name}.html").read_text(encoding="utf-8")
    assert "<title>" in h and 'rel="canonical"' in h and 'og:title' in h

def test_internal_links_resolve():
    for name in PAGES:
        h=(S/f"{name}.html").read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#:]+\.html)"',h):
            assert (S/href).exists(),f"{name}.html -> {href}"

def test_sitemap_matches_pages():
    sm=(S/"sitemap.xml").read_text(); paths=set(re.findall(r"keizai-atlas\.com(/[a-z]*)</loc>",sm))
    assert paths=={"/"}|{f"/{p}" for p in PAGES if p!="index"}

def test_index_cards_have_distinct_targets():
    h=(S/"index.html").read_text(encoding="utf-8")
    hrefs=re.findall(r'<a href="([^"]+)" class="card ',h)
    assert len(hrefs)>=4 and len(hrefs)==len(set(hrefs))

def test_data_sanity():
    d=json.loads((R/"data/similarity_map.json").read_text()); assert len(d["nodes"])==108 and 0.3<d["rho"]<1
    e=json.loads((R/"data/explorer_data.json").read_text()); assert len(e["nodes"])==37 and len(e["edges"])>100

# ---- ブラウザ
@pytest.mark.parametrize("name",PAGES)
def test_no_js_errors(browser,base,name):
    pg,errs=open_page(browser,base,name); assert errs==[]; pg.close()

def test_explorer_flow_button_shows_svg(browser,base):
    pg,errs=open_page(browser,base,"explorer")
    pg.click("#v-fl"); pg.wait_for_timeout(500)
    assert pg.evaluate("getComputedStyle(document.getElementById('flow')).display")!="none"
    assert pg.evaluate("document.getElementById('flow').childElementCount")>20
    pg.click("#v-3d"); pg.wait_for_timeout(300)
    assert pg.evaluate("getComputedStyle(document.getElementById('flow')).display")=="none"
    assert errs==[]; pg.close()

def test_explorer_3d_not_blocked_by_overlay(browser,base):
    pg,_=open_page(browser,base,"explorer")
    # 3D表示のとき、ステージ中央の要素がSVGオーバーレイではない(ドラッグを妨げない)
    assert pg.evaluate("document.elementFromPoint(650,450).closest('#flow')===null"); pg.close()

def test_similarity_page(browser,base):
    pg,errs=open_page(browser,base,"similarity")
    assert pg.locator("#sm circle").count()==108
    assert pg.locator("#coh tr").count()==4
    f0=pg.locator("#sm circle").first.get_attribute("fill")
    pg.click("[data-m=bo]"); f1=pg.locator("#sm circle").first.get_attribute("fill")
    assert f0!=f1
    pg.hover('#sm circle[data-i="10"]'); assert "取引の相手が似ている" in pg.inner_text("#info")
    assert errs==[]; pg.close()

def test_latest_charts_rendered(browser,base):
    pg,_=open_page(browser,base,"latest")
    for i in ["n-sppi","n-bp","n-cg","n-meti","n-tq","n-tp"]:
        assert pg.locator(f"#{i} svg").count()==1,i
    pg.close()

def test_theme_toggle(browser,base):
    pg,_=open_page(browser,base,"index")
    t0=pg.evaluate("document.documentElement.dataset.theme")
    pg.click("[aria-label*=テーマ],#thm,label.swap,button:has-text('◐')",timeout=3000)
    assert pg.evaluate("document.documentElement.dataset.theme")!=t0; pg.close()
