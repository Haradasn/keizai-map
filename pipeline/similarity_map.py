"""108部門を『取引の相手の似かた』で2次元に並べる。距離=取引プロファイルの非類似度。
入力: data/edges.csv(level108), nodes.csv, blue_ocean_ranking_108.csv, blue_ocean_groups.csv
出力: data/similarity_map.json"""
import pandas as pd,numpy as np,json,pathlib
from sklearn.manifold import MDS
from scipy.stats import spearmanr
from scipy.spatial.distance import squareform
R=pathlib.Path(__file__).resolve().parent.parent; D=R/"data"
rd=lambda f,**k:pd.read_csv(D/f,encoding="utf-8-sig",**k)
n=rd("nodes.csv",dtype={"code":str}); n=n[n.level==108].reset_index(drop=True)
e=rd("edges.csv"); e=e[(e.level==108)&(e.type=="SUPPLIES")]
ids=list(n.id); ix={k:i for i,k in enumerate(ids)}; N=len(ids)
A=np.zeros((N,N))  # A[i,j]=iがjに売った額
for s,d,a in zip(e.src,e.dst,e.amount): A[ix[s],ix[d]]+=a
np.fill_diagonal(A,0); A=np.clip(A,0,None)
buy=A/np.maximum(A.sum(0,keepdims=True),1e-9)    # 列=買い手jの仕入れ構成
sell=A/np.maximum(A.sum(1,keepdims=True),1e-9)   # 行=売り手iの販売先構成
X=np.hstack([np.sqrt(buy.T),np.sqrt(sell)])      # 平方根=Hellinger距離
X/=np.maximum(np.linalg.norm(X,axis=1,keepdims=True),1e-9)
dist=np.sqrt(np.maximum(2-2*(X@X.T),0)); np.fill_diagonal(dist,0)
mds=MDS(n_components=2,metric_mds=True,metric="precomputed",init="random",n_init=8,max_iter=1000,random_state=0,normalized_stress="auto")
P=mds.fit_transform(dist)
rho=spearmanr(squareform(dist,checks=False),squareform(np.linalg.norm(P[:,None]-P[None],axis=2),checks=False))[0]
print("rank corr(dist, map dist)=",round(rho,3),"stress",round(mds.stress_,3))
P=(P-P.mean(0)); P/=np.abs(P).max()
rk=rd("blue_ocean_ranking_108.csv",dtype={"code":str}).set_index("code")
G={"G1":["663","661","481","576","577"],"G2":["594","593","662","591"],"G3":["644","643","675","552"],"G4":["113","221","208","281","329"]}
gname={"G1":"モノの寿命を支える裏方","G2":"ネット経済の配管","G3":"ケアと公的価格の市場","G4":"素材の川上・見えない部材"}
c2g={c:g for g,cs in G.items() for c in cs}
tot=A.sum()
ed=json.load(open(D/"explorer_data.json")); p2g={x["name"]:x["grp"] for x in ed["nodes"]}; gl=ed["groups"]
allm=dist[np.triu_indices(N,1)].mean()
coh={}
for g,cs in G.items():
    ii=[ix["S108_"+c] for c in cs]; sub=dist[np.ix_(ii,ii)][np.triu_indices(len(ii),1)]
    rnd=[np.random.default_rng(k).choice(N,len(ii),replace=False) for k in range(2000)]
    nul=np.array([dist[np.ix_(r,r)][np.triu_indices(len(ii),1)].mean() for r in rnd])
    coh[g]=dict(within=round(float(sub.mean()),3),all=round(float(allm),3),pct=round(float((nul<sub.mean()).mean()*100),1))
print(coh)
nodes=[]
for i,r in n.iterrows():
    nn=np.argsort(dist[i])[1:4]
    q=rk.loc[r.code] if r.code in rk.index else None
    nodes.append(dict(c=r.code,n=r["name"],p=str(r.parent37_name),grp=p2g.get(str(r.parent37_name)),x=round(float(P[i,0]),4),y=round(float(P[i,1]),4),
      o=round(float(r.output)/1000,2),g=round(float(q.real_cagr_2015_2020)*100,1) if q is not None else None,
      bo=c2g.get(r.code),nb=[n.loc[j,"name"] for j in nn]))
json.dump(dict(nodes=nodes,grpnames=gl,groups={k:dict(name=gname[k],codes=v) for k,v in G.items()},rho=round(float(rho),3),coh=coh),open(D/"similarity_map.json","w"),ensure_ascii=False)
print(len(nodes)); 
for g,cs in G.items():
    print(g,[ (x["n"],x["nb"]) for x in nodes if x["c"] in cs][:2])
