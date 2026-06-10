/* ===========================================================================
 * polar-core — angle/radius 2D engine family. Renders polar plots (radiation patterns,
 * directivity) and radar/spider charts (categories as evenly-spaced spokes).
 * Series: { name, theta:[deg], r:[value], color?, closed? }. θ=0 at top, clockwise.
 * Dispatched via window.GraphEngines["polar-core"].
 * =========================================================================== */
(function () {
  "use strict";
  var PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#777777", "#000000"];
  var DEFAULTS = { radius: { label: "", unit: "" }, thetaStep: 30, theme: "auto", title: "",
                   exportButtons: ["png"], legend: { show: true } };
  var D2R = Math.PI / 180;

  function deepMerge(b, o) {
    var out = {}; for (var k in b) if (b.hasOwnProperty(k)) out[k] = b[k];
    if (!o) return out;
    for (var j in o) { if (!o.hasOwnProperty(j)) continue; var v = o[j];
      out[j] = (v && typeof v === "object" && !Array.isArray(v) && b[j] && typeof b[j] === "object") ? deepMerge(b[j], v) : v; }
    return out;
  }
  function el(c) { var d = document.createElement("div"); if (c) d.className = c; return d; }
  function fmtVal(v) { if (v == null || !isFinite(v)) return "—"; var a = Math.abs(v); if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(2); return String(Math.round(v * 1e4) / 1e4); }
  function niceNum(x, round) { if (!(x > 0)) return 1; var e = Math.floor(Math.log10(x)), f = x / Math.pow(10, e), nf; if (round) nf = f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10; else nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10; return nf * Math.pow(10, e); }
  function rTicks(lo, hi) { if (!(hi > lo)) hi = lo + 1; var step = niceNum((hi - lo) / 5, true), out = []; for (var v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) out.push(v); return out; }

  function PolarCore(mount, options) {
    this.root = mount; this.root.classList.add("gs-root");
    this.opts = deepMerge(DEFAULTS, options || {});
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this.canvas = document.createElement("canvas"); this.root.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.series = []; this.cursor = null;
    this._buildDOM(); this._bind();
    var self = this; this._ro = new ResizeObserver(function () { self._resize(); }); this._ro.observe(this.root);
    this._resize();
  }
  PolarCore.prototype.use = function () { return this; };
  PolarCore.prototype.autoFit = function () { this.render(); };
  PolarCore.prototype.setData = function (s) { this.setAssets({ series: s }); };
  PolarCore.prototype.setAssets = function (a) {
    var ser = (a && a.series) || [];
    this.series = ser.map(function (s, i) {
      return { name: s.name || ("series " + (i + 1)), theta: s.theta || [], r: s.r || [],
               closed: !!s.closed, _color: s.color || PALETTE[i % PALETTE.length] };
    });
    var lo = Infinity, hi = -Infinity;
    for (var k = 0; k < this.series.length; k++) for (var j = 0; j < this.series[k].r.length; j++) {
      var v = this.series[k].r[j]; if (v == null || !isFinite(v)) continue; if (v < lo) lo = v; if (v > hi) hi = v;
    }
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (this.opts.angleLabels) lo = Math.min(lo, 0); // radar from 0
    if (this.opts.rmin != null) lo = this.opts.rmin;
    if (this.opts.rmax != null) hi = this.opts.rmax;
    this.rmin = lo; this.rmax = hi === lo ? lo + 1 : hi;
    this.rose = (a && a.rose) || null;            // wind-rose: {directions:[deg], bins:[{label,counts[],color?}]}
    if (this.rose && this.rose.directions && this.rose.bins) {
      var rmx = 0, nd = this.rose.directions.length, bi, di, sum;
      for (di = 0; di < nd; di++) {
        sum = 0;
        for (bi = 0; bi < this.rose.bins.length; bi++) sum += (this.rose.bins[bi].counts[di] || 0);
        if (sum > rmx) rmx = sum;
      }
      this.rmin = 0; this.rmax = this.opts.rmax != null ? this.opts.rmax : (rmx || 1);
    }
    this._buildLegend(); this.render();
  };

  PolarCore.prototype._resize = function () {
    var r = this.root.getBoundingClientRect();
    var w = Math.max(160, Math.floor(r.width || 400)), h = Math.max(160, Math.floor(r.height || 400));
    this.dpr = Math.max(1, window.devicePixelRatio || 1);
    this.canvas.width = Math.round(w * this.dpr); this.canvas.height = Math.round(h * this.dpr);
    this.canvas.style.width = w + "px"; this.canvas.style.height = h + "px";
    this.W = w; this.H = h; this.render();
  };
  PolarCore.prototype._tokens = function () {
    var cs = getComputedStyle(this.root); function v(n, f) { var x = cs.getPropertyValue(n).trim(); return x || f; }
    return { bg: v("--gs-bg", "#fff"), fg: v("--gs-fg", "#1a1a2e"), sub: v("--gs-sub", "#6b7280"), grid: v("--gs-grid", "#e3e7ec"), axis: v("--gs-axis", "#9aa3af"), accent: v("--gs-accent", "#2563eb") };
  };
  PolarCore.prototype._radius = function (v) { return (v - this.rmin) / (this.rmax - this.rmin) * this.R; };
  PolarCore.prototype._pt = function (theta, r) { var a = (90 - theta) * D2R, rr = this._radius(r); return { px: this.cx + rr * Math.cos(a), py: this.cy - rr * Math.sin(a) }; };

  PolarCore.prototype.render = function () {
    if (!this.ctx) return;
    var ctx = this.ctx, tok = this._tokens();
    ctx.save(); ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H); ctx.fillStyle = tok.bg; ctx.fillRect(0, 0, this.W, this.H);
    var top = this.opts.title ? 24 : 8;
    this.cx = this.W / 2; this.cy = top + (this.H - top) / 2;
    this.R = Math.min(this.W, this.H - top) / 2 - 34;
    if (this.R < 10) { ctx.restore(); return; }

    // radius rings + labels
    var rt = rTicks(this.rmin, this.rmax);
    ctx.strokeStyle = tok.grid; ctx.fillStyle = tok.sub; ctx.lineWidth = 1; ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    for (var i = 0; i < rt.length; i++) {
      var rr = this._radius(rt[i]); if (rr < 0 || rr > this.R + 0.5) continue;
      ctx.beginPath(); ctx.arc(this.cx, this.cy, rr, 0, 6.2832); ctx.stroke();
      ctx.fillText(fmtVal(rt[i]), this.cx + 3, this.cy - rr);
    }
    // spokes + angle labels
    ctx.strokeStyle = tok.grid; ctx.fillStyle = tok.sub; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    var labels = this.opts.angleLabels, n = labels ? labels.length : Math.round(360 / (this.opts.thetaStep || 30));
    for (var k = 0; k < n; k++) {
      var th = labels ? (k * 360 / n) : (k * (this.opts.thetaStep || 30));
      var a = (90 - th) * D2R;
      ctx.beginPath(); ctx.moveTo(this.cx, this.cy); ctx.lineTo(this.cx + this.R * Math.cos(a), this.cy - this.R * Math.sin(a)); ctx.stroke();
      var lx = this.cx + (this.R + 14) * Math.cos(a), ly = this.cy - (this.R + 14) * Math.sin(a);
      ctx.fillStyle = tok.fg; ctx.fillText(labels ? String(labels[k]) : (th + "°"), lx, ly); ctx.fillStyle = tok.sub;
    }
    // series
    for (var s = 0; s < this.series.length; s++) {
      var se = this.series[s]; ctx.strokeStyle = se._color; ctx.fillStyle = se._color; ctx.lineWidth = 2; ctx.beginPath();
      var started = false, first = null;
      for (var j = 0; j < se.theta.length; j++) {
        var v2 = se.r[j]; if (v2 == null || !isFinite(v2)) { started = false; continue; }
        var p = this._pt(se.theta[j], v2);
        if (!started) { ctx.moveTo(p.px, p.py); started = true; if (!first) first = p; } else ctx.lineTo(p.px, p.py);
      }
      if (se.closed && first) ctx.closePath();
      ctx.stroke();
      if (this.opts.angleLabels) { ctx.globalAlpha = 0.12; ctx.fill(); ctx.globalAlpha = 1; }
    }
    if (this.rose) this._drawRose(ctx, tok);
    // cursor dot
    if (this.cursor) { ctx.fillStyle = tok.accent; ctx.strokeStyle = tok.bg; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(this.cursor.px, this.cursor.py, 4, 0, 6.2832); ctx.fill(); ctx.stroke(); }
    if (this.opts.title) { ctx.fillStyle = tok.fg; ctx.font = "700 13px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(this.opts.title, this.cx, 4); }
    ctx.restore(); this._updateHUD();
  };

  PolarCore.prototype._drawRose = function (ctx, tok) {
    var dirs = this.rose.directions, bins = this.rose.bins, nd = dirs.length;
    var pal = ["#2563eb", "#0891b2", "#059669", "#ca8a04", "#dc2626", "#9333ea"];
    var w = (360 / nd) * 0.86, N = 6, di, bi, k;
    ctx.save();
    ctx.lineWidth = 1; ctx.strokeStyle = tok.bg;
    for (di = 0; di < nd; di++) {
      var c = dirs[di], t0 = c - w / 2, t1 = c + w / 2, base = 0;
      for (bi = 0; bi < bins.length; bi++) {
        var cnt = bins[bi].counts[di] || 0;
        if (cnt <= 0) continue;
        var rin = base, rout = base + cnt;
        ctx.fillStyle = bins[bi].color || pal[bi % pal.length];
        ctx.beginPath();
        for (k = 0; k <= N; k++) { var p = this._pt(t0 + (t1 - t0) * k / N, rout); if (k === 0) ctx.moveTo(p.px, p.py); else ctx.lineTo(p.px, p.py); }
        for (k = N; k >= 0; k--) { var q = this._pt(t0 + (t1 - t0) * k / N, rin); ctx.lineTo(q.px, q.py); }
        ctx.closePath(); ctx.fill(); ctx.stroke();
        base = rout;
      }
    }
    // legend (speed bins) — top-left
    ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    for (bi = 0; bi < bins.length; bi++) {
      var ly = 12 + bi * 14;
      ctx.fillStyle = bins[bi].color || pal[bi % pal.length];
      ctx.fillRect(8, ly - 4, 10, 10);
      ctx.fillStyle = tok.fg; ctx.fillText(String(bins[bi].label || ("bin " + (bi + 1))), 22, ly);
    }
    ctx.restore();
  };

  PolarCore.prototype._updateHUD = function () {
    if (!this.cursor) { this.hud.style.display = "none"; return; }
    var c = this.cursor, rad = this.opts.radius || {};
    this.hud.style.display = "block";
    this.hud.innerHTML = "<div>θ: <b>" + fmtVal(c.theta) + "</b>°</div><div>" + (rad.label || "r") + ": <b>" + fmtVal(c.r) + "</b>" + (rad.unit ? " " + rad.unit : "") + "</div>" + (c.name ? "<div>" + c.name + "</div>" : "");
  };

  PolarCore.prototype._bind = function () {
    var self = this, cv = this.canvas;
    cv.addEventListener("pointermove", function (e) {
      var r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, best = null, bd = 400;
      for (var s = 0; s < self.series.length; s++) { var se = self.series[s];
        for (var j = 0; j < se.theta.length; j++) { var v = se.r[j]; if (v == null || !isFinite(v)) continue;
          var p = self._pt(se.theta[j], v), d = (p.px - mx) * (p.px - mx) + (p.py - my) * (p.py - my);
          if (d < bd) { bd = d; best = { px: p.px, py: p.py, theta: se.theta[j], r: v, name: se.name }; } } }
      self.cursor = best; self.render();
    });
    cv.addEventListener("pointerleave", function () { self.cursor = null; self.render(); });
  };

  PolarCore.prototype._buildDOM = function () {
    this.controlbar = el("gs-controlbar"); this.root.appendChild(this.controlbar);
    this.hud = el("gs-hud"); this.hud.style.display = "none"; this.root.appendChild(this.hud);
    if (this.opts.legend.show) { this.legend = el("gs-legend"); this.root.appendChild(this.legend); }
    var self = this;
    this._btn("◐", "테마", function () { var o = ["auto", "light", "dark"], c = self.root.getAttribute("data-theme") || "auto"; self.root.setAttribute("data-theme", o[(o.indexOf(c) + 1) % 3]); self.render(); });
    if ((this.opts.exportButtons || []).indexOf("png") >= 0) this._btn("PNG", "PNG", function () { self._png(); });
  };
  PolarCore.prototype._btn = function (label, title, fn) { var b = document.createElement("button"); b.className = "gs-btn"; b.type = "button"; b.textContent = label; b.title = title; b.addEventListener("click", fn); this.controlbar.appendChild(b); };
  PolarCore.prototype._buildLegend = function () {
    if (!this.legend) return; this.legend.innerHTML = "";
    this.series.forEach(function (s) { var it = el("gs-legend-item"); var sw = el("gs-sw"); sw.style.background = s._color; it.appendChild(sw); var nm = document.createElement("span"); nm.textContent = s.name; it.appendChild(nm); this.legend.appendChild(it); }, this);
  };
  PolarCore.prototype._png = function () { var off = document.createElement("canvas"); off.width = this.W * 2; off.height = this.H * 2; off.getContext("2d").drawImage(this.canvas, 0, 0, off.width, off.height); var a = document.createElement("a"); a.href = off.toDataURL("image/png"); a.download = (this.opts.title || "polar") + ".png"; document.body.appendChild(a); a.click(); document.body.removeChild(a); };
  PolarCore.prototype.destroy = function () { if (this._ro) this._ro.disconnect(); };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["polar-core"] = function (mount, options) { return new PolarCore(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {}; window.GraphPlugins["polar-core"] = window.GraphPlugins["polar-core"] || {};
})();
