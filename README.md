# 経済の地図帳（趣味の統計分析サイト）

産業連関表から産業間のお金の流れを可視化する静的サイト。公開物は `site/` のみ（サーバー不要）。

## 構成
- `site/` 公開ディレクトリ（index / explorer / about、`assets.css`、`vendor/` に3d-force-graph同梱）
- `scripts/build_site.py` HTML生成（`pip`不要）、`npm run build:css` でTailwind+daisyUIをビルド
- `pipeline/` データ加工スクリプト（元データはe-Statから取得。パスは各スクリプト冒頭を参照）
- `data/` 加工済みCSV/JSON

## 開発
```
npm install
python3 scripts/build_site.py && npm run build:css
npx serve site   # または python3 -m http.server -d site
```
## デプロイ
Cloudflare Pages（推奨・商用可）: Build command `npm run build:css`、出力ディレクトリ `site`。Vercel Hobbyは非商用のみ。

## 出典・ライセンス
データ出典：総務省ほか「産業連関表」、経済産業省「延長産業連関表」（政府統計の総合窓口 e-Stat）。本リポジトリの数値・図は筆者による加工物で、政府が作成したものではありません。ストーリーは筆者の仮説です。
