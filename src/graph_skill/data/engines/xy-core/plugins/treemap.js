/* treemap — draws squarified rectangles (layout pre-computed by the recipe in a unit square).
   Covers the plot, hiding the cartesian grid. config: { rects:[{label,value,x,y,w,h,color}] } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.treemap) || {}; }
  function fmt(v) { if (v == null || !isFinite(v)) return ""; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-2)) ? v.toExponential(1) : (Math.round(v * 100) / 100).toString(); }
  var P = {
    id: "treemap",
    order: 40,
    onDrawOver: function (ctx, view) {
      var rects = cfg(view).rects || [], pl = view.plot;
      ctx.save();
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        var px = pl.left + r.x * pl.width, py = pl.top + r.y * pl.height, w = r.w * pl.width, h = r.h * pl.height;
        ctx.fillStyle = r.color || view.theme.accent;
        ctx.strokeStyle = view.theme.bg; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.rect(px, py, w, h); ctx.fill(); ctx.stroke();
        if (w > 34 && h > 16) {
          ctx.fillStyle = "#fff"; ctx.textAlign = "left"; ctx.textBaseline = "top";
          ctx.fillText(String(r.label || ""), px + 4, py + 4);
          if (h > 30) ctx.fillText(fmt(r.value), px + 4, py + 18);
        }
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var rects = cfg(view).rects || [], pl = view.plot; if (!cursor) return null;
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i], px = pl.left + r.x * pl.width, py = pl.top + r.y * pl.height;
        if (cursor.px >= px && cursor.px <= px + r.w * pl.width && cursor.py >= py && cursor.py <= py + r.h * pl.height) {
          return { hud: (r.label || "") + ": " + fmt(r.value) };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].treemap = P;
})();
