// データは explorer.html のインライン script が window.XP に置く
const D = window.XP.data;
const GC = window.XP.gc;
const N = Object.fromEntries(D.nodes.map((n) => [n.id, n]));
/** @type {(id: string) => any} 要素の型は使う側で決まるので any */
const $ = (id) => document.getElementById(id);
const fmt = (x, d = 1) =>
  x == null ? "–" : Number(x).toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (x) => (x == null ? "–" : (x > 0 ? "+" : "") + fmt(x, 1));
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const isMobile = () => innerWidth < 640;
const FK = 6; // 選択時に強調する仕入れ先・販売先の数
const FOVY = 22,
  ZK = 0.6,
  REL = 3; // 3Dの視野角(小さいほど遠近が弱い)と奥行きの圧縮
/* ---- 配色トークン(テーマ切替で再取得) ---- */
let T = {};
function readTokens() {
  const s = getComputedStyle($("xp"));
  const g = (n) => s.getPropertyValue(n).trim();
  T = {
    up: g("--up"),
    flat: g("--flat"),
    down: g("--down"),
    link: g("--link"),
    lin: g("--lin"),
    lout: g("--lout"),
    accent: g("--accent"),
    graph: g("--graph"),
  };
}
const al = (hex, a) =>
  hex +
  Math.round(Math.max(0, Math.min(1, a)) * 255)
    .toString(16)
    .padStart(2, "0");

let topN = 24,
  sel = null,
  flowOn = !REDUCED,
  Graph = null,
  period = "y20",
  view = "3d"; // スマホでも最初は3D(見た目のインパクトを優先。フローへは上で切り替え)
const CH = () => period === "chg";
const val = (e) => (CH() ? e.v22 : e.v);
const tr = (e) => {
  if (CH()) {
    const d = e.s22 != null && e.s20 != null ? e.s22 - e.s20 : 0;
    return d >= 0.8 ? 1 : d <= -0.8 ? -1 : 0;
  }
  const g = e.g || 0;
  return g >= 2 ? 1 : g <= -2 ? -1 : 0;
};
const trCol = (e) => ({ 1: T.up, 0: T.flat, "-1": T.down })[tr(e)];
const nOut = (n) => (CH() && n.o22 != null ? n.o22 : n.out);
const nodeBase = (n) => (CH() ? T.flat : GC[n.grp]); // 円の色: 2020年=部門グループ / 変化=灰色(増減色と混ぜない)

/* ---- 取引(エッジ)の集合 ---- */
let _all = null,
  _allP = null;
function allE() {
  if (_allP !== period) {
    _all = D.edges.filter((e) => e.s !== e.t && val(e) != null && val(e) > 0).sort((a, b) => val(b) - val(a));
    _allP = period;
  }
  return _all;
}
const ovSet = () => new Set(allE().slice(0, topN));
function focusEdges(id) {
  const A = allE();
  return { inn: A.filter((e) => e.t === id).slice(0, FK), out: A.filter((e) => e.s === id).slice(0, FK) };
}
let OV = new Set(),
  NEAR = null,
  LP = [];
function recompute() {
  OV = ovSet();
  NEAR = null;
  if (sel && sel.type === "n") {
    const f = focusEdges(sel.id);
    NEAR = new Set([sel.id]);
    f.inn.concat(f.out).forEach((e) => {
      NEAR.add(e.s);
      NEAR.add(e.t);
    });
    sel.f = f;
  } else if (sel) {
    NEAR = new Set([sel.e.s, sel.e.t]);
  }
  // ラベルを出す順(優先度): 選択 → 取引先 → 生産額の大きい12部門
  LP = [];
  const seen = new Set();
  const add = (id, c) => {
    if (!seen.has(id)) {
      seen.add(id);
      LP.push([id, c]);
    }
  };
  if (sel && sel.type === "n") {
    add(sel.id, "sel");
    sel.f.inn
      .concat(sel.f.out)
      .sort((a, b) => val(b) - val(a))
      .forEach((e) => {
        add(e.s, "hl");
        add(e.t, "hl");
      });
  } else if (sel) {
    add(sel.e.s, "sel");
    add(sel.e.t, "sel");
  }
  D.nodes
    .slice()
    .sort((a, b) => nOut(b) - nOut(a))
    .slice(0, 12)
    .forEach((n) => add(n.id, sel ? "dim" : "big"));
}
const isNear = (id) => !NEAR || NEAR.has(id);
function roleOf(e) {
  if (!sel) return "none";
  if (sel.type === "n") return e.t === sel.id ? "in" : e.s === sel.id ? "out" : "other";
  return e === sel.e ? "sel" : "other";
}
/* 線の見た目: 色・不透明度・太さ(2020年=単色、変化=増減色) */
function estyle(e) {
  const role = roleOf(e),
    inOv = OV.has(e),
    v = val(e);
  const base = CH() ? trCol(e) : T.link;
  if (!sel) return { role, col: base, a: inOv ? (CH() ? 0.6 : 0.5) : 0, w: 0.3 + Math.sqrt(v) * 0.5 };
  if (role === "other") return { role, col: base, a: inOv ? 0.08 : 0, w: 0.2 };
  const col = CH() ? trCol(e) : role === "in" ? T.lin : role === "out" ? T.lout : T.accent;
  return { role, col, a: 0.95, w: 0.7 + Math.sqrt(v) * 1.1 };
}
/* ---- 凡例・ヒント ---- */
function legend() {
  const nodeRow = CH()
    ? `<div class="r"><em>円</em><span>灰色(この表示では色に意味はありません。大きさ=2022年の生産額)</span></div>`
    : `<div class="r"><em>円の色</em>${D.groups.map((g, i) => `<span><i style="background:${GC[i]}"></i>${g}</span>`).join("")}</div><div class="r"><em>円の大きさ</em><span>2020年の生産額(大きいほど大きい)</span></div>`;
  const sw = (c, t) => `<span><span class="ln" style="background:${c}"></span>${t}</span>`;
  const lk = CH()
    ? `<div class="r"><em>線の色</em>${sw(T.up, "買い手の費用に占める割合が上昇(+0.8pt〜)")}${sw(T.flat, "横ばい")}${sw(T.down, "低下(−0.8pt〜)")}</div><div class="r"><em>線の太さ</em><span>2022年の取引額。向きは売り手→買い手(矢印・粒子)</span></div>`
    : `<div class="r"><em>線</em>${sw(T.link, "取引額の大きい上位" + topN + "本(薄く表示)")}${sw(T.lin, "選択した産業の仕入れ先")}${sw(T.lout, "選択した産業の販売先")}</div><div class="r"><em>線の太さ</em><span>取引額。向きは売り手→買い手(矢印・粒子)</span></div>`;
  $("legend").innerHTML =
    nodeRow +
    lk +
    `<div class="r"><span class="note">配置は固定で、同じ色(部門グループ)がまとまるように並べただけです。距離そのものに厳密な意味はありません。3Dは遠近を弱めてあり、円の大きさは生産額の比較に使えます。</span></div>`;
}
function syncUI() {
  $("pick").value = sel && sel.type === "n" ? sel.id : "";
  $("b-clear").disabled = !sel;
  const sw = (c) => `<span class="sw" style="background:${c}"></span>`;
  let h;
  if (!sel)
    h = `<b>使い方:</b> 円(産業)をクリック、または「産業を選ぶ」で、取引先だけが浮かび上がります。(薄い線は取引額が大きい上位${topN}本)`;
  else if (sel.type === "n") {
    const f = sel.f;
    h =
      `<b>${N[sel.id].name}</b> を選択中。` +
      (CH()
        ? `線の色は増減(凡例参照)。向きは売り手→買い手です。`
        : `${sw(T.lin)}仕入れ先(この産業が買う相手)上位${f.inn.length}${sw(T.lout)}販売先(この産業が売る相手)上位${f.out.length}`) +
      ` 他は薄くしています。<a class="m-only" href="#panel" style="color:var(--accent)">詳細を見る ↓</a>`;
  } else
    h = `<b>${N[sel.e.s].name} → ${N[sel.e.t].name}</b> の取引を選択中。<a class="m-only" href="#panel" style="color:var(--accent)">詳細を見る ↓</a>`;
  $("hint").innerHTML = h;
  legend();
}
/* ---- 3D ---- */
const bbox = (() => {
  const xs = D.nodes.map((n) => n.x),
    ys = D.nodes.map((n) => n.y);
  return {
    cx: (Math.min(...xs) + Math.max(...xs)) / 2,
    cy: (Math.min(...ys) + Math.max(...ys)) / 2,
    w: Math.max(...xs) - Math.min(...xs),
    h: Math.max(...ys) - Math.min(...ys),
  };
})();
function fit3d(ms) {
  if (!Graph) return;
  const W = $("stage").clientWidth,
    H = $("stage").clientHeight,
    asp = W / Math.max(H, 1);
  const padW = bbox.w + 50,
    padH = bbox.h + 50; // 余白つきで全体を収める
  const visH = Math.max(padH, padW / asp);
  const d = visH / (2 * Math.tan((FOVY * Math.PI) / 360));
  Graph.cameraPosition({ x: bbox.cx, y: bbox.cy, z: d }, { x: bbox.cx, y: bbox.cy, z: 0 }, ms || 0);
}
function initGraph() {
  try {
    if (typeof ForceGraph3D === "undefined") throw 0;
    Graph = ForceGraph3D({ controlType: "orbit" })($("g"))
      .backgroundColor(T.graph)
      .graphData({
        nodes: D.nodes.map((n) => ({ ...n, fx: n.x, fy: n.y, fz: n.z * ZK })),
        links: allE().map((e) => ({ source: e.s, target: e.t, e })),
      })
      .nodeId("id")
      .nodeRelSize(REL)
      .nodeResolution(20)
      .nodeOpacity(0.95)
      .nodeLabel(
        (n) =>
          `<div style="font:13px sans-serif;padding:3px 6px;background:rgba(10,12,18,.9);color:#fff;border-radius:3px">${n.name}<br>${fmt(nOut(n), 0)}兆円${CH() && n.rg != null ? ` / 数量${sgn(n.rg)}%・価格${sgn(n.pc)}%` : ` / 実質${sgn(n.cagr)}%/年`}</div>`
      )
      .linkOpacity(1)
      .linkDirectionalArrowRelPos(1)
      .linkDirectionalParticleWidth(2)
      .linkLabel(
        (l) =>
          `<div style="font:12px sans-serif;padding:3px 6px;background:rgba(10,12,18,.9);color:#fff;border-radius:3px">${N[l.e.s].name} → ${N[l.e.t].name}<br>${CH() ? `${fmt(l.e.v20, 1)}兆 → ${fmt(l.e.v22, 1)}兆円` : `${fmt(l.e.v, 1)}兆円 / 実質${sgn(l.e.g)}%/年`}</div>`
      )
      .onNodeClick((n) => select({ type: "n", id: n.id }))
      .onLinkClick((l) => {
        if (estyle(l.e).a > 0) select({ type: "e", e: l.e });
      })
      .onBackgroundClick(() => select(null))
      .cooldownTicks(0)
      .showNavInfo(false)
      .width($("stage").clientWidth)
      .height($("stage").clientHeight);
    Graph.camera().fov = FOVY;
    Graph.camera().updateProjectionMatrix();
    Graph.controls().autoRotateSpeed = 1.1;
    applyStyle();
    fit3d(0);
    new ResizeObserver(() => {
      if (Graph) Graph.width($("stage").clientWidth).height($("stage").clientHeight);
      if (view === "fl") drawFlow();
    }).observe($("stage"));
    labelLoop();
  } catch (err) {
    $("fallback").style.display = "flex";
    Graph = null;
    setView("fl");
  }
}
function applyStyle() {
  // 新しい関数を渡して再描画させる
  if (!Graph) return;
  Graph.nodeVal((n) => Math.max(nOut(n), 2))
    .nodeColor((n) => {
      const c = nodeBase(n);
      return isNear(n.id) ? c : al(c, 0.2);
    })
    .linkVisibility((l) => estyle(l.e).a > 0)
    .linkWidth((l) => estyle(l.e).w)
    .linkColor((l) => {
      const s = estyle(l.e);
      return al(s.col, s.a);
    })
    .linkDirectionalArrowLength((l) => {
      const r = estyle(l.e).role;
      return r === "in" || r === "out" || r === "sel" ? 5 : 0;
    })
    .linkDirectionalParticles((l) => {
      const r = estyle(l.e).role;
      return flowOn && (r === "in" || r === "out" || r === "sel") ? Math.min(4, Math.ceil(val(l.e) / 2)) : 0;
    })
    .linkDirectionalParticleColor((l) => estyle(l.e).col)
    .linkDirectionalParticleSpeed((l) => 0.004 + val(l.e) * 0.0004);
}
let labelEls = {};
function labelLoop() {
  const box = $("labels");
  D.nodes.forEach((n) => {
    const d = document.createElement("div");
    d.className = "lb";
    d.textContent = n.name;
    d.style.display = "none";
    box.appendChild(d);
    labelEls[n.id] = d;
  });
  (function tick() {
    const on = view === "3d" && Graph;
    if (!on) {
      for (const id in labelEls) labelEls[id].style.display = "none";
    } else {
      const SW = $("stage").clientWidth,
        placed = [],
        shown = new Set(),
        fs = SW < 500 ? 11 : 11.5,
        cw = fs + 0.5;
      for (const [id, cls] of LP) {
        const n = Graph.graphData().nodes.find((x) => x.id === id);
        if (!n || n.x == null) continue;
        const d = labelEls[id],
          p = Graph.graph2ScreenCoords(n.x, n.y, n.z || 0),
          q = Graph.graph2ScreenCoords(n.x + Math.cbrt(Math.max(nOut(n), 2)) * REL, n.y, n.z || 0);
        const r = Math.abs(q.x - p.x),
          w = n.name.length * cw + (cls === "sel" ? 18 : 6),
          h = cls === "sel" ? 20 : 16;
        const x = Math.min(Math.max(p.x, w / 2 + 2), SW - w / 2 - 2),
          y = p.y + r + 2;
        const b = { l: x - w / 2 - 2, r: x + w / 2 + 2, t: y - 1, b: y + h };
        if (placed.some((o) => b.l < o.r && b.r > o.l && b.t < o.b && b.b > o.t)) {
          continue;
        }
        placed.push(b);
        shown.add(id);
        d.style.display = "";
        d.style.left = x + "px";
        d.style.top = y + "px";
        d.style.fontSize = fs + "px";
        d.className = "lb" + (cls === "sel" ? " sel" : cls === "dim" ? " dim" : "");
      }
      for (const id in labelEls) if (!shown.has(id)) labelEls[id].style.display = "none";
    }
    requestAnimationFrame(tick);
  })();
}
function refresh() {
  applyStyle();
  if (view === "fl") drawFlow();
}
function reloadLinks() {
  if (Graph)
    Graph.graphData({
      nodes: Graph.graphData().nodes,
      links: allE().map((e) => ({ source: e.s, target: e.t, e })),
    });
  recompute();
  refresh();
}
function select(s) {
  sel = s;
  recompute();
  syncUI();
  refresh();
  render();
}
/* ---- フロー図(売り手 → 買い手の2列) ---- */
function flowEdges() {
  const s = new Set(OV);
  if (sel && sel.type === "n") {
    sel.f.inn.concat(sel.f.out).forEach((e) => s.add(e));
  } else if (sel && allE().includes(sel.e)) s.add(sel.e);
  return allE().filter((e) => s.has(e));
}
function drawFlow() {
  const svg = $("flow"),
    W = $("stage").clientWidth,
    H = $("stage").clientHeight;
  if (!W || !H) return;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const mob = W < 560,
    fs = mob ? 10.5 : 11.5,
    colW = mob ? 10 : 14,
    lx = Math.min(190, W * (mob ? 0.31 : 0.26)),
    rx = W - lx - colW,
    top = 34,
    bot = H - 10;
  const maxCh = Math.max(3, Math.floor((lx - 10) / fs)),
    cut = (s) => (s.length > maxCh ? s.slice(0, maxCh - 1) + "…" : s);
  const L = flowEdges(),
    sOut = {},
    tIn = {};
  L.forEach((e) => {
    sOut[e.s] = (sOut[e.s] || 0) + val(e);
    tIn[e.t] = (tIn[e.t] || 0) + val(e);
  });
  const order = (o) => Object.keys(o).sort((a, b) => N[a].grp - N[b].grp || o[b] - o[a]);
  const lay = (o) => {
    const ids = order(o),
      tot = Object.values(o).reduce((a, b) => a + b, 0),
      avail = bot - top - ids.length * 4,
      sc = avail / tot;
    let y = top;
    const m = {};
    ids.forEach((id) => {
      m[id] = { y, h: o[id] * sc, sc };
      y += o[id] * sc + 4;
    });
    return m;
  };
  const LS = lay(sOut),
    RT = lay(tIn),
    oS = order(sOut),
    oT = order(tIn);
  const bySrc = {},
    byTgt = {};
  L.forEach((e) => {
    (bySrc[e.s] = bySrc[e.s] || []).push(e);
    (byTgt[e.t] = byTgt[e.t] || []).push(e);
  });
  for (const k in bySrc) bySrc[k].sort((a, b) => oT.indexOf(a.t) - oT.indexOf(b.t));
  for (const k in byTgt) byTgt[k].sort((a, b) => oS.indexOf(a.s) - oS.indexOf(b.s));
  const y0s = {},
    y0t = {};
  for (const k in bySrc) {
    let y = LS[k].y;
    bySrc[k].forEach((e) => {
      y0s[e.s + "|" + e.t] = y;
      y += val(e) * LS[k].sc;
    });
  }
  for (const k in byTgt) {
    let y = RT[k].y;
    byTgt[k].forEach((e) => {
      y0t[e.s + "|" + e.t] = y;
      y += val(e) * RT[k].sc;
    });
  }
  const focusFirst = L.slice().sort((a, b) => Number(estyle(a).a > 0.5) - Number(estyle(b).a > 0.5)); // 強調する帯を手前に
  const paths = focusFirst
    .map((e) => {
      const k = e.s + "|" + e.t,
        ys = y0s[k],
        yt = y0t[k],
        hs = val(e) * LS[e.s].sc,
        ht = val(e) * RT[e.t].sc,
        st = estyle(e);
      const x1 = lx + colW,
        x2 = rx,
        cx = (x1 + x2) / 2,
        op = !sel ? (CH() ? 0.5 : 0.4) : st.a > 0.5 ? 0.75 : 0.07;
      return `<path class="fl" data-e="${D.edges.indexOf(e)}" d="M${x1},${ys} C${cx},${ys} ${cx},${yt} ${x2},${yt} L${x2},${yt + ht} C${cx},${yt + ht} ${cx},${ys + hs} ${x1},${ys + hs} Z" fill="${st.a > 0.5 || !sel ? st.col : T.link}" fill-opacity="${op}"><title>${N[e.s].name} → ${N[e.t].name} ${CH() ? fmt(e.v20, 1) + "兆→" + fmt(e.v22, 1) + "兆円" : fmt(e.v, 1) + "兆円"}</title></path>`;
    })
    .join("");
  const labelSet = (M) => {
    const c = Object.keys(M)
        .map((id) => ({
          id,
          y: M[id].y + Math.max(M[id].h, 2) / 2,
          pri: (sel && sel.type === "n" && sel.id === id ? 2e6 : sel && NEAR.has(id) ? 1e6 : 0) + M[id].h,
        }))
        .sort((a, b) => b.pri - a.pri),
      ys = [],
      ok = new Set();
    for (const q of c) {
      if (!(q.pri >= 1e6 || M[q.id].h >= (mob ? 13 : 11)) || ys.some((y) => Math.abs(y - q.y) < fs + 3))
        continue;
      ys.push(q.y);
      ok.add(q.id);
    }
    return ok;
  };
  const nodesSvg = (M, x, right) => {
    const LB = labelSet(M);
    return Object.keys(M)
      .map((id) => {
        const m = M[id],
          n = N[id],
          near = isNear(id),
          h = Math.max(m.h, 2),
          show = LB.has(id);
        return `<g class="fl" data-n="${id}" opacity="${near ? 1 : 0.3}"><rect x="${x}" y="${m.y}" width="${colW}" height="${h}" rx="2" fill="${nodeBase(n)}"/><text x="${right ? x + colW + 6 : x - 6}" y="${m.y + h / 2 + 4}" text-anchor="${right ? "start" : "end"}" style="font-size:${fs}px${sel && sel.type === "n" && sel.id === id ? ";font-weight:700" : ""}">${show ? cut(n.name) : ""}</text><title>${n.name}</title></g>`;
      })
      .join("");
  };
  svg.innerHTML =
    `<text x="${lx}" y="20" text-anchor="end" style="font-weight:600;font-size:${fs}px">売る側</text><text x="${rx + colW}" y="20" style="font-weight:600;font-size:${fs}px">買う側</text><text x="${W / 2}" y="20" text-anchor="middle" style="fill:var(--muted);font-size:${fs - 0.5}px">帯の太さ=取引額(${CH() ? "2022年" : "2020年"})</text>` +
    paths +
    nodesSvg(LS, lx, false) +
    nodesSvg(RT, rx, true);
}
$("flow").addEventListener("click", (ev) => {
  const t = /** @type {HTMLElement | null} */ (
    /** @type {Element} */ (ev.target).closest("[data-e],[data-n]")
  );
  if (!t) {
    select(null);
    return;
  }
  if (t.dataset.e != null) select({ type: "e", e: D.edges[+t.dataset.e] });
  else select({ type: "n", id: t.dataset.n });
});
/* ---- 右パネル ---- */
function spark(n) {
  const v = n.real,
    w = 170,
    h = 46,
    mx = Math.max(...v),
    mn = Math.min(...v),
    pad = 6;
  const yy = (x) => h - pad - ((x - mn) / (mx - mn || 1)) * (h - 2 * pad),
    xx = (i) => 10 + (i * (w - 20)) / 2;
  const idx = v.map((x) => (x / v[0]) * 100);
  const c = n.cagr >= 2 ? T.up : n.cagr <= -2 ? T.down : T.flat;
  return `<svg width="${w}" height="${h + 14}" viewBox="0 0 ${w} ${h + 14}" role="img" aria-label="実質生産額の推移">
  <polyline fill="none" stroke="${c}" stroke-width="2" points="${v.map((x, i) => xx(i) + "," + yy(x)).join(" ")}"/>
  ${v.map((x, i) => `<circle cx="${xx(i)}" cy="${yy(x)}" r="3" fill="${c}"/><text x="${xx(i)}" y="${h + 11}" text-anchor="middle">${[2011, 2015, 2020][i]}</text>`).join("")}
  <text x="${w - 2}" y="10" text-anchor="end">2011=100 → ${fmt(idx[2], 0)}</text></svg>`;
}
function bar(g) {
  const c = Math.max(-6, Math.min(6, g || 0));
  const left = c >= 0 ? 50 : 50 + (c / 6) * 50,
    wd = (Math.abs(c) / 6) * 50;
  return `<span class="bar"><i style="left:${left}%;width:${wd}%;background:${g >= 2 ? T.up : g <= -2 ? T.down : T.flat}"></i></span>`;
}
function renderOverview() {
  const hubs = allE()
    .slice(0, 20)
    .reduce((m, e) => ((m[e.s] = (m[e.s] || 0) + 1), m), {});
  const hub = Object.entries(hubs).sort((a, b) => b[1] - a[1])[0];
  let ins = "";
  if (CH()) {
    const top = D.edges
      .filter((e) => e.v20 != null && e.v22 != null)
      .sort((a, b) => b.v22 - b.v20 - (a.v22 - a.v20))
      .slice(0, 3);
    const EN = ["06", "21", "46"],
      enHit = top.some((e) => EN.includes(e.s) || EN.includes(e.t)); // 鉱業・石油石炭製品・電気ガス
    const W = D.nodes.filter((n) => n.o20x && n.o22),
      s20 = W.reduce((a, n) => a + n.o20x, 0),
      s22 = W.reduce((a, n) => a + n.o22, 0);
    const sReal = D.nodes
      .filter((n) => n.o20x && n.rg != null)
      .reduce((a, n) => a + n.o20x * (1 + n.rg / 100), 0);
    const pcTop = D.nodes
      .filter((n) => n.pc != null)
      .sort((a, b) => b.pc - a.pc)
      .slice(0, 3)
      .map((n) => n.name)
      .join("、");
    ins = `<div class="story">2020→2022年に最も増えた取引は、${top.map((e) => `<a href="#" data-e="${D.edges.indexOf(e)}">${N[e.s].name}→${N[e.t].name}</a>(${fmt(e.v20, 1)}→${fmt(e.v22, 1)}兆円)`).join("、")}。${enHit ? "エネルギー関連の取引が含まれています。" : ""}</div>
    <div class="story">2022年の生産額の合計は、2020年比で名目${sgn((s22 / s20 - 1) * 100)}%、価格の影響を除いた実質では${sgn((sReal / s20 - 1) * 100)}%です。値上がりが大きかったのは${pcTop}などです。<small>2021・2022年は経産省の延長表(推計)。2023年以降、生成AIの実用化などは含みません。</small></div>`;
  } else {
    const big = D.nodes.filter((n) => n.out >= 15).sort((a, b) => b.cagr - a.cagr);
    ins = `<div class="story">上位20本の取引のうち<b>${hub[1]}本</b>が「${N[hub[0]].name}」から出ています。${hub[0] === "66" ? "人材・リース・警備・広告などの『外注の受け皿』が、取引の中心にいます。" : ""}</div>
    <div class="story">生産額15兆円以上の部門で、2011→2020年の実質成長が大きいのは:${big
      .slice(0, 4)
      .map((n) => `<a href="#" data-n="${n.id}">${n.name}(${sgn(n.cagr)}%)</a>`)
      .join("、")}。</div>`;
  }
  $("panel").innerHTML = `<h2>全体の見方</h2>
  <p class="note">円(産業)をクリックするか、上の「産業を選ぶ」で選ぶと、仕入れ先と販売先が浮かび上がり、ここに中身と仮説が出ます。線・帯(取引)をクリックすると、その取引の詳細に入れます。</p>
  <h3>目立つ点</h3>${ins}
  <h3>部門一覧(クリックで詳細)</h3>
  ${D.nodes
    .slice()
    .sort((a, b) => nOut(b) - nOut(a))
    .map(
      (n) =>
        `<div class="row" data-n="${n.id}"><i style="width:9px;height:9px;border-radius:50%;background:${GC[n.grp]};flex:none"></i><span class="nm">${n.name}</span><span class="num">${fmt(nOut(n), 0)}兆</span>${CH() ? bar(n.rg != null ? n.rg / 2 : 0) : bar(n.cagr)}<span class="num" style="width:44px;text-align:right">${CH() ? (n.rg != null ? sgn(n.rg) + "%" : "–") : sgn(n.cagr) + "%"}</span></div>`
    )
    .join("")}
  <p class="note" style="margin-top:12px">出典: 令和2年産業連関表、平成23-27-令和2年接続産業連関表(総務省ほか)、延長産業連関表(経産省)。${CH() ? "棒と数字は2020→2022年の数量(実質)の増減。" : "棒と数字は2011→2020年の実質・年率。"}2020年はコロナ禍の年です。仮説は筆者の推測で、検証前のものです。政府が作成・保証したものではありません。</p>`;
}
function edgeRow(e) {
  const v = val(e);
  return `<div class="row" data-e="${D.edges.indexOf(e)}"><span class="nm"><span class="tx">${N[e.s].name} → ${N[e.t].name}</span>${(CH() ? e.st22 : e.story) ? `<span class="tag">${CH() ? e.c22 : e.conf}</span>` : ""}</span><span class="num">${v != null ? fmt(v, 1) + "兆" : "–"}</span>${CH() ? "" : bar(e.g)}</div>`;
}
function renderNode(id) {
  const n = N[id],
    f = sel && sel.type === "n" && sel.id === id ? sel.f : focusEdges(id),
    out = f.out,
    inn = f.inn;
  const bs = n.subs.filter((s) => s.b);
  const chg =
    n.rg != null
      ? `<h3>2020→2022年の変化(延長表)</h3><div class="kv"><div><b>${fmt(n.o20x, 0)}→${fmt(n.o22, 0)}兆</b><span>生産額(名目)</span></div><div><b>${sgn(n.rg)}%</b><span>数量(実質)</span></div><div><b>${sgn(n.pc)}%</b><span>価格</span></div></div>`
      : `<div class="note">この部門は延長表に対応する部門がなく、2022年の数値はありません。</div>`;
  const sw = (c) => (CH() ? "" : `<span class="sw" style="background:${c};margin-left:0"></span>`);
  $("panel").innerHTML = `<span class="back" data-back>← 全体に戻る(選択を解除)</span>
  <h2><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${GC[n.grp]};margin-right:6px"></i>${n.name}</h2>
  <div class="note">${D.groups[n.grp]}</div>
  <div class="kv"><div><b>${fmt(n.out, 0)}兆円</b><span>生産額(2020)</span></div><div><b>${sgn(n.cagr)}%</b><span>実質増減/年(2011→20)</span></div><div><b>${fmt(n.va, 0)}%</b><span>付加価値率</span></div>
  <div><b>${fmt(n.exp, 0)}%</b><span>輸出向け</span></div><div><b>${fmt(n.cons, 0)}%</b><span>家計消費向け</span></div><div><b>${fmt(n.imp, 0)}%</b><span>輸入依存度</span></div></div>
  ${spark(n)}<div class="note">2011〜15年 ${sgn(n.c1)}%/年、2015〜20年 ${sgn(n.c2)}%/年(実質)</div>
  <h3>主な仕入れ先(この部門が買う相手)</h3>${inn.map(edgeRow).join("") || '<div class="note">該当する取引なし</div>'}
  <h3>主な販売先(この部門が売る相手)</h3>${out.map(edgeRow).join("") || '<div class="note">該当する取引なし</div>'}
  ${chg}
  ${bs.length ? `<div class="story">この部門にはブルーオーシャン候補が含まれます:${bs.map((s) => `${s.n}<span class="tag B1">${s.b} ${D.bn[s.b]}</span>`).join("、")}<small>見えにくさと成長などで点数化した仮説。競争の少なさは直接測れていません。</small></div>` : ""}
  <h3>中身(108部門・2020年の生産額と実質増減)</h3>
  ${n.subs.map((s) => `<div class="row" style="cursor:default"><span class="nm" title="${s.n}">${s.n}${s.b ? `<span class="tag B1">${s.b}</span>` : ""}</span><span class="num">${fmt(s.o, 1)}兆</span>${bar(s.g)}<span class="num" style="width:44px;text-align:right">${sgn(s.g)}%</span></div>`).join("")}`;
}
function renderEdge(e) {
  const a = N[e.s],
    b = N[e.t];
  const b20 =
    e.v != null
      ? `<h3>2020年(基本表)</h3><div class="kv"><div><b>${fmt(e.v, 1)}兆円</b><span>取引額</span></div><div><b>${fmt(e.sh, 1)}%</b><span>買い手の費用に占める割合</span></div><div><b>${sgn(e.g)}%</b><span>実質増減/年(2011→20)</span></div></div><div><b>目的:</b> ${e.p || "–"}</div>
  ${e.story ? `<div class="story">${e.story}<small>確からしさ ${e.conf}(A=数字から確かめやすい / B=もっともらしいが未検証 / C=弱い推測)${e.ver ? "<br>確かめ方: " + e.ver : ""}</small><button type="button" class="hyp-fb" data-hyp="${a.name}→${b.name}">この仮説に補足・反論を送る</button></div>` : '<div class="note">この取引には、まだ個別の仮説を付けていません。</div>'}${e.cau ? `<div class="note">注意: ${e.cau}</div>` : ""}`
      : "";
  const c22 =
    e.v22 != null
      ? `<h3>2020→2022年(延長表)</h3><div class="kv"><div><b>${fmt(e.v20, 1)}→${fmt(e.v22, 1)}兆</b><span>取引額(名目)</span></div><div><b>${fmt(e.s20, 1)}→${fmt(e.s22, 1)}%</b><span>買い手の費用に占める割合</span></div><div><b>${e.v20 > 0 ? sgn((e.v22 / e.v20 - 1) * 100) : "–"}%</b><span>名目の増減(2年)</span></div></div>
  ${e.st22 ? `<div class="story">${e.st22}<small>確からしさ ${e.c22}${e.vf22 ? "<br>確かめ方: " + e.vf22 : ""}</small></div>` : '<div class="note">2022年の変化には、まだ個別の仮説を付けていません。名目の増減には値上がりを含みます。</div>'}`
      : "";
  $("panel").innerHTML = `<span class="back" data-back>← 全体に戻る(選択を解除)</span>
  <h2>${a.name} → ${b.name}</h2><div class="note">モノ・サービスの向き(代金は逆向き)</div>
  ${CH() ? c22 + b20 : b20 + c22}
  <h3>両端の部門</h3>
  <div class="row" data-n="${a.id}"><i style="width:9px;height:9px;border-radius:50%;background:${GC[a.grp]}"></i><span class="nm">${a.name}</span><span class="num">${fmt(a.out, 0)}兆</span></div>
  <div class="row" data-n="${b.id}"><i style="width:9px;height:9px;border-radius:50%;background:${GC[b.grp]}"></i><span class="nm">${b.name}</span><span class="num">${fmt(b.out, 0)}兆</span></div>`;
}
function render() {
  if (!sel) renderOverview();
  else if (sel.type === "n") renderNode(sel.id);
  else renderEdge(sel.e);
  $("panel").scrollTop = 0;
}
$("panel").addEventListener("click", (ev) => {
  const t = /** @type {HTMLElement | null} */ (
    /** @type {Element} */ (ev.target).closest("[data-n],[data-e],[data-back]")
  );
  if (!t) return;
  ev.preventDefault();
  if (t.hasAttribute("data-back")) select(null);
  else if (t.dataset.n) select({ type: "n", id: t.dataset.n });
  else select({ type: "e", e: D.edges[+t.dataset.e] });
});
/* ---- 操作 ---- */
function pressed(ids, on) {
  ids.forEach((i) => $(i).setAttribute("aria-pressed", String(i === on)));
}
function setView(v) {
  view = v;
  pressed(["v-3d", "v-fl"], v === "3d" ? "v-3d" : "v-fl");
  $("flow").toggleAttribute("hidden", v !== "fl");
  $("g").style.visibility = v === "3d" ? "visible" : "hidden";
  if (v === "fl") drawFlow();
}
$("v-3d").onclick = () => setView("3d");
$("v-fl").onclick = () => setView("fl");
function setPeriod(p) {
  period = p;
  pressed(["p-20", "p-ch"], p === "y20" ? "p-20" : "p-ch");
  if (sel && sel.type === "e" && val(sel.e) == null) sel = null;
  reloadLinks();
  if (sel && sel.type === "n") recompute();
  syncUI();
  render();
}
$("p-20").onclick = () => setPeriod("y20");
$("p-ch").onclick = () => setPeriod("chg");
$("topn").oninput = (e) => {
  topN = +(/** @type {HTMLInputElement} */ (e.target).value);
  $("topnv").textContent = String(topN);
  recompute();
  syncUI();
  refresh();
};
$("b-flow").onchange = (e) => {
  flowOn = /** @type {HTMLInputElement} */ (e.target).checked;
  refresh();
};
$("b-rot").onchange = (e) => {
  if (Graph) Graph.controls().autoRotate = /** @type {HTMLInputElement} */ (e.target).checked;
};
$("b-clear").onclick = () => select(null);
$("b-reset").onclick = () => {
  select(null);
  fit3d(800);
  $("opt").open = false;
};
$("pick").onchange = (e) => {
  const v = /** @type {HTMLSelectElement} */ (e.target).value;
  select(v ? { type: "n", id: v } : null);
};
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && sel && !$("opt").open) select(null);
});
/* ---- 初期化 ---- */
readTokens();
$("pick").innerHTML =
  '<option value="">全体を見る(未選択)</option>' +
  D.groups
    .map(
      (g, i) =>
        `<optgroup label="${g}">${D.nodes
          .filter((n) => n.grp === i)
          .sort((a, b) => b.out - a.out)
          .map((n) => `<option value="${n.id}">${n.name}</option>`)
          .join("")}</optgroup>`
    )
    .join("");
if (REDUCED) {
  $("b-flow").checked = false;
  $("b-flow").disabled = true;
  $("b-rot").disabled = true;
  $("rm-note").hidden = false;
}
if (isMobile()) $("lgd").open = false;
{
  const q = new URLSearchParams(location.search).get("sel");
  if (q && D.nodes.some((n) => n.id === q)) {
    sel = { type: "n", id: q };
    $("pick").value = q;
  }
} // ?sel=66 で産業を選んだ状態で開く
setView(view);
recompute();
syncUI();
render();
initGraph();
new MutationObserver(() => {
  readTokens();
  if (Graph) Graph.backgroundColor(T.graph);
  syncUI();
  render();
  refresh();
}).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
