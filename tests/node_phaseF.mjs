// Headless runtime test for the (F) batch: boot pareto / qq / ecdf / spc rendered HTML in a
// Canvas/DOM stub, exercise render + hover + zoom + log toggle, assert zero console errors.
// Covers the new threshold-lines axis:"y2" path, curve:"step", and mixed bar+line on a 2nd axis.
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
  try {
    for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s);
  } catch (e) { threw = e; }
  return { g: global.window.__graph, errors, threw };
}

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

// --- pareto: bars (left) + cumulative line (right axis) + y2 threshold (80%) ---
let r = run("pareto.html");
ok("pareto booted, no throw", !!r.g && !r.threw);
ok("pareto 2 series", r.g && r.g.series.length === 2);
ok("pareto has bar + right axis", r.g && r.g._hasBar === true && r.g._hasRight === true);
ok("pareto secondary scale built (sy2)", r.g && !!r.g.sy2 && isFinite(r.g.sy2.to(80)));
if (r.g) { r.g.autoFit(); r.g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false }); r.g._onWheel({ clientX: 300, clientY: 180, deltaY: -120, preventDefault() {}, shiftKey: false, ctrlKey: true }); }
ok("pareto no console.error", r.errors.length === 0);

// --- qq: scatter + regression fit line ---
r = run("qq.html");
ok("qq booted, no throw", !!r.g && !r.threw);
ok("qq 1 series (markers)", r.g && r.g.series.length === 1);
if (r.g) { r.g.autoFit(); r.g._onMove({ clientX: 280, clientY: 170, pointerId: 1, shiftKey: false }); }
ok("qq regression-fit config present", r.g && !!r.g.opts.pluginConfig["regression-fit"]);
ok("qq no console.error", r.errors.length === 0);

// --- ecdf: step curve ---
r = run("ecdf.html");
ok("ecdf booted, no throw", !!r.g && !r.threw);
ok("ecdf curve=step", r.g && r.g.opts.curve === "step");
if (r.g) { r.g.autoFit(); r.g._setLog("x", true); r.g._setLog("x", false); }
ok("ecdf no console.error", r.errors.length === 0);

// --- spc: control limits (threshold y) + OOC markers (named-markers) ---
r = run("spc.html");
ok("spc booted, no throw", !!r.g && !r.threw);
const tl = r.g && r.g.opts.pluginConfig["threshold-lines"];
const nm = r.g && r.g.opts.pluginConfig["named-markers"];
ok("spc 3 control lines (CL/UCL/LCL)", tl && tl.lines.length === 3);
ok("spc 2 OOC markers", nm && nm.markers.length === 2);
if (r.g) { r.g.autoFit(); r.g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false }); }
ok("spc no console.error", r.errors.length === 0);

console.log(fail ? "NODE PHASEF: FAILURES" : "NODE PHASEF OK");
process.exitCode = fail;
