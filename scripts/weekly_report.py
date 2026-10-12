"""週次レポート: Cloudflare Web Analytics と Google Search Console から、直近7日の状況をまとめる。
環境変数: CF_API_TOKEN, CF_ACCOUNT_ID, GSC_SA_JSON(サービスアカウントのJSON)。
  python3 scripts/weekly_report.py --check   … キーが使えるかだけ確認(数値は出さない。公開リポジトリのログに残るため)
  python3 scripts/weekly_report.py > report.md
"""
import os,sys,json,datetime as dt,urllib.request,urllib.parse,urllib.error
CHECK="--check" in sys.argv
def _open(req):
    try:
        with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:                     # 原因が分かるよう、応答の本文の先頭を添える(キーは含まれない)
        raise RuntimeError(f"HTTP {e.code} {e.read()[:300].decode('utf-8','replace')}") from None
def post(url,body,headers): return _open(urllib.request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json",**headers}))
def get(url,headers): return _open(urllib.request.Request(url,headers=headers))

# ---------- Cloudflare Web Analytics(GraphQL Analytics API, rumPageloadEventsAdaptiveGroups)
def cloudflare(start,end):
    tok,acc=os.environ.get("CF_API_TOKEN"),os.environ.get("CF_ACCOUNT_ID")
    if not tok or not acc: return None,"CF_API_TOKEN / CF_ACCOUNT_ID が未設定"
    f='{datetime_geq:$s,datetime_lt:$e}'
    def grp(alias,dim,n): return f'{alias}: rumPageloadEventsAdaptiveGroups(limit:{n},filter:{f},orderBy:[count_DESC]){{count sum{{visits}} dimensions{{{dim}}}}}'
    q=('query($a:String!,$s:Time!,$e:Time!){viewer{accounts(filter:{accountTag:$a}){'
       f'total: rumPageloadEventsAdaptiveGroups(limit:1,filter:{f}){{count sum{{visits}}}} '
       +grp("pages","requestPath",15)+" "+grp("refs","refererHost",10)+" "+grp("countries","countryName",5)+" "+grp("devices","deviceType",5)+'}}}')
    r=post("https://api.cloudflare.com/client/v4/graphql",{"query":q,"variables":{"a":acc,"s":start.isoformat()+"T00:00:00Z","e":end.isoformat()+"T00:00:00Z"}},{"Authorization":"Bearer "+tok})
    if r.get("errors"): return None,"Cloudflare: "+"; ".join(e.get("message","") for e in r["errors"])
    accs=r["data"]["viewer"]["accounts"]
    if not accs: return None,"Cloudflare: アカウントが見つからない(CF_ACCOUNT_ID か権限を確認)"
    return accs[0],None

# ---------- Google Search Console(サービスアカウントで署名したJWTからアクセストークンを得る)
def gsc_token():
    raw=os.environ.get("GSC_SA_JSON")
    if not raw: return None,"GSC_SA_JSON が未設定"
    from google.oauth2 import service_account
    import google.auth.transport.requests as gtr
    cred=service_account.Credentials.from_service_account_info(json.loads(raw),scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(gtr.Request()); return cred.token,None
def gsc(start,end):
    tok,err=gsc_token()
    if err: return None,None,err
    H={"Authorization":"Bearer "+tok}
    sites=[s["siteUrl"] for s in get("https://www.googleapis.com/webmasters/v3/sites",H).get("siteEntry",[]) if "keizai-atlas" in s["siteUrl"]]
    if not sites: return None,None,"Search Console: keizai-atlas のプロパティが見つからない(サービスアカウントをユーザーに追加したか確認)"
    site=sites[0]; u="https://www.googleapis.com/webmasters/v3/sites/"+urllib.parse.quote(site,safe="")+"/searchAnalytics/query"
    body=lambda dims,n:{"startDate":start.isoformat(),"endDate":end.isoformat(),"dimensions":dims,"rowLimit":n}
    out={"total":post(u,body([],1),H).get("rows",[]),"queries":post(u,body(["query"],15),H).get("rows",[]),"pages":post(u,body(["page"],10),H).get("rows",[])}
    return site,out,None

# ---------- 読者の反応(サイトの Worker が D1 に保存したもの。合言葉 FEEDBACK_KEY で読み出す)
def feedback(since):
    k=os.environ.get("FEEDBACK_KEY")
    if not k: return None,"FEEDBACK_KEY が未設定"
    return get("https://keizai-atlas.com/api/feedback/export?since="+since.isoformat(),{"Authorization":"Bearer "+k,"User-Agent":"keizai-atlas-weekly-report"}),None

if __name__=="__main__":
    from zoneinfo import ZoneInfo
    today=dt.datetime.now(ZoneInfo('Asia/Tokyo')).date()   # 日本時間の日付で集計
    e=today; s=e-dt.timedelta(days=7)          # Cloudflare: 直近7日
    ge=today-dt.timedelta(days=3); gs=ge-dt.timedelta(days=6)          # Search Console は2〜3日遅れて確定するので、3日前までの7日間
    try: cf,cerr=cloudflare(s,e)
    except Exception as x: cf,cerr=None,f"{type(x).__name__}: {getattr(x,'reason','') or x}"[:300]
    try: site,g,gerr=gsc(gs,ge)
    except Exception as x: site,g,gerr=None,None,f"{type(x).__name__}: {getattr(x,'reason','') or x}"[:300]
    try: fb,ferr=feedback(s)
    except Exception as x: fb,ferr=None,f"{type(x).__name__}: {getattr(x,'reason','') or x}"[:300]
    if CHECK:
        print("::notice::読者の反応 OK" if fb is not None else "::warning::読者の反応 NG - "+str(ferr))
        # GitHub Actions のアノテーションとして結果を残す(数値は含めない)
        print(("::notice::Cloudflare OK" if cf is not None else "::error::Cloudflare NG - "+str(cerr)).replace("\n"," "))
        print(("::notice::Search Console OK ("+site+")" if g is not None else "::error::Search Console NG - "+str(gerr)).replace("\n"," "))
        sys.exit(0 if (cf is not None and g is not None) else 1)
    L=[f"# Keizai Atlas 週次レポート（{today.isoformat()}）",""]
    if cf is not None:
        t=(cf["total"] or [{"count":0,"sum":{"visits":0}}])[0]
        L+=[f"## アクセス（Cloudflare、{s}〜{e - dt.timedelta(days=1)}）",f"- ページビュー {t['count']:,}　訪問 {t['sum']['visits']:,}","","| ページ | PV |","|---|---:|"]
        L+=[f"| {x['dimensions']['requestPath']} | {x['count']:,} |" for x in cf["pages"]] or ["| （データなし） | |"]
        L+=["","参照元："+("、".join(f"{x['dimensions']['refererHost'] or '(直接)'} {x['count']}" for x in cf["refs"]) or "なし"),
            "国："+("、".join(f"{x['dimensions']['countryName']} {x['count']}" for x in cf["countries"]) or "なし"),
            "端末："+("、".join(f"{x['dimensions']['deviceType']} {x['count']}" for x in cf["devices"]) or "なし"),""]
    else: L+=["## アクセス","取得できませんでした："+cerr,""]
    if g is not None:
        t=(g["total"] or [{"clicks":0,"impressions":0,"ctr":0,"position":0}])[0]
        L+=[f"## Google検索（Search Console、{gs}〜{ge}）",f"- クリック {t['clicks']:,.0f}　表示回数 {t['impressions']:,.0f}　CTR {t['ctr']*100:.1f}%　平均掲載順位 {t['position']:.1f}","","| 検索語 | クリック | 表示 | 順位 |","|---|---:|---:|---:|"]
        L+=[f"| {x['keys'][0]} | {x['clicks']:.0f} | {x['impressions']:.0f} | {x['position']:.1f} |" for x in g["queries"]] or ["| （データなし） | | | |"]
        L+=["","| ページ | クリック | 表示 |","|---|---:|---:|"]+[f"| {x['keys'][0].replace('https://keizai-atlas.com','')} | {x['clicks']:.0f} | {x['impressions']:.0f} |" for x in g["pages"]] or ["| （データなし） | | |"]
    else: L+=["## Google検索","取得できませんでした："+gerr]
    if fb is not None:
        L+=["",f"## 読者の反応（{s}〜{e - dt.timedelta(days=1)}）","","**👍 役に立った**",""]
        L+=[f"- {x['page']}：{x['n']}" for x in fb["likes"]] or ["- （なし）"]
        L+=["","**届いた要望**",""]
        L+=[f"- {x['ts'][:10]} {x['page'] or ''}：{x['body']}".replace("\n"," ") for x in fb["requests"]] or ["- （なし）"]
    else: L+=["","## 読者の反応","取得できませんでした："+ferr]
    print("\n".join(L))
