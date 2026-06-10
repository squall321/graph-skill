/* xsync — shared crosshair across sibling xy-core instances in the SAME document
   (e.g. multitrack panels). Each instance publishes its hover x to a named group on a
   tiny window-level bus; peers draw a synced vertical line at that x. No engine surgery,
   no cross-instance data — just an x value. config (pluginConfig.xsync): { group } */
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
  var P = {
    id: "xsync",
    order: 55,
    onInit: function (core) {
      var c = core.opts.pluginConfig && core.opts.pluginConfig.xsync; if (!c) return;
      var me = (window.__xsyncN = (window.__xsyncN || 0) + 1);
      var st = core._pstate.xsync = { group: c.group, me: me, peerX: null };
      bus().sub(c.group, function (data, src) {
        if (src === st.me) return;
        st.peerX = data ? data.x : null;
        core.render();
      });
    },
    onHover: function (view, cursor) {
      var c = view.pluginConfig && view.pluginConfig.xsync; if (!c) return null;
      var st = view.core._pstate.xsync; if (!st) return null;
      bus().pub(c.group, st.me, cursor ? { x: cursor.dataX } : null);
      return null;
    },
    onDrawOver: function (ctx, view) {
      var st = view.core._pstate.xsync; if (!st || st.peerX == null) return;
      var pl = view.plot, px = view.scaleX(st.peerX);
      if (px < pl.left || px > pl.left + pl.width) return;
      ctx.save();
      ctx.strokeStyle = view.theme.accent; ctx.globalAlpha = 0.55; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(px, pl.top); ctx.lineTo(px, pl.top + pl.height); ctx.stroke();
      ctx.restore();
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["xsync"] = P;
})();
