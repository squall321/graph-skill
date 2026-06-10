/* graph-skill bootstrap — family-agnostic. Reads #graph-config, dispatches to the engine
   registry window.GraphEngines[family], registers plugins, loads assets. */
(function () {
  "use strict";
  var el = document.getElementById("graph-config");
  if (!el) { console.error("[graph-skill] missing #graph-config"); return; }
  var cfg;
  try { cfg = JSON.parse(el.textContent); }
  catch (e) { console.error("[graph-skill] invalid config JSON", e); return; }

  var mount = document.getElementById("graph-root");
  var registry = window.GraphEngines || {};
  var factory = registry[cfg.engine];
  if (typeof factory !== "function") {
    console.error("[graph-skill] unknown engine family: " + cfg.engine);
    if (mount) mount.innerHTML = '<div class="gs-error">엔진 패밀리를 찾을 수 없음: ' + cfg.engine + "</div>";
    return;
  }

  try {
    var inst = factory(mount, cfg.options || {});
    var fam = (window.GraphPlugins && window.GraphPlugins[cfg.engine]) || {};
    (cfg.plugins || []).forEach(function (id) {
      if (fam[id] && inst.use) inst.use(fam[id]);
      else if (id) console.warn("[graph-skill] plugin not found for " + cfg.engine + ": " + id);
    });
    var assets = cfg.assets || {};
    if (inst.setAssets) inst.setAssets(assets);
    else if (inst.setData) inst.setData(assets.series || []);
    if (inst.autoFit) inst.autoFit();
    window.__graph = inst; // debug / Playwright handle

    // a11y naming + theme sync are best-effort extras — they must never break boot
    try {
      var label = (cfg.options && cfg.options.title) || document.title || "graph";
      if (mount.querySelectorAll) {
        Array.prototype.slice.call(mount.querySelectorAll("canvas")).forEach(function (cv) {
          cv.setAttribute("role", "img");
          cv.setAttribute("aria-label", label);
        });
      }
      var applyTheme = function (th) {
        if (!/^(light|dark|auto)$/.test(th)) return;
        var targets = [];
        if (mount.getAttribute && mount.getAttribute("data-theme")) targets.push(mount);   // engine themed the mount itself
        if (mount.querySelectorAll) targets = targets.concat(Array.prototype.slice.call(mount.querySelectorAll("[data-theme]")));
        if (!targets.length) targets = [mount];
        targets.forEach(function (r) { if (r && r.setAttribute) r.setAttribute("data-theme", th); });
        if (inst.render) inst.render();
        else if (inst._draw) inst._draw();
        else if (inst._render) inst._render();
      };
      var qm = /[?&]theme=(light|dark|auto)/.exec((window.location && window.location.search) || "");
      if (qm) applyTheme(qm[1]);
      if (window.addEventListener) {
        window.addEventListener("message", function (ev) {
          var d = ev && ev.data;
          if (d && d.type === "gs-theme" && typeof d.theme === "string") applyTheme(d.theme);
        });
      }
    } catch (e3) { if (window.console && console.warn) console.warn("[graph-skill] extras skipped", e3); }
  } catch (e2) {
    console.error("[graph-skill] engine boot failed", e2);
    if (mount) mount.innerHTML = '<div class="gs-error">그래프 렌더 실패: ' + (e2 && e2.message) + "</div>";
  }
})();
