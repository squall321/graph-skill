/* domain-toggle — the "FFT toggle": switch the chart between time and frequency domains.
   The recipe pre-computes both; this plugin swaps series + axes (+ peak markers) at runtime.
   config: { start:"time"|"freq", time:{series,axes}, freq:{series,axes}, peaks:[markers] } */
(function () {
  "use strict";
  function cfgOf(core) { return (core.opts.pluginConfig && core.opts.pluginConfig["domain-toggle"]) || null; }

  var P = {
    id: "domain-toggle",
    order: 5,
    onInit: function (core) {
      var c = cfgOf(core);
      if (!c || !c.time || !c.freq) return;
      core._pstate["domain-toggle"] = { cur: c.start || "freq" };
      var b = document.createElement("button");
      b.className = "gs-btn"; b.type = "button";
      b.textContent = (c.start === "time") ? "FFT →" : "⏱ time";
      b.title = "시간 ↔ 주파수(FFT) 토글";
      b.addEventListener("click", function () { P._toggle(core, b); });
      if (core.controlbar) core.controlbar.insertBefore(b, core.controlbar.firstChild);
    }
  };

  P._toggle = function (core, b) {
    var c = cfgOf(core), st = core._pstate["domain-toggle"];
    if (!c) return;
    st.cur = st.cur === "freq" ? "time" : "freq";
    var d = c[st.cur];
    core.opts.axes = d.axes;
    core.xLog = !!(d.axes.x && d.axes.x.log);
    core.yLog = !!(d.axes.y && d.axes.y.log);
    if (core.opts.pluginConfig["named-markers"]) {
      core.opts.pluginConfig["named-markers"].markers = st.cur === "freq" ? (c.peaks || []) : [];
    }
    b.textContent = st.cur === "freq" ? "⏱ time" : "FFT →";
    if (core._syncButtons) core._syncButtons();
    core.setData(d.series);  // recomputes domain + autoFit + render
  };

  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["domain-toggle"] = P;
})();
