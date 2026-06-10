// Headless test for nyquist-plot / root-locus: verify equalAspect actually equalizes
// px-per-unit (so the unit circle is round) + unit-circle plugin boots with no console error.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 600, height: 360 };   // non-square → equalize must act
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
function ppu(g) {
  const p = g.plot;
  return { x: (p.right - p.left) / (g.view.x[1] - g.view.x[0]),
           y: (p.bottom - p.top) / (g.view.y[1] - g.view.y[0]) };
}

let r = run("nyquist.html");
ok("nyquist booted, no throw", !!r.g && !r.threw);
ok("unit-circle plugin loaded", r.g && r.g.plugins.some((p) => p.id === "unit-circle"));
let s = r.g && ppu(r.g);
ok("equalAspect: px/unit equal (x≈y)", s && Math.abs(s.x - s.y) <= 1e-3 * Math.max(s.x, s.y));
if (r.g) { r.g.autoFit(); s = ppu(r.g); }
ok("equalAspect holds after autoFit", s && Math.abs(s.x - s.y) <= 1e-3 * Math.max(s.x, s.y));
if (r.g) r.g._onWheel({ clientX: 300, clientY: 180, deltaY: -120, preventDefault() {}, shiftKey: false, ctrlKey: true });
ok("nyquist no console.error", r.errors.length === 0);

r = run("rootlocus.html");
ok("root-locus booted, no throw", !!r.g && !r.threw);
s = r.g && ppu(r.g);
ok("root-locus equalAspect", s && Math.abs(s.x - s.y) <= 1e-3 * Math.max(s.x, s.y));
ok("root-locus pole/zero markers", r.g && r.g.opts.pluginConfig["named-markers"].markers.length === 3);
if (r.g) r.g.autoFit();
ok("root-locus no console.error", r.errors.length === 0);

// control: a non-equalAspect type must NOT be equalized (sanity that the option is the cause)
r = run("base_xy.html");
s = r.g && ppu(r.g);
ok("base-xy is NOT equal-aspect (option off)", s && Math.abs(s.x - s.y) > 1e-3 * Math.max(s.x, s.y));

console.log(fail ? "NODE CONTROLS: FAILURES" : "NODE CONTROLS OK");
process.exitCode = fail;
