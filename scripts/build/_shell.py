"""全ページ共通の殻(head・ヘッダー・フッター)の描画に必要な値を用意する。マークアップは templates/base.html.j2。"""

import json
import pathlib

from _tpl import render

ROOT = pathlib.Path(__file__).resolve().parents[2]
FEEDBACK = json.loads((ROOT / "pages" / "feedback.json").read_text(encoding="utf-8"))


def ld_script(data):
    """構造化データ(JSON-LD)の <script> タグを返す。"""
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def breadcrumb_head(items):
    """パンくずの JSON-LD と <base href="/"> を返す。items=[(名前, URL or None)] を上から順に。"""
    elements = []
    for position, (name, url) in enumerate(items, start=1):
        element = {"@type": "ListItem", "position": position, "name": name}
        if url:
            element["item"] = url
        elements.append(element)
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements}
    return '<base href="/">' + ld_script(data)


def render_page(path, title, desc, body, site_url, site_name, head_extra="", og_image=None):
    """共通の殻に本文を入れた1ページ分のHTMLを返す。path は拡張子なしのページ名('index' など)。"""
    url = site_url + ("/" if path in ("", "index") else "/" + path)
    return render(
        "base.html.j2",
        title=title,
        desc=desc,
        body=body,
        url=url,
        site_url=site_url,
        site_name=site_name,
        og_image=og_image or site_url + "/og.png",
        head_extra=head_extra,
        sitekey=FEEDBACK.get("sitekey", ""),
    )
