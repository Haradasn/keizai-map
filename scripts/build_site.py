"""site/*.html を生成。explorer は ../io/out の成果物(または data/ にコピー済みのもの)から取り込む。"""

import sys, pathlib, json

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _shell import HEAD, FOOT, seo
from site_config import SITE_URL, SITE_NAME
from derive import metrics, render

MET = metrics()
R = pathlib.Path(__file__).resolve().parent.parent
S = R / "site"


def page(name, title, desc, body, extra=""):
    path = name[:-5]
    ld = ""
    if path == "index":
        ld = (
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": SITE_NAME,
                    "url": SITE_URL + "/",
                    "inLanguage": "ja",
                    "description": desc,
                },
                ensure_ascii=False,
            )
            + "</script>"
        )
    S_ = seo(path, title, desc, SITE_URL, SITE_NAME, ld + extra)
    if path.startswith("industry/") and (S / "og" / (path[9:] + ".png")).exists():
        S_ = S_.replace(SITE_URL + "/og.png", SITE_URL + "/og/" + path[9:] + ".png")
    (S / name).write_text(HEAD.format(title=title, desc=desc, seo=S_) + body + FOOT, encoding="utf-8")


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
        fh = "".join(
            f'<div class="collapse collapse-arrow bg-base-100 border border-base-300"><input type="checkbox" aria-label="{q["q"]}"><div class="collapse-title font-medium">{q["q"]}</div><div class="collapse-content text-sm text-base-content/80"><p>{q["a"]}</p></div></div>'
            for q in faq
        )
        ld = (
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": q["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": q["a"]},
                        }
                        for q in faq
                    ],
                },
                ensure_ascii=False,
            )
            + "</script>"
        )
        body = body.replace("__FAQ_HTML__", fh).replace("__FAQ_LD__", ld)
    if name == "glossary":
        gl = json.loads((R / "pages" / "glossary.json").read_text(encoding="utf-8"))
        h = ""
        for g in gl:
            h += f'<section class="space-y-2"><h2 class="text-xl font-bold">{g["group"]}</h2><dl class="space-y-3">'
            for t in g["terms"]:
                h += f'<div id="{t["id"]}" class="scroll-mt-20"><dt class="font-bold">{t["t"]}</dt><dd class="text-sm text-base-content/80">{t["d"]}</dd></div>'
            h += "</dl></section>"
        body = body.replace("__GLOSSARY__", h)
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

from xml.sax.saxutils import escape as xe

CL = json.loads((R / "pages" / "changelog.json").read_text(encoding="utf-8"))
fe = "".join(
    f'<entry><title>{xe(c["title"])}</title><link href="{SITE_URL}{c["link"]}"/><id>{SITE_URL}/feed#{c["date"]}-{len(CL) - i}</id><updated>{c["date"]}T00:00:00+09:00</updated><summary>{xe(c["summary"])}</summary></entry>'
    for i, c in enumerate(CL)
)
(S / "feed.xml").write_text(
    f'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>{SITE_NAME} 更新情報</title><link href="{SITE_URL}/feed.xml" rel="self"/><link href="{SITE_URL}/"/><id>{SITE_URL}/</id><updated>{CL[0]["date"]}T00:00:00+09:00</updated><author><name>{SITE_NAME}</name></author>{fe}</feed>',
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
