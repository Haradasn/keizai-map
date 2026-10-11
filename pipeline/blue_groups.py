import pandas as pd, numpy as np
from _paths import OUT
r=pd.read_csv(OUT/'blue_ocean_ranking_108.csv',encoding='utf-8-sig',dtype={'code':str})
t=pd.read_csv(OUT/'sector_timeseries_108.csv',encoding='utf-8-sig',dtype={'code':str})
e=pd.read_csv(OUT/'edges.csv',encoding='utf-8-sig'); e=e[(e.level==108)&(e.type=='SUPPLIES')]
nn=pd.read_csv(OUT/'nodes.csv',encoding='utf-8-sig',dtype={'code':str}); nm=nn[nn.level==108].set_index('code').name.to_dict()
GROUPS={
 "G1 モノの寿命を支える裏方":dict(codes=["663","661","481","576","577"],
   story="作る産業ではなく『使い続ける・運ぶ・処分する』産業。設備や車が増え古くなるほど需要が増え、買い手は製造・運輸・建設など広い。業界地図には整備と廃棄物処理の項目が無い。"),
 "G2 ネット経済の配管":dict(codes=["594","593","662","591"],
   story="サービスのデジタル化で、広告・ソフト開発・通信の取引が増える領域。成長は明白だが、実際の売り手はプラットフォームの下請けに分散し、個社の姿は見えにくい。"),
 "G3 ケアと公的価格の市場":dict(codes=["644","643","675","552"],
   story="高齢化とペット化で需要が積み上がる。価格が公定・制度に左右され、民間の参入余地は『制度の外側』(周辺サービス)に出る。"),
 "G4 素材の川上・見えない部材":dict(codes=["113","221","208","281","329"],
   story="最終製品の陰で他産業に売る素材・部材。成長は平均並みだが、買い手が多く、需要は川下の動きに連動する。"),
}
rows=[]
for g,v in GROUPS.items():
    s=t[t.code.isin(v['codes'])]
    o11,o15,o20=s.output_r11.sum(),s.output_r15.sum(),s.output_n20.sum()
    q=r[r.code.isin(v['codes'])]
    b2b=(q.b2b_share*q.size_tril).sum()/q.size_tril.sum()
    ids=["S108_"+c for c in v['codes']]
    ee=e[e.dst.isin(ids)&~e.src.isin(ids)]  # unused
    sell=e[e.src.isin(ids)&~e.dst.isin(ids)].groupby('dst').amount.sum().sort_values(ascending=False).head(5)
    buyers="、".join(f"{nm.get(i[5:],i)}" for i in sell.index)
    buyers=buyers if b2b>=0.3 else '最終需要(家計・政府)が中心。産業向けは '+buyers
    rows.append(dict(group=g,members="、".join(nm[c] for c in v['codes']),output_2020_tril=o20/1000,
      cagr_2011_2020_pct=((o20/o11)**(1/9)-1)*100,cagr_2015_2020_pct=((o20/o15)**(1/5)-1)*100,
      b2b_share=b2b,map_visibility=(q.map_visibility*q.size_tril).sum()/q.size_tril.sum(),main_buyers=buyers,story=v['story']))
G=pd.DataFrame(rows).round(3); G.to_csv(OUT/'blue_ocean_groups.csv',index=False,encoding='utf-8-sig')
pd.set_option('display.width',250); print(G.drop(columns='story').to_string())
tot=t.output_r11.sum(),t.output_r15.sum(),t.output_n20.sum()
print('economy cagr',(tot[2]/tot[0])**(1/9)-1)
