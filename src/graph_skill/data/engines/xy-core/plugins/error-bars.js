/* error-bars — vertical error whiskers at each point. config: { bars:[{x,y,err}], color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["error-bars"]) || {}; }
  var P = {
    id: "error-bars",
    order: 45,
    onDrawOver: function (ctx, view) {
      var bars = cfg(view).bars || []; if (!bars.length) return;
      var col = cfg(view).color || view.theme.sub, cap = 4;
      ctx.save(); ctx.strokeStyle = col; ctx.lineWidth = 1.5;
      for (var i = 0; i < bars.length; i++) {
        var b = bars[i]; if (b.err == null || !isFinite(b.err)) continue;
        var px = view.scaleX(b.x), pHi = view.scaleY(b.y + b.err), pLo = view.scaleY(b.y - b.err);
        ctx.beginPath();
        ctx.moveTo(px, pHi); ctx.lineTo(px, pLo);
        ctx.moveTo(px - cap, pHi); ctx.lineTo(px + cap, pHi);
        ctx.moveTo(px - cap, pLo); ctx.lineTo(px + cap, pLo);
        ctx.stroke();
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["error-bars"] = P;
})();
