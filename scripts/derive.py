"""最新動向の本文に差し込む数値を、データ(nowcast*.json)から計算する。
本文テンプレート(pages/*.html)の {{名前}} を置き換える。データ更新で本文の数字が自動的に追従する。"""
import json,pathlib
R=pathlib.Path(__file__).resolve().parent.parent
def _last(v):
    i=len(v)-1
    while v[i] is None: i-=1
    return v[i]
from decimal import Decimal,ROUND_HALF_UP
def F(x,d=1):
    """四捨五入(半分は切り上げ)。float表現のぶれを避けるため一度丸めてからDecimalで処理。"""
    q=Decimal(1).scaleb(-d); return str(Decimal(str(round(float(x),9))).quantize(q,rounding=ROUND_HALF_UP))
def ym(m): return f"{m[:4]}年{int(m[4:])}月"
def sgn(x,d=0):
    s=F(abs(x),d); return ("+" if x>=0 else "−")+s
def metrics():
    n=json.loads((R/"data/nowcast_chart.json").read_text(encoding="utf-8")); m=json.loads((R/"data/nowcast2_chart.json").read_text(encoding="utf-8"))
    M={}; B="202212"
    # --- 1. SPPI
    mo=n["months"]; ib=mo.index(B); M["sppi_last"]=ym(mo[-1]); M["base"]=ym(B)
    for key,name in (("avg","総平均"),("tech","技術サービス"),("haken","職業紹介・労働者派遣サービス"),("info","情報サービス"),("tsushin","通信"),("senmon","専門サービス")):
        v=n["sppi"][name]; a,b=v[ib],_last(v); M[f"sppi_{key}_0"]=f"{F(a,1)}"; M[f"sppi_{key}_1"]=f"{F(b,1)}"
        M[f"sppi_{key}_p1"]=sgn((b/a-1)*100,1); M[f"sppi_{key}_p0"]=sgn((b/a-1)*100,0)
    # --- 2. 国際収支(最後の12か月分そろった年)
    bp=n["bp"]; ys=[y for y in bp["digital_pay"] if bp["digital_pay"][y][1]==12]; y0,y1=ys[0],ys[-1]
    g=lambda k,y:bp[k][y][0]
    M["bp_y0"],M["bp_y1"]=y0,y1; M["bp_pay0"],M["bp_pay1"]=f"{F(g('digital_pay',y0),1)}",f"{F(g('digital_pay',y1),1)}"
    M["bp_pay_x"]=f"{F(g('digital_pay',y1)/g('digital_pay',y0),1)}"
    M["bp_rec0"],M["bp_rec1"]=f"{F(g('digital_rec',y0),1)}",f"{F(g('digital_rec',y1),1)}"
    M["bp_net0"],M["bp_net1"]=f"{F(-g('digital_net',y0),1)}",f"{F(-g('digital_net',y1),1)}"
    py=max(ys,key=lambda y:-g('digital_net',y)); M["bp_netpeak_y"]=py; M["bp_netpeak"]=f"{F(-g('digital_net',py),1)}"
    M["bp_con0"],M["bp_con1"]=f"{F(-g('consult_net',y0),1)}",f"{F(-g('consult_net',y1),1)}"
    yp=[y for y in bp["digital_pay"] if bp["digital_pay"][y][1]<12]
    M["bp_part_y"]=yp[-1] if yp else ""; M["bp_part_m"]=bp["digital_pay"][yp[-1]][1] if yp else 12
    # --- 3. CGPI
    c=n["cgpi"]; v=c["電力・都市ガス・水道"]; M["cg_el_0"]=f"{F(v[ib],1)}"; M["cg_el_1"]=f"{F(_last(v),1)}"
    seg=v[ib:]; im=seg.index(min(seg)); M["cg_el_min"]=f"{F(seg[im],1)}"; M["cg_el_min_ym"]=ym(mo[ib+im])
    v=c["石炭・原油・天然ガス"]; M["cg_coal_0"]=f"{F(v[ib],1)}"; M["cg_coal_1"]=f"{F(_last(v),1)}"
    M["cg_oil_1"]=f"{F(_last(c['石油・石炭製品']),1)}"
    # --- 4. 活動量
    mm=m["months"]; jb=mm.index(B); M["meti_last"]=ym(mm[-1])
    for key,name in (("ict","情報通信業"),("inet","インターネット附随サービス業"),("soft","ソフトウェア業"),("haken","職業紹介・労働者派遣業"),("tech","技術サービス業")):
        v=m["meti"][name]; a,b=v[jb],_last(v); M[f"meti_{key}_0"]=f"{F(a,1)}"; M[f"meti_{key}_1"]=f"{F(b,1)}"; M[f"meti_{key}_p1"]=sgn((b/a-1)*100,1); M[f"meti_{key}_p0"]=sgn((b/a-1)*100,0)
    # --- 5. 貿易
    t=m["trade"]; Y=t["years"]; y0,y1=Y[0],Y[-1]; M["tr_y0"],M["tr_y1"]=y0,y1
    f=t["fuel_v"]; ip=f.index(max(f)); M["fuel_0"],M["fuel_peak"],M["fuel_1"]=f"{F(f[0],1)}",f"{F(f[ip],1)}",f"{F(f[-1],1)}"; M["fuel_peak_y"]=Y[ip]; M["fuel_peak_x"]=f"{F(f[ip]/f[0],0)}"
    for key in ("crude","lng","coal"):
        M[f"q_{key}"]=sgn(t[f"{key}_q_idx"][-1]-100,0); M[f"p_{key}"]=f"{F(t[f'{key}_p_idx'][-1]/100,1)}"
    ytd=t["fuel_ytd"]; M["ytd_m"]=ytd["last_month"]; M["ytd_1"],M["ytd_0"]=f"{F(ytd['v2026'],1)}",f"{F(ytd['v2025'],1)}"; M["ytd_pct"]=f"{F((ytd['v2026']/ytd['v2025']-1)*100,0)}"
    M["pc_0"],M["pc_1"]=f"{F(t['pc_v'][0],1)}",f"{F(t['pc_v'][-1],1)}"; M["pc_pct"]=sgn((t['pc_v'][-1]/t['pc_v'][0]-1)*100,0); M["pc_px"]=f"{F(t['pc_p_idx'][-1]/100,1)}"
    # --- 6. OECD ICIO(5か国)
    import csv as _csv
    rows=list(_csv.DictReader(open(R/"data/icio_summary_5countries.csv",encoding="utf-8")))
    Y=sorted({r["year"] for r in rows}); y0,y1=Y[0],Y[-1]; M["icio_y0"],M["icio_y1"]=y0,y1
    v=lambda c,y,k:float(next(r[k] for r in rows if r["country"]==c and r["year"]==y))
    for c in ("JPN","USA","DEU","KOR","CHN"):
        cl=c.lower(); xs=[v(c,y,"outsourcing_share_pct") for y in Y]
        M[f"icio_out_{cl}"]=F(v(c,y1,"outsourcing_share_pct"),0)                       # 最新年の外注比率(%)
        lo,hi=F(min(xs),0),F(max(xs),0); M[f"icio_out_{cl}_rng"]=lo if lo==hi else f"{lo}〜{hi}"   # 期間中の範囲
        M[f"icio_out_{cl}1"]=F(v(c,y1,"outsourcing_share_pct"),1)
        M[f"icio_enimp_{cl}"]=F(v(c,y1,"energy_import_share_pct"),0)
    M["icio_out_half"]="半分以下" if v("JPN",y1,"outsourcing_share_pct")<0.5*v("USA",y1,"outsourcing_share_pct") else "半分程度"
    M["icio_digimp0"],M["icio_digimp1"]=F(v("JPN",y0,"digital_import_share_pct"),1),F(v("JPN",y1,"digital_import_share_pct"),1)
    M["icio_en_y0"]=str(int(y1)-2)
    for c in ("JPN","DEU"):
        M[f"icio_en_{c.lower()}0"],M[f"icio_en_{c.lower()}1"]=F(v(c,M["icio_en_y0"],"energy_share_pct"),1),F(v(c,y1,"energy_share_pct"),1)
    M["icio_enimp_jpn0"]=F(v("JPN",M["icio_en_y0"],"energy_import_share_pct"),0)
    return M
def render(text,M):
    import re
    def r(mt):
        k=mt.group(1)
        if k not in M: raise KeyError(k)
        return str(M[k])
    return re.sub(r"\{\{(\w+)\}\}",r,text)
if __name__=="__main__":
    for k,v in metrics().items(): print(k,v)
