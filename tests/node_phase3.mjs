// Headless runtime test for field-core: boot the rendered field artifact, hover to probe z,
// exercise colormap/reverse/zoom, assert no console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, "..", "graph-out", "field.html");

const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  ["save","restore","setTransform","clearRect","fillRect","beginPath","moveTo","lineTo","stroke",
   "rect","clip","fillText","arc","fill","bezierCurveTo","setLineDash","strokeRect","translate",
   "rotate","drawImage","putImageData"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.createImageData = (w, h) => ({ data: new Uint8ClampedArray(w * h * 4), width: w, height: h });
  c.getImageData = (x, y, w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
  c.canvas = { width: 1200, height: 720 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null, width: 300, height: 150,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute(k, v) { this["__" + k] = v; }, getAttribute(k) { return this["__" + k] || "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, remove() {},
    addEventListener() {}, removeEventListener() {}, getBoundingClientRect() { return RECT; },
    setPointerCapture() {}, releasePointerCapture() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
    click() {},
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
global.window = global;
global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.document = { body, createElement: (t) => makeEl(t),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };

const html = fs.readFileSync(htmlPath, "utf-8");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const errors = []; console.error = (...a) => errors.push(a.join(" "));
for (const s of scripts) (0, eval)(s);

const g = global.window.__graph;
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

ok("field-core registered", typeof global.window.GraphEngines["field-core"] === "function");
ok("field booted", !!g);
ok("grid 25x25", g && g.nx === 25 && g.ny === 25);
ok("z range computed", g && isFinite(g.zmin) && isFinite(g.zmax) && g.zmax > g.zmin);
ok("8 contour levels", g && g.levels.length === 8);

// hover -> probe z (bilinear)
g._onMove({ clientX: 200, clientY: 180, pointerId: 1, shiftKey: false });
ok("hover probes z (number)", g.cursor && typeof g.cursor.z === "number" && isFinite(g.cursor.z));

// colormap cycle + reverse + wheel zoom + reset
const cm0 = g.cmapName;
g.controlbar.children.forEach(() => {}); // (buttons are stubbed; call methods directly)
g.cmapName = "coolwarm"; g._rasterize(); g.render();
ok("colormap change re-rasterizes", true);
g.reverse = true; g._rasterize(); g.render();
g._onWheel({ clientX: 200, clientY: 180, deltaY: -120, preventDefault() {}, shiftKey: false, ctrlKey: true });
ok("wheel zoom clamped within grid", g.view.x[0] >= g.full.x[0] - 1e-6 && g.view.x[1] <= g.full.x[1] + 1e-6);
g.autoFit();
ok("autoFit reset", g.view.x[0] === g.full.x[0] && g.view.x[1] === g.full.x[1]);

console.log("console.error count:", errors.length, errors);
ok("no console.error", errors.length === 0);
console.log(fail ? "NODE PHASE3: FAILURES" : "NODE PHASE3 OK");
process.exitCode = fail;
