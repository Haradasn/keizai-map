"""Google の登録(インデックス)状況を確かめる。Search Console API(URL 検査・サイトマップ)を使う。

  GSC_SA_JSON=... python3 scripts/ops/index_status.py > index-status.md

主要ページと、産業・県別ページの見本について、Google が登録済みか・最後にいつ読みに来たかを表にする。
鍵は週次レポートと同じサービスアカウント(読み取りのみ)。結果は非公開リポジトリに保存する(公開ログには出さない)。
"""

import datetime as dt
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from weekly_report import get, gsc_token, post  # noqa: E402

R = pathlib.Path(__file__).resolve().parents[2]
BASE = "https://keizai-atlas.com"
MAIN = [
    "/",
    "/explorer",
    "/industries",
    "/prefecture-map",
    "/prefectures",
    "/fx",
    "/latest",
    "/guide",
    "/learn",
]


def sample_pages():
    """サイトマップから、産業ページと県別ページの見本を数件ずつ"""
    sm = (R / "site" / "sitemap.xml").read_text(encoding="utf-8")
    locs = [u.split(BASE, 1)[1] for u in __import__("re").findall(r"<loc>([^<]+)</loc>", sm)]
    ind = [p for p in locs if p.startswith("/industry/")]
    pref = [p for p in locs if p.startswith("/prefecture/")]
    return ind[:: max(1, len(ind) // 8)][:8] + pref[:4], len(locs)


def main():
    tok, err = gsc_token()
    if err:
        print(err)
        sys.exit(1)
    H = {"Authorization": "Bearer " + tok}
    sites = [
        s["siteUrl"]
        for s in get("https://www.googleapis.com/webmasters/v3/sites", H).get("siteEntry", [])
        if "keizai-atlas" in s["siteUrl"]
    ]
    if not sites:
        print("Search Console のプロパティが見つからない")
        sys.exit(1)
    site = sites[0]
    q = urllib.parse.quote(site, safe="")
    out = [f"# Google の登録状況({dt.date.today().isoformat()})", "", f"プロパティ: `{site}`", ""]

    sm = get(f"https://www.googleapis.com/webmasters/v3/sites/{q}/sitemaps", H).get("sitemap", [])
    out.append("## サイトマップ")
    if not sm:
        out.append(
            "- **未送信**(Search Console の「サイトマップ」から `https://keizai-atlas.com/sitemap.xml` を送信する)"
        )
    for s in sm:
        c = s.get("contents", [{}])
        sub = sum(int(x.get("submitted", 0)) for x in c)
        out.append(
            f"- {s['path']} 最終送信 {s.get('lastSubmitted', '-')[:10]}・最終読み込み {s.get('lastDownloaded', '-')[:10]}・"
            f"URL {sub} 件・エラー {s.get('errors', 0)}・警告 {s.get('warnings', 0)}"
        )
    samples, total = sample_pages()
    out += ["", f"## ページごと(主要ページと見本。サイトマップ全体は {total} 件)", ""]
    out += ["| ページ | 状態 | 最終クロール | Google が選んだ正規URL |", "|---|---|---|---|"]
    counts = {}
    for p in MAIN + samples:
        try:
            r = post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                {"inspectionUrl": BASE + p, "siteUrl": site, "languageCode": "ja"},
                H,
            )
            ix = r.get("inspectionResult", {}).get("indexStatusResult", {})
            state = ix.get("coverageState", "?")
            crawl = (ix.get("lastCrawlTime") or "-")[:10]
            canon = ix.get("googleCanonical", "-").replace(BASE, "") or "-"
        except Exception as e:  # 1ページの失敗で全体を止めない
            state, crawl, canon = f"取得失敗 {type(e).__name__}", "-", "-"
        counts[state] = counts.get(state, 0) + 1
        out.append(f"| {p} | {state} | {crawl} | {canon} |")
    out += ["", "## 集計", ""] + [f"- {k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    print("\n".join(out))
    print(json.dumps(counts, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
