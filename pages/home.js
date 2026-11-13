/* トップページ。(1) 県を選ぶと、その県が県外・海外に何を売って稼いでいるかを県別データ(pref-map-data.js の PREF_MAP)から文章にし、
   立体地図(prefmap.js)に "pm:set" で伝える。地図で県をクリックすると "pm:pick" が届く。
   (2) 産業どうしの取引の図(net-mini.js の NET_MINI)。線の太さ=取引額、点は売り手の産業から買い手の産業へ動く。
       画面で動くのは、実際の取引を表すものだけにする。 */
(function () {
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ---------- (1) 県を選ぶ
  // 答えは「県外・海外への販売額(移輸出額)が大きい産業」。県ごとの上位は、ビルド時に計算したもの(PREF_MAP.prefs[id].x)を
  // そのまま使う: [名前, 全国の部門コード(無ければ null), 県の移輸出額に占める割合, 特化係数(無ければ null), 補足(無ければ null)]。
  // 県ページ・稼ぎ頭マップ・共有画像と同じ関数(scripts/build/build_pref.py の kasegi_ranking)から作っているので、数字が食い違わない。
  var D = window.PREF_MAP,
    root = document.getElementById("pm-map"),
    sel = /** @type {HTMLSelectElement | null} */ (document.getElementById("hp-pref")),
    out = document.getElementById("hp-out");
  if (D && root && sel && out) {
    var P = D.prefs;
    /** 割合を%の数字に(整数) @param {number} v */
    var pc = function (v) {
      return (v * 100).toFixed(0);
    };
    var cur = { id: "", i: 0 };
    /** @param {string} id 県のJISコード @param {number} [i] 上位の何番目を選ぶか(0が稼ぎ頭) @param {boolean} [user] 人の操作か */
    var show = function (id, i, user) {
      var p = P[id];
      if (!p || !p.x || !p.x.length) return;
      var T = p.x;
      i = Math.max(0, Math.min(T.length - 1, i || 0));
      cur = { id: id, i: i };
      var r = T[i],
        code = r[1],
        sub = [];
      if (r[3] != null) sub.push("全国平均と比べた集中度は" + r[3].toFixed(1) + "倍です。");
      if (r[4]) sub.push(r[4]);
      if (!code) sub.push("全国の分布を出せない部門のため、地図はすべての産業の合計です。");
      out.innerHTML =
        '<p class="hp-fact"><span class="hp-pn">' +
        esc(p.n) +
        '</span>が県外・海外に売る額の<br><b class="hp-x">' +
        pc(r[2]) +
        "</b>%は、" +
        esc(r[0]) +
        "。</p>" +
        (sub.length ? '<p class="hp-sub">' + esc(sub.join("")) + "</p>" : "") +
        '<ul class="hp-tops" aria-label="' +
        esc(p.n) +
        'が県外・海外に多く売っている産業">' +
        T.map(function (t, n) {
          return (
            '<li><button type="button" data-i="' +
            n +
            '" aria-pressed="' +
            (n === i) +
            '"><span class="hp-tn">' +
            esc(t[0]) +
            '</span><span class="hp-tb"><i style="width:' +
            ((t[2] / T[0][2]) * 100).toFixed(1) +
            '%"></i></span><span class="hp-tv">' +
            pc(t[2]) +
            "%</span></button></li>"
          );
        }).join("") +
        "</ul>" +
        '<p class="hp-go"><a href="prefecture/' +
        p.g +
        '.html">' +
        esc(p.n) +
        "の産業構造を読む</a>" +
        (code ? '<a href="industry/' + code + '.html">' + esc(r[0]) + "とは</a>" : "") +
        '<a href="kasegi-map.html">全国の稼ぎ頭マップ</a><a target="_blank" rel="noopener" href="https://twitter.com/intent/tweet?text=' +
        encodeURIComponent(
          p.n +
            "の稼ぎ頭は、" +
            T[0][0] +
            "。県外・海外に売る額の" +
            pc(T[0][2]) +
            "%を占めます。あなたの県は、何で稼いでいる？ #KeizaiAtlas"
        ) +
        "&url=" +
        encodeURIComponent("https://keizai-atlas.com/prefecture/" + p.g) +
        '">Xで共有</a></p>';
      // 凡例: 全国の部門に対応する産業なら、その産業の分布(高さ=産出額、色=集中度)。対応しない部門なら、すべての産業の合計
      var lg = document.getElementById("hp-legend"),
        lh = document.getElementById("hp-legend-h"),
        lc = document.getElementById("hp-legend-c");
      if (lg) lg.classList.toggle("is-all", !code);
      if (lh) lh.textContent = code ? r[0] + "の産出額" : "すべての産業の産出額";
      if (lc) lc.textContent = code ? "全国平均と比べた集中度" : "付加価値率（茶に近いほど高い）";
      sel.value = id;
      root.dispatchEvent(new CustomEvent("pm:set", { detail: { k: code || "all", id: id, user: !!user } }));
      if (user)
        try {
          localStorage.setItem("hp-pref", id);
        } catch (e) {}
    };
    Object.keys(P)
      .sort(function (a, b) {
        return Number(a) - Number(b);
      })
      .forEach(function (id) {
        var o = document.createElement("option");
        o.value = id;
        o.textContent = P[id].n;
        sel.appendChild(o);
      });
    var cnt = document.getElementById("hp-count");
    if (cnt) cnt.textContent = String(Object.keys(P).length);
    sel.addEventListener("change", function () {
      show(sel.value, 0, true);
    });
    out.addEventListener("click", function (ev) {
      var b = /** @type {HTMLElement} */ (ev.target).closest("button[data-i]");
      if (b) show(cur.id, Number(b.getAttribute("data-i")), true);
    });
    root.addEventListener("pm:pick", function (ev) {
      show(/** @type {CustomEvent} */ (ev).detail.id, 0, true);
    });
    // 最初に見せる県: リンクの ?pref=aichi で指定された県。次に、前に選んだ県。どちらもなければ、稼ぎ頭の割合がいちばん高い県
    var first = "",
      want = new URLSearchParams(location.search).get("pref");
    if (want)
      Object.keys(P).forEach(function (id) {
        if (P[id].g === want) first = id;
      });
    if (!first)
      try {
        first = localStorage.getItem("hp-pref") || "";
      } catch (e) {}
    if (!P[first]) {
      var best = 0;
      Object.keys(P).forEach(function (id) {
        var x = P[id].x;
        if (x && x.length && x[0][2] > best) {
          best = x[0][2];
          first = id;
        }
      });
    }
    show(first, 0);
  }

  // ---------- (2) 取引の図
  var M = window.NET_MINI,
    cv = /** @type {HTMLCanvasElement | null} */ (document.getElementById("fl-cv")),
    say = document.getElementById("fl-say");
  if (M && cv && cv.getContext) {
    var top20 = M.edges.slice(0, 20),
      c = /** @type {Record<string, number>} */ ({});
    top20.forEach(function (e) {
      c[e.s] = (c[e.s] || 0) + 1;
    });
    var hub = Object.keys(c).sort(function (a, b) {
        return c[b] - c[a];
      })[0],
      byId = /** @type {Record<string, any>} */ ({});
    M.nodes.forEach(function (n) {
      byId[n.id] = n;
    });
    if (say)
      say.innerHTML =
        "金額の大きい取引、上位" +
        top20.length +
        '本のうち<b class="hp-x">' +
        c[hub] +
        "</b>本は、「" +
        esc(byId[hub].name) +
        "」から出ています。";
    var more = /** @type {HTMLAnchorElement | null} */ (document.getElementById("fl-more"));
    if (more) more.href = "explorer.html?sel=" + hub;
    var E = M.edges.slice(0, 40),
      x = cv.getContext("2d"),
      W = 0,
      H = 0,
      t = 0,
      raf = 0,
      seen = false,
      x0 = 1e9,
      x1 = -1e9,
      y0 = 1e9,
      y1 = -1e9,
      omx = 0,
      vmx = E[0].v;
    M.nodes.forEach(function (n) {
      x0 = Math.min(x0, n.x);
      x1 = Math.max(x1, n.x);
      y0 = Math.min(y0, n.y);
      y1 = Math.max(y1, n.y);
      omx = Math.max(omx, n.out);
    });
    /** @param {any} n */
    var px = function (n) {
      var pad = Math.min(W, H) * 0.09;
      return [
        pad + ((n.x - x0) / (x1 - x0)) * (W - pad * 2),
        pad + (1 - (n.y - y0) / (y1 - y0)) * (H - pad * 2),
      ];
    };
    /** @param {number[]} a @param {number[]} b @param {number} u 弓なりの線の上の点(u=0..1) */
    var at = function (a, b, u) {
      var mx = (a[0] + b[0]) / 2 - (b[1] - a[1]) * 0.18,
        my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * 0.18,
        v = 1 - u;
      return [
        v * v * a[0] + 2 * v * u * mx + u * u * b[0],
        v * v * a[1] + 2 * v * u * my + u * u * b[1],
        mx,
        my,
      ];
    };
    var size = function () {
      var r = cv.getBoundingClientRect(),
        d = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width;
      H = r.height;
      cv.width = W * d;
      cv.height = H * d;
      x.setTransform(d, 0, 0, d, 0, 0);
    };
    var draw = function () {
      var st = getComputedStyle(cv),
        ink = st.getPropertyValue("--fl-ink").trim() || "#14232e",
        hot = st.getPropertyValue("--fl-hot").trim() || "#c8361f",
        sea = st.getPropertyValue("--fl-bg").trim() || "#dcebf1";
      x.clearRect(0, 0, W, H);
      E.forEach(function (e) {
        var a = px(byId[e.s]),
          b = px(byId[e.t]),
          m = at(a, b, 0.5),
          isHub = e.s === hub;
        x.beginPath();
        x.moveTo(a[0], a[1]);
        x.quadraticCurveTo(m[2], m[3], b[0], b[1]);
        x.lineWidth = 0.6 + (e.v / vmx) * 7;
        x.strokeStyle = isHub ? hot : ink;
        x.globalAlpha = isHub ? 0.85 : 0.22;
        x.stroke();
      });
      // 動く点: 売り手から買い手へ。取引額が大きいほど点が多い
      x.globalAlpha = 1;
      E.forEach(function (e, i) {
        var a = px(byId[e.s]),
          b = px(byId[e.t]),
          n = 1 + Math.round((e.v / vmx) * 3);
        for (var j = 0; j < n; j++) {
          var u = (t * 0.12 + j / n + i * 0.137) % 1,
            q = at(a, b, u);
          x.beginPath();
          x.arc(q[0], q[1], e.s === hub ? 2.6 : 1.8, 0, 6.3);
          x.fillStyle = e.s === hub ? hot : ink;
          x.fill();
        }
      });
      M.nodes.forEach(function (n) {
        var p = px(n),
          r = 3 + Math.sqrt(n.out / omx) * Math.min(W, H) * 0.045;
        x.beginPath();
        x.arc(p[0], p[1], r, 0, 6.3);
        x.fillStyle = M.gc[n.grp];
        x.fill();
        x.lineWidth = n.id === hub ? 2.5 : 1;
        x.strokeStyle = n.id === hub ? hot : sea;
        x.stroke();
      });
      // 名前: 大きい産業から順に、ほかの名前と重ならないものだけ書く
      x.font = "500 12px " + st.fontFamily;
      x.fillStyle = ink;
      x.textAlign = "center";
      var used = /** @type {number[][]} */ ([]);
      M.nodes
        .slice()
        .sort(function (a, b) {
          return (b.id === hub ? 1e9 : b.out) - (a.id === hub ? 1e9 : a.out);
        })
        .forEach(function (n) {
          if (n.out / omx < 0.25 && n.id !== hub) return;
          var p = px(n),
            r = 3 + Math.sqrt(n.out / omx) * Math.min(W, H) * 0.045,
            w = x.measureText(n.name).width / 2 + 4,
            y = p[1] + r + 14;
          for (var i = 0; i < used.length; i++)
            if (Math.abs(used[i][0] - p[0]) < used[i][2] + w && Math.abs(used[i][1] - y) < 15) return;
          used.push([p[0], y, w]);
          x.fillText(n.name, p[0], y);
        });
    };
    var loop = function (/** @type {number} */ ts) {
      t = ts / 1000;
      draw();
      raf = requestAnimationFrame(loop);
    };
    var sync = function () {
      cancelAnimationFrame(raf);
      if (!reduce && seen && !document.hidden) raf = requestAnimationFrame(loop);
      else draw();
    };
    size();
    if ("IntersectionObserver" in window)
      new IntersectionObserver(function (en) {
        seen = en[0].isIntersecting;
        sync();
      }).observe(cv);
    else seen = true;
    document.addEventListener("visibilitychange", sync);
    window.addEventListener("resize", function () {
      size();
      sync();
    });
    if (window.MutationObserver)
      new MutationObserver(sync).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    sync();
  }
})();
