"""SNS共有用の画像(OGP, 1200x630)を生成する。data/ogp_cards.json(build_siteが出力)から site/og/<id>.png と site/og.png を作る。
日本語フォント(Noto Sans CJK)が必要なため、CIでは実行せず、手元で実行して生成物をコミットする。 実行: python3 scripts/build/build_ogp.py"""

import json, pathlib
from PIL import Image, ImageDraw, ImageFont

R = pathlib.Path(__file__).resolve().parents[2]
S = R / "site"
PAL = json.loads((R / "pages/palette.json").read_text(encoding="utf-8"))
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def font(path, sz):
    return ImageFont.truetype(path, sz, index=0)  # index0=JP


W, H = 1200, 630
BG = (13, 31, 45)  # 夜の海図の海の色(pages/palette.json の theme.night.bg)
FG = (226, 232, 240)
MUT = (148, 163, 184)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def fit(d, text, path, maxw, sizes):
    for sz in sizes:
        f = font(path, sz)
        if d.textlength(text, font=f) <= maxw:
            return f
    return font(path, sizes[-1])


def wrap(d, text, f, maxw):
    lines = []
    cur = ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + [cur]


def card(c):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    col = hexrgb(PAL["groups"][c["grp"] % len(PAL["groups"])])
    d.rectangle([0, 0, 18, H], fill=col)
    d.text((70, 52), c["kind"], font=font(FR, 28), fill=MUT)
    ft = font(FB, 76)
    lines = wrap(d, c["title"], ft, 1060)[:2]
    if len(lines) > 1:
        ft = font(FB, 64)
        lines = wrap(d, c["title"], ft, 1060)[:2]
    y = 104
    for ln in lines:
        d.text((70, y), ln, font=ft, fill=FG)
        y += ft.size + 14
    # 指標4つ
    y0 = 300
    x = 70
    for lab, val in c["stats"]:
        d.text((x, y0), lab, font=font(FR, 22), fill=MUT)
        d.text((x, y0 + 34), val, font=fit(d, val, FB, 250, [44, 38, 32, 28]), fill=FG)
        x += 275
    # 行き先の構成
    if c["parts"]:
        d.text((70, 430), "この産業の製品・サービスの行き先", font=font(FR, 22), fill=MUT)
        xx = 70
        bw = 1060
        for lab, sh, colr in c["parts"]:
            w = bw * sh
            if w < 1:
                continue
            d.rectangle([xx, 466, xx + w, 506], fill=hexrgb(colr))
            if w > 60:
                d.text((xx + w / 2, 486), f"{sh * 100:.0f}%", font=font(FB, 22), fill=BG, anchor="mm")
            xx += w
        lx = 70
        for lab, sh, colr in c["parts"]:
            if sh < 0.02:
                continue
            d.rectangle([lx, 524, lx + 14, 538], fill=hexrgb(colr))
            t = lab
            d.text((lx + 22, 520), t, font=font(FR, 20), fill=MUT)
            lx += int(d.textlength(t, font=font(FR, 20))) + 52
    d.text((70, 568), "Keizai Atlas", font=font(FB, 30), fill=(255, 115, 85))
    d.text((290, 574), "産業連関表で見る日本経済の地図帳｜keizai-atlas.com", font=font(FR, 22), fill=MUT)
    return im


def top():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 18, H], fill=(255, 115, 85))
    d.text((74, 96), "Keizai Atlas｜経済の地図帳", font=font(FR, 30), fill=MUT)
    d.text((70, 170), "あなたの県は、", font=font(FB, 92), fill=FG)
    d.text((70, 290), "何で稼いでいる？", font=font(FB, 92), fill=FG)
    x = 74
    for lab in ("つながり", "産業", "地域", "変化と世界"):
        w = d.textlength(lab, font=font(FR, 28)) + 44
        d.rounded_rectangle([x, 452, x + w, 506], radius=27, outline=MUT, width=2)
        d.text((x + 22, 479), lab, font=font(FR, 28), fill=FG, anchor="lm")
        x += w + 18
    d.text(
        (74, 560),
        "産業連関表などの公的統計を、趣味で集計して眺めています｜keizai-atlas.com",
        font=font(FR, 24),
        fill=MUT,
    )
    return im


# ---------- 県ごとの共有画像と、看板産業マップ(昼の地図帳の色: 海・紙・墨・朱)
SEA = (220, 235, 241)
PAPER = (251, 252, 250)
INK = (20, 35, 46)
SHU = (200, 54, 31)
SOFT = (74, 92, 104)
FK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
NOTE = "2020年の産業連関表を筆者が集計。政府・自治体が作成したものではありません｜keizai-atlas.com"


def blend(c, bg, a):
    return tuple(round(c[i] * a + bg[i] * (1 - a)) for i in range(3))


def pref_card(bp, slug, p):
    """県の共有画像: 県の形、看板産業の一文、産業の構成の帯(上=県、下=全国)。"""
    im = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(im)
    for ring in bp.silhouette_rings(bp.JIS[slug], 320, 8):
        d.polygon([(x + 56, y + 52) for x, y in ring], fill=PAPER, outline=INK, width=3)
    k = bp.kanban(p)
    x = 430
    d.text((x, 62), f"{p['name']}は、", font=font(FK, 62), fill=INK)
    d.text((x, 150), f"{k['n']}が", font=fit(d, f"{k['n']}が", FK, 710, [62, 54, 46, 40]), fill=INK)
    base = 372
    d.text((x, base), "全国平均の", font=font(FK, 50), fill=INK, anchor="ls")
    x += d.textlength("全国平均の", font=font(FK, 50)) + 14
    num = f"{k['lq']:.1f}"
    d.text((x, base + 6), num, font=font(FK, 150), fill=SHU, anchor="ls")
    x += d.textlength(num, font=font(FK, 150)) + 12
    d.text((x, base), "倍。", font=font(FK, 50), fill=INK, anchor="ls")
    # 産業の構成の帯(build_pref.face_data と同じ値。1000 の幅を 1088px に)
    sc, x0, y0 = 1.088, 56, 426
    for s in bp.face_data(slug, p)["segs"]:
        col = hexrgb(s["color"])
        tx, tw, nx, nw = (
            float(s[key]) * sc + (x0 if key in ("x", "nx") else 0) for key in ("x", "w", "nx", "nw")
        )
        pts = [float(v) for pair in s["band"].split() for v in pair.split(",")]
        d.polygon(
            [(pts[i] * sc + x0, y0 + (26 if pts[i + 1] < 50 else 70)) for i in range(0, 8, 2)],
            fill=blend(col, SEA, 0.38),
        )
        d.rectangle([tx, y0, tx + tw, y0 + 26], fill=col)
        d.rectangle([nx, y0 + 70, nx + nw, y0 + 96], fill=col)
    d.text(
        (56, 534),
        f"産業の構成（産出額に占める割合）。上の帯が{p['name']}、下の帯が全国",
        font=font(FR, 20),
        fill=SOFT,
    )
    d.text((56, 578), "Keizai Atlas", font=font(FB, 26), fill=INK)
    d.text((238, 584), NOTE, font=font(FR, 18), fill=SOFT)
    return im


def kanban_grid(d, tiles, ox, oy, tw, th, gap, detail):
    """看板産業マップのタイルを描く。detail=True は県名・産業名・倍率、False は県名だけ(小さい画像用)。"""
    for t in tiles:
        x, y = ox + t["col"] * (tw + gap), oy + t["row"] * (th + gap)
        short = t["name"] if t["name"] == "北海道" else t["name"][:-1]
        if not t["data"]:
            d.rectangle([x, y, x + tw, y + th], outline=blend(INK, SEA, 0.35), width=1)
            d.text((x + 8, y + 8), short, font=font(FR, 18 if detail else 15), fill=SOFT)
            if detail:
                d.text((x + 8, y + th - 30), "未掲載", font=font(FR, 16), fill=SOFT)
            continue
        band = 9 if detail else 12
        d.rectangle([x, y, x + tw, y + th], fill=PAPER)
        d.rectangle([x, y, x + tw, y + band], fill=hexrgb(t["color"]))
        if not detail:
            d.text((x + tw / 2, y + band + (th - band) / 2), short, font=font(FB, 17), fill=INK, anchor="mm")
            continue
        d.text((x + 7, y + 13), short, font=font(FR, 17), fill=SOFT)
        f = font(FB, 17)
        for i, ln in enumerate(wrap(d, t["ind"], f, tw - 12)[: (3 if th > 110 else 2)]):
            d.text((x + 7, y + 36 + i * 21), ln, font=f, fill=INK)
        d.text((x + 7, y + th - 8), f"{t['lq']}倍", font=font(FB, 22), fill=SHU, anchor="ls")


def kanban_images(bp, D):
    """看板産業マップの画像2枚: 投稿に付ける大きい画像(share/)と、リンクを貼ったときに出る画像(og/)。"""
    tiles = bp.kanban_tiles(D)
    n = sum(1 for t in tiles if t["data"])
    rule = f"県の産出額の{bp.pct(bp.KANBAN_MIN)}以上を占める産業のうち、"
    # 大きい画像。題名は、タイルの無い左上(日本海のあたり)に置く
    big = Image.new("RGB", (1600, 1720), SEA)
    d = ImageDraw.Draw(big)
    d.text((56, 60), "都道府県の", font=font(FK, 76), fill=INK)
    d.text((56, 156), "看板産業マップ", font=font(FK, 76), fill=INK)
    d.text((60, 270), rule, font=font(FR, 26), fill=INK)
    d.text((60, 308), "全国平均と比べて最も集中している産業（2020年）", font=font(FR, 26), fill=INK)
    d.text((60, 366), "数字は、全国平均の何倍か", font=font(FR, 22), fill=SOFT)
    kanban_grid(d, tiles, 46, 56, 104, 122, 4, True)
    F = bp._face_sources()
    x, y = 56, 1470
    for g, c in zip(F["names"], F["colors"]):
        w = int(d.textlength(g, font=font(FR, 20))) + 58
        if x + w > 1540:
            x, y = 56, y + 34
        d.rectangle([x, y + 4, x + 18, y + 22], fill=hexrgb(c))
        d.text((x + 26, y), g, font=font(FR, 20), fill=INK)
        x += w
    d.text(
        (56, 1560),
        f"タイルの上の線の色は産業の大分類。{n}都道府県を掲載（未掲載の県は、2020年の表を載せられていません）",
        font=font(FR, 20),
        fill=SOFT,
    )
    d.text((56, 1636), "Keizai Atlas", font=font(FB, 30), fill=INK)
    d.text((262, 1644), NOTE, font=font(FR, 20), fill=SOFT)
    # リンクを貼ったときに出る画像
    og = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(og)
    d.text((50, 50), "都道府県の", font=font(FK, 54), fill=INK)
    d.text((50, 118), "看板産業マップ", font=font(FK, 54), fill=INK)
    d.text((52, 212), "あなたの県は、", font=font(FB, 30), fill=INK)
    d.text((52, 254), "何で稼いでいる？", font=font(FB, 30), fill=SHU)
    kanban_grid(d, tiles, 290, 36, 60, 44, 4, False)
    d.text((50, 584), "Keizai Atlas｜筆者が集計。政府の作成ではありません", font=font(FR, 17), fill=SOFT)
    return big, og


if __name__ == "__main__":
    cards = json.loads((R / "data/ogp_cards.json").read_text(encoding="utf-8"))
    (S / "og").mkdir(exist_ok=True)
    q = lambda im: im.quantize(64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q(top()).save(S / "og.png", optimize=True)
    for c in cards:
        q(card(c)).save(S / "og" / f"{c['id']}.png", optimize=True)
    import build_pref as bp  # 県の形・看板産業・帯の値は、ページと同じ関数で作る

    D = json.loads((R / "data/pref_37.json").read_text(encoding="utf-8"))
    for slug, p in D.items():
        q(pref_card(bp, slug, p)).save(S / "og" / f"pref-{slug}.png", optimize=True)
    big, og = kanban_images(bp, D)
    (S / "share").mkdir(exist_ok=True)
    big.quantize(200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(
        S / "share" / "kanban-map.png", optimize=True
    )
    q(og).save(S / "og" / "kanban-map.png", optimize=True)
    print(len(D), "pref cards + kanban map")
    print(len(cards), "cards")
