FONTS='<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+JP:wght@400;500;700;800&display=swap" rel="stylesheet">'
HEAD='''<!doctype html><html lang="ja" data-theme="night"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">{seo}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+JP:wght@400;500;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="assets.css">
<script>try{{var t=localStorage.getItem("theme");if(t!=="nord")t="night";document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head><body class="bg-base-200 text-base-content font-sans min-h-screen flex flex-col">
<header class="navbar bg-base-100/80 backdrop-blur border-b border-base-300 sticky top-0 z-50 px-4">
 <div class="flex-1"><a href="index.html" class="text-lg font-bold tracking-tight">Keizai Atlas <span class="text-xs font-normal text-base-content/60 ml-2 hidden sm:inline">経済の地図帳</span></a></div>
 <nav class="flex-none gap-1"><a class="btn btn-ghost btn-sm" href="explorer.html">産業マップ</a><a class="btn btn-ghost btn-sm" href="similarity.html">近さの地図</a><a class="btn btn-ghost btn-sm" href="latest.html">最新動向</a><a class="btn btn-ghost btn-sm" href="international.html">国際比較</a><a class="btn btn-ghost btn-sm" href="about.html">方法と出典</a>
 <label class="swap swap-rotate btn btn-ghost btn-sm btn-circle" aria-label="テーマ切替"><input type="checkbox" id="thm"><span class="swap-on">☀</span><span class="swap-off">☾</span></label></nav>
</header>'''
FOOT='''<footer class="footer footer-center p-6 bg-base-100 border-t border-base-300 text-sm text-base-content/70 mt-12">
<p>出典：総務省ほか「産業連関表」、経済産業省「延長産業連関表」（政府統計の総合窓口 e-Stat 掲載）を筆者が加工して作成。<br>加工・分析・「仮説」は筆者によるもので、政府が作成・保証したものではありません。投資・経営判断の根拠にはしないでください。</p>
<p><a class="link" href="about.html">方法と出典・免責</a></p></footer>
<script>document.getElementById("thm").checked=document.documentElement.dataset.theme==="nord";
document.getElementById("thm").onchange=function(e){var t=e.target.checked?"nord":"night";document.documentElement.dataset.theme=t;try{localStorage.setItem("theme",t)}catch(x){}}</script>
</body></html>'''

def seo(path,title,desc,site,name,jsonld=""):
    url=site+("/" if path in("","index") else "/"+path)
    return (f'<link rel="canonical" href="{url}"><meta property="og:type" content="website"><meta property="og:site_name" content="{name}">'
      f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{url}">'
      f'<meta property="og:image" content="{site}/og.png"><meta property="og:locale" content="ja_JP"><meta name="twitter:card" content="summary_large_image">'
      f'<meta name="theme-color" content="#0b1120">'+jsonld)
