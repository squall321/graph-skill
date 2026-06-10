/* box-plot — draws box-and-whisker glyphs per group (categorical x). Stats are pre-computed
   by the recipe. config: { groups:[{x, q1, med, q3, lo, hi, outliers:[..]}], color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["box-plot"]) || {}; }
  var P = {
    id: "box-plot",
    order: 50,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), gs = c.groups || [];
      var col = c.color || view.theme.accent, hw = 0.3;
      ctx.save();
      ctx.lineWidth = 1.5;
      for (var i = 0; i < gs.length; i++) {
        var g = gs[i];
        var xc = view.scaleX(g.x), x0 = view.scaleX(g.x - hw), x1 = view.scaleX(g.x + hw);
        var q1 = view.scaleY(g.q1), q3 = view.scaleY(g.q3), md = view.scaleY(g.med);
        var lo = view.scaleY(g.lo), hi = view.scaleY(g.hi);
        ctx.strokeStyle = col; ctx.fillStyle = view.theme.bg;
        // box
        ctx.beginPath(); ctx.rect(Math.min(x0, x1), Math.min(q1, q3), Math.abs(x1 - x0), Math.abs(q3 - q1));
        ctx.fill(); ctx.stroke();
        // median
        ctx.beginPath(); ctx.moveTo(x0, md); ctx.lineTo(x1, md); ctx.stroke();
        // whiskers
        ctx.beginPath(); ctx.moveTo(xc, q3); ctx.lineTo(xc, hi); ctx.moveTo(xc, q1); ctx.lineTo(xc, lo);
        ctx.moveTo(x0 + (x1 - x0) * 0.25, hi); ctx.lineTo(x1 - (x1 - x0) * 0.25, hi);
        ctx.moveTo(x0 + (x1 - x0) * 0.25, lo); ctx.lineTo(x1 - (x1 - x0) * 0.25, lo);
        ctx.stroke();
        // outliers
        ctx.fillStyle = col;
        for (var k = 0; k < (g.outliers || []).length; k++) {
          ctx.beginPath(); ctx.arc(xc, view.scaleY(g.outliers[k]), 2.2, 0, 6.2832); ctx.fill();
        }
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var gs = cfg(view).groups || []; if (!cursor) return null;
      var gi = Math.round(cursor.dataX);
      for (var i = 0; i < gs.length; i++) {
        if (gs[i].x === gi) {
          var g = gs[i];
          return { hud: "med " + view.fmt(g.med) + " · IQR [" + view.fmt(g.q1) + ", " + view.fmt(g.q3) + "]" };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["box-plot"] = P;
})();
