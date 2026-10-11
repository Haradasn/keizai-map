"""都道府県の産業連関表(2020年・統合大分類37部門ベース)を共通形式に整え、data/pref_37.json を作る。
入力: pref_raw/ (各県の公表ファイル。出典は pref_raw/SOURCES.json)。単位は百万円。"""
import csv,json,pathlib
import openpyxl,pandas as pd
R=pathlib.Path(__file__).resolve().parent.parent; RAW=R/"pref_raw"; OUT=R/"data"
SRC=json.loads((RAW/"SOURCES.json").read_text(encoding="utf-8"))
num=lambda x:float(str(x).replace(",","")) if x not in (None,"") else 0.0

import re
norm=lambda v:re.sub(r"\s+","",str(v))
def table(rows,name_row,first,code_col,name_col):
    cols={}
    for j,v in enumerate(rows[name_row]):
        if v not in (None,""): cols.setdefault(norm(v),j)   # 同名は最初の列
    rl=[(norm(r[code_col]) if r[code_col] is not None else "",norm(r[name_col]),i) for i,r in enumerate(rows) if i>=first and r[name_col]]
    return cols,rl

def load(slug):
    s=SRC[slug]; f=RAW/s["file"]
    if f.suffix==".csv": rows=list(csv.reader(open(f,encoding="cp932"))); name_row,first,code_col,name_col=1,2,0,1
    else:
        ws=openpyxl.load_workbook(f,read_only=True,data_only=True)[s["sheet"]]; rows=[list(r) for r in ws.iter_rows(values_only=True)]
        name_row,first,code_col,name_col=s["name_row"],s["first"],s["code_col"],s["name_col"]
    cols,rl=table(rows,name_row,first,code_col,name_col)
    return rows,cols,rl,s

PICK={"X":["生産額","県内生産額","府内生産額","都内生産額","国内生産額"],"dem":["都内需要合計","県内需要合計","府内需要合計","県内需要計"],"int":["内生部門計"],
      "mexp":["移輸出計"],"explicit_imp":["（控除）移輸入計","移輸入計"]}
def col(cols,k):
    for n in PICK[k]:
        if n in cols: return cols[n]
    raise KeyError((k,list(cols)[:60]))
def colopt(cols,k):
    for n in PICK[k]:
        if n in cols: return cols[n]

def build_okinawa(slug):
    """沖縄県: 全国の基本分類に対応する397×361部門表を、全国の37部門に合算する。"""
    s=SRC[slug]; ws=openpyxl.load_workbook(RAW/s["file"],read_only=True,data_only=True).worksheets[0]
    rows=[list(r) for r in ws.iter_rows(values_only=True)]
    nd=pd.read_csv(OUT/"nodes.csv",encoding="utf-8-sig",dtype={"code":str}); n108=nd[nd.level==108].set_index("code"); n37=nd[nd.level==37].set_index("code")
    to37=lambda code3:"%02d"%int(n108.loc[code3,"parent37"])
    hdr=[norm(x) for x in rows[5]]; cd=rows[4]
    ci={h:j for j,h in reversed(list(enumerate(hdr))) if h}
    first_col=2; last_col=[j for j,h in enumerate(hdr) if h=="内生部門計"][0]     # 内生の列は first_col..last_col-1
    rowidx={norm(r[1]):i for i,r in enumerate(rows) if i>=6 and r[1]}
    for k in ("県内需要合計","輸出計","移出計","県内生産額"): assert k in ci,k
    agg={}
    a=lambda k:agg.setdefault(k,dict(out=0.0,dem=0.0,exp=0.0,va=0.0,intin=0.0))
    ri_int=[i for i,r in enumerate(rows) if i>=6 and r[1] and norm(r[1])=="内生部門計"][0]
    ri_va=[i for i,r in enumerate(rows) if i>=6 and r[1] and norm(r[1])=="粗付加価値部門計"][0]
    for i in range(6,ri_int):                                    # 行: 内生部門
        r=rows[i]; code=str(r[0])
        if not code[:4].isdigit() or int(code[:2])>69: continue
        k=to37(code[:3]); g=a(k); g["out"]+=num(r[ci["県内生産額"]]); g["dem"]+=num(r[ci["県内需要合計"]]); g["exp"]+=num(r[ci["輸出計"]])+num(r[ci["移出計"]])
    for j in range(first_col,last_col):                          # 列: 内生部門(付加価値・中間投入)
        code=str(cd[j])
        if not code[:4].isdigit() or int(code[:2])>69: continue
        k=to37(code[:3]); g=a(k); g["va"]+=num(rows[ri_va][j]); g["intin"]+=num(rows[ri_int][j])
    out=[]
    for k,g in sorted(agg.items()):
        mi=g["dem"]+g["exp"]-g["out"]
        assert abs(g["intin"]+g["va"]-g["out"])<=max(3,g["out"]*1e-4),(slug,k,"費用側",g["intin"]+g["va"],g["out"])
        assert mi>=-max(3,g["out"]*1e-4),(slug,k,"移輸入が負",mi)
        out.append(dict(c=k,n=n37.loc[k,"name"],out=g["out"],va=g["va"],exp=g["exp"],imp=max(mi,0),dem=g["dem"]))
    return dict(name=s["name"],year=s["year"],url=s["url"],file=s["file"],sectors=out)

def build(slug):
    if SRC[slug].get("special")=="okinawa": return build_okinawa(slug)
    rows,cols,rl,s=load(slug)
    sec=[(c.lstrip("A").zfill(2),n,i) for c,n,i in rl if c.lstrip("A").isdigit() and int(c.lstrip("A"))<=69]
    sec+=[("HQ",n,i) for c,n,i in rl if n=="本社"]       # 東京都のみの部門
    X_r=[i for c,n,i in rl if n in PICK["X"]][0]
    VA_r=[i for c,n,i in rl if n=="粗付加価値部門計"][0]; ti=[i2 for c2,n2,i2 in rl if n2=="内生部門計"][0]
    cX,cD=col(cols,"X"),col(cols,"dem"); cME=colopt(cols,"mexp"); cEI=colopt(cols,"explicit_imp")
    out=[]
    for c,n,i in sec:
        r=rows[i]; j=cols.get(n)
        X=num(r[cX])
        if X<=0: continue
        va=num(rows[VA_r][j]) if j is not None else None
        intin=num(rows[ti][j]) if j is not None else None
        e=num(r[cME]) if cME is not None else num(r[cols["輸出"]])+num(r[cols["移出"]])
        dem=num(r[cD]); mi=dem+e-X          # 移輸入 = 域内需要 + 移輸出 - 生産額 (需給バランスから)
        # 検証: 公表された移輸入の合計列があれば一致すること、費用側(中間投入+付加価値=生産額)が合うこと
        if cEI is not None: assert abs(abs(num(r[cEI]))-mi)<=max(2,X*1e-6),(slug,n,"移輸入",num(r[cEI]),mi)
        if va is not None and intin is not None: assert abs(intin+va-X)<=max(2,X*1e-6),(slug,n,"費用側",intin+va,X)
        assert mi>=-max(2,X*1e-6),(slug,n,"移輸入が負",mi)
        out.append(dict(c=c,n=n,out=X,va=va,exp=e,imp=max(mi,0),dem=dem))
    m=s.get("merge")
    if m:                                             # 兵庫県の39部門を全国の37部門に合わせる(農・林・漁を農林漁業に合算)
        nat={"01":"農林漁業"}; g={}
        for o in out:
            k=m.get(o["c"],o["c"]); a=g.setdefault(k,dict(c=k,n=nat.get(k,o["n"]),out=0,va=0,exp=0,imp=0,dem=0))
            for f in ("out","va","exp","imp","dem"): a[f]+=o[f]
        out=list(g.values())
    return dict(name=s["name"],year=s["year"],url=s["url"],file=s["file"],sectors=out)

if __name__=="__main__":
    nd=pd.read_csv(OUT/"nodes.csv",encoding="utf-8-sig",dtype={"code":str}); n37=nd[nd.level==37].set_index("code"); nat=n37.output.astype(float); natt=nat.sum()
    res={}
    for slug in SRC:
        p=build(slug); T=sum(o["out"] for o in p["sectors"]); VA=sum(o["va"] or 0 for o in p["sectors"])
        for o in p["sectors"]:
            o["share"]=o["out"]/T; ns=float(nat.get(o["c"],0))/natt if o["c"] in nat.index else None
            o["nat_share"]=ns; o["lq"]=(o["share"]/ns) if ns else None
            o["va_ratio"]=(o["va"]/o["out"]) if o["va"] is not None else None
            o["exp_ratio"]=o["exp"]/o["out"]; o["imp_ratio"]=o["imp"]/o["dem"] if o["dem"] else None
        p["total_out"]=T; p["total_va"]=VA; p["exp_total"]=sum(o["exp"] for o in p["sectors"]); p["imp_total"]=sum(o["imp"] for o in p["sectors"])
        p["note"]=SRC[slug].get("note",""); res[slug]=p; print(slug,p["name"],round(T/1e6,1),"兆円",len(p["sectors"]),"部門","VA",round(VA/1e6,1))
    (OUT/"pref_37.json").write_text(json.dumps(res,ensure_ascii=False),encoding="utf-8")
