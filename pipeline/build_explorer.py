import pandas as pd, numpy as np, json, os
OUT="out"
r=lambda f,**k: pd.read_csv(f"{OUT}/{f}",encoding="utf-8-sig",dtype={"code":str,"seller":str,"buyer":str,"parent37":str},**k)
t37=r("sector_timeseries_37.csv"); t108=r("sector_timeseries_108.csv"); es=r("edge_stories.csv"); an=r("analysis_37.csv"); bo=r("blue_ocean_ranking_108.csv")
GROUPS=[("資源・一次産業",["01","06"]),("素材",["15","16","20","21","22","25","26","27","28"]),("食品・生活関連製造",["11","39","68"]),
 ("機械・電機・輸送機械",["29","30","31","32","33","34","35"]),("建設・エネルギー・環境",["41","46","47","48"]),
 ("流通・金融・不動産・運輸通信",["51","53","55","57","59"]),("対事業所・対個人サービス等",["66","67","65","69"]),("公務・教育・医療",["61","63","64"])]
gi={c:i for i,(_,cs) in enumerate(GROUPS) for c in cs}
BG={"663":"G1","661":"G1","481":"G1","576":"G1","577":"G1","594":"G2","593":"G2","662":"G2","591":"G2","644":"G3","643":"G3","675":"G3","552":"G3","113":"G4","221":"G4","208":"G4","281":"G4","329":"G4"}
BN={"G1":"モノの寿命を支える裏方","G2":"ネット経済の配管","G3":"ケアと公的価格の市場","G4":"素材の川上・見えない部材"}
import json as _j, networkx as nx
M97=_j.load(open("data/map97to37.json"))
X97=r("ext_sector_97.csv"); X97["p"]=X97.code.map(M97)
XA=X97.groupby("p")[["output_n2020","output_n2022","output_r2022"]].sum()
XW=pd.read_csv(f"{OUT}/ext_edges_97.csv",encoding="utf-8-sig",dtype={"seller":str,"buyer":str})
XW["sp"]=XW.seller.map(M97); XW["bp"]=XW.buyer.map(M97)
XE=XW.groupby(["sp","bp"])[["amount_2020","amount_2022"]].sum().reset_index(); XE=XE[(XE.sp!=XE.bp)]
XE["sh20"]=XE.amount_2020/XE.bp.map(XA.output_n2020)*100; XE["sh22"]=XE.amount_2022/XE.bp.map(XA.output_n2022)*100
XE["d"]=XE.amount_2022-XE.amount_2020
XEd={(a,b):x for a,b,x in zip(XE.sp,XE.bp,XE.itertuples())}
def xa(c,k):
    if c not in XA.index: return None
    r_=XA.loc[c]
    return {'o22':rnd(r_.output_n2022/1000,1),'o20x':rnd(r_.output_n2020/1000,1),'rg':rnd((r_.output_r2022/r_.output_n2020-1)*100,1),'pc':rnd((r_.output_n2022/r_.output_r2022-1)*100,1)}[k]
rnd=lambda x,n=3: None if pd.isna(x) else round(float(x),n)
an=an.set_index("code"); nodes=[]
for x in t37.itertuples():
    a=an.loc[x.code]
    subs=[]
    for s in t108[t108.parent37==x.code].sort_values("output_n20",ascending=False).itertuples():
        subs.append(dict(c=s.code,n=s.name,o=rnd(s.output_n20/1000,2),g=rnd(s.real_cagr_2011_2020*100,1),b=BG.get(s.code)))
    nodes.append(dict(id=x.code,name=x.name,grp=gi[x.code],out=rnd(x.output_n20/1000,1),
        real=[rnd(x.output_r11/1000,1),rnd(x.output_r15/1000,1),rnd(x.output_n20/1000,1)],
        cagr=rnd(x.real_cagr_2011_2020*100,1),c1=rnd(x.real_cagr_2011_2015*100,1),c2=rnd(x.real_cagr_2015_2020*100,1),
        o22=xa(x.code,'o22'),o20x=xa(x.code,'o20x'),rg=xa(x.code,'rg'),pc=xa(x.code,'pc'),va=rnd(x.va_ratio_2020*100,0),exp=rnd(x.export_ratio_2020*100,0),cons=rnd(x.consumption_ratio_2020*100,0),
        imp=rnd(a["輸入依存度"]*100,0),subs=subs))
STORY22={("06","21"):("A","原油の価格急騰(ウクライナ侵攻、円安)で、石油製品の原料費が3倍近くに。数量よりも価格の効果が大きい。ほぼ全量が輸入で、支払先の大半は海外。","原油価格と為替の推移、輸入数量(貿易統計)と突き合わせる"),
("06","46"):("A","LNG・石炭・原油の価格高騰で、電力・ガスの燃料費が3倍強に。再エネ・原発の稼働状況で数量の影響も重なる。","燃料費調整・電源構成と照らす"),
("21","57"):("A","燃油価格の上昇に加え、航空・水運の回復で使用量も増えた(2020年がコロナ禍で小さかった反動)。","運輸の部門内訳(航空・水運)で確かめる"),
("21","20"):("B","ナフサなど石油由来の原料費の上昇が、化学製品の費用を押し上げた。","石油化学系基礎製品への取引(97部門)で確かめる"),
("20","61"):("B","2022年は新型コロナワクチン等の国費購入が公務(政府消費)に計上されたと読める。2020年はほぼゼロ。","政府の医薬品購入額(予算・決算)と照らす"),
("66","59"):("B","通信・ソフト・ネット企業が、開発・運用の人手や設備を外から調達する額が増えた。ただし延長表は推計で、サービス間の取引の変化は粗い。","基本表(令和7年表)が出たら確かめる"),
("06","26"):("B","鉄鉱石・原料炭などの価格高騰で、鉄鋼の原料費が増えた。","鉄鋼の原料別(97部門)で確かめる"),
("26","28"):("B","鋼材価格の上昇が、金属製品の費用に転嫁された。","鋼材価格指数と照らす")}
E=es[(es.seller!=es.buyer)&(es.amount_2020_tril>0)].sort_values("amount_2020_tril",ascending=False).head(220)
edges=[]; seen=set()
for e in E.itertuples():
    hand=e.story_type=="手書き仮説"; x=XEd.get((e.seller,e.buyer)); seen.add((e.seller,e.buyer))
    edges.append(dict(s=e.seller,t=e.buyer,v=rnd(e.amount_2020_tril,2),sh=rnd(e.share_of_buyer_cost_pct,1),g=rnd(e.real_cagr_2011_2020_pct,1),
        p=e.purpose if isinstance(e.purpose,str) else "",story=e.story if hand else "",conf=e.confidence if hand else "",
        ver=e.verify if hand and isinstance(e.verify,str) else "",cau=e.cautions if isinstance(e.cautions,str) else "",
        v20=rnd(x.amount_2020/1000,2) if x is not None else None,v22=rnd(x.amount_2022/1000,2) if x is not None else None,
        s20=rnd(x.sh20,1) if x is not None else None,s22=rnd(x.sh22,1) if x is not None else None))
extra=XE.assign(k=lambda d:d[["amount_2020","amount_2022"]].max(axis=1)).sort_values("k",ascending=False).head(160)
extra=pd.concat([extra,XE.sort_values("d",ascending=False).head(30)]).drop_duplicates(["sp","bp"])
for x in extra.itertuples():
    if (x.sp,x.bp) in seen: continue
    edges.append(dict(s=x.sp,t=x.bp,v=None,sh=None,g=None,p="",story="",conf="",ver="",cau="",v20=rnd(x.amount_2020/1000,2),v22=rnd(x.amount_2022/1000,2),s20=rnd(x.sh20,1),s22=rnd(x.sh22,1)))
for e in edges:
    k=(e["s"],e["t"])
    if k in STORY22: e["c22"],e["st22"],e["vf22"]=STORY22[k]
# 固定レイアウト(力学法で一度だけ計算)
import math
Gx=nx.Graph()
for n_ in nodes: Gx.add_node(n_["id"])
for e in edges[:220]: 
    if e["v"]: Gx.add_edge(e["s"],e["t"],weight=math.sqrt(e["v"]))
# --- レイアウト: 部門グループを球面上に分離配置 → 群内は取引で引き合い → 重なり解消
rng=np.random.default_rng(7); NG=len(GROUPS); ids=[n_["id"] for n_ in nodes]; ix={k:i for i,k in enumerate(ids)}
ctr=np.array([[math.sin(math.acos(1-2*(i+0.5)/NG))*math.cos(math.pi*(1+5**0.5)*i),math.sin(math.acos(1-2*(i+0.5)/NG))*math.sin(math.pi*(1+5**0.5)*i),math.cos(math.acos(1-2*(i+0.5)/NG))] for i in range(NG)])*120
gid=np.array([n_["grp"] for n_ in nodes]); rad=np.array([max(n_["out"],2)**(1/3)*2.6 for n_ in nodes])
X=ctr[gid]+rng.normal(0,18,(len(nodes),3))
W=np.zeros((len(nodes),len(nodes)))
for e in edges[:220]:
    if e["v"]: W[ix[e["s"]],ix[e["t"]]]+=math.sqrt(e["v"]); W[ix[e["t"]],ix[e["s"]]]+=math.sqrt(e["v"])
W/=W.max()
for it in range(400):
    cool=1-it/400; F=np.zeros_like(X)
    D_=X[:,None,:]-X[None,:,:]; dist=np.linalg.norm(D_,axis=2)+1e-6
    F+=(D_/dist[...,None]**3*900).sum(1)                       # 反発
    F-=(W[...,None]*D_*0.02).sum(1)                             # 取引で引き合う
    F-=(X-ctr[gid])*0.05                                        # グループ中心へ
    X+=np.clip(F,-6,6)*cool
for it in range(200):                                          # 重なり解消(半径+余白)
    D_=X[:,None,:]-X[None,:,:]; dist=np.linalg.norm(D_,axis=2)+1e-6; need=rad[:,None]+rad[None,:]+9
    ov=np.clip(need-dist,0,None); np.fill_diagonal(ov,0)
    X+=((D_/dist[...,None])*ov[...,None]).sum(1)*0.25
X-=X.mean(0)
for n_,p in zip(nodes,X): n_["x"],n_["y"],n_["z"]=[round(float(v),1) for v in p]
print("layout extent",np.abs(X).max().round(0),"min gap",round(float((np.linalg.norm(X[:,None]-X[None],axis=2)+np.eye(len(X))*1e9-rad[:,None]-rad[None]).min()),1))
D=dict(groups=[g for g,_ in GROUPS],nodes=nodes,edges=edges,bn=BN)
open("out/explorer_data.json","w",encoding="utf-8").write(json.dumps(D,ensure_ascii=False,separators=(",",":")))
print(len(nodes),len(edges),sum(1 for e in edges if e["story"]),sum(1 for e in edges if "c22" in e),os.path.getsize("out/explorer_data.json"))
