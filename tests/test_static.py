"""静的チェック(ブラウザ不要): HTML・サイトマップ・リンク・産業ページ・フィード・OGP など"""

import re, json
import pytest
from conftest import R, S, PAGES


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


def test_index_finding_links_hit_existing_anchors():
    h = (S / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'href="([a-z]+\.html)#([\w-]+)"', h)
    assert len(links) >= 6
    for page, anchor in links:
        assert f'id="{anchor}"' in (S / page).read_text(encoding="utf-8"), (page, anchor)


def test_no_unrendered_placeholders():
    for name in PAGES:
        assert "{{" not in (S / f"{name}.html").read_text(encoding="utf-8"), name


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
