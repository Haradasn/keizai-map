"""data/ の検査。サイトが使うデータの「形」と、前回(比較元の git の版)からの変化を確かめる。

  python3 scripts/check_data.py                 # 形の検査だけ
  python3 scripts/check_data.py --base origin/main [--github] [--report out.md]

- 形の検査で問題があれば終了コード 1(CI・月次更新を止める)。
- 前回からの変化は、異常と言い切れない(統計の改訂はある)ので警告として報告するだけ。
  ただし「最新月が古くなった」「月が消えた」「行が消えた」は誤った取得の可能性が高いので失敗にする。
- --github で GitHub Actions のアノテーションも出す。--report で Markdown の報告を書き出す(PR 本文用)。
"""

import argparse
import csv
import io
import json
import math
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parent.parent
D = R / "data"

# 月次の系列: ファイル → months と同じ長さであるべき系列(「a.*」は a の下の全系列)
SERIES = {
    "fx_chart.json": ["yen", "contract", "fx"],
    "nowcast_chart.json": ["sppi.*", "cgpi.*"],
    "nowcast2_chart.json": ["meti.*"],
}
REVISION_WARN = 0.05  # 過去の月の値がこれ以上(相対)変わったら警告
CHANGE_WARN = 0.20  # 月次以外の数値がこれ以上(相対)変わったら警告
MAX_LISTED = 8  # 1ファイルで報告する変化の数の上限


class Result:
    def __init__(self):
        self.errors = []  # (ファイル, 内容)
        self.warnings = []
        self.notes = []

    def error(self, f, msg):
        self.errors.append((f, msg))

    def warn(self, f, msg):
        self.warnings.append((f, msg))

    def note(self, f, msg):
        self.notes.append((f, msg))


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def bad_float(x):
    return isinstance(x, float) and (math.isnan(x) or math.isinf(x))


def get(o, path):
    for k in path.split("."):
        o = o[k]
    return o


def series_of(d, specs):
    """SERIES の指定を {名前: 値の列} に展開する"""
    out = {}
    for s in specs:
        if s.endswith(".*"):
            for k, v in get(d, s[:-2]).items():
                out[f"{s[:-2]}.{k}"] = v
        else:
            out[s] = get(d, s)
    return out


def read_csv(text):
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    return rows[0], rows[1:]


def leaves(o, path=""):
    """JSON の数値の葉を {パス: 値} にする"""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")
    elif is_num(o):
        yield path, o


# ---------------------------------------------------------------- 形の検査
def check_csv(name, text, r):
    head, rows = read_csv(text)
    # 1列目だけは空でもよい(pandas の行ラベル)
    if len(set(head)) != len(head) or any(not h.strip() for h in head[1:]):
        r.error(name, "列名が空、または重複しています")
    for i, row in enumerate(rows, 2):
        if len(row) != len(head):
            r.error(name, f"{i}行目の列数が {len(row)}(見出しは {len(head)})")
            return
        for h, v in zip(head, row):
            if v.strip().lower() in ("nan", "inf", "-inf", "infinity"):
                r.error(name, f"{i}行目 {h} が {v}")
                return
    if not rows:
        r.error(name, "データ行がありません")


def check_json_generic(name, d, r):
    for p, v in leaves(d):
        if bad_float(v):
            r.error(name, f"{p} が {v}")
            return


def check_series(name, d, r):
    months = d.get("months", [])
    if not all(isinstance(m, str) and re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", m) for m in months):
        r.error(name, "months に YYYYMM 以外の値があります")
        return
    if months != sorted(set(months)):
        r.error(name, "months が昇順でないか、重複があります")
    for k, v in series_of(d, SERIES[name]).items():
        if len(v) != len(months):
            r.error(name, f"{k} の長さ {len(v)} が months({len(months)})と違います")
        elif not all(x is None or is_num(x) for x in v):
            r.error(name, f"{k} に数値以外の値があります")
        elif v and v[-1] is None and all(x is None for x in v[-3:]):
            r.warn(name, f"{k} の直近3か月が空です")


def check_specific(r):
    """ファイルごとの決まりごと(件数・範囲・つながり)"""
    nodes = list(csv.DictReader(io.StringIO((D / "nodes.csv").read_text(encoding="utf-8-sig"))))
    levels = {lv: sum(n["level"] == lv for n in nodes) for lv in ("108", "37")}
    if levels != {"108": 108, "37": 37}:
        r.error("nodes.csv", f"部門数が想定と違います: {levels}")
    if any(n["output"] and float(n["output"]) < 0 for n in nodes):
        r.error("nodes.csv", "生産額が負の部門があります")

    # 表の整合性(build_graph.py が出す): 最大差・残差は丸めの範囲(10億円単位で 1 未満)
    head, rows = read_csv((D / "checks.csv").read_text(encoding="utf-8-sig"))
    for label, v in rows:
        if ("差" in label) and abs(float(v)) >= 1.0:
            r.error("checks.csv", f"{label} が {float(v):g}(1 未満のはず)")

    ids = {n["id"] for n in nodes}
    edges = list(csv.DictReader(io.StringIO((D / "edges.csv").read_text(encoding="utf-8-sig"))))
    unknown = {e[k] for e in edges for k in ("src", "dst") if e[k].startswith("S") and e[k] not in ids}
    if unknown:
        r.error("edges.csv", f"nodes.csv に無い部門: {sorted(unknown)[:5]}")

    a37 = list(csv.DictReader(io.StringIO((D / "analysis_37.csv").read_text(encoding="utf-8-sig"))))
    if len(a37) != 37:
        r.error("analysis_37.csv", f"{len(a37)} 行(37 のはず)")
    for row in a37:
        for col in ("輸入依存度", "付加価値率"):
            if not -0.05 <= float(row[col]) <= 1.05:
                r.error("analysis_37.csv", f"{row['name']} の {col} が範囲外: {row[col]}")

    ic = json.loads((D / "import_content_37.json").read_text(encoding="utf-8"))
    if len(ic["rows"]) != 37:
        r.error("import_content_37.json", f"{len(ic['rows'])} 行(37 のはず)")
    for row in ic["rows"]:
        if not 0 <= row["direct"] <= row["total"] + 1e-9 <= 1.0 + 1e-9:
            r.error("import_content_37.json", f"{row['name']}: 0 ≤ 直接 ≤ 全体 ≤ 1 になっていません")

    ex = json.loads((D / "explorer_data.json").read_text(encoding="utf-8"))
    eids = {n["id"] for n in ex["nodes"]}
    if len(eids) != 37:
        r.error("explorer_data.json", f"部門数 {len(eids)}(37 のはず)")
    if any(e["s"] not in eids or e["t"] not in eids for e in ex["edges"]):
        r.error("explorer_data.json", "部門に無いつながりがあります")

    pref = json.loads((D / "pref_37.json").read_text(encoding="utf-8"))
    for k, p in pref.items():
        share = sum(s["share"] for s in p["sectors"])
        if abs(share - 1) > 0.01:
            r.error("pref_37.json", f"{k}: 構成比の合計が {share:.3f}")
        if any(s["out"] < 0 for s in p["sectors"]):
            r.error("pref_37.json", f"{k}: 生産額が負の部門があります")


def check_shape(r):
    for f in sorted(D.glob("*.csv")):
        check_csv(f.name, f.read_text(encoding="utf-8-sig"), r)
    for f in sorted(D.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        check_json_generic(f.name, d, r)
        if f.name in SERIES:
            check_series(f.name, d, r)
    try:
        check_specific(r)
    except (KeyError, ValueError, TypeError) as e:
        r.error("data", f"想定した列・キーがありません: {e!r}")


# ---------------------------------------------------------------- 前回との比較
def git_show(base, name):
    p = subprocess.run(
        ["git", "show", f"{base}:data/{name}"],
        cwd=R,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return p.stdout if p.returncode == 0 else None


def rel(a, b):
    if a == b:
        return 0.0
    return abs(b - a) / max(abs(a), abs(b), 1e-9)


def compare_series(name, old, new, r):
    om, nm = old["months"], new["months"]
    if nm and om and nm[-1] < om[-1]:
        r.error(name, f"最新月が古くなりました({om[-1]} → {nm[-1]})")
    lost = sorted(set(om) - set(nm))
    if lost:
        r.error(name, f"前回あった月がなくなりました: {lost[:3]}")
    added = [m for m in nm if m not in set(om)]
    if added:
        r.note(name, f"追加された月: {added[0]}〜{added[-1]}({len(added)}か月)")
    os_, ns = series_of(old, SERIES[name]), series_of(new, SERIES[name])
    idx = {m: i for i, m in enumerate(om)}
    revised = []
    for k, v in ns.items():
        if k not in os_:
            r.note(name, f"新しい系列: {k}")
            continue
        for j, m in enumerate(nm):
            i = idx.get(m)
            if i is None:
                continue
            a, b = os_[k][i], v[j]
            if a is not None and b is not None and rel(a, b) > REVISION_WARN:
                revised.append((rel(a, b), f"{k} {m}: {a} → {b}"))
    for k in set(os_) - set(ns):
        r.warn(name, f"系列がなくなりました: {k}")
    for _, msg in sorted(revised, reverse=True)[:MAX_LISTED]:
        r.warn(name, f"過去の値が {REVISION_WARN:.0%} 超改訂: {msg}")


def compare_csv(name, old, new, r):
    oh, orows = read_csv(old)
    nh, nrows = read_csv(new)
    if set(oh) - set(nh):
        r.error(name, f"列がなくなりました: {sorted(set(oh) - set(nh))[:5]}")
    key = oh[0]
    if key not in nh:
        return
    ki = nh.index(key)
    o = {row[0]: dict(zip(oh, row)) for row in orows}
    n = {row[ki]: dict(zip(nh, row)) for row in nrows}
    if len(o) != len(orows) or len(n) != len(nrows):
        return  # 1列目が一意でない表(つながりの表など)は行単位では比べない
    if set(o) - set(n):
        r.error(name, f"行がなくなりました: {sorted(set(o) - set(n))[:5]}")
    if set(n) - set(o):
        r.note(name, f"追加された行: {len(set(n) - set(o))}")
    changed = []
    for k in set(o) & set(n):
        for c in set(oh) & set(nh):
            try:
                a, b = float(o[k][c]), float(n[k][c])
            except ValueError:
                continue
            if rel(a, b) > CHANGE_WARN and max(abs(a), abs(b)) > 1e-6:
                changed.append((rel(a, b), f"{k} {c}: {a:g} → {b:g}"))
    for _, msg in sorted(changed, reverse=True)[:MAX_LISTED]:
        r.warn(name, f"{CHANGE_WARN:.0%} 超の変化: {msg}")


def compare_json(name, old, new, r):
    o, n = dict(leaves(old)), dict(leaves(new))
    gone = sorted(set(o) - set(n))
    if gone:
        r.warn(name, f"なくなった値: {len(gone)} 件(例: {gone[0]})")
    added = set(n) - set(o)
    if added:
        r.note(name, f"追加された値: {len(added)} 件")
    changed = [
        (rel(o[k], n[k]), f"{k}: {o[k]:g} → {n[k]:g}")
        for k in set(o) & set(n)
        if rel(o[k], n[k]) > CHANGE_WARN and max(abs(o[k]), abs(n[k])) > 1e-6
    ]
    for _, msg in sorted(changed, reverse=True)[:MAX_LISTED]:
        r.warn(name, f"{CHANGE_WARN:.0%} 超の変化: {msg}")


def compare(base, r):
    for f in sorted(list(D.glob("*.csv")) + list(D.glob("*.json"))):
        old = git_show(base, f.name)
        if old is None:
            r.note(f.name, "新しいファイル")
            continue
        new = f.read_text(encoding="utf-8")
        if old.lstrip("﻿") == new.lstrip("﻿"):
            continue
        r.note(f.name, "変更あり")
        if f.suffix == ".csv":
            compare_csv(f.name, old, new, r)
        elif f.name in SERIES:
            compare_series(f.name, json.loads(old), json.loads(new), r)
        else:
            compare_json(f.name, json.loads(old), json.loads(new), r)


# ---------------------------------------------------------------- 出力
def report(r, base):
    out = ["### データの検査", ""]
    if base:
        out.append(f"比較元: `{base}`")
        out.append("")
    if not (r.errors or r.warnings or r.notes):
        out.append("問題なし(前回からの変更もなし)")
    for title, items in (("❌ エラー", r.errors), ("⚠️ 確認", r.warnings), ("変更", r.notes)):
        if items:
            out.append(f"**{title}**")
            out += [f"- `{f}` {m}" for f, m in items]
            out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="比較元の git の版(例: origin/main, HEAD)")
    ap.add_argument("--github", action="store_true", help="GitHub Actions のアノテーションを出す")
    ap.add_argument("--report", help="Markdown の報告の出力先")
    a = ap.parse_args()

    r = Result()
    check_shape(r)
    if a.base:
        compare(a.base, r)
    text = report(r, a.base)
    print(text)
    if a.report:
        pathlib.Path(a.report).write_text(text + "\n", encoding="utf-8")
    if a.github:
        for f, m in r.errors:
            print(f"::error file=data/{f}::{m}")
        for f, m in r.warnings:
            print(f"::warning file=data/{f}::{m}")
    sys.exit(1 if r.errors else 0)


if __name__ == "__main__":
    main()
