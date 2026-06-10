// Headless runtime test for batch H — boot the 5 rendered HTML (4 xy-core + 1 field-core) in a
// Canvas/DOM stub, exercise interactions, assert zero console errors + correct wiring.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "bezierCurveTo", "setLineDash",
   "strokeRect", "translate", "rotate", "drawImage", "putImageData"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.createImageData = (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
  c.canvas = { width: 1200, height: 720 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null, width: 0, height: 0,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, insertBefore(n) { this.children.unshift(n); return n; },
    get firstChild() { return this.children[0] || null; },
    removeChild() {}, remove() {}, addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return RECT; }, setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
    click() {},
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
global.window = global; global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };

function run(name) {
  const html = fs.readFileSync(path.join(OUT, name), "utf-8");
  const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
  cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
  global.document = { body, createElement: (t) => makeEl(t),
    getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
  const errors = []; console.error = (...a) => errors.push(a.join(" "));
  let threw = null;
  try { for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s); }
  catch (e) { threw = e; }
  return { g: global.window.__graph, errors, threw };
}
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
function ex(g) { if (!g) return; g.autoFit(); g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false }); }

let r = run("capability.html");
ok("capability booted (count + normal fit)", !!r.g && !r.threw && r.g.series.length === 2);
ok("capability spec lines (USL/LSL/Target)", r.g && r.g.opts.pluginConfig["threshold-lines"].lines.length === 3);
ex(r.g); ok("capability no console.error", r.errors.length === 0);

r = run("paris.html");
ok("paris log-log", !!r.g && r.g.xLog === true && r.g.yLog === true);
ok("paris data + fit series", r.g && r.g.series.length === 2);
ok("paris ΔKth + KIC lines", r.g && r.g.opts.pluginConfig["threshold-lines"].lines.length === 2);
ex(r.g); ok("paris no console.error", r.errors.length === 0);

r = run("campbell.html");
ok("campbell 2 modes + 3 order rays = 5 series", !!r.g && r.g.series.length === 5);
ex(r.g); ok("campbell no console.error", r.errors.length === 0);

r = run("km.html");
ok("km step curve", !!r.g && r.g.opts.curve === "step");
ok("km 2 group series", r.g && r.g.series.length === 2);
ok("km censoring markers", r.g && r.g.opts.pluginConfig["named-markers"].markers.length > 0);
ex(r.g); ok("km no console.error", r.errors.length === 0);

r = run("mac.html");
ok("mac field-core booted (4x4)", !!r.g && !r.threw && r.g.nx === 4 && r.g.ny === 4);
ok("mac engine registered", typeof global.window.GraphEngines["field-core"] === "function");
if (r.g) { r.g.autoFit(); }
ok("mac no console.error", r.errors.length === 0);

r = run("weibull.html");
ok("weibull booted (data + fit, log-x)", !!r.g && !r.threw && r.g.series.length === 2 && r.g.xLog === true);
ex(r.g); ok("weibull no console.error", r.errors.length === 0);

r = run("vquiver.html");
ok("quiver field-core booted (5x5 + vectors)", !!r.g && !r.threw && r.g.nx === 5 && r.g.ny === 5 && !!r.g.vectors);
ok("quiver arrowsOnly (no raster)", r.g && r.g.opts.arrowsOnly === true && r.g._off === null);
if (r.g) { r.g.autoFit(); r.g._onMove && r.g._onMove({ clientX: 300, clientY: 180, pointerId: 1 }); }
ok("quiver _drawArrows no console.error", r.errors.length === 0);

r = run("rainflow.html");
ok("rainflow field-core heatmap booted", !!r.g && !r.threw && r.g.nx > 0 && r.g.ny > 0 && !r.g.vectors);
if (r.g) { r.g.autoFit(); }
ok("rainflow no console.error", r.errors.length === 0);

console.log(fail ? "NODE PHASEH: FAILURES" : "NODE PHASEH OK");
process.exitCode = fail;
