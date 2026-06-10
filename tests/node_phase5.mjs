// Headless runtime test for filter-tuner: boot, change the cutoff (client FFT re-filter),
// toggle time/freq, confirm the filtered series responds, zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, "..", "graph-out", "filter.html");

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
    appendChild(c) { this.children.push(c); return c; },
    insertBefore(n) { this.children.unshift(n); return n; },
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
const root = makeEl("div"), cfgEl = makeEl("script"), body = makeEl("body");
global.window = global; global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.document = { body, createElement: (t) => makeEl(t),
  getElementById: (id) => (id === "graph-config" ? cfgEl : id === "graph-root" ? root : null) };

const html = fs.readFileSync(htmlPath, "utf-8");
cfgEl.textContent = html.match(/<script id="graph-config"[^>]*>([\s\S]*?)<\/script>/)[1];
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const errors = []; console.error = (...a) => errors.push(a.join(" "));
for (const s of scripts) (0, eval)(s);

const g = global.window.__graph;
const sum = (a) => a.reduce((s, v) => s + Math.abs(v), 0);
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

const P = global.window.GraphPlugins["xy-core"]["filter-panel"];
const st = g._pstate["filter-panel"];
ok("filter-tuner booted with filter-panel", !!g && g.plugins.indexOf(P) >= 0 && !!st);
ok("starts in freq, fc=80, low", st.domain === "freq" && st.fc === 80 && st.kind === "low");
ok("two series (original + filtered)", g.series.length === 2 && g.series[1].name === "filtered");

// raise cutoff -> more high-freq energy passes -> filtered spectrum sum increases
const e80 = sum(g.series[1].y);
st.fc = 250; P._apply(g);
const e250 = sum(g.series[1].y);
ok("raising cutoff passes more energy (live re-filter)", e250 > e80 * 1.2);

// switch to time domain
st.domain = "time"; P._apply(g);
ok("time domain swap", g.opts.axes.x.label === "Time" && Math.max.apply(null, g.series[0].x) <= 1.1);
ok("filtered waveform present", g.series[1].name === "filtered" && g.series[1].y.length === g.series[0].y.length);

// back to freq + render exercises onDrawOver cutoff line
st.domain = "freq"; P._apply(g);
ok("back to freq", g.opts.axes.x.label === "Frequency");

console.log("console.error count:", errors.length, errors);
ok("no console.error", errors.length === 0);
console.log(fail ? "NODE PHASE5: FAILURES" : "NODE PHASE5 OK");
process.exitCode = fail;
