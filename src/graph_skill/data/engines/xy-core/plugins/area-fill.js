/* area-fill — fills the band under each (visible) series to a baseline, or between stacked
   series. Draws UNDER the lines (self-clipped to the plot). config:
   { baseline?:0, stacked?:bool, opacity?:0.25, only?:[seriesIndex,...] } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["area-fill"]) || {}; }
  function hex2rgba(c, a) {
    if (!c || c[0] !== "#") return c;
    var h = c.slice(1);
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  var P = {
    id: "area-fill",
    order: 5,
    onDrawUnder: function (ctx, view) {
      var c = cfg(view), base = c.baseline || 0, op = c.opacity == null ? 0.25 : c.opacity;
      var stacked = !!c.stacked, only = c.only, pl = view.plot, S = view.series;
      ctx.save();
      ctx.beginPath(); ctx.rect(pl.left, pl.top, pl.width, pl.height); ctx.clip();
      for (var i = 0; i < S.length; i++) {
        if (!view.visible[i]) continue;
        if (only && only.indexOf(i) < 0) continue;
        var s = S[i], n = s.x.length;
        if (!n) continue;
        ctx.beginPath();
        var started = false, k;
        for (k = 0; k < n; k++) {
          var y = s.y[k];
          if (y == null || !isFinite(y)) continue;
          var px = view.scaleX(s.x[k]), py = view.scaleY(y);
          if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
        }
        if (!started) continue;
        // lower boundary (reverse): previous stacked series, else the baseline
        if (stacked && i > 0) {
          var p = S[i - 1];
          for (k = n - 1; k >= 0; k--) {
            var yv = p.y[k];
            ctx.lineTo(view.scaleX(p.x[k]), view.scaleY((yv == null || !isFinite(yv)) ? base : yv));
          }
        } else {
          var yb = view.scaleY(base);
          for (k = n - 1; k >= 0; k--) ctx.lineTo(view.scaleX(s.x[k]), yb);
        }
        ctx.closePath();
        ctx.fillStyle = hex2rgba(s._color || view.theme.accent, op);
        ctx.fill();
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["area-fill"] = P;
})();
