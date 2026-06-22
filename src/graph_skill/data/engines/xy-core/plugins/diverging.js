/* diverging — diverging stacked bar (Likert / sentiment): per category, ordered response
   segments split around a neutral center at x=0 (favorable right, unfavorable left), so
   questions are comparable (Robbins-Heiberger). hideAxes + onDrawOutside.
   config (pluginConfig.diverging):
   { cats:[{y,label,summary,segs:[{base,top,ci}]}], responses:[..], colors:[..], unit } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.diverging) || null; }
  var P = {
    id: "diverging",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var cats = c.cats || [], n = cats.length; if (!n) return;
      var pl = view.plot, tok = view.theme, cols = c.colors || [];
      var hw = Math.min(pl.height / n * 0.62, 26), bx = view.scaleX(0);
      ctx.save();
      // zero baseline
      ctx.strokeStyle = tok.fg; ctx.lineWidth = 1.2; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(bx, pl.top); ctx.lineTo(bx, pl.top + pl.height); ctx.stroke();
      ctx.setLineDash([]);
      for (var i = 0; i < n; i++) {
        var cat = cats[i], y = view.scaleY(cat.y), segs = cat.segs || [];
        for (var k = 0; k < segs.length; k++) {
          var s = segs[k], x0 = view.scaleX(s.base), x1 = view.scaleX(s.top);
          ctx.fillStyle = cols[s.ci] || tok.accent;
          ctx.fillRect(Math.min(x0, x1), y - hw / 2, Math.abs(x1 - x0) || 1, hw);
        }
        ctx.fillStyle = tok.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "right"; ctx.textBaseline = "middle"; ctx.fillText(cat.label, pl.left - 8, y);
      }
      // legend (response levels)
      var ly = pl.top + pl.height + 16, lx = pl.left + 4;
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      var resp = c.responses || [];
      for (var r = 0; r < resp.length; r++) {
        ctx.fillStyle = cols[r] || tok.accent; ctx.fillRect(lx, ly - 4, 10, 8);
        ctx.fillStyle = tok.sub; ctx.fillText(resp[r], lx + 14, ly);
        lx += 14 + ctx.measureText(resp[r]).width + 16;
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var cats = c.cats || [], gi = Math.round(cursor.dataY);
      for (var i = 0; i < cats.length; i++) if (cats[i].y === gi) {
        return { hud: cats[i].label + (cats[i].summary ? " — " + cats[i].summary : "") +
          (c.unit ? " (" + c.unit + ")" : "") };
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].diverging = P;
})();
