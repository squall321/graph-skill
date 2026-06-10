// Headless runtime test for polar-core: boot the antenna pattern + radar, confirm the engine
// renders (rmin/rmax computed, _pt maps), zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 400, height: 400 };
function makeCtx() {
  const c = {};
  ["save","restore","setTransform","clearRect","fillRect","beginPath","moveTo","lineTo","stroke",
   "rect","clip","fillText","arc","fill","closePath","setLineDash","strokeRect","translate","rotate","drawImage"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 800, height: 800 };
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
  for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s);
  return { g: global.window.__graph, errors };
}
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

let r = run("pattern.html");
ok("polar-core registered", typeof global.window.GraphEngines["polar-core"] === "function");
ok("radiation pattern booted", !!r.g && r.g.series.length === 1 && r.g.series[0].closed === true);
ok("r-range computed", r.g && isFinite(r.g.rmin) && isFinite(r.g.rmax) && r.g.rmax > r.g.rmin);
ok("_pt maps a polar point", r.g && isFinite(r.g._pt(0, r.g.rmax).px) && isFinite(r.g._pt(90, r.g.rmin).py));
ok("pattern no console.error", r.errors.length === 0);

r = run("radar.html");
ok("radar booted (5 angle labels, 2 series)", !!r.g && r.g.opts.angleLabels.length === 5 && r.g.series.length === 2 && r.g.series[0].closed === true);
ok("radar no console.error", r.errors.length === 0);

console.log(fail ? "NODE PHASE8: FAILURES" : "NODE PHASE8 OK");
process.exitCode = fail;
