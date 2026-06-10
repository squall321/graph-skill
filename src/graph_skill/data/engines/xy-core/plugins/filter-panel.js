/* filter-panel — interactive FFT-domain filter tuner (the "watch the FFT, drag the cutoff,
   see the time signal change" interaction). Self-contained: includes a small radix-2 FFT and
   applies a low/high/band filter client-side as the slider moves. Shows original + filtered
   in both domains with a time<->freq toggle and a cutoff line on the spectrum.
   config: { fs, t:[time], y:[signal], fc, fc2?, kind, edge, timeAxes, freqAxes, start, colors } */
(function () {
  "use strict";

  function fft(re, im, inv) {
    var n = re.length, i, j = 0, bit, len, k, a, b, xr, xi, wr, wi, nwr, ang, wr0, wi0;
    for (i = 1; i < n; i++) {
      for (bit = n >> 1; j & bit; bit >>= 1) j ^= bit;
      j |= bit;
      if (i < j) { var tr = re[i]; re[i] = re[j]; re[j] = tr; var ti = im[i]; im[i] = im[j]; im[j] = ti; }
    }
    for (len = 2; len <= n; len <<= 1) {
      ang = (inv ? 2 : -2) * Math.PI / len; wr0 = Math.cos(ang); wi0 = Math.sin(ang);
      for (i = 0; i < n; i += len) {
        wr = 1; wi = 0;
        for (k = 0; k < (len >> 1); k++) {
          a = i + k; b = i + k + (len >> 1);
          xr = wr * re[b] - wi * im[b]; xi = wr * im[b] + wi * re[b];
          re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
          nwr = wr * wr0 - wi * wi0; wi = wr * wi0 + wi * wr0; wr = nwr;
        }
      }
    }
    if (inv) for (i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
  }
  function np2(n) { var p = 1; while (p < n) p <<= 1; return p; }
  function maskAt(fk, kind, fc, fc2, edge) {
    function lp(f, c) { var w = Math.max(1e-9, edge * c); if (f <= c - w) return 1; if (f >= c + w) return 0; return 0.5 * (1 + Math.cos(Math.PI * (f - (c - w)) / (2 * w))); }
    if (kind === "high") return 1 - lp(fk, fc);
    if (kind === "band" && fc2 != null) return (1 - lp(fk, fc)) * lp(fk, fc2);
    return lp(fk, fc);
  }
  function filterSignal(y, fs, kind, fc, fc2, edge) {
    var n0 = y.length, n = np2(n0), re = new Array(n), im = new Array(n), i;
    for (i = 0; i < n; i++) { re[i] = i < n0 ? y[i] : 0; im[i] = 0; }
    fft(re, im, false);
    for (i = 0; i < n; i++) { var fk = fs * (i <= n / 2 ? i : n - i) / n; var m = maskAt(fk, kind, fc, fc2, edge); re[i] *= m; im[i] *= m; }
    fft(re, im, true);
    return re.slice(0, n0);
  }
  function ampSpec(y, fs) {
    var n0 = y.length, n = np2(n0), re = new Array(n), im = new Array(n), i;
    for (i = 0; i < n; i++) { re[i] = i < n0 ? y[i] : 0; im[i] = 0; }
    fft(re, im, false);
    var half = n >> 1, f = new Array(half), a = new Array(half);
    for (i = 0; i < half; i++) { f[i] = fs * i / n; var mg = Math.hypot(re[i], im[i]) / n0; a[i] = i === 0 ? mg : mg * 2; }
    return { f: f, a: a };
  }

  function cfgOf(core) { return (core.opts.pluginConfig && core.opts.pluginConfig["filter-panel"]) || null; }

  var P = {
    id: "filter-panel",
    order: 20,
    onInit: function (core) {
      var c = cfgOf(core); if (!c) return;
      var st = core._pstate["filter-panel"] = { domain: c.start || "freq", kind: c.kind || "low", fc: c.fc, fc2: c.fc2 };
      core.root.classList.add("gs-has-fp");           // legend relocates to bottom-right
      var nyq = c.fs / 2;
      var panel = document.createElement("div"); panel.className = "gs-filter-panel";

      var dbtn = document.createElement("button"); dbtn.className = "gs-fp-btn";
      dbtn.textContent = st.domain === "freq" ? "⏱ time" : "FFT →";
      dbtn.addEventListener("click", function () { st.domain = st.domain === "freq" ? "time" : "freq"; dbtn.textContent = st.domain === "freq" ? "⏱ time" : "FFT →"; P._apply(core); });
      panel.appendChild(dbtn);

      var sel = document.createElement("select");
      ["low", "high", "band"].forEach(function (k) { var o = document.createElement("option"); o.value = k; o.textContent = k; if (k === st.kind) o.selected = true; sel.appendChild(o); });
      sel.addEventListener("change", function () { st.kind = sel.value; P._apply(core); });
      panel.appendChild(sel);

      var lab = document.createElement("span"); lab.innerHTML = 'fc <b>' + Math.round(st.fc) + '</b> Hz';
      var sld = document.createElement("input"); sld.type = "range"; sld.min = 1; sld.max = Math.round(nyq); sld.value = Math.round(st.fc); sld.style.width = "120px";
      sld.addEventListener("input", function () { st.fc = +sld.value; lab.innerHTML = 'fc <b>' + st.fc + '</b> Hz'; P._apply(core); });
      panel.appendChild(sld); panel.appendChild(lab);

      core.root.appendChild(panel);
      st._sld = sld; st._lab = lab;
    },

    _apply: function (core) {
      var c = cfgOf(core), st = core._pstate["filter-panel"];
      var filt = filterSignal(c.y, c.fs, st.kind, st.fc, st.fc2, c.edge || 0.15);
      var cols = c.colors || ["#9aa3af", "#2563eb"];
      var series;
      if (st.domain === "freq") {
        var so = ampSpec(c.y, c.fs), sf = ampSpec(filt, c.fs);
        series = [{ name: "original", x: so.f, y: so.a, color: cols[0] }, { name: "filtered", x: sf.f, y: sf.a, color: cols[1] }];
        core.opts.axes = c.freqAxes;
      } else {
        series = [{ name: "original", x: c.t, y: c.y, color: cols[0] }, { name: "filtered", x: c.t, y: filt, color: cols[1] }];
        core.opts.axes = c.timeAxes;
      }
      core.xLog = false; core.yLog = false;
      core.setData(series);
    },

    onDrawOver: function (ctx, view) {
      var st = view.core._pstate["filter-panel"]; if (!st || st.domain !== "freq") return;
      var pl = view.plot;
      function vline(f, lbl) {
        var px = view.scaleX(f); if (px < pl.left || px > pl.left + pl.width) return;
        ctx.save(); ctx.strokeStyle = view.theme.accent; ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]);
        ctx.beginPath(); ctx.moveTo(px, pl.top); ctx.lineTo(px, pl.top + pl.height); ctx.stroke();
        ctx.fillStyle = view.theme.accent; ctx.font = "11px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "top";
        ctx.fillText(lbl, px + 3, pl.top + 3); ctx.restore();
      }
      vline(st.fc, "fc");
      if (st.kind === "band" && st.fc2 != null) vline(st.fc2, "fc2");
    }
  };

  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["filter-panel"] = P;
})();
