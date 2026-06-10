/* smith-core — Smith chart engine family (RF impedance). Plots reflection coefficient Γ
   inside the unit circle with constant-R and constant-X grid (Möbius z=(1+Γ)/(1-Γ)), and
   overlays S11 trajectories. Hover reports z=R+jX, |Γ|, return loss. Self-contained Canvas. */
(function () {
  "use strict";
  var PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"];
  function el(cls) { var d = document.createElement("div"); d.className = cls; return d; }
  function fmt(v) { if (v == null || !isFinite(v)) return "–"; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-3)) ? v.toExponential(2) : (Math.round(v * 1000) / 1000).toString(); }

  function SmithCore(mount, options) {
    this.root = mount; this.root.classList.add("gs-smith-root");
    this.opts = options || {}; this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this.canvas = document.createElement("canvas"); this.root.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.series = []; this.cursor = null;
    this.hud = el("gs-smith-hud"); this.hud.style.display = "none"; this.root.appendChild(this.hud);
    var self = this;
    this.canvas.addEventListener("pointermove", function (e) { self._onMove(e); });
    this.canvas.addEventListener("pointerleave", function () { self.cursor = null; self.render(); });
    this._ro = new ResizeObserver(function () { self._resize(); }); this._ro.observe(this.root);
    this._buildBar();
    this._resize();
  }
  SmithCore.prototype._buildBar = function () {
    var self = this, bar = el("gs-smith-bar");
    function btn(txt, title, fn) {
      var b = document.createElement("button");
      b.className = "gs-smith-btn"; b.type = "button"; b.textContent = txt; b.title = title;
      b.setAttribute("aria-label", title);
      b.addEventListener("click", fn); bar.appendChild(b); return b;
    }
    btn("◐", "테마 (자동/밝게/어둡게)", function () {
      var o = ["auto", "light", "dark"], cur = self.root.getAttribute("data-theme") || "auto";
      self.root.setAttribute("data-theme", o[(o.indexOf(cur) + 1) % 3]);
      self.render();
    });
    btn("PNG", "PNG 내보내기", function () {
      var a2 = document.createElement("a");
      a2.href = self.canvas.toDataURL("image/png");
      a2.download = "smith-chart.png";
      document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    });
    btn("{}", "graph-config JSON 내보내기", function () {
      var node = document.getElementById("graph-config");
      var txt = node ? node.textContent : JSON.stringify({ engine: "smith-core", series: self.series });
      var a2 = document.createElement("a");
      a2.href = "data:application/json;charset=utf-8," + encodeURIComponent(txt);
      a2.download = "smith-chart.json";
      document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    });
    this.root.appendChild(bar);
  };
  SmithCore.prototype.use = function () { return this; };
  SmithCore.prototype.setData = function (s) { this.setAssets({ series: s }); };
  SmithCore.prototype.setAssets = function (a) {
    var ser = (a && a.series) || [];
    this.series = ser.map(function (s, i) {
      return { name: s.name || ("S11 " + (i + 1)), gamma: s.gamma || [], _color: s.color || PALETTE[i % PALETTE.length] };
    });
    this.render();
  };
  SmithCore.prototype.autoFit = function () { this.cursor = null; this.render(); };
  SmithCore.prototype._resize = function () {
    var r = this.root.getBoundingClientRect();
    var w = Math.max(160, Math.floor(r.width || 400)), h = Math.max(160, Math.floor(r.height || 400));
    this.dpr = Math.max(1, window.devicePixelRatio || 1);
    this.canvas.width = Math.round(w * this.dpr); this.canvas.height = Math.round(h * this.dpr);
    this.canvas.style.width = w + "px"; this.canvas.style.height = h + "px";
    this.W = w; this.H = h; this.render();
  };
  SmithCore.prototype._tokens = function () {
    var cs = getComputedStyle(this.root); function v(n, f) { var x = cs.getPropertyValue(n).trim(); return x || f; }
    return { bg: v("--gs-bg", "#fff"), fg: v("--gs-fg", "#1a1a2e"), sub: v("--gs-sub", "#6b7280"), grid: v("--gs-grid", "#e3e7ec"), accent: v("--gs-accent", "#2563eb") };
  };
  SmithCore.prototype._px = function (re, im) { return { px: this.cx + re * this.R, py: this.cy - im * this.R }; };

  SmithCore.prototype.render = function () {
    if (!this.ctx) return;
    var ctx = this.ctx, tok = this._tokens();
    ctx.save(); ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H); ctx.fillStyle = tok.bg; ctx.fillRect(0, 0, this.W, this.H);
    var top = this.opts.title ? 24 : 8;
    this.cx = this.W / 2; this.cy = top + (this.H - top) / 2;
    this.R = Math.min(this.W, this.H - top) / 2 - 16;
    if (this.R < 10) { ctx.restore(); return; }
    var c0 = this._px(0, 0);
    // clip everything to the unit circle
    ctx.save();
    ctx.beginPath(); ctx.arc(c0.px, c0.py, this.R, 0, 6.2832); ctx.clip();
    ctx.strokeStyle = tok.grid; ctx.lineWidth = 1;
    // constant-R circles
    var Rs = [0.2, 0.5, 1, 2, 5], i;
    for (i = 0; i < Rs.length; i++) {
      var rr = Rs[i], gc = rr / (1 + rr), grad = 1 / (1 + rr);
      ctx.beginPath(); ctx.arc(this.cx + gc * this.R, this.cy, grad * this.R, 0, 6.2832); ctx.stroke();
    }
    // constant-X arcs (±)
    var Xs = [0.2, 0.5, 1, 2, 5];
    for (i = 0; i < Xs.length; i++) {
      for (var sgn = -1; sgn <= 1; sgn += 2) {
        var X = sgn * Xs[i], cyx = 1 / X, radx = 1 / Math.abs(X);
        var pc = this._px(1, cyx);
        ctx.beginPath(); ctx.arc(pc.px, pc.py, radx * this.R, 0, 6.2832); ctx.stroke();
      }
    }
    ctx.restore();
    // outer unit circle + real axis
    ctx.strokeStyle = tok.sub; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.arc(c0.px, c0.py, this.R, 0, 6.2832); ctx.stroke();
    ctx.strokeStyle = tok.grid;
    ctx.beginPath(); ctx.moveTo(c0.px - this.R, c0.py); ctx.lineTo(c0.px + this.R, c0.py); ctx.stroke();
    // R labels on real axis
    ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top";
    var labelR = [0, 0.5, 1, 2, 5];
    for (i = 0; i < labelR.length; i++) {
      var g = (labelR[i] - 1) / (labelR[i] + 1), p = this._px(g, 0);
      ctx.fillText(String(labelR[i]), p.px, this.cy + 3);
    }
    // series (Γ trajectories)
    for (var s = 0; s < this.series.length; s++) {
      var se = this.series[s], gm = se.gamma;
      ctx.strokeStyle = se._color; ctx.fillStyle = se._color; ctx.lineWidth = 2; ctx.beginPath();
      var started = false;
      for (var k = 0; k < gm.length; k++) {
        var pt = this._px(gm[k][0], gm[k][1]);
        if (!started) { ctx.moveTo(pt.px, pt.py); started = true; } else ctx.lineTo(pt.px, pt.py);
      }
      ctx.stroke();
      for (k = 0; k < gm.length; k++) { var d = this._px(gm[k][0], gm[k][1]); ctx.beginPath(); ctx.arc(d.px, d.py, 2.4, 0, 6.2832); ctx.fill(); }
    }
    if (this.cursor) { ctx.fillStyle = tok.accent; ctx.strokeStyle = tok.bg; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(this.cursor.px, this.cursor.py, 4, 0, 6.2832); ctx.fill(); ctx.stroke(); }
    if (this.opts.title) { ctx.fillStyle = tok.fg; ctx.font = "700 13px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(this.opts.title, this.cx, 4); }
    ctx.restore();
    this._updateHUD();
  };

  SmithCore.prototype._onMove = function (e) {
    var r = this.canvas.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
    var best = null, bd = 400;
    for (var s = 0; s < this.series.length; s++) {
      var gm = this.series[s].gamma;
      for (var k = 0; k < gm.length; k++) {
        var p = this._px(gm[k][0], gm[k][1]), dd = (p.px - mx) * (p.px - mx) + (p.py - my) * (p.py - my);
        if (dd < bd) { bd = dd; best = { px: p.px, py: p.py, re: gm[k][0], im: gm[k][1], name: this.series[s].name }; }
      }
    }
    this.cursor = best; this.render();
  };
  SmithCore.prototype._updateHUD = function () {
    if (!this.cursor) { this.hud.style.display = "none"; return; }
    var c = this.cursor, re = c.re, im = c.im;
    var den = (1 - re) * (1 - re) + im * im;       // z = (1+Γ)/(1-Γ)
    var zr = (1 - re * re - im * im) / den, zx = (2 * im) / den;
    var mag = Math.sqrt(re * re + im * im), rl = mag > 0 ? -20 * Math.log10(mag) : Infinity;
    this.hud.innerHTML = "<b>" + c.name + "</b><br>z = " + fmt(zr) + (zx >= 0 ? " + j" : " − j") + fmt(Math.abs(zx))
      + "<br>|Γ| = " + fmt(mag) + " · RL " + (isFinite(rl) ? fmt(rl) + " dB" : "∞");
    this.hud.style.display = "block";
  };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["smith-core"] = function (mount, options) { return new SmithCore(mount, options); };
})();
