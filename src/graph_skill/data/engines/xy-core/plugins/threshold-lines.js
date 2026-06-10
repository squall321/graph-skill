/* threshold-lines — horizontal/vertical reference/limit/spec lines with labels.
   config: { lines: [ {axis:"x"|"y"|"y2", value, label?, color?, dash?} ] }
   axis "y2" maps the value onto the secondary (right) y-scale when present. */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["threshold-lines"]) || {}; }
  var P = {
    id: "threshold-lines",
    order: 30,
    onDrawOver: function (ctx, view) {
      var lines = cfg(view).lines || [];
      if (!lines.length) return;
      var pl = view.plot;
      ctx.save();
      ctx.lineWidth = 1.5;
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      for (var i = 0; i < lines.length; i++) {
        var L = lines[i], col = L.color || view.theme.sub;
        ctx.strokeStyle = col; ctx.fillStyle = col; ctx.setLineDash(L.dash || [5, 4]);
        if (L.axis === "x") {
          var px = view.scaleX(L.value);
          if (px < pl.left || px > pl.left + pl.width) continue;
          ctx.beginPath(); ctx.moveTo(px, pl.top); ctx.lineTo(px, pl.top + pl.height); ctx.stroke();
          if (L.label) { ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.fillText(L.label, px + 3, pl.top + 3); }
        } else {
          var right = L.axis === "y2";
          var sc2 = view.core && view.core.sy2;
          if (right && !sc2) continue;             // y2 requested but no right axis — skip
          var py = right ? sc2.to(L.value) : view.scaleY(L.value);
          if (py < pl.top || py > pl.top + pl.height) continue;
          ctx.beginPath(); ctx.moveTo(pl.left, py); ctx.lineTo(pl.left + pl.width, py); ctx.stroke();
          if (L.label) {
            if (right) { ctx.textAlign = "left"; ctx.textBaseline = "bottom"; ctx.fillText(L.label, pl.left + 3, py - 2); }
            else { ctx.textAlign = "right"; ctx.textBaseline = "bottom"; ctx.fillText(L.label, pl.left + pl.width - 3, py - 2); }
          }
        }
      }
      ctx.setLineDash([]); ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["threshold-lines"] = P;
})();
