/* ===========================================================================
 * xy-core — graph-skill's vanilla Canvas 2D engine (engine family "xy-core").
 *
 * Fixed, version-controlled asset. NOT regenerated per request. Provides the full
 * base-xy interaction set with zero config:
 *   multi-series · per-series hover tracking + crosshair + unified tooltip · HUD ·
 *   click-lock · wheel zoom (cursor-centered, axis-modifiers) · drag pan · box zoom ·
 *   double-click reset · log/linear toggle (x/y, with non-positive guard) ·
 *   nice ticks · legend toggle/isolate · dark mode (auto/light/dark) · responsive
 *   (ResizeObserver + devicePixelRatio) · PNG/CSV/config export.
 *
 * Plugins (future: region-shading, live-tangent, fft-view...) register via core.use()
 * and hook the lifecycle (onScale/onDrawUnder/onHover/onDrawOver/onClick/...).
 * =========================================================================== */
(function () {
  "use strict";

  var PALETTE = {
    "okabe-ito": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#777777", "#000000"]
  };
  var DASHES = [[6, 4], [2, 3], [8, 3, 2, 3], [1, 3]];

  var DEFAULTS = {
    axes: { x: { label: "", unit: "", log: false }, y: { label: "", unit: "", log: false } },
    curve: "monotone",
    grid: { major: true, minor: true, divisions: 10 },
    palette: "okabe-ito",
    theme: "auto",
    interactions: { hover: true, crosshair: true, zoom: true, pan: true, boxZoom: true },
    legend: { show: true, isolateOnDblClick: true },
    responsive: { aspectRatio: "16 / 9", widthPct: 100 },
    exportButtons: ["png", "csv", "config"],
    title: ""
  };

  // ----- small helpers -------------------------------------------------------
  function deepMerge(base, over) {
    var out = Array.isArray(base) ? base.slice() : {};
    for (var k in base) if (Object.prototype.hasOwnProperty.call(base, k)) out[k] = base[k];
    if (!over) return out;
    for (var j in over) {
      if (!Object.prototype.hasOwnProperty.call(over, j)) continue;
      var v = over[j];
      if (v && typeof v === "object" && !Array.isArray(v) && base[j] && typeof base[j] === "object") {
        out[j] = deepMerge(base[j], v);
      } else { out[j] = v; }
    }
    return out;
  }
  function el(cls) { var d = document.createElement("div"); if (cls) d.className = cls; return d; }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function lbl(ax) { return (ax.label || "") + (ax.unit ? " [" + ax.unit + "]" : ""); }
  function fmtVal(v) {
    if (v == null || !isFinite(v)) return "—";
    var a = Math.abs(v);
    if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(2);
    return String(Math.round(v * 1e4) / 1e4);
  }
  function niceNum(x, round) {
    if (!(x > 0)) return 1;
    var exp = Math.floor(Math.log10(x)), f = x / Math.pow(10, exp), nf;
    if (round) nf = f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10;
    else nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
    return nf * Math.pow(10, exp);
  }
  function fmtTick(v, step) {
    if (v === 0) return "0";
    var a = Math.abs(v);
    if (a >= 1e5 || a < 1e-3) return v.toExponential(1).replace("e+", "e").replace("e-0", "e-");
    var dec = Math.max(0, -Math.floor(Math.log10(step)));
    if (dec > 6) dec = 6;
    return v.toFixed(dec);
  }
  function linTicks(lo, hi, target) {
    if (!(hi > lo)) hi = lo + 1;
    var span = niceNum(hi - lo, false);
    var step = niceNum(span / Math.max(2, target), true);
    var start = Math.ceil(lo / step) * step;
    var out = [];
    for (var v = start; v <= hi + step * 1e-6; v += step) {
      out.push({ v: Math.abs(v) < step * 1e-9 ? 0 : v, label: fmtTick(v, step), major: true });
    }
    return { step: step, ticks: out };
  }
  function logLabel(e) {
    if (e === 0) return "1";
    if (e >= -3 && e <= 4) return String(Math.pow(10, e));
    return "10^" + e;
  }
  function logTicks(lo, hi) {
    lo = Math.max(lo, 1e-300);
    var e0 = Math.floor(Math.log10(lo)), e1 = Math.ceil(Math.log10(hi)), out = [];
    for (var e = e0; e <= e1; e++) {
      var base = Math.pow(10, e);
      if (base >= lo * 0.999 && base <= hi * 1.001) out.push({ v: base, label: logLabel(e), major: true });
      for (var m = 2; m <= 9; m++) {
        var vv = m * base;
        if (vv >= lo && vv <= hi) out.push({ v: vv, label: "", major: false });
      }
    }
    return { step: null, ticks: out };
  }
  function makeScale(d0, d1, p0, p1, log) {
    if (log) {
      var l0 = Math.log10(d0 <= 0 ? 1e-9 : d0), l1 = Math.log10(d1 <= 0 ? 1 : d1);
      if (l1 === l0) l1 = l0 + 1;
      return {
        to: function (v) { return p0 + (Math.log10(v) - l0) / (l1 - l0) * (p1 - p0); },
        inv: function (p) { return Math.pow(10, l0 + (p - p0) / (p1 - p0) * (l1 - l0)); }
      };
    }
    if (d1 === d0) d1 = d0 + 1;
    return {
      to: function (v) { return p0 + (v - d0) / (d1 - d0) * (p1 - p0); },
      inv: function (p) { return d0 + (p - p0) / (p1 - p0) * (d1 - d0); }
    };
  }

  // Largest-Triangle-Three-Buckets downsample (render-time only; preserves visual shape).
  function lttbIdx(xs, ys, threshold) {        // returns SELECTED INDICES (so callers can keep originals)
    var n = xs.length, out = [0];
    if (threshold >= n || threshold <= 2) { out = []; for (var q = 0; q < n; q++) out.push(q); return out; }
    var every = (n - 2) / (threshold - 2), a = 0, i, j, k;
    for (i = 0; i < threshold - 2; i++) {
      var rs = Math.floor((i + 1) * every) + 1, re = Math.min(Math.floor((i + 2) * every) + 1, n);
      var avgX = 0, avgY = 0, cnt = re - rs || 1;
      for (j = rs; j < re; j++) { avgX += xs[j]; avgY += ys[j]; }
      avgX /= cnt; avgY /= cnt;
      var ps = Math.floor(i * every) + 1, pe = Math.floor((i + 1) * every) + 1, maxA = -1, nextA = ps;
      for (k = ps; k < pe; k++) {
        var area = Math.abs((xs[a] - avgX) * (ys[k] - ys[a]) - (xs[a] - xs[k]) * (avgY - ys[a]));
        if (area > maxA) { maxA = area; nextA = k; }
      }
      out.push(nextA); a = nextA;
    }
    out.push(n - 1);
    return out;
  }
  function lttb(xs, ys, threshold) {
    var idx = lttbIdx(xs, ys, threshold), ox = [], oy = [];
    for (var i = 0; i < idx.length; i++) { ox.push(xs[idx[i]]); oy.push(ys[idx[i]]); }
    return { x: ox, y: oy };
  }
  function lowerBound(arr, v) { var lo = 0, hi = arr.length; while (lo < hi) { var m = (lo + hi) >> 1; if (arr[m] < v) lo = m + 1; else hi = m; } return lo; }

  // ===========================================================================
  function XYCore(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-root");
    this.opts = deepMerge(DEFAULTS, options || {});
    this.xLog = !!this.opts.axes.x.log;
    this.yLog = !!this.opts.axes.y.log;
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    if (this.opts.responsive && this.opts.responsive.aspectRatio) {
      this.root.style.aspectRatio = this.opts.responsive.aspectRatio;
    }
    this.canvas = document.createElement("canvas");
    this.root.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");

    this.series = [];
    this.visible = [];
    this.plugins = [];
    this._pstate = {};                       // per-core plugin state (plugins are shared singletons)
    if (!this.opts.pluginConfig) this.opts.pluginConfig = {};
    this.view = null;
    this.full = null;
    this.cursor = null;
    this.locked = false;
    this._drag = null;
    this._moved = false;
    this._lodMax = (this.opts.responsive && this.opts.responsive.lodMax) || 4000;  // render-time downsample cap
    this._hudHideXY = !!this.opts.hideAxes;  // non-cartesian: HUD shows only plugin rows
    this._ptrs = {};                         // active pointers (pinch zoom)
    this._pinch = null;

    this._buildDOM();
    this._bindEvents();
    var self = this;
    this._ro = new ResizeObserver(function () { self._resize(); });
    this._ro.observe(this.root);
    this._resize();
  }

  XYCore.prototype.use = function (p) { this.plugins.push(p); if (p.onInit) p.onInit(this); this.render(); return this; };
  XYCore.prototype.setAssets = function (assets) { this.setData((assets && assets.series) || []); };

  XYCore.prototype.setData = function (series) {
    var pal = PALETTE[this.opts.palette] || PALETTE["okabe-ito"];
    this.series = (series || []).map(function (s, i) {
      var x = s.x || [], y = s.y || [];
      if ((!x || !x.length) && s.data && s.data.length) {     // recipes may emit [[x,y]|{x,y}] pairs
        x = []; y = [];
        for (var d = 0; d < s.data.length; d++) {
          var pt = s.data[d];
          if (pt == null) { x.push(null); y.push(null); }
          else if (Object.prototype.toString.call(pt) === "[object Array]") { x.push(pt[0]); y.push(pt[1]); }
          else { x.push(pt.x); y.push(pt.y); }
        }
      }
      var mono = true;
      for (var k = 1; k < x.length; k++) { if (!(x[k] > x[k - 1])) { mono = false; break; } }
      return {
        name: s.name || ("series " + (i + 1)),
        x: x, y: y,
        style: s.style || "line",
        axis: s.axis === "right" ? "right" : "left",
        _color: s.color || pal[i % pal.length],
        _dash: s.dash || (i >= pal.length ? DASHES[(i - pal.length) % DASHES.length] : null),
        _mono: mono,
        // autoscale carriers etc.: hidden from legend/tooltip/hit-test, never toggled off
        _internal: (s.style === "none") || (typeof s.name === "string" && s.name.charAt(0) === "_")
      };
    });
    this.visible = this.series.map(function () { return true; });
    this._hasBar = this.series.some(function (s) { return (s.style || "") === "bar"; });
    this._hasRight = this.series.some(function (s) { return s.axis === "right"; });
    this._cats = (this.opts.axes.x && this.opts.axes.x.categories) || null;
    if (this._cats) this.xLog = false;
    this._computeFull();
    this.view = this._cloneDom(this.full);
    this._buildLegend();
    this.render();
  };

  XYCore.prototype.autoFit = function () {
    this._computeFull();
    this.view = this._cloneDom(this.full);
    this.locked = false; this.cursor = null;
    this.render();
  };

  XYCore.prototype._cloneDom = function (d) { var o = { x: d.x.slice(), y: d.y.slice() }; if (d.y2) o.y2 = d.y2.slice(); return o; };

  // equal-aspect (opt-in): expand the looser axis so px-per-unit matches on x and y, so a
  // unit circle reads round (Nyquist/root-locus). Idempotent: once equal it leaves view alone,
  // so applying every render is stable and keeps zoom/pan consistent.
  XYCore.prototype._equalize = function (plot) {
    var pxw = plot.right - plot.left, pxh = plot.bottom - plot.top;
    if (pxw <= 0 || pxh <= 0) return;
    var v = this.view, ux = v.x[1] - v.x[0], uy = v.y[1] - v.y[0];
    if (!(ux > 0) || !(uy > 0)) return;
    var ppx = pxw / ux, ppy = pxh / uy;
    if (Math.abs(ppx - ppy) <= 1e-6 * Math.max(ppx, ppy)) return;
    if (ppx > ppy) { var nux = pxw / ppy, cx = (v.x[0] + v.x[1]) / 2; v.x = [cx - nux / 2, cx + nux / 2]; }
    else { var nuy = pxh / ppx, cy = (v.y[0] + v.y[1]) / 2; v.y = [cy - nuy / 2, cy + nuy / 2]; }
  };

  XYCore.prototype._computeFull = function () {
    var xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity, any = false;
    var y2min = Infinity, y2max = -Infinity, any2 = false;
    for (var i = 0; i < this.series.length; i++) {
      if (!this.visible[i]) continue;
      var s = this.series[i], right = this._hasRight && s.axis === "right";
      for (var k = 0; k < s.x.length; k++) {
        var xv = s.x[k], yv = s.y[k];
        if (yv == null || !isFinite(yv)) continue;
        if (this.xLog && xv <= 0) continue;
        if (xv < xmin) xmin = xv; if (xv > xmax) xmax = xv;
        if (right) { any2 = true; if (yv < y2min) y2min = yv; if (yv > y2max) y2max = yv; }
        else {
          if (this.yLog && yv <= 0) continue;
          any = true; if (yv < ymin) ymin = yv; if (yv > ymax) ymax = yv;
        }
      }
    }
    if (this._hasBar) { if (ymin > 0) ymin = 0; if (ymax < 0) ymax = 0; }
    var anyX = isFinite(xmin);
    if (!any && !anyX) {
      this.full = { x: [this.xLog ? 1 : 0, this.xLog ? 10 : 1], y: [this.yLog ? 1 : 0, this.yLog ? 10 : 1] };
    } else {
      this.full = {
        x: anyX ? this._pad(xmin, xmax, this.xLog) : [0, 1],
        y: any ? this._pad(ymin, ymax, this.yLog) : [0, 1]
      };
    }
    if (any2) this.full.y2 = this._pad(y2min, y2max, false);
    if (this._cats && this._cats.length) this.full.x = [-0.5, this._cats.length - 0.5];
  };

  XYCore.prototype._pad = function (lo, hi, log) {
    if (log) {
      if (lo <= 0) lo = hi > 0 ? hi / 1000 : 1e-3;
      var l0 = Math.log10(lo), l1 = Math.log10(hi);
      if (l1 - l0 < 1e-9) { l0 -= 0.5; l1 += 0.5; }
      var padl = (l1 - l0) * 0.04;
      return [Math.pow(10, l0 - padl), Math.pow(10, l1 + padl)];
    }
    if (hi - lo < 1e-12) { var c = lo === 0 ? 1 : Math.abs(lo); return [lo - c * 0.5, hi + c * 0.5]; }
    var pad = (hi - lo) * 0.05;
    return [lo - pad, hi + pad];
  };

  // ----- layout & render -----------------------------------------------------
  XYCore.prototype._resize = function () {
    if (this.root && this.root.classList) this.root.classList.toggle("gs-narrow", (this.root.clientWidth || 600) < 540);
    var r = this.root.getBoundingClientRect();
    var w = Math.max(140, Math.floor(r.width || 600));
    var h = Math.max(140, Math.floor(r.height || 360));
    this.dpr = Math.max(1, window.devicePixelRatio || 1);
    this.canvas.width = Math.round(w * this.dpr);
    this.canvas.height = Math.round(h * this.dpr);
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
    this.W = w; this.H = h;
    this.render();
  };

  XYCore.prototype._tokens = function () {
    var cs = getComputedStyle(this.root);
    function v(n, f) { var x = cs.getPropertyValue(n).trim(); return x || f; }
    return {
      bg: v("--gs-bg", "#ffffff"), fg: v("--gs-fg", "#1a1a2e"), sub: v("--gs-sub", "#6b7280"),
      grid: v("--gs-grid", "#e3e7ec"), gridMinor: v("--gs-grid-minor", "#f1f3f5"),
      axis: v("--gs-axis", "#9aa3af"), accent: v("--gs-accent", "#2563eb")
    };
  };

  XYCore.prototype._ticks = function (axis) {
    var dom = axis === "x" ? this.view.x : this.view.y;
    var log = axis === "x" ? this.xLog : this.yLog;
    if (axis === "x" && this._cats && this._cats.length) {
      var ts = [];
      for (var ci = 0; ci < this._cats.length; ci++) {
        if (ci < dom[0] - 0.5 || ci > dom[1] + 0.5) continue;
        ts.push({ v: ci, label: String(this._cats[ci]), major: true });
      }
      return { step: 1, ticks: ts };
    }
    if (log) return logTicks(dom[0], dom[1]);
    return linTicks(dom[0], dom[1], this.opts.grid.divisions || 10);
  };

  XYCore.prototype._layout = function (ctx, tok, xt, yt) {
    ctx.font = "11px " + "Segoe UI, system-ui, sans-serif";
    var maxYW = 0;
    for (var i = 0; i < yt.ticks.length; i++) {
      if (!yt.ticks[i].major || !yt.ticks[i].label) continue;
      maxYW = Math.max(maxYW, ctx.measureText(yt.ticks[i].label).width);
    }
    var yTitle = lbl(this.opts.axes.y), xTitle = lbl(this.opts.axes.x);
    var left = Math.ceil(maxYW) + 12 + (yTitle ? 16 : 0);
    // reserve room for the absolute-positioned overlays so they never cover ticks/curves
    var oBottom = 0, qs = this.root.querySelector ? this.root : null;
    if (this.legend && this.legend.offsetHeight) oBottom = Math.max(oBottom, this.legend.offsetHeight + 8);
    var pb = qs && qs.querySelector(".gs-playbar");
    if (pb && pb.offsetHeight) oBottom = Math.max(oBottom, pb.offsetHeight + 10);
    var fp = qs && qs.querySelector(".gs-filter-panel");
    if (fp && fp.offsetHeight) oBottom = Math.max(oBottom, fp.offsetHeight + 10);
    var bottom = 20 + (xTitle ? 18 : 0) + oBottom;
    var cbH = this.controlbar ? this.controlbar.offsetHeight : 0;
    var top = Math.max(this.opts.title ? 26 : 12, cbH ? cbH + 12 : 0);
    var right = 16;
    if (this.opts.hideAxes) {                 // non-cartesian plugins (treemap/gantt/...) own the frame
      var pad = this.opts.pad || {};
      left = pad.left != null ? pad.left : 12;
      right = pad.right != null ? pad.right : 12;
      bottom = (pad.bottom != null ? pad.bottom : 14) + oBottom;
      if (pad.top != null) top = Math.max(top, pad.top);
    }
    if (this._hasRight && this.full && this.full.y2) {
      var rt = linTicks(this.full.y2[0], this.full.y2[1], 6), maxR = 0;
      for (var r = 0; r < rt.ticks.length; r++) maxR = Math.max(maxR, ctx.measureText(rt.ticks[r].label).width);
      right = Math.ceil(maxR) + 12 + (lbl(this.opts.axes.y2 || { label: "", unit: "" }) ? 16 : 0);
    }
    return { left: left, right: this.W - right, top: top, bottom: this.H - bottom };
  };

  XYCore.prototype.render = function () {
    if (!this.ctx || !this.view) return;
    var ctx = this.ctx, tok = this._tokens();
    ctx.save();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H);
    ctx.fillStyle = tok.bg; ctx.fillRect(0, 0, this.W, this.H);

    var xt = this._ticks("x"), yt = this._ticks("y");
    var plot = this._layout(ctx, tok, xt, yt);
    this.plot = plot;
    if (plot.right <= plot.left || plot.bottom <= plot.top) { ctx.restore(); return; }
    if (this.opts.equalAspect && !this.xLog && !this.yLog) this._equalize(plot);

    var sx = makeScale(this.view.x[0], this.view.x[1], plot.left, plot.right, this.xLog);
    var sy = makeScale(this.view.y[0], this.view.y[1], plot.bottom, plot.top, this.yLog);
    this.sx = sx; this.sy = sy;
    this.sy2 = (this._hasRight && this.view.y2) ? makeScale(this.view.y2[0], this.view.y2[1], plot.bottom, plot.top, false) : null;
    var viewObj = this._viewObject(plot, sx, sy, tok);

    if (!this.opts.hideAxes) this._drawGrid(ctx, plot, sx, sy, tok, xt, yt);

    for (var pi = 0; pi < this.plugins.length; pi++) {
      if (this.plugins[pi].onScale) this.plugins[pi].onScale(viewObj);
    }
    for (var pu = 0; pu < this.plugins.length; pu++) {
      if (this.plugins[pu].onDrawUnder) this.plugins[pu].onDrawUnder(ctx, viewObj);
    }

    ctx.save();
    ctx.beginPath();
    ctx.rect(plot.left, plot.top, plot.right - plot.left, plot.bottom - plot.top);
    ctx.clip();
    this._drawSeries(ctx, sx, sy, this.sy2);
    this._drawCursor(ctx, plot, sx, sy, tok);
    for (var po = 0; po < this.plugins.length; po++) {
      if (this.plugins[po].onDrawOver) this.plugins[po].onDrawOver(ctx, viewObj);
    }
    if (this._drag && this._drag.mode === "box") this._drawBox(ctx, tok);
    ctx.restore();
    if (!this.opts.hideAxes && !this._hasAnyData()) {
      ctx.fillStyle = tok.sub; ctx.globalAlpha = 0.8;
      ctx.font = "600 13px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("표시할 데이터 없음", (plot.left + plot.right) / 2, (plot.top + plot.bottom) / 2);
      ctx.globalAlpha = 1;
    }

    if (!this.opts.hideAxes) this._drawAxes(ctx, plot, sx, sy, tok, xt, yt);
    for (var px2 = 0; px2 < this.plugins.length; px2++) {           // unclipped pass (labels in margins)
      if (this.plugins[px2].onDrawOutside) this.plugins[px2].onDrawOutside(ctx, viewObj);
    }
    if (this.opts.title) {
      ctx.fillStyle = tok.fg; ctx.font = "700 13px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      ctx.fillText(this.opts.title, (plot.left + plot.right) / 2, 4);
    }
    ctx.restore();
    this._updateHUD();
  };

  XYCore.prototype._hasAnyData = function () {
    for (var hi = 0; hi < this.series.length; hi++) {
      var hs = this.series[hi];
      if (!this.visible[hi] || hs._internal) continue;
      for (var hj = 0; hj < hs.y.length; hj++) { var hv = hs.y[hj]; if (hv != null && isFinite(hv)) return true; }
    }
    return false;
  };
  XYCore.prototype._viewObject = function (plot, sx, sy, tok) {
    return {
      scaleX: sx.to, scaleY: sy.to, invX: sx.inv, invY: sy.inv,
      domain: { x: this.view.x.slice(), y: this.view.y.slice(), xLog: this.xLog, yLog: this.yLog },
      plot: { left: plot.left, top: plot.top, width: plot.right - plot.left, height: plot.bottom - plot.top },
      dpr: this.dpr, theme: tok, series: this.series, visible: this.visible,
      cursor: this.cursor,
      core: this,                              // plugins reach per-core state/opts via view.core
      pluginConfig: this.opts.pluginConfig || {},
      fmt: fmtVal
    };
  };

  XYCore.prototype._drawGrid = function (ctx, plot, sx, sy, tok, xt, yt) {
    ctx.lineWidth = 1;
    var i, px, py, t;
    for (i = 0; i < xt.ticks.length; i++) {
      t = xt.ticks[i]; px = Math.round(sx.to(t.v)) + 0.5;
      if (px < plot.left - 0.5 || px > plot.right + 0.5) continue;
      if (!this.opts.grid.minor && !t.major) continue;
      ctx.strokeStyle = t.major ? tok.grid : tok.gridMinor;
      ctx.beginPath(); ctx.moveTo(px, plot.top); ctx.lineTo(px, plot.bottom); ctx.stroke();
    }
    for (i = 0; i < yt.ticks.length; i++) {
      t = yt.ticks[i]; py = Math.round(sy.to(t.v)) + 0.5;
      if (py < plot.top - 0.5 || py > plot.bottom + 0.5) continue;
      if (!this.opts.grid.minor && !t.major) continue;
      ctx.strokeStyle = t.major ? tok.grid : tok.gridMinor;
      ctx.beginPath(); ctx.moveTo(plot.left, py); ctx.lineTo(plot.right, py); ctx.stroke();
    }
  };

  XYCore.prototype._drawAxes = function (ctx, plot, sx, sy, tok, xt, yt) {
    ctx.strokeStyle = tok.axis; ctx.lineWidth = 1;
    ctx.strokeRect(plot.left + 0.5, plot.top + 0.5, plot.right - plot.left - 1, plot.bottom - plot.top - 1);
    ctx.fillStyle = tok.sub; ctx.font = "11px Segoe UI, system-ui, sans-serif";
    var i, t, px, py;
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (i = 0; i < xt.ticks.length; i++) {
      t = xt.ticks[i]; if (!t.major || !t.label) continue;
      px = sx.to(t.v); if (px < plot.left - 1 || px > plot.right + 1) continue;
      ctx.fillText(t.label, px, plot.bottom + 5);
    }
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (i = 0; i < yt.ticks.length; i++) {
      t = yt.ticks[i]; if (!t.major || !t.label) continue;
      py = sy.to(t.v); if (py < plot.top - 1 || py > plot.bottom + 1) continue;
      ctx.fillText(t.label, plot.left - 6, py);
    }
    // secondary (right) y axis
    if (this._hasRight && this.sy2 && this.view.y2) {
      var rt = linTicks(this.view.y2[0], this.view.y2[1], 6);
      ctx.fillStyle = tok.sub; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      for (var ri = 0; ri < rt.ticks.length; ri++) {
        var rtt = rt.ticks[ri], rpy = this.sy2.to(rtt.v);
        if (rpy < plot.top - 1 || rpy > plot.bottom + 1) continue;
        ctx.fillText(rtt.label, plot.right + 6, rpy);
      }
      var y2T = lbl(this.opts.axes.y2 || { label: "", unit: "" });
      if (y2T) {
        ctx.save(); ctx.fillStyle = tok.fg; ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
        ctx.translate(this.W - 14, (plot.top + plot.bottom) / 2); ctx.rotate(-Math.PI / 2);
        ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(y2T, 0, 0); ctx.restore();
      }
    }
    // axis titles
    ctx.fillStyle = tok.fg; ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
    var xTitle = lbl(this.opts.axes.x), yTitle = lbl(this.opts.axes.y);
    if (xTitle) {
      ctx.textAlign = "center"; ctx.textBaseline = "bottom";
      ctx.fillText(xTitle, (plot.left + plot.right) / 2, this.H - 2);
    }
    if (yTitle) {
      ctx.save(); ctx.translate(10, (plot.top + plot.bottom) / 2); ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(yTitle, 0, 0); ctx.restore();
    }
  };

  // ----- series paths --------------------------------------------------------
  // Level-of-detail: cap drawn points for huge series. Render-time only (config keeps full
  // data). View-windowed LTTB for monotonic-x series (detail-on-zoom); skipped if gaps/log.
  XYCore.prototype._lod = function (s) {
    var n = s.x.length;
    if (n <= this._lodMax) return s;
    if (s._sorted == null) { s._sorted = true; for (var r = 1; r < n; r++) if (s.x[r] < s.x[r - 1]) { s._sorted = false; break; } }
    var xs = s.x, ys = s.y;
    if (s._sorted) {                                        // view-window first (works with gaps too)
      var v0 = this.view.x[0], v1 = this.view.x[1], pad = (v1 - v0) * 0.05;
      var lo = Math.max(0, lowerBound(xs, v0 - pad) - 1), hi = Math.min(n, lowerBound(xs, v1 + pad) + 1);
      xs = xs.slice(lo, hi); ys = ys.slice(lo, hi);
      if (xs.length <= this._lodMax) return { x: xs, y: ys };
    }
    var xLog = this.xLog, yLog = this.yLog, m = xs.length;
    // split into finite runs (nulls and log-invalid points are gap separators)
    var runs = [], st = -1, i;
    for (i = 0; i < m; i++) {
      var yv = ys[i], bad = (yv == null || !isFinite(yv)) || (xLog && xs[i] <= 0) || (yLog && yv <= 0);
      if (bad) { if (st >= 0) { runs.push([st, i]); st = -1; } }
      else if (st < 0) st = i;
    }
    if (st >= 0) runs.push([st, m]);
    if (runs.length === 1 && runs[0][0] === 0 && runs[0][1] === m && !xLog) return lttb(xs, ys, this._lodMax);
    var total = 0;
    for (i = 0; i < runs.length; i++) total += runs[i][1] - runs[i][0];
    var budget = Math.max(64, this._lodMax - runs.length), ox = [], oy = [], k, j;
    for (i = 0; i < runs.length; i++) {
      var a = runs[i][0], b = runs[i][1], len = b - a;
      var th = Math.max(3, Math.round(budget * (len / Math.max(1, total))));
      if (i > 0) { ox.push(xs[a]); oy.push(null); }          // re-insert the gap separator
      if (len <= th) { for (j = a; j < b; j++) { ox.push(xs[j]); oy.push(ys[j]); } continue; }
      var rx = xs.slice(a, b), ry = ys.slice(a, b);
      var tx = rx;
      if (xLog) { tx = new Array(len); for (j = 0; j < len; j++) tx[j] = Math.log(rx[j]); }  // bucket in log space
      var idx = lttbIdx(tx, ry, th);
      for (k = 0; k < idx.length; k++) { ox.push(rx[idx[k]]); oy.push(ry[idx[k]]); }
    }
    return { x: ox, y: oy };
  };

  XYCore.prototype._segments = function (s, sx, sy) {
    var segs = [], cur = [];
    for (var i = 0; i < s.x.length; i++) {
      var xv = s.x[i], yv = s.y[i], gap = false;
      if (yv == null || !isFinite(yv)) gap = true;
      else if (this.xLog && xv <= 0) gap = true;
      else if (this.yLog && yv <= 0) gap = true;
      if (gap) { if (cur.length) { segs.push(cur); cur = []; } continue; }
      cur.push({ px: sx.to(xv), py: sy.to(yv) });
    }
    if (cur.length) segs.push(cur);
    return segs;
  };

  XYCore.prototype._drawSeries = function (ctx, sx, sy, sy2) {
    var mode = this.opts.curve;
    for (var i = 0; i < this.series.length; i++) {
      if (!this.visible[i]) continue;
      var s = this.series[i], col = s._color, style = s.style || "line";
      if (style === "none") continue;
      var ssy = (sy2 && s.axis === "right") ? sy2 : sy;
      if (style === "bar") { this._drawBars(ctx, s, sx, ssy, col); continue; }
      var segs = this._segments(this._lod(s), sx, ssy);
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.lineCap = "round";
      ctx.setLineDash(s._dash || []);
      if (style !== "markers") {
        for (var g = 0; g < segs.length; g++) {
          var seg = segs[g];
          if (seg.length < 2) continue;
          ctx.beginPath();
          if (mode === "step") this._pathStep(ctx, seg);
          else if (mode === "monotone" && s._mono) this._pathMonotone(ctx, seg);
          else this._pathStraight(ctx, seg);
          ctx.stroke();
        }
      }
      if (style === "markers" || style === "line+markers" || (style === "line" && this._singletons(segs))) {
        ctx.fillStyle = col; ctx.setLineDash([]);
        for (var m = 0; m < segs.length; m++) {
          for (var p = 0; p < segs[m].length; p++) {
            if (style === "line" && segs[m].length > 1) break; // only draw dots for singletons
            ctx.beginPath(); ctx.arc(segs[m][p].px, segs[m][p].py, 2.6, 0, 6.2832); ctx.fill();
          }
        }
      }
      ctx.setLineDash([]);
    }
  };
  XYCore.prototype._singletons = function (segs) {
    for (var i = 0; i < segs.length; i++) if (segs[i].length === 1) return true;
    return false;
  };
  XYCore.prototype._drawBars = function (ctx, s, sx, sy, col) {
    var gap = 1, k;
    if (!this._cats) {
      gap = Infinity;
      for (k = 1; k < s.x.length; k++) { var g = Math.abs(s.x[k] - s.x[k - 1]); if (g > 0 && g < gap) gap = g; }
      if (!isFinite(gap)) gap = 1;
    }
    var hw = gap * 0.4, y0 = sy.to(0);
    ctx.fillStyle = col;
    for (var i = 0; i < s.x.length; i++) {
      var yv = s.y[i]; if (yv == null || !isFinite(yv)) continue;
      var xa = sx.to(s.x[i] - hw), xb = sx.to(s.x[i] + hw), yy = sy.to(yv);
      ctx.fillRect(Math.min(xa, xb), Math.min(y0, yy), Math.abs(xb - xa), Math.abs(yy - y0));
    }
  };

  XYCore.prototype._pathStraight = function (ctx, pts) {
    ctx.moveTo(pts[0].px, pts[0].py);
    for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i].px, pts[i].py);
  };
  XYCore.prototype._pathStep = function (ctx, pts) {
    ctx.moveTo(pts[0].px, pts[0].py);
    for (var i = 1; i < pts.length; i++) { ctx.lineTo(pts[i].px, pts[i - 1].py); ctx.lineTo(pts[i].px, pts[i].py); }
  };
  XYCore.prototype._pathMonotone = function (ctx, pts) {
    var n = pts.length;
    if (n === 2) { ctx.moveTo(pts[0].px, pts[0].py); ctx.lineTo(pts[1].px, pts[1].py); return; }
    var dx = [], m = [], t = [], i;
    for (i = 0; i < n - 1; i++) { dx[i] = pts[i + 1].px - pts[i].px; m[i] = (pts[i + 1].py - pts[i].py) / (dx[i] || 1e-9); }
    t[0] = m[0]; t[n - 1] = m[n - 2];
    for (i = 1; i < n - 1; i++) t[i] = (m[i - 1] * m[i] <= 0) ? 0 : (m[i - 1] + m[i]) / 2;
    for (i = 0; i < n - 1; i++) {
      if (m[i] === 0) { t[i] = 0; t[i + 1] = 0; }
      else { var a = t[i] / m[i], b = t[i + 1] / m[i], h = a * a + b * b; if (h > 9) { var tau = 3 / Math.sqrt(h); t[i] = tau * a * m[i]; t[i + 1] = tau * b * m[i]; } }
    }
    ctx.moveTo(pts[0].px, pts[0].py);
    for (i = 0; i < n - 1; i++) {
      var hh = dx[i];
      ctx.bezierCurveTo(pts[i].px + hh / 3, pts[i].py + t[i] * hh / 3, pts[i + 1].px - hh / 3, pts[i + 1].py - t[i + 1] * hh / 3, pts[i + 1].px, pts[i + 1].py);
    }
  };

  // ----- cursor / hover ------------------------------------------------------
  XYCore.prototype._drawCursor = function (ctx, plot, sx, sy, tok) {
    var c = this.cursor; if (!c || !this.opts.interactions.crosshair) return;
    ctx.save();
    ctx.strokeStyle = tok.axis; ctx.lineWidth = 1; ctx.setLineDash([3, 3]); ctx.globalAlpha = 0.85;
    ctx.beginPath(); ctx.moveTo(c.px, plot.top); ctx.lineTo(c.px, plot.bottom);
    ctx.moveTo(plot.left, c.py); ctx.lineTo(plot.right, c.py); ctx.stroke();
    ctx.setLineDash([]); ctx.globalAlpha = 1;
    if (c.hits) {
      for (var i = 0; i < c.hits.length; i++) {
        var h = c.hits[i];
        if (h.py == null) continue;
        ctx.fillStyle = h.color; ctx.strokeStyle = tok.bg; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(h.px, h.py, 4, 0, 6.2832); ctx.fill(); ctx.stroke();
      }
    }
    ctx.restore();
  };

  XYCore.prototype._hitTest = function (dataX) {
    var hits = [];
    for (var i = 0; i < this.series.length; i++) {
      if (!this.visible[i]) continue;
      var s = this.series[i];
      if (s._internal) continue;
      var idx = this._nearestX(s, dataX);
      if (idx < 0) continue;
      var x = s.x[idx], y = s.y[idx];
      if (y == null || !isFinite(y)) continue;
      if (this.xLog && x <= 0) continue;
      if (this.yLog && y <= 0) continue;
      var ssy = (this.sy2 && s.axis === "right") ? this.sy2 : this.sy;
      var px = this.sx.to(x), py = ssy.to(y);
      hits.push({ i: i, name: s.name, color: s._color, x: x, y: y, px: px, py: py });
    }
    var cpy = this.cursor ? this.cursor.py : 0;
    hits.sort(function (a, b) { return Math.abs(a.py - cpy) - Math.abs(b.py - cpy); });
    return hits;
  };
  XYCore.prototype._nearestX = function (s, x) {
    var best = -1, bd = Infinity;
    for (var i = 0; i < s.x.length; i++) {
      if (s.y[i] == null) continue;
      var d = Math.abs(s.x[i] - x);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };

  // ----- HUD / tooltip -------------------------------------------------------
  XYCore.prototype._updateHUD = function () {
    if (!this.cursor) { this.hud.style.display = "none"; return; }
    var ax = this.opts.axes, c = this.cursor;
    var extra = "";
    for (var i = 0; i < this.plugins.length; i++) {
      if (this.plugins[i].onHover) {
        var r = this.plugins[i].onHover(this._viewObject(this.plot, this.sx, this.sy, this._tokens()), c);
        if (r && r.hud) extra += '<div>' + r.hud + '</div>';
      }
    }
    this.hud.style.display = "block";
    var xl = lbl(ax.x) || "x", yl = lbl(ax.y) || "y";
    var rows = this._hudHideXY ? "" :
      '<div>' + esc(xl) + ': <b>' + fmtVal(c.dataX) + '</b></div>' +
      '<div>' + esc(yl) + ': <b>' + fmtVal(c.dataY) + '</b></div>';
    this.hud.innerHTML = rows + extra + (this.locked ? '<div class="gs-lock">🔒 lock</div>' : '');
  };

  XYCore.prototype._showTooltip = function () {
    var c = this.cursor;
    if (!c || !c.hits || !c.hits.length) { this.tooltip.style.opacity = "0"; return; }
    var ax = this.opts.axes, html = '<div class="gs-tt-x">' + esc(ax.x.label || "x") + ": " + fmtVal(c.dataX) + (ax.x.unit ? " " + esc(ax.x.unit) : "") + "</div>";
    for (var i = 0; i < c.hits.length; i++) {
      var h = c.hits[i];
      html += '<div class="gs-tt-row"><span class="gs-sw" style="background:' + h.color + '"></span>' +
        esc(h.name) + ": " + fmtVal(h.y) + (ax.y.unit ? " " + esc(ax.y.unit) : "") + "</div>";
    }
    this.tooltip.innerHTML = html;
    this.tooltip.style.opacity = "1";
    var tw = this.tooltip.offsetWidth, th = this.tooltip.offsetHeight;
    var x = c.px + 14, y = c.py + 14;
    if (x + tw > this.W - 4) x = c.px - tw - 14;
    if (y + th > this.H - 4) y = c.py - th - 14;
    if (x < 4) x = 4; if (y < 4) y = 4;
    this.tooltip.style.left = x + "px";
    this.tooltip.style.top = y + "px";
  };

  // ----- events --------------------------------------------------------------
  XYCore.prototype._bindEvents = function () {
    var self = this, cv = this.canvas;
    if (cv.setAttribute) cv.setAttribute("tabindex", "0");      // keyboard: focusable chart
    cv.addEventListener("keydown", function (e) { self._onKey(e); });
    cv.addEventListener("pointermove", function (e) { self._onMove(e); });
    cv.addEventListener("pointerdown", function (e) { self._onDown(e); });
    cv.addEventListener("pointerup", function (e) { self._onUp(e); });
    cv.addEventListener("pointerleave", function () { if (!self.locked) { self.cursor = null; self.tooltip.style.opacity = "0"; self.render(); } });
    cv.addEventListener("dblclick", function () { self.autoFit(); });
    cv.addEventListener("wheel", function (e) { self._onWheel(e); }, { passive: false });
  };

  XYCore.prototype._onKey = function (e) {
    if (!this.view) return;
    var sx = (this.view.x[1] - this.view.x[0]) * 0.1, sy = (this.view.y[1] - this.view.y[0]) * 0.1;
    var handled = true;
    switch (e.key) {
      case "ArrowLeft": this.view.x = [this.view.x[0] - sx, this.view.x[1] - sx]; break;
      case "ArrowRight": this.view.x = [this.view.x[0] + sx, this.view.x[1] + sx]; break;
      case "ArrowUp": this.view.y = [this.view.y[0] + sy, this.view.y[1] + sy]; break;
      case "ArrowDown": this.view.y = [this.view.y[0] - sy, this.view.y[1] - sy]; break;
      case "+": case "=": this._zoomBy(1 / 1.25); return;
      case "-": case "_": this._zoomBy(1.25); return;
      case "Home": case "0": this.autoFit(); break;
      case "Escape": this.locked = false; this.cursor = null; this.tooltip.style.opacity = "0"; break;
      default: handled = false;
    }
    if (handled) { if (e.preventDefault) e.preventDefault(); this.render(); }
  };
  XYCore.prototype._localXY = function (e) {
    var r = this.canvas.getBoundingClientRect();
    return { px: e.clientX - r.left, py: e.clientY - r.top };
  };
  XYCore.prototype._inPlot = function (px, py) {
    return this.plot && px >= this.plot.left && px <= this.plot.right && py >= this.plot.top && py <= this.plot.bottom;
  };

  XYCore.prototype._onMove = function (e) {
    if (this._ptrs[e.pointerId]) {
      this._ptrs[e.pointerId] = this._localXY(e);
      var pids = Object.keys(this._ptrs);
      if (this._pinch && pids.length >= 2) {
        var pp1 = this._ptrs[pids[0]], pp2 = this._ptrs[pids[1]];
        var pd = Math.hypot(pp1.px - pp2.px, pp1.py - pp2.py) || 1;
        var pf = this._pinch.d / pd;           // spread -> factor<1 -> zoom in (matches _zoom)
        this._pinch.d = pd;
        var pmx = (pp1.px + pp2.px) / 2, pmy = (pp1.py + pp2.py) / 2;
        if (this.sx && this.sy) {
          this.view.x = this._zoom(this.view.x, this.sx.inv(pmx), pf, this.xLog);
          this.view.y = this._zoom(this.view.y, this.sy.inv(pmy), pf, this.yLog);
          this.render();
        }
        return;
      }
    }
    var p = this._localXY(e);
    if (this._drag) { this._onDrag(p.px, p.py); return; }
    if (this.locked) return;
    if (!this._inPlot(p.px, p.py)) { this.cursor = null; this.tooltip.style.opacity = "0"; this.render(); return; }
    this.cursor = { px: p.px, py: p.py, dataX: this.sx.inv(p.px), dataY: this.sy.inv(p.py) };
    this.cursor.hits = this._hitTest(this.cursor.dataX);
    this._showTooltip();
    this.render();
  };

  XYCore.prototype._onDown = function (e) {
    if (e.pointerType === "touch") {
      this._ptrs[e.pointerId] = this._localXY(e);
      var pids = Object.keys(this._ptrs);
      if (pids.length === 2) {                 // two fingers -> pinch (cancels pan/box)
        var pp1 = this._ptrs[pids[0]], pp2 = this._ptrs[pids[1]];
        this._pinch = { d: Math.hypot(pp1.px - pp2.px, pp1.py - pp2.py) || 1 };
        this._drag = null;
        return;
      }
    }
    var p = this._localXY(e);
    if (!this._inPlot(p.px, p.py)) return;
    this.canvas.setPointerCapture(e.pointerId);
    this._moved = false;
    // a plugin may claim the drag (e.g. parcoord brushing); existing plugins define no onDown
    var pc = { px: p.px, py: p.py, dataX: this.sx.inv(p.px), dataY: this.sy.inv(p.py) };
    for (var pd = 0; pd < this.plugins.length; pd++) {
      if (this.plugins[pd].onDown && this.plugins[pd].onDown(this._viewObject(this.plot, this.sx, this.sy, this._tokens()), pc) === true) {
        this._drag = { mode: "plugin", plugin: this.plugins[pd] }; this.render(); return;
      }
    }
    if (e.shiftKey && this.opts.interactions.boxZoom) {
      this._drag = { mode: "box", x0: p.px, y0: p.py, x1: p.px, y1: p.py };
    } else if (this.opts.interactions.pan) {
      this._drag = { mode: "pan", x0: p.px, y0: p.py, vx: this.view.x.slice(), vy: this.view.y.slice() };
    }
  };

  XYCore.prototype._onDrag = function (px, py) {
    var ds = this._drag; if (!ds) return;
    if (ds.mode === "plugin") {
      this._moved = true;
      if (ds.plugin.onDrag) ds.plugin.onDrag(this._viewObject(this.plot, this.sx, this.sy, this._tokens()),
        { px: px, py: py, dataX: this.sx.inv(px), dataY: this.sy.inv(py) });
      this.render(); return;
    }
    if (Math.abs(px - ds.x0) + Math.abs(py - ds.y0) > 3) this._moved = true;
    if (ds.mode === "box") { ds.x1 = px; ds.y1 = py; this.render(); return; }
    var pw = this.plot.right - this.plot.left, ph = this.plot.bottom - this.plot.top;
    this.view.x = this._shift(ds.vx, -(px - ds.x0) / pw, this.xLog);
    this.view.y = this._shift(ds.vy, (py - ds.y0) / ph, this.yLog);
    this.render();
  };

  XYCore.prototype._shift = function (dom, frac, log) {
    if (log) {
      var l0 = Math.log10(dom[0]), l1 = Math.log10(dom[1]), d = (l1 - l0) * frac;
      return [Math.pow(10, l0 + d), Math.pow(10, l1 + d)];
    }
    var span = dom[1] - dom[0];
    return [dom[0] + span * frac, dom[1] + span * frac];
  };

  XYCore.prototype._onUp = function (e) {
    if (e && e.pointerId != null && this._ptrs[e.pointerId]) {
      delete this._ptrs[e.pointerId];
      if (Object.keys(this._ptrs).length < 2) this._pinch = null;
    }
    var ds = this._drag;
    try { this.canvas.releasePointerCapture(e.pointerId); } catch (_) {}
    if (ds && ds.mode === "plugin") {
      var pu = this._localXY(e);
      if (ds.plugin.onUp) ds.plugin.onUp(this._viewObject(this.plot, this.sx, this.sy, this._tokens()),
        { px: pu.px, py: pu.py, dataX: this.sx.inv(pu.px), dataY: this.sy.inv(pu.py), moved: this._moved });
      this._drag = null; this.render(); return;
    }
    if (ds && ds.mode === "box" && this._moved) {
      var x0 = Math.min(ds.x0, ds.x1), x1 = Math.max(ds.x0, ds.x1);
      var y0 = Math.min(ds.y0, ds.y1), y1 = Math.max(ds.y0, ds.y1);
      if (x1 - x0 > 6 && y1 - y0 > 6) {
        this.view.x = [this.sx.inv(x0), this.sx.inv(x1)];
        this.view.y = [this.sy.inv(y1), this.sy.inv(y0)]; // y inverted
      }
    } else if (!this._moved) {
      // a click toggles lock at the current cursor
      var p = this._localXY(e);
      if (this._inPlot(p.px, p.py)) {
        this.locked = !this.locked;
        if (this.locked) { this.cursor = { px: p.px, py: p.py, dataX: this.sx.inv(p.px), dataY: this.sy.inv(p.py) }; this.cursor.hits = this._hitTest(this.cursor.dataX); }
        if (this.locked) this._showTooltip();   // tap/click shows series values (touch has no hover)
        for (var i = 0; i < this.plugins.length; i++) if (this.plugins[i].onClick) this.plugins[i].onClick(this._viewObject(this.plot, this.sx, this.sy, this._tokens()), this.cursor);
      }
    }
    this._drag = null;
    this.render();
  };

  XYCore.prototype._zoomHint = function () {
    var self = this;
    if (!this._zh) {
      this._zh = el("gs-zoom-hint");
      var mac = typeof navigator !== "undefined" && navigator.platform && navigator.platform.indexOf("Mac") >= 0;
      this._zh.textContent = (mac ? "⌘" : "Ctrl") + " + 스크롤로 확대/축소";
      this.root.appendChild(this._zh);
    }
    this._zh.classList.add("gs-show");
    clearTimeout(this._zhT);
    this._zhT = setTimeout(function () { self._zh.classList.remove("gs-show"); }, 1400);
  };
  XYCore.prototype._onWheel = function (e) {
    if (!this.opts.interactions.zoom) return;
    var p = this._localXY(e);
    if (!this._inPlot(p.px, p.py)) return;
    // plain wheel keeps scrolling the host page (no embed scroll-trap); Ctrl/⌘+wheel zooms
    if (!(e.ctrlKey || e.metaKey)) { this._zoomHint(); return; }
    e.preventDefault();
    var factor = Math.pow(1.0015, e.deltaY); // deltaY>0 -> zoom out
    var zx = !e.altKey, zy = !e.shiftKey;    // Ctrl+Shift = x only, Ctrl+Alt = y only
    var ax = this.sx.inv(p.px), ay = this.sy.inv(p.py);
    if (zx) this.view.x = this._zoom(this.view.x, ax, factor, this.xLog);
    if (zy) this.view.y = this._zoom(this.view.y, ay, factor, this.yLog);
    this.render();
  };
  XYCore.prototype._zoom = function (dom, center, factor, log) {
    if (log) {
      var l0 = Math.log10(dom[0]), l1 = Math.log10(dom[1]), lc = Math.log10(center);
      return [Math.pow(10, lc + (l0 - lc) * factor), Math.pow(10, lc + (l1 - lc) * factor)];
    }
    return [center + (dom[0] - center) * factor, center + (dom[1] - center) * factor];
  };

  XYCore.prototype._drawBox = function (ctx, tok) {
    var ds = this._drag;
    ctx.save();
    ctx.fillStyle = tok.accent; ctx.globalAlpha = 0.12;
    ctx.fillRect(ds.x0, ds.y0, ds.x1 - ds.x0, ds.y1 - ds.y0);
    ctx.globalAlpha = 0.8; ctx.strokeStyle = tok.accent; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.strokeRect(ds.x0, ds.y0, ds.x1 - ds.x0, ds.y1 - ds.y0);
    ctx.restore();
  };

  // ----- log toggle ----------------------------------------------------------
  XYCore.prototype._setLog = function (axis, on) {
    var prev = axis === "x" ? this.xLog : this.yLog;
    if (axis === "x") this.xLog = on; else this.yLog = on;
    this._computeFull();
    // guard: if turning log on left no positive data, revert
    var dom = axis === "x" ? this.full.x : this.full.y;
    if (on && (!(dom[0] > 0) || !(dom[1] > 0))) {
      if (axis === "x") this.xLog = prev; else this.yLog = prev;
      console.warn("[graph-skill] log scale needs positive data on " + axis + " axis; kept linear.");
      this._computeFull();
    }
    this.view = this._cloneDom(this.full);
    this._syncButtons();
    this.render();
  };

  // ----- DOM (controls / legend) ---------------------------------------------
  XYCore.prototype._buildDOM = function () {
    if (this.opts.controlbar !== false) { this.controlbar = el("gs-controlbar"); this.root.appendChild(this.controlbar); }
    this.hud = el("gs-hud"); this.hud.style.display = "none"; this.root.appendChild(this.hud);
    this.tooltip = el("gs-tooltip"); this.root.appendChild(this.tooltip);
    if (this.opts.legend.show) { this.legend = el("gs-legend"); this.root.appendChild(this.legend); }
    this._buildButtons();
  };

  XYCore.prototype._btn = function (label, title, onclick, parent) {
    var b = document.createElement("button");
    b.className = "gs-btn"; b.type = "button"; b.textContent = label; b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("click", onclick);
    (parent || this.controlbar).appendChild(b);
    return b;
  };
  XYCore.prototype._zoomBy = function (factor) {
    if (!this.view) return;
    var zcx = this.xLog ? Math.sqrt(this.view.x[0] * this.view.x[1]) : (this.view.x[0] + this.view.x[1]) / 2;
    var zcy = this.yLog ? Math.sqrt(this.view.y[0] * this.view.y[1]) : (this.view.y[0] + this.view.y[1]) / 2;
    this.view.x = this._zoom(this.view.x, zcx, factor, this.xLog);
    this.view.y = this._zoom(this.view.y, zcy, factor, this.yLog);
    this.render();
  };
  XYCore.prototype._toggleHelp = function () {
    if (!this._help) {
      var h = el("gs-help");
      var rows = [
        "호버 — 값 추적 + 크로스헤어 / 클릭 — 고정(잠금)",
        "드래그 — 이동 · Shift+드래그 — 영역 확대",
        "Ctrl(Cmd)+스크롤 — 확대/축소 (+Shift: x만 · +Alt: y만)",
        "더블클릭 — 전체 보기 · 두 손가락(터치) — 확대/축소",
        "범례 클릭 — 숨김/표시 · 더블클릭 — 단독 보기"
      ];
      var inner = rows.map(function (r) { return "<div>" + r + "</div>"; }).join("");
      h.innerHTML = '<div class="gs-help-title">조작 방법</div>' + inner;
      h.addEventListener("click", function () { h.classList.remove("gs-open"); });
      this.root.appendChild(h);
      this._help = h;
    }
    this._help.classList.toggle("gs-open");
  };

  XYCore.prototype._buildButtons = function () {
    var self = this;
    if (!this.controlbar) return;
    if (this.opts.interactions.zoom !== false) {
      this._btn("＋", "확대", function () { self._zoomBy(1 / 1.25); });
      this._btn("－", "축소", function () { self._zoomBy(1.25); });
    }
    if (!this.opts.hideAxes) {                // log toggles are meaningless on non-cartesian plugins
      this._btnLogX = this._btn("log x", "x축 로그/선형 토글", function () { self._setLog("x", !self.xLog); });
      this._btnLogY = this._btn("log y", "y축 로그/선형 토글", function () { self._setLog("y", !self.yLog); });
    }
    this._btn("↺", "전체 보기", function () { self.autoFit(); });
    this._btn("◐", "테마 (자동/밝게/어둡게)", function () { self._cycleTheme(); });
    var ex = this.opts.exportButtons || [];
    if (ex.length) {                          // exports collapse into a single menu on narrow widths
      this._moreBtn = this._btn("⋯", "내보내기 메뉴", function () { self._exports.classList.toggle("gs-open"); });
      this._moreBtn.classList.add("gs-more");
      this._exports = el("gs-exports");
      this.controlbar.appendChild(this._exports);
      if (ex.indexOf("png") >= 0) this._btn("PNG", "PNG 내보내기", function () { self.exportPNG(2); }, this._exports);
      if (ex.indexOf("csv") >= 0) this._btn("CSV", "데이터 CSV 내보내기", function () { self.exportCSV(); }, this._exports);
      if (ex.indexOf("config") >= 0) this._btn("{}", "graph-config JSON 내보내기", function () { self.exportConfig(); }, this._exports);
    }
    this._btn("?", "조작 방법", function () { self._toggleHelp(); });
    this._syncButtons();
  };
  XYCore.prototype._syncButtons = function () {
    if (this._btnLogX) this._btnLogX.setAttribute("aria-pressed", this.xLog ? "true" : "false");
    if (this._btnLogY) this._btnLogY.setAttribute("aria-pressed", this.yLog ? "true" : "false");
  };
  XYCore.prototype._cycleTheme = function () {
    var order = ["auto", "light", "dark"];
    var cur = this.root.getAttribute("data-theme") || "auto";
    this.root.setAttribute("data-theme", order[(order.indexOf(cur) + 1) % 3]);
    this.render();
  };

  XYCore.prototype._buildLegend = function () {
    if (!this.legend) return;
    var self = this;
    this.legend.innerHTML = "";
    this.series.forEach(function (s, i) {
      if (s._internal) return;                 // carriers stay out of the legend
      var item = el("gs-legend-item");
      item._si = i;                            // legend rows may be sparser than series
      if (item.setAttribute) {                 // keyboard: Enter/Space toggles the series
        item.setAttribute("tabindex", "0"); item.setAttribute("role", "button");
        item.setAttribute("aria-label", (s.name || "") + " 표시/숨김");
      }
      item.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { if (e.preventDefault) e.preventDefault(); self._toggleSeries(i); }
      });
      var sw = el("gs-sw"); sw.style.background = s._color; item.appendChild(sw);
      var name = document.createElement("span"); name.textContent = s.name; item.appendChild(name);
      if (!self.visible[i]) item.classList.add("gs-off");
      item.addEventListener("click", function () { self._toggleSeries(i); });
      item.addEventListener("dblclick", function (e) { e.preventDefault(); self._isolateSeries(i); });
      self.legend.appendChild(item);
    });
    if (!this.legend.children.length) this.legend.style.display = "none";
  };
  XYCore.prototype._isZoomed = function () {
    if (!this.view || !this.full) return false;
    function neq(a, b, span) { return Math.abs(a - b) > Math.abs(span) * 1e-9 + 1e-12; }
    var fx = this.full.x, fy = this.full.y;
    return neq(this.view.x[0], fx[0], fx[1] - fx[0]) || neq(this.view.x[1], fx[1], fx[1] - fx[0]) ||
      neq(this.view.y[0], fy[0], fy[1] - fy[0]) || neq(this.view.y[1], fy[1], fy[1] - fy[0]);
  };
  XYCore.prototype._afterVisibility = function () {
    this._refreshLegendState();
    if (this._isZoomed()) { this._computeFull(); this.render(); }   // keep the user's zoom/lock
    else this.autoFit();
  };
  XYCore.prototype._toggleSeries = function (i) {
    this.visible[i] = !this.visible[i];
    this._afterVisibility();
  };
  XYCore.prototype._isolateSeries = function (i) {
    if (!this.opts.legend.isolateOnDblClick) return;
    var self = this;
    var onlyThis = this.visible.every(function (v, k) {
      if (self.series[k]._internal) return true;
      return k === i ? v : !v;
    });
    for (var k = 0; k < this.visible.length; k++) {
      if (this.series[k]._internal) { this.visible[k] = true; continue; }
      this.visible[k] = onlyThis ? true : (k === i);
    }
    this._afterVisibility();
  };
  XYCore.prototype._refreshLegendState = function () {
    if (!this.legend) return;
    var items = this.legend.children;
    for (var i = 0; i < items.length; i++) {
      var si = items[i]._si != null ? items[i]._si : i;
      items[i].classList.toggle("gs-off", !this.visible[si]);
    }
  };

  // ----- export --------------------------------------------------------------
  XYCore.prototype._download = function (url, name) {
    var a = document.createElement("a"); a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };
  XYCore.prototype.exportPNG = function (scale) {
    scale = scale || 2;
    var off = document.createElement("canvas");
    off.width = Math.round(this.W * scale); off.height = Math.round(this.H * scale);
    off.getContext("2d").drawImage(this.canvas, 0, 0, off.width, off.height);
    this._download(off.toDataURL("image/png"), (this.opts.title || "graph") + ".png");
  };
  XYCore.prototype.exportCSV = function () {
    var lines = ["series,x,y"];
    for (var i = 0; i < this.series.length; i++) {
      var s = this.series[i];
      var nm = /[",\n]/.test(s.name) ? '"' + s.name.replace(/"/g, '""') + '"' : s.name;
      for (var k = 0; k < s.x.length; k++) lines.push(nm + "," + s.x[k] + "," + (s.y[k] == null ? "" : s.y[k]));
    }
    this._download("data:text/csv;charset=utf-8," + encodeURIComponent(lines.join("\n")), (this.opts.title || "graph") + ".csv");
  };
  XYCore.prototype.exportConfig = function () {
    var node = document.getElementById("graph-config");
    var txt = node ? node.textContent : JSON.stringify({ engine: "xy-core", options: this.opts, assets: { series: this.series } });
    this._download("data:application/json;charset=utf-8," + encodeURIComponent(txt), (this.opts.title || "graph") + ".json");
  };
  XYCore.prototype.destroy = function () { if (this._ro) this._ro.disconnect(); };

  // ----- register family -----------------------------------------------------
  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["xy-core"] = function (mount, options) { return new XYCore(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.XYCore = XYCore;
})();
