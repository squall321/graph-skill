# graph-skill 확장 실행 로드맵 (Expansion Execution Roadmap)

> 이 문서는 **새 계획이 아니라 실행 계획**이다. 무엇을 만들지(=타입 레지스트리)는 이미
> [`RESULT-VIZ-STANDARD.md`](RESULT-VIZ-STANDARD.md)가, 3D 패밀리 골격은
> [`SKILL-PLAN.md` §18](SKILL-PLAN.md)이 SSOT로 예약해 두었다. 여기서는 그 예약을
> **착수 가능한 배치(G→N)**, **cad3d-core(3D) 구현 설계**, **헤드리스 검증 전략**으로 운영화한다.
>
> 근거: 6개 공학 도메인 시각화 인벤토리(106개 후보, 미커버 ~102, high 70) + 3D 웹렌더·메쉬
> 인제스트·WebGL 검증 기술조사를 멀티에이전트로 수행 → 현재 26타입과 dedup하여 종합한 결과.
> (조사일 2026-06-08, 10개 에이전트.)

---

## 0. 현재 상태 (baseline)

- **4 엔진패밀리 / 26 타입 / 0.11.0.** xy-core(Canvas2D 16) · field-core(2D필드 4) · polar-core(극좌표 3) · review-matrix(DOM표 3).
- 불변식: **엔진=버전관리된 번들 자산**(LLM은 데이터·축·타입만), **결정적 빌드**, **외부 의존 0 self-contained**, **report-write `html_embed` 인라인 게시**.
- 위 불변식이 확장의 제약이자 설계 기준이다. 특히 3D는 "브라우저에 CAD 커널을 내려보낼 수 없다 → 서버측 테셀레이션 후 메시만 인라인" 이라는 결론을 강제한다.

## 1. 배치 로드맵 한눈에

| 배치 | 제목 | 핵심 | 신규 엔진 | 노력 | 의존 |
|---|---|---|---|---|---|
| **G** | DOE/통계/과도 2D 빠른 승부 | xy-core 재사용, 신규 엔진 0 | — | M | (현재) |
| **H** | 경량 plugin 필요 2D | prob-axis / unit-circle / quiver plugin | — | L | G |
| **I** | smith-core 신규 패밀리 | RF 임피던스(Smith) | smith-core | M | H |
| **J** | cad3d-core 뷰어 골격 | three.js vendor + 엔진 팩토리 + GLB 인라인 | **cad3d-core** | XL | (I와 병렬 가능) |
| **K** | 3D 형상 뷰어 + probe | STL/OBJ/GLB 뷰, Raycaster probe | cad3d-core | L | J |
| **L** | 3D FE 필드 결과 | 응력/온도/안전계수 컨투어 컬러맵(VTU) | cad3d-core | L | K |
| **M** | 3D 단면/변형/등치면/모드 | clip plane·deform·isosurface·mode-anim | cad3d-core | XL | L |
| **N** | STEP/IGES 서버 테셀레이션 | 격리 컨테이너, 선택 의존 | (postprocess) | L | M |

원칙: **2D 빠른 승부(G–I)로 즉시 가치 산출**하면서, 위험·노력이 큰 **cad3d-core(J–N)는 골격(J)을 일찍 병렬 착수**해 리스크를 선분산한다.

### 검증 깊이 업그레이드 (2026-06-09) — "안 죽는다 → 제대로 그려진다"

이전까지 모든 "렌더" 검증은 헤드리스 DOM/Canvas **스텁**(메서드 no-op)이라 throw만 잡고 시각 결과는 못 봤다. 이를 보강:

- **실 브라우저 시각 스모크** — `tests/playwright_smoke.py`(전 58종) + `tests/test_visual.py`(pytest, 6 엔진패밀리 대표 15 + **WebGL cad3d/smith**). 각 아티팩트를 headless Chromium에 로드해 **booted·콘솔에러 0·캔버스 실제 드로잉(non-blank data-URL)** 확인. **58/58 클린 렌더** — cad3d(WebGL)·smith 실 픽셀 최초 검증.
- **엣지 강건성** — `tests/test_robustness.py` 9케이스: NaN/gap·단일점·미정렬/중복x·로그축0·all-null·히스토그램NaN·컨투어gap·20k 대용량·gap하 결정성.
- 전체 **pytest 258** (브라우저 없으면 visual은 skip), 6 엔진패밀리 / 58 타입 / 0.23.0.
- **남은 깊이 TODO**: >5k점 LTTB 다운샘플(성능) · 픽셀 골든(ΔE) · 신규 plugin 인터랙션(parcoord brushing, SPLOM 연동, spectrogram probe) · 게시 대규모 검증(서버 복구 시) · RESULT-VIZ-STANDARD 드리프트 정리.

### 진행 상황 (2026-06-08)

- **배치 G — ✅ 완료** (0.12.0). 7종(main-effects/interaction/transient-time-history/convergence-residual/cfd-line-extract-compare/nonlinear-load-displacement/s-n-fatigue-curve) 추가, 신규 엔진/plugin 0. 4-레이어 검증 통과(smoke/node/pytest 136/CLI), 갤러리 33종 반영.
- **배치 H — 🟡 무(無)신규-plugin 부분집합 완료** (0.13.0). 5종(process-capability-hist/paris-crack-growth/campbell-diagram/kaplan-meier-survival/mac-matrix-heatmap) 추가, 신규 엔진/plugin 0. `postprocess/stats.capability` + 신규 `reliability.py`(KM·median-rank). 4-레이어 검증(pytest 159), 갤러리 38종.
  - **H2 — ✅ 제어/신뢰성 3종 추가** (0.14.0). nyquist-plot · root-locus(신규 **equalAspect 엔진옵션**[opt-in, idempotent] + **unit-circle plugin**) · weibull-prob-paper(reliability.weibull_fit, reuse만). node에서 equalAspect 등비율 수치 검증 + 회귀 0(pytest 171). 갤러리 41종.
  - **H3 — ✅ CFD/피로 필드 2종 추가** (0.15.0). vector-quiver-2d(field-core에 `_drawArrows`+`arrowsOnly` 추가, opt-in·무회귀) · rainflow-cycle-histogram(신규 `fatigue.py` ASTM E1049 + field-core 히트맵). pytest 182, 갤러리 43종.
  - **H4 — ✅ residual-diagnostic-panel 추가** (0.16.0). 회귀 진단 4종(Q-Q/Resid-Fitted/Scale-Location/Resid-Leverage)을 review-matrix 그래프셀로 임베드(셀=실제 인터랙티브 base-xy, 엔진 변경 0). node에서 review-matrix+xy-core 동시부팅·4셀 마운트 검증, pytest 188. 갤러리 44종.
  - **남은 H:** polar-2d-radiation-cut(polar-core 빔폭 마커) · streamline(quiver 확장 RK4).
- **배치 J(K/L 일부) — ✅ cad3d-core WebGL 뷰어 MVP** (0.17.0). 새 엔진패밀리 `cad3d-core`(three.js r128 vendor, sha256 핀, `assets.read_engine_js` vendor 인라인) + 2종: `cad-3d-viewer`(STL/OBJ/GLB·primitive·vertices/faces → 인라인 GLB, orbit·**단면(clip plane)**·와이어·테마·PNG) · `mesh-result-3d`(정점 필드 컬러 + 컬러바). 아티팩트 ~780KB, **lint self-contained·external_urls 0**(three.js의 w3 네임스페이스/문서URL은 src/href가 아니라 통과). 검증 3층: Python 파이프라인+lint(✓) · node 번들무결성(THREE/로더/엔진등록 ✓) · 브라우저 런타임(Playwright tier — 사용자 확인). pytest 195. 갤러리 46종.
  - **남은 J(M/N):** 변형형상·등치면·모드 애니(morphTarget) · STEP/IGES 서버 테셀레이션(격리 cadquery/pythonocc) · Playwright 픽셀 tier.
- **배치 J — 🟡 데이터 파이프라인 기반(완료, 위 MVP의 토대)**. `postprocess/field_to_color.py`(무의존 LUT) + `mesh_ingest.py`(trimesh: STL/OBJ/GLB→표면스키마+정점컬러+GLB) + `decimate.py`(QEM) 구축·검증(`test_cad3d.py` 10 케이스: LUT 결정성/box 스키마·bbox/GLB 결정성·왕복/QEM 5120→500). 선택 의존 `[cad3d] = trimesh, fast-simplification` 등록.
  - **남은 J (다음 단계, 브라우저/three.js 필요):** ① three.js 서브셋 vendor + sha256 핀 ② `data/engines/cad3d-core/engine.js`(scene·camera·OrbitControls·GLB·colorbar) + boot/catalog 배선 + `cad-3d-viewer` 타입 ③ mock-GL + Playwright 검증 tier. (data pipeline은 이미 결정적으로 검증됨 → 위험 큰 부분만 남음.)

---

## 2. 2D/2.5D 빠른 승부 (배치 G · H · I)

현재 엔진 재사용으로 신규 엔진코드 없이(또는 경량 plugin 1개로) 추가 가능한 미커버 양식. 우선순위는 "보고/문제확인 빈도 × 구현 저비용".

### 2.1 배치 G — 신규 엔진 0, base-xy/기존 plugin 재사용 (effort M)

| 타입 | 재사용 | 비고 |
|---|---|---|
| `main-effects-plot` | base-xy 멀티시리즈 + threshold-lines(그랜드평균) | DOE 1차 분석. recipe가 인자×수준 평균 변환 |
| `interaction-plot` | base-xy(인자2=시리즈, 인자1=x) + 범례 isolate | DOE 교호작용(선 교차) |
| `transient-time-history` | base-xy 멀티채널 + named-markers(피크) + threshold-lines | 충격/지진/crash 과도응답. 피크검출 `postprocess/stats.py` |
| `convergence-residual-plot` | base-xy(yLog) + threshold-lines(수렴 임계) | CFD/FEA 솔버 잔차 모니터 |
| `cfd-line-extract-compare` | base-xy 멀티케이스 + region-shading + error-bars | 해석-실험 라인 비교·격자독립성. Cp/Cf/속도프로파일 |
| `nonlinear-load-displacement` | force-displacement + live-tangent + named-markers + region-shading | F-d/pushover. 항복/좌굴/극한 마커 + 에너지면적 |
| `s-n-fatigue-curve` | base-xy(log-log) + threshold-lines(피로한도) + named-markers + region-shading | Wöhler. 여러 도메인 high 중복 |

### 2.2 배치 H — 경량 신규 plugin/postprocess 필요 (effort L)

| 타입 | 신규 요소 | 재사용 |
|---|---|---|
| `weibull-prob-paper` | **prob-axis plugin**(inverse-CDF 좌표) + `postprocess/reliability.py`(median-rank, MLE) | base-xy + regression-fit + named-markers(B10/B50) + region-shading |
| `kaplan-meier-survival` | `reliability.py`(KM estimator) | curve:'step' + region-shading + named-markers(censoring) |
| `process-capability-hist` | `stats.py` 확장(Cp·Cpk·PPM·정규fit) | histogram + threshold-lines(USL/LSL/T) |
| `nyquist-plot` | **unit-circle/equal-aspect plugin** | base-xy(parametric) + named-markers((-1,0)). frf/EIS-nyquist 흡수 |
| `root-locus` | (정적) — | base-xy parametric + named-markers(pole×/zero○) + region-shading(LHP) |
| `paris-crack-growth` | — | base-xy(log-log) + regression-fit(C,m) + threshold-lines(ΔKth/KIC) |
| `campbell-diagram` | recipe가 엔진오더 직선 생성 | base-xy 멀티시리즈 + named-markers(교차점) |
| `vector-quiver-2d` | **quiver-arrows plugin**(화살표+밀도) | field-core 격자/colormap/probe. 후속 streamline(RK4) 합류 |
| `rainflow-cycle-histogram` | `postprocess/fatigue.py`(rainflow) | field-core heatmap-grid(mean×range) + 1D 토글 |
| `mac-matrix-heatmap` | — | field-core heatmap-grid(N×N) + 0.9 임계. 셀클릭→3D 모드뷰는 cad3d 후 review-matrix 임베드 |
| `residual-diagnostic-panel` | panel-grid(소) 또는 review-matrix 그래프셀 임베드 | qq-plot + correlation-scatter |

### 2.3 배치 I — smith-core 신규 경량 패밀리 (effort M)

- `smith-chart-sparam` (S11 반사계수 궤적). 등저항/등리액턴스 원격자는 직교/극좌표로 재현 불가 → **Möbius 좌표변환의 경량 신규 패밀리 `smith-core`**. polar-core의 캔버스 셸·줌팬·HUD 패턴을 복제, 좌표변환만 신규. `boot.js` dispatch는 family-agnostic이라 무변경. 후속 `nichols-chart`·`bat-eis-nyquist` 흡수 여지.

---

## 3. cad3d-core (3D) 엔진 패밀리 — 구현 설계

> **명명 정합:** RESULT-VIZ-STANDARD §3.6의 정식 명칭 **`cad3d-core`** 를 쓴다(별칭 `mesh3d`/`cad3d`/`cad-viewer` 폐기). SKILL-PLAN §18의 `cad-viewer` 스케치를 이 설계로 구체화·대체한다.

사용자 핵심 요구: **3D CAD·STL·gmsh FE mesh를 보고/문제확인용으로 "돌려보며" 단면·변형·등치면·모드까지 확인**.

### 3.1 렌더 기술 — three.js 서브셋 vendor 번들

- **채택: three.js(UMD 인라인).** core + OrbitControls + GLTFLoader만 **커스텀 서브셋 빌드(~250–300KB)** 로 full UMD(~600KB)의 절반 이하. `data/vendor/three.min.js` 에 **sha256 핀**(manifest 패턴 그대로) → 결정적 빌드. `window.THREE` 전역 → `boot.js`의 `GraphEngines['cad3d-core']` 팩토리가 래핑(현 family-agnostic dispatch 무변경).
- **기각:** 커스텀 미니렌더러/regl(구현·검증비용 과도), `<model-viewer>`(clipping·probe 불가, customElements 전역등록이 review-matrix 셀 재마운트와 충돌, 번들 더 큼).
- 근거: orbit/pan/zoom·다중조명·`WebGLRenderer.clippingPlanes`(단면)·`Raycaster`(probe)·`morphTarget`(변형/모드)이 전부 three.js first-class API → **검증 대상이 "우리 자작 렌더러"가 아니라 "데이터·어댑터"로 한정**된다.

### 3.2 입력 파이프라인 (Python postprocess) — 단일 GLB로 수렴

모든 입력 경로를 **표면삼각형 + 정점컬러 단일 스키마 `{vertices:Float32, indices:Uint32, vertexColors:Uint8}` → 최종 GLB**로 통일.

- **MVP (`pip install meshio trimesh pyvista`):**
  - STL(bin/ascii) · OBJ · GLB → `trimesh` 단일 진입점 (`postprocess/mesh_ingest.py`)
  - VTK `.vtu/.vtp` → `meshio`+`pyvista` 체인: read → `extract_surface` → `warp_by_vector`(변위·배율) → `cell_data_to_point_data` 필드 보간 (`postprocess/vtk_field.py`)
  - Abaqus `.inp` · Nastran `.bdf` → `meshio`(지오메트리 전용)
- **후순위 / 선택 의존(격리 컨테이너):**
  - **STEP/IGES** → `cadquery`(OCCT, pip 개선됨) 또는 `pythonocc-core`(conda) 격리 tessellator → BRepMesh(deflection 0.1) → GLB. **STEP 단위계(mm/inch)는 `requires` 게이트로 질문**(브라우저는 CAD 못 읽음 → 서버 테셀레이션 필수).
  - gmsh `.msh` → gmsh API(80MB) 또는 `meshio` fallback(Physical Group 손실 허용)
  - Abaqus `.odb` → 외부 `odb→vtu` 변환 스크립트 별도 제공

**필요 postprocess 어댑터:** `mesh_ingest.py` · `vtk_field.py` · `field_to_color.py`(matplotlib 무의존 viridis/turbo/coolwarm 256×3 uint8 LUT, field-core CMAPS와 동일 색공간) · `decimate.py`(QEM + bbox 정규화 양자화) · `cad.py`(후순위 격리) · `modal.py`(모드별 morphTarget 트랙 + 고유진동수).

### 3.3 인라인 임베드 & 크기예산

report-write `html_embed`는 **인라인 base64 단일 파일만** 허용. 파이프라인 고정 순서:

```
read → surface_extract → warp(disp,factor) → QEM decimation(face 타겟)
     → field_to_vertex_color → trimesh.export(GLB) → base64 data URI inline
```

- three.js vendor(~300KB)는 sha256 핀 번들로 인라인. **크기예산:** `graph_lint_output`이 GLB base64 **>8MB warn**(SKILL-PLAN §18.4). face 타겟 데스크탑 50k / 모바일 10k, 좌표 **int16 양자화**(또는 5자리 round)로 30–40% 절감 → 총 HTML 5–6MB 이하 유지.
- **컬러 매핑은 반드시 decimation 후**(보간오차 배가 방지). 대형 모델(>500k node)은 aggressive decimation 또는 §18.4 번들 모드(HTML+.glb 분리; 단 report-write 게시는 인라인만).

### 3.4 인터랙션 (= plugin 번들로 박제; LLM은 colormap·scale·zdomain·제목만)

- orbit / pan / zoom(OrbitControls) + 더블클릭 리셋
- **단면 클립(section-plane plugin):** clipping plane 법선·오프셋 슬라이더 + capping(절단면 채움)
- **변형 배율(deform plugin):** scale factor 슬라이더(morphTarget/warp) + undeformed 반투명 오버레이 토글
- **등치면(isosurface plugin):** 노달 스칼라 marching-cubes 임계값 슬라이더 실시간 재생성
- **probe-pick:** Raycaster 호버/클릭 → 노드 좌표·필드값 HUD
- colorbar + zdomain 수동범위(항복강도 기준) + colormap 전환(field-core LUT 재사용)
- **모드 애니메이션(mode plugin):** 모드 드롭다운 + 재생/정지/속도 + 위상 사이클(morphTarget per mode)
- 와이어프레임/솔리드/반투명, 파트 isolate/hide, PNG 내보내기, 다크모드, console.error 0

### 3.5 헤드리스 검증 — 3분층 (결정론은 데이터층, 픽셀은 허용오차층)

현재 Canvas2D는 node DOM스텁으로 검증 중. 3D는 GL 컨텍스트가 필요하므로:

1. **수학/데이터 골든 (`test_cad3d_math.py`, 결정론 100%):** `decimate.py`/`cad.py`의 vertex count·bbox·단위(mm/inch) 환산·법선 정규화 골든, 카메라 `makePerspective/lookAt` 해석 대조, section-plane `ax+by+cz+d=0` face-count 예측. (순수 Python+JS)
2. **mock-GL (`test_cad3d_mock_gl.py`, 빌드 의존성 0):** node에서 mock WebGL context 주입 → 팩토리 부팅 → `drawElements≥1`·`bufferData` byte size(입력 vertex 대비)·MVP mat4 uniform·clipping uniform 어서션. self-contained 불변식(config 직렬화/engine sha256/plugin 목록) 보호 — 현 `test_phase` 골든 패턴 그대로.
3. **Playwright headless Chromium (`e2e/test_cad3d_playwright.py`, 허용오차):** three.js 실부팅 → canvas non-black pixel·console.error 0·orbit 응답·픽셀 해시 ΔE<2%. GL 픽셀은 드라이버 의존이라 byte-identical 불가 → **결정론은 1·2층, 픽셀은 3층만**.
   - `headless-gl`(네이티브 addon)은 self-contained 불변식과 상충 → Linux CI Mesa 한정 선택적 보류.

### 3.6 리스크 & 완화

| 리스크 | 완화 |
|---|---|
| 번들 크기(three.js+GLB가 8MB warn 근접) | 서브셋 빌드 + QEM decimation + int16 양자화; 대형은 LOD/번들 모드 |
| 결정론(GL 픽셀 드라이버 의존) | 결정론을 GLB 페이로드+config 직렬화 층에만; 픽셀은 허용오차 3층. lib 버전 핀 + 골든 재생성 정책 |
| STEP/IGES 의존성(OCCT/conda CI 병목) | MVP 제외, 격리 컨테이너로 GLB만 산출해 합류(브라우저에 CAD 커널 불가) |
| 검증 표면 급증 | three.js 채택으로 검증대상=데이터·어댑터 한정; mock-canvas 부팅 공식 패턴 |
| iframe/srcdoc 내 WebGL 컨텍스트 실패 | model-viewer 회피, three.js 직접 부팅으로 review-matrix 셀 재마운트 안전 |
| 엔진=고정자산 원칙 | 모든 3D 인터랙션을 plugin 번들로 박제; LLM은 colormap·scale·zdomain·라벨만 |

### 3.7 cad3d-core 배치 분해 (J → N)

- **J (XL) 골격:** vendor three 서브셋(sha256) + `GraphEngines['cad3d-core']` 팩토리(씬·카메라·조명·OrbitControls·GLB 로드·colorbar·다크·PNG) + `mesh_ingest.py`/`field_to_color.py`/`decimate.py` + 크기예산 lint + 3분층 하네스 스캐폴딩.
- **K (L) 형상 뷰어:** `cad-3d-viewer`(STL/OBJ/GLB) · `mesh-geometry-3d`. Raycaster probe, 와이어/솔리드/반투명, isolate/hide. Abaqus inp/Nastran bdf 지오메트리 입력.
- **L (L) FE 필드:** `mesh-result-3d`(von Mises/온도/FoS 컨투어) — VTU → 표면추출+노달필드 → 정점컬러 GLB. colorbar + zdomain + colormap 전환. (= mcae-stress-contour의 3D 짝.)
- **M (XL) 인터랙션:** `cad-section`(clip+capping) · `mesh-deformed-3d`(deform+undeformed 오버레이) · `isosurface-3d` · `mode-shape-3d`(모드 애니, `modal.py`). 각 인터랙션 = plugin 번들.
- **N (L) STEP/IGES:** `postprocess/cad.py`(격리 cadquery/pythonocc → GLB), 단위계 requires 게이트, gmsh fallback. CI는 격리 이미지로만.

---

## 4. 즉시 착수 (top priorities)

1. **배치 G 착수** — main-effects / interaction / transient-time-history / convergence-residual / cfd-line-compare (+ nonlinear-load-disp, s-n-curve). 전부 base-xy+기존 plugin, types.json 블록 + recipe + fixture/golden/node-smoke만. **가장 빠른 가치.**
2. **s-n-fatigue-curve + nonlinear-load-displacement** — 여러 도메인 high 중복, force-displacement/threshold/markers/region 확장으로 저비용.
3. **weibull-prob-paper + kaplan-meier + process-capability-hist** — 신뢰성/SPC 핵심. `reliability.py`(MLE·KM) + `stats.py`(Cp/Cpk) + prob-axis plugin 1개.
4. **cad3d-core 골격(J) 선행 준비** — three.js 서브셋 vendor + sha256 핀 + 팩토리 + 3분층 하네스 스캐폴딩. XL이라 2D와 **병렬로 일찍** 시작해 리스크 선분산.
5. **vector-quiver-2d / rainflow / mac-matrix** — field-core(heatmap·colormap·probe) 재사용 + quiver plugin 하나로 CFD/피로/모달검증 커버리지 확장.

---

## 부록 A — 도메인 커버리지 (조사 요약)

6개 도메인 × 12–18개 = **106개 후보**, 현재 26과 dedup 전 미커버 ~102, high 70. synth가 20개 신규 2D + cad3d-core(3D 5+α 타입)로 압축.

| 도메인 | 후보 | 미커버 | high | 대표 미커버 |
|---|---:|---:|---:|---|
| structural-fea | 18 | 17 | 9 | 3D 변형형상·모드애니·단면슬라이스·S-N·FoS맵·crash에너지 |
| cfd-thermal | 18 | 17 | 12 | 유선·벡터장·수렴잔차·라인추출비교·3D온도컨투어 |
| em-rf-signal | 18 | 16 | 11 | Smith·S-파라미터·EMI마스크·3D방사구·표면전류 |
| quality-reliability-doe | 18 | 18 | 14 | Weibull·KM생존·Cp/Cpk·main-effects·interaction·RSM |
| materials-multiphysics | 17 | 17 | 13 | ternary·연성-취성·Paris균열·연성커플드필드 |
| systems-controls-dynamics | 17 | 17 | 11 | Nyquist·Nichols·Campbell·근궤적·FRF·모드형상 |

전체 인벤토리·기술조사 원본은 워크플로 산출물(run `wf_857b8e6b-6b7`)에 보존.

---

## 부록 B — 기존 문서와의 관계

- **무엇을(타입)**: `RESULT-VIZ-STANDARD.md` (§3 패밀리/타입 레지스트리, §3.6 cad3d-core) = SSOT.
- **왜·아키텍처**: `SKILL-PLAN.md` (§18 엔진패밀리 일반화 & 3D 확장, §18.3 cad-viewer 스케치, §18.4 번들/크기예산).
- **어떻게·언제(실행)**: 이 문서(배치 G–N, cad3d-core 구현/검증, 우선순위).
- 본 문서가 §18.3 `cad-viewer` 스케치를 `cad3d-core` 구현 설계로 구체화·대체한다(명칭 정합).
