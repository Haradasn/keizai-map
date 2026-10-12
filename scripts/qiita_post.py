"""Qiita に記事を投稿・更新する(GitHub Actions から実行)。
  QIITA_TOKEN: Qiita の個人用アクセストークン(write_qiita)
  python3 scripts/qiita_post.py create            -> 限定共有で新規投稿(IDとURLは /tmp/qiita_state.json に書く)
  python3 scripts/qiita_post.py update <id> <private:true|false>  -> 本文を更新(false で全体に公開)
記事: docs/qiita/article.md(本文)と docs/qiita/meta.json(タイトル・タグ)。URLは公開ログに出さない(限定共有のため)。
"""
import json,os,sys,urllib.request,pathlib
R=pathlib.Path(__file__).resolve().parent.parent
tok=os.environ["QIITA_TOKEN"].strip()
meta=json.loads((R/"docs/qiita/meta.json").read_text(encoding="utf-8")); body=(R/"docs/qiita/article.md").read_text(encoding="utf-8")
def call(method,path,data):
    req=urllib.request.Request("https://qiita.com/api/v2"+path,method=method,data=json.dumps(data).encode(),
        headers={"Authorization":"Bearer "+tok,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        print("::error::Qiita API",e.code,e.read()[:300].decode("utf-8","replace")); sys.exit(1)
act=sys.argv[1]
if act=="stats":                                   # 閲覧数・いいね・ストックを読む(自分の記事だけ page_views_count が取れる)
    it=json.load(urllib.request.urlopen(urllib.request.Request("https://qiita.com/api/v2/items/"+sys.argv[2],headers={"Authorization":"Bearer "+tok}),timeout=60))
    pathlib.Path("/tmp/qiita_stats.json").write_text(json.dumps({k:it.get(k) for k in ("page_views_count","likes_count","stocks_count","comments_count","url")},ensure_ascii=False))
    print("::notice::Qiita 統計を取得"); sys.exit(0)
if act=="create":
    it=call("POST","/items",dict(title=meta["title"],body=body,tags=meta["tags"],private=True))
elif act=="update":
    it=call("PATCH","/items/"+sys.argv[2],dict(title=meta["title"],body=body,tags=meta["tags"],private=sys.argv[3]=="true"))
else: sys.exit("create か update")
pathlib.Path("/tmp/qiita_state.json").write_text(json.dumps({"id":it["id"],"url":it["url"],"private":it["private"],"updated_at":it["updated_at"]},ensure_ascii=False))
print("::notice::Qiita 投稿OK(private=%s)"%it["private"])
