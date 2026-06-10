/* ===========================================================================
 * flow-core — freeform flowchart / node-link diagram (engine family).
 * Nodes are rich CARDS that can hold text / value / key-value / list / image /
 * table / a REAL interactive graph (re-mounted in-document via graph_payloads —
 * no new chart code). Edges are SVG arrows with labels. Layout is explicit
 * (x,y per node = irregular/비정형) OR auto-layered (Sugiyama-lite) when omitted.
 * Auto interactions: pan (drag bg) / wheel-zoom / fit / node modal (full graph,
 * image lightbox, big table) / theme / export-source.
 * Dispatched via window.GraphEngines["flow-core"].
 * =========================================================================== */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function svg(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
    return e;
  }
  function fmtNum(v) {
    if (v == null || v === "" || (typeof v === "number" && !isFinite(v))) return "—";
    return typeof v === "number" ? String(Math.round(v * 1e4) / 1e4) : String(v);
  }

  function mountGraph(div, gp, override) {
    var fac = window.GraphEngines && window.GraphEngines[gp.engine];
    if (typeof fac !== "function") {
      div.innerHTML = '<div class="gs-error">내장 그래프 엔진 없음: ' + (gp.engine || "?") + "</div>";
      return null;
    }
    var core = fac(div, Object.assign({}, gp.options || {}, override || {}));
    var fam = (window.GraphPlugins && window.GraphPlugins[gp.engine]) || {};
    (gp.plugins || []).forEach(function (id) { if (fam[id] && core.use) core.use(fam[id]); });
    if (core.setAssets) core.setAssets(gp.assets || {});
    else if (core.setData) core.setData((gp.assets || {}).series || []);
    if (core.autoFit) core.autoFit();
    return core;
  }

  // ---- node content (text/value/kv/list/image/table/graph) ------------------
  function tableEl(t) {
    var cols = t.columns, rows = t.rows || [];
    var tbl = el("table", "gs-fl-tbl"), thead = el("thead"), htr = el("tr");
    var keys;
    if (cols && cols.length) {                 // [{key,label}] + rows[{key:val}]
      keys = cols.map(function (c) { return c.key != null ? c.key : c; });
      cols.forEach(function (c) { htr.appendChild(el("th", null, c.label != null ? c.label : c)); });
    } else if (t.headers) {                     // headers[] + rows[[...]]
      keys = null;
      t.headers.forEach(function (h) { htr.appendChild(el("th", null, String(h))); });
    } else { keys = Object.keys(rows[0] || {}); keys.forEach(function (k) { htr.appendChild(el("th", null, k)); }); }
    thead.appendChild(htr); tbl.appendChild(thead);
    var tb = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr");
      if (keys) keys.forEach(function (k) { tr.appendChild(el("td", null, fmtNum(r[k]))); });
      else (r || []).forEach(function (v) { tr.appendChild(el("td", null, fmtNum(v))); });
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
    return tbl;
  }

  function FlowCore(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-flow");
    this.opts = options || {};
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this.dir = this.opts.direction === "LR" ? "LR" : "TB";
    this.nodeW = this.opts.node_w || 210;
    this.scale = 1; this.tx = 0; this.ty = 0;
    this._buildToolbar();
    this.stage = el("div", "gs-fl-stage");
    this.vp = el("div", "gs-fl-vp");
    this.svg = svg("svg", { "class": "gs-fl-edges" });
    var defs = svg("defs");
    ["", "-sel"].forEach(function (sfx) {
      var m = svg("marker", { id: "gs-arrow" + sfx, viewBox: "0 0 10 10", refX: "9", refY: "5",
        markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
      m.appendChild(svg("path", { d: "M0,0 L10,5 L0,10 z", "class": "gs-fl-arrowhead" + sfx }));
      defs.appendChild(m);
    });
    this.svg.appendChild(defs);
    this.nodeLayer = el("div", "gs-fl-nodes");
    this.vp.appendChild(this.svg); this.vp.appendChild(this.nodeLayer);
    this.stage.appendChild(this.vp); this.root.appendChild(this.stage);
    this._buildModal();
    this._bindPanZoom();
    var self = this;
    if (typeof ResizeObserver === "function") {
      this._ro = new ResizeObserver(function () { self._fit(); });
      this._ro.observe(this.stage);
    }
  }
  FlowCore.prototype.use = function () { return this; };
  FlowCore.prototype.autoFit = function () { this._fit(); };

  FlowCore.prototype.setAssets = function (a) {
    this.a = a || {};
    this.kind = this.a.kind || "flowchart";
    if (this._sim) { this._sim.dead = true; this._sim = null; }       // stop any prior force loop
    if (this.kind === "sankey") return this._renderSankey();
    if (this.kind === "network") return this._renderNetwork();
    if (this.kind === "chord") return this._renderChord();
    if (this.kind === "sunburst") return this._renderSunburst();
    this.dir = this.a.direction === "LR" ? "LR" : (this.a.direction === "TB" ? "TB" : this.dir);
    this.nodes = (this.a.nodes || []).filter(function (n) { return n && n.id != null; });
    this.edges = (this.a.edges || []).filter(function (e) { return e && e.from != null && e.to != null; });
    this.gp = this.a.graph_payloads || {};
    this._byId = {};
    this.nodes.forEach(function (n) { this._byId[n.id] = n; }, this);
    this._render();
  };

  // ---- shared reset for non-flowchart (data-viz) modes ---------------------
  FlowCore.prototype._resetStage = function (w, h) {
    this.nodeLayer.innerHTML = "";
    Array.prototype.slice.call(this.svg.querySelectorAll(":scope > *:not(defs)")).forEach(function (n) { n.remove(); });
    this._world = { x: 0, y: 0, w: w, h: h };
    this.vp.style.width = w + "px"; this.vp.style.height = h + "px";
    this.svg.setAttribute("width", w); this.svg.setAttribute("height", h);
  };
  FlowCore.prototype._rankNodes = function (nodes, links, byId) {
    var rank = {}, i;
    nodes.forEach(function (n) { rank[n.id] = 0; });
    for (i = 0; i < nodes.length + 1; i++) {
      var ch = false;
      links.forEach(function (l) {
        if (rank[l.source] == null || rank[l.target] == null) return;
        if (rank[l.target] < rank[l.source] + 1) { rank[l.target] = rank[l.source] + 1; ch = true; }
      });
      if (!ch) break;
    }
    return rank;
  };
  var FPAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#999999",
    "#8c564b", "#17becf", "#bcbd22", "#7f7f7f"];

  // ---- SANKEY ---------------------------------------------------------------
  FlowCore.prototype._renderSankey = function () {
    var self = this, nodes = this.a.nodes || [], links = this.a.links || [];
    if (!links.length || !links.some(function (l) { return l && l.value > 0; })) {
      this._resetStage(400, 200);
      this.nodeLayer.innerHTML = '<div class="gs-error">유효한 흐름 데이터 없음 (links[].value > 0 필요)</div>';
      this._fit(); return;
    }
    var byId = {}; nodes.forEach(function (n, i) { n._i = i; byId[n.id] = n; });
    var rank = this._rankNodes(nodes, links, byId);
    var maxR = 0; nodes.forEach(function (n) { maxR = Math.max(maxR, rank[n.id]); });
    var W = Math.max(560, (maxR + 1) * 220), nodeW = 18, vgap = 14, pad = 30;
    // node throughput
    var inSum = {}, outSum = {};
    links.forEach(function (l) { outSum[l.source] = (outSum[l.source] || 0) + l.value; inSum[l.target] = (inSum[l.target] || 0) + l.value; });
    nodes = nodes.filter(function (n) { return (inSum[n.id] || 0) + (outSum[n.id] || 0) > 0; });  // drop flow-less nodes
    nodes.forEach(function (n) { n._val = Math.max(inSum[n.id] || 0, outSum[n.id] || 0, 1e-9); });
    // bucket by rank, scale heights to fit
    var buckets = {}; nodes.forEach(function (n) { (buckets[rank[n.id]] = buckets[rank[n.id]] || []).push(n); });
    var maxLayerVal = 0;
    Object.keys(buckets).forEach(function (r) { var s = 0; buckets[r].forEach(function (n) { s += n._val; }); maxLayerVal = Math.max(maxLayerVal, s); });
    var avail = 460, k = avail / maxLayerVal;
    var H = avail + 2 * pad;
    this._resetStage(W, H);
    var colX = function (r) { return pad + r * ((W - 2 * pad - nodeW) / Math.max(1, maxR)); };
    Object.keys(buckets).forEach(function (r) {
      var y = pad, layer = buckets[r];
      layer.forEach(function (n) { n._h = Math.max(2, n._val * k); n._x = colX(+r); n._y = y; n._outO = y; n._inO = y; y += n._h + vgap; });
    });
    // ribbons (under nodes)
    links.forEach(function (l, li) {
      var s = byId[l.source], t = byId[l.target]; if (!s || !t) return;
      var w = Math.max(1, l.value * k);
      var x0 = s._x + nodeW, x1 = t._x, sy = s._outO, ty = t._inO;
      s._outO += w; t._inO += w;
      var xm = (x0 + x1) / 2;
      var d = "M" + x0 + "," + sy + " C" + xm + "," + sy + " " + xm + "," + ty + " " + x1 + "," + ty +
        " L" + x1 + "," + (ty + w) + " C" + xm + "," + (ty + w) + " " + xm + "," + (sy + w) + " " + x0 + "," + (sy + w) + " Z";
      var col = l.color || (s.color || FPAL[s._i % FPAL.length]);
      var path = svg("path", { d: d, "class": "gs-fl-ribbon" });
      path.style.fill = col; path.style.fillOpacity = "0.4";
      var title = svg("title"); title.textContent = (s.label || s.id) + " → " + (t.label || t.id) + " : " + l.value;
      path.appendChild(title);
      path.addEventListener("mouseenter", function () { path.style.fillOpacity = "0.7"; });
      path.addEventListener("mouseleave", function () { path.style.fillOpacity = "0.4"; });
      self.svg.appendChild(path);
    });
    // node rects + labels
    nodes.forEach(function (n) {
      var col = n.color || FPAL[n._i % FPAL.length];
      var rect = svg("rect", { x: n._x, y: n._y, width: nodeW, height: n._h, rx: 2, "class": "gs-fl-snode" });
      rect.style.fill = col;
      self.svg.appendChild(rect);
      var atEnd = (rank[n.id] === maxR);
      var tx = svg("text", { x: atEnd ? n._x - 6 : n._x + nodeW + 6, y: n._y + n._h / 2 + 4,
        "class": "gs-fl-slabel", "text-anchor": atEnd ? "end" : "start" });
      tx.textContent = (n.label || n.id) + " (" + (Math.round(n._val * 10) / 10) + ")";
      self.svg.appendChild(tx);
    });
    this._fit();
  };

  // ---- NETWORK (force-directed, draggable) ---------------------------------
  FlowCore.prototype._renderNetwork = function () {
    var self = this, nodes = (this.a.nodes || []).map(function (n) { return { id: n.id, label: n.label || n.id, group: n.group, value: n.value, color: n.color }; });
    var links = (this.a.links || []).filter(function (l) { return l.source != null && l.target != null; });
    var byId = {}; nodes.forEach(function (n, i) { n._i = i; byId[n.id] = n; });
    var W = 640, H = 480; this._resetStage(W, H);
    var cx = W / 2, cy = H / 2, R0 = Math.min(W, H) * 0.34;
    nodes.forEach(function (n, i) {
      var a = i / Math.max(1, nodes.length) * 6.2832;
      n.x = cx + R0 * Math.cos(a); n.y = cy + R0 * Math.sin(a); n.vx = 0; n.vy = 0;
      n.deg = 0;
    });
    links.forEach(function (l) { if (byId[l.source]) byId[l.source].deg++; if (byId[l.target]) byId[l.target].deg++; });
    var groups = {}; nodes.forEach(function (n) { if (n.group != null && groups[n.group] == null) groups[n.group] = Object.keys(groups).length; });
    // svg elements
    var lineEls = links.map(function (l) {
      var e = svg("line", { "class": "gs-fl-nedge" });
      if (l.value) e.style.strokeWidth = Math.max(1, Math.min(6, l.value)) + "";
      self.svg.appendChild(e); return e;
    });
    if (nodes.length > 40 && this.svg.classList) this.svg.classList.add("gs-fl-dense");  // labels -> tooltips
    var nodeG = [];
    nodes.forEach(function (n) {
      var r = 6 + (n.value ? Math.min(16, Math.sqrt(n.value) * 2) : Math.min(10, n.deg * 1.4));
      n._r = r;
      var c = svg("circle", { r: r, "class": "gs-fl-nnode" });
      c.style.fill = n.color || FPAL[(groups[n.group] != null ? groups[n.group] : n._i) % FPAL.length];
      var ct = svg("title"); ct.textContent = n.label + (n.value != null ? " · " + n.value : "") + (n.group ? " (" + n.group + ")" : "");
      c.appendChild(ct);
      var tx = svg("text", { "class": "gs-fl-nlabel", "text-anchor": "middle" }); tx.textContent = n.label;
      self.svg.appendChild(c); self.svg.appendChild(tx);
      nodeG.push({ c: c, tx: tx, n: n });
      // drag a node (pins while held) — pointer events so touch works too
      c.addEventListener("pointerdown", function (ev) {
        ev.stopPropagation(); ev.preventDefault(); n._fixed = true; self._dragN = n;
        var move = function (e2) {
          var rect = self.stage.getBoundingClientRect();
          n.x = (e2.clientX - rect.left - self.tx) / self.scale; n.y = (e2.clientY - rect.top - self.ty) / self.scale;
          self._reheat();
        };
        var up = function () {
          window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up);
          n._fixed = false; self._dragN = null;
        };
        window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
      });
    });
    function paint() {
      links.forEach(function (l, i) {
        var s = byId[l.source], t = byId[l.target]; if (!s || !t) return;
        lineEls[i].setAttribute("x1", s.x); lineEls[i].setAttribute("y1", s.y);
        lineEls[i].setAttribute("x2", t.x); lineEls[i].setAttribute("y2", t.y);
      });
      nodeG.forEach(function (g) {
        g.c.setAttribute("cx", g.n.x); g.c.setAttribute("cy", g.n.y);
        g.tx.setAttribute("x", g.n.x); g.tx.setAttribute("y", g.n.y - g.n._r - 3);
      });
    }
    // force simulation — settles (stops the rAF loop) once alpha decays; drags reheat it
    var sim = this._sim = { alpha: 1, dead: false, running: false };
    var raf = window.requestAnimationFrame || function (f) { return setTimeout(function () { f(16); }, 16); };
    var L = 70, kRep = 2600, kSpr = 0.04, grav = 0.02;
    var reduced = false;
    try { reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
    this._reheat = function () {
      if (!self._sim || self._sim.dead) return;
      self._sim.alpha = 0.6;
      if (!self._sim.running) { self._sim.running = true; raf(step); }
    };
    function tick() {                                 // one physics iteration (no scheduling)
      var i, j;
      for (i = 0; i < nodes.length; i++) { nodes[i]._fx = 0; nodes[i]._fy = 0; }
      for (i = 0; i < nodes.length; i++) for (j = i + 1; j < nodes.length; j++) {
        var a = nodes[i], b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy + 0.01, d = Math.sqrt(d2);
        var f = kRep / d2, ux = dx / d, uy = dy / d;
        a._fx += f * ux; a._fy += f * uy; b._fx -= f * ux; b._fy -= f * uy;
      }
      links.forEach(function (l) {
        var a = byId[l.source], b = byId[l.target]; if (!a || !b) return;
        var dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) + 0.01, f = kSpr * (d - L);
        var ux = dx / d, uy = dy / d;
        a._fx += f * ux; a._fy += f * uy; b._fx -= f * ux; b._fy -= f * uy;
      });
      for (i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n._fx += (cx - n.x) * grav; n._fy += (cy - n.y) * grav;
        if (n._fixed) { n.vx = 0; n.vy = 0; continue; }
        n.vx = (n.vx + n._fx * sim.alpha) * 0.82; n.vy = (n.vy + n._fy * sim.alpha) * 0.82;
        n.x += n.vx * 0.1; n.y += n.vy * 0.1;
        n.x = Math.max(n._r, Math.min(W - n._r, n.x)); n.y = Math.max(n._r, Math.min(H - n._r, n.y));
      }
      sim.alpha *= 0.985;
    }
    function step() {
      if (sim.dead) { sim.running = false; return; }
      tick();
      paint();
      if (sim.alpha > 0.005) raf(step);
      else sim.running = false;                       // settled — no idle rAF/CPU burn
    }
    if (reduced) {                                    // prefers-reduced-motion: settle instantly
      for (var it = 0; it < 600 && sim.alpha > 0.005; it++) tick();
      paint(); sim.running = false;
    } else {
      sim.running = true; paint(); raf(step);
    }
    var od = this.destroy; this.destroy = function () { if (self._sim) self._sim.dead = true; if (od) od.call(self); };
    this._fit();
  };

  // ---- CHORD ----------------------------------------------------------------
  FlowCore.prototype._renderChord = function () {
    var self = this, labels = this.a.labels || [], M = this.a.matrix || [];
    var n = labels.length || M.length; if (!n) { this._resetStage(400, 300); return; }
    var size = 480, cx = size / 2, cy = size / 2, R = size * 0.40, thick = 16;
    this._resetStage(size, size);
    var rowTot = M.map(function (row) { return row.reduce(function (a, b) { return a + b; }, 0); });
    var colTot = []; for (var j = 0; j < n; j++) { var s = 0; for (var i = 0; i < n; i++) s += (M[i] && M[i][j]) || 0; colTot[j] = s; }
    var gsize = rowTot.map(function (rt, i) { return rt + colTot[i]; });
    var total = gsize.reduce(function (a, b) { return a + b; }, 0) || 1;
    var gapA = 0.04, ang = -Math.PI / 2, groups = [];
    for (var g = 0; g < n; g++) {
      var span = (gsize[g] / total) * (6.2832 - n * gapA);
      groups.push({ a0: ang, a1: ang + span, label: labels[g] || ("G" + g), color: FPAL[g % FPAL.length] });
      ang += span + gapA;
    }
    function pol(a, r) { return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }
    function arcPath(a0, a1, r) {
      var p0 = pol(a0, r), p1 = pol(a1, r), large = (a1 - a0) > Math.PI ? 1 : 0;
      return "M" + p0[0] + "," + p0[1] + " A" + r + "," + r + " 0 " + large + " 1 " + p1[0] + "," + p1[1];
    }
    // group arcs
    groups.forEach(function (gr, gi) {
      var band = svg("path", { d: arcPath(gr.a0, gr.a1, R) + " L" + pol(gr.a1, R - thick).join(",") +
        " A" + (R - thick) + "," + (R - thick) + " 0 " + ((gr.a1 - gr.a0) > Math.PI ? 1 : 0) + " 0 " + pol(gr.a0, R - thick).join(",") + " Z",
        "class": "gs-fl-carc" });
      band.style.fill = gr.color;
      self.svg.appendChild(band);
      var mid = (gr.a0 + gr.a1) / 2, lp = pol(mid, R + 12);
      var tx = svg("text", { x: lp[0], y: lp[1] + 4, "class": "gs-fl-clabel",
        "text-anchor": Math.cos(mid) < -0.05 ? "end" : (Math.cos(mid) > 0.05 ? "start" : "middle") });
      tx.textContent = gr.label; self.svg.appendChild(tx);
    });
    // ribbons: sub-arc offsets per group (outgoing then incoming)
    var outOff = groups.map(function (gr, i) { return gr.a0; });
    var inOff = groups.map(function (gr, i) { return gr.a0 + (rowTot[i] / total) * 0; });
    // place outgoing first, then incoming, within each group's span
    var spanPer = groups.map(function (gr, i) { return (gr.a1 - gr.a0) / Math.max(1e-9, gsize[i]); });
    var cur = groups.map(function (gr) { return gr.a0; });
    var ribs = [];
    for (var i2 = 0; i2 < n; i2++) for (var j2 = 0; j2 < n; j2++) {
      var v = (M[i2] && M[i2][j2]) || 0; if (v <= 0) continue;
      ribs.push({ i: i2, j: j2, v: v });
    }
    // assign source-side arcs (i outgoing) and target-side arcs (j incoming) sequentially
    var srcA = {}, tgtA = {};
    for (var i3 = 0; i3 < n; i3++) {
      for (var j3 = 0; j3 < n; j3++) {
        var v3 = (M[i3] && M[i3][j3]) || 0; if (v3 <= 0) continue;
        var a0 = cur[i3], a1 = a0 + v3 * spanPer[i3]; cur[i3] = a1; srcA[i3 + "_" + j3] = [a0, a1];
      }
    }
    for (var j4 = 0; j4 < n; j4++) {
      for (var i4 = 0; i4 < n; i4++) {
        var v4 = (M[i4] && M[i4][j4]) || 0; if (v4 <= 0) continue;
        var b0 = cur[j4], b1 = b0 + v4 * spanPer[j4]; cur[j4] = b1; tgtA[i4 + "_" + j4] = [b0, b1];
      }
    }
    var Ri = R - thick;
    ribs.forEach(function (rb) {
      var sa = srcA[rb.i + "_" + rb.j], ta = tgtA[rb.i + "_" + rb.j]; if (!sa || !ta) return;
      var s0 = pol(sa[0], Ri), s1 = pol(sa[1], Ri), t0 = pol(ta[0], Ri), t1 = pol(ta[1], Ri);
      var d = "M" + s0[0] + "," + s0[1] +
        " A" + Ri + "," + Ri + " 0 0 1 " + s1[0] + "," + s1[1] +
        " Q" + cx + "," + cy + " " + t0[0] + "," + t0[1] +
        " A" + Ri + "," + Ri + " 0 0 1 " + t1[0] + "," + t1[1] +
        " Q" + cx + "," + cy + " " + s0[0] + "," + s0[1] + " Z";
      var path = svg("path", { d: d, "class": "gs-fl-crib" });
      path.style.fill = groups[rb.i].color; path.style.fillOpacity = "0.42";
      var title = svg("title"); title.textContent = groups[rb.i].label + " → " + groups[rb.j].label + " : " + rb.v;
      path.appendChild(title);
      path.addEventListener("mouseenter", function () { path.style.fillOpacity = "0.72"; });
      path.addEventListener("mouseleave", function () { path.style.fillOpacity = "0.42"; });
      self.svg.appendChild(path);
    });
    this._fit();
  };

  FlowCore.prototype._render = function () {
    var self = this;
    this.nodeLayer.innerHTML = "";
    Array.prototype.slice.call(this.svg.querySelectorAll(".gs-fl-edge,.gs-fl-elabel")).forEach(function (n) { n.remove(); });
    this._mounts = [];
    this._cards = {};

    // 1) build + measure cards
    this.nodes.forEach(function (n) {
      var card = self._card(n);
      self.nodeLayer.appendChild(card);
      self._cards[n.id] = card;
      n._w = n.w || self.nodeW;
      card.style.width = n._w + "px";
    });
    // measure heights now in DOM
    this.nodes.forEach(function (n) { n._h = n.h || self._cards[n.id].offsetHeight || 64; });

    // 2) layout (explicit x/y kept; rest auto-layered)
    this._layout();

    // 3) position
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    this.nodes.forEach(function (n) {
      var c = self._cards[n.id];
      c.style.left = n._x + "px"; c.style.top = n._y + "px";
      minX = Math.min(minX, n._x); minY = Math.min(minY, n._y);
      maxX = Math.max(maxX, n._x + n._w); maxY = Math.max(maxY, n._y + n._h);
    });
    if (!isFinite(minX)) { minX = minY = 0; maxX = maxY = 100; }
    var pad = 40;
    this._world = { x: minX - pad, y: minY - pad, w: (maxX - minX) + 2 * pad, h: (maxY - minY) + 2 * pad };
    this.vp.style.width = this._world.w + "px";
    this.vp.style.height = this._world.h + "px";
    // shift everything so world origin is 0,0 inside vp
    this.nodes.forEach(function (n) {
      var c = self._cards[n.id];
      c.style.left = (n._x - self._world.x) + "px";
      c.style.top = (n._y - self._world.y) + "px";
    });
    this.svg.setAttribute("width", this._world.w);
    this.svg.setAttribute("height", this._world.h);

    // 4) edges
    this.edges.forEach(function (e) { self._edge(e); });

    // 5) mount graph cells
    this._mounts.forEach(function (m) {
      try { mountGraph(m.div, m.gp); }
      catch (err) {
        m.div.innerHTML = '<div class="gs-error">내장 그래프 렌더 실패</div>';
        if (window.console && console.error) console.error("[flow-core] cell mount failed", err);
      }
    });
    this._buildSearch();
    this._fit();
    if (!this._hinted) {                       // one-time discoverability toast
      this._hinted = true;
      var hs = this;
      setTimeout(function () { hs._zoomHint(); }, 500);
    }
  };

  FlowCore.prototype._buildSearch = function () {
    var self = this;
    if (this._search || (this.nodes || []).length <= 30) return;
    var inp = document.createElement("input");
    inp.className = "gs-fl-search"; inp.type = "search"; inp.placeholder = "노드 검색…";
    inp.setAttribute("aria-label", "노드 검색");
    inp.addEventListener("input", function () {
      var q = inp.value.toLowerCase();
      var hit = null;
      (self.nodes || []).forEach(function (n) {
        var card = self._cards[n.id], match = q && String(n.label || n.id).toLowerCase().indexOf(q) >= 0;
        if (card) card.classList.toggle("gs-fl-found", !!match);
        if (match && !hit) hit = n;
      });
      if (hit) {                                // pan the first match to center
        var sw = self.stage.clientWidth || 600, sh = self.stage.clientHeight || 400;
        self.tx = sw / 2 - (hit._x - self._world.x + hit._w / 2) * self.scale;
        self.ty = sh / 2 - (hit._y - self._world.y + hit._h / 2) * self.scale;
        self._apply();
      }
    });
    var bar = this.root.querySelector(".gs-fl-toolbar");
    if (bar) bar.insertBefore(inp, bar.firstChild);
    this._search = inp;
  };

  FlowCore.prototype._card = function (n) {
    var self = this;
    var type = n.type || "process";
    var card = el("div", "gs-fl-node gs-fl-" + type);
    if (n.accent || n.color) card.style.setProperty("--gs-fl-accent", n.accent || n.color);
    var head = el("div", "gs-fl-head");
    if (type === "decision") head.appendChild(el("span", "gs-fl-glyph", "◇"));
    else if (type === "terminal") head.appendChild(el("span", "gs-fl-glyph", "▷"));
    else if (type === "io" || type === "data") head.appendChild(el("span", "gs-fl-glyph", "▱"));
    head.appendChild(document.createTextNode(n.label != null ? n.label : n.id));
    card.appendChild(head);

    var c = n.content;
    if (c && c.kind) {
      var body = el("div", "gs-fl-body");
      var openable = null;
      if (c.kind === "text") body.appendChild(el("p", "gs-fl-text", c.text != null ? c.text : ""));
      else if (c.kind === "value") {
        body.appendChild(el("span", "gs-fl-bignum", fmtNum(c.value) + (c.unit ? " " + c.unit : "")));
        if (c.sub) body.appendChild(el("div", "gs-fl-sub", c.sub));
      } else if (c.kind === "kv") {
        var dl = el("div", "gs-fl-kv"), items = c.items || {};
        Object.keys(items).forEach(function (k) {
          dl.appendChild(el("span", "gs-fl-k", k));
          dl.appendChild(el("span", "gs-fl-v", fmtNum(items[k])));
        });
        body.appendChild(dl);
      } else if (c.kind === "list") {
        var ul = el("ul", "gs-fl-list");
        (c.items || []).forEach(function (t) { ul.appendChild(el("li", null, String(t))); });
        body.appendChild(ul);
      } else if (c.kind === "image" && c.image) {
        var img = document.createElement("img");
        img.className = "gs-fl-img";
        img.src = c.image.mode === "inline" ? ("data:" + (c.image.mime || "image/png") + ";base64," + c.image.data) : (c.image.ref || "");
        img.alt = n.label || "";
        body.appendChild(img);
        openable = function () { self._openImage(img.src, n.label); };
      } else if (c.kind === "table" && c.table) {
        var t = tableEl(c.table);
        body.appendChild(t);
        openable = function () { self._openTable(c.table, n.label); };
      } else if (c.kind === "graph" && this.gp[c.ref]) {
        var gdiv = el("div", "gs-fl-graph");
        body.appendChild(gdiv);
        this._mounts.push({ div: gdiv, gp: this.gp[c.ref] });
        openable = function () { self._openGraph(self.gp[c.ref], n.label); };
      }
      card.appendChild(body);
      if (openable) {
        card.classList.add("gs-fl-clickable");
        if (card.setAttribute) { card.setAttribute("tabindex", "0"); card.setAttribute("role", "button"); }
        card.addEventListener("click", function (ev) { if (!self._panned) openable(); ev.stopPropagation(); });
        card.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") { if (ev.preventDefault) ev.preventDefault(); openable(); }
        });
      }
    }
    return card;
  };

  // ---- layout: keep explicit x/y; auto-layer the rest --------------------
  FlowCore.prototype._layout = function () {
    var self = this, explicit = this.nodes.filter(function (n) { return n.x != null && n.y != null; });
    this.nodes.forEach(function (n) { if (n.x != null) n._x = n.x; if (n.y != null) n._y = n.y; });
    if (explicit.length === this.nodes.length) return;   // fully positioned (비정형)

    // longest-path ranking over edges (cycle-safe: cap iterations)
    var rank = {}, indeg = {};
    this.nodes.forEach(function (n) { rank[n.id] = 0; indeg[n.id] = 0; });
    this.edges.forEach(function (e) { if (indeg[e.to] != null) indeg[e.to]++; });
    var order = this.nodes.map(function (n) { return n.id; });
    for (var iter = 0; iter < this.nodes.length + 1; iter++) {
      var changed = false;
      this.edges.forEach(function (e) {
        if (rank[e.from] == null || rank[e.to] == null) return;
        if (rank[e.to] < rank[e.from] + 1) { rank[e.to] = rank[e.from] + 1; changed = true; }
      });
      if (!changed) break;
    }
    // bucket by rank, preserve declaration order within a rank
    var buckets = {};
    order.forEach(function (id) { (buckets[rank[id]] = buckets[rank[id]] || []).push(id); });
    var rankGap = this.opts.rank_gap || 60, nodeGap = this.opts.node_gap || 36;
    var ranks = Object.keys(buckets).map(Number).sort(function (a, b) { return a - b; });
    // width of widest rank to center others
    var lateral = {};
    ranks.forEach(function (r) {
      var ids = buckets[r], pos = 0;
      lateral[r] = ids.map(function (id) {
        var n = self._byId[id], span = self.dir === "TB" ? n._w : n._h;
        var p = pos; pos += span + nodeGap; return { id: id, p: p, span: span };
      });
      lateral[r]._total = pos - nodeGap;
    });
    var maxTotal = 0; ranks.forEach(function (r) { maxTotal = Math.max(maxTotal, lateral[r]._total); });
    var depthPos = 0, depthOf = {};
    ranks.forEach(function (r) {
      depthOf[r] = depthPos;
      var maxDepth = 0;
      buckets[r].forEach(function (id) { var n = self._byId[id]; maxDepth = Math.max(maxDepth, self.dir === "TB" ? n._h : n._w); });
      depthPos += maxDepth + rankGap;
    });
    ranks.forEach(function (r) {
      var off = (maxTotal - lateral[r]._total) / 2;
      lateral[r].forEach(function (item) {
        var n = self._byId[item.id];
        if (n.x != null && n.y != null) return;          // respect explicit
        if (self.dir === "TB") { n._x = (n.x != null ? n.x : off + item.p); n._y = (n.y != null ? n.y : depthOf[r]); }
        else { n._y = (n.y != null ? n.y : off + item.p); n._x = (n.x != null ? n.x : depthOf[r]); }
      });
    });
    this.nodes.forEach(function (n) { if (n._x == null) n._x = 0; if (n._y == null) n._y = 0; });
  };

  // ---- edges ----------------------------------------------------------------
  FlowCore.prototype._anchor = function (n, side) {
    var x = n._x - this._world.x, y = n._y - this._world.y;
    var cx = x + n._w / 2, cy = y + n._h / 2;
    if (side === "T") return [cx, y];
    if (side === "B") return [cx, y + n._h];
    if (side === "L") return [x, cy];
    if (side === "R") return [x + n._w, cy];
    return [cx, cy];
  };
  FlowCore.prototype._edge = function (e) {
    var a = this._byId[e.from], b = this._byId[e.to];
    if (!a || !b) return;
    var sSide, tSide;
    if (this.dir === "TB") { sSide = e.from_side || "B"; tSide = e.to_side || "T"; }
    else { sSide = e.from_side || "R"; tSide = e.to_side || "L"; }
    var s = this._anchor(a, sSide), t = this._anchor(b, tSide);
    var d;
    if (this.dir === "TB") {
      var my = (s[1] + t[1]) / 2;
      d = "M" + s[0] + "," + s[1] + " C" + s[0] + "," + my + " " + t[0] + "," + my + " " + t[0] + "," + t[1];
    } else {
      var mx = (s[0] + t[0]) / 2;
      d = "M" + s[0] + "," + s[1] + " C" + mx + "," + s[1] + " " + mx + "," + t[1] + " " + t[0] + "," + t[1];
    }
    var p = svg("path", { d: d, "class": "gs-fl-edge" + (e.kind === "dashed" ? " gs-fl-dashed" : ""),
      "marker-end": "url(#gs-arrow)" });
    if (e.color) p.style.stroke = e.color;
    this.svg.appendChild(p);
    if (e.label != null && e.label !== "") {
      var lx = (s[0] + t[0]) / 2, ly = (s[1] + t[1]) / 2;
      var bg = svg("rect", { "class": "gs-fl-elabel-bg", x: lx - 4, y: ly - 9, rx: 3, height: 16 });
      var tx = svg("text", { "class": "gs-fl-elabel", x: lx, y: ly + 3, "text-anchor": "middle" });
      tx.textContent = String(e.label);
      this.svg.appendChild(bg); this.svg.appendChild(tx);
      var w = (tx.getComputedTextLength ? tx.getComputedTextLength() : String(e.label).length * 7) + 8;
      bg.setAttribute("x", lx - w / 2); bg.setAttribute("width", w);
    }
  };

  // ---- pan / zoom / fit -----------------------------------------------------
  FlowCore.prototype._apply = function () {
    this.vp.style.transform = "translate(" + this.tx + "px," + this.ty + "px) scale(" + this.scale + ")";
    this.root.classList.toggle("gs-sem-small", this.scale < 0.55);   // semantic zoom: fade card bodies
  };
  FlowCore.prototype._fit = function () {
    if (!this._world) return;
    var sw = this.stage.clientWidth || 600, sh = this.stage.clientHeight || 400;
    var sc = Math.min(sw / this._world.w, sh / this._world.h);
    sc = Math.max(0.05, Math.min(sc, 1.4));
    this.scale = sc;
    this.tx = (sw - this._world.w * sc) / 2;
    this.ty = (sh - this._world.h * sc) / 2;
    this._apply();
  };
  FlowCore.prototype._zoomHint = function () {
    var self = this;
    if (!this._zh) {
      this._zh = el("div", "gs-fl-zoom-hint");
      var mac = typeof navigator !== "undefined" && navigator.platform && navigator.platform.indexOf("Mac") >= 0;
      this._zh.textContent = (mac ? "⌘" : "Ctrl") + " + 스크롤로 확대/축소 · 배경 드래그=이동";
      this.root.appendChild(this._zh);
    }
    this._zh.classList.add("gs-show");
    clearTimeout(this._zhT);
    this._zhT = setTimeout(function () { self._zh.classList.remove("gs-show"); }, 1400);
  };
  FlowCore.prototype._bindPanZoom = function () {
    // pointer events (mouse + touch + pen); plain wheel keeps scrolling the host page
    var self = this, dragging = false, sx = 0, sy = 0, otx = 0, oty = 0;
    this.stage.addEventListener("pointerdown", function (ev) {
      self._panned = false;                                   // always reset (fixes dead clicks after a pan)
      if (ev.target.closest && ev.target.closest(".gs-fl-clickable,.gs-fl-nnode,.gs-fl-btn")) return;
      dragging = true; sx = ev.clientX; sy = ev.clientY; otx = self.tx; oty = self.ty;
      if (self.stage.setPointerCapture) { try { self.stage.setPointerCapture(ev.pointerId); } catch (e) {} }
      self.stage.classList.add("gs-fl-grabbing");
    });
    this.stage.addEventListener("pointermove", function (ev) {
      if (!dragging) return;
      var dx = ev.clientX - sx, dy = ev.clientY - sy;
      if (Math.abs(dx) + Math.abs(dy) > 3) self._panned = true;
      self.tx = otx + dx; self.ty = oty + dy; self._apply();
    });
    this.stage.addEventListener("pointerup", function () { dragging = false; self.stage.classList.remove("gs-fl-grabbing"); });
    this.stage.addEventListener("pointercancel", function () { dragging = false; self.stage.classList.remove("gs-fl-grabbing"); });
    this.stage.addEventListener("dblclick", function (ev) {
      if (ev.target.closest && ev.target.closest(".gs-fl-clickable,.gs-fl-nnode,.gs-fl-btn")) return;
      self._fit();
    });
    this.stage.addEventListener("wheel", function (ev) {
      if (!(ev.ctrlKey || ev.metaKey)) { self._zoomHint(); return; }   // no embed scroll-trap
      ev.preventDefault();
      var rect = self.stage.getBoundingClientRect();
      var mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
      var k = ev.deltaY < 0 ? 1.1 : 1 / 1.1, ns = Math.max(0.05, Math.min(4, self.scale * k));
      var r = ns / self.scale;
      self.tx = mx - (mx - self.tx) * r; self.ty = my - (my - self.ty) * r; self.scale = ns; self._apply();
    }, { passive: false });
  };

  // ---- SUNBURST (radial hierarchy, click to drill down) --------------------
  FlowCore.prototype._renderSunburst = function () {
    var self = this, root = this.a.tree || { name: "root", children: [] };
    // annotate: value (sum of leaves), depth, parent, branch color
    function annotate(n, depth, parent, branchCol) {
      n._depth = depth; n._parent = parent;
      var kids = n.children || [];
      if (depth === 1) branchCol = n.color || FPAL[(parent._kidIdx = (parent._kidIdx || 0)) % FPAL.length], parent._kidIdx++;
      n._branch = n.color || branchCol || FPAL[0];
      if (!kids.length) { n._val = (n.value != null ? +n.value : 0) || 1; return n._val; }
      var s = 0; for (var i = 0; i < kids.length; i++) s += annotate(kids[i], depth + 1, n, branchCol);
      n._val = (n.value != null ? +n.value : s) || s || 1; return n._val;
    }
    annotate(root, 0, null, null);
    this._sbRoot = root; this._sbFocus = this._sbFocus && this._inTree(this._sbFocus, root) ? this._sbFocus : root;
    this._paintSunburst();
  };
  FlowCore.prototype._inTree = function (node, root) {
    if (node === root) return true;
    var k = root.children || []; for (var i = 0; i < k.length; i++) if (this._inTree(node, k[i])) return true;
    return false;
  };
  FlowCore.prototype._paintSunburst = function () {
    var self = this, focus = this._sbFocus, size = 480, cx = size / 2, cy = size / 2;
    this._resetStage(size, size);
    var maxDepthFromFocus = 0;
    (function dd(n, d) { maxDepthFromFocus = Math.max(maxDepthFromFocus, d); (n.children || []).forEach(function (c) { dd(c, d + 1); }); })(focus, 0);
    var rings = Math.max(1, maxDepthFromFocus), r0 = size * 0.12, ringW = (size * 0.40 - r0) / rings;
    function pol(a, r) { return [cx + r * Math.cos(a - Math.PI / 2), cy + r * Math.sin(a - Math.PI / 2)]; }
    function sector(a0, a1, ri, ro) {
      var p0 = pol(a0, ro), p1 = pol(a1, ro), p2 = pol(a1, ri), p3 = pol(a0, ri), large = (a1 - a0) > Math.PI ? 1 : 0;
      return "M" + p0[0] + "," + p0[1] + " A" + ro + "," + ro + " 0 " + large + " 1 " + p1[0] + "," + p1[1] +
        " L" + p2[0] + "," + p2[1] + " A" + ri + "," + ri + " 0 " + large + " 0 " + p3[0] + "," + p3[1] + " Z";
    }
    // layout descendants of focus across [0,2π]
    (function layout(n, a0, a1, depth) {
      n._a0 = a0; n._a1 = a1; n._ring = depth;
      var kids = n.children || [], tot = 0, i; for (i = 0; i < kids.length; i++) tot += kids[i]._val;
      var a = a0; for (i = 0; i < kids.length; i++) { var span = tot > 0 ? (kids[i]._val / tot) * (a1 - a0) : 0; layout(kids[i], a, a + span, depth + 1); a += span; }
    })(focus, 0, 6.2832, 0);
    // draw descendant arcs
    (function draw(n) {
      (n.children || []).forEach(function (c) {
        var ri = r0 + (c._ring - 1) * ringW, ro = ri + ringW;
        var path = svg("path", { d: sector(c._a0, c._a1, ri, ro), "class": "gs-fl-sbseg" });
        path.style.fill = c._branch; path.style.fillOpacity = String(Math.max(0.35, 0.95 - (c._ring - 1) * 0.16));
        var title = svg("title"); title.textContent = (c.name || "") + " : " + (Math.round(c._val * 100) / 100); path.appendChild(title);
        if (c.children && c.children.length) {
          path.style.cursor = "pointer";
          path.addEventListener("click", function (e) { e.stopPropagation(); self._sbFocus = c; self._paintSunburst(); });
        }
        path.addEventListener("mouseenter", function () { path.style.fillOpacity = "1"; });
        var fo = path.style.fillOpacity;
        path.addEventListener("mouseleave", function () { path.style.fillOpacity = String(Math.max(0.35, 0.95 - (c._ring - 1) * 0.16)); });
        // arc label if wide enough
        if (c._a1 - c._a0 > 0.16) {
          var mid = (c._a0 + c._a1) / 2, lp = pol(mid, (ri + ro) / 2);
          var tx = svg("text", { x: lp[0], y: lp[1] + 3, "class": "gs-fl-sblabel", "text-anchor": "middle" });
          tx.textContent = c.name || ""; tx.style.pointerEvents = "none"; self.svg.appendChild(path); self.svg.appendChild(tx);
        } else { self.svg.appendChild(path); }
        draw(c);
      });
    })(focus);
    // center disc (focus) — click to go up
    var disc = svg("circle", { cx: cx, cy: cy, r: r0 - 2, "class": "gs-fl-sbcenter" });
    if (focus._parent) { disc.style.cursor = "pointer"; disc.addEventListener("click", function () { self._sbFocus = focus._parent; self._paintSunburst(); }); }
    this.svg.appendChild(disc);
    var ct = svg("text", { x: cx, y: cy + 1, "class": "gs-fl-sbctext", "text-anchor": "middle" });
    ct.textContent = focus._parent ? "↑ " + (focus.name || "") : (focus.name || "전체");
    this.svg.appendChild(ct);
    this._fit();
  };

  // ---- toolbar + modal ------------------------------------------------------
  FlowCore.prototype._buildToolbar = function () {
    var self = this, bar = el("div", "gs-fl-toolbar");
    if (this.opts.title) this.root.appendChild(el("div", "gs-fl-title", this.opts.title));
    function btn(txt, title, fn) {
      var b = el("button", "gs-fl-btn", txt); b.title = title;
      b.setAttribute("aria-label", title);
      b.addEventListener("click", fn); bar.appendChild(b); return b;
    }
    btn("⤢", "fit", function () { self._fit(); });
    btn("＋", "zoom in", function () { self.scale = Math.min(4, self.scale * 1.2); self._apply(); });
    btn("－", "zoom out", function () { self.scale = Math.max(0.05, self.scale / 1.2); self._apply(); });
    btn("◐", "theme", function () {
      var order = ["auto", "light", "dark"], cur = self.root.getAttribute("data-theme") || "auto";
      self.root.setAttribute("data-theme", order[(order.indexOf(cur) + 1) % 3]);
    });
    btn("PNG", "PNG 내보내기 (SVG 모드)", function () { self._exportPNG(); });
    btn("{}", "source JSON", function () { self._exportSource(); });
    this.root.appendChild(bar);
  };
  FlowCore.prototype._buildModal = function () {
    var self = this, m = el("div", "gs-fl-modal"), box = el("div", "gs-fl-modal-box");
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
    var head = el("div", "gs-fl-modal-head");
    this._mTitle = el("span", null, "");
    var x = el("button", "gs-fl-x", "×");
    x.setAttribute("aria-label", "닫기 (Esc)"); x.title = "닫기 (Esc)";
    x.addEventListener("click", function () { self._closeModal(); });
    head.appendChild(this._mTitle); head.appendChild(x);
    this._mBody = el("div", "gs-fl-modal-body");
    box.appendChild(head); box.appendChild(this._mBody); m.appendChild(box);
    m.addEventListener("click", function (e) { if (e.target === m) self._closeModal(); });
    if (document.addEventListener) document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && m.classList.contains("open")) self._closeModal();
    });
    this.root.appendChild(m); this.modal = m; this._mX = x;
  };
  FlowCore.prototype._closeModal = function () {
    if (this._mGraph && this._mGraph.destroy) this._mGraph.destroy();
    this._mGraph = null; this._mBody.innerHTML = ""; this.modal.classList.remove("open");
  };
  FlowCore.prototype._openGraph = function (gp, title) {
    this._mTitle.textContent = title || ""; this._mBody.innerHTML = "";
    var div = el("div", "gs-fl-modal-graph"); this._mBody.appendChild(div); this.modal.classList.add("open"); if (this._mX && this._mX.focus) this._mX.focus();
    this._mGraph = mountGraph(div, gp, { legend: { show: true }, exportButtons: ["png", "csv"] });
  };
  FlowCore.prototype._openImage = function (src, title) {
    this._mTitle.textContent = title || ""; this._mBody.innerHTML = "";
    var img = document.createElement("img"); img.className = "gs-fl-modal-img"; img.src = src;
    this._mBody.appendChild(img); this.modal.classList.add("open"); if (this._mX && this._mX.focus) this._mX.focus();
  };
  FlowCore.prototype._openTable = function (t, title) {
    this._mTitle.textContent = title || ""; this._mBody.innerHTML = "";
    var w = el("div", "gs-fl-modal-tbl"); w.appendChild(tableEl(t)); this._mBody.appendChild(w); this.modal.classList.add("open"); if (this._mX && this._mX.focus) this._mX.focus();
  };
  FlowCore.prototype._exportPNG = function () {
    // SVG kinds (sankey/network/chord/sunburst) rasterize; the DOM flowchart kind cannot.
    if (this.kind === "flowchart" || !this.svg) { this._zoomHint(); return; }
    var self = this;
    var clone = this.svg.cloneNode(true);
    // inline computed styles so class-based fills/strokes survive standalone rasterization
    var src = this.svg.querySelectorAll("*"), dst = clone.querySelectorAll("*");
    for (var i = 0; i < src.length; i++) {
      var cs = getComputedStyle(src[i]);
      if (!cs) continue;
      var st = "fill:" + cs.fill + ";stroke:" + cs.stroke + ";stroke-width:" + cs.strokeWidth +
        ";fill-opacity:" + cs.fillOpacity + ";stroke-opacity:" + cs.strokeOpacity +
        ";font:" + cs.font + ";paint-order:" + cs.paintOrder + ";stroke-dasharray:" + cs.strokeDasharray;
      dst[i].setAttribute("style", st);
    }
    var w = +this.svg.getAttribute("width") || 800, h = +this.svg.getAttribute("height") || 600;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    var bgTok = getComputedStyle(this.root).getPropertyValue("--gs-bg").trim() || "#ffffff";
    var blob = new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" });
    var url = URL.createObjectURL(blob);
    var img = new Image();
    img.onload = function () {
      var cv = document.createElement("canvas");
      cv.width = w * 2; cv.height = h * 2;
      var ctx = cv.getContext("2d");
      ctx.fillStyle = bgTok; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      var a2 = document.createElement("a");
      a2.href = cv.toDataURL("image/png");
      a2.download = (self.opts.title || self.kind || "graph") + ".png";
      document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    };
    img.src = url;
  };
  FlowCore.prototype._exportSource = function () {
    var node = document.getElementById("graph-config");
    var txt = node ? node.textContent : JSON.stringify({ engine: "flow-core", assets: this.a, options: this.opts });
    var a = document.createElement("a");
    a.href = "data:application/json;charset=utf-8," + encodeURIComponent(txt);
    a.download = (this.opts.title || "flowchart") + ".json";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["flow-core"] = function (mount, options) { return new FlowCore(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["flow-core"] = window.GraphPlugins["flow-core"] || {};
})();
