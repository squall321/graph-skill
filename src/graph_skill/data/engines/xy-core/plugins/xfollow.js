/* xfollow — detail panel that zooms its x-domain to the range published by a sibling
   xbrush overview (focus+context). Pure subscriber; no drawing. config: { group } */
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
    id: "xfollow",
    order: 10,
    onInit: function (core) {
      var c = core.opts.pluginConfig && core.opts.pluginConfig.xfollow; if (!c) return;
      var me = (window.__xfollowN = (window.__xfollowN || 0) + 1);
      bus().sub(c.group, function (data, src) {
        if (src === me || !data || !core.view) return;
        core.view.x = [data.x0, data.x1];
        core.xLog = false;
        if (core.render) core.render();
      });
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["xfollow"] = P;
})();
