import numpy as np, pandas as pd, os, matplotlib, textwrap
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _paths import RAW as D, OUT
plt.rcParams["font.family"]="Noto Sans CJK JP"
S=pd.read_csv(f"{OUT}/ext_sector_97.csv",encoding="utf-8-sig",dtype={"code":str})
W=pd.read_csv(f"{OUT}/ext_edges_97.csv",encoding="utf-8-sig",dtype={"seller":str,"buyer":str})
B=pd.read_csv(f"{OUT}/ext_basic_rows_output.csv",encoding="utf-8-sig",dtype={"code":str}).set_index("code")
UP,DN,NEU="#2a78d6","#eb6834","#8a8a85"
fig=plt.figure(figsize=(19,12),dpi=170,facecolor="#fcfcfb")
fig.text(0.03,0.962,"2020→2022年に何が変わったか(延長産業連関表・97部門)",fontsize=27,fontweight="bold",va="center")
fig.text(0.03,0.925,"価格が急騰したのはエネルギーと素材。数量(実質)が伸びたのは機械・電子部品、対事業所サービス、情報サービス、運輸の回復。AI実用化(2023年〜)はまだ入っていません。",fontsize=13.5,color="#2d2c2a",va="center")
# A 散布図
ax=fig.add_axes([0.05,0.10,0.40,0.76]); ax.set_facecolor("#fcfcfb")
S["pc"]=S.price_chg_2020_2022*100; S["rg"]=S.real_growth_2020_2022*100
ax.axhline(0,color="#c9c8c3",lw=1); ax.axvline(0,color="#c9c8c3",lw=1)
for r in S.itertuples():
    col=DN if r.pc>=30 else UP if r.rg>=12 else NEU
    ax.scatter(r.pc,min(r.rg,58),s=25+r.output_n2022/60,color=col,alpha=0.75 if col!=NEU else 0.4,ec="white",lw=1,zorder=3)
LAB={"石炭・原油・天然ガス":(-8,12),"石油製品":(8,6),"電気":(8,-12),"銑鉄・粗鋼":(8,6),"木材・木製品":(-30,-14),"航空輸送":(8,-2),"通信":(10,-3),"生産用機械":(8,4),"医薬品":(-12,10),"インターネット附随サービス":(10,6),"その他の対事業所サービス":(10,8),"商業":(10,-6),"情報サービス":(-60,-16),"住宅賃貸料":(10,2),"はん用機械":(10,-14),"電子応用装置・電気計測器":(-125,16)}
for n,(dx,dy) in LAB.items():
    r=S[S.name==n].iloc[0]; y=min(r.rg,58)
    ax.annotate(n+("↑" if r.rg>58 else ""),(r.pc,y),xytext=(dx,dy),textcoords="offset points",fontsize=11,color="#0b0b0b",zorder=6,arrowprops=dict(arrowstyle="-",color="#8a8a85",lw=0.7))
ax.set_xlabel("価格の変化(2020→2022年、%)  右ほど値上がり",fontsize=13); ax.set_ylabel("数量(実質生産額)の変化(2020→2022年、%)  上ほど増えた",fontsize=13)
for s_ in ["top","right"]: ax.spines[s_].set_visible(False)
ax.grid(alpha=0.2); ax.set_xlim(-45,100); ax.set_ylim(-20,62)
ax.text(98,-18,"オレンジ=価格+30%以上 / 青=数量+12%以上 / 灰=その他　円の大きさ=2022年の生産額",fontsize=10.5,color="#52514e",ha="right")
ax.text(-43,-12,"↑は上端で切った点(航空輸送+106%、通信+88%)。\n通信は価格指数が−39%(携帯料金引下げ)で、数量が\n大きく出る。物価指数の作り方の影響を含む",fontsize=10.5,color="#52514e",va="top")
# B エッジ
ax2=fig.add_axes([0.64,0.52,0.14,0.33]); 
x=W[(W.amount_2022>=800)&(W.seller!=W.buyer)].sort_values("share_chg_pt",ascending=False)
STORY={("003","061"):"燃料高騰で電力会社の費用の4割近くが燃料に(A)",("003","022"):"原油高で石油製品の原料費が急増(A)",("003","062"):"LNG高騰でガスの費用が膨らむ(A)",("003","023"):"原料炭・コークス価格の上昇(A)",
("022","016"):"ナフサ高騰で石化原料の費用が上昇(A)",("035","036"):"銅・アルミ等の価格上昇(B)",("022","073"):"燃油高に加え、航空の回復で使用量も増加(A)",("022","072"):"燃料高と運航回復(A)",("033","033"):""}
top=x.head(8)
ax2.barh(range(len(top))[::-1],top.share_chg_pt,color=DN,alpha=0.85)
ax2.set_yticks(range(len(top))[::-1]); ax2.set_yticklabels([f"{r.seller_name.replace('石炭・原油・天然ガス','原油・天然ガス')}→{r.buyer_name.replace('石油化学系基礎製品','石化基礎製品').replace('電子応用装置・電気計測器','電子応用・計測器').replace('非鉄金属加工製品','非鉄加工').replace('ガス・熱供給','ガス・熱')}" for r in top.itertuples()],fontsize=10.5)
ax2.set_xlabel("買い手の費用に占める割合の変化(pt)",fontsize=10.5); 
for s_ in ["top","right"]: ax2.spines[s_].set_visible(False)
fig.text(0.50,0.885,"取引の中身が変わった流れ(費用構成比の増加の上位)",fontsize=14,fontweight="bold")
fig.text(0.50,0.862,"上位はほぼ、原油・天然ガスなどの値上がり(確からしさA)。",fontsize=11.5,color="#2d2c2a")
# C 詳細
ax3=fig.add_axes([0.64,0.08,0.14,0.30])
codes=["6699099","6699031","6699041","6699021","6699051","6699011","5931011","5941011","5911021","5951011"]
sub=B.loc[codes].copy(); sub["g"]=(sub.n2022/sub.n2020-1)*100
sub["lab"]=[n.replace("（新聞・出版を除く。）","") for n in sub.name]
ax3.barh(range(len(sub))[::-1],sub.g,color=[UP if c.startswith("66") else "#6250d6" for c in sub.index],alpha=0.85)
ax3.set_yticks(range(len(sub))[::-1]); ax3.set_yticklabels([f"{l[:13]}({v/1000:.1f}兆)" for l,v in zip(sub.lab,sub.n2020)],fontsize=10)
ax3.set_xlabel("2020→2022年の名目増加率(%)、()は2020年の額",fontsize=10.5)
for s_ in ["top","right"]: ax3.spines[s_].set_visible(False)
fig.text(0.50,0.425,"対事業所サービス(青)と情報通信(紫)の中身(名目)",fontsize=14,fontweight="bold")
fig.text(0.50,0.402,"『その他の対事業所』が+27%で最大。人材・警備・建物・土木建築も+14〜22%。",fontsize=11,color="#2d2c2a")
# 右端: 注記
notes=["読み取りの注意",
"・2021・2022年は『延長表』(推計表)。特別調査をしないため、サービス産業どうしの取引の変化は実態より粗い。価格・数量の動きは信頼しやすいが、取引構造の変化は仮説の域。",
"・2020年は基本表(ベンチマーク)と延長表で概念が異なり、生産額が約3%小さい(996兆円 vs 1,026兆円)。2020→2022の比較は同じ延長表の概念に統一している。",
"・名目の増加には値上がりを含む(2022年の名目合計は2020年比+15.5%、実質では+8.0%)。",
"・生成AIの実用化・データセンター投資・2023年以降のエネルギー需給は、この表には入っていません。"]
y=0.86
for i,t in enumerate(notes):
    fig.text(0.80,y,textwrap.fill(t,19),fontsize=11.5 if i else 13.5,fontweight="bold" if i==0 else None,va="top",color="#0b0b0b" if i==0 else "#2d2c2a",linespacing=1.4)
    y-=0.03 if i==0 else 0.027*(len(textwrap.fill(t,19).split("\n"))+0.6)
fig.text(0.97,0.012,"出典: 経済産業省『延長産業連関表(令和2年基準)』2020〜2022年(e-Stat掲載)から作成。仮説は筆者の推測です。",fontsize=10,color="#52514e",ha="right")
fig.savefig(f"{OUT}/ext_change_2020_2022.png",facecolor=fig.get_facecolor()); print("ok")
