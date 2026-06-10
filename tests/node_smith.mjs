// Headless runtime test for smith-core: boot the Smith chart, draw R/X grid + Γ trajectory,
// exercise hover (z = (1+Γ)/(1-Γ) HUD), assert zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 400, height: 400 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "setLineDash", "strokeRect"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 800, height: 800 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, remove() {},
    addEventListener() {}, removeEventListener() {}, getBoundingClientRect() { return RECT; },
    setPointerCapture() {}, releasePointerCapture() {},
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
global.window = global; global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };

const html = fs.readFileSync(path.join(OUT, "smith-chart.html"), "utf-8");
const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
global.document = { body, createElement: (t) => makeEl(t),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
const errors = []; console.error = (...a) => errors.push(a.join(" "));
let threw = null;
try { for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s); }
catch (e) { threw = e; }

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
const g = global.window.__graph;
ok("smith-core engine registered", typeof global.window.GraphEngines["smith-core"] === "function");
ok("smith chart booted (1 series, Γ points)", !!g && !threw && g.series.length === 1 && g.series[0].gamma.length > 0);
ok("Γ→pixel maps", g && isFinite(g._px(0.3, 0.2).px) && isFinite(g._px(0, 0).py));
if (g) { var p0 = g._px(g.series[0].gamma[0][0], g.series[0].gamma[0][1]); g._onMove({ clientX: p0.px, clientY: p0.py }); }
ok("hover at Γ point sets cursor + HUD (z=R+jX)", g && g.cursor != null && /z =/.test(g.hud.innerHTML));
if (g) g.autoFit();
ok("no console.error", errors.length === 0);

console.log(fail ? "NODE SMITH: FAILURES" : "NODE SMITH OK");
process.exitCode = fail;
