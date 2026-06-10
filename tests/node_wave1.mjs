// Headless runtime test for wave-1: pdf-kde / ridgeline (xy-core) · spectrogram (field-core) ·
// scatter-matrix (review-matrix embedding correlation-scatter cells). Boot + no console error.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");
const RECT = { left: 0, top: 0, width: 480, height: 300 };
function makeCtx() {
  const c = {};
  ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo",
   "stroke", "rect", "clip", "fillText", "arc", "fill", "closePath", "bezierCurveTo", "setLineDash",
   "strokeRect", "translate", "rotate", "drawImage", "putImageData"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.createImageData = (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
  c.canvas = { width: 960, height: 600 };
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
  global.document = { body, createElement: (t) => makeEl(t), createTextNode: (t) => ({ nodeType: 3, textContent: t }),
    getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };
  const errors = []; console.error = (...a) => errors.push(a.join(" "));
  let threw = null;
  try { for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s); }
  catch (e) { threw = e; }
  return { g: global.window.__graph, errors, threw };
}
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

let r = run("pdf-kde.html");
ok("pdf-kde booted (1 density series)", !!r.g && !r.threw && r.g.series.length === 1);
ok("pdf-kde no console.error", r.errors.length === 0);

r = run("ridgeline.html");
ok("ridgeline booted (3 group ridges)", !!r.g && !r.threw && r.g.series.length === 3);
ok("ridgeline no console.error", r.errors.length === 0);

r = run("spectrogram.html");
ok("spectrogram field-core heatmap (nx,ny>0)", !!r.g && !r.threw && r.g.nx > 0 && r.g.ny > 0);
ok("spectrogram no console.error", r.errors.length === 0);

r = run("scatter-matrix.html");
ok("SPLOM review-matrix booted", !!r.g && !r.threw);
ok("SPLOM xy-core bundled", typeof global.window.GraphEngines["xy-core"] === "function");
ok("SPLOM 6 off-diagonal scatter cells (3x3−3)", r.g && r.g._mounts && r.g._mounts.length === 6);
ok("SPLOM no console.error", r.errors.length === 0);

console.log(fail ? "NODE WAVE1: FAILURES" : "NODE WAVE1 OK");
process.exitCode = fail;
