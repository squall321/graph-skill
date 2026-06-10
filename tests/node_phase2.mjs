// Headless test for review-matrix: boot the rendered matrix (review-matrix + xy-core engines
// + boot) with a DOM/Canvas stub and confirm graph cells re-mount xy-core with no errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, "..", "graph-out", "design_state.html");

const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  ["save","restore","setTransform","clearRect","fillRect","beginPath","moveTo","lineTo","stroke",
   "rect","clip","fillText","arc","fill","bezierCurveTo","setLineDash","strokeRect","translate",
   "rotate","drawImage"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.canvas = { width: 1200, height: 720 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null, colSpan: 1,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, remove() {},
    addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return RECT; }, setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    get offsetWidth() { return 200; }, get offsetHeight() { return 120; },
    set innerHTML(v) { this._html = v; this.children = []; }, get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text || ""; },
    click() {},
  };
  if (tag === "canvas") { e.getContext = () => (e._ctx ||= makeCtx()); e.toDataURL = () => "data:image/png;base64,AA"; }
  return e;
}
const root = makeEl("div");
const cfgEl = makeEl("script");
const body = makeEl("body");
global.window = global;
global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.document = {
  body,
  createElement: (t) => makeEl(t),
  createTextNode: (t) => ({ nodeType: 3, textContent: t }),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null),
};

const html = fs.readFileSync(htmlPath, "utf-8");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]); // engine(s), plugins, boot

const errors = [];
console.error = (...a) => errors.push(a.join(" "));
for (const s of scripts) (0, eval)(s);

const g = global.window.__graph;
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

ok("both engines registered", typeof global.window.GraphEngines["review-matrix"] === "function" &&
  typeof global.window.GraphEngines["xy-core"] === "function");
ok("matrix booted (window.__graph)", !!g);
ok("3 states", g && g.states.length === 3);
ok("5 item rows", g && g._itemRows.length === 5);
ok("3 graph cells mounted (xy-core re-mount)", g && (g._mounts || []).length === 3);
ok("baseline resolved", g && g.baseline === "v1");

// exercise interactions
g.query = "emi"; g._applyFilter();
ok("filter ran without throw", true);
g.query = ""; g._applyFilter();
g._toggleAll();
ok("collapse-all ran", true);
// open a graph cell modal (re-mount full graph)
const someGp = Object.values(g.gp)[0];
g._openGraph(someGp, "modal");
ok("graph modal opened (full re-mount)", !!g._modalGraph);  // stub classList is no-op; _modalGraph is the real signal
g._closeModal();
ok("modal closed cleanly", !g._modalGraph);

console.log("console.error count:", errors.length, errors);
ok("no console.error", errors.length === 0);

console.log(fail ? "NODE PHASE2: FAILURES" : "NODE PHASE2 OK");
process.exitCode = fail;
