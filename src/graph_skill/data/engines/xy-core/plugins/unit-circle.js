/* unit-circle — origin axes + a radius-r circle in data space, for complex-plane plots
   (Nyquist, root-locus). Reads round only under equalAspect. config:
   { circle?:bool(=true), radius?:1, showAxes?:bool(=true), color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["unit-circle"]) || {}; }
  var P = {
    id: "unit-circle",
    order: 20,
    onDrawUnder: function (ctx, view) {
      var c = cfg(view), pl = view.plot;
      var col = c.color || view.theme.sub;
      ctx.save();
      ctx.lineWidth = 1;
      ctx.strokeStyle = col;
      // origin axes (real/imag = stability boundary)
      if (c.showAxes !== false) {
        ctx.setLineDash([2, 3]);
        var px0 = view.scaleX(0), py0 = view.scaleY(0);
        if (py0 >= pl.top && py0 <= pl.top + pl.height) {
          ctx.beginPath(); ctx.moveTo(pl.left, py0); ctx.lineTo(pl.left + pl.width, py0); ctx.stroke();
        }
        if (px0 >= pl.left && px0 <= pl.left + pl.width) {
          ctx.beginPath(); ctx.moveTo(px0, pl.top); ctx.lineTo(px0, pl.top + pl.height); ctx.stroke();
        }
      }
      // circle of radius r centered at origin (data space → pixels)
      if (c.circle !== false) {
        var r = c.radius || 1, N = 96;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        for (var i = 0; i <= N; i++) {
          var a = (i / N) * 6.283185307;
          var px = view.scaleX(r * Math.cos(a)), py = view.scaleY(r * Math.sin(a));
          if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["unit-circle"] = P;
})();
