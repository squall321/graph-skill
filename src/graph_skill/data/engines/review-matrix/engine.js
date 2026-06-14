/* ===========================================================================
 * review-matrix — design-state checklist / comparison table (engine family).
 * Renders a DOM grid (states × items). Cells: number / status / text / image / graph.
 * Graph cells RE-MOUNT a real graph-skill engine (xy-core...) in-document — no new chart
 * code. Auto interactions: search/filter, group collapse, sticky label col, diff vs
 * baseline, spec pass/fail/warn badges, cell modal (full graph / image lightbox),
 * export-source. Dispatched via window.GraphEngines["review-matrix"].
 * =========================================================================== */
(function () {
  "use strict";

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function fmtNum(v, unit) {
    if (v == null || v === "" || (typeof v === "number" && !isFinite(v))) return "—";
    var s = typeof v === "number" ? String(Math.round(v * 1e4) / 1e4) : String(v);
    return unit ? s + " " : s;
  }
  function evalSpec(value, spec) {
    if (!spec || typeof value !== "number" || !isFinite(value)) return null;
    if (spec.max != null && value > spec.max) return "fail";
    if (spec.min != null && value < spec.min) return "fail";
    if (spec.warn_at != null) {
      if (spec.goal === "min" && value >= spec.warn_at) return "warn";
      if (spec.goal === "max" && value <= spec.warn_at) return "warn";
    }
    return "pass";
  }

  function heatColor(t) {                        // 3-stop green→yellow→red for conditional formatting
    t = t < 0 ? 0 : (t > 1 ? 1 : t);
    var stops = [[22, 163, 74], [234, 179, 8], [220, 38, 38]];
    var seg = t < 0.5 ? 0 : 1, f = t < 0.5 ? t / 0.5 : (t - 0.5) / 0.5;
    var a = stops[seg], b = stops[seg + 1];
    return "rgb(" + Math.round(a[0] + (b[0] - a[0]) * f) + "," + Math.round(a[1] + (b[1] - a[1]) * f) + "," + Math.round(a[2] + (b[2] - a[2]) * f) + ")";
  }

  function mountGraph(div, gp, override) {
    var fac = window.GraphEngines && window.GraphEngines[(gp || {}).engine];
    if (!gp) { div.innerHTML = '<div class="gs-error">graph 정의 누락(ref)</div>'; return null; }
    if (typeof fac !== "function") {
      div.innerHTML = '<div class="gs-error">내장 그래프 엔진 없음: ' + (gp.engine || "?") + "</div>";
      return null;
    }
    var opts = Object.assign({}, gp.options || {}, override || {});
    var core = fac(div, opts);
    var fam = (window.GraphPlugins && window.GraphPlugins[gp.engine]) || {};
    (gp.plugins || []).forEach(function (id) { if (fam[id] && core.use) core.use(fam[id]); });
    if (core.setAssets) core.setAssets(gp.assets || {});
    else if (core.setData) core.setData((gp.assets || {}).series || []);
    if (core.autoFit) core.autoFit();
    return core;
  }

  function ReviewMatrix(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-matrix");
    this.opts = options || {};
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this.query = "";
    this._collapsed = {};
    (this.opts.collapsed_groups || []).forEach(function (g) { this._collapsed[g] = true; }, this);
    this._buildModal();
  }

  ReviewMatrix.prototype.use = function () { return this; };  // matrix logic is in the engine
  ReviewMatrix.prototype.autoFit = function () {};

  ReviewMatrix.prototype.setAssets = function (a) {
    this.a = a || {};
    this.states = (this.a.states || []).filter(function (s) { return s && s.id; });
    this.baseline = this.a.baseline || (this.states[0] && this.states[0].id) || null;
    this.gp = this.a.graph_payloads || {};
    this._build();
  };

  ReviewMatrix.prototype._build = function () {
    var self = this;
    // remove any prior table/toolbar (keep modal)
    Array.prototype.slice.call(this.root.querySelectorAll(".gs-mx-toolbar,.gs-mx-wrap")).forEach(function (n) { n.remove(); });

    // ---- toolbar ----
    var bar = el("div", "gs-mx-toolbar");
    if (this.opts.title) bar.appendChild(el("div", "gs-mx-title", this.opts.title));
    var search = el("input", "gs-mx-search");
    search.type = "search"; search.placeholder = "검색 (항목/값)…";
    search.addEventListener("input", function () { self.query = search.value.toLowerCase(); self._applyFilter(); });
    bar.appendChild(search);
    var bExp = el("button", "gs-mx-btn", "펼침/접힘");
    bExp.addEventListener("click", function () { self._toggleAll(); });
    bar.appendChild(bExp);
    var bTheme = el("button", "gs-mx-btn", "◐");
    bTheme.title = "테마";
    bTheme.addEventListener("click", function () {
      var order = ["auto", "light", "dark"], cur = self.root.getAttribute("data-theme") || "auto";
      self.root.setAttribute("data-theme", order[(order.indexOf(cur) + 1) % 3]);
    });
    bar.appendChild(bTheme);
    var bCsv = el("button", "gs-mx-btn", "CSV");
    bCsv.title = "표를 CSV로 내보내기";
    bCsv.addEventListener("click", function () { self._exportCSV(); });
    bar.appendChild(bCsv);
    var bExport = el("button", "gs-mx-btn", "{} source");
    bExport.title = "정규화 source JSON 내보내기";
    bExport.addEventListener("click", function () { self._exportSource(); });
    bar.appendChild(bExport);
    this.root.appendChild(bar);
    if (this.root.style && this.root.style.setProperty) {
      this.root.style.setProperty("--gs-mx-th-top", (bar.offsetHeight || 47) + "px");   // sticky header offset
    }
    [bExp, bTheme, bCsv, bExport].forEach(function (b) { b.setAttribute("aria-label", b.title || b.textContent); });
    search.setAttribute("aria-label", "표 검색");

    // ---- table ----
    var wrap = el("div", "gs-mx-wrap");
    var table = el("table", "gs-mx-table");
    var thead = el("thead"), htr = el("tr");
    htr.appendChild(el("th", "gs-col-label", ""));
    this.states.forEach(function (s) {
      var th = el("th", null, s.label || s.id);
      if (s.id === self.baseline) th.title = "baseline";
      htr.appendChild(th);
    });
    thead.appendChild(htr); table.appendChild(thead);

    var tbody = el("tbody");
    this._itemRows = [];
    this._groups = {};
    var groupOrder = [], seen = {};
    (this.a.items || []).forEach(function (it) {
      var g = it.group || "";
      if (!seen[g]) { seen[g] = 1; groupOrder.push(g); }
    });

    groupOrder.forEach(function (g) {
      if (g) {
        var gtr = el("tr", "gs-grp-row");
        var gtd = el("td"); gtd.colSpan = self.states.length + 1;
        gtd.appendChild(el("span", "gs-caret", self._collapsed[g] ? "▶" : "▼"));
        gtd.appendChild(document.createTextNode(" " + g));
        gtr.appendChild(gtd);
        gtr.addEventListener("click", function () { self._toggleGroup(g); });
        tbody.appendChild(gtr);
        self._groups[g] = { row: gtr };
      }
      (self.a.items || []).forEach(function (it) {
        if ((it.group || "") !== g) return;
        self._appendItemRow(tbody, it, g);
      });
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    this.root.appendChild(wrap);

    // mount graph cells (now attached to DOM)
    (this._mounts || []).forEach(function (m) {
      try { mountGraph(m.div, m.gp); }
      catch (e) {
        m.div.innerHTML = '<div class="gs-error">내장 그래프 렌더 실패</div>';
        if (window.console && console.error) console.error("[review-matrix] cell mount failed", e);
      }
    });
    this._applyFilter();
  };

  ReviewMatrix.prototype._appendItemRow = function (tbody, it, group) {
    var self = this;
    var tr = el("tr");
    var label = el("td", "gs-col-label");
    label.appendChild(document.createTextNode(it.label || it.id));
    if (it.unit) label.appendChild(el("span", "gs-unit", " [" + it.unit + "]"));
    tr.appendChild(label);

    var searchText = (it.label || "") + " " + (it.group || "") + " " + (it.tags || []).join(" ");

    if (it.overlay && this.gp[it.overlay]) {
      var td = el("td"); td.colSpan = this.states.length;
      var gdiv = el("div", "gs-cell-graph gs-cell-graph-wide");
      if (it.h) gdiv.style.height = it.h + "px";   // e.g. a full-width gantt inside a work-plan
      td.appendChild(gdiv);
      (this._mounts = this._mounts || []).push({ div: gdiv, gp: this.gp[it.overlay] });
      gdiv.addEventListener("click", function () { self._openGraph(self.gp[it.overlay], it.label); });
      tr.appendChild(td);
    } else {
      var baseVal = this._numAt(it, this.baseline);
      this.states.forEach(function (s) {
        var c = (it.cells || {})[s.id];
        var td = self._cellTd(it, s, c, baseVal);
        searchText += " " + (td._search || "");
        tr.appendChild(td);
      });
    }
    tbody.appendChild(tr);
    this._itemRows.push({ tr: tr, group: group, text: searchText.toLowerCase() });
  };

  ReviewMatrix.prototype._numAt = function (it, stateId) {
    var c = (it.cells || {})[stateId];
    return c && (c.kind === "number" || c.kind === "status") && typeof c.value === "number" ? c.value : null;
  };

  ReviewMatrix.prototype._cellTd = function (it, state, c, baseVal) {
    var self = this;
    var td = el("td");
    if (!c || c.kind === "empty") { td.appendChild(el("span", "gs-cell-empty", "—")); td._search = ""; return td; }

    if (c.kind === "graph" && this.gp[c.ref]) {
      var gdiv = el("div", "gs-cell-graph");
      gdiv.title = "클릭하여 확대";
      td.appendChild(gdiv);
      (this._mounts = this._mounts || []).push({ div: gdiv, gp: this.gp[c.ref] });
      gdiv.addEventListener("click", function () { self._openGraph(self.gp[c.ref], it.label + " · " + (state.label || state.id)); });
      td._search = "graph";
      return td;
    }
    if (c.kind === "image" && c.image) {
      var img = document.createElement("img");
      img.className = "gs-cell-img";
      img.src = c.image.mode === "inline" ? ("data:" + (c.image.mime || "image/png") + ";base64," + c.image.data) : (/^\s*(?:https?:)?\/\//i.test(c.image.ref || "") ? "" : (c.image.ref || ""));
      img.alt = it.label || "";
      img.addEventListener("click", function () { self._openImage(img.src, it.label); });
      td.appendChild(img); td._search = "image";
      return td;
    }
    if (c.kind === "text") {
      td.appendChild(document.createTextNode(c.value == null ? "" : String(c.value)));
      if (c.link && c.link.href) {
        var a = document.createElement("a"); a.className = "gs-cell-link"; a.href = c.link.href; a.textContent = " " + (c.link.text || "link");
        td.appendChild(a);
      }
      td._search = String(c.value || "");
      return td;
    }
    if (c.kind === "status") {
      var st = c.status || "pass";
      var b = el("span", "gs-badge gs-" + st, st.toUpperCase());
      td.appendChild(b);
      if (c.value != null) td.appendChild(document.createTextNode(" " + fmtNum(c.value, it.unit) + (it.unit || "")));
      td._search = st + " " + (c.value || "");
      return td;
    }
    if (c.kind === "heat") {                       // conditional formatting / heat cell
      var hmin = c.min != null ? c.min : 0, hmax = c.max != null ? c.max : 1;
      var ht = hmax > hmin ? (c.value - hmin) / (hmax - hmin) : 0;
      if (c.scale === "highgood") ht = 1 - ht;
      var hbg = c.color || heatColor(ht);
      td.style.background = hbg;
      var hm = /rgb\((\d+),(\d+),(\d+)\)/.exec(hbg);
      var hl = hm ? (0.299 * +hm[1] + 0.587 * +hm[2] + 0.114 * +hm[3]) / 255 : (ht > 0.5 ? 0.3 : 0.7);
      td.style.color = hl > 0.55 ? "#111827" : "#fff";
      td.appendChild(el("span", "gs-cell-num", fmtNum(c.value, it.unit) + (it.unit && c.value != null ? it.unit : "")));
      td._search = String(c.value); return td;
    }
    if (c.kind === "bar") {                        // mini horizontal bar
      var bmax = c.max != null ? c.max : 1, pct = bmax > 0 ? Math.max(0, Math.min(100, (c.value || 0) / bmax * 100)) : 0;
      var bw = el("div", "gs-cell-bar"), bf = el("div", "gs-cell-bar-fill");
      bf.style.width = pct + "%"; if (c.color) bf.style.background = c.color;
      bw.appendChild(bf); td.appendChild(bw);
      td.appendChild(el("span", "gs-cell-barlab", fmtNum(c.value, it.unit) + (it.unit || "")));
      td._search = String(c.value); return td;
    }
    if (c.kind === "delta") {                       // value + trend arrow
      td.appendChild(el("span", "gs-cell-num", fmtNum(c.value, it.unit) + (it.unit && c.value != null ? it.unit : "")));
      if (c.delta != null && Math.abs(c.delta) > 1e-12) {
        var dc = c.goal === "min" ? (c.delta < 0 ? "gs-good" : "gs-bad") : c.goal === "max" ? (c.delta > 0 ? "gs-good" : "gs-bad") : "gs-neutral";
        td.appendChild(el("span", "gs-diff " + dc, (c.delta > 0 ? "▲" : "▼") + fmtNum(Math.abs(c.delta))));
      }
      td._search = String(c.value); return td;
    }
    if (c.kind === "badges") {                      // multiple tags
      var tags = c.tags || (c.value != null ? [c.value] : []);
      for (var bi = 0; bi < tags.length; bi++) td.appendChild(el("span", "gs-badge gs-tag", String(tags[bi])));
      td._search = tags.join(" "); return td;
    }
    if (c.kind === "rating") {                      // n / max dots
      var rv = Math.round(c.value || 0), rmax = c.max || 5, rs = el("span", "gs-rating");
      for (var ri = 0; ri < rmax; ri++) rs.appendChild(el("span", ri < rv ? "gs-dot gs-on" : "gs-dot"));
      td.appendChild(rs); td._search = String(rv); return td;
    }
    // number
    var span = el("span", "gs-cell-num", fmtNum(c.value, it.unit) + (it.unit && c.value != null ? (it.unit) : ""));
    td.appendChild(span);
    // spec badge (left border)
    var status = evalSpec(c.value, it.spec || (this.a.spec && this.a.spec.targets && this.a.spec.targets[it.id]));
    if (status) td.className = "gs-spec-" + status;
    // diff vs baseline
    if (this.opts.diff && baseVal != null && state.id !== this.baseline && typeof c.value === "number") {
      var d = c.value - baseVal;
      if (Math.abs(d) > 1e-9) {
        var goal = it.spec && it.spec.goal;
        var cls = goal === "min" ? (d < 0 ? "gs-good" : "gs-bad") : goal === "max" ? (d > 0 ? "gs-good" : "gs-bad") : "gs-neutral";
        td.appendChild(el("span", "gs-diff " + cls, (d > 0 ? "▲" : "▼") + fmtNum(Math.abs(d))));
      }
    }
    td._search = String(c.value || "");
    return td;
  };

  // ---- interactions ----
  ReviewMatrix.prototype._applyFilter = function () {
    var q = this.query, anyVisible = false;
    for (var i = 0; i < this._itemRows.length; i++) {
      var r = this._itemRows[i];
      var hidden = (this._collapsed[r.group] === true) || (q && r.text.indexOf(q) < 0);
      r.tr.classList.toggle("gs-row-hidden", !!hidden);
      if (!hidden) anyVisible = true;
    }
    if (this._noRes) this._noRes.style.display = (q && !anyVisible) ? "block" : "none";
    if (q && !anyVisible && !this._noRes) {
      this._noRes = document.createElement("div");
      this._noRes.className = "gs-mx-nores";
      this._noRes.textContent = "검색 결과 없음";
      var w = this.root.querySelector(".gs-mx-wrap");
      if (w) w.appendChild(this._noRes);
    }
    for (var g in this._groups) {
      if (this._groups.hasOwnProperty(g)) {
        var caret = this._groups[g].row.querySelector(".gs-caret");
        if (caret) caret.textContent = this._collapsed[g] ? "▶" : "▼";
        // hide a group header entirely if searching and no child matches
        if (q) {
          var any = this._itemRows.some(function (r) { return r.group === g && r.text.indexOf(q) >= 0; });
          this._groups[g].row.classList.toggle("gs-row-hidden", !any);
        } else {
          this._groups[g].row.classList.remove("gs-row-hidden");
        }
      }
    }
  };
  ReviewMatrix.prototype._toggleGroup = function (g) { this._collapsed[g] = !this._collapsed[g]; this._applyFilter(); };
  ReviewMatrix.prototype._toggleAll = function () {
    var anyOpen = false, g;
    for (g in this._groups) if (this._groups.hasOwnProperty(g) && !this._collapsed[g]) anyOpen = true;
    for (g in this._groups) if (this._groups.hasOwnProperty(g)) this._collapsed[g] = anyOpen;
    this._applyFilter();
  };

  // ---- modal ----
  ReviewMatrix.prototype._buildModal = function () {
    var self = this;
    var m = el("div", "gs-modal");
    var box = el("div", "gs-modal-box");
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
    var head = el("div", "gs-modal-head");
    this._modalTitle = el("span", null, "");
    var x = el("button", "gs-x", "×");
    x.setAttribute("aria-label", "닫기 (Esc)"); x.title = "닫기 (Esc)";
    x.addEventListener("click", function () { self._closeModal(); });
    head.appendChild(this._modalTitle); head.appendChild(x);
    this._modalBody = el("div", "gs-modal-body");
    box.appendChild(head); box.appendChild(this._modalBody); m.appendChild(box);
    m.addEventListener("click", function (e) { if (e.target === m) self._closeModal(); });
    if (document.addEventListener) document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && m.classList.contains("open")) self._closeModal();
    });
    this.root.appendChild(m);
    this.modal = m; this._mX = x;
  };
  ReviewMatrix.prototype._closeModal = function () {
    if (this._modalGraph && this._modalGraph.destroy) this._modalGraph.destroy();
    this._modalGraph = null;
    this._modalBody.innerHTML = "";
    this.modal.classList.remove("open");
  };
  ReviewMatrix.prototype._openGraph = function (gp, title) {
    this._modalTitle.textContent = title || "";
    this._modalBody.innerHTML = "";
    var div = el("div", "gs-modal-graph");
    this._modalBody.appendChild(div);
    this.modal.classList.add("open"); if (this._mX && this._mX.focus) this._mX.focus();
    this._modalGraph = mountGraph(div, gp, { legend: { show: true }, exportButtons: ["png", "csv"], controlbar: true });
  };
  ReviewMatrix.prototype._openImage = function (src, title) {
    this._modalTitle.textContent = title || "";
    this._modalBody.innerHTML = "";
    var img = document.createElement("img"); img.className = "gs-modal-img"; img.src = src;
    this._modalBody.appendChild(img);
    this.modal.classList.add("open"); if (this._mX && this._mX.focus) this._mX.focus();
  };

  ReviewMatrix.prototype._cellText = function (c, unit) {
    if (!c) return "";
    if (c.kind === "status") return (c.status || "") + (c.value != null ? " " + c.value : "");
    if (c.kind === "badges") return (c.tags || []).join("|");
    if (c.kind === "graph") return "(graph)";
    if (c.kind === "image") return "(image)";
    return c.value != null ? String(c.value) + (unit ? " " + unit : "") : "";
  };
  ReviewMatrix.prototype._exportCSV = function () {
    var self = this, esc2 = function (v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    var rows = [["item"].concat(this.states.map(function (st) { return st.label || st.id; }))];
    (this.a.items || []).forEach(function (it) {
      var row = [it.label || it.id];
      self.states.forEach(function (st) { row.push(self._cellText((it.cells || {})[st.id], it.unit)); });
      rows.push(row);
    });
    var csv = "\ufeff" + rows.map(function (r) { return r.map(esc2).join(","); }).join("\n");
    var a2 = document.createElement("a");
    a2.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
    a2.download = (this.opts.title || "table") + ".csv";
    document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
  };
  ReviewMatrix.prototype._exportSource = function () {
    var node = document.getElementById("graph-config");
    var txt = node ? node.textContent : JSON.stringify({ engine: "review-matrix", assets: this.a, options: this.opts });
    var a = document.createElement("a");
    a.href = "data:application/json;charset=utf-8," + encodeURIComponent(txt);
    a.download = (this.opts.title || "review-matrix") + ".json";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["review-matrix"] = function (mount, options) { return new ReviewMatrix(mount, options); };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["review-matrix"] = window.GraphPlugins["review-matrix"] || {};
})();
