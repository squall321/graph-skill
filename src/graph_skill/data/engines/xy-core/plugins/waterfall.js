/* waterfall — floating bars from base→top per category (budget/contribution decomposition).
   Stats pre-computed by the recipe. config:
   { bars:[{x, base, top, kind:"inc"|"dec"|"total"}], hw?:0.34, connectors?:true,
     incColor?, decColor?, totalColor? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["waterfall"]) || {}; }
  var P = {
    id: "waterfall",
    order: 45,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), bars = c.bars || [], hw = c.hw || 0.34;
      var inc = c.incColor || "#2563eb", dec = c.decColor || "#dc2626", tot = c.totalColor || "#6b7280";
      ctx.save();
      ctx.lineWidth = 1;
      var prevTopPx = null, prevX1 = null;
      for (var i = 0; i < bars.length; i++) {
        var b = bars[i];
        var x0 = view.scaleX(b.x - hw), x1 = view.scaleX(b.x + hw);
        var yb = view.scaleY(b.base), yt = view.scaleY(b.top);
        ctx.fillStyle = b.kind === "total" ? tot : (b.kind === "dec" ? dec : inc);
        ctx.strokeStyle = view.theme.bg;
        ctx.beginPath();
        ctx.rect(Math.min(x0, x1), Math.min(yb, yt), Math.abs(x1 - x0), Math.abs(yt - yb) || 1);
        ctx.fill(); ctx.stroke();
        if (c.connectors !== false && prevTopPx != null) {
          ctx.strokeStyle = view.theme.sub; ctx.setLineDash([3, 3]);
          ctx.beginPath(); ctx.moveTo(prevX1, prevTopPx); ctx.lineTo(x0, yb); ctx.stroke();
          ctx.setLineDash([]);
        }
        prevTopPx = yt; prevX1 = x1;
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var bars = cfg(view).bars || []; if (!cursor) return null;
      var gi = Math.round(cursor.dataX);
      for (var i = 0; i < bars.length; i++) {
        if (bars[i].x === gi) {
          return { hud: (bars[i].kind || "") + " Δ" + view.fmt(bars[i].top - bars[i].base) + " → " + view.fmt(bars[i].top) };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["waterfall"] = P;
})();
