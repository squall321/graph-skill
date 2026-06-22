/* dumbbell — paired values per category (before/after, A/B, baseline/target) as two dots
   joined by a connector, ranked by category so the gap is the visual focus. Horizontal:
   value = x, category = row. hideAxes + onDrawOutside (labels/legend in margins).
   config (pluginConfig.dumbbell): { rows:[{y,label,a,b}], aName,bName,aColor,bColor,unit,xlabel } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.dumbbell) || null; }
  var P = {
    id: "dumbbell",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var rows = c.rows || [], n = rows.length; if (!n) return;
      var pl = view.plot, tok = view.theme;
      var aCol = c.aColor || "#0072B2", bCol = c.bColor || "#E69F00";
      ctx.save();
      for (var i = 0; i < n; i++) {
        var r = rows[i], y = view.scaleY(r.y);
        var xa = view.scaleX(r.a), xb = view.scaleX(r.b);
        // connector
        ctx.strokeStyle = tok.sub; ctx.lineWidth = 2.2;
        ctx.beginPath(); ctx.moveTo(xa, y); ctx.lineTo(xb, y); ctx.stroke();
        // dots
        ctx.fillStyle = aCol; ctx.beginPath(); ctx.arc(xa, y, 4.6, 0, 6.2832); ctx.fill();
        ctx.fillStyle = bCol; ctx.beginPath(); ctx.arc(xb, y, 4.6, 0, 6.2832); ctx.fill();
        // category label (left margin)
        ctx.fillStyle = tok.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "right"; ctx.textBaseline = "middle"; ctx.fillText(r.label, pl.left - 8, y);
        // value labels outside each end
        var lo = Math.min(xa, xb), hi = Math.max(xa, xb);
        var loV = (xa <= xb) ? r.a : r.b, hiV = (xa <= xb) ? r.b : r.a;
        ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "right"; ctx.fillText(view.fmt(loV), lo - 7, y);
        ctx.textAlign = "left"; ctx.fillText(view.fmt(hiV), hi + 7, y);
      }
      // legend + axis title (bottom margin)
      var ly = pl.top + pl.height + 16, lx = pl.left + 4;
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      ctx.fillStyle = aCol; ctx.beginPath(); ctx.arc(lx + 4, ly, 4, 0, 6.2832); ctx.fill();
      ctx.fillStyle = tok.sub; ctx.fillText(c.aName || "A", lx + 12, ly);
      var lx2 = lx + 12 + ctx.measureText(c.aName || "A").width + 18;
      ctx.fillStyle = bCol; ctx.beginPath(); ctx.arc(lx2 + 4, ly, 4, 0, 6.2832); ctx.fill();
      ctx.fillStyle = tok.sub; ctx.fillText(c.bName || "B", lx2 + 12, ly);
      if (c.xlabel || c.unit) {
        ctx.textAlign = "right"; ctx.fillStyle = tok.sub;
        ctx.fillText((c.xlabel || "") + (c.unit ? " [" + c.unit + "]" : ""), pl.left + pl.width, ly);
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var rows = c.rows || [], gi = Math.round(cursor.dataY);
      for (var i = 0; i < rows.length; i++) if (rows[i].y === gi) {
        var r = rows[i];
        return { hud: r.label + ": " + (c.aName || "A") + " " + view.fmt(r.a) + " → " +
          (c.bName || "B") + " " + view.fmt(r.b) + "  (Δ " + view.fmt(r.b - r.a) + ")" };
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].dumbbell = P;
})();
