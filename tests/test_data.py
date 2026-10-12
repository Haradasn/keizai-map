"""データの整合(data/*.json の形、導出値、県別の需給バランス、check_data、週次レポート)"""

import json
from conftest import R, S


def test_data_sanity():
    d = json.loads((R / "data/similarity_map.json").read_text())
    assert len(d["nodes"]) == 108 and 0.3 < d["rho"] < 1
    e = json.loads((R / "data/explorer_data.json").read_text())
    assert len(e["nodes"]) == 37 and len(e["edges"]) > 100


# ---- データ整合
def test_explorer_data_consistency():
    e = json.loads((R / "data/explorer_data.json").read_text())
    tot = sum(n["out"] for n in e["nodes"])
    assert 800 < tot < 1100, tot  # 兆円: 国内生産額の合計は約1,000兆円
    ids = {n["id"] for n in e["nodes"]}
    assert all(
        x["s"] in ids and x["t"] in ids and max(x.get("v") or 0, x.get("v20") or 0, x.get("v22") or 0) > 0
        for x in e["edges"]
    )
    assert all(0 <= n["grp"] < len(e["groups"]) for n in e["nodes"])


def test_chart_data_aligned():
    n2 = json.loads((R / "data/nowcast2_chart.json").read_text())
    for k, v in n2["meti"].items():
        assert len(v) == len(n2["months"]), k
    n1 = json.loads((R / "data/nowcast_chart.json").read_text())
    for k, v in n1["sppi"].items():
        assert len(v) == len(n1["months"]), k
    ic = json.loads((R / "data/icio_chart.json").read_text())
    for key in ("out", "dig", "digimp", "en", "enimp"):
        for c, v in ic[key].items():
            assert len(v) == len(ic["years"]) and all(0 <= x <= 100 for x in v), (key, c)


def test_similarity_groups_exist():
    d = json.loads((R / "data/similarity_map.json").read_text())
    codes = {n["c"] for n in d["nodes"]}
    for g, v in d["groups"].items():
        assert set(v["codes"]) <= codes, g
    assert set(d["coh"]) == set(d["groups"])


def test_derived_metrics_sane():
    import sys

    sys.path.insert(0, str(R / "scripts" / "build"))
    from derive import metrics

    M = metrics()
    assert 0 < float(M["sppi_avg_0"]) < 300 and float(M["fuel_peak"]) > float(M["fuel_0"])
    assert M["sppi_last"].endswith("月") and M["meti_last"].endswith("月")


def test_prefecture_pages_and_balance():
    d = json.loads((R / "data/pref_37.json").read_text(encoding="utf-8"))
    assert {
        "tokyo",
        "aichi",
        "osaka",
        "kanagawa",
        "saitama",
        "chiba",
        "hyogo",
        "okinawa",
        "fukuoka",
        "hokkaido",
        "tochigi",
        "yamanashi",
        "kyoto",
        "wakayama",
        "shiga",
        "kumamoto",
        "niigata",
        "toyama",
        "okayama",
        "mie",
        "kagoshima",
        "gunma",
        "tottori",
        "fukui",
    } <= set(d)
    known = {
        "tokyo": 209.8,
        "aichi": 80.0,
        "osaka": 72.1,
        "kanagawa": 61.5,
        "chiba": 43.5,
        "okinawa": 6.9,
        "fukuoka": 37.1,
        "hokkaido": 36.2,
        "shiga": 13.4,
        "kyoto": 18.0,
        "tochigi": 17.2,
        "niigata": 16.2,
        "kumamoto": 11.1,
        "mie": 18.7,
    }  # 各県の公表値(兆円)
    for k, p in d.items():
        assert k not in known or abs(p["total_out"] / 1e6 - known[k]) < 0.1, (k, p["total_out"])
        for o in p["sectors"]:
            assert abs(o["dom_dummy"] if False else (o["dem"] + o["exp"] - o["imp"] - o["out"])) <= max(
                2, o["out"] * 1e-6
            )
        assert (S / "prefecture" / f"{k}.html").exists()
    sm = (S / "sitemap.xml").read_text(encoding="utf-8")
    assert "/prefectures" in sm and "/prefecture/aichi" in sm


def test_weekly_report_runs_without_keys():
    """キーが無くても最後まで動き、各節に「取得できませんでした」が出ること(書き間違いで落ちないことの確認)"""
    import subprocess, os

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CF_API_TOKEN", "CF_ACCOUNT_ID", "GSC_SA_JSON", "FEEDBACK_KEY")
    }
    r = subprocess.run(
        ["python3", str(R / "scripts/ops/weekly_report.py")],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert r.returncode == 0 and r.stdout.count("取得できませんでした") == 3, (r.stdout, r.stderr)
    r = subprocess.run(
        ["python3", str(R / "scripts/ops/weekly_report.py"), "--check"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert "NameError" not in r.stdout and "未設定" in r.stdout, (r.stdout, r.stderr)


def test_data_checks_pass():
    """scripts/ops/check_data.py の形の検査が通ること(比較元なし)"""
    import subprocess, sys

    p = subprocess.run([sys.executable, str(R / "scripts/ops/check_data.py")], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-2000:]
