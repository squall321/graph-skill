// Headless runtime test for phase-1 plugins: boot each rendered HTML (engine+plugins+boot)
// with a Canvas/DOM stub, exercise hover, and assert the plugins run without console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");

const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "bezierCurveTo", "setLineDash",
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
    appendChild(c) { this.children.push(c); return c; }, removeChild() {},
    addEventListener() {}, removeEventListener() {}, getBoundingClientRect() { return RECT; },
    setPointerCapture() {}, releasePointerCapture() {},
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
    click() {},
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
global.window = global;
global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };

function run(htmlPath) {
  const html = fs.readFileSync(htmlPath, "utf-8");
  const cfg = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]); // engine, plugins, boot
  const root = makeEl("div"); const cfgEl = makeEl("script"); cfgEl.textContent = cfg; const body = makeEl("body");
  global.document = { body, createElement: (t) => makeEl(t),
    getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
  const errors = []; console.error = (...a) => errors.push(a.join(" "));
  for (const s of scripts) (0, eval)(s);
  return { g: global.window.__graph, errors };
}

let fail = 0;
const ok = (label, cond) => { console.log((cond ? "  ok  " : " FAIL ") + label); if (!cond) fail = 1; };

// stress-strain: hover -> live-tangent HUD shows Et; markers/regions draw clean
{
  const { g, errors } = run(path.join(OUT, "stress_strain.html"));
  ok("stress-strain booted", !!g && g.plugins.length === 3);
  g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false });
  ok("hover HUD shows Et (live-tangent)", g.hud.innerHTML.includes("Et"));
  ok("stress-strain no console.error", errors.length === 0);
}
// force-displacement: hover -> stiffness N/mm
{
  const { g, errors } = run(path.join(OUT, "force_displacement.html"));
  g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false });
  ok("force-disp HUD shows N/mm (stiffness)", g.hud.innerHTML.includes("N/mm"));
  ok("force-disp no console.error", errors.length === 0);
}
// correlation-scatter: regression-fit draws (onDrawOver during autoFit render)
{
  const { g, errors } = run(path.join(OUT, "correlation.html"));
  ok("correlation booted (regression-fit)", !!g && g.plugins.length === 1);
  ok("correlation no console.error", errors.length === 0);
}

console.log(fail ? "NODE PHASE1: FAILURES" : "NODE PHASE1 OK");
process.exitCode = fail;
