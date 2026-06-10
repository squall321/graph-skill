/* brushlink — linked brushing across SPLOM cells (sibling xy-core scatters of the SAME
   rows). Box-drag selects point indices in one cell; the selection is published on the
   window bus by row-index, and every cell dims non-selected points + highlights the rest.
   Index i = row i (cells share row order). config (pluginConfig.brushlink): { group } */
(function () {
  "use strict";
  function bus() {
    if (window.GraphLink) return window.GraphLink;
    var groups = {};
    window.GraphLink = {
      sub: function (g, fn) { (groups[g] = groups[g] || []).push(fn); },
      pub: function (g, src, data) { var e = groups[g]; if (!e) return; for (var i = 0; i < e.length; i++) e[i](data, src); }
    };
    return window.GraphLink;
  }
  function ptsSeries(view) {                              // the marker (scatter) series
    var ss = view.series || [];
    for (var i = 0; i < ss.length; i++) if ((ss[i].style || "").indexOf("markers") >= 0) return ss[i];
    return ss[0] || null;
  }
  var P = {
    id: "brushlink",
    order: 56,
    onInit: function (core) {
      var c = core.opts.pluginConfig && core.opts.pluginConfig.brushlink; if (!c) return;
      var me = (window.__brushN = (window.__brushN || 0) + 1);
      var st = core._pstate.brushlink = { group: c.group, me: me, sel: null, rect: null, drag: false };
      bus().sub(c.group, function (data, src) {
        if (src === st.me) return;
        st.sel = data ? data.sel : null;
        core.render();
      });
    },
    onDown: function (view, c) {
      var cf = view.pluginConfig && view.pluginConfig.brushlink; if (!cf) return false;
      var st = view.core._pstate.brushlink; if (!st) return false;
      st.rect = { x0: c.px, y0: c.py, x1: c.px, y1: c.py }; st.drag = true;
      return true;
    },
    onDrag: function (view, c) {
      var st = view.core._pstate.brushlink; if (!st || !st.drag) return;
      st.rect.x1 = c.px; st.rect.y1 = c.py; view.core.render();
    },
    onUp: function (view) {
      var st = view.core._pstate.brushlink; if (!st || !st.drag) return;
      st.drag = false; var r = st.rect; st.rect = null;
      if (!r || (Math.abs(r.x1 - r.x0) < 3 && Math.abs(r.y1 - r.y0) < 3)) {   // tiny → clear selection
        st.sel = null; bus().pub(st.group, st.me, null); view.core.render(); return;
      }
      var xmin = Math.min(r.x0, r.x1), xmax = Math.max(r.x0, r.x1), ymin = Math.min(r.y0, r.y1), ymax = Math.max(r.y0, r.y1);
      var s = ptsSeries(view), sel = {};
      if (s) {
        for (var i = 0; i < s.x.length; i++) {
          var y = s.y[i]; if (y == null || !isFinite(y)) continue;
          var px = view.scaleX(s.x[i]), py = view.scaleY(y);
          if (px >= xmin && px <= xmax && py >= ymin && py <= ymax) sel[i] = 1;
        }
      }
      st.sel = sel; bus().pub(st.group, st.me, { sel: sel }); view.core.render();
    },
    onDrawOver: function (ctx, view) {
      var st = view.core._pstate.brushlink; if (!st) return;
      var pl = view.plot;
      if (st.sel) {                                       // dim plot, then redraw selected bright
        ctx.save();
        ctx.fillStyle = view.theme.bg; ctx.globalAlpha = 0.62;
        ctx.fillRect(pl.left, pl.top, pl.width, pl.height);
        ctx.restore();
        var s = ptsSeries(view);
        if (s) {
          ctx.save(); ctx.fillStyle = view.theme.accent;
          for (var k in st.sel) {
            if (!st.sel.hasOwnProperty(k)) continue;
            var y = s.y[k]; if (y == null || !isFinite(y)) continue;
            var px = view.scaleX(s.x[k]), py = view.scaleY(y);
            if (px < pl.left || px > pl.left + pl.width || py < pl.top || py > pl.top + pl.height) continue;
            ctx.beginPath(); ctx.arc(px, py, 2.8, 0, 6.2832); ctx.fill();
          }
          ctx.restore();
        }
      }
      if (st.rect) {                                      // active brush rectangle
        var r = st.rect;
        ctx.save();
        ctx.fillStyle = view.theme.accent; ctx.globalAlpha = 0.12;
        ctx.fillRect(Math.min(r.x0, r.x1), Math.min(r.y0, r.y1), Math.abs(r.x1 - r.x0), Math.abs(r.y1 - r.y0));
        ctx.globalAlpha = 1; ctx.strokeStyle = view.theme.accent; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
        ctx.strokeRect(Math.min(r.x0, r.x1), Math.min(r.y0, r.y1), Math.abs(r.x1 - r.x0), Math.abs(r.y1 - r.y0));
        ctx.restore();
      }
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["brushlink"] = P;
})();
