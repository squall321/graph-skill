// Headless runtime test for dual-axis + bode: confirm the secondary y-axis activates and the
// right-axis series scale to their own range, log-x for bode, zero console errors.
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
  for (const s of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])) (0, eval)(s);
  return { g: global.window.__graph, errors };
}
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

let r = run("bode.html");
ok("bode booted (2 series)", !!r.g && r.g.series.length === 2);
ok("phase series on right axis", r.g && r.g.series[1].axis === "right" && r.g._hasRight === true);
ok("secondary y-domain computed", r.g && r.g.full.y2 && isFinite(r.g.full.y2[0]) && !!r.g.sy2);
ok("frequency axis is log", r.g && r.g.xLog === true);
ok("left mag domain != right phase domain", r.g && r.g.full.y[0] !== r.g.full.y2[0]);
ok("bode no console.error", r.errors.length === 0);

r = run("dual.html");
ok("dual-axis booted with right axis", !!r.g && r.g._hasRight === true && !!r.g.full.y2);
ok("dual-axis no console.error", r.errors.length === 0);

console.log(fail ? "NODE PHASE7: FAILURES" : "NODE PHASE7 OK");
process.exitCode = fail;
