"""アクセシビリティ(axe-core)・ページの重さ・CSP とセキュリティヘッダー"""

import re, pathlib
import pytest
from conftest import R, S, open_page


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
