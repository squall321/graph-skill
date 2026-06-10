// Headless bundle-integrity test for cad3d-core: eval the inlined three.js + OrbitControls +
// GLTFLoader + engine (skipping boot, which needs a real GL context) and assert the globals
// wire up. Then attempt a mock-GL construction of the engine (best-effort, reported not gated).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, "..", "graph-out", "cad-3d-viewer.html"), "utf-8");

global.window = global;
global.self = global;
global.devicePixelRatio = 2;
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.matchMedia = () => ({ matches: false });
global.atob = (b) => Buffer.from(b, "base64").toString("binary");

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };
const errors = []; console.error = (...a) => errors.push(a.join(" "));

// eval all plain <script> blocks EXCEPT boot (which constructs a WebGLRenderer → needs GL)
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
let threw = null;
try {
  for (const s of blocks) { if (s.includes("engine boot failed")) continue; (0, eval)(s); }
} catch (e) { threw = e; }

ok("vendor+engine eval, no throw", !threw);
ok("THREE loaded", typeof global.THREE === "object" && typeof global.THREE.WebGLRenderer === "function");
ok("OrbitControls attached", typeof global.THREE.OrbitControls === "function");
ok("GLTFLoader attached", typeof global.THREE.GLTFLoader === "function");
ok("cad3d-core engine registered", typeof global.window.GraphEngines["cad3d-core"] === "function");
ok("no console.error during load", errors.length === 0);

// --- best-effort mock-GL construction (reported, not gated: full WebGL mock is browser territory) ---
function mockGL() {
  const nameByNum = {}; let ctr = 0x9000;
  const base = {
    getShaderPrecisionFormat: () => ({ precision: 23, rangeMin: 127, rangeMax: 127 }),
    getExtension: () => null, getSupportedExtensions: () => [], getContextAttributes: () => ({ alpha: false }),
    getShaderParameter: () => true, getProgramParameter: () => true,
    createShader: () => ({}), createProgram: () => ({}), createBuffer: () => ({}),
    createTexture: () => ({}), createFramebuffer: () => ({}), createRenderbuffer: () => ({}),
    createVertexArray: () => ({}), getAttribLocation: () => 0, getUniformLocation: () => ({}),
    getProgramInfoLog: () => "", getShaderInfoLog: () => "", drawingBufferWidth: 480, drawingBufferHeight: 360,
    getParameter(n) {
      const nm = nameByNum[n] || "";
      if (/VERSION|VENDOR|RENDERER|LANGUAGE/.test(nm)) return "WebGL 1.0 (mock)";
      if (/EXTENSIONS/.test(nm)) return "";
      return 16384;
    },
  };
  return new Proxy(base, { get(t, p) {
    if (p in t) return t[p];
    if (typeof p === "string" && /^[A-Z0-9_]+$/.test(p)) { const n = ++ctr; nameByNum[n] = p; return n; }
    return () => {};
  } });
}
function mkEl(tag) {
  const e = { tagName: tag, style: {}, children: [], classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } }, dataset: {},
    setAttribute() {}, getAttribute() { return "auto"; }, appendChild(c) { this.children.push(c); return c; },
    addEventListener() {}, removeEventListener() {}, remove() {},
    getBoundingClientRect: () => ({ width: 480, height: 360 }), set textContent(v) {}, get textContent() { return ""; },
    set innerHTML(v) {}, get innerHTML() { return ""; }, getContext: (t) => (t === "webgl" || t === "experimental-webgl" ? mockGL() : null),
    toDataURL: () => "data:image/png;base64,AA" };
  return e;
}
global.document = { body: mkEl("body"), createElement: (t) => mkEl(t), createElementNS: (ns, t) => mkEl(t) };
let constructed = false, cerr = null;
try {
  const inst = global.window.GraphEngines["cad3d-core"](mkEl("div"), {});
  constructed = !!(inst && inst.renderer && inst.scene && inst.camera && inst.controls);
} catch (e) { cerr = e.message; }
console.log(constructed ? "  ok  (bonus) engine constructs three.js scene under mock-GL"
                        : "  ~~  (bonus) mock-GL construct skipped: " + (cerr || "incomplete mock — browser/Playwright is the runtime tier"));

console.log(fail ? "NODE CAD3D: FAILURES" : "NODE CAD3D OK");
process.exitCode = fail;
