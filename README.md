# Keizai Atlas（経済の地図帳）— 趣味の統計分析サイト

産業連関表から産業間のお金の流れを可視化する静的サイト。公開物は `site/` のみ（サーバー不要）。

## 構成
- `site/` 公開ディレクトリ（index / explorer / about、`assets.css`、`vendor/` に3d-force-graph同梱）
- `scripts/build_site.py` HTML生成（`pip`不要）、`npm run build:css` でTailwind+daisyUIをビルド
- `pipeline/` データ加工スクリプト（元データはe-Statから取得。パスは各スクリプト冒頭を参照）
- `data/` 加工済みCSV/JSON

## データ加工パイプライン（`pipeline/`）
`scripts/run_all.sh` で、原本→加工済みデータ(`data/`)→サイトを一括生成します。`scripts/run_all.sh --site` はサイトのビルドのみ。
- 原本（e-Statの産業連関表xlsx、延長表など）は `raw/` に置きます（git管理外。`KEIZAI_RAW` で場所を変更可）。出力先は `data/`（`KEIZAI_OUT` で変更可）。パスは `pipeline/_paths.py` に集約。
- 再現性の確認済み：原本から再生成した `data/` は、コミット済みのものとバイト単位で一致します。
- `build_explorer.py` 産業マップ用データ / `similarity_map.py` 近さの地図（MDS）
- `icio_agg.py` OECD ICIO 国際比較 / `boj_nowcast.py` 日銀 / `nowcast2.py` 経産省・財務省
- 大きな元データ（ICIO等）はリポジトリに含めない。各スクリプト冒頭の引数を参照。

## 開発
```
npm install
python3 scripts/build_site.py && npm run build:css
npx serve site   # または python3 -m http.server -d site
```
## テスト
```
pip install pytest playwright && playwright install chromium
python3 scripts/build_site.py && pytest tests/
```
全ページのJSエラー、内部リンク、sitemap、フロー図ボタン、近さの地図、グラフ描画を確認します。PRごとに GitHub Actions（`.github/workflows/test.yml`）でも実行されます。

## デプロイ
Cloudflare（Workers 静的アセット、商用可）: Build command `npm install && npm run build:css`、Deploy command `npx wrangler deploy`（公開フォルダは `wrangler.jsonc` で `site`）。Vercel Hobbyは非商用のみ。

## 出典・ライセンス
データ出典：総務省ほか「産業連関表」、経済産業省「延長産業連関表」「第3次産業活動指数」、財務省「貿易統計」、日本銀行、OECD ICIO（政府統計の総合窓口 e-Stat）。本リポジトリの数値・図は筆者による加工物で、政府が作成したものではありません。ストーリーは筆者の仮説です。
