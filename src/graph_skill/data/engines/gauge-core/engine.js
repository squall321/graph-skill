/* ===========================================================================
 * gauge-core — single-value KPI indicators (engine family). One artifact holds a
 * responsive GRID of indicators of one kind:
 *   kind "gauge"           : 270° dial with colored bands + needle + center value
 *   kind "radial-progress" : donut ring filled to (value-min)/(max-min) + big center
 *   kind "bullet"          : horizontal qualitative bands + measure bar + target tick
 * Values animate from min on load (cosmetic; artifact stays deterministic). Auto:
 * theme toggle, ▶ replay, PNG export, retina, responsive. window.GraphEngines["gauge-core"].
 * =========================================================================== */
(function () {
  "use strict";
  var TAU = Math.PI * 2;
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function fmt(v, u) {
    if (v == null || (typeof v === "number" && !isFinite(v))) return "—";
    var s = typeof v === "number" ? String(Math.round(v * 1e4) / 1e4) : String(v);
    return u ? s + " " + u : s;
  }
  function heat(t) {                                  // green→yellow→red
    t = clamp(t, 0, 1);
    var st = [[22, 163, 74], [234, 179, 8], [220, 38, 38]], seg = t < 0.5 ? 0 : 1, f = t < 0.5 ? t / 0.5 : (t - 0.5) / 0.5;
    var a = st[seg], b = st[seg + 1];
    return "rgb(" + Math.round(a[0] + (b[0] - a[0]) * f) + "," + Math.round(a[1] + (b[1] - a[1]) * f) + "," + Math.round(a[2] + (b[2] - a[2]) * f) + ")";
  }

  function GaugeCore(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-gauge");
    this.opts = options || {};
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this.dpr = Math.max(1, window.devicePixelRatio || 1);
    this.t = 0;                                        // animation progress 0..1
    this._buildDOM();
    var self = this;
    if (typeof ResizeObserver === "function") {
      this._ro = new ResizeObserver(function () { self._resize(); self._draw(); });
      this._ro.observe(this.stage);
    }
  }
  GaugeCore.prototype.use = function () { return this; };
  GaugeCore.prototype.autoFit = function () { this._resize(); this._draw(); };

  GaugeCore.prototype._buildDOM = function () {
    var self = this;
    var bar = document.createElement("div"); bar.className = "gs-g-toolbar";
    if (this.opts.title) { var ti = document.createElement("div"); ti.className = "gs-g-title"; ti.textContent = this.opts.title; this.root.appendChild(ti); }
    function btn(txt, title, fn) { var b = document.createElement("button"); b.className = "gs-g-btn"; b.textContent = txt; b.title = title; b.addEventListener("click", fn); bar.appendChild(b); return b; }
    btn("▶", "replay", function () { self._animate(); });
    btn("◐", "theme", function () { var o = ["auto", "light", "dark"], c = self.root.getAttribute("data-theme") || "auto"; self.root.setAttribute("data-theme", o[(o.indexOf(c) + 1) % 3]); self._draw(); });
    btn("PNG", "export", function () { self._exportPNG(); });
    this.root.appendChild(bar);
    this.stage = document.createElement("div"); this.stage.className = "gs-g-stage";
    this.canvas = document.createElement("canvas"); this.canvas.className = "gs-g-canvas";
    this.stage.appendChild(this.canvas); this.root.appendChild(this.stage);
    this.ctx = this.canvas.getContext("2d");
  };

  GaugeCore.prototype.setAssets = function (a) {
    this.a = a || {};
    this.kind = this.a.kind || "gauge";
    this.items = (this.a.items || []).map(function (it) {
      var min = it.min != null ? +it.min : 0, max = it.max != null ? +it.max : 100;
      return { label: it.label || "", value: +it.value, min: min, max: max,
        unit: it.unit || "", target: it.target != null ? +it.target : null,
        bands: it.bands || null, goal: it.goal || null, color: it.color || null,
        delta: it.delta != null ? +it.delta : null, spark: it.spark || null };
    });
    this._resize();
    this._animate();
  };

  GaugeCore.prototype._tok = function () {
    var cs = getComputedStyle(this.root);
    function v(n, f) { var x = cs.getPropertyValue(n).trim(); return x || f; }
    return { bg: v("--gs-bg", "#fff"), fg: v("--gs-fg", "#1a1a2e"), sub: v("--gs-sub", "#6b7280"),
      track: v("--gs-track", "#e5e7eb"), accent: v("--gs-accent", "#2563eb") };
  };
  GaugeCore.prototype._resize = function () {
    var w = this.stage.clientWidth || 600, h = this.stage.clientHeight || 360;
    this.canvas.width = Math.round(w * this.dpr); this.canvas.height = Math.round(h * this.dpr);
    this.canvas.style.width = w + "px"; this.canvas.style.height = h + "px";
    this.W = w; this.H = h;
  };

  GaugeCore.prototype._animate = function () {
    var self = this, raf = window.requestAnimationFrame || function (f) { return setTimeout(function () { f(16); }, 16); };
    var reduced = false;
    try { reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
    if (reduced) { this.t = 1; this._draw(); return; }   // no count-up animation
    this.t = 0; var start = null;
    function step(ts) {
      if (self._dead) return;
      if (start == null) start = ts;
      var p = clamp((ts - start) / 650, 0, 1);
      self.t = 1 - Math.pow(1 - p, 3);                 // ease-out cubic
      self._draw();
      if (p < 1) raf(step);
    }
    raf(step);
  };

  GaugeCore.prototype._grid = function (n) {
    var minW = this.kind === "bullet" ? 280 : (this.kind === "card" ? 200 : 200);
    var cols = Math.max(1, Math.min(n, Math.floor(this.W / minW) || 1));
    var rows = Math.ceil(n / cols);
    return { cols: cols, rows: rows, cw: this.W / cols, ch: this.H / rows };
  };

  GaugeCore.prototype._draw = function () {
    if (!this.ctx || !this.items) return;
    var ctx = this.ctx, tok = this._tok();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H);
    var g = this._grid(this.items.length);
    for (var i = 0; i < this.items.length; i++) {
      var cx = (i % g.cols) * g.cw, cy = Math.floor(i / g.cols) * g.ch;
      ctx.save(); ctx.translate(cx, cy);
      if (this.kind === "radial-progress") this._ring(ctx, tok, this.items[i], g.cw, g.ch);
      else if (this.kind === "bullet") this._bullet(ctx, tok, this.items[i], g.cw, g.ch);
      else if (this.kind === "card") this._statcard(ctx, tok, this.items[i], g.cw, g.ch);
      else this._gauge(ctx, tok, this.items[i], g.cw, g.ch);
      ctx.restore();
    }
  };

  GaugeCore.prototype._frac = function (it) {
    var f = (it.max > it.min) ? (it.value - it.min) / (it.max - it.min) : 0;
    return clamp(f, 0, 1) * this.t;
  };
  GaugeCore.prototype._bandColor = function (it, f) {
    if (it.color) return it.color;
    if (it.bands) { for (var b = 0; b < it.bands.length; b++) { var to = (it.bands[b].to - it.min) / (it.max - it.min); if (f <= to) return it.bands[b].color; } return it.bands[it.bands.length - 1].color; }
    var h = it.goal === "low" ? f : (it.goal === "high" ? 1 - f : 0);
    return it.goal ? heat(h) : "var";
  };

  GaugeCore.prototype._gauge = function (ctx, tok, it, cw, ch) {
    var cx = cw / 2, cy = ch * 0.58, r = Math.min(cw, ch) * 0.36;
    var a0 = Math.PI * 0.75, sweep = Math.PI * 1.5, f = this._frac(it);
    // track
    ctx.lineWidth = Math.max(7, r * 0.18); ctx.lineCap = "round";
    ctx.strokeStyle = tok.track; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + sweep); ctx.stroke();
    // bands (if any) along full range
    if (it.bands) {
      var prev = 0;
      for (var b = 0; b < it.bands.length; b++) {
        var to = clamp((it.bands[b].to - it.min) / (it.max - it.min), 0, 1);
        ctx.strokeStyle = it.bands[b].color; ctx.beginPath();
        ctx.arc(cx, cy, r, a0 + prev * sweep, a0 + to * sweep); ctx.stroke(); prev = to;
      }
    }
    // value arc
    var col = this._bandColor(it, (it.max > it.min) ? clamp((it.value - it.min) / (it.max - it.min), 0, 1) : 0);
    if (col === "var") col = it.color || tok.accent;
    if (!it.bands) { ctx.strokeStyle = col; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + f * sweep); ctx.stroke(); }
    // needle
    var ang = a0 + f * sweep;
    ctx.strokeStyle = tok.fg; ctx.lineWidth = Math.max(2, r * 0.04); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ang) * r * 0.92, cy + Math.sin(ang) * r * 0.92); ctx.stroke();
    ctx.fillStyle = tok.fg; ctx.beginPath(); ctx.arc(cx, cy, Math.max(3, r * 0.07), 0, TAU); ctx.fill();
    // target tick
    if (it.target != null) {
      var tf = clamp((it.target - it.min) / (it.max - it.min), 0, 1), ta = a0 + tf * sweep;
      ctx.strokeStyle = tok.fg; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(ta) * (r - r * 0.13), cy + Math.sin(ta) * (r - r * 0.13));
      ctx.lineTo(cx + Math.cos(ta) * (r + r * 0.13), cy + Math.sin(ta) * (r + r * 0.13)); ctx.stroke();
    }
    // center value + label
    ctx.fillStyle = tok.fg; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "700 " + Math.round(r * 0.42) + "px Segoe UI, system-ui, sans-serif";
    ctx.fillText(fmt(Math.round((it.min + (it.value - it.min) * this.t) * 100) / 100, it.unit), cx, cy + r * 0.34);
    ctx.fillStyle = tok.sub; ctx.font = "600 " + Math.round(Math.min(15, r * 0.22)) + "px Segoe UI, system-ui, sans-serif";
    ctx.fillText(it.label, cx, cy - r * 0.55);
  };

  GaugeCore.prototype._ring = function (ctx, tok, it, cw, ch) {
    var cx = cw / 2, cy = ch * 0.52, r = Math.min(cw, ch) * 0.34, lw = Math.max(8, r * 0.26);
    var f = this._frac(it), top = -Math.PI / 2;
    ctx.lineWidth = lw; ctx.lineCap = "round";
    ctx.strokeStyle = tok.track; ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.stroke();
    var col = this._bandColor(it, (it.max > it.min) ? clamp((it.value - it.min) / (it.max - it.min), 0, 1) : 0);
    if (col === "var") col = it.color || tok.accent;
    ctx.strokeStyle = col; ctx.beginPath(); ctx.arc(cx, cy, r, top, top + f * TAU); ctx.stroke();
    ctx.fillStyle = tok.fg; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "700 " + Math.round(r * 0.5) + "px Segoe UI, system-ui, sans-serif";
    var disp = it.unit === "%" ? Math.round(f / this.t * 100 * (this.t || 1)) : Math.round((it.min + (it.value - it.min) * this.t) * 100) / 100;
    var shown = it.unit === "%" ? Math.round(((it.value - it.min) / (it.max - it.min)) * 100 * this.t) + "%" : fmt(disp, it.unit);
    ctx.fillText(shown, cx, cy);
    ctx.fillStyle = tok.sub; ctx.font = "600 " + Math.round(Math.min(15, r * 0.26)) + "px Segoe UI, system-ui, sans-serif";
    ctx.fillText(it.label, cx, cy + r + lw * 0.4 + 10);
  };

  GaugeCore.prototype._bullet = function (ctx, tok, it, cw, ch) {
    var pad = 16, x = pad, w = cw - 2 * pad, cy = ch * 0.6, h = Math.min(26, ch * 0.22);
    // label + value
    ctx.fillStyle = tok.fg; ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.font = "600 13px Segoe UI, system-ui, sans-serif"; ctx.fillText(it.label, x, cy - h);
    ctx.textAlign = "right"; ctx.fillText(fmt(Math.round((it.min + (it.value - it.min) * this.t) * 100) / 100, it.unit), x + w, cy - h);
    // qualitative bands
    if (it.bands) {
      var prev = it.min;
      for (var b = 0; b < it.bands.length; b++) {
        var x0 = x + clamp((prev - it.min) / (it.max - it.min), 0, 1) * w;
        var x1 = x + clamp((it.bands[b].to - it.min) / (it.max - it.min), 0, 1) * w;
        ctx.fillStyle = it.bands[b].color; ctx.fillRect(x0, cy - h / 2, x1 - x0, h); prev = it.bands[b].to;
      }
    } else { ctx.fillStyle = tok.track; ctx.fillRect(x, cy - h / 2, w, h); }
    // measure bar
    var f = this._frac(it), col = it.color || tok.accent;
    ctx.fillStyle = col; ctx.fillRect(x, cy - h / 4, f * w, h / 2);
    // target tick
    if (it.target != null) {
      var tx = x + clamp((it.target - it.min) / (it.max - it.min), 0, 1) * w;
      ctx.strokeStyle = tok.fg; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(tx, cy - h * 0.75); ctx.lineTo(tx, cy + h * 0.75); ctx.stroke();
    }
  };

  GaugeCore.prototype._statcard = function (ctx, tok, it, cw, ch) {
    var pad = 16, x = pad, y = pad, w = cw - 2 * pad, h = ch - 2 * pad;
    // card panel
    ctx.fillStyle = tok.bg; ctx.strokeStyle = tok.track; ctx.lineWidth = 1;
    if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(x, y, w, h, 10); ctx.fill(); ctx.stroke(); }
    else { ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h); }
    // label
    ctx.fillStyle = tok.sub; ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.font = "600 12px Segoe UI, system-ui, sans-serif"; ctx.fillText(it.label, x + 14, y + 12);
    // big value (count-up)
    var shown = it.min + (it.value - it.min) * this.t;
    ctx.fillStyle = tok.fg; ctx.font = "700 " + Math.round(Math.min(36, h * 0.34)) + "px Segoe UI, system-ui, sans-serif";
    ctx.textBaseline = "alphabetic"; ctx.fillText(fmt(Math.round(shown * 100) / 100, it.unit), x + 14, y + h * 0.5);
    // delta arrow
    if (it.delta != null) {
      var good = it.goal === "low" ? it.delta < 0 : it.goal === "high" ? it.delta > 0 : null;
      ctx.fillStyle = good == null ? tok.sub : (good ? "#16a34a" : "#dc2626");
      ctx.font = "600 13px Segoe UI, system-ui, sans-serif";
      ctx.fillText((it.delta > 0 ? "▲" : it.delta < 0 ? "▼" : "•") + " " + fmt(Math.abs(Math.round(it.delta * 100) / 100), ""),
        x + 14, y + h * 0.5 + 22);
    }
    // sparkline (bottom)
    if (it.spark && it.spark.length > 1) {
      var sp = it.spark, mn = Math.min.apply(null, sp), mx = Math.max.apply(null, sp), rng = (mx - mn) || 1;
      var sx = x + 14, sw = w - 28, sy = y + h - 16, sh = Math.min(28, h * 0.26);
      ctx.strokeStyle = it.color || tok.accent; ctx.lineWidth = 1.6; ctx.lineJoin = "round"; ctx.beginPath();
      for (var k = 0; k < sp.length; k++) {
        var px = sx + sw * k / (sp.length - 1), py = sy - (sp[k] - mn) / rng * sh;
        if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
  };

  GaugeCore.prototype._exportPNG = function () {
    var url = this.canvas.toDataURL("image/png");
    var a = document.createElement("a"); a.href = url; a.download = (this.opts.title || "gauge") + ".png";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };
  GaugeCore.prototype.destroy = function () { this._dead = true; if (this._ro) this._ro.disconnect(); };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["gauge-core"] = function (mount, options) { return new GaugeCore(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["gauge-core"] = window.GraphPlugins["gauge-core"] || {};
})();
