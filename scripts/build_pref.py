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
<section class="space-y-2"><h2 class="text-xl font-bold">37部門の一覧</h2>{table(rows,["産業","産出額（兆円）","産出額に占める割合","全国の割合","特化係数","付加価値率","移輸出（産出額比）","移輸入（域内需要比）"])}<p class="text-xs text-base-content/60">移輸出＝輸出＋他の都道府県への移出。移輸入＝輸入＋他の都道府県からの移入。移輸入は、その産業の域内需要（中間需要と域内の最終需要の合計）に対する割合です。</p></section>
<section class="space-y-2"><h2 class="text-xl font-bold">読むときの注意</h2><ul class="list-disc pl-6 text-sm space-y-1 text-base-content/80"><li>特化係数は、産業の「集中度」の目安です。競争力や収益性を表すものではありません。</li><li>全国との比較に使う全国の値は、このサイトの{2020}年の37部門表です。県の表は各県が独自に作成しており、集計の細部は一致しない場合があります。</li><li>移輸出入には、海外との取引に加えて、他の都道府県との取引が含まれます。</li></ul></section>
<p class="text-xs text-base-content/60">出典：{esc(nm)}「{p["year"]}年（令和2年）産業連関表」の取引基本表（<a class="link" href="{p["url"]}" rel="noopener">公表ページ</a>）を筆者が集計。政府・自治体が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p>
</main>'''
        ld='<base href="/">'+'<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"県別の産業構造","item":SITE_URL+"/prefectures"},{"@type":"ListItem","position":2,"name":nm}]},ensure_ascii=False)+"</script>"
        page(f"prefecture/{slug}.html",f"{nm}の産業構造・得意な産業｜Keizai Atlas",desc,body,ld); paths.append(f"prefecture/{slug}")
    cards="".join(f'<a href="prefecture/{k}.html" class="card bg-base-100 border border-base-300 hover:border-primary transition"><div class="card-body gap-1 p-5"><h3 class="font-bold">{esc(p["name"])}</h3><p class="text-sm text-base-content/80">産出額 {tril(p["total_out"])}兆円。特化: {"、".join(esc(o["n"]) for o in sorted([o for o in p["sectors"] if o["lq"] and o["share"]>=0.005],key=lambda o:-o["lq"])[:3])}</p></div></a>' for k,p in D.items())
    trs=[[f'<a class="link link-primary" href="prefecture/{k}.html">{esc(p["name"])}</a>',tril(p["total_out"]),pct(p["total_va"]/p["total_out"]),pct(p["exp_total"]/p["total_out"]),pct(p["imp_total"]/p["total_out"])] for k,p in D.items()]
    order=sorted(D,key=lambda k:-D[k]["total_out"]); nat=[n for n in json.loads((R/"data"/"explorer_data.json").read_text(encoding="utf-8"))["nodes"]]
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
<header class="space-y-3"><h1 class="text-3xl font-bold">県別の産業構造</h1><p class="text-base-content/80">各都道府県が公表した2020年の産業連関表から、産業の構成を全国と比べます。現在は{len(D)}都府県（東京都・神奈川県・埼玉県・千葉県・愛知県・大阪府・兵庫県）です。順次、追加します。</p></header>
<section class="grid sm:grid-cols-2 gap-3">{cards}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">都府県の比較</h2>{table(sorted(trs,key=lambda r:-float(r[1])),["都道府県","産出額（兆円）","付加価値率","移輸出（産出額比）","移輸入（産出額比）"])}</section>
<section class="space-y-2"><h2 class="text-xl font-bold">産業×都府県の特化係数</h2><p class="text-sm text-base-content/70">全国の割合を1としたときの、各都府県の産業の集中度です（<a class="link" href="glossary.html#tokka-keisu">特化係数</a>）。青が濃いほど、その産業が全国平均より集中しています。産出額の割合が0.5%未満の産業は、値が不安定なため色をつけていません。列は産出額の大きい順です。</p>{hm}</section>
<p class="text-xs text-base-content/60">出典：各都道府県「2020年（令和2年）産業連関表」を筆者が集計。政府・自治体が作成したものではありません。<a class="link" href="about.html">方法と出典</a></p></main>'''
    page("prefectures.html","県別の産業構造（東京・愛知・大阪など7都府県）｜Keizai Atlas","東京都・神奈川県・埼玉県・千葉県・愛知県・大阪府・兵庫県の2020年産業連関表から、産業構造と全国との違い（特化係数）、移輸出入の割合を比べる。",body)
    return paths
