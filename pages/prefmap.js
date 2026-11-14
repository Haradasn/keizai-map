/* 県別の立体地図(MapLibre GL JS)。/prefecture-map とトップページで共通。データは pref-map-data.js の window.PREF_MAP。
   使い方: <div id="pm-map" data-prefmap="page|hero"> と <select id="pm-ind">。hero はトップ用(最初に柱が伸びる・操作は協調ジェスチャー)。
   動くのは柱の高さと色だけ(=データ)。産業や県を切り替えると、前の高さから次の高さへ伸び縮みする。カメラは勝手に動かさない。
   hero では、外から root に CustomEvent "pm:set"({k: 産業コード, id: 県のJISコード})を送ると表示を切り替え、県をクリックすると "pm:pick"({id})を出す(pages/home.js)。
   色は地図帳の標高の段彩(緑→黄→黄土→茶)。選んだ県だけ墨(暗いテーマでは白)。 */
(function () {
  var root = document.querySelector("[data-prefmap]");
  if (!root || !window.PREF_MAP) return;
  var HERO = root.getAttribute("data-prefmap") === "hero",
    DATA = window.PREF_MAP,
    INDS = DATA.inds,
    P = DATA.prefs;
  var sel = /** @type {HTMLSelectElement} */ (document.getElementById("pm-ind")) || {
      value: root.getAttribute("data-k") || "all",
      addEventListener: function () {},
    },
    box = root,
    list = document.getElementById("pm-list"),
    note = document.getElementById("pm-note"),
    cap = document.getElementById("pm-cap"),
    ins = document.getElementById("pm-insight");
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  function ok() {
    try {
      var c = document.createElement("canvas");
      return !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch (e) {
      return false;
    }
  }
  function lerp(a, b, t) {
    return Math.round(a + (b - a) * t);
  }
  function mix(a, b, t) {
    return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
  }
  function css(c) {
    return "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
  }
  var TH = null; // テーマ(背景色から計算。nord/night どちらでも使える)
  function theme() {
    if (TH) return TH;
    var m = rgb().match(/\d+/g).map(Number),
      dark = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2] < 128;
    TH = {
      bg: m,
      dark: dark,
      off: dark ? mix(m, [255, 255, 255], 0.07) : mix(m, [0, 0, 0], 0.07),
      pick: dark ? [245, 248, 249] : [20, 35, 46],
    };
    return TH;
  }
  // 段彩。トップの凡例(pages/index.html の .hp-ramp)と同じ色・同じ等間隔
  var STOPS = [
    [79, 154, 106],
    [207, 214, 107],
    [230, 176, 79],
    [181, 83, 47],
  ];
  function ramp(t) {
    t = Math.max(0, Math.min(1, t)) * (STOPS.length - 1);
    var i = Math.min(STOPS.length - 2, Math.floor(t));
    return mix(STOPS[i], STOPS[i + 1], t - i);
  }
  function col(lq) {
    return ramp((lq - 0.5) / 3.5);
  }
  function values(k) {
    var out = {};
    Object.keys(P).forEach(function (id) {
      var p = P[id],
        v = null,
        lq = null;
      if (k === "all") {
        v = p.t;
      } else {
        var s = p.s[k];
        if (s) {
          v = s[0];
          lq = s[1];
        }
      }
      out[id] = { name: p.n, slug: p.g, v: v, lq: lq, va: p.va };
    });
    return out;
  }
  /** 柱の高さ(メートル)。産出額の平方根に比例(いちばん大きい県が 262km) @param {number} v 産出額 @param {number} mx その産業でいちばん大きい県の産出額 */
  function height(v, mx) {
    return Math.sqrt(v / mx) * 260000 + 2000;
  }
  var map = null,
    geo = null,
    flat = HERO && !reduce, // hero は、地図ができるまで柱を伸ばさずに待ち、できたら伸ばす
    picked = /** @type {string | null} */ (null), // hero で選んだ県(墨で塗る。暗いテーマでは白)
    NOW = /** @type {Record<string, {h: number, c: number[]}>} */ ({}), // 県ごとの、いま描いている高さと色
    run = 0; // 高さを変えていく動きの番号(次の切り替えが始まったら、前の動きはやめる)
  /** 県ごとの高さと色を、いまの値から to へ変える。ms を渡すと、その時間をかけて伸び縮みさせる
   * @param {Record<string, {h: number, c: number[]}>} to @param {number} [ms] */
  function tween(to, ms) {
    var from = NOW,
      my = ++run,
      t0 = /** @type {number | null} */ (null);
    var put = function (e) {
      var now = /** @type {Record<string, {h: number, c: number[]}>} */ ({});
      geo.features.forEach(function (f) {
        var id = f.properties.id,
          b = to[id],
          a = from[id] || b;
        now[id] = { h: a.h + (b.h - a.h) * e, c: mix(a.c, b.c, e) };
        f.properties.h = now[id].h;
        f.properties.c = css(now[id].c);
      });
      NOW = now;
      if (map && map.getSource && map.getSource("pref")) map.getSource("pref").setData(geo);
    };
    if (!ms || reduce) return put(1);
    (function step(ts) {
      if (my !== run) return;
      if (t0 === null) t0 = ts;
      var t = Math.min(1, (ts - t0) / ms);
      put(1 - Math.pow(1 - t, 3));
      if (t < 1) requestAnimationFrame(step);
    })(performance.now());
  }
  /** @param {number} [ms] 柱の高さと色を変えるのにかける時間(ミリ秒)。省くとすぐに切り替える */
  function render(ms) {
    var k = sel.value,
      V = values(k),
      mx = 0,
      rows = [],
      vmin = 1,
      vmax = 0;
    Object.keys(V).forEach(function (i) {
      if (V[i].v > mx) mx = V[i].v;
      if (V[i].va < vmin) vmin = V[i].va;
      if (V[i].va > vmax) vmax = V[i].va;
      if (V[i].v != null) rows.push(V[i]);
    });
    // 地図(境界データを読み込めたとき)。下の一覧や説明は、地図がなくても出す
    if (geo) {
      var to = /** @type {Record<string, {h: number, c: number[]}>} */ ({});
      geo.features.forEach(function (f) {
        var id = f.properties.id,
          d = V[id],
          has = d && d.v != null;
        to[id] = {
          h: has ? (flat ? 2000 : height(d.v, mx)) : 600,
          c:
            picked !== null && String(id) === picked
              ? theme().pick
              : has
                ? k === "all"
                  ? ramp((d.va - vmin) / (vmax - vmin || 1))
                  : col(d.lq == null ? 0.5 : d.lq)
                : theme().off,
        };
      });
      tween(to, ms);
    }
    rows.sort(function (a, b) {
      return b.v - a.v;
    });
    var nm = k === "all" ? "すべての産業" : INDS[k];
    if (list) {
      list.innerHTML =
        '<caption class="text-left text-sm font-bold pb-2">' +
        (k === "all" ? "総産出額" : nm) +
        '（産出額の大きい順）</caption><thead><tr><th>都道府県</th><th class="text-right">産出額（兆円）</th><th class="text-right">' +
        (k === "all" ? "付加価値率" : "特化係数") +
        "</th></tr></thead><tbody>" +
        rows
          .map(function (d) {
            return (
              '<tr><td><a class="link" href="prefecture/' +
              d.slug +
              '.html">' +
              d.name +
              '</a></td><td class="text-right">' +
              d.v.toFixed(2) +
              '</td><td class="text-right">' +
              (k === "all" ? (d.va * 100).toFixed(1) + "%" : d.lq == null ? "−" : d.lq.toFixed(2)) +
              "</td></tr>"
            );
          })
          .join("") +
        "</tbody>";
    }
    if (note)
      note.textContent =
        k === "all"
          ? "高さ＝総産出額、色＝付加価値率（緑から茶へ、茶に近いほど高い）。"
          : "高さ＝その産業の産出額、色＝特化係数（緑から茶へ、茶に近いほど全国平均より集中）。灰色はデータなし、または部門を合算していて比べられない県です。";
    var lt = document.getElementById("pm-legend-t");
    if (lt)
      lt.textContent =
        k === "all" ? "高さ＝総産出額　／　色＝付加価値率" : "高さ＝産出額　／　色＝集中度（特化係数）";
    if (cap) {
      var top = rows
        .slice(0, 3)
        .map(function (d) {
          return d.name;
        })
        .join("・");
      cap.textContent =
        "表示中：" +
        nm +
        "　産出額が大きい県：" +
        top +
        "（データのある" +
        Object.keys(P).length +
        "都道府県のうち）";
    }
    document.querySelectorAll(".pm-chip").forEach(function (b) {
      var on = b.getAttribute("data-k") === k;
      b.classList.toggle("pm-on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (ins) {
      var h = "";
      if (k === "all") {
        var t = rows[0];
        if (t)
          h =
            '<span class="pm-ins-n">' +
            t.name +
            '</span><span class="pm-ins-v">' +
            t.v.toFixed(1) +
            '<small>兆円</small></span><span class="pm-ins-d">総産出額が最も大きい県</span>';
      } else {
        /** @type {{n: string, lq: number} | null} */
        var best = null;
        Object.keys(P).forEach(function (id) {
          var p = P[id],
            s = p.s[k];
          if (s && s[1] != null && p.t > 0 && s[0] / p.t >= 0.005 && (!best || s[1] > best.lq))
            best = { n: p.n, lq: s[1] };
        });
        if (best)
          h =
            '<span class="pm-ins-n">' +
            best.n +
            '</span><span class="pm-ins-v">' +
            best.lq.toFixed(1) +
            '<small>倍</small></span><span class="pm-ins-d">全国平均と比べた集中度（特化係数）</span>';
      }
      ins.innerHTML = h;
    }
  }
  function loadLib(cb) {
    if (window.maplibregl) return cb();
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "vendor/maplibre-gl.css";
    document.head.appendChild(l);
    var s = document.createElement("script");
    s.src = "vendor/maplibre-gl.js";
    s.onload = cb;
    s.onerror = nomap;
    document.head.appendChild(s);
  }
  /** 立体地図を出せないとき(WebGL が使えない、地図の部品を読み込めない) */
  function nomap() {
    if (!HERO)
      box.innerHTML =
        '<p class="p-6 text-sm">この環境では3D地図を表示できません。下の一覧をご覧ください。</p>';
    else {
      // トップ: 地図の枠と凡例ごと隠す(問いと答えの文はそのまま使える)
      var hp = root.closest(".hp");
      if (hp) hp.classList.add("hp-nomap");
    }
  }
  function rgb() {
    var cv = document.createElement("canvas");
    cv.width = cv.height = 1;
    var cx = cv.getContext("2d");
    cx.fillStyle = getComputedStyle(document.body).backgroundColor;
    cx.fillRect(0, 0, 1, 1);
    var p = cx.getImageData(0, 0, 1, 1).data;
    return "rgb(" + p[0] + "," + p[1] + "," + p[2] + ")";
  } // oklch等はMapLibreが読めない
  // トップ: 日本(はめ込みを含む)が、柱の上の端まで枠に収まるように、向き・ズーム・中心を決める。
  // 傾けた地図では、緯度・経度の範囲だけからは決められないので、県の輪郭の点を画面に投影して大きさを測る。
  // 柱は真上ではなく、カメラの真下の点(画面の下の外)から遠ざかる向きに伸びて見える。端の県の柱は外側へ傾くので、
  // 柱の上の端も計算して、枠からはみ出さないようにする。高さは、その県の柱がいちばん高くなるとき(tallest)で見積もる。
  // 産業を切り替えるたびに合わせ直すと地図が動いてしまうので、最初に1回だけ、どの産業でも収まる位置に決める。
  // 枠が横長か縦長かで収まりのよい向きが違うので、いくつかの向きを試して、いちばん大きく表示できるものを選ぶ。
  var PTS = /** @type {number[][]} */ ([]), // [経度, 緯度, 柱の高さ(メートル)]
    moved = false; // 人が地図を動かしたあとは、勝手に合わせ直さない
  /** 県ごとに、柱がいちばん高くなるときの高さ(メートル)。トップで出しうる産業(どこかの県の上位に入る産業と、すべての産業の合計)で調べる */
  function tallest() {
    var ks = /** @type {Record<string, number>} */ ({ all: 1 }),
      out = /** @type {Record<string, number>} */ ({});
    ks[sel.value] = 1;
    Object.keys(P).forEach(function (id) {
      (P[id].x || []).forEach(function (r) {
        if (r[1]) ks[r[1]] = 1;
      });
    });
    Object.keys(ks).forEach(function (k) {
      var V = values(k),
        mx = 0;
      Object.keys(V).forEach(function (i) {
        if (V[i].v > mx) mx = V[i].v;
      });
      Object.keys(V).forEach(function (i) {
        if (V[i].v != null) out[i] = Math.max(out[i] || 0, height(V[i].v, mx));
      });
    });
    return out;
  }
  function fitHero() {
    if (!map || !PTS.length) return;
    var W = box.clientWidth,
      H = box.clientHeight;
    if (W < 50 || H < 50) return;
    var top = 14,
      side = 14,
      bottom = 30; // 下は、出典の文字の分
    // カメラ: 画面の中心を向いた透視投影。f は焦点距離(ピクセル)、(W/2, ny) はカメラの真下の点が見える位置
    var rad = Math.PI / 180,
      fov = (map.getVerticalFieldOfView ? map.getVerticalFieldOfView() : 36.87) * rad,
      f = H / 2 / Math.tan(fov / 2),
      tan = Math.tan(map.getPitch() * rad),
      cos = Math.cos(map.getPitch() * rad),
      ny = H / 2 + f * tan;
    /** いまの向きのまま、輪郭と柱が枠に収まるズームと中心に合わせる(数回くり返して収束させる) */
    var once = function () {
      for (var n = 0; n < 5; n++) {
        // 1メートルが画面の何ピクセルか(MapLibre は、高さを地図の中心の緯度の縮尺で描く)
        var ppm = (512 * Math.pow(2, map.getZoom())) / (40075016.686 * Math.cos(map.getCenter().lat * rad)),
          x0 = 1e9,
          x1 = -1e9,
          y0 = 1e9,
          y1 = -1e9;
        for (var i = 0; i < PTS.length; i++) {
          var p = map.project([PTS[i][0], PTS[i][1]]),
            gz = (f * f) / (f - (H / 2 - p.y) * tan), // 地面の点の、カメラからの奥行き
            k = gz / (gz - PTS[i][2] * ppm * cos), // 柱の上の端は、カメラの真下の点から見て k 倍の位置に見える
            tx = W / 2 + (p.x - W / 2) * k,
            ty = ny + (p.y - ny) * k;
          x0 = Math.min(x0, p.x, tx);
          x1 = Math.max(x1, p.x, tx);
          y0 = Math.min(y0, p.y, ty);
          y1 = Math.max(y1, p.y, ty);
        }
        var s = Math.min((W - side * 2) / (x1 - x0), (H - top - bottom) / (y1 - y0));
        map.jumpTo({
          // いまの中心を、輪郭の中心と(余白を引いた)枠の中心のずれの分だけ動かす
          center: map.unproject([(x0 + x1) / 2, H / 2 + ((y0 + y1) / 2 - (top + (H - top - bottom) / 2))]),
          zoom: Math.max(2.5, Math.min(7, map.getZoom() + Math.log(s) / Math.LN2)),
        });
      }
      return { z: map.getZoom(), c: map.getCenter() };
    };
    var best = /** @type {{b: number, z: number, c: any} | null} */ (null);
    [-20, -12, -4, 4, 12, 20].forEach(function (b) {
      map.jumpTo({ bearing: b });
      var r = once();
      if (!best || r.z > best.z + 0.01) best = { b: b, z: r.z, c: r.c };
    });
    if (best) map.jumpTo({ bearing: best.b, zoom: best.z, center: best.c });
  }
  function init() {
    var small = window.innerWidth < 640;
    map = new maplibregl.Map({
      container: box,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "bg", type: "background", paint: { "background-color": rgb() } }],
        light: { anchor: "viewport", color: "#ffffff", intensity: 0.35, position: [1.5, 200, 35] },
      },
      center: HERO ? [138.6, 37.6] : [137.5, 37.2],
      zoom: HERO ? 4 : small ? 3.6 : 4.6,
      pitch: HERO ? 52 : 45,
      bearing: -12,
      minZoom: 2.5,
      maxZoom: 8,
      cooperativeGestures: HERO,
      // トップは、右下にはめ込み(沖縄・奄美)があるので、出典を左下に、文字だけで出す(見た目は pages/index.html)
      attributionControl: HERO
        ? false
        : { compact: true, customAttribution: "境界: 地球地図日本(国土地理院)" },
    });
    if (HERO) {
      map.addControl(
        new maplibregl.AttributionControl({
          compact: false,
          customAttribution: "境界: 地球地図日本(国土地理院)",
        }),
        "bottom-left"
      );
      fitHero();
      map.on("resize", function () {
        if (!moved) fitHero();
      });
      ["dragstart", "zoomstart", "rotatestart", "pitchstart"].forEach(function (ev) {
        map.on(ev, function (e) {
          if (e.originalEvent) moved = true; // 人の操作で始まったものだけ
        });
      });
    }
    if (!HERO) map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.on("load", function () {
      map.addSource("pref", { type: "geojson", data: geo });
      if (FRAME) {
        map.addSource("frame", { type: "geojson", data: FRAME });
        map.addLayer({
          id: "frame",
          type: "line",
          source: "frame",
          paint: { "line-color": "#64748b", "line-opacity": 0.5, "line-width": 1, "line-dasharray": [2, 2] },
        });
      }
      map.addLayer({
        id: "ext",
        type: "fill-extrusion",
        source: "pref",
        paint: {
          "fill-extrusion-color": ["get", "c"],
          "fill-extrusion-height": ["get", "h"],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.94,
          "fill-extrusion-vertical-gradient": true,
        },
      });
      if (window.MutationObserver)
        new MutationObserver(function () {
          TH = null;
          map.setPaintProperty("bg", "background-color", rgb());
          render();
        }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      var pop = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
      map.on("mousemove", "ext", function (e) {
        var f = e.features[0],
          V = values(sel.value)[f.properties.id];
        if (!V) return;
        map.getCanvas().style.cursor = "pointer";
        pop
          .setLngLat(e.lngLat)
          .setHTML(
            "<b>" +
              f.properties.name +
              "</b><br>" +
              (V.v == null
                ? "データなし"
                : "産出額 " +
                  V.v.toFixed(2) +
                  "兆円" +
                  (sel.value === "all"
                    ? "<br>付加価値率 " + (V.va * 100).toFixed(1) + "%"
                    : V.lq == null
                      ? ""
                      : HERO
                        ? "<br>全国平均の " + V.lq.toFixed(1) + "倍の集中度"
                        : "<br>特化係数 " + V.lq.toFixed(2)))
          )
          .addTo(map);
      });
      map.on("mouseleave", "ext", function () {
        map.getCanvas().style.cursor = "";
        pop.remove();
      });
      map.on("click", "ext", function (e) {
        var id = e.features[0].properties.id,
          V = values(sel.value)[id];
        if (!V) return;
        if (HERO) root.dispatchEvent(new CustomEvent("pm:pick", { detail: { id: String(id) } }));
        else location.href = "prefecture/" + V.slug + ".html";
      });
      // 地図ができたら、柱を伸ばす(トップ。1.2秒)
      flat = false;
      render(HERO && !reduce ? 1200 : 0);
    });
  }
  // トップでは、沖縄県と鹿児島県の奄美などの島々を、関東の東の海上に寄せて表示する(はめ込み)。地図ページは実際の位置のまま。
  // 本土の東西・南北の範囲の中に収まる位置なので、地図全体を大きく表示できる
  var DX = 17.2,
    DY = 5.9,
    FRAME = null;
  function inset(g) {
    var bb = [999, 999, -999, -999];
    var mv = function (poly) {
      return poly.map(function (r) {
        return r.map(function (c) {
          var x = c[0] + DX,
            y = c[1] + DY;
          bb = [Math.min(bb[0], x), Math.min(bb[1], y), Math.max(bb[2], x), Math.max(bb[3], y)];
          return [x, y];
        });
      });
    };
    var cy = function (poly) {
      var s = 0;
      poly[0].forEach(function (c) {
        s += c[1];
      });
      return s / poly[0].length;
    };
    g.features.forEach(function (f) {
      var id = f.properties.id;
      if (id !== 47 && id !== 46) return;
      f.geometry.coordinates = f.geometry.coordinates.map(function (poly) {
        return id === 47 || cy(poly) < 29.5 ? mv(poly) : poly;
      });
    });
    var x0 = bb[0] - 0.35,
      x1 = bb[2] + 0.35,
      y0 = bb[1] - 0.35,
      y1 = bb[3] + 0.35; // はめ込みの枠
    // 枠の四隅も、地図を枠に合わせるための点に入れる
    PTS.push([x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]);
    FRAME = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [x0, y0],
              [x1, y0],
              [x1, y1],
              [x0, y1],
              [x0, y0],
            ],
          },
        },
      ],
    };
  }
  function start() {
    fetch("vendor/japan-pref.json")
      .then(function (r) {
        return r.json();
      })
      .then(function (g) {
        if (HERO) inset(g);
        var hm = HERO ? tallest() : {};
        g.features.forEach(function (f) {
          // 枠に合わせるための点(輪郭の点を3つおきに。柱がいちばん高くなるときの高さを添える)
          var h = hm[f.properties.id] || 600;
          f.geometry.coordinates.forEach(function (poly) {
            for (var i = 0; i < poly[0].length; i += 3) PTS.push([poly[0][i][0], poly[0][i][1], h]);
          });
        });
        geo = g;
        render();
        if (!ok()) return nomap();
        loadLib(init);
      })
      .catch(nomap);
  }
  sel.addEventListener("change", function () {
    render(450);
  });
  render(); // 一覧と説明は、地図の読み込みを待たずに出す
  root.addEventListener("pm:set", function (ev) {
    var d = /** @type {CustomEvent} */ (ev).detail || {};
    if (d.k) sel.value = d.k;
    if ("id" in d) picked = d.id;
    render(d.user ? 450 : 0); // 人が選んだときは、柱が前の高さから伸び縮みする
  });
  document.querySelectorAll(".pm-chip").forEach(function (b) {
    b.addEventListener("click", function () {
      sel.value = b.getAttribute("data-k");
      render(450);
    });
  });
  var fl = document.getElementById("pm-flat"),
    tl = document.getElementById("pm-tilt");
  if (fl)
    fl.addEventListener("click", function () {
      if (map) map.easeTo({ pitch: 0, bearing: 0, duration: 600 });
    });
  if (tl)
    tl.addEventListener("click", function () {
      if (map) map.easeTo({ pitch: 45, bearing: -12, duration: 600 });
    });
  if (HERO) {
    // トップは表示を邪魔しないよう、ページの読み込み後に始める
    var go = function () {
      (
        window.requestIdleCallback ||
        function (f) {
          setTimeout(f, 300);
        }
      )(start);
    };
    if (document.readyState === "complete") go();
    else window.addEventListener("load", go);
  } else start();
})();
