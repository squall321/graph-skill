/* ===========================================================================
 * field-core — 2D scalar field (contour / heatmap) engine family.
 * Renders z = f(x,y) on a grid: colormap raster (offscreen + drawImage), marching-squares
 * iso-contours, a colorbar legend, probe-pick (hover -> x,y,z in HUD), zoom/pan/box-zoom,
 * dark mode, responsive. Dispatched via window.GraphEngines["field-core"].
 * =========================================================================== */
(function () {
  "use strict";

  var CMAPS = {
    viridis: [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
    coolwarm: [[0, [59, 76, 192]], [0.5, [221, 221, 221]], [1, [180, 4, 38]]],
    turbo: [[0, [48, 18, 59]], [0.25, [33, 144, 141]], [0.5, [122, 209, 81]], [0.75, [251, 162, 53]], [1, [122, 4, 3]]],
    gray: [[0, [20, 20, 20]], [1, [240, 240, 240]]]
  };
  var CMAP_ORDER = ["viridis", "turbo", "coolwarm", "gray"];

  var DEFAULTS = {
    axes: { x: { label: "", unit: "" }, y: { label: "", unit: "" } },
    z: { label: "", unit: "" },
    colormap: "viridis", reverse: false, contours: true, levels: 8,
    theme: "auto", responsive: { aspectRatio: "16 / 9" }, title: "", exportButtons: ["png"]
  };

  function deepMerge(b, o) {
    var out = {}; for (var k in b) if (b.hasOwnProperty(k)) out[k] = b[k];
    if (!o) return out;
    for (var j in o) {
      if (!o.hasOwnProperty(j)) continue;
      var v = o[j];
      if (v && typeof v === "object" && !Array.isArray(v) && b[j] && typeof b[j] === "object") out[j] = deepMerge(b[j], v);
      else out[j] = v;
    }
    return out;
  }
  function el(c) { var d = document.createElement("div"); if (c) d.className = c; return d; }
  function fmtVal(v) {
    if (v == null || !isFinite(v)) return "—";
    var a = Math.abs(v);
    if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(2);
    return String(Math.round(v * 1e4) / 1e4);
  }
  function lbl(ax) { return (ax.label || "") + (ax.unit ? " [" + ax.unit + "]" : ""); }
  function niceNum(x, round) {
    if (!(x > 0)) return 1;
    var e = Math.floor(Math.log10(x)), f = x / Math.pow(10, e), nf;
    if (round) nf = f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10; else nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
    return nf * Math.pow(10, e);
  }
  function fmtTick(v, step) {
    if (v === 0) return "0";
    var a = Math.abs(v);
    if (a >= 1e5 || a < 1e-3) return v.toExponential(1);
    var dec = Math.max(0, -Math.floor(Math.log10(step))); if (dec > 6) dec = 6;
    return v.toFixed(dec);
  }
  function linTicks(lo, hi, target) {
    if (!(hi > lo)) hi = lo + 1;
    var span = niceNum(hi - lo, false), step = niceNum(span / Math.max(2, target), true);
    var out = []; for (var v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) out.push(v);
    return { step: step, vals: out };
  }
  function scale(d0, d1, p0, p1) {
    if (d1 === d0) d1 = d0 + 1;
    return { to: function (v) { return p0 + (v - d0) / (d1 - d0) * (p1 - p0); },
             inv: function (p) { return d0 + (p - p0) / (p1 - p0) * (d1 - d0); } };
  }
  function cmap(name, t, reverse) {
    var stops = CMAPS[name] || CMAPS.viridis;
    t = t < 0 ? 0 : t > 1 ? 1 : t; if (reverse) t = 1 - t;
    for (var i = 1; i < stops.length; i++) {
      if (t <= stops[i][0]) {
        var a = stops[i - 1], b = stops[i], f = (t - a[0]) / (b[0] - a[0] || 1);
        return [Math.round(a[1][0] + f * (b[1][0] - a[1][0])),
                Math.round(a[1][1] + f * (b[1][1] - a[1][1])),
                Math.round(a[1][2] + f * (b[1][2] - a[1][2]))];
      }
    }
    return stops[stops.length - 1][1];
  }
  function bisect(arr, v) { // largest index with arr[i] <= v (assumes ascending)
    var lo = 0, hi = arr.length - 1;
    if (v <= arr[0]) return 0; if (v >= arr[hi]) return hi - 1 < 0 ? 0 : hi - 1;
    while (lo < hi) { var m = (lo + hi + 1) >> 1; if (arr[m] <= v) lo = m; else hi = m - 1; }
    return lo;
  }

  function FieldCore(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-root");
    this.opts = deepMerge(DEFAULTS, options || {});
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    if (this.opts.responsive && this.opts.responsive.aspectRatio) this.root.style.aspectRatio = this.opts.responsive.aspectRatio;
    this.canvas = document.createElement("canvas"); this.root.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.cmapName = this.opts.colormap; this.reverse = !!this.opts.reverse;
    this.cursor = null; this._drag = null; this._moved = false;
    this._buildDOM(); this._bindEvents();
    var self = this; this._ro = new ResizeObserver(function () { self._resize(); }); this._ro.observe(this.root);
    this._resize();
  }

  FieldCore.prototype.use = function () { return this; };
  FieldCore.prototype.setAssets = function (a) {
    var f = (a && a.field) || {};
    this.x = f.x || []; this.y = f.y || []; this.z = f.z || [];
    this.vectors = f.vectors || null;                  // optional {x,y,u,v} for quiver overlay
    this.nx = this.x.length; this.ny = this.y.length;
    this._computeZ();
    this.full = { x: [this.x[0], this.x[this.nx - 1]], y: [this.y[0], this.y[this.ny - 1]] };
    this.view = { x: this.full.x.slice(), y: this.full.y.slice() };
    this._buildLevels(); this._rasterize(); this.render();
  };
  FieldCore.prototype.setData = function (d) { this.setAssets({ field: d }); };
  FieldCore.prototype.autoFit = function () { if (this.full) { this.view = { x: this.full.x.slice(), y: this.full.y.slice() }; this.cursor = null; this.render(); } };

  FieldCore.prototype._computeZ = function () {
    var mn = Infinity, mx = -Infinity;
    for (var j = 0; j < this.ny; j++) for (var i = 0; i < this.nx; i++) {
      var v = this.z[j] && this.z[j][i];
      if (v == null || !isFinite(v)) continue;
      if (v < mn) mn = v; if (v > mx) mx = v;
    }
    if (!isFinite(mn)) { mn = 0; mx = 1; }
    if (this.opts.zdomain) { mn = this.opts.zdomain[0]; mx = this.opts.zdomain[1]; }
    this.zmin = mn; this.zmax = mx === mn ? mn + 1 : mx;
  };
  FieldCore.prototype._buildLevels = function () {
    var L = this.opts.levels;
    if (Array.isArray(L)) { this.levels = L.slice(); return; }
    var n = (typeof L === "number" && L > 0) ? L : 8, out = [];
    for (var k = 1; k <= n; k++) out.push(this.zmin + (this.zmax - this.zmin) * k / (n + 1));
    this.levels = out;
  };
  FieldCore.prototype._rasterize = function () {
    if (!this.nx || !this.ny || this.opts.arrowsOnly) { this._off = null; return; }
    var off = document.createElement("canvas"); off.width = this.nx; off.height = this.ny;
    var octx = off.getContext("2d"), img = octx.createImageData(this.nx, this.ny), d = img.data;
    for (var j = 0; j < this.ny; j++) {
      var row = this.ny - 1 - j;
      for (var i = 0; i < this.nx; i++) {
        var v = this.z[j] && this.z[j][i], idx = (row * this.nx + i) * 4;
        if (v == null || !isFinite(v)) { d[idx + 3] = 0; continue; }
        var c = cmap(this.cmapName, (v - this.zmin) / (this.zmax - this.zmin), this.reverse);
        d[idx] = c[0]; d[idx + 1] = c[1]; d[idx + 2] = c[2]; d[idx + 3] = 255;
      }
    }
    octx.putImageData(img, 0, 0); this._off = off;
  };

  FieldCore.prototype._resize = function () {
    var r = this.root.getBoundingClientRect();
    var w = Math.max(160, Math.floor(r.width || 600)), h = Math.max(140, Math.floor(r.height || 360));
    this.dpr = Math.max(1, window.devicePixelRatio || 1);
    this.canvas.width = Math.round(w * this.dpr); this.canvas.height = Math.round(h * this.dpr);
    this.canvas.style.width = w + "px"; this.canvas.style.height = h + "px";
    this.W = w; this.H = h; this.render();
  };
  FieldCore.prototype._tokens = function () {
    var cs = getComputedStyle(this.root); function v(n, f) { var x = cs.getPropertyValue(n).trim(); return x || f; }
    return { bg: v("--gs-bg", "#fff"), fg: v("--gs-fg", "#1a1a2e"), sub: v("--gs-sub", "#6b7280"),
             grid: v("--gs-grid", "#e3e7ec"), axis: v("--gs-axis", "#9aa3af"), accent: v("--gs-accent", "#2563eb") };
  };
  FieldCore.prototype._layout = function (ctx, yt) {
    ctx.font = "11px Segoe UI, system-ui, sans-serif";
    var maxYW = 0; for (var i = 0; i < yt.vals.length; i++) maxYW = Math.max(maxYW, ctx.measureText(fmtTick(yt.vals[i], yt.step)).width);
    var left = Math.ceil(maxYW) + 12 + (lbl(this.opts.axes.y) ? 16 : 0);
    var bottom = 20 + (lbl(this.opts.axes.x) ? 18 : 0);
    var top = this.opts.title ? 26 : 12;
    var cbar = 64; // colorbar + labels + z title
    return { left: left, right: this.W - cbar, top: top, bottom: this.H - bottom };
  };

  FieldCore.prototype.render = function () {
    if (!this.ctx || !this.view) return;
    var ctx = this.ctx, tok = this._tokens();
    ctx.save(); ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H); ctx.fillStyle = tok.bg; ctx.fillRect(0, 0, this.W, this.H);
    var xt = linTicks(this.view.x[0], this.view.x[1], 8), yt = linTicks(this.view.y[0], this.view.y[1], 8);
    var plot = this._layout(ctx, yt); this.plot = plot;
    if (plot.right <= plot.left || plot.bottom <= plot.top) { ctx.restore(); return; }
    var sx = scale(this.view.x[0], this.view.x[1], plot.left, plot.right);
    var sy = scale(this.view.y[0], this.view.y[1], plot.bottom, plot.top);
    this.sx = sx; this.sy = sy;

    // raster (clipped)
    ctx.save(); ctx.beginPath(); ctx.rect(plot.left, plot.top, plot.right - plot.left, plot.bottom - plot.top); ctx.clip();
    if (this._off) {
      var gx0 = this.full.x[0], gx1 = this.full.x[1], gy0 = this.full.y[0], gy1 = this.full.y[1];
      var srcx = (this.view.x[0] - gx0) / (gx1 - gx0) * this.nx, srcw = (this.view.x[1] - this.view.x[0]) / (gx1 - gx0) * this.nx;
      var srcy = (gy1 - this.view.y[1]) / (gy1 - gy0) * this.ny, srch = (this.view.y[1] - this.view.y[0]) / (gy1 - gy0) * this.ny;
      ctx.imageSmoothingEnabled = true;
      try { ctx.drawImage(this._off, srcx, srcy, srcw, srch, plot.left, plot.top, plot.right - plot.left, plot.bottom - plot.top); } catch (e) {}
    }
    if (this.opts.contours) this._drawContours(ctx, sx, sy, tok);
    if (this.vectors) this._drawArrows(ctx, sx, sy, tok);
    this._drawCrosshair(ctx, plot, tok);
    ctx.restore();

    this._drawAxes(ctx, plot, sx, sy, tok, xt, yt);
    this._drawColorbar(ctx, plot, tok);
    if (this.opts.title) { ctx.fillStyle = tok.fg; ctx.font = "700 13px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(this.opts.title, (plot.left + plot.right) / 2, 4); }
    ctx.restore();
    this._updateHUD();
  };

  FieldCore.prototype._drawArrows = function (ctx, sx, sy, tok) {
    var V = this.vectors; if (!V || !V.u || !V.v) return;
    var vx = V.x || this.x, vy = V.y || this.y, nx = vx.length, ny = vy.length;
    if (!nx || !ny) return;
    var dens = this.opts.arrowDensity || 24;
    var stepX = Math.max(1, Math.round(nx / dens)), stepY = Math.max(1, Math.round(ny / dens));
    var maxm = 0, i, j, u, w, m;
    for (j = 0; j < ny; j++) for (i = 0; i < nx; i++) {
      u = V.u[j] && V.u[j][i]; w = V.v[j] && V.v[j][i];
      if (u == null || w == null || !isFinite(u) || !isFinite(w)) continue;
      m = Math.sqrt(u * u + w * w); if (m > maxm) maxm = m;
    }
    if (maxm <= 0) return;
    var cellpx = Math.abs(sx.to(vx[Math.min(stepX, nx - 1)]) - sx.to(vx[0]));
    var Lpx = (cellpx > 1 ? cellpx : 14) * 0.85, k = Lpx / maxm, span = this.zmax - this.zmin || 1;
    ctx.save(); ctx.lineWidth = 1.2; ctx.lineJoin = "round";
    for (j = 0; j < ny; j += stepY) {
      for (i = 0; i < nx; i += stepX) {
        u = V.u[j] && V.u[j][i]; w = V.v[j] && V.v[j][i];
        if (u == null || w == null || !isFinite(u) || !isFinite(w)) continue;
        var px = sx.to(vx[i]), py = sy.to(vy[j]), tx = px + u * k, ty = py - w * k;
        m = Math.sqrt(u * u + w * w);
        var c = cmap(this.cmapName, (m - this.zmin) / span, this.reverse);
        ctx.strokeStyle = ctx.fillStyle = "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(tx, ty); ctx.stroke();
        var ang = Math.atan2(ty - py, tx - px), hl = Math.min(6, Lpx * 0.45);
        ctx.beginPath(); ctx.moveTo(tx, ty);
        ctx.lineTo(tx - hl * Math.cos(ang - 0.4), ty - hl * Math.sin(ang - 0.4));
        ctx.lineTo(tx - hl * Math.cos(ang + 0.4), ty - hl * Math.sin(ang + 0.4));
        ctx.closePath(); ctx.fill();
      }
    }
    ctx.restore();
  };

  FieldCore.prototype._drawContours = function (ctx, sx, sy, tok) {
    ctx.save(); ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 1;
    if (this.root.getAttribute("data-theme") === "dark") ctx.strokeStyle = "rgba(255,255,255,.4)";
    for (var li = 0; li < this.levels.length; li++) {
      var L = this.levels[li];
      for (var j = 0; j < this.ny - 1; j++) {
        for (var i = 0; i < this.nx - 1; i++) {
          var z00 = this.z[j][i], z10 = this.z[j][i + 1], z11 = this.z[j + 1][i + 1], z01 = this.z[j + 1][i];
          if (z00 == null || z10 == null || z11 == null || z01 == null) continue;
          var pts = [];
          this._edge(pts, this.x[i], this.y[j], z00, this.x[i + 1], this.y[j], z10, L);
          this._edge(pts, this.x[i + 1], this.y[j], z10, this.x[i + 1], this.y[j + 1], z11, L);
          this._edge(pts, this.x[i + 1], this.y[j + 1], z11, this.x[i], this.y[j + 1], z01, L);
          this._edge(pts, this.x[i], this.y[j + 1], z01, this.x[i], this.y[j], z00, L);
          for (var p = 0; p + 1 < pts.length; p += 2) {
            ctx.beginPath();
            ctx.moveTo(sx.to(pts[p][0]), sy.to(pts[p][1]));
            ctx.lineTo(sx.to(pts[p + 1][0]), sy.to(pts[p + 1][1]));
            ctx.stroke();
          }
        }
      }
    }
    ctx.restore();
  };
  FieldCore.prototype._edge = function (pts, xa, ya, va, xb, yb, vb, L) {
    if ((va - L) * (vb - L) < 0) { var t = (L - va) / (vb - va); pts.push([xa + t * (xb - xa), ya + t * (yb - ya)]); }
  };

  FieldCore.prototype._drawAxes = function (ctx, plot, sx, sy, tok, xt, yt) {
    var i, px, py;
    ctx.strokeStyle = tok.grid; ctx.lineWidth = 1;
    for (i = 0; i < xt.vals.length; i++) { px = Math.round(sx.to(xt.vals[i])) + 0.5; if (px < plot.left || px > plot.right) continue; ctx.beginPath(); ctx.moveTo(px, plot.top); ctx.lineTo(px, plot.bottom); ctx.stroke(); }
    for (i = 0; i < yt.vals.length; i++) { py = Math.round(sy.to(yt.vals[i])) + 0.5; if (py < plot.top || py > plot.bottom) continue; ctx.beginPath(); ctx.moveTo(plot.left, py); ctx.lineTo(plot.right, py); ctx.stroke(); }
    ctx.strokeStyle = tok.axis; ctx.strokeRect(plot.left + 0.5, plot.top + 0.5, plot.right - plot.left - 1, plot.bottom - plot.top - 1);
    ctx.fillStyle = tok.sub; ctx.font = "11px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (i = 0; i < xt.vals.length; i++) { px = sx.to(xt.vals[i]); if (px < plot.left - 1 || px > plot.right + 1) continue; ctx.fillText(fmtTick(xt.vals[i], xt.step), px, plot.bottom + 5); }
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (i = 0; i < yt.vals.length; i++) { py = sy.to(yt.vals[i]); if (py < plot.top - 1 || py > plot.bottom + 1) continue; ctx.fillText(fmtTick(yt.vals[i], yt.step), plot.left - 6, py); }
    ctx.fillStyle = tok.fg; ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
    var xT = lbl(this.opts.axes.x), yT = lbl(this.opts.axes.y);
    if (xT) { ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.fillText(xT, (plot.left + plot.right) / 2, this.H - 2); }
    if (yT) { ctx.save(); ctx.translate(10, (plot.top + plot.bottom) / 2); ctx.rotate(-Math.PI / 2); ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(yT, 0, 0); ctx.restore(); }
  };

  FieldCore.prototype._drawColorbar = function (ctx, plot, tok) {
    var bx = plot.right + 14, bw = 14, bt = plot.top, bb = plot.bottom, bh = bb - bt;
    var steps = 64;
    for (var s = 0; s < steps; s++) {
      var t = 1 - s / steps; var c = cmap(this.cmapName, t, this.reverse);
      ctx.fillStyle = "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
      ctx.fillRect(bx, bt + s / steps * bh, bw, bh / steps + 1);
    }
    ctx.strokeStyle = tok.axis; ctx.lineWidth = 1; ctx.strokeRect(bx + 0.5, bt + 0.5, bw, bh);
    ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    var ct = linTicks(this.zmin, this.zmax, 5);
    for (var k = 0; k < ct.vals.length; k++) {
      var vv = ct.vals[k]; if (vv < this.zmin - 1e-9 || vv > this.zmax + 1e-9) continue;
      var yy = bb - (vv - this.zmin) / (this.zmax - this.zmin) * bh;
      ctx.fillText(fmtTick(vv, ct.step), bx + bw + 4, yy);
    }
    var zT = lbl(this.opts.z || { label: "", unit: "" });
    if (zT) { ctx.save(); ctx.fillStyle = tok.fg; ctx.font = "600 11px Segoe UI, system-ui, sans-serif"; ctx.translate(this.W - 4, (bt + bb) / 2); ctx.rotate(-Math.PI / 2); ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(zT, 0, 0); ctx.restore(); }
  };

  FieldCore.prototype._drawCrosshair = function (ctx, plot, tok) {
    var c = this.cursor; if (!c) return;
    ctx.save(); ctx.strokeStyle = tok.axis; ctx.lineWidth = 1; ctx.setLineDash([3, 3]); ctx.globalAlpha = 0.8;
    ctx.beginPath(); ctx.moveTo(c.px, plot.top); ctx.lineTo(c.px, plot.bottom); ctx.moveTo(plot.left, c.py); ctx.lineTo(plot.right, c.py); ctx.stroke();
    ctx.restore();
    if (c.z != null) { ctx.save(); ctx.fillStyle = tok.bg; ctx.strokeStyle = tok.accent; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(c.px, c.py, 4, 0, 6.2832); ctx.fill(); ctx.stroke(); ctx.restore(); }
  };

  FieldCore.prototype._bilinear = function (x, y) {
    if (!this.nx || x < this.full.x[0] || x > this.full.x[1] || y < this.full.y[0] || y > this.full.y[1]) return null;
    var i = bisect(this.x, x), j = bisect(this.y, y);
    var x0 = this.x[i], x1 = this.x[i + 1], y0 = this.y[j], y1 = this.y[j + 1];
    var z00 = this.z[j][i], z10 = this.z[j][i + 1], z01 = this.z[j + 1][i], z11 = this.z[j + 1][i + 1];
    if (z00 == null || z10 == null || z01 == null || z11 == null) return null;
    var tx = x1 === x0 ? 0 : (x - x0) / (x1 - x0), ty = y1 === y0 ? 0 : (y - y0) / (y1 - y0);
    return (z00 * (1 - tx) + z10 * tx) * (1 - ty) + (z01 * (1 - tx) + z11 * tx) * ty;
  };

  FieldCore.prototype._updateHUD = function () {
    if (!this.cursor) { this.hud.style.display = "none"; return; }
    var c = this.cursor, ax = this.opts.axes, z = this.opts.z || {};
    this.hud.style.display = "block";
    this.hud.innerHTML = "<div>" + (ax.x.label || "x") + ": <b>" + fmtVal(c.dataX) + "</b>" + (ax.x.unit ? " " + ax.x.unit : "") + "</div>" +
      "<div>" + (ax.y.label || "y") + ": <b>" + fmtVal(c.dataY) + "</b>" + (ax.y.unit ? " " + ax.y.unit : "") + "</div>" +
      "<div>" + (z.label || "z") + ": <b>" + fmtVal(c.z) + "</b>" + (z.unit ? " " + z.unit : "") + "</div>";
  };

  // ---- events (linear pan/zoom/box) ----
  FieldCore.prototype._bindEvents = function () {
    var self = this, cv = this.canvas;
    cv.addEventListener("pointermove", function (e) { self._onMove(e); });
    cv.addEventListener("pointerdown", function (e) { self._onDown(e); });
    cv.addEventListener("pointerup", function (e) { self._onUp(e); });
    cv.addEventListener("pointerleave", function () { self.cursor = null; self.render(); });
    cv.addEventListener("dblclick", function () { self.autoFit(); });
    cv.addEventListener("wheel", function (e) { self._onWheel(e); }, { passive: false });
  };
  FieldCore.prototype._xy = function (e) { var r = this.canvas.getBoundingClientRect(); return { px: e.clientX - r.left, py: e.clientY - r.top }; };
  FieldCore.prototype._in = function (p) { return this.plot && p.px >= this.plot.left && p.px <= this.plot.right && p.py >= this.plot.top && p.py <= this.plot.bottom; };
  FieldCore.prototype._onMove = function (e) {
    var p = this._xy(e);
    if (this._drag) { return this._onDrag(p); }
    if (!this._in(p)) { this.cursor = null; this.render(); return; }
    var dx = this.sx.inv(p.px), dy = this.sy.inv(p.py);
    this.cursor = { px: p.px, py: p.py, dataX: dx, dataY: dy, z: this._bilinear(dx, dy) };
    this.render();
  };
  FieldCore.prototype._onDown = function (e) {
    var p = this._xy(e); if (!this._in(p)) return; this.canvas.setPointerCapture(e.pointerId); this._moved = false;
    if (e.shiftKey) this._drag = { mode: "box", x0: p.px, y0: p.py, x1: p.px, y1: p.py };
    else this._drag = { mode: "pan", x0: p.px, y0: p.py, vx: this.view.x.slice(), vy: this.view.y.slice() };
  };
  FieldCore.prototype._onDrag = function (p) {
    var ds = this._drag; if (Math.abs(p.px - ds.x0) + Math.abs(p.py - ds.y0) > 3) this._moved = true;
    if (ds.mode === "box") { ds.x1 = p.px; ds.y1 = p.py; this.render(); return; }
    var pw = this.plot.right - this.plot.left, ph = this.plot.bottom - this.plot.top;
    var spanx = ds.vx[1] - ds.vx[0], spany = ds.vy[1] - ds.vy[0];
    var ddx = -(p.px - ds.x0) / pw * spanx, ddy = (p.py - ds.y0) / ph * spany;
    this.view.x = [ds.vx[0] + ddx, ds.vx[1] + ddx]; this.view.y = [ds.vy[0] + ddy, ds.vy[1] + ddy];
    this._clamp(); this.render();
  };
  FieldCore.prototype._onUp = function (e) {
    var ds = this._drag; try { this.canvas.releasePointerCapture(e.pointerId); } catch (_) {}
    if (ds && ds.mode === "box" && this._moved) {
      var x0 = Math.min(ds.x0, ds.x1), x1 = Math.max(ds.x0, ds.x1), y0 = Math.min(ds.y0, ds.y1), y1 = Math.max(ds.y0, ds.y1);
      if (x1 - x0 > 6 && y1 - y0 > 6) { this.view.x = [this.sx.inv(x0), this.sx.inv(x1)]; this.view.y = [this.sy.inv(y1), this.sy.inv(y0)]; this._clamp(); }
    }
    this._drag = null; this.render();
  };
  FieldCore.prototype._zoomHint = function () {
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
  FieldCore.prototype._onWheel = function (e) {
    var p = this._xy(e); if (!this._in(p)) return;
    if (!(e.ctrlKey || e.metaKey)) { this._zoomHint(); return; }   // no embed scroll-trap
    e.preventDefault();
    var f = Math.pow(1.0015, e.deltaY), ax = this.sx.inv(p.px), ay = this.sy.inv(p.py);
    this.view.x = [ax + (this.view.x[0] - ax) * f, ax + (this.view.x[1] - ax) * f];
    this.view.y = [ay + (this.view.y[0] - ay) * f, ay + (this.view.y[1] - ay) * f];
    this._clamp(); this.render();
  };
  FieldCore.prototype._clamp = function () {
    var f = this.full;
    this.view.x[0] = Math.max(f.x[0], Math.min(this.view.x[0], f.x[1]));
    this.view.x[1] = Math.min(f.x[1], Math.max(this.view.x[1], f.x[0]));
    this.view.y[0] = Math.max(f.y[0], Math.min(this.view.y[0], f.y[1]));
    this.view.y[1] = Math.min(f.y[1], Math.max(this.view.y[1], f.y[0]));
    if (this.view.x[1] - this.view.x[0] < (f.x[1] - f.x[0]) * 1e-3) this.view.x = f.x.slice();
    if (this.view.y[1] - this.view.y[0] < (f.y[1] - f.y[0]) * 1e-3) this.view.y = f.y.slice();
  };

  // ---- controls ----
  FieldCore.prototype._buildDOM = function () {
    this.controlbar = el("gs-controlbar"); this.root.appendChild(this.controlbar);
    this.hud = el("gs-hud"); this.hud.style.display = "none"; this.root.appendChild(this.hud);
    var self = this;
    this._btn("↺", "전체 보기", function () { self.autoFit(); });
    this._btn("◐", "테마", function () { var o = ["auto", "light", "dark"], c = self.root.getAttribute("data-theme") || "auto"; self.root.setAttribute("data-theme", o[(o.indexOf(c) + 1) % 3]); self.render(); });
    this._btn("🎨", "컬러맵", function () { self.cmapName = CMAP_ORDER[(CMAP_ORDER.indexOf(self.cmapName) + 1) % CMAP_ORDER.length]; self._rasterize(); self.render(); });
    this._btn("⇄", "컬러맵 반전", function () { self.reverse = !self.reverse; self._rasterize(); self.render(); });
    if ((this.opts.exportButtons || []).indexOf("png") >= 0) this._btn("PNG", "PNG 내보내기", function () { self._png(); });
  };
  FieldCore.prototype._btn = function (label, title, fn) {
    var b = document.createElement("button"); b.className = "gs-btn"; b.type = "button"; b.textContent = label; b.title = title;
    b.addEventListener("click", fn); this.controlbar.appendChild(b); return b;
  };
  FieldCore.prototype._png = function () {
    var off = document.createElement("canvas"); off.width = this.W * 2; off.height = this.H * 2;
    off.getContext("2d").drawImage(this.canvas, 0, 0, off.width, off.height);
    var a = document.createElement("a"); a.href = off.toDataURL("image/png"); a.download = (this.opts.title || "field") + ".png";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };
  FieldCore.prototype.destroy = function () { if (this._ro) this._ro.disconnect(); };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["field-core"] = function (mount, options) { return new FieldCore(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["field-core"] = window.GraphPlugins["field-core"] || {};
})();
