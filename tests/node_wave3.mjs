// Headless runtime test for wave-3: nichols-chart / parallel-coordinates (xy-core) +
// wind-rose (polar-core wedge drawing). Boot + exercise + zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 460, height: 420 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "bezierCurveTo", "setLineDash",
   "strokeRect", "translate", "rotate", "drawImage"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 920, height: 840 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, insertBefore(n) { this.children.unshift(n); return n; },
    get firstChild() { return this.children[0] || null; },
    removeChild() {}, remove() {}, addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return RECT; }, setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; }, click() {},
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

let r = run("nichols-chart.html");
ok("nichols booted + refs + crit", !!r.g && !r.threw && r.g.opts.pluginConfig["threshold-lines"].lines.length === 2 && r.g.opts.pluginConfig["named-markers"].markers.length === 1);
if (r.g) { r.g.autoFit(); r.g._onMove({ clientX: 230, clientY: 200, pointerId: 1, shiftKey: false }); }
ok("nichols no console.error", r.errors.length === 0);

r = run("parallel-coordinates.html");
const pc = r.g && r.g.opts.pluginConfig.parcoord;
ok("parcoord booted (4 dims, rows)", !!r.g && !r.threw && pc && pc.dims.length === 4 && pc.rows.length > 0);
if (r.g) { r.g.autoFit(); }
ok("parcoord no console.error", r.errors.length === 0);

r = run("wind-rose.html");
ok("wind-rose polar-core booted (rose data)", !!r.g && !r.threw && !!r.g.rose && r.g.rose.bins.length === 4);
ok("wind-rose engine registered", typeof global.window.GraphEngines["polar-core"] === "function");
if (r.g) r.g.autoFit();
ok("wind-rose no console.error", r.errors.length === 0);

console.log(fail ? "NODE WAVE3: FAILURES" : "NODE WAVE3 OK");
process.exitCode = fail;
