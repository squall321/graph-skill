/* xbrush — context overview with a draggable/resizable x-window. Publishes the window's
   data x-range on the bus; the linked detail panel (xfollow) zooms to it. The overview
   itself always shows the full series. config (pluginConfig.xbrush): { group } */
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
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  var P = {
    id: "xbrush",
    order: 58,
    onInit: function (core) {
      var c = core.opts.pluginConfig && core.opts.pluginConfig.xbrush; if (!c) return;
      core._pstate.xbrush = { group: c.group, me: (window.__xbrushN = (window.__xbrushN || 0) + 1), win: null, drag: null };
    },
    _pub: function (view) {
      var st = view.core._pstate.xbrush;
      bus().pub(st.group, st.me, { x0: st.win[0], x1: st.win[1] });
    },
    onDrawOver: function (ctx, view) {
      var st = view.core._pstate.xbrush; if (!st) return;
      var dom = view.domain.x, pl = view.plot;
      if (st.win == null) { var sp = dom[1] - dom[0]; st.win = [dom[0] + sp * 0.30, dom[0] + sp * 0.70]; P._pub(view); }
      var x0 = view.scaleX(st.win[0]), x1 = view.scaleX(st.win[1]);
      ctx.save();
      ctx.fillStyle = view.theme.sub || "#888"; ctx.globalAlpha = 0.16;
      ctx.fillRect(pl.left, pl.top, x0 - pl.left, pl.height);
      ctx.fillRect(x1, pl.top, pl.left + pl.width - x1, pl.height);
      ctx.globalAlpha = 1; ctx.strokeStyle = view.theme.accent; ctx.lineWidth = 1.5;
      ctx.strokeRect(x0, pl.top + 1, x1 - x0, pl.height - 2);
      ctx.fillStyle = view.theme.accent;
      ctx.fillRect(x0 - 2, pl.top + pl.height / 2 - 10, 4, 20);
      ctx.fillRect(x1 - 2, pl.top + pl.height / 2 - 10, 4, 20);
      ctx.restore();
    },
    onHover: function (view, c) {
      var st = view.core._pstate.xbrush;
      if (!st || !st.win || !c || !view.core.canvas) return null;
      var x0 = view.scaleX(st.win[0]), x1 = view.scaleX(st.win[1]);
      var cur = "";
      if (Math.abs(c.px - x0) <= 6 || Math.abs(c.px - x1) <= 6) cur = "ew-resize";
      else if (c.px > x0 && c.px < x1) cur = "grab";
      view.core.canvas.style.cursor = cur;
      return null;
    },
    onDown: function (view, c) {
      var cf = view.pluginConfig && view.pluginConfig.xbrush; if (!cf) return false;
      var st = view.core._pstate.xbrush; if (!st || !st.win) return false;
      var x0 = view.scaleX(st.win[0]), x1 = view.scaleX(st.win[1]), m = 6;
      if (Math.abs(c.px - x0) <= m) st.drag = { mode: "l" };
      else if (Math.abs(c.px - x1) <= m) st.drag = { mode: "r" };
      else if (c.px > x0 && c.px < x1) st.drag = { mode: "move", at: view.invX(c.px) };
      else { var w = st.win[1] - st.win[0], cx = view.invX(c.px); st.win = [cx - w / 2, cx + w / 2]; st.drag = { mode: "move", at: cx }; P._clamp(view); P._pub(view); view.core.render(); }
      return true;
    },
    onDrag: function (view, c) {
      var st = view.core._pstate.xbrush; if (!st || !st.drag) return;
      var dx = view.invX(c.px);
      if (st.drag.mode === "l") st.win[0] = Math.min(dx, st.win[1] - 1e-9);
      else if (st.drag.mode === "r") st.win[1] = Math.max(dx, st.win[0] + 1e-9);
      else { var d = dx - st.drag.at; st.win[0] += d; st.win[1] += d; st.drag.at = dx; }
      P._clamp(view); P._pub(view); view.core.render();
    },
    onUp: function (view) { var st = view.core._pstate.xbrush; if (st) st.drag = null; },
    _clamp: function (view) {
      var st = view.core._pstate.xbrush, dom = view.domain.x, w = st.win[1] - st.win[0];
      if (st.win[0] < dom[0]) { st.win[0] = dom[0]; st.win[1] = Math.min(dom[1], dom[0] + w); }
      if (st.win[1] > dom[1]) { st.win[1] = dom[1]; st.win[0] = Math.max(dom[0], dom[1] - w); }
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["xbrush"] = P;
})();
