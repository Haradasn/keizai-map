/* トップのインサイト・カルーセル。数値は pref-map-data.js(県別)と、ページに差し込まれた data 属性・文字から計算する。 */
(function () {
  var root = document.getElementById("ins");
  if (!root) return;
  var slides = [].slice.call(root.querySelectorAll(".ins-slide")),
    layers = [].slice.call(root.querySelectorAll(".ins-v")),
    dots = [].slice.call(root.querySelectorAll(".ins-dot")),
    n = slides.length,
    cur = 0,
    timer = null,
    userPause = false,
    hold = false,
    MS = 7000,
    reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches,
    live = document.getElementById("ins-live"),
    count = document.getElementById("ins-count"),
    pauseBtn = document.getElementById("ins-pause");
  function num(s) {
    return parseFloat(String(s).replace(/[−–]/g, "-").replace(/,/g, ""));
  }
  // 1) 地域: 輸送機械(35)の特化係数が最大の県(その産業が県の総産出額の0.5%以上のもの)
  function region() {
    var D = window.PREF_MAP;
    if (!D) return;
    /** @type {{n: string, lq: number, sh: number} | null} */
    var best = null;
    Object.keys(D.prefs).forEach(function (id) {
      var p = D.prefs[id],
        s = p.s["35"];
      if (s && s[1] != null && p.t > 0 && s[0] / p.t >= 0.005 && (!best || s[1] > best.lq))
        best = { n: p.n, lq: s[1], sh: s[0] / p.t };
    });
    if (!best) return;
    var el = slides[0];
    el.querySelector(".ins-lead").textContent = best.n + "の" + D.inds["35"] + "は、全国平均の";
    el.querySelector("[data-f=big]").innerHTML = best.lq.toFixed(1) + "<small>倍</small>";
    el.querySelector("[data-f=tail]").textContent = "集中している（特化係数）";
    var m = el.querySelector(".ins-mean");
    if (m && best.sh != null)
      m.textContent =
        "つまり、" +
        best.n +
        "の産出額のうち" +
        D.inds["35"] +
        "が占める割合は" +
        (best.sh * 100).toFixed(1) +
        "%で、全国の" +
        ((best.sh / best.lq) * 100).toFixed(1) +
        "%を大きく上回っています。";
  }
  // 5) つながり: 取引額の上位20本(同じ産業の中の取引を除く)のうち、出どころとして最も多い産業
  var NET = null,
    netOn = false,
    HUB = null;
  function connect() {
    var M = window.NET_MINI;
    if (!M) return;
    var top = M.edges.slice(0, 20),
      c = {};
    top.forEach(function (e) {
      c[e.s] = (c[e.s] || 0) + 1;
    });
    var hub = Object.keys(c).sort(function (a, b) {
      return c[b] - c[a];
    })[0];
    HUB = hub;
    var nm = M.nodes.filter(function (n) {
        return n.id === hub;
      })[0].name,
      el = slides[4];
    if (!el) return;
    el.querySelector("[data-f=lead5]").textContent =
      "金額の大きい産業間の取引、上位" + top.length + "本のうち";
    el.querySelector("[data-f=big5]").innerHTML = c[hub] + "<small>本</small>";
    el.querySelector("[data-f=tail5]").textContent = "が「" + nm + "」から出ている";
    el.querySelector("[data-f=more5]").setAttribute("href", "explorer.html?sel=" + hub);
  }
  function net(on) {
    // ネットワークは、このスライドに来たときに初めて読み込む。離れたら描画を止める
    netOn = on;
    var box = document.getElementById("ins-net");
    if (!box || !window.NET_MINI) return;
    if (NET) {
      if (on) NET.resumeAnimation();
      else NET.pauseAnimation();
      return;
    }
    if (!on) return;
    try {
      var cv = document.createElement("canvas");
      if (!(cv.getContext("webgl2") || cv.getContext("webgl"))) return;
    } catch (e) {
      return;
    }
    var go = function () {
      if (NET || !window.ForceGraph3D) return;
      var M = window.NET_MINI,
        G = M.gc,
        dark = document.documentElement.dataset.theme !== "nord";
      var links = M.edges.slice(0, 40).map(function (e) {
        return { source: e.s, target: e.t, v: e.v, hub: e.s === HUB };
      });
      var mx = Math.max.apply(
        null,
        M.nodes.map(function (n) {
          return n.out;
        })
      );
      NET = ForceGraph3D({ controlType: "orbit" })(box)
        .width(box.clientWidth)
        .height(box.clientHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showNavInfo(false)
        .enableNodeDrag(false)
        .graphData({
          nodes: M.nodes.map(function (n) {
            return Object.assign({}, n, { fx: n.x, fy: n.y, fz: n.z * 0.6 });
          }),
          links: links,
        })
        .nodeVal(function (n) {
          return 2 + (30 * n.out) / mx;
        })
        .nodeRelSize(3)
        .nodeOpacity(0.95)
        .nodeColor(function (n) {
          return n.id === HUB ? "#f8fafc" : G[n.grp];
        })
        .nodeLabel(function (n) {
          return n.name;
        })
        .linkColor(function (l) {
          return l.hub ? "#38bdf8" : dark ? "rgba(148,163,184,0.25)" : "rgba(71,85,105,0.25)";
        })
        .linkWidth(function (l) {
          return l.hub ? 1.6 : 0.4;
        })
        .linkOpacity(0.6)
        .linkDirectionalParticles(function (l) {
          return l.hub && !reduce ? 3 : 0;
        })
        .linkDirectionalParticleWidth(2)
        .linkDirectionalParticleColor(function () {
          return "#7dd3fc";
        })
        .onNodeClick(function (n) {
          location.href = "explorer.html?sel=" + n.id;
        });
      setTimeout(function () {
        NET.zoomToFit(0, 0);
        var p = NET.cameraPosition();
        NET.cameraPosition({ x: p.x * 0.7, y: p.y * 0.7, z: p.z * 0.7 });
        var c = NET.controls();
        c.enabled = false;
        box.querySelectorAll("canvas").forEach(function (x) {
          x.style.touchAction = "pan-y";
        }); // トップでは回転・拡大の操作は受け付けず、ページのスクロールを邪魔しない
        if (!reduce) {
          c.autoRotate = true;
          c.autoRotateSpeed = 0.8;
        }
      }, 300);
      window.addEventListener("resize", function () {
        if (NET) NET.width(box.clientWidth).height(box.clientHeight);
      });
      if (!netOn) NET.pauseAnimation();
    };
    if (window.ForceGraph3D) go();
    else {
      var sc = document.createElement("script");
      sc.src = "vendor/3d-force-graph.min.js";
      sc.onload = go;
      document.head.appendChild(sc);
    }
  }
  // 2) 棒グラフ: 棒の長さは数値に比例
  function bars() {
    [].forEach.call(root.querySelectorAll("svg[data-vals],svg[data-q]"), function (svg) {
      var vals = svg.dataset.vals
          ? svg.dataset.vals.split(",").map(num)
          : [100 + num(svg.dataset.q), num(svg.dataset.p) * 100],
        ref = svg.dataset.ref ? num(svg.dataset.ref) : 0,
        mx = Math.max.apply(null, vals.concat([ref])),
        rects = svg.querySelectorAll("rect.b"),
        lbl = svg.querySelectorAll(".bl");
      if (svg.dataset.dir === "h") {
        var W = 230;
        vals.forEach(function (v, i) {
          var w = (W * v) / mx;
          rects[i].setAttribute("width", w.toFixed(1));
          lbl[i].setAttribute("x", (90 + w + 10).toFixed(1));
        });
        return;
      }
      var base = num(svg.dataset.base),
        H = num(svg.dataset.maxh);
      vals.forEach(function (v, i) {
        var h = (H * v) / mx;
        rects[i].setAttribute("y", (base - h).toFixed(1));
        rects[i].setAttribute("height", h.toFixed(1));
        lbl[i].setAttribute("y", (base - h - 10).toFixed(1));
      });
      var rf = svg.querySelector(".rf");
      if (rf) {
        var y = base - (H * ref) / mx;
        rf.setAttribute("y1", y);
        rf.setAttribute("y2", y);
        svg.querySelector(".rt").setAttribute("y", y - 8);
      }
    });
  }
  function show(k, manual) {
    cur = (k + n) % n;
    slides.forEach(function (s, i) {
      s.classList.toggle("is-on", i === cur);
      s.setAttribute("aria-hidden", i === cur ? "false" : "true");
    });
    layers.forEach(function (l, i) {
      l.classList.toggle("is-on", i === cur);
    });
    net(cur === 4);
    dots.forEach(function (d, i) {
      d.setAttribute("aria-current", i === cur ? "true" : "false");
    });
    if (count) count.textContent = cur + 1 + " / " + n;
    if (manual && live) live.textContent = slides[cur].querySelector("h2").textContent;
    schedule();
  }
  function schedule() {
    clearTimeout(timer);
    root.classList.remove("ins-run");
    if (reduce || userPause || hold || document.hidden) return;
    void root.offsetWidth;
    root.classList.add("ins-run");
    timer = setTimeout(function () {
      show(cur + 1, true);
    }, MS);
  }
  root.classList.add("ins-js");
  region();
  connect();
  bars();
  show(0, false);
  document.getElementById("ins-prev").addEventListener("click", function () {
    show(cur - 1, true);
  });
  document.getElementById("ins-next").addEventListener("click", function () {
    show(cur + 1, true);
  });
  dots.forEach(function (d, i) {
    d.addEventListener("click", function () {
      show(i, true);
    });
  });
  if (pauseBtn) {
    if (reduce) pauseBtn.style.display = "none";
    pauseBtn.addEventListener("click", function () {
      userPause = !userPause;
      pauseBtn.setAttribute("aria-pressed", userPause ? "true" : "false");
      pauseBtn.setAttribute("aria-label", userPause ? "自動切り替えを再開する" : "自動切り替えを止める");
      pauseBtn
        .querySelector(".pp")
        .setAttribute("d", userPause ? "M8 5v14l11-7z" : "M7 5h3.5v14H7zM13.5 5H17v14h-3.5z");
      schedule();
    });
  }
  root.addEventListener("pointerenter", function (e) {
    if (e.pointerType === "mouse") {
      hold = true;
      schedule();
    }
  });
  root.addEventListener("pointerleave", function (e) {
    if (e.pointerType === "mouse") {
      hold = false;
      schedule();
    }
  });
  root.addEventListener("focusin", function (e) {
    if (e.target instanceof Element && e.target.matches(":focus-visible")) {
      hold = true;
      schedule();
    }
  });
  root.addEventListener("focusout", function () {
    hold = false;
    schedule();
  });
  document.addEventListener("visibilitychange", schedule);
  root.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") {
      show(cur - 1, true);
    } else if (e.key === "ArrowRight") {
      show(cur + 1, true);
    }
  });
  var sx = null,
    sy = 0,
    st = document.getElementById("ins-stack");
  st.addEventListener(
    "touchstart",
    function (e) {
      sx = e.touches[0].clientX;
      sy = e.touches[0].clientY;
    },
    { passive: true }
  );
  st.addEventListener(
    "touchend",
    function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx,
        dy = e.changedTouches[0].clientY - sy;
      sx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(cur + (dx < 0 ? 1 : -1), true);
    },
    { passive: true }
  );
})();
