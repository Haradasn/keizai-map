/* トップページ。(1) 県を選ぶと、その県が何で稼いでいるかを県別データ(pref-map-data.js の PREF_MAP)から文章にし、
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
  var D = window.PREF_MAP,
    root = document.getElementById("pm-map"),
    sel = /** @type {HTMLSelectElement | null} */ (document.getElementById("hp-pref")),
    out = document.getElementById("hp-out");
  if (D && root && sel && out) {
    var P = D.prefs,
      INDS = D.inds,
      MIN = 0.005; // 県の産出額に占める割合がこれ未満の産業は、集中度の比較から除く(県別ページと同じ)
    /** @param {string} id */
    var tops = function (id) {
      var p = P[id];
      return Object.keys(p.s)
        .filter(function (k) {
          return p.s[k][1] != null && p.s[k][0] / p.t >= MIN && INDS[k];
        })
        .sort(function (a, b) {
          return p.s[b][1] - p.s[a][1];
        })
        .slice(0, 4);
    };
    /** 割合を%の数字に。0.1%未満は小数2桁 @param {number} v */
    var pc = function (v) {
      return (v * 100).toFixed(v < 0.001 ? 2 : 1);
    };
    var cur = { id: "", k: "" };
    /** @param {string} id @param {string} [k] @param {boolean} [user] */
    var show = function (id, k, user) {
      var p = P[id];
      if (!p) return;
      var T = tops(id);
      if (!T.length) return;
      if (!k || T.indexOf(k) < 0) k = T[0];
      cur = { id: id, k: k };
      var s = p.s[k],
        share = s[0] / p.t,
        mx = p.s[T[0]][1];
      out.innerHTML =
        '<p class="hp-fact"><span class="hp-pn">' +
        esc(p.n) +
        "</span>は、" +
        esc(INDS[k]) +
        'が<br>全国平均の<b class="hp-x">' +
        s[1].toFixed(1) +
        "</b>倍。</p>" +
        '<p class="hp-sub">県の産出額の' +
        pc(share) +
        "%を占めます（全国では" +
        pc(share / s[1]) +
        "%）。</p>" +
        '<ul class="hp-tops" aria-label="' +
        esc(p.n) +
        'で全国より集中している産業">' +
        T.map(function (t) {
          var lq = p.s[t][1];
          return (
            '<li><button type="button" data-k="' +
            t +
            '" aria-pressed="' +
            (t === k) +
            '"><span class="hp-tn">' +
            esc(INDS[t]) +
            '</span><span class="hp-tb"><i style="width:' +
            ((lq / mx) * 100).toFixed(1) +
            '%"></i></span><span class="hp-tv">' +
            lq.toFixed(1) +
            "倍</span></button></li>"
          );
        }).join("") +
        "</ul>" +
        '<p class="hp-go"><a href="prefecture/' +
        p.g +
        '.html">' +
        esc(p.n) +
        'の産業構造を読む</a><a href="industry/' +
        k +
        '.html">' +
        esc(INDS[k]) +
        "とは</a></p>";
      var lg = document.getElementById("hp-legend-k");
      if (lg) lg.textContent = INDS[k];
      sel.value = id;
      root.dispatchEvent(new CustomEvent("pm:set", { detail: { k: k, id: id, user: !!user } }));
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
      show(sel.value, "", true);
    });
    out.addEventListener("click", function (ev) {
      var b = /** @type {HTMLElement} */ (ev.target).closest("button[data-k]");
      if (b) show(cur.id, b.getAttribute("data-k") || "", true);
    });
    root.addEventListener("pm:pick", function (ev) {
      show(/** @type {CustomEvent} */ (ev).detail.id, "", true);
    });
    // 最初に見せる県: 前に選んだ県。なければ、集中度がいちばん高い県と産業
    var first = "";
    try {
      first = localStorage.getItem("hp-pref") || "";
    } catch (e) {}
    var firstK = "";
    if (!P[first]) {
      // 集中度×県内の割合がいちばん大きい組み合わせ(大きな産業が、その県に強く集まっている例)
      var best = 0;
      Object.keys(P).forEach(function (id) {
        tops(id).forEach(function (t) {
          var s = P[id].s[t],
            w = (s[1] * s[0]) / P[id].t;
          if (w > best) {
            best = w;
            first = id;
            firstK = t;
          }
        });
      });
    }
    if (!P[first]) first = Object.keys(P)[0];
    show(first, firstK);
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
