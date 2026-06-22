/* funnel — conversion / stage-attrition funnel: ordered stages as centered bars whose
   width ∝ value, narrowing top→bottom, with conversion % (vs first / vs prev) and a
   tapered connector between stages. hideAxes + onDrawOutside.
   config (pluginConfig.funnel): { stages:[{i,label,value,pctFirst,pctPrev}], maxValue, color?, unit? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.funnel) || null; }
  var P = {
    id: "funnel",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var st = c.stages || [], n = st.length; if (!n) return;
      var pl = view.plot, tok = view.theme, base = c.color || "#2563eb";
      var cx = pl.left + pl.width / 2, maxV = c.maxValue || 1, maxHalf = pl.width * 0.40;
      function halfW(v) { return maxHalf * (v > 0 ? v / maxV : 0); }
      var rowH = Math.min(pl.height / n * 0.60, 42);
      ctx.save();
      ctx.font = "11px Segoe UI, system-ui, sans-serif"; ctx.textBaseline = "middle";
      for (var i = 0; i < n; i++) {
        var s = st[i], y = view.scaleY(s.i), hwid = halfW(s.value);
        // tapered connector to next stage
        if (i < n - 1) {
          var s2 = st[i + 1], y2 = view.scaleY(s2.i), h2 = halfW(s2.value);
          ctx.fillStyle = base; ctx.globalAlpha = 0.12;
          ctx.beginPath();
          ctx.moveTo(cx - hwid, y + rowH / 2); ctx.lineTo(cx + hwid, y + rowH / 2);
          ctx.lineTo(cx + h2, y2 - rowH / 2); ctx.lineTo(cx - h2, y2 - rowH / 2);
          ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
        }
        // stage bar
        ctx.fillStyle = base; ctx.globalAlpha = 0.32 + 0.55 * (s.value > 0 ? s.value / maxV : 0);
        ctx.fillRect(cx - hwid, y - rowH / 2, hwid * 2, rowH); ctx.globalAlpha = 1;
        // stage label (left margin)
        ctx.fillStyle = tok.fg; ctx.textAlign = "right"; ctx.fillText(s.label, pl.left - 8, y);
        // value (centered) + conversion (right margin)
        ctx.fillStyle = tok.fg; ctx.textAlign = "center";
        ctx.fillText(view.fmt(s.value) + (c.unit ? " " + c.unit : ""), cx, y);
        ctx.fillStyle = tok.sub; ctx.textAlign = "left"; ctx.font = "10px Segoe UI, system-ui, sans-serif";
        var pct = (i === 0) ? "100%" : (Math.round(s.pctFirst) + "%  (Δ" + Math.round(s.pctPrev) + "%)");
        ctx.fillText(pct, cx + maxHalf + 10, y);
        ctx.font = "11px Segoe UI, system-ui, sans-serif";
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var st = c.stages || [], gi = Math.round(cursor.dataY);
      for (var i = 0; i < st.length; i++) if (st[i].i === gi) {
        var s = st[i];
        return { hud: s.label + ": " + view.fmt(s.value) + (c.unit ? " " + c.unit : "") +
          "  (" + s.pctFirst.toFixed(1) + "% of first" +
          (s.pctPrev < 100 || i > 0 ? ", Δ" + s.pctPrev.toFixed(1) + "% vs prev" : "") + ")" };
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].funnel = P;
})();
