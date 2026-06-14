# graph-skill — 인터랙티브 단일 HTML 그래프 생성

데이터(시리즈/표/노드·엣지/필드/메시 + 축 의미·단위 + 그래프 타입 + 필요 시 배경 물리값)를 받아, **검증된 고정 렌더 엔진**으로 **외부 의존이 0인 단일 `.html`** 을 생성한다. 결과는 HTML 임베드형 사이트(report archive 등)에 그대로 올릴 수 있는 self-contained 아티팩트다.

핵심 원칙 한 줄: **너(LLM)는 그래프 엔진을 직접 코딩하지 않는다.** 엔진/인터랙션은 버전관리된 번들 자산이고, 너의 일은 (a) 데이터 수집, (b) 축·배경값 확인(부족하면 질문), (c) 타입 선택, (d) 렌더 호출이다. 이렇게 해야 "같은 입력이면 항상 동일한 고품질 인터랙션"이 보장된다.

엔진은 **9개 패밀리 / 119+ 타입**으로 일반화돼 있다(도구 사용법은 패밀리와 무관하게 동일):

| 패밀리 | 렌더 | 대표 타입 | 자동 인터랙션 |
|---|---|---|---|
| `xy-core` | Canvas 2D | base-xy 계열 73종(+playback/treemap 등 plugin) | 호버/줌/팬/박스줌/범례/내보내기 (아래) |
| `field-core` | Canvas 2D | contour/heatmap/spectrogram/confusion-matrix | probe·컬러바·줌 |
| `polar-core` | Canvas 2D | polar/radar/방사패턴/wind-rose | 각도 호버 |
| `smith-core` | Canvas 2D | smith-chart | 임피던스 호버 |
| `review-matrix` | DOM 표 | review-matrix/design-state-compare/kpi-scorecard/decision-matrix/multitrack/SPLOM | 검색·group 접기·셀 모달, 셀=값/상태/heat/bar/delta/그래프/이미지 |
| `flow-core` | DOM+SVG | flowchart(노드에 그래프·표·이미지 내장)/sankey/network/chord/sunburst | 팬/줌/노드 모달/드릴다운 |
| `gauge-core` | Canvas 2D | gauge/radial-progress/bullet-chart/stat-card | 로드 애니·재생·PNG |
| `cad3d-core` | WebGL(three.js) | cad-3d-viewer/mesh-result-3d/mesh-deformed-3d/mode-shape-3d/point-cloud-3d/surface-3d/isosurface-3d | orbit·단면·변형배율·모드재생 |
| (linked) | plugin 버스 | overview-detail(focus+context)/multitrack 공유 크로스헤어/SPLOM 연동 브러싱 | 패널 간 연동 |

**비-xy 패밀리의 입력 최상위 키는 타입마다 다르다**(nodes/edges/links/tree/frames/variables/matrix/points/z_grid/mesh/items/value …). **`graph_schema_get`의 hint가 SSOT** — 추측하지 말고 hint대로 구성하라.

---

## 자동으로 켜지는 것 (설정 불필요)
xy-core 계열 렌더 시 아래가 **별도 설정 없이** 전부 켜진다. 옵션으로 지정하려 하지 마라(무시되거나 역효과):
- 멀티 시리즈 + 색맹 안전 팔레트(Okabe-Ito), 시리즈별 호버 트래킹 + 크로스헤어 + 통합 툴팁 + 좌상단 HUD
- 클릭 lock/unlock, **Ctrl(⌘)+휠 줌**(커서 중심; +Shift=x만, +Alt=y만 — 일반 휠은 페이지 스크롤 통과), 드래그 팬, Shift+드래그 박스줌, 더블클릭 리셋
- x/y 로그·선형 토글(음수/0 데이터 가드), nice 눈금, 범례 토글/isolate(더블클릭)
- 다크모드(auto/light/dark 토글), 반응형(ResizeObserver + 레티나), PNG/CSV/config 내보내기, 4000점 초과 시 LTTB 자동 다운샘플
다른 패밀리도 위 표의 자동 인터랙션이 기본 탑재다.

---

## Tools

| 도구 | 용도 |
|---|---|
| `graph_types_list` | 타입을 **목적 카테고리(19)로 분류**한 인덱스 + 타입별 dims/use_when/입력형태/필수배경값. **항상 먼저.** `categories`를 먼저 훑어라. |
| `graph_find <query>` | 자연어 목적(예: "피로 수명", "3d 응력", "막대 경주")으로 후보 타입 즉시 검색(순위). 고르기 애매할 때. |
| `graph_schema_get <graph_type>` | 그 타입의 입력 스키마 + `requires[]` + plugin + **hint(입력 키 SSOT)**. |
| `graph_validate_inputs` | **렌더 전 필수 게이트.** `missing[]` + `questions[]` 반환. |
| `graph_render` | 검증된 입력 → 단일 self-contained `.html`. 배경값 부족하면 `needs_input` 반환(렌더 안 함). |
| `graph_lint_output <html_path>` | 산출 HTML 정적 검증(외부 URL 0 / 단일 루트). 게시 전 게이트. |
| `graph_embed_block <html_path>` | report-write `html_embed` draft 조각 생성. height 생략 시 **아티팩트의 권장 높이 자동 사용**. |
| `ingest_s2p <text>` | Touchstone .s2p → S-파라미터(freq/s11_db/s21_db/vswr/s11_gamma + usage 조각). |
| `ingest_csv <text>` | 장비 raw CSV/TSV 텍스트 → 수치 컬럼 파싱(헤더/단위행/구분자 자동). 컬럼을 골라 series 구성. |
| `resample` | 시계열을 균일 dt로 리샘플(선형보간). FFT/스펙트럼 전처리. |
| `smooth` | 스무딩(savgol/moving). |

> 비-MCP(python 직접 호출) 매핑: graph_types_list→`tools.types_list()`, graph_find→`tools.types_find(q)`, graph_schema_get→`tools.schema_get(t)`, graph_validate_inputs→`tools.validate_inputs(t, payload)`, graph_render→`tools.render_payload(t, payload, out_path)`, graph_lint_output→`tools.lint_output(path)`, graph_embed_block→`tools.embed_block(path)`.

---

## 타입 분류 — 빠른 선택 (의도 → 카테고리 → 타입)

먼저 **의도에 맞는 카테고리**를 고르고, 그 안에서 타입을 좁힌 뒤 `graph_schema_get`. 애매하면 `graph_find`. (전체·최신 목록은 `graph_types_list`가 SSOT. 분류 SSOT = `data/catalog/taxonomy.json`.)

| 카테고리 | 언제 | 대표 타입 |
|---|---|---|
| **trend** 추세·시계열 | X에 따른 곡선/응답 | base-xy, transient-time-history, stream-graph, overview-detail, animated-trajectory |
| **distribution** 분포 | 표본 분포/정규성/누적 | histogram, box-plot, violin-plot, qq-plot, ecdf-plot, pdf-kde, ridgeline |
| **comparison** 비교·상관 | 두 변수/케이스 비교·검증 | correlation-scatter, error-bar, dual-axis, scatter-matrix, chord-diagram |
| **ranking** 순위·구성 | 범주 크기·기여·우선순위 | bar-plot, pareto, waterfall-chart |
| **relations** 흐름·관계 | 흐름량/연결망/그룹관계/순서도 | sankey-diagram, network-graph, chord-diagram, flowchart |
| **hierarchy** 계층·구성 | 부분-전체 계층 | treemap, treemap-drilldown, sunburst |
| **kpi-status** 지표·현황 | KPI 현재값/달성률/목표 대비 | gauge, radial-progress, bullet-chart, stat-card |
| **playback** 시간 재생 | 순위/분포의 시간 변화 재생 | bar-chart-race, bubble-timeline |
| **mechanics** 재료/구조 | 응력-변형·하중-변위 | stress-strain, force-displacement, nonlinear-load-displacement |
| **reliability** 신뢰성·피로 | 수명/피로/고장 | weibull-prob-paper, kaplan-meier-survival, s-n-fatigue-curve, paris-crack-growth, rainflow-cycle-histogram, goodman-haigh |
| **process-quality** 공정/품질 | 공정 안정성/능력/MSA | spc-control-chart, process-capability-hist, cusum-chart, gauge-r-r |
| **doe** 실험계획·회귀진단 | 인자효과/교호작용/회귀가정 | main-effects-plot, interaction-plot, residual-diagnostic-panel, response-surface-2d |
| **signal-frequency** 신호·주파수 | 스펙트럼/필터/주파수응답 | fft-spectrum, psd-welch, spectrogram, filter-tuner, bode, eye-diagram |
| **control-dynamics** 제어·동역학 | 안정도/공진/모달 | nyquist-plot, root-locus, nichols-chart, pole-zero-map, campbell-diagram, mac-matrix-heatmap |
| **field-2d** 2D 필드·맵 | 2D 공간 분포 | contour-plot, heatmap-grid, mcae-stress-contour, vector-quiver-2d |
| **polar** 극좌표·방사 | 각도의존/방사/레이더 | polar-plot, radar-chart, rf-radiation-pattern, wind-rose, smith-chart |
| **geometry-3d** 3D 형상·결과 | 3D 형상/FE 결과/점군/곡면 | cad-3d-viewer, mesh-result-3d, mesh-deformed-3d, mode-shape-3d, point-cloud-3d, surface-3d, isosurface-3d |
| **table** 점검·비교표·다이어그램 | 항목/설계안 점검·비교·순서도 | review-matrix, design-state-compare, kpi-scorecard, decision-matrix, correlation-matrix, confusion-matrix, flowchart, multitrack-stack |
| **planning** 일정·계획 | 일정/마일스톤/업무 진척/계획서 | gantt-chart, milestone-timeline, calendar-heatmap, task-table, work-plan(종합 계획서: KPI+간트+마일스톤+리스크 결합) |

디스플레이·음향·RF·재료: cie-chromaticity(색역) · octave-band · vswr-curve · dma-curve · motor-tn-curve · tornado-chart(민감도) · test-report(시험성적서 컴포지트). RF는 `ingest_s2p`로 .s2p→smith/VSWR/S21 직결.

구조·열·측정 정형 플롯: mesh-convergence(GCI) · stress-linearization · hysteresis-loop · thermal-response(τ) · nusselt-correlation · frf-coherence · allan-deviation · calibration-curve.

E-CAE 검증·시험 정형 플롯(기존 카테고리에 분산): srs-spectrum(낙하 SRS) · emi-spectrum(CISPR 한계) · zth-transient(JESD51-14) · pdn-impedance(target) · temp-cycle-profile(JESD22-A104) · spec-margin-chart(합부 마진) · derating-curve · battery-discharge.

---

## 입력 모양 (graph_render / graph_validate_inputs)

xy 계열 기본형:
```jsonc
{
  "graph_type": "base-xy",
  "title": "Damped vs driven",            // 선택
  "axes": {
    "x": { "label": "Time", "unit": "s" },          // unit 무차원이면 ""
    "y": { "label": "Amplitude", "unit": "mm", "scale": "linear" }  // scale: "linear"|"log"
  },
  "series": [
    { "name": "damped", "data": [[0,0],[0.5,8.2],[1,5.1]] },        // [x,y] 쌍
    { "name": "driven", "data": [{"x":0,"y":0},{"x":1,"y":5.9}] },  // 또는 {x,y}
    { "name": "noisy",  "style": "line+markers", "color": "#888",
      "data": [[0,0.4],[1,4.2]] }                                  // y=null 이면 선 끊김(gap)
  ],
  "out_path": "d:/.../graph-out/plot.html"  // graph_render 만. 생략 시 기본 출력 폴더.
}
```
- `series[].style`: `line`(기본) | `markers` | `line+markers` | `step`.
- 축 `label` 과 `unit` 은 **필수**(unit 은 빈 문자열 허용). 모르면 추측하지 말고 **사용자에게 질문**.
- **비-xy 패밀리는 최상위 키가 다르다** — 예: flowchart `nodes/edges`, sankey `links`, gauge `value|items`, surface-3d `z_grid`, SPLOM `variables`, review-matrix `states/items`. 반드시 `graph_schema_get`의 hint를 따라 구성.

---

## Flow A — 기본 그래프
1. `graph_types_list`(또는 `graph_find`) → 적합한 타입 선택.
2. `graph_schema_get` → `requires[]` + hint 확인.
3. `graph_validate_inputs` 호출. `ok:true` 면 4로. `ok:false` 면 **Flow B**.
4. `graph_render` → `graph_lint_output`(게이트 통과 확인) → (게시 시) **Flow C**.

## Flow B — 배경정보/축 누락 해소 (반드시 지킬 것)
1. `graph_validate_inputs` 가 `missing[]` 을 반환하면 → **절대 렌더하지 말 것.**
2. 각 `missing[].ask` 문구로 사용자에게 질문한다. (출처가 aidatahub record 면 먼저 `get_record_sections` 로 조회 시도 후, 없으면 질문. 청크 텍스트에서 추출한 값은 "추정"이니 사용자에게 confirm 받을 것.)
3. 답을 받아 입력을 채워 `graph_validate_inputs` 를 **재호출**. `ok:true` 가 되면 `graph_render`.

## Flow C — report-write 게시 핸드오프
1. `graph_render` 로 나온 `html_path` 를 `graph_lint_output` 으로 검증.
2. `graph_embed_block <html_path>` 로 조각 생성(높이 자동; 필요 시 `--height` 로 override).
3. 그 조각을 report-write draft 의 `extra_blocks` 에 `html_embed` 로 추가. report-write 가 `local_path`→`file_id` 자동 업로드 → sandbox iframe 으로 렌더.

## Flow D — 웹 / 원격 MCP 서빙 (graph_skill.server, v0.46.0+)

로컬 파일/stdio 가 아니라 **HTTP 로 원격 제공**할 때. 코어(타입선택·검증·렌더·게이트)는 동일하고 전송만 다르다.

- 기동: `pip install -e ".[web]"` → `graph-skill-web` (단일 ASGI: REST + `/mcp` Streamable HTTP).
- 렌더: `POST /v1/render {graph_type, series/axes/...}` → **콘텐츠주소 아티팩트** `{status, hash, artifact_url, lint}`.
  배경값 부족 시 **HTTP 422** + `{status:"needs_input", missing[], questions[], answer_template}` — 서버는 절대 추측하지 않는다(Flow B 와 동일 계약, 원격에서도 유지). 자동화 클라이언트는 `answer_template`(채울 스켈레톤)을 채워 재호출.
- 수신: `GET /artifact_url` → self-contained HTML(immutable 캐시 + CSP).
- 그 외: `POST /v1/lint|embed {hash}`, `POST /v1/{graph_types_list|graph_find|graph_schema_get|graph_validate_inputs|ingest_csv|ingest_s2p|resample|smooth}`.
- 원격 MCP 클라이언트는 `/mcp` 로 접속(로컬 stdio `graph-skill-mcp` 도 그대로 유효).
- 산출이 **바이트결정적**이라 같은 입력은 같은 `hash`(자동 dedupe·CDN 캐시).

---

## Rules
- **NEVER invent** 축 단위·물리 배경값. `graph_validate_inputs` 가 `missing` 을 주면 렌더 전에 **반드시 사용자에게 질문**한다. 추정값으로 그린 그래프는 "자신있게 틀린" 최악의 실패다.
- **엔진/인터랙션을 직접 작성하지 마라.** 손으로 HTML/Canvas/차트 코드를 쓰지 말고 `graph_render` 만 사용한다. 인터랙션은 자동이다(위 목록).
- 산출물은 **외부 프레임 0·self-contained**. `graph_lint_output` 이 `ok:false`(외부 URL 발견 등)면 게시하지 마라.
- aidatahub 에 정적 PNG `stress_strain_plot` 이 따로 있다. **정적 이미지면 그쪽, 인터랙티브 HTML이면 graph-skill** (경쟁 아님, 직렬 보완).
- 게시는 report-write `html_embed` 계약(`file_id`/`local_path`, `height_px` 60–4000)에 묶인다.

---

## 예시 (요약)
사용자: "이 데이터로 시간-진폭 그래프 그려줘" + 시리즈 제공.
1. `graph_validate_inputs({graph_type:"base-xy", series:[...], axes:{x:{label:"Time",unit:"s"}, y:{label:"Amplitude",unit:"mm"}}})` → `ok:true`.
2. `graph_render({..., out_path:"…/plot.html"})` → `{status:"ok", html_path, recommended_height_px:520, lint:{ok:true}}`.
3. (게시) `graph_embed_block(html_path)` → report-write 로 전달.

축 단위를 모르면? → `graph_validate_inputs` 가 `axes.x/axes.y` 를 `missing` 으로 반환 → 그 `ask` 문구로 사용자에게 물어본 뒤 재시도.
사용자: "에너지 흐름도 그려줘" → `graph_find("흐름")` → sankey-diagram → `graph_schema_get` hint: `links:[{source,target,value}]` → 그 형태로 구성 → validate → render.
