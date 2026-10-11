import numpy as np, pandas as pd, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Polygon, Circle, Rectangle
D=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(D,"out")
plt.rcParams["font.family"]="Noto Sans CJK JP"
nodes=pd.read_csv(f"{OUT}/nodes.csv",dtype={"code":str}); n37=nodes[nodes.level==37].set_index("code")
d=pd.read_csv(f"{OUT}/edge_stories.csv",encoding="utf-8-sig",dtype={"seller":str,"buyer":str})
x=d[(d.seller!=d.buyer)&(d.story_type=="手書き仮説")].sort_values("amount_2020_tril",ascending=False).head(20).reset_index(drop=True)
SHORT={ # 図用の短い仮説(各行とも元のedge_stories.csvの仮説を要約)
 0:"高齢化と新薬・高額薬の増加で、病院・薬局の薬代が膨らんだ",
 1:"通信・ネット企業が開発や運用の人手・設備を外から調達",
 2:"広告・人材・リース会社がクラウドやシステムへの支出を増やした",
 3:"食品の原料(農水産物)の実質量が減少。簡便化・輸入品への切替か",
 4:"低金利で不動産が借入を増やした。預貸残高がそのまま反映されやすい",
 5:"卸・小売が警備・清掃・販促・派遣を外注。実質は横ばい",
 6:"設計・測量・建機リース・技能者派遣を建設が外から調達",
 7:"運転手・整備士不足とリース化で、運送会社の外注比率が上昇",
 8:"再開発・インフラ更新で建築金物の割合が上昇(2015年以降は横ばい)",
 9:"原油安が主因(ほぼ全量が輸入で、支払先の大半は海外)",
 10:"燃料価格の下落が主因。再エネ・原発再稼働で使用量も減った可能性",
 11:"卸を通さない直接取引・ECで、卸経由の物流が減った可能性",
 12:"研究の外部化とも読めるが、統計の定義差が大きい部門",
 13:"金融機関がシステム運用・事務・販促の外注を増やした",
 14:"原油安に加え、2020年は航空・旅客の縮小で使用量も減った",
 15:"2020年はコロナ禍で外食・宿泊の需要が急減",
 16:"調査・システム・清掃・人材などの委託(民間委託)が増えた",
 17:"実質は横ばい。通信料金・システム単価の低下が構成比の低下に",
 18:"建設需要に連動する典型的な素材の調達",
 19:"病院・施設が検査・給食・清掃・リネンを外部委託",
}
CAVEAT_NODES={"41","57","06","63","55"}  # 統計定義が2020年と異なる部門
COVID_EDGES={("57","51"),("21","57"),("11","67")}
GROUPS=[("資源・一次産業",["01","06"]),("素材",["15","16","20","21","22","25","26","27","28"]),("食品・生活関連製造",["11","39","68"]),
 ("機械・電機・輸送機械",["29","30","31","32","33","34","35"]),("建設・エネルギー・環境",["41","46","47","48"]),
 ("流通・金融・不動産・運輸通信",["51","53","55","57","59"]),("対事業所・対個人サービス等",["66","67","65","69"]),("公務・教育・医療",["61","63","64"])]
COL=["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#6250d6","#e34948"]
gidx={c:gi for gi,(_,cs) in enumerate(GROUPS) for c in cs}
used=sorted(set(x.seller)|set(x.buyer),key=lambda c:(gidx[c],c))
N=len(used); ang={c:np.pi/2-2*np.pi*(i+0.5)/N for i,c in enumerate(used)}
pos={c:np.array([np.cos(t),np.sin(t)]) for c,t in ang.items()}
X=n37.output; Rn={c:0.03+0.065*np.sqrt(X[c]/X.max()) for c in used}
nm=lambda c:n37.name[c].replace("（","(").replace("）",")")
UP,DN,NEU="#2a78d6","#eb6834","#8a8a85"
def tc(v): return UP if v>=2 else DN if v<=-2 else NEU
fig=plt.figure(figsize=(18,12.5),dpi=170,facecolor="#fcfcfb")
ax=fig.add_axes([0.0,0.10,0.53,0.76]); ax.set_xlim(-1.7,1.7); ax.set_ylim(-1.4,1.4); ax.set_aspect("equal"); ax.axis("off")
amax=x.amount_2020_tril.max()
for r in x.sort_values("amount_2020_tril").itertuples():
    p0,p1=pos[r.seller],pos[r.buyer]; u=(p1-p0)/np.linalg.norm(p1-p0)
    s=p0+u*Rn[r.seller]; t=p1-u*(Rn[r.buyer]+0.012); C=(s+t)/2*0.25
    lw=1.2+9*np.sqrt(r.amount_2020_tril/amax); col=tc(r.real_cagr_2011_2020_pct)
    ax.add_patch(PathPatch(Path([s,C,t],[Path.MOVETO,Path.CURVE3,Path.CURVE3]),fc="none",ec=col,lw=lw,alpha=0.55,capstyle="round",zorder=2))
    tan=t-C; tan/=np.linalg.norm(tan); nr=np.array([-tan[1],tan[0]]); hl=0.05; hw=0.028
    ax.add_patch(Polygon([t,t-tan*hl+nr*hw,t-tan*hl-nr*hw],closed=True,fc=col,ec="none",alpha=0.9,zorder=3))
    i=x.index[(x.seller==r.seller)&(x.buyer==r.buyer)][0]+1
    q=0.22+0.56*((i*0.618)%1); m=(1-q)**2*s+2*q*(1-q)*C+q*q*t
    ax.add_patch(Circle(m,0.055,fc="white",ec=col,lw=1.8,zorder=7)); ax.text(m[0],m[1],str(i),ha="center",va="center",fontsize=11,fontweight="bold",color="#0b0b0b",zorder=8)
for c in used:
    ax.add_patch(Circle(pos[c],Rn[c],fc=COL[gidx[c]],ec="#fcfcfb",lw=2,zorder=5))
    t=ang[c]; ux,uy=np.cos(t),np.sin(t); right=ux>=0; r0=1+Rn[c]+0.04
    lab=nm(c)+("※" if c in CAVEAT_NODES else "")
    ax.text(ux*r0,uy*r0,lab,ha="left" if right else "right",va="center",fontsize=13.5,color="#0b0b0b",zorder=6)
    ax.text(ux*r0,uy*r0-0.075,f"{X[c]/1000:,.0f}兆円",ha="left" if right else "right",va="center",fontsize=11,color="#52514e",zorder=6)
fig.text(0.03,0.955,"お金の流れの太いところを、仮説つきで読む(37部門・上位20本)",fontsize=27,fontweight="bold",va="center")
fig.text(0.03,0.918,"上位20本のうち8本の起点が『対事業所サービス』(人材・リース・警備・広告など=外注の受け皿)。",fontsize=13.5,color="#2d2c2a",va="center")
fig.text(0.03,0.885,"線の太さ=2020年の取引額　色=実質の増減(2011→20年・年率)\n円の大きさ=その部門の生産額　矢印=モノ・サービスの向き(代金は逆向き)",fontsize=12,color="#52514e",va="center")
# 凡例
lx=0.03
for k,(c,l) in enumerate([(UP,"増えている(年+2%以上)"),(NEU,"横ばい(±2%未満)"),(DN,"減っている(年−2%以下)")]):
    xx=lx+k*0.165; fig.patches.append(Rectangle((xx,0.0965),0.02,0.007,transform=fig.transFigure,fc=c,ec="none")); fig.text(xx+0.025,0.1,l,fontsize=12,va="center")
fig.text(0.03,0.045,"※=2011・2015年と2020年で統計の定義が異なる部門(増減の一部は統計上の要因の可能性)。\n原油・LNGの流れは売り手の行に輸入を含むため、支払先の大半は海外。",fontsize=11,color="#52514e",va="center")
fig.text(0.03,0.018,"確からしさ A=数字から確かめやすい / B=もっともらしいが未検証 / C=弱い推測。部門の色は独自グルーピング(公式分類ではない)。",fontsize=11,color="#52514e",va="center")
# 右:ストーリー
fig.text(0.545,0.925,"番号ごとの仮説(売り手 → 買い手 / 2020年の額 / 実質の増減 / 確からしさ)",fontsize=14.5,fontweight="bold",va="center")
y0=0.895; dy=0.0435
for i,r in enumerate(x.itertuples()):
    y=y0-i*dy; col=tc(r.real_cagr_2011_2020_pct)
    fig.patches.append(Circle((0.553,y-0.003),0.0,transform=fig.transFigure))
    fig.text(0.548,y,f"{i+1}",fontsize=12.5,fontweight="bold",color="white",ha="center",va="center",bbox=dict(boxstyle="circle,pad=0.3",fc=col,ec="none"))
    mark="※" if (r.seller in CAVEAT_NODES or r.buyer in CAVEAT_NODES) else ""
    cv=" ・コロナ影響" if (r.seller,r.buyer) in COVID_EDGES else ""
    fig.text(0.562,y+0.009,f"{nm(r.seller)} → {nm(r.buyer)}{mark}　{r.amount_2020_tril:.1f}兆円　{r.real_cagr_2011_2020_pct:+.1f}%/年　[{r.confidence}]{cv}",fontsize=12.5,fontweight="bold",va="center",color="#0b0b0b")
    fig.text(0.562,y-0.011,SHORT[i],fontsize=11.5,va="center",color="#2d2c2a")
fig.text(0.97,0.006,"出典: 令和2年産業連関表、平成23-27-令和2年接続産業連関表(総務省ほか)から作成。仮説は筆者の推測で、検証前のものです。",fontsize=10,color="#52514e",ha="right",va="center")
fig.savefig(f"{OUT}/industry_story_overview.png",facecolor=fig.get_facecolor()); print("ok",N)
