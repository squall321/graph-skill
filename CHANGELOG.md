# Changelog

## 0.53.0 (2026-06-16) — 정형 그래프 마무리 2종 (gap 분석 전량 완료)
- **마지막 정형 그래프 2종** — 둘 다 xy-core 재사용:
  `milestone-trend`(MTA — 보고시점별 예상완료일 추이, 완료선 y=x·달성 마커) ·
  `reliability-demo-sprt`(PRST — accept/continue/reject 경계 + 시험경로, MIL-HDBK-781).
- `postprocess/domain_t6.py`(Wald SPRT 경계·판정) — self-check.
- 규모: **167 → 169 타입**. 검증: pytest 470 · node 21 · Chromium 169/169 클린.
- **갭 분석 미구현 그래프 타입 48종 전량 완료** (T1 11 + T2 26 + T3 11). 잔여는 웹 인프라뿐
  (S3/CDN·OAuth·cad3d 워커격리 · report-archive file_id 풀 연동).

## 0.52.0 (2026-06-15) — 엔진 오버레이 정형 그래프 5종 (gap 완결)
- **field-core 범용 오버레이 레이어** 신설 — `overlays:{curves, markers, polygons}`(데이터좌표)를
  히트맵/컨투어 위에 렌더(`_drawOverlays`). field-core 0.5.1.
- **신규 타입 5종**:
  `eye-mask-compliance`(마스크 폴리곤 + point-in-polygon 히트카운트·합부) ·
  `efficiency-map`(등효율 컨투어 + 외곽선·동작점 오버레이) ·
  `rpm-order-map`(스펙트로그램 + 오더선 f=order×rpm/60 오버레이) ·
  `psychrometric-chart`(ASHRAE 포화선·RH선·상태점, 순수 레시피) ·
  `distribution-fit-compare`(분포별 확률지 + 선형적합 R² 랭킹, 4패널).
- `postprocess/domain_t5.py`(point-in-polygon·아이마스크 히트·습공기·inverse-normal·확률지
  선형화) — 전부 self-check.
- 규모: **162 → 167 타입**. 검증: pytest 465 · node 21 · Chromium 167/167 클린.
- **갭 분석 미구현 그래프 타입 사실상 완결** — 잔여: milestone-trend(날짜축)·reliability-demo-sprt,
  그리고 웹 인프라(S3/CDN·OAuth·cad3d 워커격리).

## 0.51.0 (2026-06-15) — T2 표준 보고 그래프 배치 C (9종)
- **T2 정형 그래프 9종 신설** — 전부 기존 엔진/플러그인 재사용(엔진 신규작업 0):
  `risk-matrix`(P·I zone·완화 전후) · `friction-wear-curve`(정상상태·런인) ·
  `fan-pump-operating-point`(성능×시스템 곡선 교점) · `tq-pinch-diagram`(복합곡선·ΔTmin) ·
  `jr-curve`(블런팅·멱법칙, ASTM E1820) · `load-transient-response`(2패널·오버슈트/회복) ·
  `mott-schottky-cv`(1/C² 선형적합·N_D·V_fb) · `compressor-map`(속도선·서지·운전점) ·
  `harmonic-spur-table`(n×f0 피크 자동검출·dBc).
- `postprocess/domain_t4.py` 신설(곡선교점·J-R 멱법칙·과도 메트릭·Mott-Schottky·고조파 피크·
  복합곡선) — 전부 self-check.
- 규모: **153 → 162 타입**. 검증: pytest 458 · node 21 · Chromium 162/162 클린.
- 잔여: 엔진작업 5종(eye-mask·efficiency-map·rpm-order·psychrometric·distribution-fit) ·
  milestone-trend(날짜축)·reliability-demo-sprt · 웹 인프라.

## 0.50.0 (2026-06-15) — T2 표준 보고 그래프 배치 B (10종)
- **T2 정형 그래프 10종 신설** — 전부 기존 엔진/플러그인 재사용(엔진 신규작업 0):
  `phase-noise`(L(f)·RMS 지터 적분) · `soa-chart`(안전동작영역 log-log·동작점 합부) ·
  `uncertainty-budget-chart`(GUM 기여율·확장불확도) · `tolerance-stackup-chart`(WC/RSS) ·
  `evm-s-curve`(PV/EV/AC·SPI/CPI/EAC) · `burndown-burnup`(이상선·범위변경) ·
  `dqdv-curve`(미분용량 ICA·스무딩) · `torque-angle-curve`(항복점 자동검출) ·
  `creep-curve`(최소 크리프율·단계 음영) · `equivalence-tost-plot`(CI⊂등가한계 판정).
- `postprocess/domain_t3.py` 신설(위상지터 적분·SOA 경계/포함·GUM 버짓·공차 WC/RSS·EVM·
  리스크 zone·dQ/dV·토크 항복·최소 크리프율) — 전부 self-check.
- 규모: **143 → 153 타입**. 검증: pytest 451 · node 21 · Chromium 153/153 클린.
- 잔여: T2 엔진작업 ~5종(eye-mask·efficiency-map·rpm-order·psychrometric·distribution-fit) ·
  T3 일부(~7종) · 웹 인프라.

## 0.49.0 (2026-06-15) — T2 표준 보고 그래프 배치 A (11종)
- **T2 정형 그래프 11종 신설** — 전부 기존 엔진/플러그인 재사용(엔진 신규작업 0):
  `ewma-chart`(시변 한계) · `oc-curve`(이항 Pa·AQL/LTPD) · `roc-pr-curve`(AUC·Youden) ·
  `bathtub-curve`(Weibull hazard 3구간) · `crow-amsaa-growth`(β MLE·MTBF log-log) ·
  `mohr-circle`(응력원·등축) · `boiling-curve`(CHF 자동) · `gate-charge-curve`(Miller plateau) ·
  `immunity-level-profile`(IEC 판정 색마커) · `resource-histogram`(누적막대·용량 초과) ·
  `raci-matrix`(R/A/C/I, A 1명 검증).
- `postprocess/domain_t2.py` 신설(EWMA·이항 OC·ROC/PR AUC·Weibull hazard·Crow-AMSAA MLE·
  Mohr 원·CHF·정상상태·Miller plateau) — 전부 self-check.
- 규모: **132 → 143 타입**. 검증: pytest 442 · node 21 · Chromium 143/143 클린.
- 잔여: T2 배치 B(~15종, 일부 field-core/plugin 작업) · T3(~11종) · 웹 인프라.

## 0.48.0 (2026-06-14) — T1 표준 보고 그래프 10종 (P2 완결)
- **T1 정형 그래프 10종 신설** — 전부 기존 엔진/플러그인 재사용(threshold-lines·region-shading·
  named-markers·waterfall), 판정(교차 보간·마진·룩업)이 붙는 정형 그림:
  `loop-gain-margin`(PM/GM 자동) · `conducted-emission`(QP/AVG 이중한계, CISPR32) ·
  `tdr-impedance-profile`(회랑 일탈) · `jitter-bathtub`(dual-Dirac BER, erfc) ·
  `battery-cycle-fade`(EOL 교차) · `cc-cv-charge-profile`(전환점 음영) ·
  `thermal-resistance-stack`(ΔT=P·R 사다리, Tj margin) · `hardness-profile`(CHD 교점) ·
  `xbar-r-chart`(A2/D3/D4 2단 패널) · `fmea-worksheet`(RPN/AIAG-VDA AP 색배지).
- `postprocess/domain_t1.py` 신설(안정도 마진·dual-Dirac·열저항 스택·X̄-R 상수·RPN/AP) — 전부 self-check.
- **엔진 픽스**: `_hasAnyData`가 플러그인 데이터(waterfall/stream/box/violin)를 세도록 — 캐리어만 있는
  차트의 '표시할 데이터 없음' 오워터마크 제거(기존 waterfall-chart도 개선). xy-core 1.8.4.
- 규모: **122 → 132 타입**. 검증: pytest 433 · node 21 · Chromium 132/132 클린.
- P2 미구현 T1 10종 **전부 완료** — 잔여는 웹 인프라(S3/CDN/OAuth/cad3d 워커격리)뿐.

## 0.47.0 (2026-06-14) — 개선 로드맵 P0/P1 + P2 일부
- **서버 P0 경화**(신규 server 코드 자체 결함 수정): async 핸들러가 동기 render를
  `run_in_threadpool`로 오프로드(이벤트루프 블로킹 제거) · ArtifactStore LRU 상한
  (`GRAPH_STORE_MAX_ITEMS`, OOM 차단) · 스트리밍 body-size 강제(chunked 우회 차단) ·
  토큰버킷 eviction(키회전 DoS 차단) · API key 상수시간 비교(`hmac`). 동시성/eviction/
  스트리밍 가드 테스트 추가.
- **정확성 게이트(NEVER-invent)**: stress-linearization·multitrack-stack 단위 게이트 ·
  SRS Nyquist/half_sine 경계 가드 · SPC 관리한계 within-σ(MR̄/d2, 시프트 은폐 제거) ·
  self-check 3종(linear_fit·gamut·band_edges) · **신선도 바인딩 게이트**(엔진 코드해시↔
  ENGINE_VERSION 매니페스트 — '코드 변경 후 버전 미범프'를 구조적으로 거부).
- **신규 타입 3종**: `grouped-bar`/`stacked-bar`(xy-core 엔진에 grouped 오프셋·stacked
  baseline+autoscale 추가, 막대+선 콤보 우측축 지원) · `bland-altman`(측정-CAE 일치도,
  차이-평균 + bias·±1.96SD LoA). types_find 랭킹 강화(synonyms·양방향 부분일치).
- **DX**: top-level export(`from graph_skill import types_find, render_payload`) ·
  needs_input `answer_template`(자동화 클라이언트 기계가독) · SKILL.md Flow D(웹/MCP 서빙) ·
  embed_stored `local_path` 모드(웹 산출물→report-write html_embed 브릿지).
- 규모: 122 타입 / 8 엔진. 검증: pytest 430+ · node 21 · Chromium 122/122 클린.
- 잔여(P2): T1 미구현 10종(loop-gain-margin·tdr·jitter-bathtub·battery-cycle 등) ·
  웹 인프라(S3/CDN/OAuth/cad3d 워커격리) — docs/_analysis_status.md 참조.

## 0.46.0 (2026-06-14) — 웹/원격 MCP 서빙
- **`graph_skill.server`** 신규 패키지 — 단일 ASGI 앱(`graph-skill-web`)으로 세 표면을 한 배포에:
  REST `/v1/*`(render/lint/embed + 순수도구 passthrough) · `/artifacts/<sha256>`(self-contained
  HTML 서빙, immutable 캐시 + CSP) · `/mcp`(원격 MCP, **Streamable HTTP**; stdio MCP는 그대로 유지).
  코어(`tools.DISPATCH`)·엔진 자산·결정성·self-contained 게이트는 무수정 재사용.
- **콘텐츠주소 아티팩트 스토어** — 산출이 바이트결정적이라 `sha256(html)`이 자연 캐시키(동일 입력 dedupe·
  CDN 친화). 무상태 `render_to_store`(디스크 안 씀)로 멀티테넌트 안전, 경로 traversal 가드.
- **보안 미들웨어**(env-gated, pure ASGI) — API key 인증 / 본문크기 / 토큰버킷 레이트리밋. `needs_input`
  게이트는 422로 명시 반환(서버가 NEVER-invent를 절대 우회 안 함).
- **점검 후속 수정**: `ingest_s2p` DISPATCH 누락 수정(+ TOOLS↔DISPATCH 정합 가드 테스트); `image.ref`
  외부 URL self-contained 우회 갭 차단 — lint를 #graph-config 데이터 채널까지 확장 + review-matrix/
  flow-core 엔진 런타임에서 외부 ref blank(방어 2중). `scale:"log"` 죽은 키→`log:true`(stream/overview/
  playback 5종 로그축 복구). 엔진 버전 범프(xy 1.8.2·cad3d 0.6.1·flow 0.6.2·review-matrix 0.7.1).
- 검증: pytest 409 · node 21/21 · Chromium 119/119 클린.

## 0.45.0 (2026-06-12)
- 확장 7종: cie-chromaticity(공식 CIE 018:2019 궤적 내장) · octave-band(IEC 61260) ·
  tornado-chart · motor-tn-curve · vswr-curve(S11→VSWR) · dma-curve(Tg 자동) ·
  **test-report**(시험성적서 컴포지트, 멀티엔진 1파일)
- `ingest_s2p` 도구: Touchstone .s2p → smith/VSWR/S21 직결
- GitHub Actions CI(.github/workflows/ci.yml): pytest+node+갤러리 신선도 게이트+실브라우저 스모크
- P2 잔여: 3D 컨투어 unlit 정점색(변형/모드는 음영 유지), xy 제목 말줄임(컨트롤바 겹침 해소),
  네트워크 반발력 그리드 근사(n>150)

## 0.40.0 ~ 0.44.0 (2026-06-10 ~ 06-11) — 요약
- 0.44.0: 구조·열·측정 8종(mesh-convergence GCI · stress-linearization · hysteresis ·
  thermal-response τ · nusselt · frf-coherence · allan-deviation · calibration) — 수치 자가검증 포함
- 0.43.0: E-CAE 8종(SRS Smallwood · EMI CISPR · Zth JESD51-14 · PDN target · 온도사이클 ·
  spec-margin(gauge-core margin kind) · derating · battery)
- 0.42.x: 실전 게시 검증(report-archive #54, sandbox iframe에서 Ctrl+휠 줌·WebGL orbit 픽셀 검증)
  + LLM 블라인드 사용성 테스트 10/10 → hint 자체완결화/escape hatch 반영 + git 버전관리 시작
- 0.40.0~0.41.0: UX 감사(멀티에이전트 73건→로드맵 30건) **P0/P1/P2 전체 구현** —
  임베드 휠 스크롤 통과(Ctrl+휠), 터치/핀치/키보드, a11y(aria/focus-visible/reduced-motion),
  LTTB 갭/log 수리(2.5ms/frame), 도움말 오버레이, 에러 표준화, 테마 postMessage,
  taxonomy 19카테고리, 일정/계획 5종(gantt·timeline·calendar-heatmap·task-table·work-plan)

## 0.2.0 ~ 0.39.0 (요약)
- 엔진 패밀리 8개 구축(xy/field/polar/smith/review-matrix/flow/gauge/cad3d + linked-view 플러그인 버스)
- 그래프 타입 1 → 96 (공학 2D·신뢰성·제어·신호·3D WebGL·표·관계흐름·계층·KPI·재생 애니)
- 검증 4층 체계: 결정성/lint + node 헤드리스 + 실 Chromium 스모크 + 인터랙션 픽셀 검증


All notable changes to graph-skill. SemVer (0.x). Engine assets carry a separate
`ENGINE_VERSION` baked into every artifact.

## [0.10.0] — equipment raw post-processing (ingest / resample / smooth)
### Added
- **`postprocess/{ingest,resample,smoothing}.py`** (pure Python): CSV/TSV ingest (header +
  units row + delimiter auto, non-numeric→None); uniform-grid resample (linear interp) +
  `is_uniform` detection + decimate; moving-average + **Savitzky-Golay** (normal-equations).
- **Helper tools** `ingest_csv` / `resample` / `smooth` (return numeric, not HTML) on MCP +
  CLI — the LLM pre-processes raw scope/Instron data, then feeds it to `graph_render`.
- Verified: ingest/resample/SG numeric correctness (SG noise RMSE 0.3→0.08) + e2e
  (ingest→resample→smooth→render) + pytest (88 passed).

## [0.9.0] — polar-core family (radiation pattern / radar)
### Added
- **New engine family `polar-core`** (engine 0.1.0) — angle/radius Canvas engine: polar grid
  (radius rings + angle spokes), series as polar polylines (θ=0 at top, clockwise), radar
  fill, hover probe (θ, r), legend, dark mode, PNG. Types `polar-plot`, `radar-chart`
  (categories→spokes, closed polygons, rmax scale), `rf-radiation-pattern` (Gain[dBi] preset).
- **validate preview made shape-agnostic** (handles theta/r and field series, not just x/y).
- Verified: render/lint + gates (radius/labels/series) + headless (engine renders, _pt maps,
  0 console errors) + pytest (79 passed).

## [0.8.0] — dual-axis + bode (secondary y-axis)
### Added
- **xy-core secondary y-axis**: series with `axis:"right"` get an independent right-hand
  scale (own data range, right ticks/labels/title via `axes.y2`); left/right domains are
  computed separately; hover/snap use the correct per-series scale. Guarded by `_hasRight`
  so single-axis rendering is byte-unchanged in behaviour.
- Types `dual-axis` (generic left/right, e.g. power↔temperature) and `bode` (log-frequency
  Magnitude[dB] left + Phase[deg] right, from `freqs/mag/phase`). Verified: 2nd-order system
  resonance peak ≈14 dB; right-axis scaling; gates; headless (right axis active, log-x,
  0 console errors) + pytest (72 passed).

## [0.7.0] — statistical & bar types (histogram / bar / box / error-bar)
### Added
- **xy-core engine** gained bar rendering (`style:"bar"` with baseline 0), a categorical x-axis
  (`axes.x.categories`), and a domain-only `style:"none"` series (for box-plot extents).
- **`stats` postprocess** — histogram binning (sqrt rule) + Tukey quartiles/whiskers/outliers.
- **box-plot / error-bars plugins** + types `histogram`, `bar-plot`, `box-plot`, `error-bar`
  (each with its own structural gate: histogram→values+axis.x, bar→categories+axis.y,
  box→groups+axis.y). Covers DOE / Monte-Carlo / reliability / margin reporting.
- Verified: stats correctness + gates + headless runtime (bars/categorical/box/error-bar
  render, 0 console errors) + pytest (65 passed).

## [0.6.0] — filter-tuner (interactive FFT filter)
### Added
- **`filter-tuner` type** (xy-core) — completes the "watch the FFT, drag the cutoff, see the
  time signal change" loop in a single self-contained HTML (no server). A `filter-panel`
  plugin renders a cutoff slider + type select + time/freq toggle; the filtered waveform and
  spectrum update live via a client-side radix-2 FFT, with a cutoff line drawn on the spectrum.
- **`spectral.fft_filter` / `amp_spectrum` / `_ifft`** — pure-Python FFT-domain filter
  (low/high/band, raised-cosine transition) used for the initial paint, matching the JS used
  for live updates. Verified: lowpass fc=80 keeps 30 Hz, removes 180 Hz; highpass inverts.
- Verified: filter correctness + fs gate + headless runtime (boot, cutoff change re-filters
  live, time/freq toggle, 0 console errors) + pytest (54 passed).

## [0.5.0] — fft-spectrum (time ↔ frequency toggle)
### Added
- **`fft-spectrum` type** (xy-core) — the headline "FFT toggle": a time-domain signal in,
  one-sided amplitude spectrum out, with a control-bar button that switches the chart between
  time and frequency at runtime (peak markers auto in freq).
- **`postprocess/spectral.py`** — pure-Python FFT (iterative radix-2, zero-pad to 2ⁿ, Hann
  window, one-sided amplitude) + peak finder. No numpy. Verified: peaks at 49.8 & 120.1 Hz
  for a 50 + 120 Hz signal.
- **`domain-toggle` plugin** — swaps series + axes (+ peak markers) between the pre-computed
  time and frequency domains; requires `params.fs` (gate asks if missing).
- Verified: FFT numeric correctness + fs gate + headless runtime (boots in freq at Nyquist,
  toggles to time/seconds and back, 0 console errors) + pytest (47 passed).

## [0.4.0] — field-core family (2D contour/heatmap, phase 3)
### Added
- **New engine family `field-core`** (engine 0.1.0) — 2D scalar field z=f(x,y): colormap
  raster (offscreen + drawImage, zoom-aware), **marching-squares iso-contours**, a colorbar
  legend, **probe-pick** (hover → x,y,z in HUD), zoom/pan/box-zoom, colormap cycle
  (viridis/turbo/coolwarm/gray) + reverse, dark mode, responsive, PNG export.
- Types: `contour-plot`, `heatmap-grid` (color-only), `scalar-field-2d`, `mcae-stress-contour`
  (turbo preset). Input `field={x[],y[],z[][]}` + axes + z{label,unit}.
- **field recipe + structural gate**: asks for the z quantity/unit (colorbar meaning) and
  validates grid rectangularity (z is ny×nx); z sanitized to float|None (null = transparent).
- Verified: Python build/lint + z-meta & dimension gates + headless runtime (boot, 25×25 grid,
  bilinear probe, colormap re-rasterize, zoom clamp, 0 console errors) + pytest (40 passed).
  Implements `docs/RESULT-VIZ-STANDARD.md` §3.2 (field-core, highest-ROI new family).

## [0.3.0] — review-matrix family (design-state checklist/comparison, phase 2)
### Added
- **New engine family `review-matrix`** (engine 0.1.0) — a DOM-grid meta-artifact, not a
  chart. Renders states × items; cells are number / status(pass/fail/warn) / text / image
  (base64-inline) / **graph** (re-mounts a real graph-skill engine in the cell). Auto:
  search/filter, group collapse, sticky label column, diff(▲▼) vs baseline, spec badges,
  cell modal (full-graph re-mount / image lightbox), export-source JSON.
- **Multi-engine bundling** in the builder (`_collect_engines`) — a matrix HTML inlines its
  own engine + every engine/plugin its graph cells need (e.g. xy-core), deduped. Backward
  compatible (single-engine artifacts unchanged). Added `graphconfig.graph_config` helper.
- **validate-v2 structural gate** — `Recipe.structural_requires(payload)` for non-scalar
  checks; catalog `require_series` flag. Enforced: `items≥1`, `states≥2` (compare),
  `baseline ∈ states`. require_axes/require_series default off for matrix types.
- Types: `review-matrix`, `design-state-compare` (≥2 states + baseline, diff/spec badges,
  `overlay_states`), `single-state-checklist`. Tool surface accepts `states/items/spec/meta`.
- Verified: Python multi-engine bundle + structural gates + headless runtime (matrix boots,
  3 graph cells re-mount xy-core, modal full re-mount, 0 console errors) + pytest (31 passed).
  Implements `docs/DESIGN-STATE-TABLE.md` (inline-only publish, overlay, structured query).

## [0.2.0] — xy-core plugin layer (result-viz standard, phase 1)
### Added
- **Plugin composition seam** in `xy-core` (engine 1.1.0): `view.core` / `view.pluginConfig` /
  per-core `_pstate`, so shared singleton plugins carry per-graph config + state.
- **5 reusable plugins** (`data/engines/xy-core/plugins/`): `threshold-lines`,
  `region-shading`, `named-markers`, `live-tangent` (hover slope, recipe-relabelled:
  Et[GPa]/stiffness[N/mm]/CTE…), `regression-fit` (LSQ line + R² + y=x identity).
- **`postprocess/units.py`** — σ=F/A0, ε=ΔL/L0, eng→true (pure Python, guarded).
- **3 new types** via `extends` + plugin composition: `stress-strain` (requires A0/L0 →
  gate, auto UTS/Fracture markers + Et tangent, eng/true), `force-displacement`
  (stiffness tangent), `correlation-scatter` (regression + identity + R²).
- Verified: Python pipeline + headless plugin runtime (hover→Et/stiffness, regression draw,
  0 console errors) + pytest (23 passed). See `tests/{smoke_phase1.py,node_phase1.mjs,test_phase1.py}`.
  Implements `docs/RESULT-VIZ-STANDARD.md` §3.1 (xy-core domain types, first slice).

## [0.1.0] — base-xy MVP
### Added
- **Engine family architecture** (engine-agnostic builder/catalog/validate/shell). `xy-core`
  is the first family; `data/engines/<family>/` layout reserves space for future families
  (e.g. `cad-viewer`). See docs/SKILL-PLAN.md §18.
- **`xy-core` Canvas 2D engine** (`data/engines/xy-core/engine.js`, ENGINE_VERSION 1.0.0):
  multi-series, color-blind-safe palette, per-series hover tracking + crosshair + unified
  tooltip + HUD, click lock, wheel zoom (cursor-centered; Shift=x, Alt/Ctrl=y), drag pan,
  box zoom, double-click reset, log/linear toggle (x/y, non-positive guard), nice ticks,
  legend toggle/isolate, dark mode (auto/light/dark), responsive (ResizeObserver + DPR),
  PNG/CSV/config export, monotone-cubic/straight/step curves, gap handling.
- **Skill surface**: `tools.py` (shared) behind MCP (`mcp_server.py`) and CLI (`cli.py`).
  Tools: `graph_types_list`, `graph_schema_get`, `graph_validate_inputs`, `graph_render`,
  `graph_lint_output`, `graph_embed_block`.
- **Completeness gate** (`validate.py`): required axes + per-type `requires[]` → `missing[]`
  + questions; render is blocked (`MissingFieldsError` / `needs_input`) until resolved.
- **Self-contained guarantee**: deterministic, LF-only, zero external resources; static lint
  gate (`serialize.lint_self_contained`).
- `base-xy` recipe + catalog entry; SKILL.md; README; pytest suite + dependency-free smokes
  (`tests/smoke_build.py`, `tests/smoke_tools.py`) + headless engine execution
  (`tests/node_render.mjs`).
