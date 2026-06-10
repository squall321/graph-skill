/* violin — mirrored KDE density per group on a categorical x. Densities pre-computed by the
   recipe. config: { groups:[{x, ys:[value grid], dens:[density], med?}], maxw?:0.4, color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["violin"]) || {}; }
  var P = {
    id: "violin",
    order: 50,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), gs = c.groups || [], maxw = c.maxw || 0.4;
      var col = c.color || view.theme.accent;
      var gmax = 0, i, k;
      for (i = 0; i < gs.length; i++) for (k = 0; k < (gs[i].dens || []).length; k++) gmax = Math.max(gmax, gs[i].dens[k]);
      if (gmax <= 0) return;
      ctx.save();
      ctx.lineWidth = 1.2;
      for (i = 0; i < gs.length; i++) {
        var g = gs[i], ys = g.ys || [], dn = g.dens || [], m = ys.length;
        if (!m) continue;
        var sc = maxw / gmax;
        ctx.beginPath();
        for (k = 0; k < m; k++) {                       // right edge up
          ctx.lineTo(view.scaleX(g.x + dn[k] * sc), view.scaleY(ys[k]));
        }
        for (k = m - 1; k >= 0; k--) {                  // left edge down (mirror)
          ctx.lineTo(view.scaleX(g.x - dn[k] * sc), view.scaleY(ys[k]));
        }
        ctx.closePath();
        ctx.fillStyle = "rgba(37,99,235,0.18)"; ctx.strokeStyle = col;
        ctx.fill(); ctx.stroke();
        if (g.med != null) {
          var my = view.scaleY(g.med);
          ctx.strokeStyle = view.theme.fg;
          ctx.beginPath(); ctx.moveTo(view.scaleX(g.x - maxw * 0.4), my); ctx.lineTo(view.scaleX(g.x + maxw * 0.4), my); ctx.stroke();
        }
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var gs = cfg(view).groups || []; if (!cursor) return null;
      var gi = Math.round(cursor.dataX);
      for (var i = 0; i < gs.length; i++) if (gs[i].x === gi && gs[i].med != null) return { hud: "median " + view.fmt(gs[i].med) };
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["violin"] = P;
})();
