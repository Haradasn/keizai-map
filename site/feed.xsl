<?xml version="1.0" encoding="utf-8"?>
<!-- feed.xml をブラウザで開いたときに、読める形で表示するためのスタイル(RSSリーダーには影響しない) -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:a="http://www.w3.org/2005/Atom">
  <xsl:output method="html" encoding="utf-8"/>
  <xsl:template match="/">
    <html lang="ja">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title><xsl:value-of select="a:feed/a:title"/></title>
        <style>
          body{margin:0;background:#0b1120;color:#e2e8f0;font:16px/1.7 system-ui,sans-serif}
          main{max-width:720px;margin:0 auto;padding:32px 16px}
          .note{background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px 16px;font-size:14px;color:#94a3b8}
          a{color:#38bdf8}
          article{border-bottom:1px solid #1e293b;padding:16px 0}
          time{font-size:13px;color:#94a3b8}
          h2{font-size:17px;margin:4px 0}
          p{margin:4px 0;font-size:15px;color:#cbd5e1}
        </style>
      </head>
      <body>
        <main>
          <h1><xsl:value-of select="a:feed/a:title"/></h1>
          <p class="note">これは更新情報のフィード（RSSリーダー用）です。このURLをRSSリーダーに登録すると、更新を受け取れます。ふつうに読む場合は <a href="/changelog">更新情報のページ</a> をご覧ください。</p>
          <xsl:for-each select="a:feed/a:entry">
            <article>
              <time><xsl:value-of select="substring(a:updated,1,10)"/></time>
              <h2><a href="{a:link/@href}"><xsl:value-of select="a:title"/></a></h2>
              <p><xsl:value-of select="a:summary"/></p>
            </article>
          </xsl:for-each>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
