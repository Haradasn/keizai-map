# Keizai Atlas (https://keizai-atlas.com) — 作業メモ

日本の産業連関表を中心にした、趣味の統計分析サイト。静的サイト(Python で生成 → `site/`)を Cloudflare Workers の静的アセットで配信。費用ゼロ運用が前提(有料サービスは入れない)。

## 構成
- ディレクトリ: `scripts/build/`(サイト生成。build_site / build_industry / build_pref / build_geo / build_ogp / derive / _shell / _tpl ほか)、`scripts/ops/`(運用。weekly_report / qiita_post / uptime_check / visual_diff / check_data / add_changelog / fetch_latest.sh / run_all.sh / pref_pages.txt / pref_files.txt)、`pipeline/`(データ生成)、`pages/`(ページ本文と JS)、`templates/`(Jinja2 のひな形)、`tests/`(`conftest.py` に共通のサーバー・ブラウザ、`test_static` / `test_browser` / `test_a11y` / `test_data`)。
- `scripts/build/build_site.py` が全ページを生成。ページ本文は `pages/*.html` + `pages/meta.json`、数値は `{{key}}` で `scripts/build/derive.py` が `data/*.json` から計算。
- HTML のひな形: `templates/*.j2`(Jinja2。共通の殻は `base.html.j2`、部品は `_macros.html.j2` / `_charts.html.j2`)。Python は表示する値(整形済みの文字列・座標)を用意して `scripts/build/_tpl.py` の `render()` を呼ぶだけ。テンプレートは読み込み時に行頭・行末の空白と改行を詰める(行末の `⏎` で改行、行頭の `|` で空白を残す)ので、インデントして書いてよい。自動エスケープはしないので、信頼できない文字列には `|esc` を付ける。出力を変えたら `lastmod.json` が動くので注意。
- 産業ページ: `scripts/build/build_industry.py`(108産業+37部門)。県別: `scripts/build/build_pref.py`(データは `pipeline/pref_build.py` → `data/pref_37.json`)。
- データ生成: `pipeline/*.py`(`scripts/ops/run_all.sh`)。生データは `raw/`(gitignore)、県別の原本は `pref_raw/`(コミット済み、出典は `pref_raw/SOURCES.json`)。
- CSS は Tailwind+daisyUI を `npm run build:css` で `site/assets.css` にビルドし、**コミットする**(CI が最新かを検査)。HTML に新しいクラスを足したら必ず再ビルド。
- 共有画像(OGP)は `scripts/build/build_ogp.py`(Noto Sans CJK 必要)。CIでは実行しない。データが変わったら `build_site.py` → `build_ogp.py` の順に実行して `site/og*` をコミット。
- トップ(`pages/index.html`): 発見のカルーセル(`pages/insights.js` → `site/insights.js`)。スライドの数値は `{{...}}`、県別は `pref-map-data.js`、つながりは `net-mini.js`(build_site が出力)から JS で計算。
- 3D: 県の立体地図は `pages/prefmap.js`(`data-prefmap="hero|page"`、トップは沖縄・奄美をはめ込み表示)。境界 `site/vendor/japan-pref.json` は地球地図日本(国土地理院)を `scripts/build/build_geo.py` で簡略化(非営利・出典明記が条件)。ライブラリは `site/vendor/` に同梱(MapLibre GL JS、3d-force-graph)。CDN は使わない。
- 産業マップ: `pipeline/explorer_template.html` を build_site が共通シェルに入れて出力。`explorer.html?sel=66` で産業を選んだ状態で開く。
- 読者の反応: 各ページ下の「👍」「こんな情報が欲しい」(`pages/feedback.js`、欄は `templates/_feedback.html.j2`、描画は `scripts/build/_shell.py`。`pages/feedback.json` の Turnstile sitekey が空なら出さない)。送信先は `worker/index.js`(`/api/like`, `/api/request`, `/api/feedback/export`)→ D1 `keizai-feedback`。Worker の秘密値 TURNSTILE_SECRET と FEEDBACK_KEY は Cloudflare ダッシュボードで設定。週次レポートが FEEDBACK_KEY で読み出して集計。Turnstile の読み込みだけは外部スクリプト(入力欄を開いたときだけ)。
- 円安ページ(`pages/fx.html`): 輸入物価(日銀 cgpi_m_jp.csv → `pipeline/fx_import.py` → `data/fx_chart.json`、monthly-update で更新)と、2020年表の輸入品の含有率(`pipeline/import_content.py` → `data/import_content_37.json`)。
- 堅牢化(すべて無料の範囲): `site/_headers` で CSP などを付与(テストのサーバーも同じヘッダーで動き、CSP 違反を検出。外部から読むものを足したら CSP も更新)。Worker は本文 4KB 上限・連投制限(`ratelimits`)・👍の1日上限。`scripts/ops/check_data.py`(data/ の形の検査と前回比較。CI と月次更新)。テストに axe-core のアクセシビリティ検査(両テーマ)とページの重さの上限。`npm run typecheck`(checkJs、グローバルは `types/globals.d.ts`)。PR の見た目の差分は `visual-diff.yml`。死活監視は `uptime.yml`(3時間ごと、問題があれば Issue)。Dependabot・CodeQL。障害時の手順と秘密値の一覧は `docs/RUNBOOK.md`。
- 更新履歴/RSS: `pages/changelog.json`(`scripts/ops/add_changelog.py`)。ページや機能を足したら1件追記。

## 作業ルール
- `main` へ直接 push しない。ブランチ → PR → CI の `smoke` が成功 → マージ(マージはこちらで進めてよい、と許可済み)。**マージはスカッシュ**: `gh api -X PUT repos/Haradasn/keizai-map/pulls/N/merge -f merge_method=squash -f commit_title="..." -f commit_message="...Co-Authored-By/Claude-Session の行"`(GitHubが署名するので Verified になる。マージコミットは Unverified 表示になるため使わない)。
- 整形: Python は ruff(`ruff format . && ruff check --fix .`、設定は pyproject.toml)、JS/テンプレートは prettier(`npm run format`)。CI が整形済みかを検査する(未整形だと失敗)。1行に詰め込まず、読みやすさを優先する。
- ビルドは `npm run build`(build_site.py でページ生成 → 出力HTMLを prettier で整形。script/style の中身は整形しない)。
- テストは必須: `npm run build && python3 -m pytest tests -q`(約3分。ツールの2分制限を超えるので、ローカルでは `setsid nohup ... &` で回して結果を待つ。axe-core が node_modules に無いときは `AXE_PATH` で指定)。CI は `site/` と `pages/lastmod.json` がビルド結果と一致するかも検査するので、ビルドし直した成果物を必ずコミットする。
- 文章: 事実(統計から確定できること)と、筆者の推測は分ける。推測には「仮説」と明記。政府が作成・保証したものではない旨を保つ。投資判断に使えるような書き方をしない。
- 数値は手書きしない。生成物の文章中の数値は `{{...}}` かデータから生成。県別は需給バランス・費用側の検証(assert)を通すこと。
- ユーザーは日本語。報告は簡潔に、結論から。

- 確認: 画面の変更は Playwright で 1280px と 390px のスクリーンショットを撮って目で確認(WebGL は `--use-gl=swiftshader` で描ける)。サーバーは PID を控えて kill する(`pkill -f` は自分のシェルも止める)。
- 実装の分担: 仕様が決まったコード実装はサブエージェント(Sonnet)に任せ、見た目の確認・手直し・マージ判断はこちらで行うと安い。

## 落とし穴
- 政府サイトはサンドボックスから取れない。取得は GitHub Actions の `pref-fetch`(手動実行、`scripts/ops/pref_pages.txt` / `pref_files.txt` を読み、結果を `pref-scratch` ブランチに置く)か、`monthly-update` の `fetch_latest.sh`。経産省は UA と Referer が必要。
- GitHub の API でブランチ保護は設定できない(Ruleset はユーザーが手動設定)。Actions のログは読めない → アノテーション API を使う。
- `GITHUB_TOKEN` で作った PR は workflow を起動しないため、`monthly-update` は `test.yml` を `workflow_dispatch` で起動している。
- SVG には `hidden` プロパティがない(`toggleAttribute`)。flex 列で `mx-auto` を使うと幅が min-content になる(`w-full` を併用)。
- 産業ページは `<base href="/">`。Cloudflare は `.html` を外した URL が正。
- 県の表は形式がバラバラ。37部門ベースなら `SOURCES.json` に列位置を書けば追加できる。合算が必要なもの(沖縄=397部門、北海道=独自38部門、兵庫・福岡=39部門)は個別処理がある。

## 未対応・候補
薄い文字は `text-base-content/70` 以上(それ未満はコントラスト不足でテストが落ちる)。アクセス解析は Cloudflare Web Analytics を導入済み(2026-10、ユーザーが設定)。週次レポート: `.github/workflows/weekly-report.yml` が毎週月曜8時に `scripts/ops/weekly_report.py` を実行し、非公開リポジトリ `keizai-atlas-reports` に保存 → そちらの `post-issue` が Issue にして通知。Secrets: CF_API_TOKEN, CF_ACCOUNT_ID, GSC_SA_JSON, REPORT_TOKEN(1年で期限切れ)。公開リポジトリなのでレポートの数値はログに出さない。Ruleset の「PR 必須」の再設定、残り23県(PDFのみの県の扱い)、用語集への内部リンクの拡充、スマホ実機での表示速度の確認。
