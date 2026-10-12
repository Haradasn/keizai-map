#!/usr/bin/env bash
# 最新動向の元データ(日銀・経産省・財務省)を取得する。 使い方: scripts/ops/fetch_latest.sh <出力ディレクトリ>
#  日銀: stat-search.boj.or.jp/info/{sppi,cgpi,bp}_m_jp.zip (zip内にcsv)
#  財務省: customs.go.jp/toukei/suii/html/data/d61ma.csv (世界・月別・輸入)
#  経産省: meti.go.jp/statistics/tyo/sanzi/result/excel/b2020_ksmj.xlsx (ブラウザ風のUAとRefererが必要。無いと403)
set -euo pipefail
D="${1:?出力ディレクトリ}"; mkdir -p "$D"; cd "$D"
UA="Mozilla/5.0 (compatible; keizai-atlas-bot; +https://keizai-atlas.com)"
BUA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
need(){ [ -s "$1" ] && [ "$(stat -c%s "$1")" -gt "$2" ] || { echo "取得失敗または小さすぎる: $1" >&2; exit 1; }; }
for f in sppi_m_jp cgpi_m_jp bp_m_jp; do
  curl -fsS --retry 3 -A "$UA" -o "$f.zip" "https://www.stat-search.boj.or.jp/info/$f.zip"; need "$f.zip" 10000
  unzip -oq "$f.zip"; need "$f.csv" 10000
done
curl -fsS --retry 3 -A "$UA" -o d61ma.csv "https://www.customs.go.jp/toukei/suii/html/data/d61ma.csv"; need d61ma.csv 100000
curl -fsSL --retry 3 -A "$BUA" -H "Accept-Language: ja,en;q=0.8" -e "https://www.meti.go.jp/statistics/tyo/sanzi/result-2.html" \
  -o b2020_ksmj.xlsx "https://www.meti.go.jp/statistics/tyo/sanzi/result/excel/b2020_ksmj.xlsx"; need b2020_ksmj.xlsx 50000
file -b b2020_ksmj.xlsx | grep -qi "excel\|zip" || { echo "経産省のファイルがExcelではありません" >&2; exit 1; }
echo "fetched: $(ls | tr '\n' ' ')"
