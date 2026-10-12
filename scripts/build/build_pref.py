"""都道府県ページ(/prefectures, /prefecture/<slug>)を生成する。 data/pref_37.json は pipeline/pref_build.py の出力。
数値は各県が公表した2020年の産業連関表(統合大分類・37部門ベース)を、そのまま集計したもの。
マークアップは templates/ にあり、ここでは表示する値(整形済みの文字列・座標)を用意して描画を呼ぶ。"""

import json
import pathlib

from _shell import breadcrumb_head
from _tpl import render
from build_industry import pct

R = pathlib.Path(__file__).resolve().parents[2]

# 県のslug → 都道府県コード(JIS X 0401)。立体地図のデータのキーになる
JIS = {
    "hokkaido": 1,
    "tochigi": 9,
    "gunma": 10,
    "saitama": 11,
    "chiba": 12,
    "tokyo": 13,
    "kanagawa": 14,
    "niigata": 15,
    "toyama": 16,
    "fukui": 18,
    "yamanashi": 19,
    "mie": 24,
    "shiga": 25,
    "kyoto": 26,
    "osaka": 27,
    "hyogo": 28,
    "wakayama": 30,
    "tottori": 31,
    "okayama": 33,
    "fukuoka": 40,
    "kumamoto": 43,
    "kagoshima": 46,
    "okinawa": 47,
    "aichi": 23,
}

# 特化係数を「集中している」とみなす産出額割合の下限(0.5%)。これ未満は値が不安定
MIN_SHARE = 0.005


def tril(x):
    """百万円→兆円。"""
    return f"{x / 1e6:.1f}"


def pct_or_dash(value, digits=0):
    """割合を「12%」の形に。値が無いときは「−」。"""
    return pct(value, digits) if value is not None else "−"


def specialized_sectors(sectors):
    """特化係数の高い順に並べた部門(産出額割合が下限以上のもの)。"""
    return sorted([o for o in sectors if o["lq"] and o["share"] >= MIN_SHARE], key=lambda o: -o["lq"])


# ---------- SVGグラフの座標計算(描画は templates/_charts.html.j2)


def lq_bar_data(items):
    """特化係数(全国=1)の横棒の座標。items=[(名前, 特化係数)]。"""
    width = 640
    left = 170
    max_value = max(max(v for _, v in items), 1.5)
    bar_area = width - left - 50
    height = 26 * len(items) + 8
    bars = []
    for i, (name, value) in enumerate(items):
        y = 4 + i * 26
        bar_width = bar_area * value / max_value
        bars.append(
            dict(
                name=name,
                text_y=y + 15,
                rect_y=y + 3,
                bar_width=f"{bar_width:.1f}",
                value_x=f"{left + bar_width + 6:.1f}",
                value_y=y + 16,
                value=f"{value:.2f}",
            )
        )
    return dict(
        width=width,
        height=height,
        left=left,
        label_x=left - 8,
        base_x=f"{left + bar_area * 1 / max_value:.1f}",
        bars=bars,
    )


# ---------- 県別の立体地図


def build_map(page, D):
    """県別の立体地図ページと、その地図が読むデータ(pref-map-data.js)・スクリプトを書き出す。"""
    nat = json.loads((R / "data" / "explorer_data.json").read_text(encoding="utf-8"))["nodes"]
    inds = {n["id"]: n["name"] for n in nat if n["id"] not in ("69",)}
    prefs = {}
    for k, p in D.items():
        sectors = {}
        for o in p["sectors"]:
            if o["c"] == "HQ" or len(o.get("nat_codes", [o["c"]])) != 1:
                continue  # 本社(東京のみ)と、北海道の合算部門は除く
            sectors[o.get("nat_codes", [o["c"]])[0]] = [
                round(o["out"] / 1e6, 4),
                (round(o["lq"], 3) if o["lq"] else None),
            ]
        prefs[JIS[k]] = dict(
            n=p["name"],
            g=k,
            t=round(p["total_out"] / 1e6, 3),
            va=round(p["total_va"] / p["total_out"], 3),
            s=sectors,
        )
    S = R / "site"
    (S / "pref-map-data.js").write_text(
        "window.PREF_MAP="
        + json.dumps(dict(inds=inds, prefs=prefs), ensure_ascii=False, separators=(",", ":"))
        + ";",
        encoding="utf-8",
    )
    (S / "prefmap.js").write_text((R / "pages" / "prefmap.js").read_text(encoding="utf-8"), encoding="utf-8")
    (S / "insights.js").write_text(
        (R / "pages" / "insights.js").read_text(encoding="utf-8"), encoding="utf-8"
    )
    body = render("prefecture_map.html.j2", industries=list(inds.items()), count=len(D))
    page(
        "prefecture-map.html",
        "県別の産業を立体地図で見る｜Keizai Atlas",
        "産業を選ぶと、その産業の産出額が大きい県が立ち上がる3D地図。色は特化係数。各都道府県の2020年産業連関表から作成。",
        body,
    )


# ---------- 県ごとのページ


def sector_row(o):
    """県ページの「部門の一覧」表の1行。"""
    return [
        o["n"],
        tril(o["out"]),
        pct(o["share"], 1),
        (pct(o["nat_share"], 1) if o["nat_share"] else "−"),
        (f"{o['lq']:.2f}" if o["lq"] else "−"),
        pct_or_dash(o["va_ratio"]),
        pct(o["exp_ratio"]),
        pct_or_dash(o["imp_ratio"]),
    ]


def build_prefecture_page(slug, p, page, site_url):
    """県1つ分のページを書き出す。"""
    name = p["name"]
    total = p["total_out"]
    sectors = p["sectors"]
    ranked = specialized_sectors(sectors)
    top = ranked[:8]
    low = ranked[-3:][::-1]
    hq = [o for o in sectors if o["c"] == "HQ"]
    export_share = pct(p["exp_total"] / total)
    import_share = pct(p["imp_total"] / total)
    top_text = "、".join(f"{o['n']}（{o['lq']:.1f}）" for o in top[:3])
    description = (
        f"{name}の産業構造（{p['year']}年産業連関表）。産出額{tril(total)}兆円。"
        f"全国より集中している産業は{top_text}。全国との比較、移輸出入の割合。"
    )
    body = render(
        "prefecture.html.j2",
        name=name,
        year=p["year"],
        output=tril(total),
        value_added=tril(p["total_va"]),
        export_share=export_share,
        import_share=import_share,
        stats=[
            [f"産出額（{p['year']}年）", f"{tril(total)}兆円"],
            ["付加価値率", pct(p["total_va"] / total)],
            ["移輸出（産出額比）", export_share],
            ["移輸入（産出額比）", import_share],
        ],
        chart=lq_bar_data([(o["n"], o["lq"]) for o in top]),
        low=[dict(name=o["n"], lq=f"{o['lq']:.2f}") for o in low],
        hq_share=pct(hq[0]["share"], 1) if hq else None,
        note=p.get("note") or None,
        rows=[sector_row(o) for o in sorted(sectors, key=lambda o: -o["out"])],
        source_url=p["url"],
    )
    breadcrumb = breadcrumb_head([("県別の産業構造", site_url + "/prefectures"), (name, None)])
    page(
        f"prefecture/{slug}.html",
        f"{name}の産業構造・得意な産業｜Keizai Atlas",
        description,
        body,
        breadcrumb,
    )


# ---------- 県別の一覧ページ


def heat_cell(o):
    """特化係数ヒートマップのセル。値が無ければ None。色は特化係数が1.05を超える(割合が下限以上の)ものだけ。"""
    if not o or not o["lq"]:
        return None
    lq = o["lq"]
    small = o["share"] < MIN_SHARE
    colored = lq > 1.05 and not small
    return dict(
        text=f"{lq:.1f}",
        small=small,
        # 文字を読みやすく保つため、色の濃さは 0.45 まで(コントラスト 4.5:1 以上)
        alpha=f"{min(0.45, (lq - 1) / 6.6):.2f}" if colored else None,
    )


def build_prefectures_page(D, page):
    """県別の一覧ページ(カード・比較表・特化係数のヒートマップ)を書き出す。"""
    national = json.loads((R / "data" / "explorer_data.json").read_text(encoding="utf-8"))["nodes"]
    cards = [
        dict(
            slug=slug,
            name=p["name"],
            output=tril(p["total_out"]),
            top_names=[o["n"] for o in specialized_sectors(p["sectors"])[:3]],
        )
        for slug, p in D.items()
    ]
    compare = [
        [
            {"href": f"prefecture/{slug}.html", "text": p["name"]},
            tril(p["total_out"]),
            pct(p["total_va"] / p["total_out"]),
            pct(p["exp_total"] / p["total_out"]),
            pct(p["imp_total"] / p["total_out"]),
        ]
        for slug, p in D.items()
    ]
    compare.sort(key=lambda row: -float(row[1]))  # 産出額の大きい順(同額は元の順)
    # ヒートマップの列は産出額の大きい順。北海道は部門の分け方が違うので入れない
    order = sorted([k for k in D if not D[k].get("coarse")], key=lambda k: -D[k]["total_out"])
    heat_columns = [dict(slug=k, label=D[k]["name"].rstrip("都府県")) for k in order]
    heat_rows = [
        dict(
            name=node["name"],
            cells=[
                heat_cell(next((o for o in D[k]["sectors"] if o["c"] == node["id"]), None)) for k in order
            ],
        )
        for node in national
    ]
    names = [p["name"] for p in D.values()]
    body = render(
        "prefectures.html.j2",
        names=names,
        cards=cards,
        compare_rows=compare,
        heat_columns=heat_columns,
        heat_rows=heat_rows,
    )
    page(
        "prefectures.html",
        f"県別の産業構造（東京・愛知・大阪など{len(D)}都道府県）｜Keizai Atlas",
        f"{'・'.join(names)}の2020年産業連関表から、産業構造と全国との違い（特化係数）、移輸出入の割合を比べる。",
        body,
    )


def build(page, S, SITE_URL):
    """県別のページ一式を書き出し、ページのパス一覧を返す。"""
    D = json.loads((R / "data" / "pref_37.json").read_text(encoding="utf-8"))
    (S / "prefecture").mkdir(exist_ok=True)
    paths = ["prefectures"]
    for slug, p in D.items():
        build_prefecture_page(slug, p, page, SITE_URL)
        paths.append(f"prefecture/{slug}")
    build_prefectures_page(D, page)
    build_map(page, D)
    paths.append("prefecture-map")
    return paths
