/* treemap-drill — hierarchical treemap with click-to-drill-down + breadcrumb.
   Each node's child layout is pre-squarified by the recipe (node.rects aligned with
   node.children, unit-box coords), so the plugin only swaps the focus node and draws —
   no JS layout. Click a child-with-children to drill in; click a breadcrumb to pop.
   config (pluginConfig["treemap-drill"]): { tree: {name,value,color,children?,rects?} } */
(function () {
  "use strict";
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["treemap-drill"]) || null; }
  function fmt(v) { if (v == null || !isFinite(v)) return ""; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-2)) ? v.toExponential(1) : (Math.round(v * 100) / 100).toString(); }
  var BC = 22;   // breadcrumb band height (px)

  var P = {
    id: "treemap-drill",
    order: 40,
    onInit: function (core) {
      var c = (core.opts.pluginConfig && core.opts.pluginConfig["treemap-drill"]); if (!c) return;
      core._pstate["treemap-drill"] = { focus: c.tree, path: [c.tree], crumbs: [] };
    },
    onDrawOver: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var st = view.core._pstate["treemap-drill"]; if (!st) return;
      var pl = view.plot, focus = st.focus, rects = focus.rects || [], kids = focus.children || [];
      var ax = pl.left, ay = pl.top + BC, aw = pl.width, ah = pl.height - BC;
      ctx.save();
      // tiles
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      for (var i = 0; i < kids.length; i++) {
        var r = rects[i]; if (!r) continue;
        var px = ax + r.x * aw, py = ay + r.y * ah, w = r.w * aw, h = r.h * ah;
        ctx.fillStyle = kids[i].color || view.theme.accent;
        ctx.strokeStyle = view.theme.bg; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.rect(px, py, w, h); ctx.fill(); ctx.stroke();
        if (w > 34 && h > 16) {
          ctx.fillStyle = "#fff"; ctx.textAlign = "left"; ctx.textBaseline = "top";
          ctx.fillText(String(kids[i].name || "") + ((kids[i].children && kids[i].children.length) ? " ▸" : ""), px + 4, py + 4);
          if (h > 30) ctx.fillText(fmt(kids[i].value), px + 4, py + 18);
        }
      }
      // breadcrumb
      ctx.clearRect(pl.left, pl.top, pl.width, BC);
      ctx.fillStyle = view.theme.bg; ctx.fillRect(pl.left, pl.top, pl.width, BC);
      ctx.font = "600 12px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      var x = pl.left + 4; st.crumbs = [];
      for (var p = 0; p < st.path.length; p++) {
        var name = st.path[p].name || "전체", seg = (p ? " ▸ " : "") + name;
        var wseg = ctx.measureText(seg).width;
        ctx.fillStyle = (p === st.path.length - 1) ? view.theme.fg : view.theme.accent;
        ctx.fillText(seg, x, pl.top + BC / 2);
        st.crumbs.push({ x0: x, x1: x + wseg, idx: p });
        x += wseg;
      }
      ctx.restore();
    },
    onClick: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return;
      var st = view.core._pstate["treemap-drill"]; if (!st) return;
      var pl = view.plot;
      if (cursor.py <= pl.top + BC) {                          // breadcrumb click → pop
        for (var k = 0; k < st.crumbs.length; k++) {
          if (cursor.px >= st.crumbs[k].x0 && cursor.px <= st.crumbs[k].x1) {
            st.path = st.path.slice(0, st.crumbs[k].idx + 1); st.focus = st.path[st.path.length - 1];
            view.core.render(); return;
          }
        }
        return;
      }
      var ax = pl.left, ay = pl.top + BC, aw = pl.width, ah = pl.height - BC;
      var kids = st.focus.children || [], rects = st.focus.rects || [];
      for (var i = 0; i < kids.length; i++) {
        var r = rects[i]; if (!r) continue;
        var px = ax + r.x * aw, py = ay + r.y * ah, w = r.w * aw, h = r.h * ah;
        if (cursor.px >= px && cursor.px <= px + w && cursor.py >= py && cursor.py <= py + h) {
          if (kids[i].children && kids[i].children.length) {  // drill in
            st.path = st.path.concat([kids[i]]); st.focus = kids[i]; view.core.render();
          }
          return;
        }
      }
    },
    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var st = view.core._pstate["treemap-drill"]; if (!st) return null;
      var pl = view.plot, ax = pl.left, ay = pl.top + BC, aw = pl.width, ah = pl.height - BC;
      var kids = st.focus.children || [], rects = st.focus.rects || [];
      for (var i = 0; i < kids.length; i++) {
        var r = rects[i]; if (!r) continue;
        var px = ax + r.x * aw, py = ay + r.y * ah;
        if (cursor.px >= px && cursor.px <= px + r.w * aw && cursor.py >= py && cursor.py <= py + r.h * ah) {
          return { hud: (kids[i].name || "") + ": " + fmt(kids[i].value) + ((kids[i].children && kids[i].children.length) ? " (클릭=드릴다운)" : "") };
        }
      }
      return null;
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["treemap-drill"] = P;
})();
