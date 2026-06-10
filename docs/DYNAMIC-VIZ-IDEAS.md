# 역동적 표현법 — 전수 고민 (Dynamic representation backlog)

> **구현 상태(0.38.0): 권고 빌드 1~6 전부 완료.** A playback(bubble-timeline·animated-trajectory·bar-chart-race),
> C flow-core(sankey·network·chord), F gauge-core(gauge·radial-progress·bullet·stat-card), E 3D(point-cloud-3d·surface-3d·**isosurface-3d**),
> 잔여(stream-graph·sunburst), **B 연동/깊이(treemap-drilldown 드릴다운 · overview-detail focus+context · 공유 크로스헤어 xsync→multitrack · SPLOM 연동 브러싱 brushlink→scatter-matrix)**.
> **총 91종 / 9 엔진군 + 연동 버스(GraphLink: xsync·brushlink·xbrush·xfollow). pytest 344 · 실 브라우저 91/91 클린.**
> 남은 후보(선택): 3D streamlines/volume, treemap 외 계층 애니, alluvial/parallel-sets.

73종은 "정적 데이터의 인터랙티브 탐색"(줌·호버·크로스헤어·박스줌·브러시·토글·단면)에는 강하다.
하지만 **역동성(dynamism)** 을 네 축으로 쪼개 보면 비어있는 칸이 많다:

1. **시간/애니메이션** — 데이터가 시간에 따라 *변하는* 것을 재생(playback)
2. **연동/연결 인터랙션** — 한 뷰의 선택이 다른 뷰를 *바꾸는* 것(linked views, focus+context)
3. **관계·흐름·위상 구조** — 노드/엣지/흐름처럼 *구조가 데이터*인 것
4. **차원/공간** — 3D를 *돌려보고* 잘라보는 것 (메시는 했으나 scatter/surface/field는 미흡)

self-contained·결정적·엔진=고정자산 원칙은 그대로 유지(애니메이션도 임베드된 데이터의 클라이언트 재생일 뿐, 외부 스트림 아님).

---

## A. 시간/애니메이션 구동 (playback) — **가장 비어있고 레버리지 큼**

| 표현 | 역동성 | 커버 | 구현 |
|---|---|---|---|
| **time-scrubber(범용 재생)** | 타임 슬라이더+재생/정지로 임의 시계열/프레임을 애니메이션. 한 plugin이 모든 xy/field를 "재생가능"으로 격상 | ✗ | xy-core/field-core **playback plugin** (프레임=시간 인덱스, 슬라이더+▶) |
| **bar-chart-race** | 막대 순위가 시간에 따라 재배치(보간 이동) | ✗ | xy-core bar + 프레임 보간 plugin |
| **bubble-timeline(Gapminder)** | x·y·크기·색이 연도별로 움직이는 산점 | ✗ | xy-core scatter + size + playback |
| **trajectory/sweep 재생** | 궤적 위 점이 시간 따라 이동(S11 sweep, orbit, Nyquist 주파수 커서) | ✗ | 기존 타입에 frequency/time 커서 plugin |
| **operating-deflection(ODS) 2D** | 2D 구조가 진동하는 애니메이션 | ✗ | xy-core 폴리라인 warp 애니(3D 모드의 2D판) |
| **Monte-Carlo 누적 애니** | 점이 쌓이며 분포가 수렴 | ✗ | playback + 누적 산점 |

**핵심:** `playback` plugin 하나면 — time-scrubber·race·bubble-timeline·MC가 전부 파생. 3D 모드 애니는 이미 함(cad3d).

## B. 연동/연결 인터랙션 (linked / focus+context)

| 표현 | 역동성 | 커버 | 구현 |
|---|---|---|---|
| **SPLOM/crossfilter 연동 브러싱** | 한 셀에서 브러시 → 모든 셀에서 같은 점 강조 | △(parcoord brushing만) | review-matrix 셀 간 selection 버스(이벤트 공유) |
| **focus+context(overview+detail)** | 아래 미니 전체뷰에서 창을 드래그 → 위 상세뷰 줌 | ✗ | xy-core 보조 overview 스트립 + 윈도우 brush |
| **공유 크로스헤어(멀티트랙)** | 한 패널 호버 → 모든 패널 같은 x에 십자선 | △(multitrack은 독립) | 패널 간 커서 동기화 |
| **drill-down(treemap/sunburst)** | 클릭하면 하위 계층으로 확대 | ✗ | 계층 데이터 + 클릭 줌 |
| **tooltip 내 미니차트** | 호버 시 그 점의 스파크라인/분포 팝업 | ✗ | 호버 HUD에 미니 캔버스 |

## C. 관계·흐름·위상 구조 (relational / flow / topology) — **새 패밀리급**

| 표현 | 역동성 | 커버 | 구현 |
|---|---|---|---|
| **Sankey/흐름도** | 흐름 폭=값, 노드 드래그, **입자 애니메이션**으로 흐름 방향 표시 | ✗ | 신규 `flow-core`(또는 plugin): 노드/링크 레이아웃 + 입자 |
| **network/force-directed** | 노드-링크, 물리 시뮬로 펼쳐지고 드래그로 흔들림 | ✗ | `flow-core`: force 시뮬(velocity Verlet) |
| **chord diagram** | 원형 관계(상관/전이/혼동을 원호 리본으로) | ✗ | polar-core 확장(리본) |
| **dendrogram/tree** | 계층(클러스터·BOM) 접기/펼치기 | ✗ | flow-core 또는 review-matrix 트리 |
| **stream graph(themeriver)** | 흐르는 baseline 누적면적(시간별 구성) | ✗ | xy-core stacked-area + wiggle baseline |
| **alluvial/parallel-sets** | 범주 흐름(단계별 구성 이동) | ✗ | flow-core |
| **arc diagram** | 1D 노드 + 위 호 연결(시퀀스 관계) | ✗ | xy-core plugin |

## D. 계층 (hierarchy)

| 표현 | 커버 | 구현 |
|---|---|---|
| **sunburst/icicle** | ✗ | polar-core(방사 계층) / xy-core(icicle) |
| **treemap drill-down** | △(평면 treemap) | treemap plugin에 계층+클릭줌 |
| **circle packing** | ✗ | 계층 원 패킹 |

## E. 3D 동적 (orbit/section 위에 데이터 다양화)

| 표현 | 커버 | 구현 |
|---|---|---|
| **3D scatter / point-cloud** | ✗ | cad3d-core: Points(BufferGeometry) — 측정점/스캔 |
| **surface-3d (z=f(x,y))** | ✗ | cad3d-core: 격자→메시(RSM/모드형상 3D) |
| **isosurface / volume** | ✗ | cad3d-core: marching-cubes |
| **3D streamlines / vector** | ✗ | cad3d-core: 튜브/화살표 |
| **3D waterfall(스펙트럼 vs RPM/시간)** | ✗ | surface-3d 특수형(Campbell 3D) |

## F. 게이지·라이브 지표 (dynamic single-value) — **대시보드 가치, 쉬움**

| 표현 | 역동성 | 커버 | 구현 |
|---|---|---|---|
| **gauge/dial(속도계)** | 바늘이 값으로 회전, 색 밴드 | ✗ | polar-core 확장(바늘) 또는 xy plugin |
| **bullet chart** | 목표/정성밴드 대비 실적 막대 | ✗ | xy-core bar + 밴드/목표 마커 |
| **radial progress / KPI ring** | 도넛 진행률 + 중앙 큰 숫자 | ✗ | polar/canvas plugin |
| **stat-card(빅넘버+스파크+▲▼)** | 한 칸 요약 | △(kpi-scorecard 셀) | review-matrix 카드 레이아웃 |

## G. 공학 동적 (engineering motion)

| 표현 | 역동성 | 커버 | 구현 |
|---|---|---|---|
| **phase-portrait/state-space** | 궤적 + 시간 재생(리미트사이클) | ✗ | xy-core parametric + playback |
| **hysteresis loop 애니** | 하중-제하 사이클이 그려지는 재생 | ✗ | xy-core + playback |
| **P-V / T-S 사이클** | 열역학 사이클 상태점 이동 | ✗ | xy-core + 배경 + playback |
| **Bode/Nyquist/Smith 주파수 커서 연동** | 슬라이더로 주파수 → 세 뷰의 점 동시 이동 | ✗ | 다중뷰 + 공유 커서 |
| **3D 모드형상 애니** | 진동 재생 | ✓ | (mode-shape-3d 완료) |

## H. 메타/레이아웃 (composition)

| 표현 | 커버 | 구현 |
|---|---|---|
| **dashboard grid(자유 격자, 링크)** | △(multitrack 세로 스택) | review-matrix 자유 배치 + 링크 |
| **small multiples / facet** | ✗ | review-matrix 그래프셀 격자(같은 타입 × 범주) |
| **tabs / step-through 스토리** | ✗ | DOM 탭 + 주석 단계 |

---

## 권고 빌드 순서 (역동성 ROI)

1. **`playback` plugin (A축)** — 한 방에 time-scrubber·bar-race·bubble-timeline·MC·phase-portrait·hysteresis·sweep을 "재생가능"으로. **최고 레버리지.** xy-core/field-core 공용, frame 인덱스 + 슬라이더/▶, 엔진의 plugin-drag 라우팅 재사용.
2. **`flow-core` 신규 패밀리 (C축)** — Sankey(+입자 애니) · network(force) · chord · dendrogram · alluvial. 관계/흐름은 통째로 비어있고 시스템/에너지/토폴로지에 핵심.
3. **gauge·bullet·radial-progress (F축)** — 대시보드 완성도, 구현 쉬움(polar/canvas plugin).
4. **3D scatter/surface/isosurface (E축)** — cad3d-core Points/surface로 CAE 3D 결과 다양화.
5. **연동 뷰(B축)** — SPLOM 연동 브러싱 · focus+context · 공유 크로스헤어 · drill-down. (깊이/UX 고도화)
6. **sunburst/stream/stat-card 등 잔여** — 파생.

검증은 기존 4층(Python 결정성+lint, node 부팅, **실 브라우저 Playwright**, 엣지) 그대로 + 애니메이션은 "재생 토글 시 프레임 갱신·console.error 0"을 헤드리스로 가드.
