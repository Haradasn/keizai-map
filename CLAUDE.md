# Keizai Atlas (https://keizai-atlas.com) — 作業メモ

日本の産業連関表を中心にした、趣味の統計分析サイト。静的サイト(Python で生成 → `site/`)を Cloudflare Workers の静的アセットで配信。費用ゼロ運用が前提(有料サービスは入れない)。

## 構成
- `scripts/build_site.py` が全ページを生成。ページ本文は `pages/*.html` + `pages/meta.json`、数値は `{{key}}` で `scripts/derive.py` が `data/*.json` から計算。
- 産業ページ: `scripts/build_industry.py`(108産業+37部門)。県別: `scripts/build_pref.py`(データは `pipeline/pref_build.py` → `data/pref_37.json`)。
- データ生成: `pipeline/*.py`(`scripts/run_all.sh`)。生データは `raw/`(gitignore)、県別の原本は `pref_raw/`(コミット済み、出典は `pref_raw/SOURCES.json`)。
- CSS は Tailwind+daisyUI を `npm run build:css` で `site/assets.css` にビルドし、**コミットする**(CI が最新かを検査)。HTML に新しいクラスを足したら必ず再ビルド。
- 共有画像(OGP)は `scripts/build_ogp.py`(Noto Sans CJK 必要)。CIでは実行しない。データが変わったら `build_site.py` → `build_ogp.py` の順に実行して `site/og*` をコミット。
- 更新履歴/RSS: `pages/changelog.json`(`scripts/add_changelog.py`)。ページや機能を足したら1件追記。

## 作業ルール
- `main` へ直接 push しない。ブランチ → PR → CI の `smoke` が成功 → マージ(マージはこちらで進めてよい、と許可済み)。
- テストは必須: `python3 scripts/build_site.py && python3 -m pytest tests -q`(約1分)。CI は `site/` と `pages/lastmod.json` がビルド結果と一致するかも検査するので、ビルドし直した成果物を必ずコミットする。
- 文章: 事実(統計から確定できること)と、筆者の推測は分ける。推測には「仮説」と明記。政府が作成・保証したものではない旨を保つ。投資判断に使えるような書き方をしない。
- 数値は手書きしない。生成物の文章中の数値は `{{...}}` かデータから生成。県別は需給バランス・費用側の検証(assert)を通すこと。
- ユーザーは日本語。報告は簡潔に、結論から。

## 落とし穴
- 政府サイトはサンドボックスから取れない。取得は GitHub Actions の `pref-fetch`(手動実行、`scripts/pref_pages.txt` / `pref_files.txt` を読み、結果を `pref-scratch` ブランチに置く)か、`monthly-update` の `fetch_latest.sh`。経産省は UA と Referer が必要。
- GitHub の API でブランチ保護は設定できない(Ruleset はユーザーが手動設定)。Actions のログは読めない → アノテーション API を使う。
- `GITHUB_TOKEN` で作った PR は workflow を起動しないため、`monthly-update` は `test.yml` を `workflow_dispatch` で起動している。
- SVG には `hidden` プロパティがない(`toggleAttribute`)。flex 列で `mx-auto` を使うと幅が min-content になる(`w-full` を併用)。
- 産業ページは `<base href="/">`。Cloudflare は `.html` を外した URL が正。
- 県の表は形式がバラバラ。37部門ベースなら `SOURCES.json` に列位置を書けば追加できる。合算が必要なもの(沖縄=397部門、北海道=独自38部門、兵庫・福岡=39部門)は個別処理がある。

## 未対応・候補
Search Console の確認、アクセス解析(未導入)、Ruleset の「PR 必須」の再設定、他の都道府県、用語集への内部リンクの拡充。
