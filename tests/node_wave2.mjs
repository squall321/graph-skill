// Headless runtime test for wave-2: area-plot / stacked-area / waterfall-chart / violin-plot.
// Exercises the 3 new plugins (area-fill onDrawUnder, waterfall + violin onDrawOver). No errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 520, height: 320 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "bezierCurveTo", "setLineDash",
   "strokeRect", "translate", "rotate", "drawImage"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 1040, height: 640 };
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
const ex = (g) => { if (g) { g.autoFit(); g._onMove({ clientX: 260, clientY: 160, pointerId: 1, shiftKey: false }); } };

let r = run("area-plot.html");
ok("area-plot booted + area-fill cfg", !!r.g && !r.threw && !!r.g.opts.pluginConfig["area-fill"]);
ex(r.g); ok("area-plot no console.error", r.errors.length === 0);

r = run("stacked-area.html");
ok("stacked-area 3 series + stacked cfg", !!r.g && r.g.series.length === 3 && r.g.opts.pluginConfig["area-fill"].stacked === true);
ex(r.g); ok("stacked-area no console.error", r.errors.length === 0);

r = run("waterfall-chart.html");
const wf = r.g && r.g.opts.pluginConfig["waterfall"];
ok("waterfall 5 floating bars", !!r.g && !r.threw && wf && wf.bars.length === 5);
ex(r.g); ok("waterfall no console.error", r.errors.length === 0);

r = run("violin-plot.html");
const vi = r.g && r.g.opts.pluginConfig["violin"];
ok("violin 3 group densities", !!r.g && !r.threw && vi && vi.groups.length === 3 && vi.groups[0].dens.length > 0);
ex(r.g); ok("violin no console.error", r.errors.length === 0);

console.log(fail ? "NODE WAVE2: FAILURES" : "NODE WAVE2 OK");
process.exitCode = fail;
