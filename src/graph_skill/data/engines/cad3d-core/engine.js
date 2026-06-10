/* cad3d-core — WebGL 3D viewer family (three.js r128, vendored + sha256-pinned).
   Loads an inline GLB (assets.model.glb = base64) and gives orbit/pan/zoom, a section
   (clipping) plane, wireframe/solid, theme, fit, and PNG export. The interaction set is
   baked here (engine = fixed asset); the LLM only supplies model + colorbar/title/z meta. */
(function () {
  "use strict";
  var T = window.THREE;

  function el(cls) { var d = document.createElement("div"); d.className = cls; return d; }

  function CAD3D(mount, options) {
    this.root = mount;
    this.root.classList.add("gs-cad-root");
    this.opts = options || {};
    this.root.setAttribute("data-theme", this.opts.theme || "auto");
    this._dark = this._resolveDark();

    this.canvas = document.createElement("canvas");
    this.canvas.setAttribute("tabindex", "0");   // keyboard focus (OrbitControls arrow pan)
    this.root.appendChild(this.canvas);
    this.renderer = new T.WebGLRenderer({ canvas: this.canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.localClippingEnabled = true;

    this.scene = new T.Scene();
    this.camera = new T.PerspectiveCamera(45, 1, 0.01, 1e6);
    this.camera.position.set(1, 1, 1);
    this.scene.add(new T.AmbientLight(0xffffff, 0.65));
    var d1 = new T.DirectionalLight(0xffffff, 0.7); d1.position.set(1, 1, 1); this.scene.add(d1);
    var d2 = new T.DirectionalLight(0xffffff, 0.3); d2.position.set(-1, -0.6, -1); this.scene.add(d2);

    this.controls = new T.OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true; this.controls.dampingFactor = 0.1;
    // plain wheel keeps scrolling the host page; Ctrl/⌘+wheel reaches OrbitControls zoom.
    // Capture on the ROOT (ancestor) so it runs before OrbitControls' canvas listener.
    var selfW = this;
    this.root.addEventListener("wheel", function (e) {
      if (!(e.ctrlKey || e.metaKey)) { e.stopPropagation(); selfW._zoomHint(); }
    }, { capture: true, passive: true });

    this.clip = new T.Plane(new T.Vector3(0, -1, 0), 0);
    this.clipOn = false; this.wire = false;
    this.model = null; this._center = new T.Vector3(); this._size = new T.Vector3(1, 1, 1);

    this._buildDOM();
    var self = this;
    this._ro = new ResizeObserver(function () { self._resize(); });
    this._ro.observe(this.root);
    this._resize();
    this._startLoop();
  }

  CAD3D.prototype._zoomHint = function () {
    var self = this;
    if (!this._zh) {
      this._zh = document.createElement("div");
      this._zh.className = "gs-cad-zoom-hint";
      var mac = typeof navigator !== "undefined" && navigator.platform && navigator.platform.indexOf("Mac") >= 0;
      this._zh.textContent = (mac ? "⌘" : "Ctrl") + " + 스크롤로 확대/축소 · 드래그=회전";
      this.root.appendChild(this._zh);
    }
    this._zh.classList.add("gs-show");
    clearTimeout(this._zhT);
    this._zhT = setTimeout(function () { self._zh.classList.remove("gs-show"); }, 1400);
  };

  CAD3D.prototype.use = function () { return this; };

  CAD3D.prototype.setAssets = function (a) {
    var m = (a && a.model) || {};
    this.zmeta = (a && a.z) || null;
    this.zrange = m.zrange || null;
    this.cmapLUT = m.lut || null;
    if (this.opts.title) this._title.textContent = this.opts.title;
    this._buildColorbar();
    if (m.points) this._buildPoints(m);
    else if (m.vertices) this._buildRaw(m);
    else if (m.glb) this._loadGLB(m.glb);
    this._render();
  };

  // 3D point cloud / scatter — THREE.Points, per-point colors (scalar→LUT baked by recipe).
  CAD3D.prototype._buildPoints = function (m) {
    if (this.model) this.scene.remove(this.model);
    var g = new T.BufferGeometry();
    g.setAttribute("position", new T.BufferAttribute(new Float32Array(m.points), 3));
    if (m.colors) g.setAttribute("color", new T.Uint8BufferAttribute(m.colors, 3, true));
    var mat = new T.PointsMaterial({ size: m.size || 0.04, sizeAttenuation: true,
      vertexColors: !!m.colors, color: m.colors ? 0xffffff : 0x2563eb });
    mat.clippingPlanes = this.clipOn ? [this.clip] : [];
    this.points = new T.Points(g, mat);
    this.model = new T.Group(); this.model.add(this.points);
    this.scene.add(this.model);
    this._fit();
  };
  CAD3D.prototype.setData = function (d) { this.setAssets({ model: d }); };

  // raw mesh path (deformed shape / mode shape) — build BufferGeometry + warp by displacement.
  CAD3D.prototype._buildRaw = function (m) {
    if (this.model) this.scene.remove(this.model);
    var g = new T.BufferGeometry();
    var verts = new Float32Array(m.vertices);
    this._base = verts.slice();
    g.setAttribute("position", new T.BufferAttribute(verts, 3));
    if (m.indices) g.setIndex(m.indices);
    if (m.colors) g.setAttribute("color", new T.Uint8BufferAttribute(m.colors, 3, true));
    g.computeVertexNormals();
    var mat = new T.MeshStandardMaterial({ vertexColors: !!m.colors, color: m.colors ? 0xffffff : 0x9aa6b2,
      metalness: 0.08, roughness: 0.7, side: T.DoubleSide });
    mat.clippingPlanes = this.clipOn ? [this.clip] : [];
    this.mesh = new T.Mesh(g, mat);
    this.model = new T.Group(); this.model.add(this.mesh);
    this.disp = m.displacement ? new Float32Array(m.displacement) : null;
    this.modes = (m.modes || []).map(function (md) { return { name: md.name, freq: md.freq, disp: new Float32Array(md.disp) }; });
    this.warpScale = (m.scale != null ? m.scale : 1.0); this.modeIdx = 0; this.playing = false; this.animPhase = 0;
    this._undef = new T.LineSegments(new T.WireframeGeometry(g.clone()),
      new T.LineBasicMaterial({ color: 0x8a93a3, transparent: true, opacity: 0.22 }));
    this._undef.visible = false; this.model.add(this._undef);
    this.scene.add(this.model);
    this._buildDeformUI();
    this._applyWarp();
    this._fit();
  };
  CAD3D.prototype._activeDisp = function () { return (this.modes && this.modes.length) ? this.modes[this.modeIdx].disp : this.disp; };
  CAD3D.prototype._applyWarp = function () {
    if (!this.mesh || !this._base) return;
    var d = this._activeDisp(), pos = this.mesh.geometry.attributes.position.array;
    var s = this.warpScale * ((this.playing && this.modes && this.modes.length) ? Math.sin(this.animPhase) : 1.0);
    for (var i = 0; i < pos.length; i++) pos[i] = this._base[i] + (d ? s * d[i] : 0);
    this.mesh.geometry.attributes.position.needsUpdate = true;
    this.mesh.geometry.computeVertexNormals();
  };
  CAD3D.prototype._buildDeformUI = function () {
    if (!this.disp && !(this.modes && this.modes.length)) return;
    var self = this, wrap = el("gs-cad-deform");
    var lab = document.createElement("span"); lab.textContent = "변형 배율"; wrap.appendChild(lab);
    var sl = document.createElement("input"); sl.type = "range"; sl.min = 0; sl.max = (this.warpScale * 3) || 3;
    sl.step = ((this.warpScale * 3) || 3) / 100; sl.value = this.warpScale;
    sl.addEventListener("input", function () { self.warpScale = parseFloat(sl.value); self._applyWarp(); self._render(); });
    wrap.appendChild(sl);
    var ub = document.createElement("button"); ub.className = "gs-cad-btn"; ub.textContent = "원형상"; ub.title = "원형상(undeformed) 오버레이";
    ub.addEventListener("click", function () { self._undef.visible = !self._undef.visible; ub.setAttribute("aria-pressed", self._undef.visible ? "true" : "false"); self._render(); });
    wrap.appendChild(ub);
    if (this.modes && this.modes.length) {
      var sel = document.createElement("select");
      this.modes.forEach(function (md, i) { var o = document.createElement("option"); o.value = i; o.textContent = (md.name || ("Mode " + (i + 1))) + (md.freq != null ? (" · " + md.freq + " Hz") : ""); sel.appendChild(o); });
      sel.addEventListener("change", function () { self.modeIdx = parseInt(sel.value, 10) || 0; self._applyWarp(); self._render(); });
      wrap.appendChild(sel);
      var pb = document.createElement("button"); pb.className = "gs-cad-btn"; pb.textContent = "▶"; pb.title = "모드 애니메이션 재생/정지";
      pb.addEventListener("click", function () { self.playing = !self.playing; pb.textContent = self.playing ? "❚❚" : "▶"; });
      wrap.appendChild(pb);
    }
    this.root.appendChild(wrap); this._deform = wrap;
  };

  CAD3D.prototype._loadGLB = function (b64) {
    var bin = atob(b64), n = bin.length, buf = new Uint8Array(n), i;
    for (i = 0; i < n; i++) buf[i] = bin.charCodeAt(i);
    var self = this;
    new T.GLTFLoader().parse(buf.buffer, "", function (g) {
      if (self.model) self.scene.remove(self.model);
      self.model = g.scene;
      self.model.traverse(function (o) {
        if (o.isMesh) {
          if (o.geometry.attributes && o.geometry.attributes.color) o.material.vertexColors = true;
          o.material.side = T.DoubleSide;
          o.material.clippingPlanes = self.clipOn ? [self.clip] : [];
          if (!(o.geometry.attributes && o.geometry.attributes.normal)) o.geometry.computeVertexNormals();
          o._solidMat = o.material;
        }
      });
      self.scene.add(self.model);
      self._fit();
      self._render();
    }, function (err) { console.error("[cad3d] GLB parse failed", err && err.message); });
  };

  CAD3D.prototype._fit = function () {
    if (!this.model) return;
    var box = new T.Box3().setFromObject(this.model);
    if (box.isEmpty()) return;
    box.getCenter(this._center); box.getSize(this._size);
    var maxd = Math.max(this._size.x, this._size.y, this._size.z) || 1;
    this.controls.target.copy(this._center);
    var dist = maxd / (2 * Math.tan(this.camera.fov * Math.PI / 360)) * 1.7;
    this.camera.position.set(this._center.x + dist * 0.7, this._center.y + dist * 0.6, this._center.z + dist * 0.9);
    this.camera.near = maxd / 1000; this.camera.far = maxd * 2000; this.camera.updateProjectionMatrix();
    this._clipLo = this._center.y - this._size.y / 2; this._clipHi = this._center.y + this._size.y / 2;
    this.clip.constant = this._center.y;
    if (this._clipSlider) { this._clipSlider.min = this._clipLo; this._clipSlider.max = this._clipHi; this._clipSlider.value = this._center.y; this._clipSlider.step = (this._clipHi - this._clipLo) / 100 || 1; }
    this.controls.update();
  };
  CAD3D.prototype.autoFit = function () { this._fit(); this._render(); };

  CAD3D.prototype._resize = function () {
    var r = this.root.getBoundingClientRect();
    var w = Math.max(120, Math.floor(r.width || 480)), h = Math.max(120, Math.floor(r.height || 360));
    this.W = w; this.H = h;
    this.renderer.setPixelRatio(Math.max(1, window.devicePixelRatio || 1));
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this._render();
  };

  CAD3D.prototype._render = function () {
    if (!this.renderer) return;
    this.renderer.setClearColor(this._dark ? 0x0f1419 : 0xf4f6f8, 1);
    this.renderer.render(this.scene, this.camera);
  };
  CAD3D.prototype._startLoop = function () {
    var self = this;
    if (typeof window.requestAnimationFrame !== "function") { this._render(); return; }
    (function loop() { self._raf = window.requestAnimationFrame(loop); if (self.controls) self.controls.update(); if (self.playing) { self.animPhase += 0.12; self._applyWarp(); } self._render(); })();
  };

  CAD3D.prototype._setClip = function (on) {
    this.clipOn = on;
    if (this.model) this.model.traverse(function (o) { if (o.isMesh) o.material.clippingPlanes = on ? [window.__cad_clip] : []; });
    this._render();
  };
  CAD3D.prototype._setWire = function (on) {
    this.wire = on;
    if (this.model) this.model.traverse(function (o) { if (o.isMesh) o.material.wireframe = on; });
    this._render();
  };

  CAD3D.prototype._resolveDark = function () {
    var th = this.opts.theme || "auto";
    if (th === "dark") return true;
    if (th === "light") return false;
    try { return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches; } catch (e) { return false; }
  };

  // ---- DOM (controlbar + colorbar + title) ----
  CAD3D.prototype._buildDOM = function () {
    this._title = el("gs-cad-title"); this.root.appendChild(this._title);
    this.bar = el("gs-cad-bar"); this.root.appendChild(this.bar);
    var self = this;
    this._btn("⟲", "전체 보기 (fit)", function () { self.autoFit(); });
    this._btn("◧", "단면(clip) on/off", function (b) {
      self.clipOn = !self.clipOn; window.__cad_clip = self.clip; self._setClip(self.clipOn);
      b.setAttribute("aria-pressed", self.clipOn ? "true" : "false");
      self._clipWrap.style.display = self.clipOn ? "flex" : "none";
    });
    this._btn("▦", "와이어프레임", function (b) { self._setWire(!self.wire); b.setAttribute("aria-pressed", self.wire ? "true" : "false"); });
    this._btn("◐", "테마", function () { self._dark = !self._dark; self.root.setAttribute("data-theme", self._dark ? "dark" : "light"); self._render(); });
    this._btn("PNG", "PNG 내보내기", function () { self._png(); });
    // clip slider
    this._clipWrap = el("gs-cad-clip"); this._clipWrap.style.display = "none";
    var lab = document.createElement("span"); lab.textContent = "단면 위치"; this._clipWrap.appendChild(lab);
    this._clipSlider = document.createElement("input"); this._clipSlider.type = "range";
    this._clipSlider.addEventListener("input", function () { self.clip.constant = parseFloat(self._clipSlider.value); self._render(); });
    this._clipWrap.appendChild(this._clipSlider);
    this.root.appendChild(this._clipWrap);
  };
  CAD3D.prototype._btn = function (label, title, onclick) {
    var b = document.createElement("button"); b.className = "gs-cad-btn"; b.type = "button";
    b.textContent = label; b.title = title;
    b.addEventListener("click", function () { onclick(b); });
    this.bar.appendChild(b); return b;
  };
  CAD3D.prototype._buildColorbar = function () {
    if (this._cbar) { this._cbar.remove(); this._cbar = null; }
    if (!this.zrange || !this.cmapLUT) return;
    var cb = el("gs-cad-colorbar");
    var grad = []; for (var i = 0; i <= 10; i++) { var c = this.cmapLUT[Math.round(i / 10 * (this.cmapLUT.length - 1))]; grad.push("rgb(" + c[0] + "," + c[1] + "," + c[2] + ") " + (i * 10) + "%"); }
    var bar = el("gs-cad-cbar-grad"); bar.style.background = "linear-gradient(to top," + grad.join(",") + ")";
    cb.appendChild(bar);
    var lbl = el("gs-cad-cbar-lab");
    var unit = this.zmeta && this.zmeta.unit ? " [" + this.zmeta.unit + "]" : "";
    lbl.innerHTML = "<b>" + (this.zmeta && this.zmeta.label || "") + unit + "</b><span>" + fmt(this.zrange[1]) + "</span><span>" + fmt(this.zrange[0]) + "</span>";
    cb.appendChild(lbl);
    this.root.appendChild(cb); this._cbar = cb;
  };
  CAD3D.prototype._png = function () {
    this._render();
    try {
      var a = document.createElement("a"); a.href = this.canvas.toDataURL("image/png");
      a.download = (this.opts.title || "cad3d") + ".png";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
    } catch (e) { console.error("[cad3d] png export failed", e && e.message); }
  };

  function fmt(v) { if (v == null || !isFinite(v)) return ""; var a = Math.abs(v); return (a >= 1e4 || (a > 0 && a < 1e-2)) ? v.toExponential(2) : (Math.round(v * 1000) / 1000).toString(); }

  window.GraphEngines = window.GraphEngines || {};
  window.GraphEngines["cad3d-core"] = function (mount, options) { return new CAD3D(mount, options); };
})();
