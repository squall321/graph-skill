/* regression-fit — least-squares fit line + R² + optional identity (y=x) line.
   Used by correlation/DOE. config:
   { model:"linear", identityLine?:bool, showR2?:bool, seriesIndex?:0, color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["regression-fit"]) || {}; }

  function linfit(s) {
    var n = 0, sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0, i;
    for (i = 0; i < s.x.length; i++) {
      var y = s.y[i];
      if (y == null || !isFinite(y)) continue;
      var x = s.x[i];
      n++; sx += x; sy += y; sxx += x * x; sxy += x * y; syy += y * y;
    }
    if (n < 2) return null;
    var d = n * sxx - sx * sx;
    if (d === 0) return null;
    var a = (n * sxy - sx * sy) / d, b = (sy - a * sx) / n;
    var mean = sy / n, ssTot = syy - n * mean * mean, ssRes = 0;
    for (i = 0; i < s.x.length; i++) {
      var yy = s.y[i];
      if (yy == null || !isFinite(yy)) continue;
      var e = yy - (a * s.x[i] + b); ssRes += e * e;
    }
    return { a: a, b: b, r2: ssTot > 0 ? Math.max(0, 1 - ssRes / ssTot) : 1, n: n };
  }

  function poly(ctx, view, fn) {
    var pl = view.plot, N = 60, i;
    ctx.beginPath();
    for (i = 0; i <= N; i++) {
      var x = view.domain.x[0] + (view.domain.x[1] - view.domain.x[0]) * (i / N);
      var px = view.scaleX(x), py = view.scaleY(fn(x));
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  var P = {
    id: "regression-fit",
    order: 40,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), pl = view.plot;
      ctx.save();
      ctx.lineWidth = 1.5;
      if (c.identityLine) {
        ctx.strokeStyle = view.theme.sub; ctx.setLineDash([4, 4]);
        poly(ctx, view, function (x) { return x; });
        ctx.setLineDash([]);
      }
      var s = view.series[c.seriesIndex || 0];
      var f = s ? linfit(s) : null;
      if (f) {
        ctx.strokeStyle = c.color || view.theme.accent; ctx.setLineDash([]);
        poly(ctx, view, function (x) { return f.a * x + f.b; });
        if (c.showR2 !== false) {
          ctx.fillStyle = view.theme.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
          ctx.textAlign = "left"; ctx.textBaseline = "top";
          var txt = "y=" + view.fmt(f.a) + "x" + (f.b >= 0 ? "+" : "") + view.fmt(f.b) + "   R²=" + (Math.round(f.r2 * 1000) / 1000);
          ctx.fillText(txt, pl.left + 6, pl.top + 6);
        }
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["regression-fit"] = P;
})();
