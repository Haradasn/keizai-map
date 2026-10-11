#!/usr/bin/env bash
# 産業連関表パイプラインを順に実行し、サイトをビルドする。
#   原本(e-Statのxlsx)は raw/ に置く(KEIZAI_RAW で変更可)。出力は data/ (KEIZAI_OUT で変更可)。
#   使い方: scripts/run_all.sh          # 全部
#           scripts/run_all.sh --site   # サイトのビルドだけ(data/ の加工済みデータを使う)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" != "--site" ]; then
  for s in build_graph timeseries ext_timeseries analysis blue_ocean blue_groups edge_stories \
           make_flows make_circulation build_explorer similarity_map; do
    echo "== $s"; python3 -W ignore "pipeline/$s.py"
  done
  # 図(任意): make_overview make_story_overview make_blue_ocean make_ext_change
  # 外部データ(別途ダウンロードして引数で場所を指定): icio_agg / boj_nowcast / nowcast2 は各ファイル冒頭を参照
fi
python3 scripts/build_site.py
echo done
