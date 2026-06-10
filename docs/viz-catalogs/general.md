I now have the complete and exact picture of the architecture. I have everything needed to produce the comprehensive mapping. Let me compose the catalog mapping covering all requested visualization methods, plus the additional ones, mapped to engine families and graph-types per the exact schema (engine, extends, plugins[], requires[], post, options_defaults, height_px).

This is a domain-cataloger task — the output is the markdown table plus the two analysis sections. I'll produce the final answer directly.

---

# 일반 과학/공학 시각화 → graph-skill 규격화 매핑

graph-skill 아키텍처(SKILL-PLAN §6/§18, catalog `types.json` 스키마)에 정확히 사상. 각 행 = catalog 한 블록 후보. `상속 베이스`는 `extends` 필드, `feature plugin`은 `plugins[]`, `필수 배경정보`는 `requires[]`(없으면 validate가 `missing[]`→질문), `후처리`는 `post[]`(Python 사전계산 경계), `엔진패밀리`는 catalog `engine` 필드.

**엔진패밀리 후보(이 매핑에서 제안):** `xy-core`(현존, Canvas 2D) / **`polar-core`**(각도-반경, Canvas 2D) / **`field-core`**(2D 스칼라장·등고선·벡터장·히트맵, Canvas 2D + 오프스크린 ImageData) / **`flow-core`**(노드-링크/계층 다이어그램, Canvas 2D 또는 SVG) / **`3d-core`**(WebGL/three.js, cad-viewer 형제) / `table-core`(SKILL-PLAN §18 기존).

규약: x/y의 단위 누락은 `require_axes:true`로 항상 잡힘 — 표의 `필수 배경정보`에는 **축단위 외의 도메인 특유 requires만** 적었다.

---

## 표 1 — 2D 직교(xy-core) : line/area/bar/통계 분포

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `base-xy` | 일반 X-Y 곡선 | 보편(시뮬 응답곡선) | 임의 정량 | 임의 정량 | 멀티시리즈 선 | (없음) | — (코어) | (코어내장) | — | xy-core | ★★★★ |
| `scatter-xy` | 산점도 | 상관/원시점/parametric | 정량 | 정량 | 미정렬 점운 | 점 의미 | base-xy | unsorted-mode, point-markers | sort-detect | xy-core | ★ |
| `step-plot` | 계단 그래프 | 디지털신호/상태천이/ZOH | 시간 | 레벨 | 계단 보간(전/후/중) | step 방향 | base-xy | step-curve | — | xy-core | ★ |
| `area-plot` | 면적 그래프 | 누적/포락/단일채움 | 정량 | 정량 | 곡선아래 채움 | baseline(0/시리즈) | base-xy | area-fill | — | xy-core | ★ |
| `stacked-area` | 누적 면적 | 구성비 시계열(부하분담) | 시간 | 누적량 | 시리즈 적층 | 적층순서, 정규화여부 | area-plot | stack-aggregate | stack.cumulative | xy-core | ★★ |
| `dual-axis` | 이중 축 | 이종 물리량 동시(온도+전류) | 공유 x | 좌/우 독립 | 좌우 축매칭 색 | 우축 quantity+unit | base-xy | secondary-y, axis-color-match | — | xy-core | ★★ |
| `error-bar` | 오차막대 | 측정 불확도/반복편차 | 정량/범주 | 평균±σ | 점+상하 캡 | 오차 의미(σ/SE/CI%), n | base-xy | error-bars | stats.dispersion | xy-core | ★★ |
| `error-band` | 오차 밴드 | CAE 앙상블/불확도 띠 | 정량 | 중앙±밴드 | 연속 신뢰띠 채움 | 밴드 정의(±σ/분위) | base-xy | band-fill | stats.envelope | xy-core | ★★ |
| `histogram` | 히스토그램 | 분포형상/공정산포 | bin(값) | 빈도/밀도 | 막대 분포 | bin수/폭 또는 rule, density여부 | base-xy | bin-aggregate, bar-render | stats.histogram | xy-core | ★★ |
| `pdf-plot` | 확률밀도 | 분포 피팅/커널밀도 | 값 | 밀도 | KDE/파라메트릭 곡선 | 커널·대역폭 또는 분포족 | histogram | kde-fit, dist-overlay | stats.kde / stats.fit_dist | xy-core | ★★★ |
| `cdf-plot` | 누적분포 | 분위/초과확률 | 값 | 누적확률 | 단조 0→1 곡선 | (없음) | base-xy | cumulative, percentile-marker | stats.cdf | xy-core | ★★ |
| `ecdf-plot` | 경험적 CDF | 비모수 분포 비교 | 값 | F̂(x) | 계단형 ECDF+신뢰띠 | (없음) | cdf-plot | ecdf-step, dkw-band | stats.ecdf | xy-core | ★★ |
| `box-plot` | 상자그림 | 그룹 산포/이상치(DOE 셀) | 범주/그룹 | 정량 | 사분위·수염·이상치 | 그룹키, 수염규칙(1.5IQR) | base-xy | box-whisker, outlier-mark | stats.quartiles | xy-core | ★★ |
| `violin-plot` | 바이올린 | 그룹 분포형상 | 범주 | 정량 | 좌우대칭 KDE | 커널·대역폭 | box-plot | violin-kde | stats.kde | xy-core | ★★★ |
| `bee-swarm` | 비스웜 | 소표본 원시점 분산 | 범주 | 정량 | 충돌회피 점배치 | 그룹키 | scatter-xy | swarm-layout | stats.jitter_pack | xy-core | ★★★ |
| `bar-plot` | 막대 | 범주 비교 | 범주 | 정량 | 단순 막대 | 범주 순서 | base-xy | category-axis, bar-render | — | xy-core | ★ |
| `grouped-bar` | 그룹막대 | 범주×시리즈(공법별) | 범주 | 정량 | 군집 막대 | 그룹/시리즈 키 | bar-plot | group-offset | — | xy-core | ★★ |
| `stacked-bar` | 누적막대 | 구성비(소비전력 분해) | 범주 | 누적 | 적층 막대 | 적층순서, 정규화여부 | bar-plot | stack-aggregate | stack.cumulative | xy-core | ★★ |
| `pareto-chart` | 파레토 | 결함/불량 80-20 | 범주(정렬) | 빈도+누적% | 막대+누적선(이중축) | 정렬기준 | dual-axis | pareto-sort, cum-line | stats.pareto | xy-core | ★★ |
| `waterfall-chart` | 폭포 | 기여분해(질량/전력 budget) | 단계 | 증감 | 부동막대 연결 | 시작/종료, 증감부호 | bar-plot | floating-bar, connector | stats.running_total | xy-core | ★★ |
| `candlestick` | 캔들스틱 | OHLC/시뮬 범위추이 | 시간 | OHLC | 시가-고저-종가 봉 | O/H/L/C 매핑 | base-xy | ohlc-render, time-axis | — | xy-core | ★★ |
| `regression-fit` | 회귀+신뢰구간 | 상관 정량/추세 | 정량 | 정량 | 적합선+CI/PI 밴드 | 모델(선형/다항/멱), CI% | scatter-xy | regression, ci-band, residual-panel | stats.regression | xy-core | ★★★ |
| `qq-plot` | Q-Q 플롯 | 정규성/분포 적합 | 이론 분위 | 표본 분위 | 점+45°/적합선 | 기준분포(정규 등) | scatter-xy | qq-line, ref-line | stats.theoretical_quantiles | xy-core | ★★ |
| `spc-control-chart` | 관리도(SPC) | 공정 관리/이상감지 | 시간/표본# | 측정치 | CL±3σ 관리한계+룰위반 | CL/UCL/LCL 또는 부분군 | base-xy | control-limits, rule-violation | stats.control_limits | xy-core | ★★ |

---

## 표 2 — 다변량(xy-core 확장 / 일부 polar-core)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `parallel-coordinates` | 평행좌표 | 다변량 DOE/설계공간 | 변수축(N) | 정규화값 | 다축 선묶음+브러싱 | 축 목록·각 range/방향 | base-xy | parcoord-axes, axis-brush | mv.normalize_axes | xy-core | ★★★★ |
| `scatter-matrix` | 산점행렬(SPLOM) | 변수쌍 상관 일괄 | 변수 i | 변수 j | k×k 페어 그리드 | 변수 목록 | scatter-xy | splom-grid, linked-brush | mv.pairwise | xy-core | ★★★★ |
| `radar-chart` | 레이더/스파이더 | 항목 프로파일(스펙 비교) | 각(축=항목) | 반경(값) | 닫힌 다각형 | 항목축·각 스케일 | (신규) | radar-axes, polygon-fill | mv.normalize_axes | **polar-core** | ★★★ |
| `star-glyph` | 스타/글리프 | 개체별 다변량 small-multiple | 각 | 반경 | 미니 레이더 격자 | 변수 목록 | radar-chart | glyph-grid | mv.normalize_axes | **polar-core** | ★★★ |
| `ternary-plot` | 삼원도 | 3성분 조성(합금/소재비율) | 좌표A | B(/C) | 삼각형 무게중심좌표 | 3성분 합=100% 규칙 | (신규) | ternary-axes, point-map | mv.barycentric | **field-core**(또는 xy-core+좌표plugin) | ★★★★ |

> `ternary-plot`은 삼각 좌표변환이 핵심이라 xy-core의 직교 `view.scaleX/Y`로는 부정확. 전용 좌표 plugin이 붙는 `field-core`(2D 비직교 좌표 일반화) 또는 polar처럼 별도 좌표 계열로 둔다. 가장 깔끔한 건 `polar-core`를 "비직교 2D 좌표계 패밀리"로 넓혀 radar/ternary를 함께 수용하는 것 — 후술.

---

## 표 3 — 분포/밀도/장(field-core 신규 패밀리)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `heatmap-grid` | 히트맵 | 행렬/2D 룩업/온도맵 | 범주/x | 범주/y (z=색) | 셀 색 인코딩 | z 의미+단위, 컬러스케일 도메인 | (신규) | color-scale-legend, cell-hover | field.gridify | **field-core** | ★★★ |
| `correlation-heatmap` | 상관 히트맵 | 변수간 상관행렬 | 변수 | 변수 (z=ρ) | 대칭 상관행렬+발산색 | 상관계수법(Pearson 등) | heatmap-grid | diverging-scale, corr-annot | stats.corr_matrix | **field-core** | ★★★ |
| `contour-plot` | 등고선 | 2D 스칼라장 레벨(응력장) | 공간/param x | 공간/param y (z=등치) | 등치선+레벨라벨 | z 의미+단위, grid 규칙성, 레벨 | heatmap-grid | iso-lines, level-label | field.contour(marching squares) | **field-core** | ★★★★★ |
| `density-2d` | 2D 밀도 | 산점 과밀→밀도 | 정량 | 정량 (z=밀도) | KDE 밀도 음영 | 커널·대역폭, grid | heatmap-grid | density-shade | field.kde2d | **field-core** | ★★★★ |
| `hexbin-plot` | 헥스빈 | 대용량 산점 비닝 | 정량 | 정량 (z=count) | 육각셀 카운트 | hex 크기, 집계함수 | density-2d | hexbin-aggregate, hex-render | field.hexbin | **field-core** | ★★★★ |
| `scalar-field-2d` | 2D 스칼라장 | CAE 필드(온도/전위/압력) | 공간 x | 공간 y (z=값) | 연속 색장+옵션 등고선 | z 의미+단위, mesh 종류(정·비정렬) | heatmap-grid | field-image, iso-overlay | field.interpolate / field.tri_interp | **field-core** | ★★★★ |
| `vector-field-quiver` | 벡터장/퀴버 | 유동/자기장/변위벡터 | 공간 x | 공간 y (벡터 u,v) | 화살표 격자 | (u,v) 의미+단위, 정규화/스케일 | scalar-field-2d | quiver-arrows, mag-color | field.vector_grid | **field-core** | ★★★★ |
| `streamline-plot` | 유선 | 유동 흐름선 | 공간 x | 공간 y (벡터) | 적분 유선/궤적 | (u,v) 필드, seed 전략 | vector-field-quiver | streamline-integrate | field.streamlines(RK4) | **field-core** | ★★★★★ |

---

## 표 4 — 위상/주파수/극좌표(polar-core 신규 + xy-core)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `fft-spectrum` | FFT 스펙트럼 | 진동/소음 주파수성분 | 주파수[Hz] | 진폭/PSD | 단측 스펙트럼+피크 | **fs**[Hz], window | time-series(base-xy) | fft-view, domain-toggle, peak-detect | spectral.fft_onesided | xy-core | ★★★ |
| `bode-plot` | 보드 선도 | 제어/필터 주파수응답 | log f[Hz] | mag[dB] / phase[°] | mag·phase 2단 적층(로그) | 입출력쌍 또는 H(f) | fft-spectrum | dual-log-axis, mag-phase-stack | spectral.transfer_function | xy-core | ★★★★ |
| `nyquist-plot` | 나이퀴스트 | 안정성/극좌표 응답 | Re{H} | Im{H} | 복소평면 궤적+단위원 | H(f) 데이터 | (신규) | nyquist-trace, unit-circle | spectral.complex_response | **polar-core**(또는 xy-core+극plugin) | ★★★★ |
| `spectrogram-stft` | 스펙트로그램 | 시변 주파수(전력 트랜지언트) | 시간 | 주파수 (z=dB) | STFT 시간-주파수 히트맵 | **fs**, window, hop/overlap | (신규) | stft-image, freq-cursor | spectral.stft | **field-core** | ★★★★ |
| `waterfall-spectrum` | 워터폴 스펙트럼 | RPM/시간별 스펙트럼 적층 | 주파수 | 진폭(+슬라이스 오프셋) | 적층 3D풍 라인맵 | **fs**, 슬라이스 축 의미 | fft-spectrum | waterfall-stack, slice-offset | spectral.stft_slices | xy-core(2.5D) / **3d-core**(true 3D) | ★★★★ |
| `polar-plot` | 극좌표 플롯 | 방사패턴/방위 응답 | 각θ | 반경 r | 각-반경 곡선 | 각 단위(deg/rad), 각방향/0° | (신규) | polar-grid, angle-axis | — | **polar-core** | ★★★ |
| `smith-chart` | 스미스 차트 | RF 임피던스 매칭(ECAE) | Re{Γ} | Im{Γ} | 정규화 임피던스 원호격자 | Z0(특성임피던스) | nyquist-plot | smith-grid, impedance-map | spectral.reflection_coeff | **polar-core** | ★★★★★ |
| `eye-diagram` | 아이 다이어그램 | SerDes/신호무결성(ECAE) | UI 시간(폴딩) | 진폭 (z=밀도) | 비트 중첩 밀도 | UI(심볼주기), 트리거/오프셋 | density-2d | eye-fold, mask-overlay | field.eye_fold | **field-core** | ★★★★★ |

---

## 표 5 — 3D(3d-core 신규, cad-viewer 형제)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `surface-3d` | 3D 곡면 | 반응표면/2변수 응답(DOE) | x | y, z(높이) | 메시 곡면+조명 | x/y/z 의미+단위, grid 규칙성 | (신규) | orbit-camera, color-by-z, contour-proj | field.gridify / mesh.build | **3d-core** | ★★★★★ |
| `scatter-3d` | 3D 산점 | 3변수 군집/설계공간 | x | y, z | 궤도회전 점운 | x/y/z 의미+단위 | surface-3d | orbit-camera, point-cloud | — | **3d-core** | ★★★★ |
| `isosurface-3d` | 등치면 | 체적장 레벨(CAE 3D 필드) | x | y, z(+볼륨 v) | 3D 등치면 추출 | 볼륨 의미+단위, iso 레벨, voxel grid | surface-3d | isosurface, clip-plane | field.marching_cubes | **3d-core** | ★★★★★ |
| `mesh-result-3d` | CAE 결과 메시 | 해석결과 표면 컬러맵(변위/응력) | (모델공간) | — (z=결과) | 메시 표면+결과 컬러 | 결과량 의미+단위, 단위계, 변형배율 | scatter-3d | result-colormap, deform-scale, section-plane | mesh.attach_field | **3d-core**(↔cad-viewer 공유) | ★★★★★ |

> `3d-core`와 `cad-viewer`(SKILL-PLAN §18)는 같은 WebGL/three.js 토대를 공유. 분리 근거: cad-viewer는 STEP→GLB CAD 형상 중심, 3d-core는 격자/필드 데이터 시각화 중심. 공통 vendor(three.js)는 `data/vendor/`에 둔다. `mesh-result-3d`는 둘의 교집합(형상+결과장)이라 어느 쪽 패밀리로 두든 plugin 공유.

---

## 표 6 — 흐름/관계(flow-core 신규)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sankey-diagram` | 생키 | 흐름/에너지·전력 수지 | (레이아웃) | — | 노드+가중 흐름띠 | 노드/엣지+flow값, 단위 | (신규) | sankey-layout, flow-hover | flow.sankey_layout | **flow-core** | ★★★★ |
| `chord-diagram` | 코드 | 상호 흐름행렬(통신/열교환) | (원형) | — | 원형 노드+호 연결 | 인접행렬, 대칭여부 | (신규) | chord-layout, ribbon | flow.chord_layout | **flow-core** | ★★★★ |
| `network-graph` | 네트워크/그래프 | 토폴로지/의존관계 | (레이아웃) | — | 노드-엣지 force/static | 노드/엣지, 레이아웃법 | (신규) | force-layout, node-drag, edge-bundle | flow.graph_layout | **flow-core** | ★★★★ |
| `treemap` | 트리맵 | 계층 비중(스토리지/비용) | (타일) | — (크기/색) | 중첩 사각 타일 | 계층, 크기metric, 색metric | (신규) | treemap-squarify, drill-down | flow.hierarchy / flow.squarify | **flow-core** | ★★★ |
| `sunburst` | 선버스트 | 계층 비중(방사) | 각(계층깊이) | 반경(레벨) | 방사 계층 링 | 계층, 크기metric | treemap | sunburst-arcs, zoom-ring | flow.hierarchy | **flow-core**(polar 좌표) | ★★★ |
| `icicle-plot` | 아이시클 | 계층 비중(직교) | 깊이 | 비중폭 | 직교 계층 블록 | 계층, 크기metric | treemap | icicle-blocks | flow.hierarchy | **flow-core** | ★★★ |

---

## 표 7 — 시간/이벤트 & 지표(KPI)

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `gantt-chart` | 간트 | 프로젝트/해석잡 일정 | 시간 | 작업(행) | 작업 바+의존선 | 작업 start/end, 시간단위 | base-xy | time-axis, task-bars, dependency-link | time.intervals | xy-core | ★★★ |
| `timeline-events` | 타임라인 | 이벤트/마일스톤 | 시간 | (트랙) | 점/구간 이벤트 | 이벤트 시각, 트랙키 | gantt-chart | event-markers, lane-layout | time.events | xy-core | ★★ |
| `bullet-graph` | 불릿 | KPI 목표대비 실적 | 정량 | (단일행) | 실적바+목표+질적대역 | 목표/대역 임계, 단위 | bar-plot | bullet-ranges, target-marker | — | xy-core | ★★ |
| `gauge-chart` | 게이지 | 단일지표 다이얼 | 각(값) | — | 반원/원형 다이얼+니들 | 범위 min/max, 임계대역 | (신규) | gauge-arc, needle, threshold-band | — | **polar-core** | ★★ |
| `kpi-tile` | KPI 타일 | 대시보드 수치카드 | — | — | 큰수치+델타+스파크라인 | 값, 비교기준, 추세데이터 | (신규) | big-number, delta-arrow, sparkline | stats.delta | xy-core(미니) / table-core | ★ |

---

## (a) 도메인 특유 인터랙션 / 오버레이 (base 자동 인터랙션 위에 추가되는 것)

base 엔진이 자동 제공(호버/크로스헤어/툴팁/HUD/줌·팬/박스줌/로그토글/범례isolate/다크모드/반응형/PNG·CSV export) — 아래는 **타입 특유로 plugin이 얹는 오버레이**:

- **통계(box/violin/swarm/qq/ecdf):** 호버 시 사분위·중앙·이상치 수치 HUD; QQ는 가장 벗어난 점 강조; ECDF는 임의 x에서 백분위 읽기 크로스헤어; violin은 KDE 대역폭 슬라이더.
- **회귀/피팅(regression-fit, curve-fit):** 잔차 패널 동기 하이라이트, R²/계수/CI% HUD, 모델 토글(선형↔멱↔다항), 신뢰밴드↔예측밴드 전환. CAE-test correlation은 **45° 동치선 + ±오차밴드 + 점별 (CAE,test) 라벨**.
- **히스토그램/PDF/CDF:** bin 수 슬라이더 실시간, density↔count 토글, 분포 오버레이 적합(정규/Weibull) on/off — Weibull은 MX 신뢰성/수명에 필수.
- **이중축/파레토/워터폴:** 좌우축 색매칭 가이드라인, 파레토 80% 컷오프 마커, 워터폴 누적 러닝토탈 호버.
- **FFT/Bode/스펙트로그램:** 피크 라벨·하모닉 커서, peak snap, dB↔linear·amp↔PSD 토글, 차수(order) 마커(RPM 연동), STFT는 시간슬라이스 스크럽으로 순간 스펙트럼 추출.
- **필터 튜너:** 차단주파수 슬라이더 → 클라이언트 fft.js 미리보기 마스크(“preview” 라벨) → 확정 시 Python filtfilt 재계산(“exact” 라벨). (SKILL-PLAN §10.2)
- **field-core(등고선/히트맵/벡터/스칼라장):** 마우스 위치의 z값 프로브(데이터 좌표 역변환), iso-level 슬라이더, 컬러스케일 도메인/감마 조정·발산↔순차 전환, 벡터장 화살표 밀도/스케일 슬라이더, 유선 seed 클릭 배치, hexbin 집계함수(count/mean) 전환. 컬러바는 오버레이 범례 plugin.
- **polar-core(radar/polar/Nyquist/Smith/gauge):** 각 회전·0° 기준 토글, 반경 로그/선형, Nyquist 단위원·이득여유/위상여유 마커, Smith 정규화 임피던스/어드미턴스 격자 토글·매칭점 픽킹.
- **3d-core/cad:** 궤도/팬/줌 카메라, view-cube(iso/front/top 스냅), section/clip-plane 슬라이더+capping, z-기준 컬러맵, 변형배율(deform-scale) 슬라이더, 등치면 레벨 슬라이더, 측정(거리/각도) 픽킹.
- **flow-core(sankey/chord/network/treemap/sunburst):** 노드/엣지 호버 시 연결 강조(나머지 디밍), 흐름값 툴팁, 계층 drill-down(클릭 줌인), 노드 드래그(force), 경로 추적 하이라이트.
- **시간/이벤트(gantt/timeline):** overview-brush 미니맵, 작업 의존선 호버 추적, 크리티컬패스 강조, 줌 레벨별 시간 눈금 재포맷.
- **공통 오버레이 plugin:** `named-markers`(임계점/스펙 한계선), `region-shading`(허용/불허 구간), `ref-line`(목표/규격), `annotation`(주석), `live-tangent`(국소 기울기·접선).

## (b) 새 엔진패밀리가 필요한 항목 (2D xy-core 직교 `view.scaleX/scaleY`로 안 되는 것)

xy-core의 좌표계약은 “직교 data→pixel 선형/로그 변환”이다(SKILL-PLAN §4.5). 아래는 좌표계·렌더 모델 자체가 달라 **별 패밀리** 필요:

1. **`polar-core`(비직교 2D 각-반경/원호 좌표계).** 후보 타입: `polar-plot`, `radar-chart`/`star-glyph`, `nyquist-plot`, `smith-chart`, `gauge-chart`, `sunburst`(원형 변형), `ternary-plot`(삼각 무게중심 — 비직교의 또다른 변종). 근거: 각도-반경/삼각 좌표변환은 xy의 `scaleX/scaleY`로 표현 불가. 같은 `view` 추상 위에 `scalePolar(θ,r)→px`를 새로 정의하는 패밀리. *대안:* polar-core를 “비직교 2D 좌표계 패밀리”로 넓혀 ternary·smith까지 한 패밀리에 수용.

2. **`field-core`(2D 스칼라/벡터 장 — 픽셀/그리드 래스터 + 등치선/벡터 오버레이).** 후보: `heatmap-grid`, `correlation-heatmap`, `contour-plot`, `density-2d`, `hexbin-plot`, `scalar-field-2d`, `vector-field-quiver`, `streamline-plot`, `spectrogram-stft`, `eye-diagram`. 근거: z=f(x,y) 격자 보간·marching-squares 등치선·ImageData 래스터·벡터 적분(streamline)은 라인 렌더러가 아님. 오프스크린 캔버스 ImageData + 컬러맵 LUT 렌더 루프가 핵심. **MX의 CAE 필드(응력/온도/전위 맵), SI eye-diagram이 여기 의존.** (SKILL-PLAN §12.2 #13 contour/heatmap이 이 패밀리의 씨앗.)

3. **`3d-core`(WebGL/three.js — cad-viewer 형제).** 후보: `surface-3d`, `scatter-3d`, `isosurface-3d`, `mesh-result-3d`, true-3D `waterfall-spectrum`. 근거: 깊이·카메라·조명·메시는 Canvas 2D 불가. cad-viewer(§18)와 vendor(three.js)·인터랙션(orbit/section) 공유. **3D CAE 결과(변위/응력 메시), 반응표면(DOE)이 여기.** 번들 모드(§18.4)로 대용량 GLB/메시 처리.

4. **`flow-core`(노드-링크/계층 다이어그램 — 좌표가 데이터가 아니라 레이아웃 산출물).** 후보: `sankey-diagram`, `chord-diagram`, `network-graph`, `treemap`, `sunburst`, `icicle-plot`. 근거: x/y가 입력이 아니라 레이아웃 알고리즘(force/squarify/sankey)의 출력. 데이터 도메인↔픽셀 선형변환 모델이 성립하지 않음. **MX 전력/에너지 수지(Sankey), 토폴로지 의존(network)이 여기.**

**xy-core로 충분한 것(별 패밀리 불필요):** 표1 전부(line/scatter/step/area/stacked/dual-axis/error-bar·band/histogram/PDF/CDF/ECDF/box/violin/bee-swarm/bar/grouped/stacked/Pareto/waterfall/candlestick/regression/QQ/SPC), parallel-coordinates·SPLOM(직교 다축 합성), fft-spectrum·bode(직교 로그축), 2.5D waterfall-spectrum(슬라이스 오프셋 라인맵), gantt·timeline·bullet·kpi-tile. — 이들은 **catalog 한 블록(+필요시 plugin 1파일)**로 떨어지며 `engine:"xy-core"` 유지(SKILL-PLAN §6 plugin 합성 모델 그대로).

**경계/모호 케이스 결정:**
- `ternary-plot` → polar-core(비직교 좌표) 또는 field-core. 좌표변환 plugin 한 개로 xy-core에 억지로 얹을 수 있으나 정확도·틱 처리상 별 좌표 계열 권장.
- `nyquist-plot` → 데이터는 Re-Im 직교라 **xy-core+단위원 plugin으로도 가능**. 단 Smith와 묶어 polar-core에 두는 게 인터랙션(임피던스 격자) 일관.
- `waterfall-spectrum` → 의사 3D는 xy-core(슬라이스 오프셋), 진짜 3D 회전 필요 시 3d-core. 두 type-id로 분리 가능.
- `kpi-tile` → 미니 스파크라인이면 xy-core, 순수 수치 카드면 table-core.

**우선순위 제안(MX 시뮬 도메인 가치 기준):** field-core(CAE 응력/온도 필드·correlation-heatmap·eye-diagram) ≳ 3d-core(3D CAE 결과·반응표면) > polar-core(RF Smith/방사패턴·radar 스펙비교) > flow-core(전력수지 Sankey). 표1 통계군(box/violin/regression+CI/QQ/ECDF/histogram/SPC)은 xy-core plugin만으로 즉시 추가 가능해 DOE·CAE-test correlation에 가장 저비용·고효용.

**관련 파일(절대경로):** catalog 스키마 `D:\graph-skill\src\graph_skill\data\catalog\types.json`; 아키텍처 권위안 `D:\graph-skill\docs\SKILL-PLAN.md`(§4 좌표계약, §6 extends/plugin 합성, §12.2 타입 로드맵, §18 엔진패밀리 일반화·cad-viewer); 엔진 `D:\graph-skill\src\graph_skill\data\engines\xy-core\engine.js`; 부트 디스패치 `D:\graph-skill\src\graph_skill\data\shell\boot.js`(`window.GraphEngines[family]` 레지스트리 — 신규 패밀리 진입점).