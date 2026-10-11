import textwrap, numpy as np, pandas as pd, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from _paths import RAW as D, OUT
plt.rcParams["font.family"]="Noto Sans CJK JP"
r=pd.read_csv(f"{OUT}/blue_ocean_ranking_108.csv",encoding="utf-8-sig",dtype={"code":str})
G=pd.read_csv(f"{OUT}/blue_ocean_groups.csv",encoding="utf-8-sig")
GM={"G1":["663","661","481","576","577"],"G2":["594","593","662","591"],"G3":["644","643","675","552"],"G4":["331","329","333","332"]}
GC={"G1":"#eb6834","G2":"#2a78d6","G3":"#1baf7a","G4":"#6250d6"}
GN={"G1":"G1 モノの寿命を支える裏方","G2":"G2 ネット経済の配管","G3":"G3 ケアと公的価格の市場","G4":"G4 電気・電子の部品と装置"}
code2g={c:g for g,cs in GM.items() for c in cs}
r["g"]=r.code.map(code2g)
r["hidden"]=1-r.map_visibility
r["gr"]=r.real_cagr_2011_2020*100
fig=plt.figure(figsize=(18,11),dpi=170,facecolor="#fcfcfb")
ax=fig.add_axes([0.05,0.14,0.55,0.69]); ax.set_facecolor("#fcfcfb")
ax.axhline(0.34,color="#c9c8c3",lw=1,ls="--"); ax.text(1.04,0.34,"経済全体の平均 年+0.3%",fontsize=10.5,color="#52514e",va="bottom",ha="right")
YMAX=8.0; labs=[]
for _,x in r.iterrows():
    col=GC.get(x.g,"#b8b7b2"); inn=isinstance(x.g,str)
    jx=0.012*((int(x.code)%5)-2); px=x.hidden+jx; py=min(x.gr,YMAX-0.4)
    ax.scatter(px,py,s=40+x.size_tril*28,color=col,alpha=0.85 if inn else 0.4,ec="white",lw=1.5,zorder=3 if inn else 2)
    if x.gr>YMAX-0.4: ax.annotate(f"↑ 年+{x.gr:.1f}%",(px,py),xytext=(px+0.03,py-0.05),fontsize=10.5,color=col,va="center")
    if inn: labs.append([px,py,x["name"].replace("（別掲を除く。）","").replace("（医薬品を除く。）","")])
labs.sort(key=lambda l:(round(l[0]/0.2),l[1]))
last={}
for px,py,n in labs:
    k=round(px/0.2); ly=py+0.12
    if k in last and ly<last[k]+0.27: ly=last[k]+0.27
    last[k]=ly; ax.text(px+0.03,ly,n,fontsize=11.5,color="#0b0b0b",zorder=5,va="center")
ax.set_xlim(-0.08,1.1); ax.set_ylim(-0.4,YMAX)
ax.set_xlabel("業界地図での『見えにくさ』 →(右ほど載っていない)",fontsize=13); ax.set_ylabel("実質の成長率(2011→2020年・年率%)。8%超は上端に表示",fontsize=13)
ax.set_xticks([0,0.25,0.5,0.75,1]); ax.set_xticklabels(["0\n独立の項目なし","","0.5\n一部に分散","","1.0\n独立の章あり"][::-1]); 
ax.set_xticks([1,0.75,0.5,0.25,0]); ax.set_xticklabels(["独立の項目なし","","一部に分散","","独立の章あり"]); ax.invert_xaxis() if False else None
for s in ["top","right"]: ax.spines[s].set_visible(False)
ax.grid(alpha=0.25)
fig.text(0.03,0.955,"見えにくくて伸びている領域(ブルーオーシャン候補)を探す",fontsize=27,fontweight="bold",va="center")
fig.text(0.03,0.915,"産業連関表の108部門のうち、成長・買い手の増加・業界地図での見えにくさ・利益率などで点数化し、上位を4つのグループにまとめた。",fontsize=13.5,color="#2d2c2a",va="center")
fig.text(0.03,0.89,"円の大きさ=2020年の生産額　色付き=候補グループ　灰色=その他の部門(参考)　『競争の少なさ』は直接測れないため、見えにくさ・利益率などで代用",fontsize=12,color="#52514e",va="center")
# 右パネル
y=0.835
for g in GM:
    row=G[G.group.str.startswith(g)].iloc[0]
    fig.patches.append(Rectangle((0.625,y-0.115),0.006,0.125,transform=fig.transFigure,fc=GC[g],ec="none"))
    fig.text(0.64,y,GN[g],fontsize=15,fontweight="bold",va="center")
    fig.text(0.64,y-0.025,"\n".join("、".join(p) for p in [m[i:i+3] for i in range(0,len(m),3)]) if (m:=row.members.replace("（別掲を除く。）","").replace("（医薬品を除く。）","").split("、")) else "",fontsize=11,color="#2d2c2a",va="center")
    fig.text(0.64,y-0.052,f"2020年 {row.output_2020_tril:.0f}兆円 / 成長 年+{row.cagr_2011_2020_pct:.1f}%(直近5年 +{row.cagr_2015_2020_pct:.1f}%) / 法人向け比率 {row.b2b_share*100:.0f}%",fontsize=11,color="#52514e",va="center")
    import textwrap
    st=textwrap.fill(row.story,34)
    fig.text(0.64,y-0.0715,st,fontsize=11.5,va="top",color="#0b0b0b",linespacing=1.35)
    y-=0.19
fig.text(0.03,0.075,"読み方の注意:",fontsize=12,fontweight="bold",va="center")
fig.text(0.03,0.05,"・G2は成長が明白だが業界地図にも載る。『見えにくい』のは個社の姿(下請け構造)で、市場そのものではない。G3は公定価格・制度に左右される。",fontsize=11.5,color="#2d2c2a",va="center")
fig.text(0.03,0.028,"・見えにくさは日経業界地図の目次を筆者が読んで付けた手作業の判定。廃棄物処理・介護・研究は公的需要が大きく、コロナ影響の大きい業種は除外・割引している。",fontsize=11.5,color="#2d2c2a",va="center")
fig.text(0.03,0.006,"・点数は仮説づくりの入口。実際の競争状況・単価・参入障壁は、企業数(経済センサス)や個別調査で確かめる必要がある。",fontsize=11.5,color="#2d2c2a",va="center")
fig.savefig(f"{OUT}/blue_ocean_map.png",facecolor=fig.get_facecolor()); print('ok')
