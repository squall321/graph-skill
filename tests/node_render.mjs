// Headless execution test for xy-core: run the rendered HTML's engine+boot in Node with a
// minimal Canvas/DOM stub. Catches runtime errors in setData/render/hover/zoom/export
// without needing a real browser. Usage: node tests/node_render.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, "..", "graph-out", "base_xy.html");
const html = fs.readFileSync(htmlPath, "utf-8");
const cfgText = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
const engineSrc = fs.readFileSync(path.join(here, "..", "src", "graph_skill", "data", "engines", "xy-core", "engine.js"), "utf-8");
const bootSrc = fs.readFileSync(path.join(here, "..", "src", "graph_skill", "data", "shell", "boot.js"), "utf-8");

const errors = [];
const warns = [];
console.error = (...a) => errors.push(a.join(" "));
console.warn = (...a) => warns.push(a.join(" "));

const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  const methods = ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath",
    "moveTo", "lineTo", "stroke", "rect", "clip", "fillText", "arc", "fill", "bezierCurveTo",
    "setLineDash", "strokeRect", "translate", "rotate", "drawImage"];
  methods.forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 1200, height: 720 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; },
    removeChild() {}, addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return RECT; },
    setPointerCapture() {}, releasePointerCapture() {},
    get offsetWidth() { return 80; }, get offsetHeight() { return 40; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
    click() {},
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}

const root = makeEl("div");
const cfgEl = makeEl("script"); cfgEl.textContent = cfgText;
const body = makeEl("body");

global.window = global;
global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.document = {
  body,
  createElement: (t) => makeEl(t),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null),
};

// run engine then boot
(0, eval)(engineSrc);
(0, eval)(bootSrc);

const g = global.window.__graph;
const ok = (label, cond) => { console.log((cond ? "  ok  " : " FAIL ") + label); if (!cond) process.exitCode = 1; };

ok("engine registered (window.GraphEngines['xy-core'])", typeof global.window.GraphEngines["xy-core"] === "function");
ok("instance booted (window.__graph)", !!g);
ok("series loaded (3)", g && g.series.length === 3);
ok("domain computed", g && g.full && isFinite(g.full.x[0]) && isFinite(g.full.y[1]));

// exercise interactions
g.autoFit();
g._onMove({ clientX: 300, clientY: 180, pointerId: 1, shiftKey: false });
ok("hover produced cursor+hits", !!(g.cursor && g.cursor.hits && g.cursor.hits.length === 3));
g._onWheel({ clientX: 300, clientY: 180, deltaY: -120, preventDefault() {}, shiftKey: false, ctrlKey: true });
ok("wheel zoom changed view", g.view.x[0] !== g.full.x[0]);
g._setLog("y", true);
ok("log-y toggled (positive data)", g.yLog === true);
g._setLog("y", false);
g.exportCSV();
ok("exportCSV did not throw", true);
g.autoFit();
ok("autoFit reset view", g.view.x[0] === g.full.x[0]);

console.log("console.error count:", errors.length, errors);
console.log("console.warn count:", warns.length, warns);
ok("no console.error during boot/interactions", errors.length === 0);

if (process.exitCode) console.log("NODE RENDER: FAILURES"); else console.log("NODE RENDER OK");
