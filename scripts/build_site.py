"""site/*.html を生成。explorer は ../io/out の成果物(または data/ にコピー済みのもの)から取り込む。"""

import sys, pathlib, json

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _shell import ld_script, render_page
from _tpl import render as render_template
from site_config import SITE_URL, SITE_NAME
from derive import metrics, render

MET = metrics()
R = pathlib.Path(__file__).resolve().parent.parent
S = R / "site"


def page(name, title, desc, body, extra=""):
    """site/<name> に1ページ書き出す。extra は head に足すタグ(パンくずの構造化データなど)。"""
    path = name[:-5]
    head_extra = ""
    if path == "index":
        head_extra = ld_script(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": SITE_NAME,
                "url": SITE_URL + "/",
                "inLanguage": "ja",
                "description": desc,
            }
        )
    og_image = None
    if path.startswith("industry/") and (S / "og" / (path[9:] + ".png")).exists():
        og_image = SITE_URL + "/og/" + path[9:] + ".png"  # 産業ごとの共有画像があれば差し替える
    html_text = render_page(path, title, desc, body, SITE_URL, SITE_NAME, head_extra + extra, og_image)
    (S / name).write_text(html_text, encoding="utf-8")


# ---------- 共通: 色パレットと共通グラフJS
PAL = json.loads((R / "pages" / "palette.json").read_text(encoding="utf-8"))
(S / "charts.js").write_text(
    "var KA={pal:"
    + json.dumps(PAL, ensure_ascii=False)
    + "};\n"
    + (R / "pages" / "charts.js").read_text(encoding="utf-8"),
    encoding="utf-8",
)
(S / "feedback.js").write_text(
    (R / "pages" / "feedback.js").read_text(encoding="utf-8"), encoding="utf-8"
)  # 読者の反応(pages/feedback.json に sitekey があるときだけ欄を出す)
import glossary_link

# ---------- 通常ページ: pages/<name>.html(本文) + pages/meta.json(title/desc/埋め込みデータ)
META = json.loads((R / "pages" / "meta.json").read_text(encoding="utf-8"))
for name, m in META.items():
    body = (R / "pages" / f"{name}.html").read_text(encoding="utf-8")
    for ph, f in m.get("data", {}).items():
        body = body.replace(ph, (R / "data" / f).read_text(encoding="utf-8"))
    if name == "guide":
        faq = json.loads((R / "pages" / "guide_faq.json").read_text(encoding="utf-8"))
        faq_html = render_template("guide_faq.html.j2", faq=faq)
        faq_ld = ld_script(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
                    }
                    for item in faq
                ],
            }
        )
        body = body.replace("__FAQ_HTML__", faq_html).replace("__FAQ_LD__", faq_ld)
    if name == "glossary":
        groups = json.loads((R / "pages" / "glossary.json").read_text(encoding="utf-8"))
        body = body.replace("__GLOSSARY__", render_template("glossary.html.j2", groups=groups))
    body = render(body, MET)
    if name != "glossary":
        body = glossary_link.link(body)
    page(f"{name}.html", m["title"], m["desc"], "\n" + body)
# ---------- 個別産業ページと産業一覧
from build_industry import build as build_industry

IND = build_industry(page, S, PAL, SITE_URL)
import build_pref

PREF = build_pref.build(page, S, SITE_URL)
# トップの「つながり」スライド用の小さなデータ(37部門の位置・規模と、取引額の大きい上位60本)
_E = json.loads((R / "data" / "explorer_data.json").read_text(encoding="utf-8"))
_ed = sorted(
    [e for e in _E["edges"] if e["s"] != e["t"] and e.get("v") and e["v"] > 0], key=lambda e: -e["v"]
)[:60]
(S / "net-mini.js").write_text(
    "window.NET_MINI="
    + json.dumps(
        {
            "gc": PAL["groups"],
            "nodes": [{k: n[k] for k in ("id", "name", "grp", "out", "x", "y", "z")} for n in _E["nodes"]],
            "edges": [{"s": e["s"], "t": e["t"], "v": e["v"]} for e in _ed],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    + ";",
    encoding="utf-8",
)
# ---------- explorer(共通シェルの中に描画。配色トークンは #xp 内に限定)
tpl = (R / "pipeline" / "explorer_template.html").read_text(encoding="utf-8")
h = tpl.replace("__GC__", json.dumps(PAL["groups"])).replace(
    "__DATA__", (R / "data" / "explorer_data.json").read_text(encoding="utf-8")
)
ED = "日本の37産業の取引を3Dネットワークで眺め、産業を選ぶと仕入れ先と販売先が浮かび上がる産業連関表エクスプローラ"


def _tok(k, t):
    return (
        '[data-theme="%s"] #xp{' % k
        + ";".join(f"--{n}:{v}" for n, v in t.items() if n != "scheme")
        + ";color-scheme:%s}" % t["scheme"]
    )


TOK = "<style>" + "\n".join(_tok(k, t) for k, t in PAL["theme"].items()) + "</style>\n"
page("explorer.html", "産業マップ｜Keizai Atlas", ED, "\n" + TOK + h)

CL = json.loads((R / "pages" / "changelog.json").read_text(encoding="utf-8"))
(S / "feed.xml").write_text(
    render_template("feed.xml.j2", site_name=SITE_NAME, site_url=SITE_URL, changelog=CL),
    encoding="utf-8",
)
(S / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
)
import datetime, hashlib

# lastmod: ページ内容のハッシュが変わった日だけ更新(pages/lastmod.json に記録)。変更が無ければ何日ビルドしても同じ。
LM_F = R / "pages" / "lastmod.json"
LM = json.loads(LM_F.read_text(encoding="utf-8")) if LM_F.exists() else {}
today = datetime.date.today().isoformat()
urls = []
for p in (
    "/",
    "/explorer",
    "/similarity",
    "/latest",
    "/international",
    "/fx",
    "/about",
    "/industries",
    "/guide",
    "/glossary",
) + tuple("/" + x for x in IND + PREF if x != "industries"):
    f = S / (("index" if p == "/" else p[1:]) + ".html")
    hsh = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    if LM.get(p, {}).get("hash") != hsh:
        LM[p] = {"hash": hsh, "date": today}
    urls.append(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{LM[p]['date']}</lastmod></url>\n")
LM_F.write_text(json.dumps(LM, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
(S / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(urls)
    + "</urlset>\n",
    encoding="utf-8",
)
