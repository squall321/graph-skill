/* slopegraph — endpoint labels for a before/after parallel-line chart. The line+marker
   series are drawn by the engine; this adds item-name + value labels at each endpoint so
   rank reorderings read directly (Tufte). config (pluginConfig.slopegraph):
   { items:[{name,left,right,color}], xl, xr } (xl/xr = data-x of the two columns) */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.slopegraph) || {}; }
  var P = {
    id: "slopegraph",
    order: 60,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), items = c.items || []; if (!items.length) return;
      var xl = view.scaleX(c.xl != null ? c.xl : 0), xr = view.scaleX(c.xr != null ? c.xr : 1);
      ctx.save();
      ctx.font = "11px Segoe UI, system-ui, sans-serif"; ctx.textBaseline = "middle";
      for (var i = 0; i < items.length; i++) {
        var it = items[i], col = it.color || view.theme.fg;
        var yl = view.scaleY(it.left), yr = view.scaleY(it.right);
        // left value (right-aligned, left of the left dot)
        ctx.fillStyle = view.theme.sub; ctx.textAlign = "right";
        ctx.fillText(view.fmt(it.left), xl - 8, yl);
        // right: item name (colored) + value (sub)
        ctx.textAlign = "left";
        ctx.fillStyle = col; ctx.fillText(it.name, xr + 9, yr);
        ctx.fillStyle = view.theme.sub;
        ctx.fillText(view.fmt(it.right), xr + 9 + ctx.measureText(it.name).width + 8, yr);
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].slopegraph = P;
})();
