"""site/*.html を生成。explorer は ../io/out の成果物(または data/ にコピー済みのもの)から取り込む。"""
import re,sys,pathlib,shutil
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from _shell import HEAD,FOOT,FONTS
R=pathlib.Path(__file__).resolve().parent.parent; S=R/"site"
def page(name,title,desc,body):
    (S/name).write_text(HEAD.format(title=title,desc=desc)+body+FOOT,encoding="utf-8")
# ---------- index
page("index.html","経済の地図帳｜産業のつながりを眺める","日本の産業連関表から、お金の流れと産業どうしのつながりを眺める趣味の分析サイト",'''
<main class="flex-1">
<section class="hero py-16 bg-gradient-to-b from-primary/20 to-transparent"><div class="hero-content text-center max-w-3xl flex-col">
 <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight">経済を、一枚の地図で。</h1>
 <p class="py-4 text-base-content/80">37の産業と、その間を流れるお金。円をクリックすると中身へ、線をクリックすると「その取引は何のためか」の仮説へ。<br>公的統計（産業連関表）を趣味で眺めて、見えにくい産業のつながりを探しています。</p>
 <div class="flex gap-3 flex-wrap justify-center"><a class="btn btn-primary" href="explorer.html">産業マップを開く →</a><a class="btn btn-outline" href="about.html">方法と出典</a></div>
</div></section>
<section class="max-w-5xl mx-auto px-4 grid gap-4 sm:grid-cols-3">
 <div class="card bg-base-100 border border-base-300"><div class="card-body"><h2 class="card-title">俯瞰する</h2><p>37部門の取引をネットワークとフロー図で表示。2020年の規模と、2020→2022の変化を切り替えられます。</p></div></div>
 <div class="card bg-base-100 border border-base-300"><div class="card-body"><h2 class="card-title">掘り下げる</h2><p>部門→108の小分類→取引の相手先へ。上位の取引には、人が読める「ストーリー」を付けています。</p></div></div>
 <div class="card bg-base-100 border border-base-300"><div class="card-body"><h2 class="card-title">仮説を探す</h2><p>地図では目立たないが、伸びていて他産業を支える「裏方」グループ（ブルーオーシャン候補）を試算しています。</p></div></div>
</section>
<section class="max-w-5xl mx-auto px-4 mt-10"><div role="alert" class="alert alert-warning"><span><b>ご注意：</b>ストーリー・グループは筆者の<b>仮説</b>で、統計から確定できる事実ではありません。2022年値は延長産業連関表（推計表）で、基本表とは定義が異なります。</span></div></section>
</main>''')
# ---------- about
page("about.html","方法と出典｜経済の地図帳","データの出典、加工方法、制約と免責",'''
<main class="flex-1 max-w-3xl mx-auto px-4 py-10 prose-sm sm:prose-base space-y-6">
<h1 class="text-3xl font-bold">方法と出典</h1>
<section><h2 class="text-xl font-bold mb-2">データ</h2><ul class="list-disc pl-6 space-y-1">
<li>産業連関表（基本表）2011・2015・2020年、接続産業連関表（2011-2015-2020）：総務省ほか</li>
<li>延長産業連関表（2020年基準、2021・2022年）：経済産業省</li>
<li>いずれも <a class="link" href="https://www.e-stat.go.jp/" target="_blank" rel="noopener">政府統計の総合窓口（e-Stat）</a> 掲載。</li></ul></section>
<section><h2 class="text-xl font-bold mb-2">加工について</h2><ul class="list-disc pl-6 space-y-1">
<li>本サイトの数値・図は、上記統計を筆者が集約・換算・再計算したもので、<b>政府が作成したものではありません</b>。</li>
<li>108部門を37部門に集約。延長表（97部門）は対応表により37部門へ対応づけ。</li>
<li>金額は兆円表示。実質値と名目値を区別し、価格変化＝名目÷実質で試算。</li>
<li>「ブルーオーシャン」スコアは、成長率・他産業への波及・地図上の目立たなさ（筆者が業界地図の目次から判断）による簡易指標です。</li></ul></section>
<section><h2 class="text-xl font-bold mb-2">制約</h2><ul class="list-disc pl-6 space-y-1">
<li>2022年値は推計表で、サービス間取引の構造は特に粗いです。定義の違いから2020年基本表と完全には接続しません。</li>
<li>2023年以降（生成AIの普及など）は反映していません。</li>
<li>ストーリーには確度ラベル（A/B/C）を付けていますが、いずれも仮説です。</li></ul></section>
<section><h2 class="text-xl font-bold mb-2">免責</h2><p>本サイトは個人の趣味による分析で、投資・経営・その他の判断を助言するものではありません。内容の正確性は保証しません。</p></section>
<section><h2 class="text-xl font-bold mb-2">ソフトウェア</h2><p class="text-sm">Tailwind CSS（MIT）、daisyUI（MIT）、3d-force-graph（MIT）を使用。コードは GitHub で管理しています。</p></section>
</main>''')
# ---------- explorer
src=R.parent/"io"/"out"/"industry_explorer.html"
if not src.exists(): src=S/"explorer.html"
h=src.read_text(encoding="utf-8")
h=h.replace("https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.4/dist/3d-force-graph.min.js","vendor/3d-force-graph.min.js")
if "<!doctype" not in h.lower():
    h='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'+h
    h=h.replace("</style>","</style></head><body>",1)
h=h.replace("<title>产业</title>","")
h=h.replace("<title>産業マップ</title>","<title>産業マップ｜経済の地図帳</title>"+FONTS,1)
nav='<div class="topbar"><a class="brand" href="index.html">経済の地図帳</a><span class="sp"></span><a href="explorer.html">産業マップ</a><a href="about.html">方法と出典</a><button id="thm" aria-label="テーマ切替">◐</button></div><script>document.getElementById("thm").onclick=function(){var t=document.documentElement.dataset.theme==="nord"?"night":"nord";document.documentElement.dataset.theme=t;try{localStorage.setItem("theme",t)}catch(e){}}</script>'
foot='<footer style="font:12px system-ui;padding:10px 12px;opacity:.7">出典：総務省ほか「産業連関表」、経産省「延長産業連関表」（e-Stat）を筆者が加工。ストーリーは筆者の仮説であり、政府が作成したものではありません。</footer>'
h=h.replace("<h1>産業マップ</h1>",nav+"<h1>産業マップ</h1>",1)
if "</html>" not in h: h+=foot+"</body></html>"

TOK='''
:root[data-theme="night"]{--bg:#0b1120;--panel:#0f172a;--panel2:#16213a;--fg:#e2e8f0;--muted:#94a3b8;--line:#1e293b;--accent:#38bdf8;--up:#38bdf8;--flat:#64748b;--down:#fb923c;--graph:#070c18;--label:#e2e8f0;--chip:#1e293b;color-scheme:dark}
:root[data-theme="nord"]{--bg:#e5e9f0;--panel:#ffffff;--panel2:#eceff4;--fg:#2e3440;--muted:#5b6578;--line:#d8dee9;--accent:#5e81ac;--up:#3b6fb0;--flat:#8d94a3;--down:#c8501f;--graph:#eceff4;--label:#2e3440;--chip:#d8dee9;color-scheme:light}
.topbar{display:flex;align-items:center;gap:14px;margin:-14px -16px 12px;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
.topbar a{color:var(--fg);text-decoration:none;font-size:13px}.topbar a.brand{font-weight:700;font-size:16px}.topbar .sp{flex:1}
.topbar button{background:none;border:0;color:var(--fg);cursor:pointer;font-size:16px}
'''
h=h.replace("*{box-sizing:border-box}",TOK+"*{box-sizing:border-box}",1)
h=h.replace("<title>",'<script>try{var t=localStorage.getItem("theme");if(t!=="nord")t="night";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="night"}</script><title>',1)
(S/"explorer.html").write_text(h,encoding="utf-8")
