"""本番サイトの死活監視。主要ページ・配信ファイル・API(Worker と D1)・セキュリティヘッダーを確かめる。

  python3 scripts/ops/uptime_check.py [--base https://keizai-atlas.com]

問題があれば一覧を出して終了コード 1。書き込みはしない(API は存在しないパスに GET して、Worker と D1 の設定だけを見る)。
"""

import argparse
import sys
import urllib.error
import urllib.request

UA = "keizai-atlas-uptime-check"
# (パス, 本文に含まれるべき文字列)
PAGES = [
    ("/", "Keizai Atlas"),
    ("/explorer", "産業マップ"),
    ("/prefecture-map", "pm-map"),
    ("/industries", "産業一覧"),
    ("/latest", "最新動向"),
    ("/changelog", "更新情報"),
    ("/feed.xml", "<feed"),
    ("/sitemap.xml", "<urlset"),
    ("/assets.css", ".btn"),
    ("/vendor/maplibre-gl.js", "maplibre"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://keizai-atlas.com")
    a = ap.parse_args()
    bad = []
    for path, want in PAGES:
        try:
            st, _, body = fetch(a.base + path)
        except Exception as e:  # 接続できない・タイムアウト
            bad.append(f"{path}: {type(e).__name__}: {e}")
            continue
        if st != 200:
            bad.append(f"{path}: HTTP {st}")
        elif want.lower() not in body.lower():
            bad.append(f"{path}: 本文に「{want}」がない")

    # セキュリティヘッダー(site/_headers が効いているか)
    try:
        _, h, _ = fetch(a.base + "/")
        csp = h.get("Content-Security-Policy") or ""
        if "object-src 'none'" not in csp:
            bad.append("/: Content-Security-Policy が付いていない")
        if (h.get("X-Content-Type-Options") or "").lower() != "nosniff":
            bad.append("/: X-Content-Type-Options が付いていない")
    except Exception as e:
        bad.append(f"ヘッダー: {type(e).__name__}")

    # API: 存在しないパスは 404(Worker が動き、D1 がつながっている)。503 なら D1 の設定が外れている
    try:
        st, _, body = fetch(a.base + "/api/uptime-check")
        if st != 404 or '"ok":false' not in body.replace(" ", ""):
            bad.append(f"/api: HTTP {st}(404 のはず。503 なら D1 の設定を確認)")
    except Exception as e:
        bad.append(f"/api: {type(e).__name__}")

    if bad:
        print("問題あり:")
        for b in bad:
            print(" -", b)
        sys.exit(1)
    print(f"正常({len(PAGES)} ページ・ヘッダー・API)")


if __name__ == "__main__":
    main()
