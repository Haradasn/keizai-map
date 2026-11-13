/* 県別の立体地図(MapLibre GL JS)。/prefecture-map とトップページで共通。データは pref-map-data.js の window.PREF_MAP。
   使い方: <div id="pm-map" data-prefmap="page|hero"> と <select id="pm-ind">。hero はトップ用(ゆっくり回転・押し出しアニメ・操作は協調ジェスチャー)。
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
      off: css(dark ? mix(m, [255, 255, 255], 0.07) : mix(m, [0, 0, 0], 0.07)),
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
    return css(mix(STOPS[i], STOPS[i + 1], t - i));
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
  var map = null,
    geo = null,
    grow = HERO && !reduce ? 0 : 1,
    picked = /** @type {string | null} */ (null), // hero で選んだ県(朱で塗る)
    stop = false, // hero のゆっくりした回転を止める
    CEN = /** @type {Record<string, number[]>} */ ({});
  function render() {
    if (!geo) return;
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
    });
    geo.features.forEach(function (f) {
      var d = V[f.properties.id],
        has = d && d.v != null;
      f.properties.h = has ? Math.sqrt(d.v / mx) * 260000 * grow + 2000 : 600;
      f.properties.c = has
        ? k === "all"
          ? ramp((d.va - vmin) / (vmax - vmin || 1))
          : col(d.lq == null ? 0.5 : d.lq)
        : theme().off;
      if (picked !== null && String(f.properties.id) === picked) f.properties.c = css(theme().pick);
      if (d && has) rows.push(d);
    });
    if (map && map.getSource && map.getSource("pref")) map.getSource("pref").setData(geo);
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
    document.head.appendChild(s);
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
  function heroZoom() {
    var w = box.clientWidth || 360,
      h = box.clientHeight || 270,
      ppd = Math.min(w / (w < 520 ? 20.5 : 23), h / 14); // 狭い画面では少し寄る
    return Math.max(3, Math.min(5, Math.log((ppd * 360) / 512) / Math.LN2));
  } // 枠に日本(はめ込み含む)が収まるズーム
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
      center: HERO ? [136.9, 36.7] : [137.5, 37.2],
      zoom: HERO ? heroZoom() : small ? 3.6 : 4.6,
      pitch: HERO ? 52 : 45,
      bearing: -12,
      minZoom: 2.5,
      maxZoom: 8,
      cooperativeGestures: HERO,
      attributionControl: { compact: true, customAttribution: "境界: 地球地図日本(国土地理院)" },
    });
    if (!HERO) map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    if (HERO) map.setPadding({ top: 8, left: 4, right: 4, bottom: 18 });
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
                  (V.lq != null ? "<br>特化係数 " + V.lq.toFixed(2) : ""))
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
      render();
      if (HERO && !reduce) {
        // 押し出し(1.2秒)のあと、ゆっくり回転。触れたら止める
        var t0 = null,
          spin = false;
        (function rise(ts) {
          if (t0 === null) t0 = ts;
          var t = Math.min(1, (ts - t0) / 1200);
          grow = 1 - Math.pow(1 - t, 3);
          render();
          if (t < 1) requestAnimationFrame(rise);
          else spin = true;
        })(performance.now());
        var b0 = -12,
          last = /** @type {number | null} */ (null);
        ["mousedown", "touchstart", "wheel", "keydown"].forEach(function (ev) {
          box.addEventListener(
            ev,
            function () {
              stop = true;
            },
            { passive: true }
          );
        });
        document.addEventListener("visibilitychange", function () {
          last = null;
        });
        (function turn(ts) {
          if (stop) return;
          if (spin && !document.hidden) {
            if (last !== null) {
              b0 += (ts - last) * 0.004;
              map.setBearing(-12 + Math.sin(b0 / 12) * 14);
            }
            last = ts;
          }
          requestAnimationFrame(turn);
        })(0);
      }
    });
  }
  // トップでは、沖縄県と鹿児島県の奄美などの島々を、四国の南の海上に寄せて表示する(はめ込み)。地図ページは実際の位置のまま
  var DX = 8.6,
    DY = 3.3,
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
        g.features.forEach(function (f) {
          // 県のおおよその中心(いちばん点の多い多角形の外周の平均)
          var best = /** @type {number[][]} */ ([]);
          f.geometry.coordinates.forEach(function (poly) {
            if (poly[0].length > best.length) best = poly[0];
          });
          var x = 0,
            y = 0;
          best.forEach(function (c) {
            x += c[0];
            y += c[1];
          });
          CEN[String(f.properties.id)] = [x / best.length, y / best.length];
        });
        geo = g;
        render();
        if (!ok()) {
          if (!HERO)
            box.innerHTML =
              '<p class="p-6 text-sm">この環境では3D地図を表示できません。下の一覧をご覧ください。</p>';
          else {
            // トップ: 地図を描けない端末では、地図の枠と凡例ごと隠す(問いと答えの文はそのまま使える)
            var hp = root.closest(".hp");
            if (hp) hp.classList.add("hp-nomap");
          }
          return;
        }
        loadLib(init);
      });
  }
  sel.addEventListener("change", render);
  root.addEventListener("pm:set", function (ev) {
    var d = /** @type {CustomEvent} */ (ev).detail || {};
    if (d.k) sel.value = d.k;
    if ("id" in d) picked = d.id;
    render();
    if (d.user) {
      // 人が選んだときだけ、回転を止めて、選んだ県のほうへ少し寄る
      stop = true;
      var c = picked !== null ? CEN[picked] : null;
      if (map && c && !reduce)
        map.easeTo({ center: [136.9 + (c[0] - 136.9) * 0.3, 36.7 + (c[1] - 36.7) * 0.3], duration: 700 });
    }
  });
  document.querySelectorAll(".pm-chip").forEach(function (b) {
    b.addEventListener("click", function () {
      sel.value = b.getAttribute("data-k");
      render();
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
