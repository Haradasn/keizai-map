"""site/*.html を生成。explorer は ../io/out の成果物(または data/ にコピー済みのもの)から取り込む。"""
import re,sys,pathlib,shutil,json
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from _shell import HEAD,FOOT,FONTS,seo
from site_config import SITE_URL,SITE_NAME
from derive import metrics,render
MET=metrics()
R=pathlib.Path(__file__).resolve().parent.parent; S=R/"site"
def page(name,title,desc,body,extra=""):
    path=name[:-5]
    ld=""
    if path=="index": ld='<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"WebSite","name":SITE_NAME,"url":SITE_URL+"/","inLanguage":"ja","description":desc},ensure_ascii=False)+"</script>"
    S_=seo(path,title,desc,SITE_URL,SITE_NAME,ld+extra)
    (S/name).write_text(HEAD.format(title=title,desc=desc,seo=S_)+body+FOOT,encoding="utf-8")
# ---------- 共通: 色パレットと共通グラフJS
PAL=json.loads((R/"pages"/"palette.json").read_text(encoding="utf-8"))
(S/"charts.js").write_text("var KA={pal:"+json.dumps(PAL,ensure_ascii=False)+"};\n"+(R/"pages"/"charts.js").read_text(encoding="utf-8"),encoding="utf-8")
# ---------- 通常ページ: pages/<name>.html(本文) + pages/meta.json(title/desc/埋め込みデータ)
META=json.loads((R/"pages"/"meta.json").read_text(encoding="utf-8"))
for name,m in META.items():
    body=(R/"pages"/f"{name}.html").read_text(encoding="utf-8")
    for ph,f in m.get("data",{}).items(): body=body.replace(ph,(R/"data"/f).read_text(encoding="utf-8"))
    page(f"{name}.html",m["title"],m["desc"],"\n"+render(body,MET))
# ---------- 個別産業ページと産業一覧
from build_industry import build as build_industry
IND=build_industry(page,S,PAL,SITE_URL)
# ---------- explorer
tpl=(R/"pipeline"/"explorer_template.html").read_text(encoding="utf-8")
h=tpl.replace("__GC__",json.dumps(PAL["groups"])).replace("__DATA__",(R/"data"/"explorer_data.json").read_text(encoding="utf-8"))
h=h.replace("https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.4/dist/3d-force-graph.min.js","vendor/3d-force-graph.min.js")
if "<!doctype" not in h.lower():
    h='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'+h
    h=h.replace("</style>","</style></head><body>",1)
h=h.replace("<title>产业</title>","")
ED="日本の37産業の取引を3Dネットワークで眺め、ドリルダウンで中身と仮説を読める産業連関表エクスプローラ"
h=h.replace("<title>産業マップ</title>","<title>産業マップ｜Keizai Atlas</title><meta name=\"description\" content=\""+ED+"\">"+seo("explorer","産業マップ｜Keizai Atlas",ED,SITE_URL,SITE_NAME)+FONTS,1)
nav='<div class="topbar"><a class="brand" href="index.html">Keizai Atlas</a><span class="sp"></span><span class="links"><a href="explorer.html">産業マップ</a><a href="industries.html">産業一覧</a><a href="similarity.html">近さの地図</a><a href="latest.html">最新動向</a><a href="international.html">国際比較</a><a href="about.html">方法と出典</a></span><details class="mnav"><summary aria-label="メニュー">☰</summary><div class="mmenu"><a href="explorer.html">産業マップ</a><a href="industries.html">産業一覧</a><a href="similarity.html">近さの地図</a><a href="latest.html">最新動向</a><a href="international.html">国際比較</a><a href="about.html">方法と出典</a></div></details><button id="thm" aria-label="テーマ切替">◐</button></div><script>document.getElementById("thm").onclick=function(){var t=document.documentElement.dataset.theme==="nord"?"night":"nord";document.documentElement.dataset.theme=t;try{localStorage.setItem("theme",t)}catch(e){}}</script>'
foot='<footer style="font:12px system-ui;padding:10px 12px;opacity:.7">出典：総務省ほか「産業連関表」、経産省「延長産業連関表」（e-Stat）を筆者が加工。ストーリーは筆者の仮説であり、政府が作成したものではありません。</footer>'
h=h.replace("<h1>産業マップ</h1>",nav+"<h1>産業マップ</h1>",1)
if "</html>" not in h: h+=foot+"</body></html>"

def _tok(k,t):return ":root[data-theme=\"%s\"]{"%k+";".join(f"--{n}:{v}" for n,v in t.items() if n!="scheme")+";color-scheme:%s}"%t["scheme"]
TOK="\n"+"\n".join(_tok(k,t) for k,t in PAL["theme"].items())+"""
.topbar{display:flex;align-items:center;gap:14px;margin:-14px -16px 12px;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
.topbar a{color:var(--fg);text-decoration:none;font-size:13px}.topbar a.brand{font-weight:700;font-size:16px}.topbar .sp{flex:1}
.topbar button{background:none;border:0;color:var(--fg);cursor:pointer;font-size:16px}
.topbar .links{display:flex;gap:14px}.mnav{display:none;position:relative}.mnav summary{list-style:none;cursor:pointer;font-size:18px;padding:0 6px}.mnav summary::-webkit-details-marker{display:none}
.mmenu{position:absolute;right:0;top:130%;z-index:50;display:flex;flex-direction:column;gap:2px;min-width:160px;padding:6px;background:var(--panel);border:1px solid var(--line);border-radius:6px;box-shadow:0 6px 20px rgba(0,0,0,.35)}.mmenu a{padding:8px 10px;border-radius:4px}.mmenu a:hover{background:var(--chip)}
@media(max-width:1023px){.topbar .links{display:none}.mnav{display:block}}
"""
h=h.replace("*{box-sizing:border-box}",TOK+"*{box-sizing:border-box}",1)
h=h.replace("<title>",'<script>try{var t=localStorage.getItem("theme");if(t!=="nord")t="night";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="night"}</script><title>',1)
(S/"explorer.html").write_text(h,encoding="utf-8")

(S/"robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",encoding="utf-8")
import datetime,hashlib
# lastmod: ページ内容のハッシュが変わった日だけ更新(pages/lastmod.json に記録)。変更が無ければ何日ビルドしても同じ。
LM_F=R/"pages"/"lastmod.json"; LM=json.loads(LM_F.read_text(encoding="utf-8")) if LM_F.exists() else {}
today=datetime.date.today().isoformat(); urls=[]
for p in ("/","/explorer","/similarity","/latest","/international","/about","/industries")+tuple("/"+x for x in IND if x!="industries"):
    f=S/(("index" if p=="/" else p[1:])+".html"); hsh=hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    if LM.get(p,{}).get("hash")!=hsh: LM[p]={"hash":hsh,"date":today}
    urls.append(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{LM[p]['date']}</lastmod></url>\n")
LM_F.write_text(json.dumps(LM,indent=1,ensure_ascii=False)+"\n",encoding="utf-8")
(S/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"".join(urls)+"</urlset>\n",encoding="utf-8")
