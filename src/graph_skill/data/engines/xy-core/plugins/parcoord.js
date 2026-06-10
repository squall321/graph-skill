/* parcoord — parallel coordinates with axis brushing. Vertical axis per dimension
   (categorical x = dim names, y = normalized 0..1) + one polyline per observation. Drag on
   an axis to brush a value range (lines outside ALL brushes dim); click an axis to clear it.
   config: { dims:[{name,min,max}], rows:[[norm0,norm1,...]], color? } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.parcoord) || {}; }
  function st(view) { var c = view.core; c._pstate = c._pstate || {}; return (c._pstate.parcoord = c._pstate.parcoord || { brushes: {}, active: null, y0: 0 }); }
  function fmt(v) { if (v == null || !isFinite(v)) return ""; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-2)) ? v.toExponential(1) : (Math.round(v * 100) / 100).toString(); }
  function clamp01(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }
  function nearestAxis(view, c) {
    var dims = cfg(view).dims || [], best = -1, bd = 22;
    for (var i = 0; i < dims.length; i++) { var d = Math.abs(view.scaleX(i) - c.px); if (d < bd) { bd = d; best = i; } }
    return best;
  }
  function matched(brushes, row) {
    for (var k in brushes) { var b = brushes[k], v = row[k]; if (v < b[0] || v > b[1]) return false; }
    return true;
  }
  var P = {
    id: "parcoord",
    order: 40,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view), dims = c.dims || [], pl = view.plot;
      ctx.save();
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.fillStyle = view.theme.sub;
      for (var i = 0; i < dims.length; i++) {
        var x = view.scaleX(i);
        ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.fillText(fmt(dims[i].max), x, pl.top - 2);
        ctx.textBaseline = "top"; ctx.fillText(fmt(dims[i].min), x, pl.top + pl.height + 2);
      }
      ctx.restore();
    },
    onHover: function (view, cursor) {
      if (cursor && view.core && view.core.canvas) {
        var nd0 = (cfg(view).dims || []).length, near = false;
        for (var ai = 0; ai < nd0; ai++) { if (Math.abs(view.scaleX(ai) - cursor.px) < 9) { near = true; break; } }
        view.core.canvas.style.cursor = near ? "crosshair" : "";
      }
      return null;
    },
    onDown: function (view, c) {
      var i = nearestAxis(view, c);
      if (i < 0) return false;
      var s = st(view); s.active = i; s.y0 = clamp01(c.dataY); s.brushes[i] = [s.y0, s.y0];
      return true;                                     // claim the drag
    },
    onDrag: function (view, c) {
      var s = st(view); if (s.active == null) return;
      var y1 = clamp01(c.dataY);
      s.brushes[s.active] = [Math.min(s.y0, y1), Math.max(s.y0, y1)];
    },
    onUp: function (view, c) {
      var s = st(view); if (s.active == null) return;
      var b = s.brushes[s.active];
      if (!c.moved || (b && b[1] - b[0] < 0.01)) delete s.brushes[s.active];   // click / tiny → clear
      s.active = null;
    },
    onDrawOver: function (ctx, view) {
      var c = cfg(view), dims = c.dims || [], rows = c.rows || [], nd = dims.length, pl = view.plot;
      if (!nd) return;
      var brushes = st(view).brushes, hasBrush = false, kk;
      for (kk in brushes) { hasBrush = true; break; }
      ctx.save();
      // axes + min/max labels
      ctx.strokeStyle = view.theme.axis; ctx.lineWidth = 1;
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.fillStyle = view.theme.sub;
      for (var i = 0; i < nd; i++) {
        var x = view.scaleX(i);
        ctx.beginPath(); ctx.moveTo(x, pl.top); ctx.lineTo(x, pl.top + pl.height); ctx.stroke();
      }
      // polylines: matched accent, unmatched dim
      for (var r = 0; r < rows.length; r++) {
        var row = rows[r], on = !hasBrush || matched(brushes, row);
        ctx.strokeStyle = on ? (c.color || "rgba(37,99,235,0.45)") : "rgba(120,130,150,0.07)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (var k = 0; k < nd; k++) { var px = view.scaleX(k), py = view.scaleY(row[k]); if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py); }
        ctx.stroke();
      }
      // brush rectangles
      ctx.fillStyle = "rgba(37,99,235,0.16)"; ctx.strokeStyle = view.theme.accent;
      for (kk in brushes) {
        var b = brushes[kk], ax = view.scaleX(+kk), yt = view.scaleY(b[1]), yb = view.scaleY(b[0]);
        ctx.beginPath(); ctx.rect(ax - 6, Math.min(yt, yb), 12, Math.abs(yb - yt) || 2); ctx.fill(); ctx.stroke();
      }
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].parcoord = P;
})();
