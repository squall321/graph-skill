// Headless runtime test for batch G — boot the 7 engineering-2D rendered HTML in a Canvas/DOM
// stub, exercise interactions, assert zero console errors + correct plugin/axis wiring.
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
   "strokeRect", "translate", "rotate", "drawImage"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 1200, height: 720 };
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
  let threw = null;
  try { for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s); }
  catch (e) { threw = e; }
  return { g: global.window.__graph, errors, threw };
}
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
function exercise(g) {
  if (!g) return;
  g.autoFit();
  g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false });
  g._onWheel({ clientX: 300, clientY: 180, deltaY: -120, preventDefault() {}, shiftKey: false, ctrlKey: true });
}

let r = run("main_effects.html");
ok("main-effects booted (3 factor series)", !!r.g && !r.threw && r.g.series.length === 3);
ok("main-effects categorical x (8 cats)", r.g && r.g._cats && r.g._cats.length === 8);
ok("main-effects grand-mean line", r.g && r.g.opts.pluginConfig["threshold-lines"].lines.length === 1);
exercise(r.g); ok("main-effects no console.error", r.errors.length === 0);

r = run("interaction.html");
ok("interaction booted (2 series)", !!r.g && !r.threw && r.g.series.length === 2);
ok("interaction categorical x (3)", r.g && r.g._cats && r.g._cats.length === 3);
exercise(r.g); ok("interaction no console.error", r.errors.length === 0);

r = run("transient.html");
const tnm = r.g && r.g.opts.pluginConfig["named-markers"];
const ttl = r.g && r.g.opts.pluginConfig["threshold-lines"];
ok("transient 2 peak markers", tnm && tnm.markers.length === 2);
ok("transient 1 limit line", ttl && ttl.lines.length === 1);
exercise(r.g); ok("transient no console.error", r.errors.length === 0);

r = run("convergence.html");
ok("convergence log-y", !!r.g && r.g.yLog === true);
ok("convergence tolerance line", r.g && r.g.opts.pluginConfig["threshold-lines"].lines.length === 1);
exercise(r.g); ok("convergence no console.error", r.errors.length === 0);

r = run("cfd_line.html");
const cb = r.g && r.g.opts.pluginConfig["error-bars"];
ok("cfd-line booted (3 series)", !!r.g && r.g.series.length === 3);
ok("cfd-line error bars on experiment", cb && cb.bars.length === 5);
exercise(r.g); ok("cfd-line no console.error", r.errors.length === 0);

r = run("nonlinear_ld.html");
ok("nonlinear live-tangent", !!r.g && !!r.g.opts.pluginConfig["live-tangent"]);
ok("nonlinear yield+ultimate markers", r.g && r.g.opts.pluginConfig["named-markers"].markers.length === 2);
exercise(r.g); ok("nonlinear no console.error", r.errors.length === 0);

r = run("sn_curve.html");
ok("s-n log-x", !!r.g && r.g.xLog === true);
ok("s-n fatigue-limit + design-point", r.g && r.g.opts.pluginConfig["threshold-lines"].lines.length === 1 && r.g.opts.pluginConfig["named-markers"].markers.length === 1);
exercise(r.g); ok("s-n no console.error", r.errors.length === 0);

console.log(fail ? "NODE PHASEG: FAILURES" : "NODE PHASEG OK");
process.exitCode = fail;
