// Headless runtime test for the statistical batch: boot histogram/bar/box/error-bar and
// confirm bars/categorical-axis/box-plot render with zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "graph-out");

const RECT = { left: 0, top: 0, width: 600, height: 360 };
function makeCtx() {
  const c = {};
  ["save","restore","setTransform","clearRect","fillRect","beginPath","moveTo","lineTo","stroke",
   "rect","clip","fillText","arc","fill","bezierCurveTo","setLineDash","strokeRect","translate",
   "rotate","drawImage","putImageData"].forEach((m) => (c[m] = () => {}));
  c.measureText = (s) => ({ width: (s || "").length * 6 });
  c.createImageData = (w, h) => ({ data: new Uint8ClampedArray(w * h * 4), width: w, height: h });
  c.canvas = { width: 1200, height: 720 };
  return c;
}
function makeEl(tag) {
  const e = {
    tagName: tag, className: "", style: {}, children: [], _ctx: null, value: "",
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
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  for (const s of scripts) (0, eval)(s);
  return { g: global.window.__graph, errors };
}

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

let r = run("histogram.html");
ok("histogram booted (bars)", !!r.g && r.g._hasBar === true && r.g.series[0].style === "bar" && r.errors.length === 0);

r = run("bar.html");
ok("bar booted (categorical x, 5 cats)", !!r.g && r.g._cats && r.g._cats.length === 5 && r.g._hasBar === true && r.errors.length === 0);

r = run("box.html");
const hasBox = r.g && r.g.plugins.some((p) => p.id === "box-plot");
ok("box-plot booted (3 cats + plugin)", !!r.g && r.g._cats && r.g._cats.length === 3 && hasBox && r.errors.length === 0);

r = run("errbar.html");
const hasErr = r.g && r.g.plugins.some((p) => p.id === "error-bars");
ok("error-bar booted (plugin + bars)", !!r.g && hasErr && (r.g.opts.pluginConfig["error-bars"].bars || []).length === 5 && r.errors.length === 0);

console.log(fail ? "NODE PHASE6: FAILURES" : "NODE PHASE6 OK");
process.exitCode = fail;
