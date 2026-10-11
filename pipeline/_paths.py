"""パイプライン共通のパス。
  ROOT: リポジトリのルート
  RAW : e-Statから取得した原本(xlsx等)。git管理外。既定は ROOT/raw、環境変数 KEIZAI_RAW で変更可
  OUT : 加工済みCSV/JSONの出力先。既定は ROOT/data、環境変数 KEIZAI_OUT で変更可(再現性の確認用)
"""
import os,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
RAW=pathlib.Path(os.environ.get("KEIZAI_RAW",ROOT/"raw"))
OUT=pathlib.Path(os.environ.get("KEIZAI_OUT",ROOT/"data")); OUT.mkdir(parents=True,exist_ok=True)
