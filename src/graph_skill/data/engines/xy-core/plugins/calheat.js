/* calheat — calendar heatmap (GitHub-style): weeks as columns, weekdays as rows, cell
   color = value. Layout (week/dow per day) pre-computed by the recipe. hideAxes.
   config (pluginConfig.calheat): { cells:[{w,dw,v,t}], nweeks, vmax, months:[{w,label}],
                                    value_label? }                                        */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.calheat) || null; }
  function dayMs() { return 86400000; }
  function fmtDate(t) {
    var d = new Date(t * dayMs());
    return d.getUTCFullYear() + "-" + (d.getUTCMonth() + 1) + "-" + d.getUTCDate();
  }
  function shade(f, dark) {                                   // 0..1 → blue ramp
    if (f <= 0) return dark ? "#1e293b" : "#e9eef4";
    var stops = dark
      ? [[30, 58, 95], [37, 99, 168], [96, 165, 250]]
      : [[198, 219, 239], [107, 174, 214], [8, 81, 156]];
    var x = Math.min(1, f) * (stops.length - 1), i = Math.min(stops.length - 2, Math.floor(x)), u = x - i;
    var a = stops[i], b = stops[i + 1];
    return "rgb(" + Math.round(a[0] + (b[0] - a[0]) * u) + "," + Math.round(a[1] + (b[1] - a[1]) * u) + "," + Math.round(a[2] + (b[2] - a[2]) * u) + ")";
  }
  var DOW = ["월", "", "수", "", "금", "", "일"];

  var P = {
    id: "calheat",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var pl = view.plot, tok = view.theme;
      var dark = (tok.bg || "#fff").toLowerCase() !== "#ffffff" && tok.bg !== "#fff";
      var nw = Math.max(1, c.nweeks), cw = pl.width / nw, ch = pl.height / 7;
      var s = Math.min(cw, ch), gap = Math.max(1, s * 0.12), size = s - gap;
      var ox = pl.left + (pl.width - s * nw) / 2, oy = pl.top + (pl.height - s * 7) / 2;
      ctx.save();
      // weekday labels (left margin)
      ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "right"; ctx.textBaseline = "middle";
      for (var d = 0; d < 7; d++) if (DOW[d]) ctx.fillText(DOW[d], ox - 6, oy + d * s + s / 2);
      // month labels (top margin)
      ctx.textAlign = "left"; ctx.textBaseline = "bottom";
      (c.months || []).forEach(function (m) { ctx.fillText(m.label, ox + m.w * s, oy - 4); });
      // cells
      var vmax = c.vmax || 1;
      (c.cells || []).forEach(function (cell) {
        ctx.fillStyle = shade((cell.v || 0) / vmax, dark);
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(ox + cell.w * s, oy + cell.dw * s, size, size, 2);
        else ctx.rect(ox + cell.w * s, oy + cell.dw * s, size, size);
        ctx.fill();
      });
      // remember geometry for hover
      var st = view.core._pstate.calheat = view.core._pstate.calheat || {};
      st.ox = ox; st.oy = oy; st.s = s;
      ctx.restore();
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var st = view.core._pstate.calheat; if (!st) return null;
      var w = Math.floor((cursor.px - st.ox) / st.s), dw = Math.floor((cursor.py - st.oy) / st.s);
      for (var i = 0; i < (c.cells || []).length; i++) {
        var cell = c.cells[i];
        if (cell.w === w && cell.dw === dw) {
          return { hud: fmtDate(cell.t) + " · " + (c.value_label || "값") + " " + (cell.v != null ? cell.v : 0) };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].calheat = P;
})();
