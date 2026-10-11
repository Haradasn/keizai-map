"""更新履歴(pages/changelog.json)の先頭に1件追加する。 使い方: python3 scripts/add_changelog.py "タイトル" "要約" /link"""
import json,sys,pathlib,datetime
p=pathlib.Path(__file__).resolve().parent.parent/"pages"/"changelog.json"
a=json.loads(p.read_text(encoding="utf-8")); t,s,l=sys.argv[1:4]
a.insert(0,{"date":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),"title":t,"summary":s,"link":l})
p.write_text(json.dumps(a,ensure_ascii=False,indent=1),encoding="utf-8")
