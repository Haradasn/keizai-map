"""SNS共有用の画像(OGP, 1200x630)を生成する。site/og.png(トップなど)、site/og/<コード>.png(産業。data/ogp_cards.json から)、
site/og/pref-<slug>.png(県)、稼ぎ頭マップの画像を作る。色はどれも昼の地図帳(海・紙・墨・朱)。
日本語フォント(Noto Sans CJK)が必要なため、CIでは実行せず、手元で実行して生成物をコミットする。 実行: python3 scripts/build/build_ogp.py"""

import json, math, pathlib
from PIL import Image, ImageDraw, ImageFont

R = pathlib.Path(__file__).resolve().parents[2]
S = R / "site"
PAL = json.loads((R / "pages/palette.json").read_text(encoding="utf-8"))
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def font(path, sz):
    return ImageFont.truetype(path, sz, index=0)  # index0=JP


W, H = 1200, 630


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


# ---------- 県ごとの共有画像と、稼ぎ頭マップ(昼の地図帳の色: 海・紙・墨・朱)
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
    """県の共有画像: 県の形、稼ぎ頭(県外・海外にいちばん売っている産業)の一文、産業の構成の帯(上=県、下=全国)。"""
    im = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(im)
    for ring in bp.silhouette_rings(bp.JIS[slug], 320, 8):
        d.polygon([(x + 56, y + 52) for x, y in ring], fill=PAPER, outline=INK, width=3)
    (k, share), (k2, share2) = bp.kasegi_ranking(p, 2)
    x = 430
    d.text((x, 58), f"{p['name']}の稼ぎ頭は、", font=font(FK, 58), fill=INK)
    d.text((x, 140), f"{k['n']}。", font=fit(d, f"{k['n']}。", FK, 710, [62, 54, 46, 40]), fill=INK)
    base = 356
    lead = "県外・海外に売る額の"
    d.text((x, base), lead, font=font(FK, 40), fill=INK, anchor="ls")
    nx = x + d.textlength(lead, font=font(FK, 40)) + 14
    num = f"{share * 100:.0f}"
    d.text((nx, base + 6), num, font=font(FK, 150), fill=SHU, anchor="ls")
    nx += d.textlength(num, font=font(FK, 150)) + 8
    d.text((nx, base), "%", font=font(FK, 64), fill=SHU, anchor="ls")
    more = f"2番目は{k2['n']}（{bp.pct(share2)}）"
    gloss = bp.sector_gloss(k)
    if gloss:  # 名前だけでは伝わりにくい部門は、ひとこと説明を優先する
        more = f"{gloss}。{more}"
    elif k.get("lq"):
        more += f"。{k['n']}の集中度は、全国平均の{k['lq']:.1f}倍"
    d.text((x, 376), more, font=fit(d, more, FR, 720, [22, 20, 18, 16]), fill=SOFT)
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


# 出どころと行き先の図の帯の色(ページの .ioflow と同じ: 産業どうし=墨、付加価値と家計・投資・政府=黄土、海外=青)
OCHRE = (138, 90, 11)
BLUE = (11, 95, 143)
BAND = {
    "ind": blend(INK, PAPER, 0.3),
    "fin": blend(OCHRE, PAPER, 0.55),
    "sea": blend(BLUE, PAPER, 0.55),
    "etc": blend(INK, PAPER, 0.14),
}


def ribbon(x0, x1, a0, a1, c0, c1, steps=24):
    """帯の輪郭の点。外側の端(x0)の上下 a0〜a1 から、中央(x1)の上下 c0〜c1 へ、なめらかにつなぐ(ページの svg と同じ3次曲線)。"""

    def curve(ya, yc):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            u = 1 - t
            xm = (x0 + x1) / 2
            x = u**3 * x0 + 3 * u * u * t * xm + 3 * u * t * t * xm + t**3 * x1
            y = u**3 * ya + 3 * u * u * t * ya + 3 * u * t * t * yc + t**3 * yc
            pts.append((x, y))
        return pts

    return curve(a0, c0) + curve(a1, c1)[::-1]


def industry_card(bi, c):
    """産業・部門の共有画像: 名前、いちばん大きい行き先の一文、出どころと行き先の図。

    図の値と並べ方は、ページと同じ関数(build_industry.flow_layout)で作る。文字の大きさは、項目が多いほど小さくする。"""
    im = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(im)
    x = 56
    d.text((x, 38), c["kind"], font=font(FR, 24), fill=SOFT)
    d.text((x, 72), c["title"], font=fit(d, c["title"], FK, 1088, [66, 58, 50, 44]), fill=INK)
    base = 238
    lead = "行き先の"
    d.text((x, base), lead, font=font(FK, 40), fill=INK, anchor="ls")
    nx = x + d.textlength(lead, font=font(FK, 40)) + 12
    d.text((nx, base + 4), c["top_share"], font=font(FK, 112), fill=SHU, anchor="ls")
    nx += d.textlength(c["top_share"], font=font(FK, 112)) + 6
    d.text((nx, base), "%", font=font(FK, 52), fill=SHU, anchor="ls")
    nx += d.textlength("%", font=font(FK, 52)) + 10
    d.text((nx, base), f"は、{c['top_label']}。", font=font(FK, 40), fill=INK, anchor="ls")
    # 図: 紙の枠の中に、左のラベル・帯・右のラベル
    top, bottom, label_w = 268, 560, 318
    d.rectangle([x, top, W - x, bottom], fill=PAPER, outline=INK, width=2)
    items = lambda rows: [dict(label=label, href=None, value=value, kind=kind) for label, value, kind in rows]
    # 文字の大きさ・帯の太さ・項目のあいだを、項目が多いほど詰める。枠に収まる最初の組み合わせを使う
    room = bottom - top - 24
    for size, px, gap in (
        (21, 170, 6),
        (19, 170, 5),
        (17, 170, 5),
        (15, 170, 4),
        (15, 130, 3),
        (14, 90, 2),
        (13, 60, 2),
    ):
        layout = bi.flow_layout(
            items(c["flow"]["left"]),
            items(c["flow"]["right"]),
            px=px,
            gap=gap,
            pad=0,
            line=size + 6,
            label_em=(label_w - 14) / size,
        )
        if layout["height"] <= room:
            break
    assert layout["height"] <= room, (c["id"], c["title"], layout["height"])
    oy = top + (bottom - top - layout["height"]) / 2
    xl, xr, xc = x + 16 + label_w, W - x - 16 - label_w, W / 2
    fr, fb = font(FR, size), font(FB, size)
    for side, x_edge, anchor in ((layout["left"], xl, "r"), (layout["right"], xr, "l")):
        for it in side:
            d.polygon(
                [(px, py + oy) for px, py in ribbon(x_edge, xc, it["a0"], it["a1"], it["c0"], it["c1"])],
                fill=BAND[it["kind"]],
            )
            d.rectangle([x_edge - 2, it["a0"] + oy, x_edge + 2, it["a1"] + oy], fill=INK)
            # ラベル: 名前と金額(金額は太字)。1行に入らなければ、名前の下に金額
            name, amount = it["label"], it["amount"]
            wn, wa = d.textlength(name, font=fr), d.textlength(amount, font=fb)
            tx = x_edge - 12 if anchor == "r" else x_edge + 12
            cy = it["y"] + oy
            if wn + 8 + wa <= label_w - 14:
                if anchor == "r":
                    d.text((tx, cy), amount, font=fb, fill=INK, anchor="rm")
                    d.text((tx - wa - 8, cy), name, font=fr, fill=INK, anchor="rm")
                else:
                    d.text((tx, cy), name, font=fr, fill=INK, anchor="lm")
                    d.text((tx + wn + 8, cy), amount, font=fb, fill=INK, anchor="lm")
            else:
                lines = wrap(d, name, fr, label_w - 14)
                step = size + 5
                y0 = cy - step * len(lines) / 2
                for i, ln in enumerate(lines + [amount]):
                    d.text(
                        (tx, y0 + i * step),
                        ln,
                        font=fb if i == len(lines) else fr,
                        fill=INK,
                        anchor=anchor + "m",
                    )
    d.rectangle([xc - 7, layout["center"][0] + oy, xc + 7, layout["center"][1] + oy], fill=INK)
    d.text((x, 578), "Keizai Atlas", font=font(FB, 26), fill=INK)
    d.text((238, 584), NOTE, font=font(FR, 18), fill=SOFT)
    return im


def top(bp, D):
    """サイト全体の共有画像(トップページなど): 問いと、稼ぎ頭の産業の大分類で塗った日本地図。

    色は稼ぎ頭マップのタイルと同じ(build_pref.kasegi_tiles)。表を載せられていない県は白。"""
    im = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(im)
    tiles = {t["name"]: t for t in bp.kasegi_tiles(D)}
    geo = json.loads((S / "vendor/japan-pref.json").read_text(encoding="utf-8"))
    # 地図: 緯度37.5度で横を縮めた単純な投影。沖縄県と奄美などは、トップの立体地図(pages/prefmap.js)と同じく、
    # 関東の東の海上に寄せて枠で囲む
    dx, dy = 17.2, 5.9
    k = math.cos(math.radians(37.5))
    lon0, lon1, lat1 = 128.6, 149.0, 45.8
    sc = min(540 / ((lon1 - lon0) * k), 524 / (lat1 - 29.6))
    ox, oy = 1164 - (lon1 - lon0) * k * sc, 30
    box = [1e9, 1e9, -1e9, -1e9]
    for f in geo["features"]:
        t = tiles.get(f["properties"]["name"])
        fill = hexrgb(t["color"]) if t and t["data"] else PAPER
        g = f["geometry"]
        for poly in g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]:
            ring = poly[0]
            south = sum(c[1] for c in ring) / len(ring) < 29.5
            moved = f["properties"]["id"] == 47 or (f["properties"]["id"] == 46 and south)
            pts = [
                (ox + (lon + dx * moved - lon0) * k * sc, oy + (lat1 - lat - dy * moved) * sc)
                for lon, lat in ring
            ]
            if moved:
                for px, py in pts:
                    box = [min(box[0], px), min(box[1], py), max(box[2], px), max(box[3], py)]
            d.polygon(pts, fill=fill, outline=INK)
    d.rectangle([box[0] - 12, box[1] - 12, box[2] + 12, box[3] + 12], outline=blend(INK, SEA, 0.45), width=1)
    x = 56
    d.text((x, 38), "Keizai Atlas｜経済の地図帳", font=font(FR, 26), fill=SOFT)
    d.text((x, 82), "あなたの県は、", font=font(FK, 74), fill=INK)
    d.text((x, 172), "何で稼いでいる？", font=font(FK, 74), fill=INK)
    n = sum(1 for t in tiles.values() if t["data"])
    d.text((x, 280), "県外・海外にいちばん売っている産業を、", font=font(FR, 23), fill=INK)
    d.text((x, 312), f"{n}都道府県の産業連関表で調べました", font=font(FR, 23), fill=INK)
    # 凡例: 地図に出ている色だけ(稼ぎ頭の産業の大分類)。白は、表を載せられていない県
    F = bp._face_sources()
    used = {t["color"] for t in tiles.values() if t["data"]}
    items = [(hexrgb(c), g) for g, c in zip(F["names"], F["colors"]) if c in used]
    items += [(hexrgb(c), "分類なし（東京都の本社）") for c in sorted(used - set(F["colors"]))]
    if len(tiles) > n:
        items.append((PAPER, f"未掲載（{len(tiles) - n}県）"))
    y = 362
    d.text((x, y), "色は、稼ぎ頭の産業の大分類", font=font(FR, 19), fill=SOFT)
    for i, (c, g) in enumerate(items):
        yy = y + 32 + i * 26
        d.rectangle([x, yy + 4, x + 16, yy + 20], fill=c, outline=INK if c == PAPER else None)
        d.text((x + 26, yy), g, font=font(FR, 19), fill=INK)
    d.text((x, 592), NOTE, font=font(FR, 17), fill=SOFT)
    return im


def kasegi_grid(d, tiles, ox, oy, tw, th, gap, detail):
    """稼ぎ頭マップのタイルを描く。detail=True は県名・産業名・割合、False は県名だけ(小さい画像用)。"""
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
        d.text((x + 7, y + th - 8), t["share"], font=font(FB, 22), fill=SHU, anchor="ls")


def kasegi_images(bp, D):
    """稼ぎ頭マップの画像2枚: 投稿に付ける大きい画像(share/)と、リンクを貼ったときに出る画像(og/)。"""
    tiles = bp.kasegi_tiles(D)
    n = sum(1 for t in tiles if t["data"])
    # 大きい画像。題名は、タイルの無い左上(日本海のあたり)に置く
    big = Image.new("RGB", (1600, 1720), SEA)
    d = ImageDraw.Draw(big)
    d.text((56, 60), "都道府県の", font=font(FK, 76), fill=INK)
    d.text((56, 156), "稼ぎ頭マップ", font=font(FK, 76), fill=INK)
    d.text((60, 270), "県外・海外にいちばん売っている産業（2020年）", font=font(FR, 26), fill=INK)
    d.text((60, 312), "数字は、その県が県外・海外に売る額に占める割合", font=font(FR, 26), fill=INK)
    d.text(
        (60, 368),
        "「商業」は卸売・小売のこと。「本社」は東京都の表だけにある部門",
        font=font(FR, 21),
        fill=SOFT,
    )
    kasegi_grid(d, tiles, 46, 56, 104, 122, 4, True)
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
        f"タイルの上の線の色は産業の大分類（灰色は分類なし）。{n}都道府県を掲載（未掲載の県は、2020年の表を載せられていません）",
        font=font(FR, 20),
        fill=SOFT,
    )
    d.text((56, 1636), "Keizai Atlas", font=font(FB, 30), fill=INK)
    d.text((262, 1644), NOTE, font=font(FR, 20), fill=SOFT)
    # リンクを貼ったときに出る画像
    og = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(og)
    d.text((50, 50), "都道府県の", font=font(FK, 54), fill=INK)
    d.text((50, 118), "稼ぎ頭マップ", font=font(FK, 54), fill=INK)
    d.text((52, 212), "あなたの県は、", font=font(FB, 30), fill=INK)
    d.text((52, 254), "何で稼いでいる？", font=font(FB, 30), fill=SHU)
    kasegi_grid(d, tiles, 290, 36, 60, 44, 4, False)
    d.text((50, 584), "Keizai Atlas｜筆者が集計。政府の作成ではありません", font=font(FR, 17), fill=SOFT)
    return big, og


if __name__ == "__main__":
    cards = json.loads((R / "data/ogp_cards.json").read_text(encoding="utf-8"))
    (S / "og").mkdir(exist_ok=True)
    q = lambda im: im.quantize(64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    import build_industry as bi  # 出どころと行き先の図の並べ方は、ページと同じ関数で作る

    for c in cards:
        q(industry_card(bi, c)).save(S / "og" / f"{c['id']}.png", optimize=True)
    import build_pref as bp  # 県の形・稼ぎ頭・帯の値は、ページと同じ関数で作る

    D = json.loads((R / "data/pref_37.json").read_text(encoding="utf-8"))
    q(top(bp, D)).save(S / "og.png", optimize=True)
    for slug, p in D.items():
        q(pref_card(bp, slug, p)).save(S / "og" / f"pref-{slug}.png", optimize=True)
    big, og = kasegi_images(bp, D)
    (S / "share").mkdir(exist_ok=True)
    big.quantize(200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(
        S / "share" / "kasegi-map.png", optimize=True
    )
    q(og).save(S / "og" / "kasegi-map.png", optimize=True)
    print(len(D), "pref cards + kasegi map")
    print(len(cards), "cards")
