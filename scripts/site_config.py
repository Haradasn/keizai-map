import os
# 独自ドメイン取得後は、環境変数 SITE_URL か下の値だけを書き換える（末尾スラッシュなし）
SITE_URL=os.environ.get("SITE_URL","https://keizai-atlas.com")
SITE_NAME="Keizai Atlas"
