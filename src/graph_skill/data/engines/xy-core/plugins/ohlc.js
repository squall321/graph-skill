/* ohlc — candlestick / OHLC glyphs per period (categorical x). Body = open→close
   (up/down colored), wick = low→high. Stats pre-computed by the recipe.
   config (pluginConfig.ohlc): { bars:[{x,o,h,l,c}], upColor?, downColor?, hw?, unit? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.ohlc) || {}; }
  var P = {
    id: "ohlc",
    order: 50,
    onDrawOver: function (ctx, view) {
      var c = cfg(view), bars = c.bars || []; if (!bars.length) return;
      var up = c.upColor || "#16a34a", dn = c.downColor || "#dc2626", hw = c.hw || 0.3;
      ctx.save(); ctx.lineWidth = 1.4;
      for (var i = 0; i < bars.length; i++) {
        var b = bars[i], rising = b.c >= b.o, col = rising ? up : dn;
        var xc = view.scaleX(b.x), x0 = view.scaleX(b.x - hw), x1 = view.scaleX(b.x + hw);
        var yo = view.scaleY(b.o), ycl = view.scaleY(b.c), yh = view.scaleY(b.h), yl = view.scaleY(b.l);
        ctx.strokeStyle = col; ctx.fillStyle = col;
        // wick (low→high)
        ctx.beginPath(); ctx.moveTo(xc, yh); ctx.lineTo(xc, yl); ctx.stroke();
        // body (open→close); rising drawn hollow, falling filled (common convention)
        var top = Math.min(yo, ycl), bh = Math.abs(ycl - yo) || 1;
        ctx.beginPath(); ctx.rect(Math.min(x0, x1), top, Math.abs(x1 - x0), bh);
        if (rising) { ctx.fillStyle = view.theme.bg; ctx.fill(); ctx.stroke(); }
        else { ctx.globalAlpha = 0.92; ctx.fill(); ctx.globalAlpha = 1; ctx.stroke(); }
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var bars = cfg(view).bars || []; if (!cursor) return null;
      var gi = Math.round(cursor.dataX);
      for (var i = 0; i < bars.length; i++) if (bars[i].x === gi) {
        var b = bars[i];
        return { hud: "O " + view.fmt(b.o) + "  H " + view.fmt(b.h) + "  L " + view.fmt(b.l) +
          "  C " + view.fmt(b.c) + (b.c >= b.o ? "  ▲" : "  ▼") };
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].ohlc = P;
})();
