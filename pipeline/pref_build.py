"""都道府県の産業連関表(2020年・統合大分類37部門ベース)を共通形式に整え、data/pref_37.json を作る。
入力: pref_raw/ (各県の公表ファイル。出典は pref_raw/SOURCES.json)。単位は百万円。"""
import csv,json,pathlib
import openpyxl,pandas as pd
R=pathlib.Path(__file__).resolve().parent.parent; RAW=R/"pref_raw"; OUT=R/"data"
SRC=json.loads((RAW/"SOURCES.json").read_text(encoding="utf-8"))
num=lambda x:float(str(x).replace(",","")) if x not in (None,"") else 0.0

def table(rows,hdr_row,name_row,first,code_col,name_col):
    """rows: 2次元配列。 列見出し(name_row)と行見出し(name_col)でアクセスできる辞書を返す。"""
    cols={}
    for j,v in enumerate(rows[name_row]):
        if v not in (None,""): cols.setdefault(str(v).strip(),j)   # 同名は最初の列
    rl=[(str(r[code_col]).strip(),str(r[name_col]).strip() if r[name_col] else "",i) for i,r in enumerate(rows) if i>=first and r[name_col]]
    return cols,rl

def load(slug):
    s=SRC[slug]; f=RAW/s["file"]
    if f.suffix==".csv": rows=list(csv.reader(open(f,encoding="cp932"))); name_row,first,code_col,name_col=1,2,0,1
    else:
        ws=openpyxl.load_workbook(f,read_only=True,data_only=True)[s["sheet"]]; rows=[list(r) for r in ws.iter_rows(values_only=True)]
        name_row,first,code_col,name_col=s["name_row"],s["first"],s["code_col"],s["name_col"]
    cols,rl=table(rows,None,name_row,first,code_col,name_col)
    return rows,cols,rl,s

PICK={"exp":["輸出計","輸出"],"mexp":["移出計","移出"],"imp":["（控除）輸入計"],"mimp":["（控除）移入計","（控除）移入","移入"],"X":["生産額","県内生産額","府内生産額","都内生産額"],
      "dom":["都内最終需要計","県内最終需要計","府内最終需要計"],"int":["内生部門計"]}
def col(cols,k):
    for n in PICK[k]:
        if n in cols: return cols[n]
    raise KeyError((k,list(cols)[:60]))

def build(slug):
    rows,cols,rl,s=load(slug)
    sec=[(c.lstrip("A"),n,i) for c,n,i in rl if c.lstrip("A").isdigit() and int(c.lstrip("A"))<=69]
    sec+=[("HQ",n,i) for c,n,i in rl if n=="本社"]       # 東京都のみの部門
    byname={n:i for c,n,i in rl}
    X_r=[i for c,n,i in rl if n in("生産額","県内生産額","府内生産額","都内生産額","国内生産額")][0]
    VA_r=[i for c,n,i in rl if n=="粗付加価値部門計"][0]
    cX,cE,cM,cI,cMI,cD,cT=col(cols,"X"),col(cols,"exp"),col(cols,"mexp"),col(cols,"imp"),col(cols,"mimp"),col(cols,"dom"),col(cols,"int")
    out=[]
    for c,n,i in sec:
        r=rows[i]; j=cols.get(n)
        if j is None and n=="本社": j=cols.get("本社")
        X=num(r[cX]); 
        if X<=0: continue
        va=num(rows[VA_r][j]) if j is not None else None
        e=num(r[cE])+num(r[cM]); mi=abs(num(r[cI]))+abs(num(r[cMI]))
        dem=num(r[cT])+num(r[cD])            # 域内需要 = 中間需要 + 域内最終需要
        # 検証: 需要側(域内需要+移輸出-移輸入=生産額) と 費用側(中間投入+付加価値=生産額)
        ti=[i2 for c2,n2,i2 in rl if n2=="内生部門計"][0]; intin=num(rows[ti][j]) if j is not None else None
        assert abs(dem+e-mi-X)<=max(2,X*1e-6),(slug,n,"需要側",dem+e-mi,X)
        if va is not None and intin is not None: assert abs(intin+va-X)<=max(2,X*1e-6),(slug,n,"費用側",intin+va,X)
        out.append(dict(c=c,n=n,out=X,va=va,exp=e,imp=mi,dem=dem))
    tot=num(rows[X_r][cT]) if False else sum(o["out"] for o in out)
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
        res[slug]=p; print(slug,p["name"],round(T/1e6,1),"兆円",len(p["sectors"]),"部門","VA",round(VA/1e6,1))
    (OUT/"pref_37.json").write_text(json.dumps(res,ensure_ascii=False),encoding="utf-8")
