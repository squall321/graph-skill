// Headless test for residual-diagnostic-panel: boot the review-matrix artifact (which mounts
// 4 embedded xy-core graph cells) and assert both engines register + no console error.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 240, height: 140 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "bezierCurveTo", "setLineDash",
   "strokeRect", "translate", "rotate", "drawImage", "putImageData"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.createImageData = (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
  c.canvas = { width: 480, height: 280 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null, dataset: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return "auto"; }, removeAttribute() {},
    appendChild(c) { this.children.push(c); return c; }, insertBefore(n) { this.children.unshift(n); return n; },
    get firstChild() { return this.children[0] || null; },
    removeChild() {}, remove() {}, addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return RECT; }, setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    get offsetWidth() { return 220; }, get offsetHeight() { return 130; },
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

const html = fs.readFileSync(path.join(OUT, "residual.html"), "utf-8");
const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
global.document = { body, createElement: (t) => makeEl(t),
  createTextNode: (t) => ({ nodeType: 3, textContent: t }),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
const errors = []; console.error = (...a) => errors.push(a.join(" "));
let threw = null;
try { for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s); }
catch (e) { threw = e; }

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
ok("review-matrix booted, no throw", !!global.window.__graph && !threw);
ok("review-matrix engine registered", typeof global.window.GraphEngines["review-matrix"] === "function");
ok("xy-core bundled for graph cells", typeof global.window.GraphEngines["xy-core"] === "function");
const g = global.window.__graph;
ok("4 diagnostic graph cells mounted", g && g._mounts && g._mounts.length === 4);
ok("no console.error", errors.length === 0);

console.log(fail ? "NODE DIAGNOSTICS: FAILURES" : "NODE DIAGNOSTICS OK");
process.exitCode = fail;
