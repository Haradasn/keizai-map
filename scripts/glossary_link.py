"""本文の専門用語(各ページで最初の1回)を用語集の該当項目へリンクする。"""

import re

ALIASES = [
    ("付加価値率", "fuka-kachi-ritsu"),
    ("付加価値", "fuka-kachi"),
    ("産出額", "sanshutsu"),
    ("中間投入", "chukan-toonyu"),
    ("中間需要", "chukan-juyo"),
    ("最終需要", "saishu-juyo"),
    ("輸入依存度", "yunyu-izondo"),
    ("基本表", "kihon-hyo"),
    ("延長産業連関表", "encho-hyo"),
    ("延長表", "encho-hyo"),
    ("接続産業連関表", "setsuzoku-hyo"),
    ("名目", "meimoku-jissitsu"),
    ("年平均成長率", "cagr"),
    ("影響力係数", "eikyoryoku"),
    ("感応度係数", "kanojido"),
    ("MDS", "mds"),
    ("SPPI", "sppi"),
    ("CGPI", "cgpi"),
    ("国際収支", "bop"),
    ("第3次産業活動指数", "ita"),
    ("ICIO", "icio"),
    ("ブルーオーシャン", "blue-ocean"),
    ("仮説", "kasetsu"),
]
SKIP = {
    "a",
    "script",
    "style",
    "svg",
    "button",
    "summary",
    "h1",
    "h2",
    "h3",
    "h4",
    "label",
    "title",
    "textarea",
    "select",
    "option",
    "code",
    "pre",
}
TOK = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
CLS = "underline decoration-dotted underline-offset-4 hover:text-primary"
MAP = dict(ALIASES)
RX = re.compile("|".join(sorted(map(re.escape, MAP), key=len, reverse=True)))


def link(html, used_ids=None):
    parts = TOK.split(html)
    depth = []
    used = set()
    out = []
    for p in parts:
        if p.startswith("<!--"):
            out.append(p)
            continue
        if p.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", p)
            if m:
                tag = m.group(2).lower()
                if tag in SKIP:
                    if m.group(1):
                        if tag in depth:
                            depth.remove(tag)
                    elif not p.endswith("/>"):
                        depth.append(tag)
            out.append(p)
            continue
        if depth or not p.strip():
            out.append(p)
            continue

        def rep(m):
            i = MAP[m.group(0)]
            if i in used:
                return m.group(0)
            used.add(i)
            return f'<a class="{CLS}" href="glossary.html#{i}">{m.group(0)}</a>'

        p = RX.sub(rep, p)
        out.append(p)
    return "".join(out)
