# 運用の手順書

サイトが壊れた・おかしいと気づいたときに、上から順に見る。

## 気づく仕組み

| 何を | どこで | 頻度 |
|---|---|---|
| サイトが表示されるか、API・ヘッダーが正しいか | `.github/workflows/uptime.yml`(問題があると Issue「サイトの監視で問題」が開く。直ると自動で閉じる) | 3時間ごと |
| コードの変更で壊れていないか | `test.yml` の `smoke`(PR ごと。ビルド・型チェック・データの検査・ブラウザでの表示・CSP・アクセシビリティ・ページの重さ) | PR ごと |
| 見た目がどう変わったか | `visual-diff.yml`(PR の Job Summary と Artifacts「visual-diff」) | site/ が変わる PR |
| データの取得が誤っていないか | `scripts/ops/check_data.py`(CI と月次更新。形の異常・最新月の後退は失敗、大きな改訂は警告) | PR ごと・週1 |
| 依存ライブラリの脆弱性・更新 | Dependabot(月1回 PR)、CodeQL(週1回、Security タブ) | 月1・週1 |
| アクセス数・検索・読者の反応 | 週次レポート(非公開リポジトリ `keizai-atlas-reports` の Issue) | 毎週月曜 |

## 1. サイトが表示されない・壊れた

1. 直前に何をマージしたかを見る(GitHub の main の履歴)。
2. **すぐ戻す**: Cloudflare ダッシュボード → Workers & Pages → `keizai-map` → Deployments → 1つ前の版の「Rollback」。数秒で戻る。
3. **直す**: 原因の PR を `git revert` する PR を作り、CI が通ったらマージする(main への直接 push はしない)。
4. 監視の Issue が自動で閉じることを確認する(次の監視の実行、または uptime を手動実行)。

## 2. 一部の機能だけ動かない

| 症状 | 見るところ |
|---|---|
| 3D 地図・産業マップが出ない | ブラウザのコンソールに「Content Security Policy」の違反がないか。新しく外部のものを読むなら `site/_headers` の CSP に足す(テストも同じヘッダーで動くので、PR の段階で落ちるはず) |
| 「👍」「こんな情報が欲しい」が送れない | `/api/...` が 503 → D1 の設定(wrangler.jsonc の `d1_databases`)。403 turnstile → Turnstile の sitekey(`pages/feedback.json`)と秘密値 `TURNSTILE_SECRET`。429 → 連投の制限(60 秒に 20 回、wrangler.jsonc の `ratelimits`) |
| 週次レポートが来ない | Actions の `weekly-report` の結果。「キーが使えるか確認」で落ちていれば、秘密値の期限切れ(下の表) |
| 最新動向が更新されない | Actions の `monthly-update`。データの検査で止まっていれば、注記(アノテーション)に理由が出る。政府サイトの形式変更が多い |

## 3. 秘密の値と期限

値そのものはここに書かない。どこに登録してあるかだけ。

| 名前 | 置き場所 | 用途 | 期限・更新 |
|---|---|---|---|
| `TURNSTILE_SECRET` | Cloudflare → Worker `keizai-map` → Settings → Variables and Secrets(Production) | 投稿のロボット判定 | なし |
| `FEEDBACK_KEY` | 同上 + GitHub Secrets | 反応の読み出し(週次レポート・バックアップ) | なし。漏れたら両方を同じ値で更新 |
| `CF_API_TOKEN` / `CF_ACCOUNT_ID` | GitHub Secrets | アクセス解析の取得 | トークンの TTL を設定した場合はその日 |
| `GSC_SA_JSON` | GitHub Secrets | Search Console | サービスアカウントの鍵は無期限(漏れたら Google Cloud で鍵を削除・再発行) |
| `REPORT_TOKEN` | GitHub Secrets | 非公開リポジトリへの保存 | **作成から1年(2027年10月ごろ)で切れる**。切れる前に fine-grained token を作り直して差し替える |
| `QIITA_TOKEN` | GitHub Secrets | Qiita への投稿・閲覧数の取得 | Qiita の設定による |

Cloudflare の秘密値は「Build」ではなく「Variables and Secrets(実行時)」の方に登録する(以前、ここを間違えて 401 になった)。

## 4. データ

- 読者の反応(D1 `keizai-feedback`)は、週次レポートのときに全件を `keizai-atlas-reports` の `backup/feedback.json` に保存している(git の履歴が世代管理になる)。
- 戻すときは、そのファイルから `INSERT` 文を作り、`wrangler d1 execute keizai-feedback --remote --command "..."` で入れる。
- 統計データ(`data/`)は git で管理している。誤った更新は PR を revert すれば戻る。

## 5. 手作業でしかできない設定(GitHub の画面)

- Settings → Rules → Rulesets: `main` への直接 push を禁止し、`smoke` の成功を必須にする。
- Settings → Code security: Dependabot alerts と Dependabot security updates を有効にする。
