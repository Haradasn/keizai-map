"""テスト共通: 本番と同じヘッダー(CSP など)で site/ を配信するローカルサーバー、ブラウザ、ページを開く補助。
実行: pip install pytest playwright && playwright install chromium && pytest tests/
(事前に npm run build でサイトをビルドしておく)"""

import re, pathlib, threading, http.server, functools
import pytest
from playwright.sync_api import sync_playwright

R = pathlib.Path(__file__).resolve().parent.parent
S = R / "site"
PAGES = ["index", "explorer", "similarity", "latest", "international", "about", "guide", "glossary"]


def site_headers():
    """site/_headers(Cloudflare の形式)を読み、[(パスの正規表現, [(名前, 値)])] にする"""
    rules = []
    for line in (S / "_headers").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            pat = "^" + re.escape(line.strip()).replace(r"\*", ".*") + "$"
            rules.append((re.compile(pat), []))
        else:
            k, v = line.strip().split(":", 1)
            rules[-1][1].append((k.strip(), v.strip()))
    return rules


class Handler(http.server.SimpleHTTPRequestHandler):
    """本番と同じヘッダー(CSP など)を付けて返すローカルサーバー"""

    rules = []

    def end_headers(self):
        path = self.path.split("?")[0]
        for pat, hs in self.rules:
            if pat.match(path):
                for k, v in hs:
                    self.send_header(k, v)
        super().end_headers()

    def log_message(self, *a, **k):
        pass


@pytest.fixture(scope="session")
def base():
    Handler.rules = site_headers()
    h = functools.partial(Handler, directory=str(S))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        yield b
        b.close()


def open_page(browser, base, name):
    pg = browser.new_page(viewport={"width": 1300, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # CSP に止められた読み込み・実行もエラーとして数える
    pg.on(
        "console",
        lambda m: errs.append(m.text) if "Content Security Policy" in m.text else None,
    )
    pg.goto(f"{base}/{name}.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(1200)
    return pg, errs
