# 결과 도시(Result-Visualization) 표준 — graph-skill

스마트폰 시뮬레이션 / MCAE / ECAE / system·multiphysics / 통계·DOE 의 **모든 결과 도시 방법**을 graph-skill 아키텍처(engine family + catalog block + plugin 합성 + validate 게이트)에 규격화한 표준이다.

- 권위 출처(SSOT): 본 문서 §0 패밀리 사전 + §3 타입 레지스트리.
- 도메인별 **전체 상세 카탈로그(모든 행·컬럼)** 는 부록 `docs/viz-catalogs/{mcae,ecae,system,general}.md` (각 도메인 전문가 에이전트 원본), 완결성 비평은 `docs/viz-catalogs/_critique.md`.
- 본 문서는 그 4개 도메인 카탈로그를 **canonical 이름으로 통일·중복제거**하고, 비평가가 찾은 결함(게시 경로·명명 충돌·validate 모델·누락 타입)을 반영한 종합본이다.
- "설계 state 점검/비교표" 메타-아티팩트는 별도 문서 `docs/DESIGN-STATE-TABLE.md`.

---

## 0. Canonical 엔진 패밀리 사전 (SSOT) — 이름 통일

도메인 카탈로그들이 같은 패밀리를 2~5개 이름으로 불렀다(3D=5개, field=3개, matrix=2개념 충돌). **아래 8개가 유일한 정식 명칭이다.** 다른 모든 별칭은 폐기.

| 패밀리 | 상태 | 무엇을 렌더 | 좌표/렌더 모델 | 흡수 별칭(폐기) | 우선순위 |
|---|---|---|---|---|---|
| **xy-core** | ✅ 구현됨(v0.1) | 직교 2D: line/scatter/step/area/bar/통계분포/dual-axis/multitrack/FFT/Bode/Nichols/parallel-coords/SPLOM/gantt/bullet/prob-paper/chromaticity | data→pixel 선형·로그(직교) | — | (기존) |
| **field-core** | 신규 ①최우선 | 2D 스칼라/벡터 장 + 이산 셀-매트릭스: heatmap·contour·density·hexbin·scalar/vector field·streamline·STFT 스펙트로그램·BER 등고·상관/MAC/rainflow cell-matrix·모든 CAE 필드맵(응력/온도/SAR/IR-drop/휘도) | (x,y)→z 그리드 보간 + ImageData 래스터 + marching-squares 등치선 | field, field-2d, field-core, matrix(셀히트맵), heatmap-2d, raster(스펙트로그램) | ★★★★★ |
| **polar-core** | 신규 ③ | 비직교 각-반경/삼각 좌표: polar plot·방사패턴 2D·radar/star·gauge·directivity·시야각·Mohr 원·ternary·Nyquist(옵션) | scalePolar(θ,r)→px, 삼각 무게중심 | polar, radar-base, gauge-base, chromaticity(일부) | ★★★ |
| **smith-core** | 신규 | RF 임피던스/비직교 곡선격자: Smith·Nichols(등M/N원)·loadpull | 등R/등X 원형 격자, Γ↔Z 변환 | smith, smith-base | ★★ (RF 필수) |
| **raster-core** | 신규 | 고밀도 persistence 누적: eye-diagram·density-persistence | UI-fold + 다중 trace 밀도 히트 | eye-base, eye-diagram, signal-eye, raster-core, density-persistence | ★★ (SI 시그니처) |
| **cad3d-core** | 신규 ②(=§18 cad-viewer 통합) | WebGL/three.js 3D: surface/scatter/isosurface/volume·메시 결과 컬러맵·mode-shape-3d·3D 방사·RSM surface·STEP→GLB CAD 뷰어·단면 | 3D 카메라/조명/메시, three.js | mesh3d, cad3d, cad3d-core, 3d-core, surface-3d, cad-viewer, sphere-3d, volume-3d | ★★★★ |
| **flow-core** | 신규 | 노드-링크/계층: Sankey·chord·network·treemap·sunburst·icicle·RC 열저항망 | 레이아웃 알고리즘(force/squarify/sankey)→좌표 | flow-core, graph-node | ★★ |
| **review-matrix** | 신규(메타) | 셀이 다른 graph 아티팩트·이미지·값·상태·텍스트가 되는 **설계 state 점검/비교표** (차트 아님, DOM 격자 합성기) | DOM 격자 + 셀에 엔진 재마운트 | matrix-grid (← 이름 통일: field-core 의 `matrix`(셀히트맵)와 개념 분리) | ★★★ |

> **명명 규칙(이름 충돌 영구 방지):**
> - 패밀리 = 위 8개 정식명만. `data/engines/<family>/` 디렉터리명과 catalog `engine` 필드값이 곧 이 이름.
> - type-id = kebab-case. 도메인 모호 시 **도메인 네임스페이스 접두**: `mcae-*`, `ecae-*`, `sys-*`(system), `stat-*`(통계/DOE). 도메인 불문 보편 타입은 무접두(`stress-strain`, `fft-spectrum`, `bode`, `histogram`).
> - 같은 개념 1 type-id: `rf-radiation-pattern`(← antenna-pattern 폐기), `eye-diagram`(← si/rf-eye-diagram 통합), `spectrogram`(← waterfall-spectrogram/stft/acoustic-spectrogram 통합), `correlation-scatter`/`correlation-heatmap`(분리 유지), `pareto`(단일), `bode`(단일, 도메인은 옵션).

---

## 1. 규격화 규칙 — 모든 타입 = catalog 한 블록

새 결과 도시 1개 = `data/catalog/types.json` 블록 1개 (+ 필요 시 plugin 1파일, + 신규 패밀리면 `data/engines/<family>/` 자산). class 상속 없음(plugin 합성). 블록 형태:

```jsonc
"<type-id>": {
  "engine": "<canonical family>",          // 위 8개 중 하나
  "extends": "<parent type-id|null>",       // plugins/requires/options 누적
  "plugins": ["<feature plugin>", ...],     // 도메인 의미 오버레이만
  "requires": [ {field, type, unit, why, ask}, ... ],  // 스칼라 dotted-path
  "structural_requires": ["<validator id>"],// ← validate-v2 (아래 §1.2)
  "post": ["<postprocess fn>"],             // Python 사전계산 (단위환산/FFT/필터/통계)
  "options_defaults": { ... },
  "height_px": <int>
}
```

### 1.1 base 엔진 자동 인터랙션 (재확인 — 도메인 plugin은 "의미 오버레이"만 얹는다)
`xy-core` 가 설정 없이 제공: 멀티시리즈·호버 트래킹·크로스헤어·통합 툴팁·HUD·줌/팬/박스줌·로그토글·범례 isolate·다크모드·반응형·PNG/CSV export. → 도메인 plugin은 한계선/마스크/마커/피팅/구간음영/이중축 같은 **공학 의미**만 추가한다(중복 구현 금지).

### 1.2 validate-v2 — 구조적 게이트 (비평가 결함 #3 반영)
현재 `validate.check` 는 `requires[]` 의 dotted-path 단일 스칼라 + `series`/`axes` 특수로직만 본다. 아래는 그 모델로 **못 잡는 것** → recipe에 `structural_requires` 훅 추가로 해결:

```python
# recipes/<type>.py — 선택적 구조 검증 훅 (validate.check가 스칼라 pass 후 호출)
class Recipe:
    def structural_requires(self, payload) -> list[dict]:
        """배열길이/참조무결성/조건부축/자산존재/배열임계 등 비-스칼라 게이트."""
        return []
```
필수 적용 케이스(비평가 지적):
- **개수 조건**: `design-state-compare` 의 `states ≥ 2`; multitrack 의 `series ≥ 2`.
- **참조 무결성**: diff 의 `baseline ∈ states[].id`.
- **조건부 축**: dual-axis 의 `axes.y2.{label,unit}` (현 `require_axes` 가 y2 미검사 → 우축 단위 누락이 통과하는 버그. y2/z 선언 시 함께 검사하도록 확장).
- **자산 존재**: `cad3d-*` 의 메시(STL/GLB) 경로 + 단위계. field 의 grid 규칙성(정·비정렬)·보간 필요 여부.
- **배열 임계**: 색맵 iso-level 배열, BER level 배열 (단일 스칼라 아님).
- **canonical 파라미터 경로 통일**: `fs` → 항상 `params.fs`; `A0/L0` → `params.A0/params.L0`; spec → `spec.{min,max,target,tol}` (매트릭스는 `spec.targets`/`spec.error_pct` 등 타입별 분기). 한 곳(types.json requires.field)에 고정.

### 1.3 후처리(post) 경계
무거운/정확성 민감 계산은 Python 사전계산: `spectral.*`(FFT/PSD/STFT/SRS/TF), `filters.*`(Butterworth/filtfilt/CFC), `fatigue.*`(rainflow/Basquin/Coffin-Manson/Miner/Darveaux), `stats.*`(histogram/quartiles/regression/Weibull/Cpk/pareto), `field.*`(interp2d/isocontour/kde2d/streamlines), `doe.*`(main_effects/rsm_fit/pareto_rank), `units.*`(σ=F/A0·eng↔true·flexural·CTE). 슬라이더 실시간만 JS(`numeric/fft.js`) "preview" 라벨.

---

## 2. report-write 게시 제약 (비평가 결함 #1 — 검증됨)

**`html_embed` 는 단일 self-contained HTML 만 받는다(단일 블록 replace, 번들 없음).** `image`/`attachment` 만 다중 `file_id` append 가능.

| 결론 | 의미 |
|---|---|
| 게시 가능한 유일 형태 | 외부참조 0인 **단일 `.html`** (graph_lint_output 통과). |
| 번들 모드(html + assets/ 디렉터리) | **report-write에 존재하지 않음** → 폐기. 큰 이미지/대량 셀은 **base64 인라인(필요 시 다운스케일) 또는 썸네일+모달**로 단일 파일에 욱여넣어야 게시됨. |
| `data:` URI | `lint_self_contained` 의 `src=//`/`href=//` 패턴에 안 걸림 → 인라인 이미지는 게이트 통과(self-contained). |
| height_px | 60–4000 clamp. 대형 매트릭스는 행수기반 산출 후 clamp; 초과 시 내부 스크롤. |
| srcdoc(이종 패밀리 셀) | 추가 시 **HTML 속성 이스케이프**(`&`→`&amp;`,`"`→`&quot;`) 필요 — `safe_js_literal`(JS 리터럴용)로 못 덮음. 또한 srcdoc 내부는 `<html>` 없는 **fragment** 여야 `single_root` lint 안 깨짐. (현재는 xy-core 단일 패밀리라 inline 재마운트만 쓰므로 미사용 — field/polar 추가 시 적용.) |

---

## 3. 타입 레지스트리 (canonical, 패밀리별 — 중복제거)

도메인 태그: `MC`=MCAE, `EC`=ECAE, `SY`=system/multiphysics, `ST`=통계/DOE. 전체 컬럼(요구배경·plugin·post·난이도)은 부록 카탈로그 참조.

### 3.1 xy-core (직교 2D — 전체의 ~60%, 신규 패밀리 불필요. catalog 블록+plugin만)

**보편/통계 (ST·전도메인)**
`base-xy` · `scatter-xy` · `step-plot` · `area-plot` · `stacked-area` · `bar-plot` · `grouped-bar` · `stacked-bar` · `dual-axis` · `multitrack-stack`(N-패널 공유x, **신규-비평#4**) · `error-bar` · `error-band` · `histogram` · `pdf-plot` · `cdf-plot` · `ecdf-plot` · `box-plot` · `violin-plot` · `bee-swarm` · `ridgeline`(**신규**) · `pareto` · `waterfall-chart` · `candlestick` · `regression-fit` · `qq-plot` · `spc-control-chart` · `parallel-coordinates`(parcoord plugin) · `scatter-matrix`(SPLOM) · `prob-paper`(Weibull/normal, prob-axis plugin) · `chromaticity`(CIE gamut, equal-aspect+locus plugin)

**MCAE (MC)**
`stress-strain`(A0,L0) · `force-displacement` · `stiffness-curve` · `3point-bend` · `bending-stiffness` · `load-path-bar` · `drop-accel-time`(fs) · `drop-stress-time` · `drop-energy-time` · `drop-velocity-time` · `srs-spectrum`(fs,Q) · `hic-indicator` · `cumulative-energy-bar` · `frf-bode` · `frf-nyquist` · `campbell-diagram` · `psd-random`(fs) · `sine-sweep` · `transmissibility` · `modal-bar` · `s-n-curve`(R,runout) · `e-n-curve` · `goodman-haigh` · `damage-accumulation` · `hinge-life-cycle` · `hinge-torque-cycle`(hysteresis) · `fatigue-knockdown` · `temp-transient` · `thermal-deformation`(CTE) · `cte-mismatch` · `thermal-cycle-hysteresis` · `creep-strain-time` · `creep-rate-stress`(Norton) · `stress-relaxation` · `solder-creep-fatigue`(Darveaux) · `delamination-energy`(Gc) · `peel-force-curve` · `adhesion-bar` · `contact-pressure-line` · `buckling-load` · `load-deflection-postbuckling` · `gasket-pressure-curve` · `indentation-curve`(Oliver-Pharr) · `acoustic-frf`(A-weight) · `mohr-circle`(**신규-비평#4**, →polar-core)

**ECAE (EC)**
`si-sparam-mag` · `si-sparam-phase` · `si-insertion-loss-budget` · `si-tdr-impedance` · `si-tdt-step` · `si-ber-bathtub` · `si-jitter-decomp` · `si-crosstalk` · `si-pulse-response` · `si-channel-impulse` · `si-eq-fom` · `si-mode-conversion` · `si-skew-budget` · `digital-timing-waveform`(**신규-비평**, 레인 렌더) · `pi-pdn-impedance`(target-Z) · `pi-decap-effect` · `pi-voltage-droop` · `pi-ripple-spectrum` · `rf-s11-return-loss` · `rf-vswr` · `rf-gain-efficiency-freq` · `rf-beam-scan` · `rf-eirp-ccdf` · `rf-equivalent-circuit` · `rf-isolation-coupling` · `rf-ecc` · `rf-group-delay-flatness` · `rf-noise-figure` · `emi-emission-spectrum`(limit mask) · `emi-shielding-effectiveness` · `emi-conducted-emission` · `emi-tvs-esd-clamp` · `emi-radiated-immunity` · `bat-voltage-capacity`(C-rate) · `bat-voltage-time` · `bat-capacity-fade`(EOL%) · `bat-dqdv` · `bat-dvdq` · `bat-eis-nyquist`(equal-aspect) · `bat-eis-bode` · `bat-rate-ragone` · `bat-ocv-soc` · `bat-thermal-runaway` · `bat-swelling` · `et-junction-temp-transient`(Tjmax) · `et-zth-transient` · `et-structure-function` · `et-throttle-frequency` · `disp-gamma-curve` · `disp-vt-curve` · `disp-pixel-transient` · `disp-flicker-fft` · `disp-power-apl` · `touch-snr-freq` · `touch-mutual-cap-freq` · `sensor-haptic-response` · `sensor-mems-bode` · `sensor-piezo-charge` · `sensor-hall-field` · `ckt-bode`(=bode) · `ckt-nyquist` · `ckt-pole-zero` · `ckt-rootlocus`(**신규**) · `ckt-transient` · `ckt-dc-sweep-iv` · `ckt-monte-carlo-hist` · `ckt-corner-spread` · `ckt-em-weibull` · `wire-rlc-freq` · `nichols-chart`(**신규**, →smith-core)

**System/통계/DOE (SY·ST)**
`thermal-rise-curve` · `thermal-budget-bar` · `acoustic-spl-freq` · `acoustic-thd-freq` · `acoustic-impedance` · `display-reflectance-spectrum` · `display-gamma-curve` · `camera-mtf-freq` · `camera-mtf-field` · `camera-aberration-ray` · `camera-relative-illum` · `rf-return-loss`/`rf-vswr`/`rf-efficiency-freq`(EC와 공유) · `wireless-throughput-range` · `wireless-tput-rssi` · `rf-ber-curve` · `power-profile-time` · `power-battery-discharge` · `power-soc-time` · `power-thermal-coupled` · `power-efficiency-load` · `power-charge-curve` · `corr-overlay` · `corr-scatter-r2` · `corr-error-bar` · `corr-residual` · `corr-bland-altman` · `corr-frf-overlay` · `cdf-survival-overlay`(**신규**) · `rel-weibull-cdf` · `rel-bathtub-hazard` · `rel-survival-km` · `rel-accel-life`(Arrhenius) · `rel-pareto-failure` · `doe-pareto-effects` · `doe-main-effects` · `doe-interaction` · `doe-tornado` · `doe-montecarlo-hist` · `doe-montecarlo-cdf` · `doe-tolerance-hist`(Cpk) · `opt-convergence` · `opt-pareto-front-2d` · `opt-objective-tradeoff` · `opt-doe-sampling` · `margin-bullet` · `margin-waterfall` · `tornado-waterfall-bridge`(**신규**) · `gantt-chart` · `timeline-events` · `cumulative-flow-burndown`(**신규**) · `roc-pr-curve`(**신규 ML**) · `kpi-tile`

### 3.2 field-core (2D 스칼라/벡터 장 + 이산 셀-매트릭스) — 신규 ①최우선
`heatmap-grid` · `correlation-heatmap`(ST) · `contour-plot` · `density-2d` · `hexbin-plot` · `scalar-field-2d` · `vector-field-quiver` · `streamline-plot` · `spectrogram`(STFT, fs·window·hop — MC/SY/EC 공유) · `calendar-heatmap`(**신규**)
- **MC**: `mcae-stress-contour`(von Mises map) · `mcae-warpage-map` · `mcae-deformation-contour` · `mcae-safety-factor-contour` · `mcae-temp-contour` · `mcae-heatflux-field`(벡터) · `mcae-contact-pressure-map` · `mcae-gap-contour` · `mcae-indentation-map` · `mcae-mode-shape-2d` · `mcae-drop-contour-time`(time-slider) · `mcae-fatigue-damage-map`
- **EC**: `pi-ir-drop-map` · `pi-current-density-map`(벡터) · `rf-sar-map` · `emi-near-field-map`(벡터) · `et-chip-temp-contour` · `et-power-map` · `et-thermal-coupling-matrix` · `disp-luminance-map` · `disp-deltaE-map` · `touch-cap-heatmap` · `bat-soc-temp-map` · `si-eye-contour`(BER 등고)
- **이산 셀-매트릭스**(← 구 `matrix`): `rainflow-matrix`(MC) · `mac-matrix`(MC/SY) · `solder-damage-map`(MC) · `margin-spec-heat`(ST) · `confusion-matrix`(**신규 ML**)
- **SY/ST**: `doe-response-contour` · `corr-mac-matrix` · `geo-board-overlay`(보드 실루엣+필드, **신규 서브엔진**)
- 핵심: 2D 보간, colormap LUT, marching-squares 등치선, ImageData 래스터, 벡터 적분(RK4 streamline), probe-pick, iso-slider, time-slider, 단면추출(field→xy).

### 3.3 polar-core (비직교 각-반경/삼각) — 신규 ③
`polar-plot` · `radar-chart`(스펙 비교) · `star-glyph` · `gauge-chart`/`margin-gauge` · `margin-radar` · `ternary-plot`(조성) · `nyquist-plot`(옵션; xy-core+unit-circle도 가능) · `sunburst`(계층, 또는 flow-core) · `mohr-circle`(MC)
- **MC**: `mcae-drop-orientation-polar`(낙하자세 민감도)
- **EC/SY**: `rf-radiation-pattern`(2D, E/H-plane, HPBW) · `acoustic-directivity-polar` · `display-viewing-angle-polar` · `doe-sensitivity-spider`
- 핵심: scalePolar(θ,r), 등이득원, HPBW 마커, 반경 로그/선형, 0°기준 토글.

### 3.4 smith-core (RF 임피던스/곡선격자) — 신규
`rf-smith-chart`(Z0, S11 궤적) · `rf-loadpull-contour`(smith+field 합성) · `nichols-chart`(등M/N원) — 등R/등X 원형격자 공유.

### 3.5 raster-core (고밀도 persistence) — 신규
`eye-diagram`(UI, 비트열, mask — SI/RF 통합) · `density-persistence`(수만 trace 누적).

### 3.6 cad3d-core (3D, =cad-viewer 통합) — 신규 ②
`surface-3d` · `scatter-3d` · `isosurface-3d` · `volume-render-3d`(**신규**, ray-cast) · `mesh-result-3d`(필드 컬러맵+변형배율+단면)
- **MC**: `mcae-stress-contour-3d` · `mcae-temp-contour-3d` · `mcae-mode-shape-3d`(animate) · `mcae-buckling-mode-3d` · `mcae-life-contour-3d` · `mcae-solder-life-3d` · `mcae-acoustic-radiation-3d`
- **EC/SY**: `rf-radiation-pattern-3d`(방사구) · `rf-current-distribution-3d`(표면전류) · `display-color-volume-3d`(CIELAB) · `acoustic-waterfall-csd`
- **DOE**: `doe-response-surface-3d` · `opt-pareto-front-3d`
- **CAD**: `cad-viewer`(STEP→GLB) · `cad-section`(clipping+capping) · `cad-exploded` · `cad-measure` — §18 그대로, cad3d-core 안의 CAD-형상 용도.
- 백엔드 three.js(`data/vendor/`), STEP→GLB `postprocess/cad.py`, 번들 모드는 §18.4(단 report-write 게시는 §2대로 인라인 base64만).

### 3.7 flow-core (노드-링크/계층) — 신규
`sankey-diagram`(전력/에너지 수지) · `chord-diagram` · `network-graph` · `treemap` · `sunburst` · `icicle-plot` · `et-thermal-rc-network`(Foster/Cauer).

### 3.8 review-matrix (설계 state 점검/비교표 메타-아티팩트) — 신규
→ **전용 문서 `docs/DESIGN-STATE-TABLE.md`** (셀=그래프/이미지/값/상태/텍스트, 비교·diff·검색·필터·freeze·구조화 조회·인라인 게시).

---

## 4. 패밀리 도입 로드맵 (ROI 순)

| 단계 | 패밀리 | 흡수 타입 수(대략) | 근거 |
|---|---|---|---|
| 현재 | **xy-core** | ~120 (전체 60%+) | 구현됨. 통계군(box/violin/regression+CI/QQ/ECDF/multitrack)·MCAE 곡선·ECAE S-param/PDN/배터리·SY 상관/신뢰성/DOE 대부분이 plugin 합성만으로 즉시. **저비용 고효용 — 먼저 채운다.** |
| v0.6+ | **field-core** | ~35 | CAE 응력/온도/SAR/IR-drop 필드맵·spectrogram·eye-contour·correlation/MAC/rainflow. **최다 흡수, 최우선 신규.** SKILL-PLAN #13 contour가 씨앗. |
| v0.8+ | **cad3d-core**(=cad-viewer) | ~20 | 3D CAE 결과·반응표면·3D 방사·STEP 뷰어/단면. §18 통합. |
| v0.9+ | **polar-core + smith-core**("RF/극좌표 팩") | ~15 | 안테나 방사패턴·Smith·radar 스펙비교·Mohr·gauge. 직교 대체 불가. |
| v1.0+ | **raster-core** | ~3 | eye-diagram(SI 시그니처). |
| 병행 | **review-matrix** | 메타 | xy-core 위에 얹는 합성 표. xy-core MVP 직후 착수 가능(셀=xy-core 재마운트). |
| 후순위 | **flow-core** | ~7 | Sankey 전력수지·network 토폴로지. |

각 패밀리 추가 = `data/engines/<family>/{engine.js,engine.css,ENGINE_VERSION,plugins/*}` 신규 + `boot.js` 무변경(레지스트리 디스패치) + 해당 타입 catalog 블록 + recipe. **builder/serialize/catalog/validate(+structural 훅)/embed 는 패밀리 무관 — 그대로 재사용.**

---

## 5. 비평가가 추가한 누락 타입 (반영 완료, §3에 포함)
1순위: `multitrack-stack`(N-패널 공유x — 낙하/진동 실측 1순위) · `mohr-circle` · `nichols-chart` · review-matrix **그래프 셀 오버레이 비교**(같은 항목 v1/v2/v3을 한 셀에 겹침 — 단순 멀티시리즈 xy-core). 기타: `ridgeline` · `tornado-waterfall-bridge` · `digital-timing-waveform` · `confusion-matrix`/`roc-pr-curve` · `calendar-heatmap` · `cumulative-flow-burndown` · `cdf-survival-overlay` · `volume-render-3d` · `geo-board-overlay`.

미결정 경계(명시적 결정): `ternary`→polar-core. `nyquist`→xy-core(+unit-circle plugin) 기본, smith-core 격자 필요 시 이관. `waterfall-spectrum`→2.5D는 xy-core(slice-offset), 진짜 3D 회전은 cad3d-core(`-3d` 접미사로 분리). `sunburst`→flow-core(계층) 내부 polar 레이아웃.
