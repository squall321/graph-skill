# graph-skill — 상세 구축 계획 (마스터 플랜)

> 인터랙티브 단일 HTML 그래프를 "별도 설정 없이도 고품질로" 생성하는 Claude 스킬.
> 본 문서는 4개의 독립 설계(엔진 / 스킬표면 / 로드맵 / 공학후처리 렌즈)를 종합한 단일 권위안이다.
> 사상 원본: `d:\report-skill\docs\SKILL-RECIPE.md`. 품질 기준: `d:\graph-skill\samples\stress-strain\index.html`(Case1 좌측).

---

## 0. TL;DR — 5개 핵심 결정

| # | 결정 | 한 줄 근거 |
|---|---|---|
| D1 | **렌더 엔진 = vanilla Canvas 2D 자체 번들** (라이브러리 아님) | Case1 시그니처(실시간 접선·기울기색·region fill·custom HUD)는 임의 per-frame draw 필수 + self-contained 절대요건 + 결정론 회귀. Plotly 배제(1.1MB), uPlot은 대용량 백엔드로 보류(YAGNI). |
| D2 | **상속 = class extends 아님, plugin 합성(composition)** | `fft+filter+region` 동시 조합에서 다중상속 다이아몬드 방지. graph-type = "plugin 묶음 선언"일 뿐. |
| D3 | **누락 배경정보 = `requires` 집합차 + validate 게이트 + "NEVER invent" 룰** | A0/L0/fs/축단위가 없으면 `missing[]` 반환 → 렌더 차단 → LLM이 사용자에게 질문. 즉흥 판단이 아니라 데이터 구동. |
| D4 | **산출물 = 외부 의존 0인 단일 `.html`** | 빌드타임 인라인 + `graph_lint_output` 정적 게이트(외부 URL 0개). report-write `html_embed`→sandbox iframe 계약. |
| D5 | **엔진=고정 자산, LLM=데이터/메타 수집자** | 엔진/plugin은 버전관리된 번들. LLM은 즉흥 코딩하지 않고 데이터·축·배경값·타입선택만 채운다. 이것이 "설정 없이 일관 품질"의 물리적 구현. |

---

## 1. 개요 & 설계 철학

### 1.1 무엇을 만드는가
graph-skill은 **데이터 출처에 무지한 결정론적 HTML 렌더러**다.
- **입력**: 정규화된 graph config = `시리즈[] + 축 메타(의미·단위·스케일) + graph-type + (선택) feature 묶음 + 후처리 config + 필수 배경값(params)`.
- **출력**: 외부 의존 0인 **단일 `.html`** (그래프 하나만. 외부 프레임/사이트 구조 없음 = 요구 3).

### 1.2 핵심 철학 — 왜 "엔진=고정 자산, LLM=수집자"인가
참조 샘플은 그래프를 base64(`CASE1_B64`)로 인코딩해 `iframe.srcdoc`로 주입한다(samples L293/300-309). 이것이 핵심 신호다: **고품질 인터랙티브 엔진은 LLM이 매 호출 즉흥 생성하는 것이 아니라, 검증된 고정 자산으로 번들된다.**

- "vague 프롬프트 → 저품질"(Case2)의 원인은 LLM이 매번 다시 짜기 때문이다. 엔진을 고정하면 **같은 xy라도 Case1 수준이 무조건 보장**된다(요구 1).
- LLM의 책임은 4가지로 좁혀진다: **(a) 데이터 수집/검증, (b) 단위·배경정보 resolve(부족하면 질문), (c) graph-type + feature 선택, (d) 후처리 config.**
- 엔진 소스(수만 토큰)는 **LLM 컨텍스트에 절대 싣지 않는다.** LLM은 카탈로그의 타입·requires 메타만 본다.

### 1.3 책임 경계 (사슬 가운데에서만 산다)
```
aidatahub (raw 측정/시뮬 (x,y) + A0/L0/fs 메타)   ← 데이터 in: 오케스트레이터 LLM 책임
        │  get_agent_session → agent_search → get_record_sections
        ▼
graph-skill (순수 결정론 렌더러)                   ← 렌더: 고정 엔진. aidatahub를 import하지 않음
        │  requires resolve → 엔진+plugins+config+data → 단일 .html
        ▼
report-write (html_embed: local_path→file_id→sandbox iframe)  ← 게시 out: report-write 책임
        ▼
ReportArchive 보드 게시
```
graph-skill은 데이터 출처에 무지할 때 재사용성이 최대다. aidatahub `stress_strain_plot`(정적 PNG, bilinear 근사)과는 **경쟁이 아니라 직렬 보완** — 그쪽은 데이터+1차 시각화, 이쪽은 인터랙티브 고품질 렌더.

---

## 2. 아키텍처 — 레시피 4표면 치환 매핑

레시피의 "외부 시스템 운전" 모델 → graph-skill의 "산출물 생성" 모델. 표면 이름은 유지, 의미만 치환.

```
┌───────────────────────────────────────────────────────────────┐
│ SKILL.md  — LLM 명세. Tools/Flows/Rules.                        │
│   핵심 Rule: "requires 미충족이면 렌더 전 반드시 질문, 추정 금지"   │
└───────────────────────────────────────────────────────────────┘
                       │ (LLM이 어떤 도구를 부를지 결정)
                       ▼
┌───────────────────────────────────────────────────────────────┐
│ MCP 서버  — graph_types_list / graph_schema_get /              │
│            graph_validate_inputs / graph_render /              │
│            graph_lint_output / fft_preview / filter_apply ...  │
│ CLI       — graph types / graph render xy --in .. --out ..     │
└───────────────────────────────────────────────────────────────┘
                       │ (둘 다 같은 builder + recipes + catalog 호출)
                       ▼
┌───────────────────────────────────────────────────────────────┐
│ builder.py (=구 client.py)  — 고정 JS 엔진 + 활성 plugin +     │
│   정규화 config + 주입 데이터 → 단일 self-contained .html       │
└───────────────────────────────────────────────────────────────┘
                       │
                       ▼
                 산출물: 단일 .html (디스크). 외부 호출 없음.
```

| 레시피 표면 (운전 모델) | graph-skill (산출물 모델) | 운명 | 핵심 변화 |
|---|---|---|---|
| `SKILL.md` | `SKILL.md` | 재사용 | Tools=렌더/검증, Rule="추정 금지·질문 강제" |
| `mcp_server.py` `_DISPATCH` | 동일 | 재사용 [§3 황금률] | 도구가 `graph_*` |
| `cli.py` (Typer) | 동일 | 재사용 | `graph render/validate/types` (결정론 재현·diff) |
| **`client.py`** (외부 API 1:1) | **`builder.py`** (HTML 조립자) | **치환 T1** | raise_for_status 자리에 출력 검증 |
| `adapters/<unit>.py` | **`recipes/<graph_type>.py`** | **치환 T2** | normalize + `requires[]` 선언 + plugin 묶음 선언 + 후처리 config |
| (신규 없음) | **`postprocess/*`** | **신규** | 단위/FFT/필터/SG/미분/적분/resample — 정확성 핵심 |
| `prompt.py` `_INPUT_HINTS` | 동일 + `_REQUIRES_HINTS` | 재사용 R2 [§5b] | 타입별 "필수 물리값 + 없을 때 물어볼 질문" |
| (resolver 도구) | `graph_validate_inputs` + aidatahub 위임 | 재사용 R3 [§5c] | "NEVER invent ids" → "NEVER invent 물리 배경값" |
| `data/catalog.snapshot.json` | **`data/engine/*.js` + `data/plugins/*.js` + `data/catalog/*.json`** | **치환 T3** | 외부 스냅샷 → 버전관리 고정 렌더 엔진 |
| `ops.py` (lock/revision/retry) | — | **폐기** | 무상태 산출물, 동시성 없음 |
| `bundle.py` (`_TOP_KEEP`) | — | **폐기** | 인스턴스 간 이전 없음 |
| §0 안정식별자·인증·멱등성 | — (read-data resolver만 R3 생존) | **폐기** | 운전할 외부 쓰기 시스템 없음 |
| 패키징 wheel/standalone | 동일 + JS `package_data` 동봉 | 재사용 R7 | 엔진이 wheel 안에 |
| Phase 3 `pytest` | pytest + **결정론 + self-contained 정적 + Playwright 렌더** | **확장 T5** | HTML 산출물 자체를 검증 |

---

## 3. 파일 트리 (canonical, 실제 경로)

```
d:\graph-skill\
├── pyproject.toml                       name="graph-skill", entry points, package_data
├── MANIFEST.in                          data/**/*.{js,css,json,html} 강제 포함
├── README.md
├── CHANGELOG.md
├── install.ps1                          wheel 설치 + .claude/skills 복사
├── install-standalone.ps1               Python 없는 사내 PC용 (PyInstaller)
├── .env.example                         (GRAPH_OUT_DIR 등. 외부 토큰 불필요)
│
├── .claude\skills\graph-skill\
│   └── SKILL.md                         LLM 명세 (Tools / Flows / Rules) — §13 스켈레톤
│
├── src\graph_skill\
│   ├── __init__.py                      __version__ = importlib.metadata.version("graph-skill")
│   ├── mcp_server.py                    MCP stdio + _TOOLS + _DISPATCH       [§3 황금률]
│   ├── cli.py                           Typer sub-apps: build/render/validate/types/fft/filter
│   ├── settings.py                      pydantic-settings (out dir, embed mode; 네트워크 없음)
│   ├── builder.py                       ★ T1: HTML 조립자 (결정론적)
│   ├── catalog.py                       graph-type 카탈로그 로더 + extends 평탄화 + requires 집계
│   ├── validate.py                      missing[] 계산 + jsonschema 검증 (게이트)
│   ├── serialize.py                     ★ 안전 직렬화 (script/srcdoc/base64 sentinel)
│   ├── inputspec.py                     입력 스키마(pydantic) + 레거시 입력 관용
│   ├── prompt.py                        _INPUT_HINTS + _REQUIRES_HINTS + 프롬프트 빌더
│   ├── feedback.py                      누락 배경정보 → 구조화 Question 객체
│   │
│   ├── recipes\                         ★ T2: graph-type별 정규화 + 선언
│   │   ├── __init__.py                  REGISTRY: dict[str, Recipe]
│   │   ├── base.py                      Recipe ABC: normalize()/requires()/plugins()
│   │   ├── base_xy.py
│   │   ├── scatter.py
│   │   ├── stress_strain.py             requires A0,L0; plugins region/tangent/markers/table
│   │   ├── time_series.py
│   │   ├── fft_spectrum.py              requires fs
│   │   ├── filter_tuner.py              requires fs; time-domain reconstruct
│   │   └── ... (타입당 1파일)
│   │
│   ├── postprocess\                     ★ 신규: 공학 후처리 (Python 사전계산 경계)
│   │   ├── __init__.py
│   │   ├── units.py                     σ=F/A0, ε=ΔL/L0, eng↔true
│   │   ├── spectral.py                  FFT (window/scale/one-sided), PSD, peak
│   │   ├── filters.py                   Butterworth/FIR LP/HP/BP, filtfilt(영위상)
│   │   ├── smoothing.py                 Savitzky-Golay
│   │   ├── calculus.py                  도함수/접선(Et)/적분/secant
│   │   ├── resample.py                  uniform-dt 보간/리샘플/디트렌드
│   │   └── ingest.py                    raw 장비포맷 파서(헤더/메타/샘플레이트)
│   │
│   └── data\                            ★ T3: 버전관리된 고정 자산 (LLM 컨텍스트에 안 실음)
│       ├── engine\
│       │   ├── xy-core.js               vanilla Canvas 코어 (Case1 feature set 전체)
│       │   ├── xy-core.min.js           빌드 산출(번들용)
│       │   └── xy-core.css              CSS vars 토큰 (dark/light)
│       ├── backends\
│       │   └── uplot.min.js             선택 백엔드 (MIT, time-series/대용량; v0.6+ 도입 보류)
│       ├── plugins\                     feature plugin 1개당 1파일
│       │   ├── region-shading.js
│       │   ├── live-tangent.js          dσ/dε 단위환산 + 기울기 색변화 + lock
│       │   ├── named-markers.js
│       │   ├── props-table.js
│       │   ├── unit-convert.js
│       │   ├── domain-toggle.js         time↔freq
│       │   ├── fft-view.js
│       │   ├── filter-panel.js          차단주파수 슬라이더 + 역변환
│       │   └── stat-fit.js
│       ├── numeric\
│       │   └── fft.js                   클라이언트측 FFT (슬라이더 실시간 미리보기 전용)
│       ├── shell\
│       │   ├── template.html            self-contained 셸 (단일 루트 + 주입 슬롯)
│       │   └── boot.js                  엔진 부팅 + plugin 등록 글루
│       ├── catalog\
│       │   ├── graph-types.json         type → {engine, plugins, requires, hints, extends}
│       │   └── manifest.json            엔진/plugin 버전 + sha256 핀
│       └── ENGINE_VERSION               예: 1.0.0  (산출 HTML에 baked)
│
├── tests\
│   ├── test_validate_missing.py         missing[] 정확성 (A0/L0/fs 케이스)
│   ├── test_recipes.py                  normalize round-trip + requires 집계
│   ├── test_postprocess.py              ★ 수치 정확성 골든값 (FFT/필터/단위)
│   ├── test_serialize.py                </script>,  , 백틱 이스케이프
│   ├── test_builder_determinism.py      동일 입력 → 바이트 동일 HTML
│   ├── test_self_contained.py           외부 URL 0개 정적 검사 (게이트)
│   ├── test_feedback.py                 배경정보 누락 → 질문 생성
│   ├── golden\                          graph-type별 구조 골든 (config+plugins+sha)
│   │   └── stress_strain.golden.json
│   └── e2e\
│       └── test_render_playwright.py    canvas 그려짐 / hover→HUD / console error 0 / 시각회귀
│
├── scripts\
│   ├── build_engine.mjs                 JS 코어/plugin → minify + sha256 핀 + manifest 갱신
│   ├── refresh_catalog.py               recipes/*.py → data/catalog/graph-types.json dump
│   ├── gen_golden.py                    타입별 fixture → 구조 골든 + 시각 골든 PNG
│   ├── build_release.ps1
│   └── build_exe.ps1                    PyInstaller standalone
│
└── docs\
    ├── SKILL-PLAN.md                    (이 문서)
    ├── BUILDING.md                      이 계획의 인스턴스화
    ├── ENGINE-API.md                    코어 공개 API 계약 (§4)
    ├── PLUGIN-API.md                    plugin 라이프사이클 계약 (§5)
    ├── GRAPH-SPEC-TEMPLATE.md           새 타입 작성 양식 (§7)
    ├── ADD-TYPE-CHECKLIST.md            레시피 §10 변형 (§12.4)
    └── INTEGRATION.md                   aidatahub→graph→report-write 계약 (§11.4)
```

**최소 시작(MVP)**: `pyproject.toml` + `src/graph_skill/{builder,serialize,cli,mcp_server,catalog,validate}.py` + `recipes/{base,base_xy}.py` + `data/engine/xy-core.{js,css}` + `data/shell/*` + `.claude/skills/graph-skill/SKILL.md`.

---

## 4. 렌더 엔진 설계 (vanilla Canvas)

### 4.1 백엔드 선택 — 근거
| 기준 | **vanilla Canvas (채택)** | uPlot | Plotly | D3/Plot |
|---|---|---|---|---|
| Case1 시그니처(실시간 접선+Et 색변화+region fill+custom HUD+near-curve) | **per-frame draw 완전 제어** | hook 위 자작 | 정적 annotation 한계 | 가능하나 전부 자작, SVG 성능↓ |
| self-contained 인라인(외부 fetch 0) | **코드=자산, 의존성 0 (~20–60KB)** | 양호 (~40KB) | **부적합 (~1.1MB+)** | 양호하나 전부 자작 |
| 결정론 회귀검증 | **100% 우리 코드** | 라이브러리 버전 종속 | 큼 | 중 |
| report-write base64/srcdoc 임베드 친화 | **최선** | 양호 | 페이로드 비대 | 양호 |
| 라이선스/공급망 | 리스크 0 | MIT | MIT | ISC |

**채택**: 코어 = vanilla Canvas 2D 자작. uPlot은 time-series/fft-spectrum/대용량(>50k pt)에서만 **선택적 가속 백엔드**(v0.6+ 실증 시 도입). Plotly/ECharts 배제(인라인 페이로드 비대 → sandbox iframe 임베드 불리). D3/Observable Plot은 **오버레이 디자인 레퍼런스로만**(틱/스케일/색 스킴), 코드 채택 안 함.

### 4.2 코어 공개 API (`data/engine/xy-core.js`)
단일 IIFE로 `window.XYCore` 전역 하나만 노출. 클래스 1개 + 명시적 lifecycle. **상태 객체 `view`를 모든 훅에 넘겨 plugin이 좌표변환/스케일/데이터에 접근**하게 한다.

```js
// data/engine/xy-core.js  (IIFE → window.XYCore)
class XYCore {
  constructor(mount, options) { /* canvas 생성, DPR 스케일, ResizeObserver 부착 */ }

  use(plugin)      { this._plugins.push(plugin); plugin.onInit?.(this); return this; } // 합성 진입점
  setData(series)  { /* Series[] (4.4). 도메인 재계산 → onData 훅 */ }
  setOptions(patch){ /* 옵션 병합 → 필요한 훅 재실행 */ }
  setView(domain)  { /* {x:[min,max], y:[min,max], xLog, yLog} 핀 → onScale 훅 */ }
  autoFit()        { /* nice-range 도메인 자동 + 패딩 */ }
  redraw()         { /* dirty flag 렌더 루프 1프레임 강제 */ }
  exportPNG(scale) { /* 현재 뷰 → dataURL. onExport 훅으로 plugin 오버레이 포함 */ }
  exportConfig()   { /* <script id="graph-config"> 추출용 (round-trip) */ }
  destroy()        { /* ResizeObserver/리스너 해제 */ }
}
```

### 4.3 옵션 객체 (선언적, recipe가 채움)
```js
const options = {
  axes: {
    x: { label: "Strain ε", unit: "", log: false, domain: null /* auto */, tickFormat: "auto" },
    y: { label: "Stress σ", unit: "MPa", log: false, domain: null }
  },
  curve:   "monotone",           // straight | monotone(단조 3차) | step
  grid:    { major: true, minor: true, divisions: 10 },   // 참조 10×10
  palette: "okabe-ito",          // 색맹안전 기본 (§14)
  theme:   "auto",               // auto(prefers-color-scheme) | light | dark
  interactions: { hover: true, crosshair: true, zoom: true, pan: true, boxZoom: true },
  legend:  { show: true, isolateOnDblClick: true },
  responsive: { aspectRatio: "16/9", widthPct: 100 },     // ResizeObserver
  exportButtons: ["png", "csv", "config"]
};
```
**불변식**: 이 options 전체를 LLM이 매번 짜지 않는다. recipe 기본값으로 채워지고, LLM은 라벨/단위/도메인 핀 같은 **데이터-종속 슬롯만** 채운다. 이것이 "설정 없이 Case1 수준 자동 보장"의 물리적 구현.

### 4.4 데이터 모델 (`setData`)
```js
// series: Series[]
{ name: "Specimen A", x: Float64Array|number[], y: Float64Array|number[],
  color?: "#…", dash?: [4,2], markers?: bool, kind?: "line"|"scatter",
  axis?: "left"|"right",
  meta?: { /* recipe 후처리 결과: trueStress, regionId 등 */ } }
```
엔진 자체는 **항상 정식 `Series[]`만** 받는다. `[[x,y],…]` 평면배열이나 `{x:[],y:[]}` 단일을 흡수하는 레거시 관용은 recipe/builder가 짊어진다(결정론 보존).

### 4.5 좌표변환/스케일 (`view` 객체 — plugin이 공유)
```js
view = {
  scaleX(dataX) -> pxX,  scaleY(dataY) -> pxY,     // data→pixel
  invX(pxX)   -> dataX,  invY(pxY)   -> dataY,     // pixel→data (hover 역변환)
  domain: { x:[lo,hi], y:[lo,hi], xLog:false, yLog:false },
  plot:   { left, top, width, height },            // 플롯영역(축 제외) 픽셀 박스
  dpr, theme, series, cursor: { px, py, dataX, dataY, nearestIndex }
}
```
**규율(백엔드 교체 대비)**: plugin은 `ctx`에 직접 그리되, **좌표 변환은 반드시 `view.scaleX/scaleY/invX/invY` 경유.** 픽셀 좌표를 직접 계산하지 않는다. 나중에 uPlot 백엔드를 끼울 때 좌표 로직을 재사용할 수 있다.
로그스케일: `scaleX`가 `xLog`일 때 `log10` 경유. **0/음수 가드는 엔진이 클램프 + 콘솔 경고 + UI 배지**(조용히 틀린 그래프 금지).

### 4.6 렌더 루프 & 이벤트 (훅 삽입 지점 — 고정 순서 = 결정론)
```
requestAnimationFrame 루프 (dirty flag 기반, idle 시 정지)
  clear()
  → emit onScale(view)                       // 줌/팬/리사이즈로 도메인 변경 시
  → drawGrid(); drawAxes()
  → for p of plugins: p.onDrawUnder?.(ctx, view)   // region shading (배경, 곡선 아래)
  → drawSeries()                                    // bezier/monotone/step 곡선
  → for p of plugins: p.onDrawOver?.(ctx, view)     // 마커/접선/주석 (전경, 곡선 위)
  → drawLegend(); drawHUD()

이벤트:
  pointermove → update cursor → emit onHover(view, cursor) → plugin이 hud patch 반환 → 재draw
  click       → emit onClick(view, cursor)            // 접선 lock/unlock
  wheel/drag  → 줌/팬 → setView → onScale
  ResizeObserver → DPR 재계산 → onResize → redraw
```

---

## 5. Plugin 합성 시스템 (상속이 아니라 합성)

### 5.1 왜 합성인가
요구 4·5는 **그래프 타입 폭발**(base-xy → stress-strain → fft → filter → bode → s-n …)이다. `class StressStrain extends XYCore`로 가면 "stress-strain을 FFT로 보기" 같은 교차 조합에서 **다이아몬드 상속**이 터진다. 합성이면 `[regionShade, liveTangent] + [fftView]`를 **리스트 병합**으로 끝낸다. 또한 합성은 recipe가 "plugin 묶음 선언만으로" 새 타입을 정의하게 해 **per-file 병렬 구현**(plugin 1개 = 파일 1개 = owner 1명)을 보존한다.

### 5.2 Plugin 계약 (라이프사이클 훅 — 덕타이핑, 모든 훅 optional)
```js
const Plugin = {
  id:       "live-tangent",
  requires: ["A0", "L0"],            // ← LLM 질문 트리거 (§8). JS측 자기검증 + Python catalog와 동일 출처
  order:    50,                      // 합성 순서 (결정론: 정렬키)
  defaults: { tangentColorByMag: true },

  onInit(core)            {},        // 컨트롤 버튼 부착, 상태 초기화
  transform(series, cfg)  { return series },// 데이터 파생(단위환산/FFT/필터). 체인: 앞 plugin 출력→뒤 입력
  onScale(view)           {},        // 도메인 변경 시 캐시 재계산
  onDrawUnder(ctx, view)  {},        // 배경 fill (region shading)
  onHover(view, cursor)   { return {hud} },// 접선/트래킹 → HUD 패치 반환 (여러 plugin이면 머지)
  onDrawOver(ctx, view)   {},        // 전경 (마커/접선선/주석)
  onClick(view, cursor)   {},        // lock/unlock
  onExport(ctx, view)     {},        // PNG에 오버레이 포함
  controls()              { return [/* 토글/슬라이더 UI 디스크립터 */] }
};
```
합성 규칙: `core.use(p)`로 등록. 훅은 **`order` 오름차순** 호출(결정론). `transform`은 체인(앞 출력→뒤 입력). `onHover`는 HUD 패치 머지.

### 5.3 백엔드 추상화 (vanilla ↔ uPlot)
plugin은 `ctx`(2D context)와 `view`(좌표변환 + 도메인 + 테마토큰)만 받는다. 백엔드가 vanilla면 코어 캔버스, uPlot이면 uPlot의 `draw`/`setCursor` hook 안에서 같은 `view`를 합성해 넘긴다 → **plugin 코드는 백엔드 무관**. (MVP는 vanilla 단일. uPlot 자리만 `catalog.backend` 필드로 확보.)

---

## 6. graph-type 카탈로그 & 상속(`extends`)

### 6.1 카탈로그 포맷 (`data/catalog/graph-types.json`)
graph-type은 **plugin 묶음 선언**일 뿐이다(코드 아님).
```jsonc
{
  "engine_version": "1.0.0",
  "engine": "xy-core",
  "types": {
    "base-xy": {
      "extends": null,
      "backend": "canvas",
      "plugins": ["log-toggle"],
      "requires": [],
      "options_defaults": { "curve": "monotone", "grid": { "divisions": 10 } }
    },
    "stress-strain": {
      "extends": "base-xy",                                  // ← 선언적 "상속"
      "plugins": ["unit-convert","region-shading","named-markers","live-tangent","props-table"],
      "requires": [
        { "field": "params.A0", "type": "number", "unit": "mm^2",
          "why": "engineering stress σ=F/A0 환산에 필요",
          "ask": "시편 초기 단면적 A0를 mm²로 알려주세요 (예: 50.3). raw가 이미 stress면 'stress'로 답하세요." },
        { "field": "params.L0", "type": "number", "unit": "mm",
          "why": "engineering strain ε=ΔL/L0 환산에 필요",
          "ask": "표점거리 L0를 mm로 알려주세요 (예: 25). raw가 이미 strain이면 'strain'으로 답하세요." }
      ],
      "post": ["units.eng_stress_strain"]
    },
    "fft-spectrum": {
      "extends": "time-series",
      "backend": "uplot",
      "plugins": ["domain-toggle","fft-view","named-markers"],
      "requires": [
        { "field": "params.fs", "type": "number", "unit": "Hz",
          "why": "bin→Hz 환산에 sampling rate 필요. 없으면 x축이 무의미한 bin index.",
          "ask": "샘플링 레이트 fs를 Hz로 알려주세요 (예: 1000). 또는 dt[s]를 주시면 fs=1/dt." } ],
      "post": ["spectral.fft_onesided"]
    },
    "filter-tuner": {
      "extends": "fft-spectrum",
      "plugins": ["filter-panel"],
      "requires": [],                                        // fs 상속
      "post": ["spectral.fft_onesided"],
      "client_numeric": ["fft.js"]                           // 슬라이더 실시간 미리보기용
    }
  }
}
```

### 6.2 `extends` 평탄화 (`catalog.py`)
`effective_plugins(type) = plugins(부모) ∪ plugins(자식)` (dedupe, order 정렬). `effective_requires(type) = requires(부모) ∪ requires(자식)` (누적). 단일 부모 트리 → 다이아몬드 없음.
```python
# catalog.py
def resolve_type(type_name: str) -> ResolvedType:
    chain, t = [], CATALOG["types"][type_name]
    while t:
        chain.append(t)
        t = CATALOG["types"].get(t.get("extends"))
    plugins, requires = [], []
    for node in reversed(chain):                 # 부모→자식 순서로 누적 (결정론)
        for p in node.get("plugins", []):
            if p not in plugins: plugins.append(p)
        for r in node.get("requires", []):
            if r not in requires: requires.append(r)
    return ResolvedType(engine=CATALOG["engine"], plugins=plugins,
                        requires=requires, options=merge_options(chain))
```

### 6.3 boot.js — "상속"의 실체
```js
// data/shell/boot.js — 빌더가 주입한 평탄화 결과로 조립
(function () {
  const cfg = JSON.parse(document.getElementById("graph-config").textContent);
  const core = new XYCore(document.getElementById("graph-root"), cfg.options);
  for (const id of cfg.plugins) core.use(window.XYPlugins[id]);   // ← "상속"의 실체
  core.setData(cfg.series);
  core.autoFit();
})();
```
즉 **stress-strain = base-xy 엔진 + plugin 5개**, **fft-toggle = stress-strain plugin + 2개**. 코드 중복 0, 엔진 1개, 차이는 데이터(plugin 리스트)뿐. 새 타입 = catalog 한 블록 + (필요시) plugin 파일 1개 = minor 한 개.

---

## 7. graph-type spec 템플릿 (`docs/GRAPH-SPEC-TEMPLATE.md`)

새 타입 하나 = 이 spec 한 장. **spec 없이 코드 금지. spec은 사람이 읽고 빌더가 검증한다.**
```markdown
# SPEC: <graph-type-id>            (예: stress-strain)
version-introduced: 0.2.0
inherits-base: base-xy

## 1. 의미 (Semantics)
- x-axis: <quantity> [<unit>]      # strain ε [-]
- y-axis: <quantity> [<unit>]      # stress σ [MPa]
- secondary-y: <opt>
- 1줄 목적: 무엇을 보여주는 그래프인가

## 2. Plugin 묶음 (PLUGINS)        ← graph-type = 이 리스트 (draw 순서 = 결정론)
[unit-convert, region-shading, named-markers, live-tangent, props-table]

## 3. 필수 배경정보 (REQUIRES)     ← 누락 시 LLM이 질문 (§8)
field | type | unit | resolvable_from | ask (없을 때 물을 문구)
A0    | float| mm²  | aidatahub:specimen.area | "시편 초기 단면적 A0를 mm²로 ..."
L0    | float| mm   | aidatahub:gauge         | "표점거리 L0를 mm로 ..."

## 4. config 스키마 (JSON Schema, additionalProperties:false)
## 5. 후처리 (transform 파이프라인 순서)
raw(F[N], ΔL[mm]) → engineering(σ=F/A0, ε=ΔL/L0) → true(σ_t=σ(1+ε), ε_t=ln(1+ε))
## 6. 예시 입력 fixture → tests/fixtures/<type>.json
## 7. 기대 인터랙션 (Playwright 스모크 어서션)
## 8. 골든 기준 (gen_golden.py): 구조 골든 + 시각 골든 PNG (ΔE<2%)
## 9. height_px 권장값 (report-write 임베드)
```

---

## 8. 완결성 게이트 — 누락 배경정보 LLM 피드백 (요구 2 핵심)

레시피 §5c "NEVER invent ids"의 그래프판 = **"NEVER invent 물리 배경값 — 부족하면 질문"**. **즉흥 판단이 아니라 집합차 계산.** 4개 부품이 맞물린다.

### 8.1 부품 4개
**(A) recipe `requires[]` 선언 (단일 진실)** — §6.1 카탈로그의 `{field, type, unit, why, ask}`. `ask`가 실제 질문 문구.

**(B) `validate.check()` — missing[] 계산:**
```python
# validate.py
def check(graph_type: str, payload: dict) -> dict:
    req = catalog.effective_requires(graph_type)        # extends 평탄화 (A0,L0,fs...)
    missing = []
    for r in req:
        if _dig(payload, r["field"]) is None:           # "params.A0" → payload["params"]["A0"]
            missing.append({"field": r["field"], "why": r["why"], "ask": r["ask"]})
    for axis in ("x", "y"):                              # 축 의미·단위도 필수 (요구2)
        a = payload.get("axes", {}).get(axis, {})
        if not a.get("label") or not a.get("unit"):
            missing.append({"field": f"axes.{axis}",
                            "why": "축 의미·단위 미상 → 눈금 SI접두·툴팁 단위 불가",
                            "ask": f"{axis}축이 무슨 물리량이고 단위가 뭔가요? (예: '시간 [s]')"})
    return {"ok": not missing, "missing": missing,
            "questions": [m["ask"] for m in missing],
            "normalized_preview": recipes.REGISTRY[graph_type].normalize(payload) if not missing else None}
```

**(C) `_INPUT_HINTS` / `_PREAMBLE` (`prompt.py`, 레시피 §5b):**
```python
_PREAMBLE = ("NEVER invent axis units or physical background values (A0, L0, fs). "
             "Always call graph_validate_inputs first; if missing[] is non-empty, "
             "ASK the user the listed questions and DO NOT render until resolved.")
_INPUT_HINTS = {
  "stress-strain":
    "Required physics: params.A0 [mm²], params.L0 [mm]. If raw is force[N]/displacement[mm], "
    "engine converts σ=F/A0, ε=ΔL/L0. If missing: ASK. A wrong A0 silently produces a confidently-wrong curve.",
  "fft-spectrum":
    "Required: params.fs [Hz] (or dt[s] → fs=1/dt). Without fs the frequency axis is meaningless bin index.",
}
```

**(D) SKILL.md Rule** — "validate가 missing 반환 → 렌더 금지, 질문"을 "NEVER invent ids"와 동급 룰로 박음(§13).

### 8.2 정확한 흐름 — force/displacement만 주고 A0/L0 누락
```
1. 사용자: "이 인장시험 데이터로 stress-strain 그려줘" + [force(N), displacement(mm)] 시리즈
2. LLM → graph_schema_get("stress-strain")
      ← requires: params.A0[mm²], params.L0[mm]; plugins: region-shading, live-tangent ...
3. LLM → graph_validate_inputs("stress-strain", payload={series:[force,disp], axes:{...}})
      ← { ok:false, missing:[{field:"params.A0", ask:"단면적 A0를 mm²로..."},
                             {field:"params.L0", ask:"표점거리 L0를 mm로..."}],
          questions:["A0...","L0..."] }
4. LLM(SKILL.md Rule + _PREAMBLE 준수) → 렌더하지 않고 사용자에게 질문:
   "정확한 응력-변형 곡선에 두 값이 필요합니다:
     1) 시편 초기 단면적 A0 [mm²]? (예: 50.3)
     2) 표점거리 L0 [mm]? (예: 25)
    raw가 이미 stress/strain이면 그렇게 알려주세요."
   (선택) 출처가 aidatahub record면: get_record_sections로 A0/L0 조회 시도 후, 없으면 질문.
5. 사용자: "A0=50.3, L0=25"
6. LLM → graph_validate_inputs(payload={..., params:{A0:50.3, L0:25}})  ← 재호출
      ← { ok:true, missing:[], normalized_preview:{σ,ε 변환 미리보기} }
7. LLM → graph_render("stress-strain", series, axes, params={A0:50.3,L0:25}, out_path=...)
      ← { html_path, engine_version, recommended_height_px:520 }
8. LLM → graph_lint_output(html_path) ← {ok:true, external_urls:0}  (게이트 통과)
9. LLM → graph_embed_block(html_path, height_px:520) → report-write 핸드오프
```
**불변식: `missing[]`이 비어야만 렌더.** 추정 경로 없음(요구2 정면 충족).

### 8.3 P1 비대칭 방지
새 `requires` 필드를 추가하면 **같은 PR에서** 그 값을 실제로 쓰는 `transform` 슬롯(예: `unit-convert`가 `cfg.A0`를 소비)을 동시에 추가. "값은 받는데 그래프에 안 꽂힘"을 §12.4 체크리스트로 강제.

---

## 9. MCP / CLI 툴 표면

각 도구는 3-view: `mcp_server.py(_tool+_do_*+_DISPATCH)` ↔ `cli.py(@app.command)` ↔ 백엔드 함수. 파라미터·기본값 동일.

### 9.1 도구 카탈로그
| MCP 도구 | 종류 | 한 줄 설명 | CLI 미러 | 백엔드 |
|---|---|---|---|---|
| `graph_types_list` | resolver(read) | graph-type 목록 + 상속 트리 | `graph types list` | `catalog.list_types()` |
| `graph_schema_get` | resolver(read) | 한 type의 입력 스키마 + requires[] + plugin 목록 | `graph schema get <type>` | `catalog.get_schema(type)` |
| `graph_validate_inputs` | **게이트(read)** | 입력 검증 → `missing[]` + `questions[]`. **추정 금지 핵심** | `graph validate <type> --in d.json` | `validate.check(...)` |
| `graph_render` | emit | type+config+데이터 → 단일 self-contained .html (경로 반환) | `graph render <type> --in d.json --out p.html` | `builder.render(...)` |
| `graph_lint_output` | **게이트(read)** | 산출 HTML 정적 검증: 외부 URL 0, 단일 루트, srcdoc-safe | `graph lint <html>` | `builder.lint(html)` |
| `fft_preview` | helper(read) | 시계열+fs → 주파수 스펙트럼 미리보기(수치만) | `graph fft preview --in d.json --fs 1000` | `postprocess.spectral.preview(...)` |
| `filter_apply` | helper(read) | LP/HP/BP 설계+적용 → 필터링 시계열(수치만) | `graph filter apply --in d.json --fs .. --type low --fc ..` | `postprocess.filters.apply(...)` |
| `resample` | helper(read) | 비균일 시계열 → 균일 dt 재샘플(수치만) | `graph resample --in d.json --dt ..` | `postprocess.resample.uniform(...)` |
| `graph_embed_block` | emit | 산출 HTML 경로 → report-write `html_embed` draft 조각(JSON) | `graph embed-block <html> --height 520` | `builder.embed_block(...)` |

설계 의도:
- helper(`fft_preview`/`filter_apply`/`resample`)는 **HTML을 만들지 않고 수치만** 반환 → LLM이 "FFT 보면서 필터 조정"을 대화 중 미리 검토하고 최종 config를 `graph_render`에 넘김(요구 4의 도구 분해).
- `graph_lint_output`/`graph_embed_block` = 완결성 게이트 + 생태계 핸드오프. 레시피의 `raise_for_status` 자리(출력 검증)를 메운다.

### 9.2 핵심 입력 JSON Schema 윤곽
```jsonc
// graph_render
{ "type":"object", "required":["graph_type","series","axes","out_path"],
  "properties":{
    "graph_type":{"type":"string"},
    "series":{"type":"array","minItems":1,"items":{
      "type":"object","required":["name","data"],
      "properties":{
        "name":{"type":"string"},
        "data":{"type":"array","items":{"oneOf":[
          {"type":"array","minItems":2,"maxItems":2,"items":{"type":"number"}},
          {"type":"object","required":["x","y"],
           "properties":{"x":{"type":"number"},"y":{"type":"number"}}}]}},
        "color":{"type":"string"},
        "axis":{"enum":["left","right"],"default":"left"}}}},
    "axes":{"type":"object","required":["x","y"],
      "properties":{
        "x":{"type":"object","required":["label","unit"],
             "properties":{"label":{"type":"string"},"unit":{"type":"string"},
                           "scale":{"enum":["linear","log"],"default":"linear"}}},
        "y":{"$ref":"#/properties/axes/properties/x"}}},
    "params":{"type":"object"},     // requires 충족값 {A0,L0,fs,...} — recipe별 화이트리스트
    "features":{"type":"array","items":{"type":"string"}},  // 생략 시 recipe 기본 묶음
    "title":{"type":"string"},
    "embed_mode":{"enum":["standalone","srcdoc-fragment"],"default":"standalone"},
    "out_path":{"type":"string"}},
  "additionalProperties":false }    // ← html_embed의 additionalProperties:false 와 동형

// fft_preview
{ "type":"object","required":["series","fs"],
  "properties":{"series":{"type":"array"},
    "fs":{"type":"number","exclusiveMinimum":0,"description":"sampling rate [Hz]"},
    "window":{"enum":["hann","hamming","blackman","rect"],"default":"hann"},
    "one_sided":{"type":"boolean","default":true},
    "scale":{"enum":["amplitude","psd","db"],"default":"amplitude"}},
  "additionalProperties":false }

// graph_lint_output / graph_embed_block
{ "type":"object","required":["html_path"],
  "properties":{"html_path":{"type":"string"},
    "height_px":{"type":"integer","minimum":60,"maximum":4000,"default":520},  // html_embed 계약
    "caption":{"type":"string","maxLength":200}},
  "additionalProperties":false }
```
`height_px:60–4000`, `caption maxLength:200`은 `report-write` `html_embed.py` 실측 계약에서 직접 가져옴.

### 9.3 3-view 한 capability 예시 (stress-strain)
```python
# builder.py
def render(graph_type, series, axes, params, features, out_path, embed_mode="standalone", **kw) -> dict: ...
# mcp_server.py
_tool("graph_render", "정규화 config로 단일 self-contained HTML 생성", {...})
_DISPATCH["graph_render"] = _do_render
# cli.py
@graph_app.command("render")
def graph_render(graph_type: str, in_: Path, out: Path, embed_mode: str = "standalone"): ...
```

---

## 10. 데이터 인제스트 & 공학 후처리 파이프라인

### 10.1 입력 데이터 포맷 (`inputspec.py`, pydantic)
```python
class Series(BaseModel):
    name: str
    x: list[float] | None = None        # None이면 공유 x
    y: list[float | None]               # None = gap (선 끊김)
    unit_x: str | None = None; unit_y: str | None = None
    color: str | None = None            # None이면 색맹안전 팔레트 자동
    style: Literal["line","markers","line+markers","step"] = "line"

class AxisMeta(BaseModel):
    quantity: str; unit: str
    scale: Literal["linear","log","symlog"] = "linear"

class RawSource(BaseModel):             # 장비 raw 인제스트
    format: Literal["csv","tsv","instron","mts","tdms","array"]
    header_rows: int | None = None
    sample_rate: float | None = None    # fs (Hz) — 헤더 파싱 또는 사용자 제공
    columns: dict[str, str] | None = None
    meta: dict[str, float] = {}         # {A0, L0, ...}

class GraphInput(BaseModel):
    graph_type: str
    series: list[Series] = []; shared_x: list[float] | None = None
    x_axis: AxisMeta | None = None; y_axis: AxisMeta | None = None
    raw: RawSource | None = None        # raw 있으면 ingest→series
    post: dict = {}                     # 후처리 config
    overrides: dict = {}                # 사용자 수동조정 — round-trip 보존
```
레거시 관용: `[[x,y],…]`, `{x:[...], series:{a:[...],b:[...]}}`, CSV 텍스트, 장비 raw 헤더를 모두 `Series[]`로 흡수. **파싱 실패 = 추정 금지, 질문**(§8).

### 10.2 후처리 엔진 (Python 사전계산 ↔ JS 실시간 경계)
**원칙**: 무거운/일회성/정확성 민감 계산은 **Python 사전계산**(빌드타임, numpy/scipy). 사용자가 슬라이더로 실시간 조절하는 것만 **JS 클라이언트**(numeric/fft.js, 미리보기 근사).

| 후처리 | 모듈 | 필요 배경정보 | Python/JS | 정확성 함정(§10.3) |
|---|---|---|---|---|
| force→stress σ=F/A₀ | units.py | **A₀** [mm²] | Python | N6 A₀ 단위 혼동(mm² vs m²) → 1e6 배 |
| disp→strain ε=ΔL/L₀ | units.py | **L₀** [mm], 영점 | Python | baseline 미보정 → strain offset |
| eng↔true (σ_t=σ(1+ε), ε_t=ln(1+ε)) | units.py | (파생) | Python | N7 네킹 이후 true 무효 |
| FFT | spectral.py | **fs** [Hz], 윈도 | Python(고정)+JS(슬라이더) | N1 누설, N2 aliasing, N4 단측 스케일 |
| PSD | spectral.py | fs, 윈도, ENBW | Python | 윈도 보정계수 누락 |
| LP/HP/BP Butterworth | filters.py | fs, fc, 차수 | Python(filtfilt)+JS(미리보기) | N8 위상왜곡(→filtfilt 영위상) |
| 필터→시간영역 역반영 | filters.py | fs | Python 재계산(확정 시) | 경계 transient |
| Savitzky-Golay | smoothing.py | window, polyorder | Python | N3 비균일 dt 무효 |
| 도함수/접선 Et | calculus.py | (없음) | JS(실시간)+Python(곡선) | N9 노이즈 미분 증폭 |
| 적분(toughness) | calculus.py | (없음) | Python | N10 사다리꼴 vs 심슨, 단위 |
| resample/보간 | resample.py | target dt | Python | N3 비균일→균일 선행 필수 |

**필터 튜닝 흐름(요구 4 "FFT 보면서 필터 조정 → 시간 스케일 반영"):**
1. Python이 원신호 FFT 사전계산 → 주파수뷰 초기 표시.
2. `filter-panel.js`(JS)가 차단주파수 슬라이더 → **클라이언트 fft.js로 미리보기 마스크** 실시간(가벼운 근사).
3. 사용자 확정 → `graph_render` 재호출 시 **Python filters.py가 filtfilt(영위상)로 정확 재계산**, 시간영역 역반영, 새 HTML 산출.
4. JS 근사와 Python 확정값을 HUD에 **"preview"/"exact" 라벨로 구분 표시**.

**핵심 시그니처(test_postprocess.py 골든값 대상):**
```python
def fft_onesided(y, fs, window="hann", detrend="constant", nfft=None):
    """반환: freqs[Hz], amp(단측, ×2 except DC/Nyquist), info{enbw, leakage_warn}.
       비균일 dt면 ValueError('resample to uniform dt first')."""
def butter_filtfilt(y, fs, kind, fc, order=4):
    """영위상 Butterworth. fc>=fs/2면 ValueError('cutoff exceeds Nyquist')."""
def eng_to_true(sigma_eng, eps_eng):
    """σ_t=σ(1+ε), ε_t=ln(1+ε). 네킹 이후 invalid 플래그 동반."""
def savgol(y, x, window, polyorder):
    """비균일 x면 resample 경고. window 홀수, polyorder<window 강제."""
```

### 10.3 수치 정확성 함정 (반드시 막는 것)
| # | 함정 | 방어 |
|---|---|---|
| N1 | FFT 누설(non-periodic) | 윈도(Hann 기본) + `leakage_warn` 플래그 + 윈도 보정계수 |
| N2 | Aliasing | fs 대비 대역 검사, Nyquist 초과 경고. fc≥fs/2 차단 |
| N3 | 비균일 샘플 | dt 분산 감지 → "resample to uniform dt first" 강제(ValueError) |
| N4 | 단측 FFT 스케일 | ×2 보정(DC/Nyquist 제외) 명시, amp vs PSD 구분 |
| N5 | 로그축 0/음수 | symlog 폴백 또는 clamp + UI 경고 배지 |
| N6 | A₀ 단위 혼동 | 단위 명시 필수(mm²), 환산 전 차원검사 |
| N7 | true stress 네킹 후 무효 | 네킹 이후 `true_invalid` 플래그 → 점선/회색 |
| N8 | 필터 위상왜곡 | filtfilt(영위상) 기본, 경계 transient 마스킹 |
| N9 | 노이즈 미분 증폭 | SG-미분 권고(raw 차분 금지), 접선은 국소 회귀 |
| N10 | 적분 단위/방법 | 사다리꼴 기본 + 단위 라벨(toughness = MJ/m³) |

### 10.4 도메인 지식 인코딩 위치 (단일 책임 분배)
| 지식 종류 | 인코딩 위치 |
|---|---|
| 무엇이 필수 파라미터인가 | `catalog/graph-types.json` requires + recipe.requires() |
| 왜 필요하고 어떻게 묻나 | `prompt.py _INPUT_HINTS` + `feedback.Question` |
| 수식/변환 정확성 | `postprocess/*.py` |
| 시각적 공학 의미(구간/마커) | plugin JS + recipe config |
| 단위·축 의미 | `inputspec.AxisMeta` + 축 타이틀 렌더 |
| 타입별 좌표 관례 | recipe + catalog (bode=dual 로그, s-n=로그-로그) |
| 실시간 파생 의미 | plugin onHover (live-tangent → Et[GPa]) |

핵심: **수치 정확성은 Python postprocess, 시각적 공학 의미는 plugin JS, 필수성·질문은 catalog+prompt+feedback에 분리.** 한 곳에 뭉치면 새 타입 추가 시 전 영역을 건드려 병렬성이 깨진다.

---

## 11. 단일 self-contained HTML 산출 & 번들링

### 11.1 빌더 조립 (`builder.render` → `assemble`)
```python
def assemble(rtype, norm, embed_mode) -> str:
    tpl     = read_asset("shell/template.html")
    engine  = read_asset(f"engine/{rtype.engine}.min.js")   # 고정 자산
    css     = read_asset(f"engine/{rtype.engine}.css")
    plugins = "\n".join(read_asset(f"plugins/{p}.js") for p in rtype.plugins)
    boot    = read_asset("shell/boot.js")
    ev      = read_asset("ENGINE_VERSION").strip()
    cfg_js  = safe_js_literal({"plugins": rtype.plugins,
                               "options": rtype.options | norm["options"],
                               "series": norm["series"]})    # serialize.py
    html = (tpl
      .replace("{{ENGINE_VERSION}}", ev)
      .replace("{{CSS}}", f"<style>{css}</style>")
      .replace("{{ENGINE}}", f"<script>{engine}</script>")
      .replace("{{PLUGINS}}", f"<script>window.XYPlugins={{}};\n{plugins}</script>")
      .replace("{{CONFIG}}", f'<script id="graph-config" type="application/json">{cfg_js}</script>')
      .replace("{{BOOT}}", f"<script>{boot}</script>"))
    if embed_mode == "srcdoc-fragment":
        html = wrap_for_srcdoc(html)                         # 따옴표/엔티티 2중 이스케이프
    return html
```
`template.html`은 **단일 루트 `<div id="graph-root">`**만 갖는다(외부 프레임 0 = 요구 3). config를 `<script type="application/json" id="graph-config">`에 두는 이유: (a) **재편집 round-trip**(추출→수정→재생성, 사용자 수동조정 보존), (b) `JSON.parse(textContent)`가 JS literal 주입보다 sentinel 안전.

### 11.2 안전 직렬화 (`serialize.py` — 단일 함수)
```python
_ESCAPES = {"<":"\\u003c", ">":"\\u003e", "&":"\\u0026",
            " ":"\\u2028", " ":"\\u2029"}   # </script>, JS line-sep 차단
def safe_js_literal(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True,   # sort_keys → 결정론
                   separators=(",",":"), allow_nan=False)     # NaN/Inf 거부(사전에 null로 치환)
    for k, v in _ESCAPES.items(): s = s.replace(k, v)
    return s.replace("`", "\\u0060")                          # 백틱
```
**빌더 어디서도 raw `json.dumps` 금지.** `sort_keys=True`가 결정론(P7)과 sentinel(P3)을 동시에 잡는다.

### 11.3 self-contained 3겹 방어
1. **빌드 시점**: `read_asset`만. 엔진/CSS/폰트(`system-ui` 스택)/데이터 전부 인라인. `<link>`·`<script src>`·`@import url(http…)` 금지.
2. **정적 게이트** (`graph_lint_output` + `test_self_contained.py`): 산출 HTML에 `https?://`/`src=`/`@import url`/`//cdn` 0개, 단일 `<html>` 루트. 위반 시 빌드 실패(P6).
3. **결정론** (`test_builder_determinism.py`): 동일 입력 → 바이트 동일 HTML. 타임스탬프/dict 순서/plugin 순서 누출 금지(P7).
```python
def lint(html: str) -> dict:
    ext = re.findall(r'(?:src|href)\s*=\s*["\'](https?:|//)', html)
    roots = re.findall(r'(?im)^\s*<html', html)
    return {"ok": not ext and len(roots)==1, "external_urls": len(ext),
            "self_contained": not ext, "single_root": len(roots)==1,
            "srcdoc_safe": serialize.is_srcdoc_safe(html)}
```
산출 HTML에 `<!-- graph-engine v1.0.0 sha256:... -->` 주석 + `<meta name="graph-engine">`로 추적성(P4).

### 11.4 생태계 통합 계약
- **입력측**: graph-skill 빌더는 aidatahub를 import하지 않는다. 오케스트레이터 LLM이 raw 시계열 + A0/L0/fs 메타를 끌어와 graph config로 넘긴다.
- **출력측**: 단일 `.html` 디스크 출력 → report-write draft `extra_blocks`에 `html_embed` 블록 `{"local_path":"d:/.../graph.html","height_px":N,"caption":...}` → `upload_chain`이 file_id 자동 치환 → sandbox iframe 렌더. **graph-skill은 report-skill을 import하지 않는다**(파일시스템 경로로만 결합).
- **계약 위반(외부 URL/raw HTML 문자열) 시 rich_text로 강등** → self-contained 정적검증이 출력측 불변식.
- **계약 핀**: `html_embed` content_schema 해시 `8733ed67ec759a04`. widgets-sync가 이 위젯 modified를 보고하면 graph-skill 출력규격(height_px 상한 4000, file_id 필수, additionalProperties:false) 재검증. `INTEGRATION.md`에 명시.
- `embed_mode=srcdoc-fragment`: 호출자가 직접 `iframe.srcdoc`에 주입할 때(samples 패턴).

---

## 12. 로드맵 & 규격화

### 12.1 0→1 마일스톤: base-xy MVP (v0.1.0)
**base-xy가 Case1 좌측 수준이 되기 전까지 다른 타입은 시작하지 않는다.**

IN SCOPE (설정 없이 자동으로 켜짐): N개 멀티시리즈(시리즈별 독립 x), 색맹안전 팔레트(Okabe-Ito)+dash 분기, NaN/null gap, monotone-cubic/straight/step 곡선; x/y 크로스헤어+축값 라벨, nearest-x bisect 시리즈별 동시 도트 스냅, near-curve 임계, 멀티시리즈 통합 툴팁(경계 auto-flip+단위), 우상단 HUD, 클릭 lock; 휠줌(커서중심·x/y 독립+동시)·드래그팬·박스줌·더블클릭 리셋·auto-fit; **로그↔선형 토글(x/y 독립)+0/음수 가드**; nice ticks(1-2-5)·로그 decade+minor·SI 접두; 범례 토글(클릭 hide·더블클릭 isolate)·major/minor 격자(10×10); 비침습 컨트롤바; **다크모드(prefers-color-scheme+수동토글)**; `width:100%`+`aspect-ratio`+**ResizeObserver**+devicePixelRatio; PNG/CSV/JSON export·설정 hash permalink; **self-contained**.

OUT OF SCOPE (나중 plugin): region shading, 실시간 접선, FFT, 필터, 듀얼축, 곡선피팅, 통계밴드, SVG export, uPlot 백엔드, 키보드 접근성 완전판, i18n.

**v0.1.0 DoD (체크 가능):**
```
[엔진] core.js→min.js 빌드, ENGINE_VERSION=1.0.0 baked / 6개 훅 시그니처 동결
[3-view] builder.render("base-xy") + graph_render(MCP) + `graph render xy`(CLI) 시그니처 일치
[산출물] 단일 .html 외부 URL 0개 / srcdoc-safe 직렬화 / height_px 메타 동봉
[테스트] test_determinism(byte-identical) / test_self_contained / test_schema
         golden/base_xy 생성 / Playwright(canvas·휠줌·hover→HUD·로그토글·console.error==0)
[수동 합격 — "Case1 수준" 주관 게이트]
  멀티시리즈 3개 hover→3도트 동시 스냅+통합 툴팁 / 로그토글 즉시 재렌더(음수 가드) /
  리사이즈 시 레티나 선명도 / 다크모드 토글 시 전 색 토큰 전환
[패키징] wheel에 data/engine/*.js 동봉(package_data 검증) / `graph --version`==importlib.metadata
```

### 12.2 모듈/타입 로드맵 (16행, 보편→특화)
| # | 타입/모듈 | 상속 베이스 | 추가 plugin | 필요 배경정보 | 후처리 | 난이도 | 버전 |
|---|---|---|---|---|---|---|---|
| 0 | **base-xy** | — (코어) | 코어 내장(hover/zoom/log/legend/dark/export) | x/y quantity+unit | 없음 | ★★★★ | 0.1.0 |
| 1 | scatter/parametric | base-xy | unsorted-mode, point-markers | 점 의미 | 미정렬 감지→산점 | ★ | 0.2.0 |
| 2 | **stress-strain** | base-xy | unit-convert, region-shading, named-markers, live-tangent, props-table | **A0, L0**, region 경계 | F,ΔL→σ,ε (eng→true) | ★★★ | 0.2.0 |
| 3 | time-series | base-xy | time-axis, overview-brush, gap-connect | 시간 단위, dt/timestamps | 정렬·리샘플 | ★★ | 0.3.0 |
| 4 | dual-axis | base-xy | secondary-y, axis-color-match | 우축 quantity+unit | 좌우 독립 스케일 | ★★ | 0.3.0 |
| 5 | cumulative/integral | base-xy | integrate-curve, area-fill | 적분 의미 | 누적합/사다리꼴 | ★★ | 0.3.0 |
| 6 | **fft-spectrum** | time-series | fft-view, domain-toggle, peak-detect | **fs**, window | FFT(one-sided amp/PSD) | ★★★ | 0.4.0 |
| 7 | **filter-tuner** | fft-spectrum | digital-filter(슬라이더), time-reconstruct | fs, filter type/order | Butterworth/FIR→시간역반영 | ★★★★ | 0.5.0 |
| 8 | equipment-raw 후처리 | time-series | baseline-zero, gain-offset-cal, decimate, crop-trim | 채널 메타, 영점 | 영점/캘리브/데시메이션/crop | ★★★ | 0.5.0 |
| 9 | histogram/box-plot | base-xy | bin-aggregate, box-whisker, stat-band | bin 수/폭, 그룹 | binning, 사분위·IQR | ★★ | 0.6.0 |
| 10 | bode/주파수응답 | fft-spectrum | dual-log-axis, mag-phase-stack, nyquist-mode | 입출력 쌍 또는 H(f) | TF 추정, mag[dB]+phase | ★★★★ | 0.6.0 |
| 11 | hysteresis/cycle | scatter | cycle-color, loop-area, cycle-slider | 사이클 인덱스 | 사이클 분리, loop 면적 | ★★★ | 0.7.0 |
| 12 | curve-fit overlay | base-xy | regression, residual-panel | 모델(Ramberg-Osgood, Hollomon σ=Kεⁿ) | 파라미터 추정+R²+잔차 | ★★★ | 0.7.0 |
| 13 | contour/heatmap | (2D 코어 확장) | grid-field, color-scale-legend, iso-lines | z 의미+단위, grid 규칙성 | 2D 보간, 등고선 추출 | ★★★★★ | 0.8.0 |
| 14 | table 위젯 | (table 코어) | sortable, row-highlight, graph-sync | 컬럼 의미+단위 | 정렬/포맷 | ★ | 0.8.0 |
| 15 | s-n/fatigue | scatter | log-log, runout-marker, basquin-fit | 응력비 R, run-out 임계 | 로그-로그, Basquin 피팅 | ★★★ | 0.9.0 |

빌드 순서 원칙: (a) 같은 행의 plugin은 per-file 병렬(훅 계약 동결). (b) 상속 베이스가 먼저 DoD 통과해야 자식 시작. (c) 한 버전 = minor 묶음 하나 = 골든 세트 하나. (d) **scatter(#1)를 stress-strain보다 먼저**(미정렬 xy가 hysteresis/s-n의 토대).

### 12.3 실행 타임라인
```
v0.1.0  base-xy 코어 MVP                      ← 게이트: 다른 타입 시작 전 필수
v0.2.0  scatter + stress-strain               ← region/tangent/markers, A0/L0 resolve
v0.3.0  time-series + dual-axis + integral
v0.4.0  fft-spectrum                          ← fs resolve, FFT transform
v0.5.0  filter-tuner + equipment-raw          ← 필터→시간역반영 (요구 4 핵심)
v0.6.0  histogram/box + bode  [+uPlot 백엔드 도입 검토]
v0.7.0  hysteresis + curve-fit
v0.8.0  contour/heatmap + table 위젯           ← 2D 코어 확장
v0.9.0  s-n/fatigue + 도메인형
v1.0.0  훅 계약 동결 + 임베드 계약 안정 + 전 타입 golden green
```
각 minor = "spec 작성 → plugin 구현(per-file 병렬) → golden 생성 → §12.4 체크리스트 → 릴리스". **plugin 합성 덕에 타입이 늘어도 코어는 안 건드린다 = 회귀 표면이 좁게 유지된다.**

### 12.4 새 타입 추가 체크리스트 (`docs/ADD-TYPE-CHECKLIST.md`, 레시피 §10 변형)
```
[Spec] docs/specs/<type>.md 작성(코드보다 먼저) + REQUIRES 표 + ask 문구
[3-view] recipes/<type>.py(normalize 화이트리스트+PLUGINS+REQUIRES) /
         data/plugins/<plugin>.js(신규면 6훅) / builder 진입점 /
         mcp_server _tool+_do+_DISPATCH / cli 미러(바이트 동일 재현)
[P1 비대칭] 새 requires 필드 = 그 값 쓰는 transform 슬롯 동시 추가 + _INPUT_HINTS/_REQUIRES_HINTS 갱신
[P2 패스스루] 새 옵션이 config 화이트리스트 등록 + <script id=graph-config> round-trip 보존
[카탈로그/버전] refresh_catalog.py 실행 / ENGINE_VERSION bump 판단(훅 변경=major) / pyproject minor bump
[테스트] fixtures/<type>.json / gen_golden.py / test_render_smoke 인터랙션 어서션 /
         test_self_contained·determinism·schema·requires 통과 / wheel 재빌드 후 .js 동봉 확인(P4)
[릴리스] samples/<type>/index.html 갱신 / len(_DISPATCH) 증가 + `graph --version` 스모크
```

---

## 13. 품질 / 테스트 / 버전

### 13.1 3층 테스트 (산출물 모델 — HTML 자체를 검증)
**1층 (빠름, 순수 Python)** — 결정론·스키마·self-contained:
| 테스트 | 검증 | 함정 |
|---|---|---|
| test_determinism | 동일 fixture → byte-identical (10회) | P7 |
| test_self_contained | 외부 URL 0개 정규식 | P6 |
| test_serialize | `</script>`/` `/백틱/base64 경계 | P3 |
| test_schema | config JSON Schema valid, additionalProperties:false | T2 |
| test_validate_missing | REQUIRES 누락 → 정확한 question | P8 |
| test_postprocess | FFT/필터/단위 수치 골든값(scipy 레퍼런스 + 해석해) | 정확성 |

**2층 (구조 골든, 회귀 차단)** — byte-exact HTML이 아니라 **구조 골든**(R-golden 결정):
```python
def test_golden_structure(graph_type):
    out = builder.render(graph_type, load_fixture(graph_type))
    g = json.loads((GOLDEN/f"{graph_type}.golden.json").read_text())
    assert extract_config(out) == g["config"]          # GRAPH_CONFIG 직렬화
    assert resolved_plugins(out) == g["plugins"]       # plugin 목록
    assert engine_sha(out) == g["engine_sha256"]       # 엔진 자산 해시
```
엔진 minify 리포맷에 과민하지 않게. 엔진 자체 시각 회귀는 3층 픽셀 해시가 담당.

**3층 (Playwright, 느림 — PR/릴리스 시)** — 시각 회귀 + 인터랙션 스모크:
```python
async def test_stress_strain_interactions(page):
    page.set_content(builder.render("stress-strain", fixture))
    assert await page.eval("!!document.querySelector('canvas').getContext")
    errors=[]; page.on("console", lambda m: errors.append(m) if m.type=="error" else None)
    await page.mouse.move(*on_curve)                   # hover
    hud = await page.text_content("#hud")
    assert "Et" in hud and "MPa" in hud                # spec §7 어서션
    await page.mouse.click(*on_curve)                  # lock
    assert await page.eval("window.__tangentLocked === true")
    assert pixel_diff(await page.screenshot(), GOLDEN/"stress_strain.png") < 0.02  # ΔE<2%
    assert errors == []
```
CI 게이트 순서: 1층(초, 항상) → 2층(초) → 3층(분, PR/릴리스).

### 13.2 버전 정책 — 두 개의 독립 버전
**패키지 버전** (`importlib.metadata` 단일 진실, 하드코딩 금지):
- minor: 새 graph-type / 새 plugin / 새 도구
- patch: 엔진 버그픽스/스타일/recipe 손실 보존
- major: config 출력 스키마 breaking / 훅 계약 변경 / requires 필수화

**엔진 자산 버전** (`data/ENGINE_VERSION`, 산출 HTML에 baked):
- 6개 훅 시그니처 변경 = 엔진 major (모든 plugin 영향)
- 엔진 draw 로직 = 엔진 minor/patch
- **분리 이유**: 배포된 HTML(아카이브 영구 게시)은 엔진을 고쳐도 안 바뀐다. "어떤 HTML이 어떤 엔진으로 그려졌나" 추적 → 회귀 재생성 가능(P4 근본 방어).

**함정 방어**: P4(wheel `--force-reinstall` 후 build, golden에 ENGINE_VERSION baked), P5(구 dist-info 청소), §9.5(importlib.metadata 단일 진실).

---

## 14. 횡단 관심사 (완결성 비평 반영)

| 영역 | 방침 |
|---|---|
| **접근성/키보드** | MVP: Tab 포커스 + Esc(lock 해제) + 컨트롤바 버튼 aria-label. 완전판(화살표 패닝, 스크린리더 데이터테이블 대체)은 v0.6+. |
| **i18n** | 축 라벨/단위/HUD 문구는 데이터-종속 → LLM이 ko/en 채움. UI 고정문자열(범례/버튼)은 엔진 `lang` 옵션(ko 기본, en 토글). 숫자 포맷 locale. |
| **성능/다운샘플** | >5k pt 시 LTTB(Largest-Triangle-Three-Buckets) 다운샘플 후 렌더, 줌 시 해당 구간 원본 복원. >50k는 uPlot 백엔드(v0.6). 오프스크린 캔버스 캐싱. |
| **모바일/터치** | pointer 이벤트 통일(mouse/touch), 핀치줌, 탭=hover/lock. 컨트롤바 터치 타겟 ≥44px. |
| **보안(XSS)** | 데이터/축 라벨 인라인 시 `safe_js_literal` 단일 함수로 escape(§11.2). 사용자 문자열은 `textContent`로만 삽입, `innerHTML` 금지. sandbox iframe이 2차 격리. |
| **색맹 팔레트** | Okabe-Ito 8색 기본 + ≥8 시리즈 dash 분기 + 마커 모양 분기. 명도 대비 WCAG AA. |
| **상태 직렬화** | 줌/로그/isolate 상태를 URL hash(또는 config)로 permalink. **단 결정론(P7) 보존을 위해 산출 HTML의 초기 상태는 항상 고정**, 사용자 인터랙션 상태는 런타임에만. |
| **에러/빈 데이터** | 빈 시리즈/전부 NaN/단일 점 → 엔진이 "데이터 없음/부족" 플레이스홀더 + 콘솔 경고(크래시 금지). |
| **인쇄/PDF** | `@media print` 다크→라이트 강제 + 컨트롤바 숨김 + 벡터 느낌 고DPR 렌더. |
| **애니메이션** | 초기 진입 200ms ease 1회(prefers-reduced-motion 존중). 인터랙션은 즉시(애니메이션 없음). |

---

## 15. 미해결 질문에 대한 결정 (4개 설계 공통 리스크 해소)

| 리스크 | **결정 (권장 기본값)** |
|---|---|
| **uPlot 백엔드 선/후불** | **후불.** MVP는 vanilla 단일. 단 plugin은 좌표를 반드시 `view.scaleX/invX` 경유(픽셀 직접계산 금지) → 나중 백엔드 교체 시 좌표 로직 재사용. uPlot은 v0.6 대용량 실증 시 도입, 그 전엔 `catalog.backend` 필드만 예약. `view.draw.*` 추상화는 강제하지 않음(과한 선부담). |
| **golden 취성** | **구조 골든 채택.** 2층은 `GRAPH_CONFIG`+plugin목록+엔진 sha만 비교(byte-exact HTML 아님). 엔진 시각 회귀는 3층 픽셀해시(ΔE<2%). byte 결정론은 test_determinism(동일입력 2회)에서만. → 엔진 리포맷에 무뎌지지 않으면서 진짜 회귀를 잡는다. |
| **Python/JS 수치 이중구현 불일치** | **Python이 단일 진실.** 확정 산출은 항상 Python(numpy/scipy) 빌드타임 사전계산. JS 수치(fft.js)는 슬라이더 "미리보기 근사"로만, HUD에 "preview" 라벨. 동등성은 골든 허용오차로 고정. 수치 정답은 scipy 레퍼런스 + 알려진 해석해(순수 정현파 FFT 피크 등) 단위테스트가 보증(golden은 우리 출력을 고정할 뿐 정답이 아니므로 별도 해석해 테스트 필수). |
| **filter-tuner 실시간 성능 vs 정확성** | **정확성 우선, 미리보기 분리.** 확정값은 zero-phase filtfilt(공학 정확). 슬라이더는 디바운스+데시메이션된 단방향 빠른 근사(미리보기 라벨). 수만 점은 WebWorker 오프로딩 옵션. preview/exact HUD 라벨로 차이 명시. |
| **aidatahub A0/L0/fs 스키마 불확실성** | **graph-skill은 무관(순수 렌더러).** `resolvable_from`은 힌트일 뿐, 실제 조회는 오케스트레이터 책임. record가 구조화 필드를 안 주고 LLM이 RAG 청크에서 추출한 값이면 **"추정"으로 간주 → 반드시 사용자 confirm**. validate가 confirm 안 된 값을 missing 취급할 수 있게 `params._confirmed` 플래그 도입 → P8 방어 강화. (실서버 카탈로그는 연결 가능해지면 실측해 recipe source-adapter 확정.) |
| **height_px vs 반응형 충돌** | **MVP: 고정 height_px + 내부 width:100%.** `graph_render`가 `recommended_height_px`(타입별 기본, 16:10 가정) 산출. v0.3+: `srcdoc-fragment`에서 ResizeObserver가 부모에 `postMessage`로 실제 높이 통지하는 auto-height 모드 옵션. |
| **수치 커널 정확성 책임** | **postprocess 각 함수 = scipy 레퍼런스 대비 골든 + 해석해 단위테스트.** 누설/aliasing/비균일은 명시적 경고 플래그(N1–N10). "그럴듯하게 틀린 그래프"(P8의 수치판)를 테스트로 차단. |

---

## 16. SKILL.md 스켈레톤 (Tools / Flows / Rules)

```markdown
# graph-skill — 인터랙티브 단일 HTML 그래프 생성 스킬

데이터(여러 (x,y) 시리즈 + 축 의미·단위 + 그래프 타입 + 배경 물리값)를 받아
**검증된 고정 렌더 엔진**으로 self-contained 단일 .html 을 생성한다.
LLM은 엔진을 즉흥 코딩하지 않는다 — 엔진/plugin은 버전관리된 번들 자산이다.

## Tools
- graph_types_list — graph-type + 상속 트리. 항상 먼저.
- graph_schema_get <type> — 입력 스키마 + requires[](필수 물리값) + plugin 목록.
- graph_validate_inputs <type> <payload> — 렌더 전 필수. missing[]+questions[] 반환.
- graph_render <type> ... — 단일 self-contained .html 생성. 경로 반환.
- graph_lint_output <html> — 외부 URL 0/단일 루트/srcdoc-safe 검증.
- fft_preview / filter_apply / resample — 후처리 수치 미리보기(HTML 아님).
- graph_embed_block <html> — report-write html_embed draft 조각 생성.

## Flow A — 기본 그래프
1. graph_types_list → 타입 선택. 2. graph_schema_get → requires 확인.
3. graph_validate_inputs. missing 비면 4, 아니면 Flow B.
4. graph_render → graph_lint_output(게이트) → (게시 시) graph_embed_block.

## Flow B — 배경정보 누락 해소 (요구 2 핵심)
1. validate가 missing[] 반환 → 렌더 금지.
2. 각 missing의 ask 문구로 사용자에게 질문(또는 aidatahub record 조회 시도).
3. 답 받으면 params 채워 validate 재호출. ok=true면 render.

## Flow C — FFT/필터 (요구 4)
1. fs 확보(없으면 Flow B). 2. fft_preview로 스펙트럼 검토.
3. filter_apply로 차단주파수 조정 미리보기. 4. 확정 config로 graph_render(filter-tuner).

## Flow D — report-write 게시 핸드오프
1. graph_render → graph_lint_output. 2. graph_embed_block 조각을 report-write draft
   extra_blocks에 추가. 3. report-write가 local_path→file_id 자동 업로드 → sandbox iframe.

## Rules
- NEVER invent 축 단위·물리 배경값(A0, L0, fs). validate가 missing 반환 시 렌더 전
  반드시 질문. 추정값으로 그리면 '자신있게 틀린' 그래프가 된다.
- aidatahub 청크에서 추출한 값은 추정으로 간주 → 사용자 confirm 후 사용.
- 엔진/plugin은 LLM이 작성하지 않는다 — graph_render의 번들 자산만 사용.
- 산출물은 외부 프레임 0·self-contained. graph_lint_output 통과 못 하면 게시 금지.
- 정적 PNG가 필요하면 aidatahub stress_strain_plot, 인터랙티브 HTML이면 graph-skill (disambiguation).
- 게시는 html_embed 계약(file_id/local_path, height_px 60–4000)에 묶임.
```

---

## 17. 즉시 착수 단계 (Step 0–2 구체)

**Step 0 — 스캐폴딩 (레시피 §11 Step1–7):**
`pyproject.toml`(name=graph-skill, package_data=`data/**/*`) + `settings.py` + `serialize.py` + `catalog.py` 로더 + `recipes/base.py`(Recipe ABC) + `data/shell/{template.html,boot.js}` + 빈 `catalog/graph-types.json` + `SKILL.md` 첫 Flow + `mcp_server.py`(ping격 `graph_types_list`) + `cli.py`.

**Step 1 — base-xy 엔진 (v0.1.0, §12.1 DoD 전체):**
`data/engine/xy-core.{js,css}` 작성(Case1 baseline 전 feature) → `build_engine.mjs`로 min+sha → `recipes/base_xy.py` → 3-view(`graph_render`/`graph render xy`/`builder.render("base-xy")`) → 1·2·3층 테스트 + golden. **이 DoD 통과가 전체 게이트.**

**Step 2 — stress-strain (v0.2.0):**
`postprocess/units.py`(σ=F/A0, ε=ΔL/L0, eng→true) + plugins(`unit-convert`/`region-shading`/`named-markers`/`live-tangent`/`props-table`) + `recipes/stress_strain.py`(requires A0,L0) + `validate.check` missing 루프 + `_INPUT_HINTS` → golden + Playwright hover→HUD(Et) 스모크. **요구 2(누락 피드백) 첫 실증.**

---

## 18. 엔진 패밀리 일반화 & 3D CAD 확장 경로

> **실행 계획은 [`EXPANSION-ROADMAP.md`](EXPANSION-ROADMAP.md)** 참조 — 배치 G–N, `cad3d-core`(=이하 `cad-viewer`) 구체 구현/검증 설계, 우선순위. 아래 §18.3 스케치는 그 문서가 구체화·대체한다(명칭 `cad-viewer`→`cad3d-core` 정합).

graph-skill은 "2D 그래프 생성기"가 아니라 **"인터랙티브 단일 HTML 아티팩트 생성기"**다. `xy-core`(Canvas 2D)는 첫 번째 **엔진 패밀리(engine family)**일 뿐이고, 같은 builder/catalog/validate/self-contained/report-write 기계 위에 형제 패밀리를 얹는다. **3D CAD 가시화(`cad-viewer`)가 대표적 2번째 패밀리.**

### 18.1 엔진-불가지론 계층 (MVP부터 지켜야 할 seam)
- **catalog 타입은 `engine`(패밀리) 필드를 가진다.** `xy-core` | (미래) `cad-viewer` | `table`. builder는 `data/engines/<engine>/`를 읽을 뿐, 패밀리에 무지하다.
- **boot.js는 엔진 레지스트리로 디스패치한다.** `window.GraphEngines[family]` 팩토리를 찾아 `mount + config`로 인스턴스화. 패밀리별 생성자만 다르고 부팅 글루는 공통.
- **빌더의 입력은 `series[]`가 아니라 일반 `assets`다.** xy는 `assets.series`(인라인 JSON), cad는 `assets.model`(파일 ref 또는 base64). recipe.normalize가 패밀리별로 정규화.
- **validate/requires/missing/질문 루프는 패밀리 무관.** cad-viewer도 `requires`(예: STEP 단위계, 단면 평면 법선)를 같은 메커니즘으로 묻는다.
- **self-contained·serialize·lint·embed 계약은 패밀리 무관.** 단, 대용량 바이너리(GLB)는 §18.3 번들 모드.

### 18.2 데이터 자산 트리 (패밀리별 격리)
```
data/
├── engines/
│   ├── xy-core/        engine.js, engine.css, ENGINE_VERSION, plugins/*.js
│   └── cad-viewer/     (미래) engine.js(three.js 기반), engine.css, plugins/*.js
│                       └ section-plane.js, exploded-view.js, measure.js, wireframe.js
├── shell/             template.html, boot.js  (엔진 레지스트리 디스패치 — 공통)
├── vendor/            (미래) three.min.js, occt-import-js.wasm 등 패밀리 의존 번들
├── numeric/           fft.js (xy 슬라이더 미리보기)
└── catalog/           types.json, manifest.json
```
plugin은 패밀리에 종속(Canvas region-shading ≠ three.js section-plane)이므로 `data/engines/<family>/plugins/`에 격리.

### 18.3 cad-viewer 패밀리 — 향후 설계 스케치
- **입력 파이프라인 (Python postprocess)**: STEP/IGES → 메시 변환. `postprocess/cad.py`가 OpenCASCADE(pythonocc-core) 또는 FreeCAD headless 또는 WASM `occt-import-js`로 **STL/GLB 추출**. 테셀레이션 품질(선형/각편차)은 `requires` 또는 옵션. STEP 단위계(mm/inch) 명시 필요 → 없으면 질문(P8 그래프판).
- **렌더 엔진 (JS)**: three.js + GLTFLoader(또는 Google `<model-viewer>` 웹컴포넌트). 궤도 카메라, 조명, 그림자, 머티리얼.
- **CAD 특화 plugin(= "그래프의 인터랙션"에 대응)**: `section-plane`(단면 뷰 — 평면 법선/오프셋 슬라이더로 clipping plane), `exploded-view`, `measure`(거리/각도/반경 픽킹), `wireframe`/`edges` 토글, `view-cube`(iso/front/top 스냅), `cross-section-fill`(절단면 capping), 치수/주석(PMI), `explode-slider`.
- **두 가지 모드**: (a) **3D 뷰어** — 모델을 궤도 회전하며 보기, (b) **단면 뷰** — clipping plane로 내부 단면 + capping. 둘 다 같은 엔진의 plugin 토글.
- **graph-type(=artifact-type) 예시**: `cad-3d-viewer`(extends 없음, engine=cad-viewer), `cad-section`(extends cad-3d-viewer + section-plane), `cad-exploded`(+ exploded-view), `cad-measure`(+ measure).

### 18.4 self-contained vs 대용량 바이너리 — 번들 모드
- **인라인 모드(기본, 작은 모델 ≲ 2–3MB)**: GLB를 base64로 HTML에 인라인 → 단일 `.html` 유지. xy와 동일 경로.
- **번들 모드(큰 모델)**: HTML(뷰어) + `.glb`(데이터)를 **분리 파일**로 산출 → report-write `html_embed`의 **멀티파일 번들**(`bundle_id` + `entry_path`)로 게시. (design C/§15 미해결 R5에서 식별된 경로 — cad가 이걸 강제하므로 v0.8 table/cad 전에 report-write 번들 계약 확정 필요.)
- three.js(~600KB)/model-viewer(~1MB+) 같은 vendor는 패밀리 의존 번들로 인라인하되, base64 페이로드 상한을 `graph_lint_output`이 경고(예: >8MB warn).

### 18.5 MVP가 지금 보장해야 하는 것 (3D를 위한 선투자, 단 과하지 않게)
1. catalog `engine` 필드 + builder가 `data/engines/<engine>/`에서 읽기 (하드코딩 `xy-core` 금지).
2. boot.js의 `window.GraphEngines[family]` 레지스트리 디스패치.
3. recipe.normalize가 `{engine, assets, options, provided_fields}`를 반환 (xy는 `assets.series`).
4. `assets` 직렬화 seam (인라인 JSON now; base64/번들 hook은 인터페이스만 예약).
> 이 4가지 외에 cad 전용 코드는 지금 만들지 않는다(YAGNI). 패밀리 추가가 "엔진 디렉터리 + recipe + plugin 추가"로 떨어지게만 한다.

---

## 19. 결과 도시 표준 & 설계-state 표 (도메인 확장)

스마트폰 시뮬/MCAE/ECAE/system·통계·DOE 전 분야 결과 도시 방법을 망라 규격화한 **표준**과, "설계 state별 점검/비교표" 메타-아티팩트 설계를 별도 문서로 분리했다. 본 §은 그 권위 출처를 가리키고, 아키텍처에 미치는 영향만 못박는다.

- **`docs/RESULT-VIZ-STANDARD.md`** — 결과 도시 표준(canonical 엔진패밀리 SSOT + ~200 타입 레지스트리 + 도입 로드맵). 도메인별 전체 상세는 `docs/viz-catalogs/{mcae,ecae,system,general}.md`(원본), 완결성 비평은 `docs/viz-catalogs/_critique.md`.
- **`docs/DESIGN-STATE-TABLE.md`** — `review-matrix` 패밀리(셀=그래프/이미지/값/상태/텍스트, 비교·diff·검색·필터·freeze·구조화 조회·인라인 게시).

### 19.1 Canonical 엔진 패밀리 SSOT (이 8개가 유일 정식명 — §18의 ad-hoc 명칭을 대체)
`xy-core`(✅구현, 직교 2D, 전체 ~60%) · `field-core`(2D 스칼라/벡터장+이산 셀-매트릭스, **최우선 신규**) · `polar-core`(각-반경/삼각: 방사패턴/radar/gauge/Mohr/ternary) · `smith-core`(RF 임피던스/Nichols 곡선격자) · `raster-core`(eye-diagram 등 고밀도) · `cad3d-core`(=§18 cad-viewer 통합, three.js 3D+필드+STEP) · `flow-core`(Sankey/network/treemap) · `review-matrix`(설계-state 표 메타-아티팩트). 도입 순서·흡수 타입은 STANDARD §4.
> §18에서 쓴 mesh3d/field-2d/3d-core 등 별칭은 폐기. 패밀리 = `data/engines/<family>/` 디렉터리명 = catalog `engine` 값.

### 19.2 아키텍처 영향 (MVP 불변식에 추가 못박을 것)
1. **validate-v2 구조 게이트** — types.json `requires`(스칼라 dotted-path)로 못 잡는 것(배열 개수 `states≥2`, 참조 무결성 `baseline∈states`, 조건부 축 `axes.y2` 단위, 메시 자산 존재, 배열 임계)을 위해 `Recipe.structural_requires(payload)->missing[]` 훅 추가. `require_axes` 는 선언 시 y2/z 도 검사하도록 확장(현재 우축 단위 누락이 게이트 통과하는 버그).
2. **report-write 게시 = 인라인 단일 .html 만** — `html_embed` 는 단일 self-contained 파일만 받음(번들 위젯 없음, 검증됨). "html+assets/ 번들" 경로 폐기. 큰 이미지는 base64 인라인+다운스케일 또는 썸네일+모달. `data:` URI 는 lint 통과.
3. **메타-아티팩트 합성** — `review-matrix` 가 셀에서 다른 타입 recipe를 재사용해 그래프를 재마운트(동일 패밀리=inline, 이종=srcdoc fragment[+HTML 속성 이스케이프], print/대량=썸네일). `boot.js`/`builder`/`serialize`/`catalog` 무변경.
4. **로드맵 갱신** — §12.2 의 16행 로드맵은 STANDARD §3 레지스트리로 대체·확장(도메인 타입 ~200). 빌드 순서는 STANDARD §4(xy-core 채우기 → field-core → cad3d-core → polar/smith → raster → review-matrix 병행 → flow-core).

---

### 부록 — 참조 파일 (절대경로)
- `d:\report-skill\docs\SKILL-RECIPE.md` — 4표면/3-view/_INPUT_HINTS/버전정책/§9·§10 함정 (사상 원본)
- `d:\graph-skill\samples\stress-strain\index.html` — Case1 품질 기준 + base64→srcdoc 고정엔진 패턴 (L293/300-309). CASE1_B64 디코드 불필요 — feature set은 프롬프트 명세(L163–199)로 완결.
- `d:\report-skill\src\report_skill\adapters\html_embed.py` — file_id 필수·raw HTML 거부·fallback=rich_text (산출물 self-contained 강제 근거)
- `d:\report-skill\src\report_skill\upload_chain.py` — local_path→file_id 자동 (graph-skill↔report-write 결합점)
- `d:\report-skill\src\report_skill\data\widgets.snapshot.json` — html_embed content_schema, height_px 60–4000, hash `8733ed67ec759a04`
