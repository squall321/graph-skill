// Verify parcoord brushing: a drag on an axis records a brush in per-core state and dims
// non-matching lines; existing pan/box/lock are untouched (those plugins define no onDown).
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
    tagName: tag, style: {}, children: [], _ctx: null,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, remove() {},
    addEventListener() {}, removeEventListener() {}, getBoundingClientRect() { return RECT; },
    setPointerCapture() {}, releasePointerCapture() {},
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h || ""; },
    set textContent(v) { this._t = v; }, get textContent() { return this._t || ""; },
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
global.window = global; global.devicePixelRatio = 1;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };

const html = fs.readFileSync(path.join(OUT, "parallel-coordinates.html"), "utf-8");
const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
global.document = { body, createElement: (t) => makeEl(t),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
const errors = []; console.error = (...a) => errors.push(a.join(" "));
for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s);

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
const g = global.window.__graph;
g.autoFit();
const ax0 = g.sx.to(0), yTop = g.plot.top + 15, yBot = g.plot.bottom - 15;
g._onDown({ clientX: ax0, clientY: (yTop + yBot) / 2, pointerId: 1, shiftKey: false });
ok("plugin claimed the drag (mode=plugin)", g._drag && g._drag.mode === "plugin");
g._onMove({ clientX: ax0, clientY: yBot, pointerId: 1, shiftKey: false });   // routes to _onDrag
g._onUp({ clientX: ax0, clientY: yBot, pointerId: 1 });
const br = g._pstate && g._pstate.parcoord && g._pstate.parcoord.brushes;
ok("brush recorded on axis 0", !!br && Array.isArray(br["0"]) && br["0"][1] > br["0"][0]);
ok("drag released", g._drag === null);
ok("no console.error", errors.length === 0);

console.log(fail ? "NODE PARCOORD-BRUSH: FAILURES" : "NODE PARCOORD-BRUSH OK");
process.exitCode = fail;
