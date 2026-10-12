"""見た目の差分。2つの site/ (変更前・変更後)を同じ条件で撮影し、変わったページを報告する。

  python3 scripts/ops/visual_diff.py BEFORE_SITE AFTER_SITE OUT_DIR

- 1280px と 390px で各ページを撮影し、画素の差がしきい値を超えたページを一覧にする。
- 動く部分(WebGL の canvas、カルーセル)は塗りつぶして比べる(毎回違うため)。
- OUT_DIR に「変更前 | 変更後 | 差分」を並べた画像と summary.md を書き出す。CI では PR に添付する。
- 失敗にはしない(見た目の変更は意図したものが多いので、人が画像で確認する)。
"""

import functools
import http.server
import pathlib
import sys
import tempfile
import threading

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

PAGES = [
    "index",
    "explorer",
    "prefecture-map",
    "prefectures",
    "prefecture/tokyo",
    "industries",
    "industry/66",
    "fx",
    "latest",
    "similarity",
    "international",
    "changelog",
    "glossary",
    "guide",
    "about",
]
WIDTHS = [1280, 390]
MAX_HEIGHT = 6000  # 長いページは上から 6000px まで
THRESHOLD = 0.001  # 変わった画素の割合がこれを超えたら「変更あり」

# 撮影を安定させる: アニメーションを止め、動く要素を隠す
FREEZE_CSS = """
*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }
canvas { visibility: hidden !important; }
"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    h = functools.partial(Quiet, directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def shoot(browser, base, name, width, path):
    pg = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    pg.add_init_script("try{localStorage.setItem('theme','night')}catch(e){}")
    pg.goto(f"{base}/{name}.html", wait_until="networkidle")
    pg.add_style_tag(content=FREEZE_CSS)
    pg.wait_for_timeout(500)
    h = min(pg.evaluate("document.documentElement.scrollHeight"), MAX_HEIGHT)
    pg.set_viewport_size({"width": width, "height": h})
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(path))
    pg.close()


def compare(a_path, b_path, out_path):
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    w, h = max(a.width, b.width), max(a.height, b.height)
    pad = lambda im: im if im.size == (w, h) else _pad(im, w, h)  # noqa: E731
    a2, b2 = pad(a), pad(b)
    diff = ImageChops.difference(a2, b2).convert("L").point(lambda v: 255 if v > 24 else 0)
    ratio = sum(diff.histogram()[255:]) / (w * h)
    if ratio > THRESHOLD:
        red = Image.new("RGB", (w, h), (255, 40, 40))
        marked = Image.composite(red, b2.point(lambda v: v // 3), diff)
        sheet = Image.new("RGB", (w * 3 + 40, h), (40, 40, 40))
        for i, im in enumerate((a2, b2, marked)):
            sheet.paste(im, (i * (w + 20), 0))
        sheet.thumbnail((2400, 6000))
        sheet.save(out_path, optimize=True)
    return ratio, a.size != b.size


def _pad(im, w, h):
    out = Image.new("RGB", (w, h), (255, 0, 255))
    out.paste(im, (0, 0))
    return out


def main():
    before, after, out = map(pathlib.Path, sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    shots = pathlib.Path(tempfile.mkdtemp())  # 撮影したままの画像(添付しない)
    s1, u1 = serve(before)
    s2, u2 = serve(after)
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        for name in PAGES:
            if not (after / f"{name}.html").exists():
                continue
            for w in WIDTHS:
                key = f"{name.replace('/', '_')}_{w}"
                if not (before / f"{name}.html").exists():
                    rows.append((name, w, None, "新しいページ"))
                    continue
                pa, pb = shots / f"{key}_before.png", shots / f"{key}_after.png"
                shoot(b, u1, name, w, pa)
                shoot(b, u2, name, w, pb)
                ratio, resized = compare(pa, pb, out / f"{key}.png")
                if ratio > THRESHOLD:
                    rows.append((name, w, ratio, "高さが変化" if resized else ""))
        b.close()
    s1.shutdown()
    s2.shutdown()

    lines = ["### 見た目の差分", ""]
    if rows:
        lines += ["| ページ | 幅 | 変わった画素 | 備考 |", "|---|---|---|---|"]
        for name, w, ratio, note in rows:
            r = "-" if ratio is None else f"{ratio:.1%}"
            lines.append(f"| {name} | {w}px | {r} | {note} |")
        lines += [
            "",
            "画像(変更前 | 変更後 | 差分を赤で表示)は、この実行の Artifacts「visual-diff」にあります。",
        ]
    else:
        lines.append("見た目の変化はありませんでした(WebGL の地図・3D は比較対象外)。")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    for name, w, ratio, _ in rows:
        print(f"::notice title=見た目の変化::{name} ({w}px)" + ("" if ratio is None else f" {ratio:.1%}"))


if __name__ == "__main__":
    main()
