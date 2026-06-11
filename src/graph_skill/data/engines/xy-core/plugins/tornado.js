/* tornado — sensitivity tornado chart: per-factor horizontal bars spanning [low, high]
   around a baseline vertical line, sorted by |span| (recipe pre-sorts). hideAxes +
   onDrawOutside (labels in margins). config (pluginConfig.tornado):
   { rows:[{name, low, high}], baseline, unit } — x domain via carrier series. */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.tornado) || null; }
  function fmt(v) { if (v == null || !isFinite(v)) return ""; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-2)) ? v.toExponential(2) : (Math.round(v * 1000) / 1000).toString(); }

  var P = {
    id: "tornado",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var rows = c.rows || [], n = rows.length; if (!n) return;
      var pl = view.plot, tok = view.theme;
      var yOf = function (i) { return view.scaleY(n - 1 - i); };
      var rowH = pl.height / n, barH = Math.min(rowH * 0.6, 26);
      var bx = view.scaleX(c.baseline);
      ctx.save();
      // baseline
      ctx.strokeStyle = tok.fg; ctx.lineWidth = 1.4; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(bx, pl.top); ctx.lineTo(bx, pl.top + pl.height); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "bottom";
      ctx.fillText("baseline " + fmt(c.baseline) + (c.unit ? " " + c.unit : ""), bx, pl.top - 3);
      // bars
      for (var i = 0; i < n; i++) {
        var r = rows[i], y = yOf(i);
        var xl = view.scaleX(Math.min(r.low, r.high)), xh = view.scaleX(Math.max(r.low, r.high));
        // low side(blue) / high side(orange) split at baseline
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = "#0072B2";
        ctx.fillRect(Math.min(xl, bx), y - barH / 2, Math.max(0, bx - Math.min(xl, bx)), barH);
        ctx.fillStyle = "#E69F00";
        ctx.fillRect(bx, y - barH / 2, Math.max(0, Math.max(xh, bx) - bx), barH);
        ctx.globalAlpha = 1;
        ctx.strokeStyle = tok.axis; ctx.lineWidth = 1;
        ctx.strokeRect(Math.min(xl, bx), y - barH / 2, Math.max(xh, bx) - Math.min(xl, bx), barH);
        // value labels at bar ends
        ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textBaseline = "middle";
        ctx.textAlign = "right"; ctx.fillText(fmt(r.low), Math.min(xl, bx) - 4, y);
        ctx.textAlign = "left"; ctx.fillText(fmt(r.high), Math.max(xh, bx) + 4, y);
        // factor name in the left margin
        ctx.fillStyle = tok.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "right"; ctx.fillText(r.name, pl.left - 8, y);
      }
      // legend chips (low/high)
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      var lx = pl.left + 4, ly = pl.top + pl.height + 14;
      ctx.fillStyle = "#0072B2"; ctx.fillRect(lx, ly - 4, 10, 8);
      ctx.fillStyle = tok.sub; ctx.fillText("low", lx + 14, ly);
      ctx.fillStyle = "#E69F00"; ctx.fillRect(lx + 46, ly - 4, 10, 8);
      ctx.fillStyle = tok.sub; ctx.fillText("high", lx + 60, ly);
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var rows = c.rows || [], n = rows.length; if (!n) return null;
      var idx = n - 1 - Math.round(cursor.dataY);
      if (idx < 0 || idx >= n) return null;
      var r = rows[idx];
      return { hud: r.name + ": " + fmt(r.low) + " ~ " + fmt(r.high) + (c.unit ? " " + c.unit : "") +
        " (스팬 " + fmt(Math.abs(r.high - r.low)) + ")" };
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].tornado = P;
})();
