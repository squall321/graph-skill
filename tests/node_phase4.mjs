// Headless runtime test for fft-spectrum: boot (starts in freq), toggle to time domain,
// assert the series + axes swap, zero console errors.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, "..", "graph-out", "fft.html");

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
    tagName: tag, className: "", style: {}, children: [], _ctx: null,
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
const xmax = () => Math.max.apply(null, g.series[0].x);
let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

ok("fft booted", !!g && g.plugins.length === 2);
ok("starts in frequency domain", g._pstate["domain-toggle"].cur === "freq" && g.opts.axes.x.label === "Frequency");
ok("freq axis goes to ~Nyquist (500Hz)", xmax() > 400 && xmax() <= 501);
ok("peak markers present", (g.opts.pluginConfig["named-markers"].markers || []).length >= 2);

// toggle -> time
const P = global.window.GraphPlugins["xy-core"]["domain-toggle"];
P._toggle(g, makeEl("button"));
ok("toggled to time domain", g._pstate["domain-toggle"].cur === "time" && g.opts.axes.x.label === "Time");
ok("time axis is seconds (~1s)", xmax() <= 1.1);
ok("markers cleared in time domain", (g.opts.pluginConfig["named-markers"].markers || []).length === 0);

// toggle back -> freq
P._toggle(g, makeEl("button"));
ok("toggled back to frequency", g.opts.axes.x.label === "Frequency" && xmax() > 400);

console.log("console.error count:", errors.length, errors);
ok("no console.error", errors.length === 0);
console.log(fail ? "NODE PHASE4: FAILURES" : "NODE PHASE4 OK");
process.exitCode = fail;
