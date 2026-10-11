"""産業ごとの個別ページ(108産業・37部門)と産業一覧を生成する。 build_site.py から呼ばれる。
文章はデータからの機械的な生成で、事実(数値)のみ。解釈は既存の『ストーリー(仮説)』を転記し、仮説と明記する。"""
import json,html,pathlib,re
import pandas as pd
R=pathlib.Path(__file__).resolve().parent.parent; D=R/"data"
rd=lambda f,**k:pd.read_csv(D/f,encoding="utf-8-sig",**k)
esc=html.escape
def short(n): return re.sub(r"^（続き）","",re.sub(r"（[^）]*(別掲|除く)[^）]*）","",n))          # 『（別掲を除く。）』などの注記を外す
def tril(x): return f"{x/1000:.1f}" if x>=100 else f"{x/1000:.2f}"          # 10億円→兆円
def pct(x,d=0): return f"{x*100:.{d}f}%"
def sg(x,d=1): return ("+" if x>=0 else "−")+f"{abs(x):.{d}f}"

def load():
    nd=rd("nodes.csv",dtype={"code":str}); n108=nd[nd.level==108].set_index("code"); n37=nd[nd.level==37].set_index("code")
    ed=rd("edges.csv"); ed=ed[(ed.level==108)&(ed.type=="SUPPLIES")]
    ts=rd("sector_timeseries_108.csv",dtype={"code":str}).set_index("code")
    an=rd("analysis_108.csv",dtype={"code":str}).set_index("code")
    rk=rd("blue_ocean_ranking_108.csv",dtype={"code":str}).set_index("code")
    ex=json.loads((D/"explorer_data.json").read_text(encoding="utf-8")); sim=json.loads((D/"similarity_map.json").read_text(encoding="utf-8"))
    return dict(n108=n108,n37=n37,ed=ed,ts=ts,an=an,rk=rk,ex=ex,sim=sim)

def link(code,name): return f'<a class="link link-primary" href="industry/{code}.html">{esc(short(name))}</a>'

def stacked(parts):
    """parts=[(label,share,color)] を横積み棒(inline SVG)で。"""
    W=640;x=0;s=f'<svg viewBox="0 0 {W} 70" width="100%" role="img" aria-label="行き先の構成" style="font-size:11px">'
    for lab,sh,c in parts:
        w=W*sh
        if w<0.5: continue
        s+=f'<rect x="{x:.1f}" y="6" width="{w:.1f}" height="26" fill="{c}"/>'
        if w>46: s+=f'<text x="{x+w/2:.1f}" y="23" text-anchor="middle" fill="#0b1120" font-weight="700">{sh*100:.0f}%</text>'
        x+=w
    x=0;ly=[48,62]
    for i,(lab,sh,c) in enumerate(p for p in parts if p[1]>=0.005):
        s+=f'<rect x="{(i%3)*215}" y="{40+(i//3)*16}" width="9" height="9" fill="{c}"/><text x="{(i%3)*215+13}" y="{48+(i//3)*16}" fill="currentColor">{lab} {sh*100:.0f}%</text>'
    return s+'</svg>'

def bars(vals,labels,color):
    W,H=320,120;mx=max(vals);bw=W/len(vals);s=f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:360px;font-size:11px" role="img" aria-label="実質産出額の推移">'
    for i,(v,l) in enumerate(zip(vals,labels)):
        h=(H-34)*v/mx;x=i*bw+bw*.2
        s+=f'<rect x="{x:.1f}" y="{H-22-h:.1f}" width="{bw*.6:.1f}" height="{h:.1f}" fill="{color}" rx="2"/><text x="{x+bw*.3:.1f}" y="{H-22-h-4:.1f}" text-anchor="middle" fill="currentColor">{v/1000:.1f}</text><text x="{x+bw*.3:.1f}" y="{H-6}" text-anchor="middle" fill="currentColor" opacity=".7">{l}</text>'
    return s+'</svg>'

def table(rows,heads):
    t='<div class="overflow-x-auto"><table class="table table-sm"><thead><tr>'+"".join(f'<th{" class=\"text-right\"" if i else ""}>{h}</th>' for i,h in enumerate(heads))+'</tr></thead><tbody>'
    for r in rows: t+='<tr>'+"".join(f'<td{" class=\"text-right\"" if i else ""}>{c}</td>' for i,c in enumerate(r))+'</tr>'
    return t+'</tbody></table></div>'

def build(page,S,PAL,SITE_URL):
    L=load(); n108,n37,ed,ts,an,rk,ex,sim=(L[k] for k in ("n108","n37","ed","ts","an","rk","ex","sim"))
    gnames=ex["groups"]; N37={x["id"]:x for x in ex["nodes"]}; grp_of37={k:v["grp"] for k,v in N37.items()}
    GC=PAL["groups"]; tot=float(n108.output.sum())
    names={c:r["name"] for c,r in n108.iterrows()}; code_of={short(v):k for k,v in names.items()}
    simn={x["c"]:x for x in sim["nodes"]}; bo=sim["groups"]
    boc={c:g for g,v in bo.items() for c in v["codes"]}
    (S/"industry").mkdir(exist_ok=True)
    out_pages=[]
    kids_of={}
    for c,r in n108.iterrows():
        g_=float(ts.loc[c].real_cagr_2015_2020)*100 if c in ts.index else None
        kids_of.setdefault("%02d"%int(r.parent37),[]).append(dict(c=c,n=r["name"],o=float(r.output)/1000,g=g_))
    for v in kids_of.values(): v.sort(key=lambda x:-x["o"])
    # ---------- 108産業ページ
    for code,r in n108.iterrows():
        sid="S108_"+code; nm=short(r["name"]); out=float(r.output); p37="%02d"%int(r.parent37); a=an.loc[code]; t=ts.loc[code] if code in ts.index else None
        sell=ed[(ed.src==sid)&(ed.dst!=sid)].sort_values("amount",ascending=False).head(6)
        buy=ed[(ed.dst==sid)&(ed.src!=sid)].sort_values("amount",ascending=False).head(6)
        nsell=lambda i:names[i[5:]]
        srows=[[link(i[5:],names[i[5:]]),tril(v),pct(sh,1)] for i,v,sh in zip(sell.dst,sell.amount,sell.share_of_seller_sales)]
        brows=[[link(i[5:],names[i[5:]]),tril(v),pct(sh,1)] for i,v,sh in zip(buy.src,buy.amount,buy.share_of_buyer_cost)]
        selfsh=ed[(ed.src==sid)&(ed.dst==sid)].share_of_seller_sales
        # 行き先の構成
        row=n108.loc[code]; f=lambda c:float(row.get(c,0) or 0)
        parts_raw=[("他産業の材料・サービス",f("intermediate_sales"),"#38bdf8"),("家計消費",f("fd_民間消費")+f("fd_家計外消費"),"#34d399"),("設備投資・在庫",f("fd_民間固定資本形成")+f("fd_在庫純増"),"#f59e0b"),("政府（消費・公共投資）",f("fd_政府消費")+f("fd_政府消費(社会資本等減耗分)")+f("fd_公的固定資本形成"),"#a78bfa"),("輸出",f("fd_輸出"),"#ef4444")]
        pos=[(l,max(v,0),c) for l,v,c in parts_raw]; sm=sum(v for _,v,_ in pos) or 1; parts=[(l,v/sm,c) for l,v,c in pos]
        top=max(parts,key=lambda x:x[1])
        g=float(t.real_cagr_2015_2020)*100 if t is not None else None; g2=float(t.real_cagr_2011_2015)*100 if t is not None else None
        wsh=out/tot
        neigh=[(code_of.get(x),x) for x in simn[code]["nb"]]
        sib=[(c,names[c]) for c in n108.index if "%02d"%int(n108.loc[c].parent37)==p37 and c!=code]
        trend=(f'<section class="space-y-2"><h2 class="text-xl font-bold">規模の推移（実質、兆円）</h2><div class="card bg-base-100 border border-base-300"><div class="card-body p-3">{bars([float(t.output_r11),float(t.output_r15),float(t.output_n20)],["2011年","2015年","2020年"],PAL["c"]["sky"])}</div></div><p class="text-sm text-base-content/70">2011→2015年は年{sg(g2)}%、2015→2020年は年{sg(g)}%（いずれも実質、2020年価格）。</p></section>') if t is not None else ""
        bo_html=""
        if code in boc:
            gg=boc[code]; bo_html=f'<section class="space-y-2"><h2 class="text-xl font-bold">ブルーオーシャン候補グループの構成部門</h2><p class="text-sm text-base-content/80">筆者の仮説で、この産業は「{esc(bo[gg]["name"])}」（{gg}）の構成部門としています。くわしくは<a class="link" href="similarity.html">近さの地図</a>を参照してください。</p></section>'
        facts=f'{nm}は、{esc(n37.loc[p37,"name"])}部門に含まれる産業です。2020年の産出額は{tril(out)}兆円（国内の産出額全体の{wsh*100:.1f}%）、{('2015年から2020年の実質成長は年'+sg(g)+'%') if g is not None else '2011年・2015年に対応する産業がなく、成長率は算出していません'}でした。主な販売先は{"・".join(esc(short(names[i[5:]])) for i in sell.dst[:3])}、主な仕入れ先は{"・".join(esc(short(names[i[5:]])) for i in buy.src[:3])}です。'
        desc=re.sub(r"<[^>]+>","",html.unescape(facts))[:150]
        body=f'''<main class="flex-1 w-full max-w-4xl mx-auto px-4 py-10 space-y-8">
<nav class="text-sm breadcrumbs"><ul><li><a href="industries.html">産業一覧</a></li><li><a href="industry/{p37}.html">{esc(n37.loc[p37,"name"])}</a></li><li>{esc(nm)}</li></ul></nav>
<header class="space-y-3"><h1 class="text-3xl font-bold">{esc(nm)}の取引先・規模・成長</h1><p class="text-base-content/80">{facts}</p></header>
<section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">産出額（2020年）</span><b class="text-xl">{tril(out)}兆円</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">実質成長（2015→20年）</span><b class="text-xl">{(sg(g)+"%/年") if g is not None else "データなし"}</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">付加価値率</span><b class="text-xl">{pct(float(a["付加価値率"]))}</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">輸入依存度</span><b class="text-xl">{pct(float(a["輸入依存度"]))}</b></div></div></section>
<section class="space-y-2"><h2 class="text-xl font-bold">この産業の製品・サービスの行き先</h2><div class="card bg-base-100 border border-base-300"><div class="card-body p-3">{stacked(parts)}</div></div><p class="text-sm text-base-content/70">最大は「{top[0]}」で{top[1]*100:.0f}%。同じ産業内の取引は売上の{pct(float(selfsh.iloc[0]) if len(selfsh) else 0,1)}です。</p></section>
<section class="space-y-2"><h2 class="text-xl font-bold">主な販売先</h2>{table(srows,["販売先の産業","金額（兆円）","売上に占める割合"])}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">主な仕入れ先</h2>{table(brows,["仕入れ先の産業","金額（兆円）","費用に占める割合"])}</section>
{trend}
{bo_html}
<section class="space-y-2"><h2 class="text-xl font-bold">取引の相手が似ている産業</h2><p class="text-sm text-base-content/70">仕入れ先・販売先の構成が近い産業です（<a class="link" href="similarity.html">近さの地図</a>と同じ計算）。</p><ul class="list-disc pl-6 text-sm">{"".join(f"<li>{link(c,names[c])}</li>" for c,_ in neigh if c)}</ul></section>
<section class="space-y-2"><h2 class="text-xl font-bold">同じ部門の産業</h2><p class="text-sm">{"、".join(link(c,n) for c,n in sib) or "なし"}</p></section>
<p class="text-xs text-base-content/60">出典：総務省ほか「産業連関表」（2011・2015・2020年、108部門）を筆者が集計。成長率は接続産業連関表による実質値。政府が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p>
</main>'''
        ld='<base href="/">'+'<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"産業一覧","item":SITE_URL+"/industries"},{"@type":"ListItem","position":2,"name":str(n37.loc[p37,"name"]),"item":f"{SITE_URL}/industry/{p37}"},{"@type":"ListItem","position":3,"name":nm}]},ensure_ascii=False)+"</script>"
        page(f"industry/{code}.html",f"{nm}の取引先・規模・成長｜Keizai Atlas",desc,body,ld); out_pages.append(f"industry/{code}")
    # ---------- 37部門ページ
    edges37=ex["edges"]
    for nid,n in N37.items():
        nm=n["name"]; subs=kids_of.get(nid,[])
        sell=sorted([e for e in edges37 if e["s"]==nid and e["t"]!=nid and e.get("v")],key=lambda e:-e["v"])[:6]; buy=sorted([e for e in edges37 if e["t"]==nid and e["s"]!=nid and e.get("v")],key=lambda e:-e["v"])[:6]
        l37=lambda i:f'<a class="link link-primary" href="industry/{i}.html">{esc(N37[i]["name"])}</a>'
        def stories(es,own):
            h=""
            for e in es:
                if e.get("story"):
                    other=e["t"] if own=="s" else e["s"]
                    h+=f'<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-1"><b>{esc(N37[e["s"]]["name"])} → {esc(N37[e["t"]]["name"])}（{e["v"]:.1f}兆円）<span class="badge badge-outline badge-sm ml-2">確度{esc(e["conf"])}</span></b><p class="text-sm">{esc(e["story"])}</p><p class="text-xs text-base-content/60">根拠の目安：{esc(e.get("ver",""))}</p></div></div>'
            return h
        sto=stories(sell,"s")+stories(buy,"t")
        srow=[[l37(e["t"]),f'{e["v"]:.1f}',f'{e["v"]/n["out"]*100:.1f}%'] for e in sell]
        brow=[[l37(e["s"]),f'{e["v"]:.1f}',f'{e["v"]/n["out"]*100:.1f}%'] for e in buy]
        facts=f'{nm}は、日本の産業を37に分けた部門の1つで、2020年の産出額は{n["out"]:.1f}兆円、2011年から2020年の実質成長は年{sg(n["cagr"])}%でした。付加価値率は{n["va"]:.0f}%、輸出向けは{n["exp"]:.0f}%、家計消費向けは{n["cons"]:.0f}%、輸入依存度は{n["imp"]:.0f}%です。'
        gname=gnames[n["grp"]]
        body=f'''<main class="flex-1 w-full max-w-4xl mx-auto px-4 py-10 space-y-8">
<nav class="text-sm breadcrumbs"><ul><li><a href="industries.html">産業一覧</a></li><li>{esc(gname)}</li><li>{esc(nm)}</li></ul></nav>
<header class="space-y-3"><h1 class="text-3xl font-bold">{esc(nm)}（37部門）の取引先・規模・成長</h1><p class="text-base-content/80">{esc(facts)}</p></header>
<section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">産出額（2020年）</span><b class="text-xl">{n["out"]:.1f}兆円</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">実質成長（2011→20年）</span><b class="text-xl">{sg(n["cagr"])}%/年</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">付加価値率</span><b class="text-xl">{n["va"]:.0f}%</b></div></div>
<div class="card bg-base-100 border border-base-300"><div class="card-body p-4 gap-0"><span class="text-xs text-base-content/60">輸入依存度</span><b class="text-xl">{n["imp"]:.0f}%</b></div></div></section>
<section class="space-y-2"><h2 class="text-xl font-bold">含まれる産業（108産業）</h2>{table([[link(s["c"],s["n"]),f'{s["o"]:.2f}',(sg(s["g"])+"%") if s["g"] is not None else "−"] for s in subs],["産業","産出額（兆円）","実質成長（2015→20年/年）"])}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">主な販売先</h2>{table(srow,["販売先の部門","金額（兆円）","売上に占める割合"])}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">主な仕入れ先</h2>{table(brow,["仕入れ先の部門","金額（兆円）","費用に占める割合"])}</section>
{('<section class="space-y-2"><h2 class="text-xl font-bold">取引のストーリー（筆者の仮説）</h2><p class="text-sm text-base-content/70">主な取引のうち、背景を読み解いたもの。統計から確定できる事実ではありません。</p>'+sto+'</section>') if sto else ""}
<p class="text-sm"><a class="btn btn-sm btn-outline" href="explorer.html">産業マップで見る →</a></p>
<p class="text-xs text-base-content/60">出典：総務省ほか「産業連関表」（2011・2015・2020年）、経済産業省「延長産業連関表」を筆者が集計。政府が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p>
</main>'''
        ld='<base href="/">'+'<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"産業一覧","item":SITE_URL+"/industries"},{"@type":"ListItem","position":2,"name":nm}]},ensure_ascii=False)+"</script>"
        page(f"industry/{nid}.html",f"{nm}（37部門）の取引先・規模・成長｜Keizai Atlas",f"{nm}（37部門の1つ）の2020年の産出額は{n['out']:.1f}兆円。主な販売先・仕入れ先、含まれる産業、取引の背景（仮説）。",body,ld); out_pages.append(f"industry/{nid}")
    # ---------- 産業一覧
    sec=""
    for gi,gn in enumerate(gnames):
        ids=[i for i,n in N37.items() if n["grp"]==gi]
        sec+=f'<section class="space-y-2"><h2 class="text-xl font-bold flex items-center gap-2"><i style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{GC[gi]}"></i>{esc(gn)}</h2>'
        for i in sorted(ids,key=lambda i:-N37[i]["out"]):
            kids=kids_of.get(i,[])
            sec+=f'<div class="pl-2"><p><a class="link link-primary font-bold" href="industry/{i}.html">{esc(N37[i]["name"])}</a> <span class="text-xs text-base-content/60">{(f"{N37[i][chr(111)+chr(117)+chr(116)]:.1f}" if N37[i]["out"]<10 else f"{N37[i][chr(111)+chr(117)+chr(116)]:.0f}")}兆円</span></p><p class="text-sm pl-4 text-base-content/80">'+"、".join(f'<a class="link" href="industry/{s["c"]}.html">{esc(short(s["n"]))}</a>' for s in kids)+'</p></div>'
        sec+='</section>'
    body=f'''<main class="flex-1 w-full max-w-4xl mx-auto px-4 py-10 space-y-6"><header class="space-y-3"><h1 class="text-3xl font-bold">産業一覧</h1><p class="text-base-content/80">日本の産業を、8つの大分類・37の部門・108の産業に分けて、それぞれの規模と取引先を見られます。名前をクリックすると、その産業のページに移ります。数字は2020年の産業連関表です。</p></header>{sec}</main>'''
    page("industries.html","産業一覧（37部門・108産業）｜Keizai Atlas","日本の産業を8つの大分類・37部門・108産業に分けて、規模と取引先を見られる一覧。",body,'<base href="/">' if False else "")
    return out_pages+["industries"]
