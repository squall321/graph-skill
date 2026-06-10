/* streamgraph (themeriver) — stacked flowing bands on a centered/wiggle baseline.
   Bands (lo/hi per x) are pre-stacked by the recipe; this plugin just fills them with
   smooth area paths over a style:"none" carrier series (engine autoscales to lo/hi).
   config (pluginConfig.streamgraph): { x:[...], bands:[{name, lo:[...], hi:[...], color?}] } */
(function () {
  "use strict";
  var PAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#999999",
    "#8c564b", "#17becf", "#bcbd22", "#7f7f7f"];
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["streamgraph"]) || null; }

  var P = {
    id: "streamgraph",
    order: 40,
    onDrawOver: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var xs = c.x || [], bands = c.bands || [], pl = view.plot;
      if (!xs.length) return;
      ctx.save();
      ctx.beginPath(); ctx.rect(pl.left, pl.top, pl.width, pl.height); ctx.clip();
      for (var b = 0; b < bands.length; b++) {
        var band = bands[b], lo = band.lo || [], hi = band.hi || [];
        ctx.beginPath();
        var i;
        for (i = 0; i < xs.length; i++) { var px = view.scaleX(xs[i]), py = view.scaleY(hi[i]); if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py); }
        for (i = xs.length - 1; i >= 0; i--) ctx.lineTo(view.scaleX(xs[i]), view.scaleY(lo[i]));
        ctx.closePath();
        ctx.fillStyle = band.color || PAL[b % PAL.length]; ctx.globalAlpha = 0.82; ctx.fill();
        ctx.globalAlpha = 1; ctx.lineWidth = 0.8; ctx.strokeStyle = view.theme.bg || "#fff"; ctx.stroke();
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var xs = c.x || [], bands = c.bands || [];
      // nearest x index
      var bi = 0, best = Infinity, i;
      for (i = 0; i < xs.length; i++) { var d = Math.abs(xs[i] - cursor.dataX); if (d < best) { best = d; bi = i; } }
      // which band contains cursor.dataY
      for (var b = 0; b < bands.length; b++) {
        var lo = bands[b].lo[bi], hi = bands[b].hi[bi];
        if (cursor.dataY >= lo && cursor.dataY <= hi) return { hud: bands[b].name + ": " + view.fmt(hi - lo) };
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["streamgraph"] = P;
})();
