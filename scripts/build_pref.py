"""都道府県ページ(/prefectures, /prefecture/<slug>)を生成する。 data/pref_37.json は pipeline/pref_build.py の出力。
数値は各県が公表した2020年の産業連関表(統合大分類・37部門ベース)を、そのまま集計したもの。"""
import json,html,pathlib
from build_industry import table,esc,pct
R=pathlib.Path(__file__).resolve().parent.parent
def tril(x): return f"{x/1e6:.1f}"
def lqbars(items):
    """特化係数(全国=1)の横棒。items=[(name,lq)]"""
    W=640;L=170;mx=max(max(v for _,v in items),1.5);bw=W-L-50;H=26*len(items)+8
    s=f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="特化係数の上位の産業" style="font-size:12px">'
    x1=L+bw*1/mx; s+=f'<line x1="{x1:.1f}" y1="0" x2="{x1:.1f}" y2="{H}" stroke="currentColor" stroke-opacity=".4" stroke-dasharray="3 3"/>'
    for i,(n,v) in enumerate(items):
        y=4+i*26; w=bw*v/mx
        s+=f'<text x="{L-8}" y="{y+15}" text-anchor="end" fill="currentColor">{esc(n)}</text><rect x="{L}" y="{y+3}" width="{w:.1f}" height="16" rx="2" fill="#38bdf8"/><text x="{L+w+6:.1f}" y="{y+16}" fill="currentColor">{v:.2f}</text>'
    return s+'</svg>'

JIS={"hokkaido":1,"tochigi":9,"gunma":10,"saitama":11,"chiba":12,"tokyo":13,"kanagawa":14,"niigata":15,"toyama":16,"fukui":18,"yamanashi":19,"mie":24,"shiga":25,"kyoto":26,"osaka":27,"hyogo":28,"wakayama":30,"tottori":31,"okayama":33,"fukuoka":40,"kumamoto":43,"kagoshima":46,"okinawa":47,"aichi":23}
MAPJS=r"""(function(){
var DATA=window.PREF_MAP, INDS=DATA.inds, P=DATA.prefs, sel=document.getElementById('pm-ind'), box=document.getElementById('pm-map'), list=document.getElementById('pm-list'), note=document.getElementById('pm-note');
function ok(){try{var c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){return false}}
if(!ok()||!window.maplibregl){box.innerHTML='<p class="p-6 text-sm">この環境では3D地図を表示できません。下の一覧をご覧ください。</p>';}
var map=null,geo=null;
function lerp(a,b,t){return Math.round(a+(b-a)*t)}
function col(lq){ // 特化係数: 1未満はくすんだ灰青、1を超えると濃い青緑へ
  if(lq==null)return '#cbd5e1'; var t=Math.max(0,Math.min(1,(lq-0.5)/3.5));
  var A=[203,213,225],B=[14,116,144]; return 'rgb('+lerp(A[0],B[0],t)+','+lerp(A[1],B[1],t)+','+lerp(A[2],B[2],t)+')';}
function values(k){ // 県ごと{h:産出額(兆円), lq, name}
  var out={};Object.keys(P).forEach(function(id){var p=P[id],v=null,lq=null;
    if(k==='all'){v=p.t;lq=null;}else{var s=p.s[k];if(s){v=s[0];lq=s[1];}}
    out[id]={name:p.n,slug:p.g,v:v,lq:lq,va:p.va};});return out;}
function render(){
  var k=sel.value,V=values(k),mx=0;Object.keys(V).forEach(function(i){if(V[i].v>mx)mx=V[i].v;});
  var rows=[];
  geo.features.forEach(function(f){var d=V[f.properties.id],has=d&&d.v!=null;
    f.properties.h=has?Math.sqrt(d.v/mx)*260000:3000; f.properties.c=has?(k==='all'?col(1+(d.va-0.4)*12):col(d.lq)):'#e2e8f0';
    if(d&&has)rows.push(d);});
  if(map&&map.getSource('pref'))map.getSource('pref').setData(geo);
  rows.sort(function(a,b){return b.v-a.v});
  var nm=k==='all'?'総産出額':INDS[k];
  list.innerHTML='<caption class="text-left text-sm font-bold pb-2">'+nm+'（産出額の大きい順）</caption><thead><tr><th>都道府県</th><th class="text-right">産出額（兆円）</th><th class="text-right">'+(k==='all'?'付加価値率':'特化係数')+'</th></tr></thead><tbody>'+rows.map(function(d){return '<tr><td><a class="link" href="prefecture/'+d.slug+'.html">'+d.name+'</a></td><td class="text-right">'+d.v.toFixed(2)+'</td><td class="text-right">'+(k==='all'?(d.va*100).toFixed(1)+'%':(d.lq==null?'−':d.lq.toFixed(2)))+'</td></tr>'}).join('')+'</tbody>';
  note.textContent=k==='all'?'高さ＝総産出額、色＝付加価値率（濃いほど高い）。':'高さ＝その産業の産出額、色＝特化係数（濃いほど全国平均より集中）。灰色はデータなし、または部門を合算していて比べられない県です。';
}
fetch('vendor/japan-pref.json').then(function(r){return r.json()}).then(function(g){geo=g;
  if(map===null&&window.maplibregl&&ok()){
    var cv=document.createElement('canvas');cv.width=cv.height=1;var cx=cv.getContext('2d');cx.fillStyle=getComputedStyle(document.body).backgroundColor;cx.fillRect(0,0,1,1);var px=cx.getImageData(0,0,1,1).data,bg='rgb('+px[0]+','+px[1]+','+px[2]+')';   // oklch等はMapLibreが読めないのでRGBに直す
    map=new maplibregl.Map({container:box,style:{version:8,sources:{},layers:[{id:'bg',type:'background',paint:{'background-color':bg}}]},center:[137.5,37.2],zoom:window.innerWidth<640?3.6:4.6,pitch:45,bearing:-12,minZoom:2.5,maxZoom:8,attributionControl:{compact:true,customAttribution:'境界: 地球地図日本(国土地理院)'}});
    map.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');
    map.on('load',function(){map.addSource('pref',{type:'geojson',data:geo});
      map.addLayer({id:'ext',type:'fill-extrusion',source:'pref',paint:{'fill-extrusion-color':['get','c'],'fill-extrusion-height':['get','h'],'fill-extrusion-base':0,'fill-extrusion-opacity':0.92}});
      var pop=new maplibregl.Popup({closeButton:false,closeOnClick:false});
      map.on('mousemove','ext',function(e){var f=e.features[0],V=values(sel.value)[f.properties.id];if(!V)return;map.getCanvas().style.cursor='pointer';
        pop.setLngLat(e.lngLat).setHTML('<b>'+f.properties.name+'</b><br>'+(V.v==null?'データなし':'産出額 '+V.v.toFixed(2)+'兆円'+(V.lq!=null?'<br>特化係数 '+V.lq.toFixed(2):''))).addTo(map);});
      map.on('mouseleave','ext',function(){map.getCanvas().style.cursor='';pop.remove();});
      map.on('click','ext',function(e){var V=values(sel.value)[e.features[0].properties.id];if(V)location.href='prefecture/'+V.slug+'.html';});
      render();});
  }
  render();});
sel.addEventListener('change',render);
document.getElementById('pm-flat').addEventListener('click',function(){if(map)map.easeTo({pitch:0,bearing:0,duration:600});});
document.getElementById('pm-tilt').addEventListener('click',function(){if(map)map.easeTo({pitch:45,bearing:-12,duration:600});});
})();"""
def build_map(page,D):
    nat=json.loads((R/"data"/"explorer_data.json").read_text(encoding="utf-8"))["nodes"]
    inds={n["id"]:n["name"] for n in nat if n["id"] not in ("69",)}
    prefs={}
    for k,p in D.items():
        s={}
        for o in p["sectors"]:
            if o["c"]=="HQ" or len(o.get("nat_codes",[o["c"]]))!=1: continue      # 本社(東京のみ)と、北海道の合算部門は除く
            s[o.get("nat_codes",[o["c"]])[0]]=[round(o["out"]/1e6,4),(round(o["lq"],3) if o["lq"] else None)]
        prefs[JIS[k]]=dict(n=p["name"],g=k,t=round(p["total_out"]/1e6,3),va=round(p["total_va"]/p["total_out"],3),s=s)
    opts='<option value="all">すべての産業（総産出額）</option>'+"".join(f'<option value="{c}">{esc(n)}</option>' for c,n in inds.items())
    body=f"""<main class="flex-1 w-full max-w-5xl mx-auto px-4 py-10 space-y-6">
<header class="space-y-2"><h1 class="text-3xl font-bold">県別の産業を立体地図で見る</h1><p class="text-base-content/80">産業を選ぶと、その産業の産出額が大きい県ほど高く立ち上がります。色は<a class="link" href="glossary.html#tokka-keisu">特化係数</a>（全国より集中している産業ほど濃い色）です。ドラッグで回転、右ボタンまたは2本指で傾き、ホイールで拡大できます。県をクリックすると詳細ページに進みます。</p></header>
<div class="flex flex-wrap gap-2 items-center"><label class="font-bold" for="pm-ind">産業</label><select id="pm-ind" class="select select-bordered select-sm max-w-full">{opts}</select><button id="pm-flat" type="button" class="btn btn-sm btn-ghost">真上から</button><button id="pm-tilt" type="button" class="btn btn-sm btn-ghost">傾ける</button></div>
<link rel="stylesheet" href="vendor/maplibre-gl.css">
<div id="pm-map" class="w-full rounded-box border border-base-300 overflow-hidden" style="height:min(72vh,640px);min-height:380px" role="img" aria-label="都道府県を産出額の高さで表した立体地図。同じ内容を下の表でも示しています"></div>
<p id="pm-note" class="text-sm text-base-content/70"></p>
<p class="text-xs text-base-content/60">高さは、見やすさのために産出額の平方根で表示しています（高さが2倍でも、産出額は4倍）。データがあるのは{len(D)}都道府県です。北海道は部門を粗くまとめているため、一部の産業では表示されません。東京都の「本社」部門は含みません。</p>
<section class="overflow-x-auto"><table id="pm-list" class="table table-sm"></table></section>
<p class="text-xs text-base-content/60">出典：各都道府県「2020年（令和2年）産業連関表」を筆者が集計。県の境界は地球地図日本（国土地理院）を簡略化したものです。政府・自治体が作成したものではありません。<a class="link" href="prefectures.html">県別の産業構造に戻る</a></p></main>
<script src="vendor/maplibre-gl.js"></script><script>window.PREF_MAP={json.dumps(dict(inds=inds,prefs=prefs),ensure_ascii=False,separators=(",",":"))};</script><script>{MAPJS}</script>"""
    page("prefecture-map.html","県別の産業を立体地図で見る｜Keizai Atlas","産業を選ぶと、その産業の産出額が大きい県が立ち上がる3D地図。色は特化係数。各都道府県の2020年産業連関表から作成。",body)
def build(page,S,SITE_URL):
    D=json.loads((R/"data"/"pref_37.json").read_text(encoding="utf-8")); (S/"prefecture").mkdir(exist_ok=True); paths=["prefectures"]
    for slug,p in D.items():
        nm=p["name"]; T=p["total_out"]; sec=p["sectors"]; ranked=sorted([o for o in sec if o["lq"] and o["share"]>=0.005],key=lambda o:-o["lq"])
        top=ranked[:8]; low=ranked[-3:][::-1]
        hq=[o for o in sec if o["c"]=="HQ"]
        rows=[]
        for o in sorted(sec,key=lambda o:-o["out"]):
            rows.append([esc(o["n"]),tril(o["out"]),pct(o["share"],1),(pct(o["nat_share"],1) if o["nat_share"] else "−"),(f'{o["lq"]:.2f}' if o["lq"] else "−"),(pct(o["va_ratio"]) if o["va_ratio"] is not None else "−"),pct(o["exp_ratio"]),(pct(o["imp_ratio"]) if o["imp_ratio"] is not None else "−")])
        facts=f'{nm}の{p["year"]}年の産出額は{tril(T)}兆円、粗付加価値は{tril(p["total_va"])}兆円です。産出額に対する移輸出（海外と他の都道府県への販売）は{pct(p["exp_total"]/T)}、移輸入（海外と他の都道府県からの購入）は{pct(p["imp_total"]/T)}でした。'
        topt="、".join(f'{o["n"]}（{o["lq"]:.1f}）' for o in top[:3])
        desc=f'{nm}の産業構造（{p["year"]}年産業連関表）。産出額{tril(T)}兆円。全国より集中している産業は{topt}。全国との比較、移輸出入の割合。'
        hqnote=(f'<p class="text-sm text-base-content/70">注：東京都の表には、全国の37部門にない「本社」部門（産出額の{pct(hq[0]["share"],1)}）があります。全国との比較では、全国の表で各産業に含まれる本社の活動との間に差が出るため、特化係数は目安として見てください。</p>' if hq else "")
        body=f'''<main class="flex-1 w-full max-w-4xl mx-auto px-4 py-10 space-y-8">
<nav class="text-sm breadcrumbs"><ul><li><a href="prefectures.html">県別の産業構造</a></li><li>{esc(nm)}</li></ul></nav>
<header class="space-y-3"><h1 class="text-3xl font-bold">{esc(nm)}の産業構造</h1><p class="text-base-content/80">{esc(facts)}</p></header>
<section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">産出額（{p["year"]}年）</span><b class="text-xl">{tril(T)}兆円</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">付加価値率</span><b class="text-xl">{pct(p["total_va"]/T)}</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">移輸出（産出額比）</span><b class="text-xl">{pct(p["exp_total"]/T)}</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">移輸入（産出額比）</span><b class="text-xl">{pct(p["imp_total"]/T)}</b></div></div></section>
<section class="space-y-2"><h2 class="text-xl font-bold">全国より集中している産業（特化係数）</h2><p class="text-sm text-base-content/70">{esc(nm)}の産出額に占める割合を、全国の割合で割った値です（<a class="link" href="glossary.html#tokka-keisu">特化係数</a>）。1より大きいほど、全国平均より{esc(nm)}に集中しています。産出額の割合が0.5%以上の産業のみ。</p><div class="card bg-base-100 border border-base-300"><div class="card-body p-3">{lqbars([(o["n"],o["lq"]) for o in top])}</div></div>
<p class="text-sm text-base-content/70">逆に、全国より少ない産業：{"、".join(f'{esc(o["n"])}（{o["lq"]:.2f}）' for o in low)}。</p>{hqnote}{('<p class="text-sm text-base-content/70">注：'+esc(p.get("note",""))+'</p>') if p.get("note") else ""}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">部門の一覧（{len(sec)}部門）</h2>{table(rows,["産業","産出額（兆円）","産出額に占める割合","全国の割合","特化係数","付加価値率","移輸出（産出額比）","移輸入（域内需要比）"])}<p class="text-xs text-base-content/60">移輸出＝輸出＋他の都道府県への移出。移輸入＝輸入＋他の都道府県からの移入。移輸入は、その産業の域内需要（中間需要と域内の最終需要の合計）に対する割合です。</p></section>
<section class="space-y-2"><h2 class="text-xl font-bold">読むときの注意</h2><ul class="list-disc pl-6 text-sm space-y-1 text-base-content/80"><li>特化係数は、産業の「集中度」の目安です。競争力や収益性を表すものではありません。</li><li>全国との比較に使う全国の値は、このサイトの{2020}年の37部門表です。県の表は各県が独自に作成しており、集計の細部は一致しない場合があります。</li><li>移輸出入には、海外との取引に加えて、他の都道府県との取引が含まれます。</li></ul></section>
<p class="text-xs text-base-content/60">出典：{esc(nm)}「{p["year"]}年（令和2年）産業連関表」の取引基本表（<a class="link" href="{p["url"]}" rel="noopener">公表ページ</a>）を筆者が集計。政府・自治体が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p>
</main>'''
        ld='<base href="/">'+'<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"県別の産業構造","item":SITE_URL+"/prefectures"},{"@type":"ListItem","position":2,"name":nm}]},ensure_ascii=False)+"</script>"
        page(f"prefecture/{slug}.html",f"{nm}の産業構造・得意な産業｜Keizai Atlas",desc,body,ld); paths.append(f"prefecture/{slug}")
    cards="".join(f'<a href="prefecture/{k}.html" class="card bg-base-100 border border-base-300 hover:border-primary transition"><div class="card-body gap-1 p-5"><h3 class="font-bold">{esc(p["name"])}</h3><p class="text-sm text-base-content/80">産出額 {tril(p["total_out"])}兆円。特化: {"、".join(esc(o["n"]) for o in sorted([o for o in p["sectors"] if o["lq"] and o["share"]>=0.005],key=lambda o:-o["lq"])[:3])}</p></div></a>' for k,p in D.items())
    trs=[[f'<a class="link link-primary" href="prefecture/{k}.html">{esc(p["name"])}</a>',tril(p["total_out"]),pct(p["total_va"]/p["total_out"]),pct(p["exp_total"]/p["total_out"]),pct(p["imp_total"]/p["total_out"])] for k,p in D.items()]
    order=sorted([k for k in D if not D[k].get("coarse")],key=lambda k:-D[k]["total_out"]); nat=[n for n in json.loads((R/"data"/"explorer_data.json").read_text(encoding="utf-8"))["nodes"]]
    def cell(o):
        if not o or not o["lq"]: return '<td class="text-right">−</td>'
        lq=o["lq"]; small=o["share"]<0.005
        bg=f' style="background:rgba(56,189,248,{min(.85,(lq-1)/3.5):.2f})"' if lq>1.05 and not small else ""
        return f'<td class="text-right{" text-base-content/40" if small else ""}"{bg}>{lq:.1f}</td>'
    hm='<div class="overflow-x-auto"><table class="table table-xs"><thead><tr><th>産業</th>'+"".join(f'<th class="text-right"><a class="link" href="prefecture/{k}.html">{esc(D[k]["name"].rstrip("都府県"))}</a></th>' for k in order)+'</tr></thead><tbody>'
    for n in nat:
        hm+=f'<tr><td class="whitespace-nowrap">{esc(n["name"])}</td>'+"".join(cell(next((o for o in D[k]["sectors"] if o["c"]==n["id"]),None)) for k in order)+'</tr>'
    hm+='</tbody></table></div>'
    body=f'''<main class="flex-1 w-full max-w-4xl mx-auto px-4 py-10 space-y-8">
<header class="space-y-3"><h1 class="text-3xl font-bold">県別の産業構造</h1><p class="text-base-content/80">各都道府県が公表した2020年の産業連関表から、産業の構成を全国と比べます。現在は{len(D)}都道府県（{'・'.join(p['name'] for p in D.values())}）です。公表された表が機械で読める県から順に追加します。<a class="link link-primary" href="prefecture-map.html">3Dの立体地図</a>でも見られます。</p></header>
<section class="grid sm:grid-cols-2 gap-3">{cards}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">都道府県の比較</h2>{table(sorted(trs,key=lambda r:-float(r[1])),["都道府県","産出額（兆円）","付加価値率","移輸出（産出額比）","移輸入（産出額比）"])}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">産業×都道府県の特化係数</h2><p class="text-sm text-base-content/70">全国の割合を1としたときの、各都府県の産業の集中度です（<a class="link" href="glossary.html#tokka-keisu">特化係数</a>）。青が濃いほど、その産業が全国平均より集中しています。産出額の割合が0.5%未満の産業は、値が不安定なため色をつけていません。列は産出額の大きい順です。北海道は部門の分け方が異なるため、この表には入れていません（<a class="link" href="prefecture/hokkaido.html">北海道のページ</a>を見てください）。</p>{hm}</section>
<p class="text-xs text-base-content/60">出典：各都道府県「2020年（令和2年）産業連関表」を筆者が集計。政府・自治体が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p></main>'''
    page("prefectures.html",f"県別の産業構造（東京・愛知・大阪など{len(D)}都道府県）｜Keizai Atlas",f"{'・'.join(p['name'] for p in D.values())}の2020年産業連関表から、産業構造と全国との違い（特化係数）、移輸出入の割合を比べる。",body)
    build_map(page,D); paths.append("prefecture-map")
    return paths
