"""site/*.html を生成。explorer は ../io/out の成果物(または data/ にコピー済みのもの)から取り込む。"""
import re,sys,pathlib,shutil,json
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from _shell import HEAD,FOOT,FONTS,seo
from site_config import SITE_URL,SITE_NAME
R=pathlib.Path(__file__).resolve().parent.parent; S=R/"site"
def page(name,title,desc,body):
    path=name[:-5]
    ld=""
    if path=="index": ld='<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"WebSite","name":SITE_NAME,"url":SITE_URL+"/","inLanguage":"ja","description":desc},ensure_ascii=False)+"</script>"
    S_=seo(path,title,desc,SITE_URL,SITE_NAME,ld)
    (S/name).write_text(HEAD.format(title=title,desc=desc,seo=S_)+body+FOOT,encoding="utf-8")
# ---------- index
page("index.html","Keizai Atlas｜日本経済の産業のつながりを眺める地図帳","日本の産業連関表から、お金の流れと産業どうしのつながりを眺める趣味の分析サイト",'''
<main class="flex-1">
<section class="hero py-16 bg-gradient-to-b from-primary/20 to-transparent"><div class="hero-content text-center max-w-3xl flex-col">
 <p class="badge badge-outline">趣味の統計分析 · 産業連関表</p><h1 class="text-4xl sm:text-5xl font-bold tracking-tight">Keizai Atlas<br><span class="text-2xl sm:text-3xl font-medium text-base-content/80">経済を、一枚の地図で。</span></h1>
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
page("about.html","方法と出典｜Keizai Atlas","データの出典、加工方法、制約と免責",'''
<main class="flex-1 max-w-3xl mx-auto px-4 py-10 prose-sm sm:prose-base space-y-6">
<h1 class="text-3xl font-bold">方法と出典</h1>
<section><h2 class="text-xl font-bold mb-2">データ</h2><ul class="list-disc pl-6 space-y-1">
<li>産業連関表（基本表）2011・2015・2020年、接続産業連関表（2011-2015-2020）：総務省ほか</li>
<li>延長産業連関表（2020年基準、2021・2022年）：経済産業省</li>
<li>最新動向：日本銀行 時系列統計データ検索サイト（企業向けサービス価格指数、企業物価指数、国際収支統計）</li>
<li>国際比較：OECD Inter-Country Input-Output (ICIO) Tables 2025 edition（regular ICIO、2016〜2022年）</li>
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

import json as _j
_icio=(R/"data"/"icio_chart.json").read_text(encoding="utf-8")
page("international.html","国際比較｜Keizai Atlas","OECD国際産業連関表(ICIO)で、日米中独韓の外注・デジタル・エネルギーの仕入れ構成を比べる",'''
<main class="flex-1 max-w-5xl mx-auto px-4 py-10 space-y-10">
<header class="space-y-3"><h1 class="text-3xl font-bold">国際比較：日・米・中・独・韓</h1>
<p class="text-base-content/80">OECD の国際産業連関表（ICIO 2025年版、2016〜2022年）から、各国の産業が「何を仕入れているか」を比べます。指標は<b>中間投入（原材料・サービスの仕入れ）全体に占める割合</b>です。輸入分も含みます。</p>
<div role="alert" class="alert alert-warning"><span>日本の表（総務省の産業連関表）とは部門の切り方が違うため、数値は国内版と一致しません。解釈は筆者の仮説です。</span></div></header>
<section class="space-y-3"><h2 class="text-2xl font-bold">1. 外注（専門・事業支援サービス）</h2>
<p class="text-base-content/80">専門・科学技術サービス（法務・会計・コンサル・研究開発・広告など）と、事業支援サービス（人材派遣・警備・清掃・レンタルなど）の仕入れ比率。</p>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><div id="c-out"></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り:</b> 米国は約20%、ドイツ約16%に対し、日本は8〜9%、韓国も同水準、中国は5〜6%です。日本は「外注にお金が流れる国」とは言えず、国内版で大きく見える対事業所サービスは、ICIOでは定義が狭いために小さく出ている可能性があります（仮説）。</p></section>
<section class="space-y-3"><h2 class="text-2xl font-bold">2. デジタル（情報通信・情報サービス）</h2>
<p class="text-base-content/80">出版・放送、通信、情報サービス（IT・クラウド等）の仕入れ比率と、そのうち輸入の比率。</p>
<div class="grid gap-4 md:grid-cols-2"><div class="card bg-base-100 border border-base-300"><div class="card-body"><h3 class="font-bold">仕入れに占める割合（%）</h3><div id="c-dig"></div></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><h3 class="font-bold">そのうち輸入の割合（%）</h3><div id="c-digimp"></div></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り:</b> 日本のデジタル仕入れ比率は2016〜2022年でほぼ横ばい（2020年は分母の縮小で一時的に高く出る）ですが、<b>輸入比率は8.7%から13.0%に上昇</b>しました。韓国・ドイツも上昇しています。海外のクラウドやソフトウェアへの支払いが増えた可能性があります（仮説）。2023年以降の生成AIの影響は、この表には入っていません。</p></section>
<section class="space-y-3"><h2 class="text-2xl font-bold">3. エネルギー（石炭・石油ガス・石油製品・電気ガス）</h2>
<div class="grid gap-4 md:grid-cols-2"><div class="card bg-base-100 border border-base-300"><div class="card-body"><h3 class="font-bold">仕入れに占める割合（%）</h3><div id="c-en"></div></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><h3 class="font-bold">そのうち輸入の割合（%）</h3><div id="c-enimp"></div></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り:</b> 2022年は、価格高騰でエネルギーの比率が各国で跳ね上がりました（日本 7.3%→11.5%、ドイツ 5.1%→8.7%、2020→2022年）。日本の輸入比率は31%→47%と急上昇し、米国（14%）・中国（15%）との差が開きました。ドイツ（35%）は日本より低い水準です。</p></section>
<section class="text-sm text-base-content/70 space-y-1"><h2 class="text-lg font-bold text-base-content">方法と注意</h2>
<ul class="list-disc pl-6"><li>出典：OECD Inter-Country Input-Output (ICIO) Tables, 2025 edition（regular ICIO）を筆者が集計。加工・解釈は筆者によるもので、OECDが作成・保証したものではありません。</li>
<li>各国の産業（50部門）の列に対する、全世界の売り手からの仕入れを合計し、部門グループごとの割合を計算しています。名目値のため、価格変動の影響を含みます。</li>
<li>2020年はコロナ禍で全体が縮み、割合が一時的に動きます。集計スクリプトは <code>pipeline/icio_agg.py</code> にあります。</li></ul></section>
</main>
<script>
(function(){
var D=__ICIO__, C=[["JPN","日本","#38bdf8",3.2],["USA","米国","#f59e0b",1.8],["CHN","中国","#ef4444",1.8],["DEU","ドイツ","#34d399",1.8],["KOR","韓国","#a78bfa",1.8]];
function chart(id,key){var el=document.getElementById(id),W=470,H=260,L=40,R=96,T=12,B=28,Y=D.years,all=[];
 C.forEach(function(c){all=all.concat(D[key][c[0]])});var mx=Math.max.apply(null,all)*1.05,cand=[1,2,2.5,5,10,20,25,50],st=1;for(var k=0;k<cand.length;k++){var q=Math.pow(10,Math.floor(Math.log10(mx/4)));var t=cand[k]*q/1;if(mx/t<=5){st=t;break}}var mxn=Math.ceil(mx/st)*st,steps=Math.round(mxn/st);
 function X(i){return L+(W-L-R)*i/(Y.length-1)} function V(v){return T+(H-T-B)*(1-v/mxn)}
 var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="'+key+' 国別推移" style="font-size:11px">';
 for(var g=0;g<=steps;g++){var v=st*g;s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+V(v)+'" y2="'+V(v)+'" stroke="currentColor" opacity=".15"/><text x="'+(L-6)+'" y="'+(V(v)+4)+'" text-anchor="end" fill="currentColor" opacity=".7">'+(Math.round(v*10)/10)+'</text>'}
 Y.forEach(function(y,i){if(i%2==0||i==Y.length-1)s+='<text x="'+X(i)+'" y="'+(H-8)+'" text-anchor="middle" fill="currentColor" opacity=".7">'+y+'</text>'});
 var ends=[];C.forEach(function(c){var a=D[key][c[0]];ends.push([c,a[a.length-1]])});ends.sort(function(a,b){return b[1]-a[1]});
 var ly={},last=-99;ends.forEach(function(e){var y=V(e[1]);if(y-last<13&&last>-99)y=last+13;ly[e[0][0]]=y;last=y});
 C.slice().reverse().forEach(function(c){var a=D[key][c[0]],pts=a.map(function(v,i){return X(i)+","+V(v)}).join(" ");
  s+='<polyline points="'+pts+'" fill="none" stroke="'+c[2]+'" stroke-width="'+c[3]+'" stroke-linejoin="round" stroke-linecap="round"/>';
  s+='<circle cx="'+X(a.length-1)+'" cy="'+V(a[a.length-1])+'" r="'+(c[3]>3?4:3)+'" fill="'+c[2]+'"/>';
  s+='<text x="'+(W-R+8)+'" y="'+(ly[c[0]]+4)+'" fill="'+c[2]+'" font-weight="'+(c[3]>3?700:500)+'">'+c[1]+" "+a[a.length-1]+'</text>'});
 el.innerHTML=s+'</svg>'}
chart("c-out","out");chart("c-dig","dig");chart("c-digimp","digimp");chart("c-en","en");chart("c-enimp","enimp");
})();
</script>
'''.replace("__ICIO__",_icio))

_now=(R/"data"/"nowcast_chart.json").read_text(encoding="utf-8")
page("latest.html","最新動向 2023-2026｜Keizai Atlas","日銀統計で、サービス価格・デジタル関連の海外支払い・エネルギー価格の2023〜2026年の動きを見る",'''
<main class="flex-1 max-w-5xl mx-auto px-4 py-10 space-y-10">
<header class="space-y-3"><h1 class="text-3xl font-bold">最新動向：2023〜2026年</h1>
<p class="text-base-content/80">産業連関表は2022年までです。その後の動きを、日本銀行の月次・四半期統計で補います（2026年8月分まで）。サービスの<b>価格</b>、デジタル関連の<b>海外への支払い</b>、エネルギーの<b>価格</b>の3つを見ます。</p>
<div role="alert" class="alert alert-warning"><span>価格指数は「量」ではなく「価格」です。解釈は筆者の仮説で、2026年の値は速報（改訂されることがあります）です。</span></div></header>
<section class="space-y-3"><h2 class="text-2xl font-bold">1. 企業向けサービスの価格（2020年=100）</h2>
<p class="text-base-content/80">企業が企業から買うサービスの価格指数（企業向けサービス価格指数）。産業マップの「対事業所サービス」「情報通信」に近い領域です。</p>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><div id="n-sppi"></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り（2022年12月→2026年8月）:</b> 総平均は103.2→115.4（+11.8%）。<b>技術サービスが+21%</b>と最も上がり、職業紹介・労働者派遣が+11.8%、情報サービスが+11.7%、通信が+8.2%、専門サービスは+3.4%でした。人手不足や、システム・設計の需要の強さが、外注の単価に表れている可能性があります（仮説）。</p></section>
<section class="space-y-3"><h2 class="text-2xl font-bold">2. デジタル関連の海外への支払い（兆円）</h2>
<p class="text-base-content/80">国際収支の「通信・コンピュータ・情報サービス」。クラウド、ソフトウェア、システム開発などへの、海外との受け払いです。</p>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><div id="n-bp"></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り:</b> 支払いは2019年の2.4兆円から2025年の4.6兆円へ<b>約1.9倍</b>。受取（0.8→2.2兆円）も増えていますが、赤字（ネット）は1.6兆円から2.4兆円に広がりました（2024年は2.6兆円で最大）。「国際比較」ページの、デジタル仕入れの輸入比率の上昇と整合します。専門・経営コンサルティングの赤字も、1.1兆円から2.5兆円に拡大しています。生成AIによる部分は、この統計からは切り分けられません。2026年は1〜8月の累計です。</p></section>
<section class="space-y-3"><h2 class="text-2xl font-bold">3. エネルギーの価格（国内企業物価、2020年=100）</h2>
<div class="card bg-base-100 border border-base-300"><div class="card-body"><div id="n-cg"></div></div></div>
<p class="text-sm text-base-content/80"><b>読み取り:</b> 電力・都市ガス・水道は、2022年12月の168.6から、2023年12月に122.2まで下がり、2026年8月は143.5です。石炭・原油・天然ガスは258.6→177.9、石油・石炭製品は2026年8月に178.5と、期間内で目立つ水準でした。産業連関表の2022年（エネルギー高騰の年）から、高止まりしつつ落ち着いたあと、再び上がっている姿です。</p></section>
<section class="text-sm text-base-content/70 space-y-1"><h2 class="text-lg font-bold text-base-content">方法と注意</h2>
<ul class="list-disc pl-6"><li>出典：日本銀行 時系列統計データ検索サイト「企業向けサービス価格指数（2020年基準）」「企業物価指数（2020年基準）」「国際収支統計」を筆者が加工。日本銀行が作成・保証したものではありません。</li>
<li>国際収支は円建ての名目値で、円安の影響を含みます。年の合計は暦年（2026年のみ1〜8月）です。</li>
<li>集計スクリプトは <code>pipeline/boj_nowcast.py</code> にあります。</li></ul></section>
</main>
<script>
(function(){
var N=__NOW__,M=N.months;
function nice(mx){var q=Math.pow(10,Math.floor(Math.log10(mx/4))),c=[1,2,2.5,5,10];for(var i=0;i<c.length;i++){if(mx/(c[i]*q)<=5)return c[i]*q}return 10*q}
function line(id,ser,opt){var el=document.getElementById(id),W=720,H=300,L=44,R=165,T=12,B=28,all=[];
 ser.forEach(function(s){all=all.concat(s.v.filter(function(x){return x!=null}))});
 var lo=Math.floor(Math.min.apply(null,all)*0.95/10)*10,hi=Math.max.apply(null,all)*1.05,st=nice(hi-lo),lo2=Math.floor(lo/st)*st,hi2=Math.ceil(hi/st)*st;
 function X(i){return L+(W-L-R)*i/(M.length-1)}function Y(v){return T+(H-T-B)*(1-(v-lo2)/(hi2-lo2))}
 var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" style="font-size:11px">';
 for(var v=lo2;v<=hi2+1e-9;v+=st){s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="currentColor" opacity=".15"/><text x="'+(L-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" fill="currentColor" opacity=".7">'+v+'</text>'}
 M.forEach(function(m,i){if(m.slice(4)=="01")s+='<text x="'+X(i)+'" y="'+(H-8)+'" text-anchor="middle" fill="currentColor" opacity=".7">'+m.slice(0,4)+'</text>'});
 var ends=ser.map(function(x){var l=x.v.length-1;while(x.v[l]==null)l--;return [x,x.v[l],l]}).sort(function(a,b){return b[1]-a[1]}),ly={},last=-99;
 ends.forEach(function(e){var y=Y(e[1]);if(last>-99&&y-last<14)y=last+14;ly[e[0].n]=y;last=y});
 if(opt&&opt.ref)s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(opt.ref)+'" y2="'+Y(opt.ref)+'" stroke="currentColor" opacity=".35" stroke-dasharray="4 4"/>';
 ser.slice().reverse().forEach(function(x){var pts=[];x.v.forEach(function(v,i){if(v!=null)pts.push(X(i)+","+Y(v))});
  s+='<polyline points="'+pts.join(" ")+'" fill="none" stroke="'+x.c+'" stroke-width="'+(x.w||2)+'" stroke-linejoin="round"/>';
  var e=ends.filter(function(q){return q[0]===x})[0];
  s+='<circle cx="'+X(e[2])+'" cy="'+Y(e[1])+'" r="3.5" fill="'+x.c+'"/><text x="'+(W-R+8)+'" y="'+(ly[x.n]+4)+'" fill="'+x.c+'" font-weight="'+((x.w||2)>2?700:500)+'">'+x.n+" "+e[1]+'</text>'});
 el.innerHTML=s+'</svg>'}
line("n-sppi",[{n:"技術サービス",v:N.sppi["技術サービス"],c:"#f59e0b"},{n:"労働者派遣",v:N.sppi["職業紹介・労働者派遣サービス"],c:"#34d399"},{n:"情報サービス",v:N.sppi["情報サービス"],c:"#38bdf8",w:3.2},{n:"総平均",v:N.sppi["総平均"],c:"#94a3b8"},{n:"通信",v:N.sppi["通信"],c:"#a78bfa"},{n:"専門サービス",v:N.sppi["専門サービス"],c:"#ef4444"}],{ref:100});
line("n-cg",[{n:"石炭・原油・天然ガス",v:N.cgpi["石炭・原油・天然ガス"],c:"#f59e0b"},{n:"石油・石炭製品",v:N.cgpi["石油・石炭製品"],c:"#ef4444"},{n:"電力・ガス・水道",v:N.cgpi["電力・都市ガス・水道"],c:"#38bdf8",w:3.2}],{ref:100});
(function(){var el=document.getElementById("n-bp"),B=N.bp,ys=Object.keys(B.digital_pay),W=720,H=300,L=44,R=20,T=24,Bt=34,mx=5,bw=(W-L-R)/ys.length;
 function Y(v){return T+(H-T-Bt)*(1-v/mx)}
 var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" style="font-size:11px">';
 for(var v=0;v<=mx;v++)s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="currentColor" opacity=".15"/><text x="'+(L-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" fill="currentColor" opacity=".7">'+v+'</text>';
 ys.forEach(function(y,i){var x0=L+i*bw+bw*0.14,w=bw*0.34,part=B.digital_pay[y][1]<12,p=B.digital_pay[y][0],r=B.digital_rec[y][0],n=B.digital_net[y][0];
  s+='<rect x="'+x0+'" y="'+Y(p)+'" width="'+w+'" height="'+(Y(0)-Y(p))+'" fill="#f59e0b" opacity="'+(part?.5:1)+'" rx="2"/><rect x="'+(x0+w+3)+'" y="'+Y(r)+'" width="'+w+'" height="'+(Y(0)-Y(r))+'" fill="#38bdf8" opacity="'+(part?.5:1)+'" rx="2"/>';
  s+='<text x="'+(x0+w/2)+'" y="'+(Y(p)-4)+'" text-anchor="middle" fill="#f59e0b">'+p.toFixed(1)+'</text><text x="'+(x0+w*1.5+3)+'" y="'+(Y(r)-4)+'" text-anchor="middle" fill="#38bdf8">'+r.toFixed(1)+'</text>';
  s+='<text x="'+(L+i*bw+bw/2)+'" y="'+(H-16)+'" text-anchor="middle" fill="currentColor" opacity=".8">'+y+(part?"(1-8月)":"")+'</text><text x="'+(L+i*bw+bw/2)+'" y="'+(H-3)+'" text-anchor="middle" fill="currentColor" opacity=".6">差 '+n.toFixed(1)+'</text>'});
 s+='<rect x="'+(W-190)+'" y="2" width="10" height="10" fill="#f59e0b"/><text x="'+(W-176)+'" y="11" fill="currentColor">支払</text><rect x="'+(W-130)+'" y="2" width="10" height="10" fill="#38bdf8"/><text x="'+(W-116)+'" y="11" fill="currentColor">受取</text>';
 el.innerHTML=s+'</svg>'})();
})();
</script>
'''.replace("__NOW__",_now))
# ---------- explorer
tpl=(R/"pipeline"/"explorer_template.html").read_text(encoding="utf-8")
h=tpl.replace("__DATA__",(R/"data"/"explorer_data.json").read_text(encoding="utf-8"))
h=h.replace("https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.4/dist/3d-force-graph.min.js","vendor/3d-force-graph.min.js")
if "<!doctype" not in h.lower():
    h='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'+h
    h=h.replace("</style>","</style></head><body>",1)
h=h.replace("<title>产业</title>","")
ED="日本の37産業の取引を3Dネットワークで眺め、ドリルダウンで中身と仮説を読める産業連関表エクスプローラ"
h=h.replace("<title>産業マップ</title>","<title>産業マップ｜Keizai Atlas</title><meta name=\"description\" content=\""+ED+"\">"+seo("explorer","産業マップ｜Keizai Atlas",ED,SITE_URL,SITE_NAME)+FONTS,1)
nav='<div class="topbar"><a class="brand" href="index.html">Keizai Atlas</a><span class="sp"></span><a href="explorer.html">産業マップ</a><a href="about.html">方法と出典</a><button id="thm" aria-label="テーマ切替">◐</button></div><script>document.getElementById("thm").onclick=function(){var t=document.documentElement.dataset.theme==="nord"?"night":"nord";document.documentElement.dataset.theme=t;try{localStorage.setItem("theme",t)}catch(e){}}</script>'
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

(S/"robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",encoding="utf-8")
import datetime
T=datetime.date.today().isoformat()
(S/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"".join(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{T}</lastmod></url>\n" for p in ("/","/explorer","/latest","/international","/about"))+"</urlset>\n",encoding="utf-8")
