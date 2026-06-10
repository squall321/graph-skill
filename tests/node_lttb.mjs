// Regression guard for the LTTB level-of-detail downsampler (render-time perf for huge series).
// Boots an xy-core instance and asserts _lod caps drawn points + leaves small series untouched.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const eng = fs.readFileSync(path.join(here, "..", "src", "graph_skill", "data", "engines", "xy-core", "engine.js"), "utf-8");

global.window = global;
global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
const stub = () => ({ getContext: () => stubCtx(), style: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } }, setAttribute() {},
  addEventListener() {}, appendChild() {}, getBoundingClientRect: () => ({ width: 600, height: 360 }), children: [] });
function stubCtx() { const c = {}; ["save", "restore", "setTransform", "clearRect", "fillRect", "beginPath", "moveTo", "lineTo", "stroke", "rect", "clip", "fillText", "arc", "fill", "setLineDash", "strokeRect", "bezierCurveTo"].forEach((m) => (c[m] = () => {})); c.measureText = (s) => ({ width: (s || "").length * 6 }); c.canvas = { width: 1200, height: 720 }; return c; }
global.document = { createElement: () => stub(), getElementById: () => null };
(0, eval)(eng);

let fail = 0;
const ok = (l, c) => { console.log((c ? "  ok  " : " FAIL ") + l); if (!c) fail = 1; };

const mount = stub();
const g = global.window.GraphEngines["xy-core"](mount, { axes: { x: { label: "t", unit: "s" }, y: { label: "a", unit: "g" } } });
g.view = { x: [0, 30], y: [-1, 1] }; g.xLog = false; g.yLog = false;

const N = 30000, xs = [], ys = [];
for (let i = 0; i < N; i++) { xs.push(i * 30 / N); ys.push(Math.sin(i * 0.01)); }
const lod = g._lod({ x: xs, y: ys });
ok("30k series downsampled to <= lodMax", lod.x.length <= g._lodMax && lod.x.length < N);
ok("endpoints preserved", lod.x[0] === xs[0] && lod.x[lod.x.length - 1] === xs[N - 1]);

const small = { x: [0, 1, 2, 3], y: [0, 1, 0, 1] };
ok("small series passthrough (zero overhead, determinism)", g._lod(small) === small);

// P1.1: gappy series are now downsampled PER SEGMENT (null separators preserved) —
// previously they skipped LOD entirely and large gapped series dropped to ~5fps.
const gappy = { x: xs, y: ys.map((v, i) => (i % 5000 === 0 ? null : v)) };
const glod = g._lod(gappy);
const nulls = glod.y.filter((v) => v == null).length;
ok("gappy series downsampled", glod.x.length <= g._lodMax + 16 && glod.x.length < N);
ok("gap separators preserved", nulls >= 5);
ok("gappy endpoint preserved", glod.x[glod.x.length - 1] === xs[N - 1]);

// P1.1: log-x series also downsample now (buckets in log space, original values kept)
g.xLog = true;
const lx = [], ly = [];
for (let i = 0; i < N; i++) { lx.push(1 + i); ly.push(Math.sin(i * 0.01)); }
g.view = { x: [1, N], y: [-1, 1] };
const llod = g._lod({ x: lx, y: ly });
ok("log-x series downsampled", llod.x.length <= g._lodMax + 16 && llod.x.length < N);
ok("log-x keeps original x values", llod.x[0] === 1 && llod.x[llod.x.length - 1] === lx[N - 1]);
g.xLog = false;

console.log(fail ? "NODE LTTB: FAILURES" : "NODE LTTB OK");
process.exitCode = fail;
