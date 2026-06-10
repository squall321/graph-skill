/* region-shading — shaded x-ranges with labels (elastic/plastic/necking, reliability stages...).
   config: { regions: [ {x0, x1, color?, label?} ] }  (x in data coords) */
(function () {
  "use strict";
  var FILLS = ["rgba(100,200,100,.16)", "rgba(200,200,100,.16)", "rgba(200,150,100,.16)", "rgba(200,100,100,.16)", "rgba(120,160,220,.16)"];
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["region-shading"]) || {}; }
  var P = {
    id: "region-shading",
    order: 10,
    onDrawUnder: function (ctx, view) {
      var regs = cfg(view).regions || [];
      if (!regs.length) return;
      var pl = view.plot;
      ctx.save();
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      for (var i = 0; i < regs.length; i++) {
        var r = regs[i];
        var a = view.scaleX(r.x0), b = view.scaleX(r.x1);
        var lo = Math.max(pl.left, Math.min(a, b)), hi = Math.min(pl.left + pl.width, Math.max(a, b));
        if (hi <= lo) continue;
        ctx.fillStyle = r.color || FILLS[i % FILLS.length];
        ctx.fillRect(lo, pl.top, hi - lo, pl.height);
        if (r.label) {
          ctx.fillStyle = view.theme.sub;
          ctx.fillText(r.label, (lo + hi) / 2, pl.top + 3);
        }
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["region-shading"] = P;
})();
