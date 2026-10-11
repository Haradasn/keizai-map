"""SNS共有用の画像(OGP, 1200x630)を生成する。data/ogp_cards.json(build_siteが出力)から site/og/<id>.png と site/og.png を作る。
日本語フォント(Noto Sans CJK)が必要なため、CIでは実行せず、手元で実行して生成物をコミットする。 実行: python3 scripts/build_ogp.py"""
import json,pathlib,sys
from PIL import Image,ImageDraw,ImageFont
R=pathlib.Path(__file__).resolve().parent.parent; S=R/"site"
PAL=json.loads((R/"pages/palette.json").read_text(encoding="utf-8"))
FB="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"; FR="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def font(path,sz): return ImageFont.truetype(path,sz,index=0)  # index0=JP
W,H=1200,630; BG=(11,17,32); FG=(226,232,240); MUT=(148,163,184)
def hexrgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def fit(d,text,path,maxw,sizes):
    for sz in sizes:
        f=font(path,sz)
        if d.textlength(text,font=f)<=maxw: return f
    return font(path,sizes[-1])
def wrap(d,text,f,maxw):
    lines=[];cur=""
    for ch in text:
        if d.textlength(cur+ch,font=f)>maxw and cur: lines.append(cur);cur=ch
        else: cur+=ch
    return lines+[cur]
def card(c):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); col=hexrgb(PAL["groups"][c["grp"]%len(PAL["groups"])])
    d.rectangle([0,0,18,H],fill=col)
    d.text((70,52),c["kind"],font=font(FR,28),fill=MUT)
    ft=font(FB,76); lines=wrap(d,c["title"],ft,1060)[:2]
    if len(lines)>1: ft=font(FB,64); lines=wrap(d,c["title"],ft,1060)[:2]
    y=104
    for ln in lines: d.text((70,y),ln,font=ft,fill=FG); y+=ft.size+14
    # 指標4つ
    y0=300; x=70
    for lab,val in c["stats"]:
        d.text((x,y0),lab,font=font(FR,22),fill=MUT); d.text((x,y0+34),val,font=fit(d,val,FB,250,[44,38,32,28]),fill=FG); x+=275
    # 行き先の構成
    if c["parts"]:
        d.text((70,430),"この産業の製品・サービスの行き先",font=font(FR,22),fill=MUT)
        xx=70; bw=1060
        for lab,sh,colr in c["parts"]:
            w=bw*sh
            if w<1: continue
            d.rectangle([xx,466,xx+w,506],fill=hexrgb(colr))
            if w>60: d.text((xx+w/2,486),f"{sh*100:.0f}%",font=font(FB,22),fill=BG,anchor="mm")
            xx+=w
        lx=70
        for lab,sh,colr in c["parts"]:
            if sh<0.02: continue
            d.rectangle([lx,524,lx+14,538],fill=hexrgb(colr)); t=lab; d.text((lx+22,520),t,font=font(FR,20),fill=MUT); lx+=int(d.textlength(t,font=font(FR,20)))+52
    d.text((70,568),"Keizai Atlas",font=font(FB,30),fill=(56,189,248)); d.text((290,574),"産業連関表で見る日本経済の地図帳｜keizai-atlas.com",font=font(FR,22),fill=MUT)
    return im
def top():
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); d.rectangle([0,0,18,H],fill=(56,189,248))
    d.text((74,96),"Keizai Atlas｜公的統計で読む日本経済",font=font(FR,30),fill=MUT)
    d.text((70,170),"統計から、",font=font(FB,92),fill=FG); d.text((70,290),"日本経済の“なるほど”を。",font=font(FB,92),fill=(56,189,248))
    x=74
    for lab in ("つながり","産業","地域","変化と世界"):
        w=d.textlength(lab,font=font(FR,28))+44; d.rounded_rectangle([x,452,x+w,506],radius=27,outline=MUT,width=2); d.text((x+22,479),lab,font=font(FR,28),fill=FG,anchor="lm"); x+=w+18
    d.text((74,560),"産業連関表などの公的統計を、趣味で集計して眺めています｜keizai-atlas.com",font=font(FR,24),fill=MUT); return im
if __name__=="__main__":
    cards=json.loads((R/"data/ogp_cards.json").read_text(encoding="utf-8")); (S/"og").mkdir(exist_ok=True)
    q=lambda im:im.quantize(64,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    q(top()).save(S/"og.png",optimize=True)
    for c in cards: q(card(c)).save(S/"og"/f"{c['id']}.png",optimize=True)
    print(len(cards),"cards")
