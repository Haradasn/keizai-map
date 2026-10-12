"""IndexNow(Bing など)に、更新したページを知らせる。キーは site/<キー>.txt(公開して使う仕組みの値で、秘密ではない)。

python3 scripts/ops/indexnow.py changed   # 直前のコミットで pages/lastmod.json の日付が変わったページ
python3 scripts/ops/indexnow.py all       # サイトマップの全ページ(初回用)
"""

import json
import pathlib
import re
import subprocess
import sys
import urllib.request

R = pathlib.Path(__file__).resolve().parents[2]
HOST = "keizai-atlas.com"


def key():
    ks = [p.stem for p in (R / "site").glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", p.stem)]
    assert len(ks) == 1, ks
    return ks[0]


def changed():
    new = json.loads((R / "pages/lastmod.json").read_text(encoding="utf-8"))
    try:
        old = json.loads(subprocess.check_output(["git", "show", "HEAD^:pages/lastmod.json"], cwd=R))
    except subprocess.CalledProcessError:
        old = {}
    return [p for p, v in new.items() if old.get(p, {}).get("date") != v["date"]]


def all_pages():
    sm = (R / "site/sitemap.xml").read_text(encoding="utf-8")
    return [u.split(HOST, 1)[1] for u in re.findall(r"<loc>([^<]+)</loc>", sm)]


def main():
    paths = all_pages() if sys.argv[1:] == ["all"] else changed()
    if not paths:
        print("送るページなし")
        return
    k = key()
    body = {
        "host": HOST,
        "key": k,
        "keyLocation": f"https://{HOST}/{k}.txt",
        "urlList": [f"https://{HOST}{p}" for p in paths][:10000],
    }
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: {len(paths)} ページを送信(HTTP {r.status})")


if __name__ == "__main__":
    main()
