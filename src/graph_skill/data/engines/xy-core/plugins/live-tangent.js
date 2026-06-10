/* live-tangent — hover tangent line + local slope readout. Recipe re-labels the slope per
   domain: stress-strain Et[GPa], force-disp stiffness[N/mm], thermal CTE[ppm/°C], creep rate.
   config: { label:"Et", unit:"GPa", scale:1, seriesIndex:0, colorByMag:true, refSlope? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["live-tangent"]) || {}; }

  function slopeAt(s, x) {
    // nearest index (skip gaps), central difference in data space
    var best = -1, bd = Infinity, i;
    for (i = 0; i < s.x.length; i++) {
      if (s.y[i] == null) continue;
      var d = Math.abs(s.x[i] - x);
      if (d < bd) { bd = d; best = i; }
    }
    if (best < 0) return null;
    var lo = best, hi = best;
    while (lo > 0 && s.y[lo - 1] == null) lo--;
    if (lo > 0) lo--;
    while (hi < s.x.length - 1 && s.y[hi + 1] == null) hi++;
    if (hi < s.x.length - 1) hi++;
    if (hi === lo || s.y[lo] == null || s.y[hi] == null) return null;
    var dx = s.x[hi] - s.x[lo];
    if (!dx) return null;
    return { m: (s.y[hi] - s.y[lo]) / dx, x0: s.x[best], y0: s.y[best] };
  }

  function color(view, m, c) {
    if (!c.colorByMag) return m >= 0 ? view.theme.accent : "#dc2626";
    if (m < 0) return "#dc2626";
    if (c.refSlope) {
      var r = m / c.refSlope;
      return r > 0.66 ? "#2563eb" : r > 0.2 ? "#059669" : "#ea580c";
    }
    return view.theme.accent;
  }

  var P = {
    id: "live-tangent",
    order: 70,
    onInit: function (core) { core._pstate["live-tangent"] = { last: null }; },
    onHover: function (view, cursor) {
      var c = cfg(view);
      var s = view.series[c.seriesIndex || 0];
      if (!s || !cursor) return null;
      var t = slopeAt(s, cursor.dataX);
      if (!t) return null;
      view.core._pstate["live-tangent"].last = t;
      var disp = t.m * (c.scale || 1);
      return { hud: (c.label || "slope") + ": <b>" + view.fmt(disp) + "</b>" + (c.unit ? " " + c.unit : "") };
    },
    onDrawOver: function (ctx, view) {
      var c = cfg(view);
      if (!view.cursor) return;
      var s = view.series[c.seriesIndex || 0];
      if (!s) return;
      var t = slopeAt(s, view.cursor.dataX);
      if (!t) return;
      var pl = view.plot;
      // tangent: y = y0 + m*(x - x0), drawn across the visible x-domain
      var xa = view.domain.x[0], xb = view.domain.x[1];
      var ya = t.y0 + t.m * (xa - t.x0), yb = t.y0 + t.m * (xb - t.x0);
      ctx.save();
      ctx.strokeStyle = color(view, t.m, c); ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]);
      ctx.beginPath(); ctx.moveTo(view.scaleX(xa), view.scaleY(ya)); ctx.lineTo(view.scaleX(xb), view.scaleY(yb)); ctx.stroke();
      // touch point
      ctx.setLineDash([]); ctx.fillStyle = color(view, t.m, c);
      ctx.beginPath(); ctx.arc(view.scaleX(t.x0), view.scaleY(t.y0), 3, 0, 6.2832); ctx.fill();
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["live-tangent"] = P;
})();
