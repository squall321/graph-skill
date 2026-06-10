/* named-markers — labeled point markers (yield/UTS/fracture, peaks, run-out...).
   config: { markers: [ {x, y, label?, color?} ] } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["named-markers"]) || {}; }
  function inPlot(pl, px, py) { return px >= pl.left && px <= pl.left + pl.width && py >= pl.top && py <= pl.top + pl.height; }
  var P = {
    id: "named-markers",
    order: 60,
    onDrawOver: function (ctx, view) {
      var ms = cfg(view).markers || [];
      if (!ms.length) return;
      var pl = view.plot;
      ctx.save();
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      for (var i = 0; i < ms.length; i++) {
        var m = ms[i], px = view.scaleX(m.x), py = view.scaleY(m.y);
        if (!inPlot(pl, px, py)) continue;
        var col = m.color || view.theme.accent;
        ctx.fillStyle = col; ctx.strokeStyle = view.theme.bg; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(px, py, 4.5, 0, 6.2832); ctx.fill(); ctx.stroke();
        if (m.label) {
          ctx.fillStyle = view.theme.fg; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
          ctx.fillText(m.label, px + 7, py - 4);
        }
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var ms = cfg(view).markers || [];
      if (!ms.length || !cursor) return null;
      for (var i = 0; i < ms.length; i++) {
        var px = view.scaleX(ms[i].x), py = view.scaleY(ms[i].y);
        if (Math.abs(px - cursor.px) < 9 && Math.abs(py - cursor.py) < 9) {
          return { hud: (ms[i].label || "marker") + ": " + view.fmt(ms[i].x) + ", " + view.fmt(ms[i].y) };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["named-markers"] = P;
})();
