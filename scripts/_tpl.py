"""Jinja2 テンプレート(templates/*.j2)の読み込みと描画。

テンプレートは読みやすいようにインデント・改行して書き、読み込み時に次の規則で詰める
(出力するHTMLは、これまでの f-string と1バイトも変えないため)。
  - 各行の前後の空白は捨てて、改行も出力しない(行の継ぎ目に空白は入らない)
  - 行末に `⏎` を付けた行だけ、その位置に改行を1つ出力する
  - 行頭に `|` を付けた行は、`|` を取ったあとの空白をそのまま残す(先頭の空白を出したいとき)
エスケープは自動では行わない。信頼できない文字列には `|esc`(html.escape)を明示する。
"""

import html
import pathlib
from xml.sax.saxutils import escape as xml_escape

import jinja2

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"
NEWLINE_MARK = "⏎"
KEEP_MARK = "|"


def compact(source):
    """テンプレート本文を詰める。行数は変えない(エラー表示の行番号を保つため、改行は空のコメントに入れる)。"""
    lines = source.split("\n")
    out = []
    for i, line in enumerate(lines):
        text = line.strip()
        if text.startswith(KEEP_MARK):
            text = line.lstrip()[1:]
        if i == len(lines) - 1:
            out.append(text)
        elif text.endswith(NEWLINE_MARK):
            out.append(text[: -len(NEWLINE_MARK)] + "\n")
        else:
            out.append(text + "{#\n#}")
    return "".join(out)


class CompactLoader(jinja2.FileSystemLoader):
    """読み込み時に compact() を通すローダ。"""

    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        return compact(source), filename, uptodate


ENV = jinja2.Environment(
    loader=CompactLoader(str(TEMPLATE_DIR)),
    autoescape=False,
    undefined=jinja2.StrictUndefined,
    keep_trailing_newline=True,
)
ENV.filters["esc"] = html.escape
ENV.filters["xml_escape"] = xml_escape


def render(template, **context):
    """templates/<template> を context で描画して文字列を返す。"""
    return ENV.get_template(template).render(**context)
