"""Render one canonical HTML per graph type into graph-out/gallery/ and build an
index.html gallery (each graph inlined in a lazy iframe + an open-fullscreen link).
Run: venv/Scripts/python.exe build_gallery.py

절차(필수): 엔진 ENGINE_VERSION 을 범프하면 반드시 이 스크립트로 갤러리를 재생성한다 —
tests/test_ux_p2.py::test_gallery_freshness_gate 가 메타의 engine@version 과 현재 버전을
대조해 스테일 산출물을 CI 실패로 만든다.
"""
import html
import json
from pathlib import Path

from graph_skill import builder, catalog

ROOT = Path(__file__).resolve().parent
TITLES = json.loads((ROOT / "src" / "graph_skill" / "data" / "catalog" / "types.json")
                    .read_text(encoding="utf-8"))["types"]
FIX = ROOT / "tests" / "fixtures"
GAL = ROOT / "graph-out" / "gallery"
GAL.mkdir(parents=True, exist_ok=True)

# (type, fixture, group, blurb)  — order defines gallery order
MAP = [
    ("base-xy", "base_xy", "X-Y 기본", "멀티시리즈 라인/마커 + 호버·크로스헤어·줌·로그·다크모드 (모든 xy의 기반)"),
    ("stress-strain", "stress_strain", "재료/구조", "인장 σ–ε + Et 접선 HUD + UTS/파단 마커 + 영역 음영"),
    ("force-displacement", "force_displacement", "재료/구조", "하중–변위 + 국소 강성 dF/dd 접선"),
    ("correlation-scatter", "correlation", "상관/DOE", "CAE vs Test 산점 + 회귀선/R² + y=x 동치선"),
    ("bland-altman", "bland_altman", "상관/DOE", "측정-CAE 일치도 (Bland-Altman: bias·±1.96SD LoA)"),
    ("loop-gain-margin", "loop_gain", "T1 정형 ★신규", "루프 안정도 — PM/GM 자동 판정 (0dB·−180° 교차)"),
    ("conducted-emission", "conducted_emission", "T1 정형 ★신규", "전도성 방출 — QP/AVG 이중 한계 worst margin"),
    ("tdr-impedance-profile", "tdr", "T1 정형 ★신규", "TDR 임피던스 — 회랑(z0±tol) 일탈 자동 마킹"),
    ("jitter-bathtub", "jitter_bathtub", "T1 정형 ★신규", "지터 배스터브 — dual-Dirac BER + eye opening"),
    ("battery-cycle-fade", "battery_cycle", "T1 정형 ★신규", "배터리 사이클 열화 — EOL 80% 교차 사이클"),
    ("cc-cv-charge-profile", "cccv", "T1 정형 ★신규", "CC-CV 충전 — 전환점·구간 음영 (이중축)"),
    ("thermal-resistance-stack", "thermal_stack", "T1 정형 ★신규", "열저항 분해 사다리 — ΔT=P·R, Tj margin"),
    ("hardness-profile", "hardness", "T1 정형 ★신규", "경도 프로파일 — 한계경도 교점 CHD"),
    ("xbar-r-chart", "xbar_r", "T1 정형 ★신규", "X̄-R 관리도 — A2/D3/D4 2단 패널"),
    ("fmea-worksheet", "fmea", "T1 정형 ★신규", "FMEA — RPN/AIAG-VDA AP 자동·색배지"),
    ("ewma-chart", "ewma", "T2 정형 ★신규", "EWMA 관리도 — 시변 한계·작은시프트 민감"),
    ("oc-curve", "oc", "T2 정형 ★신규", "OC 곡선 — 이항 Pa(p)·AQL/LTPD"),
    ("roc-pr-curve", "rocpr", "T2 정형 ★신규", "ROC/PR — AUC·Youden 최적점"),
    ("bathtub-curve", "bathtub", "T2 정형 ★신규", "욕조곡선 — 고장률 3구간·번인"),
    ("crow-amsaa-growth", "crowamsaa", "T2 정형 ★신규", "신뢰도 성장 — β MLE·MTBF log-log"),
    ("mohr-circle", "mohr", "T2 정형 ★신규", "모어 원 — 응력원·등축·다중"),
    ("boiling-curve", "boiling", "T2 정형 ★신규", "비등곡선 — log-log·CHF 자동마킹"),
    ("gate-charge-curve", "gatecharge", "T2 정형 ★신규", "게이트 차지 — Miller plateau·Qgs/Qgd"),
    ("immunity-level-profile", "immunity", "T2 정형 ★신규", "내성 프로파일 — 판정 색마커(A/B/C/F)"),
    ("resource-histogram", "resource_hist", "T2 정형 ★신규", "자원 히스토그램 — 누적막대·용량 초과"),
    ("raci-matrix", "raci", "T2 정형 ★신규", "RACI — 책임할당·A 1명 검증"),
    ("phase-noise", "phasenoise", "T2 정형B ★신규", "위상잡음 L(f) — RMS 지터·스퍼"),
    ("soa-chart", "soa", "T2 정형B ★신규", "SOA — 전력반도체 동작점 합부"),
    ("uncertainty-budget-chart", "uncertainty", "T2 정형B ★신규", "GUM 불확도 버짓 — 기여율·확장불확도"),
    ("tolerance-stackup-chart", "tolstack", "T2 정형B ★신규", "공차 스택업 — WC/RSS·spec"),
    ("evm-s-curve", "evm", "T2 정형B ★신규", "EVM S-커브 — SPI/CPI/EAC"),
    ("burndown-burnup", "burndown", "T2 정형B ★신규", "번다운 — 이상선·범위변경"),
    ("dqdv-curve", "dqdv", "T2 정형B ★신규", "dQ/dV — 미분용량·열화비교"),
    ("torque-angle-curve", "torqueangle", "T2 정형B ★신규", "토크-각도 — 항복점·스너그"),
    ("creep-curve", "creep", "T2 정형B ★신규", "크리프 — 최소율·단계 음영"),
    ("equivalence-tost-plot", "tost", "T2 정형B ★신규", "등가성 TOST — CI⊂한계 판정"),
    ("histogram", "hist", "통계 분포", "분포 히스토그램 (√n 빈, 밀도 옵션)"),
    ("bar-plot", "bar", "통계 분포", "범주별 막대"),
    ("grouped-bar", "grouped_bar", "통계 분포", "범주별 다계열 막대 + 막대/선 콤보(우측축)"),
    ("stacked-bar", "stacked_bar", "통계 분포", "범주별 누적 막대(구성비)"),
    ("box-plot", "box", "통계 분포", "그룹 산포 박스플롯 (사분위/수염/이상치)"),
    ("error-bar", "errbar", "통계 분포", "측정 불확도 오차막대"),
    ("pareto", "pareto", "품질/신뢰성 ★신규", "정렬 막대 + 누적%(우축) + 80% 기준선"),
    ("qq-plot", "qq", "품질/신뢰성 ★신규", "정규성 Q-Q + 적합직선/R²"),
    ("ecdf-plot", "ecdf", "품질/신뢰성 ★신규", "경험적 누적분포 F(x) 계단선"),
    ("spc-control-chart", "spc", "품질/신뢰성 ★신규", "Shewhart 관리도 CL/UCL/LCL + 이탈점(OOC)"),
    ("dual-axis", "dual", "주파수/제어", "좌/우 이종 물리량 이중축"),
    ("bode", "bode", "주파수/제어", "보드선도 Magnitude[dB] + Phase[deg], 로그 주파수"),
    ("fft-spectrum", "signal", "신호", "시간 ↔ 주파수 토글 + 피크 자동 마커"),
    ("filter-tuner", "filter_signal", "신호", "FFT + 차단주파수 슬라이더 (클라이언트 필터)"),
    ("polar-plot", "pattern", "극좌표", "각–반경 극좌표"),
    ("radar-chart", "radar", "극좌표", "다지표 레이더/스파이더"),
    ("rf-radiation-pattern", "pattern", "극좌표", "안테나 방사패턴 [dBi]"),
    ("contour-plot", "field", "2D 필드", "스칼라장 컨투어 + 컬러바 + 호버 probe"),
    ("heatmap-grid", "field", "2D 필드", "히트맵 (색만, 등치선 없음)"),
    ("scalar-field-2d", "field", "2D 필드", "일반 2D 스칼라장"),
    ("mcae-stress-contour", "field", "2D 필드", "von Mises 응력 맵 (turbo 컬러맵)"),
    ("review-matrix", "design_state", "점검/비교표", "범용 점검/리뷰표 (셀 = 값/상태/그래프/이미지)"),
    ("design-state-compare", "design_state", "점검/비교표", "설계 state 비교 + diff/합부 배지"),
    ("single-state-checklist", "design_state", "점검/비교표", "단일 설계 점검표 (비교표의 N=1 특수형)"),
    ("main-effects-plot", "main_effects", "공학 2D ★신규(G)", "DOE 주효과 — 인자별 수준평균 + 전체평균 기준선"),
    ("interaction-plot", "interaction", "공학 2D ★신규(G)", "DOE 교호작용 — 선 교차 = 상호작용 존재"),
    ("transient-time-history", "transient", "공학 2D ★신규(G)", "과도 응답(충격/지진) — 채널별 피크 마커 + 한계선"),
    ("convergence-residual-plot", "convergence", "공학 2D ★신규(G)", "솔버 수렴 — 잔차(log y) + 수렴기준선"),
    ("cfd-line-extract-compare", "cfd_line", "공학 2D ★신규(G)", "라인 추출 해석 vs 실험 — 멀티케이스 + 오차막대"),
    ("nonlinear-load-displacement", "nonlinear_ld", "공학 2D ★신규(G)", "비선형 F-d/pushover — 접선강성 + 항복/극한 마커"),
    ("s-n-fatigue-curve", "sn_curve", "공학 2D ★신규(G)", "피로 S-N(Wöhler) — log N + 피로한도선 + 설계점"),
    ("process-capability-hist", "capability", "신뢰성/제어/모달 ★신규(H)", "공정능력 — USL/LSL/정규피팅 + Cp/Cpk"),
    ("paris-crack-growth", "paris", "신뢰성/제어/모달 ★신규(H)", "균열성장 da/dN-ΔK — log-log + Paris 적합 + ΔKth/KIC"),
    ("campbell-diagram", "campbell", "신뢰성/제어/모달 ★신규(H)", "회전체 Campbell — 고유진동수 vs RPM + 엔진오더선"),
    ("kaplan-meier-survival", "km", "신뢰성/제어/모달 ★신규(H)", "신뢰성 생존곡선 — 계단 S(t) + 중도절단 마커 (그룹 비교)"),
    ("mac-matrix-heatmap", "mac", "신뢰성/제어/모달 ★신규(H)", "모드 상관 MAC 행렬 — 0~1 히트맵 + probe"),
    ("weibull-prob-paper", "weibull", "제어/신뢰성 ★신규(H2)", "Weibull 확률지 — 선형화 + 적합(β·η·R²), log 수명"),
    ("nyquist-plot", "nyquist", "제어/신뢰성 ★신규(H2)", "Nyquist 안정도 — 등비율 + 단위원 + −1 임계점"),
    ("root-locus", "rootlocus", "제어/신뢰성 ★신규(H2)", "근궤적 — 등비율 + 허수축(안정경계) + 극(×)/영점(○)"),
    ("vector-quiver-2d", "vquiver", "CFD/피로 필드 ★신규(H3)", "2D 벡터장 — 화살표(길이·색=크기) + 컬러바·probe"),
    ("rainflow-cycle-histogram", "rainflow", "CFD/피로 필드 ★신규(H3)", "피로 rainflow — 평균×범위 사이클 카운트 히트맵"),
    ("residual-diagnostic-panel", "residual", "회귀 진단 ★신규(H4)", "회귀 진단 4종 — Q-Q/Resid-Fitted/Scale-Loc/Leverage (셀=실제 인터랙티브 그래프)"),
    ("cad-3d-viewer", "cad_viewer", "3D CAD/메시 ★신규(J·WebGL)", "3D 형상 뷰어(three.js) — orbit·단면(clip)·와이어프레임·PNG (STL/OBJ/GLB)"),
    ("mesh-result-3d", "mesh_result", "3D CAD/메시 ★신규(J·WebGL)", "3D FE 결과 컨투어 — 정점 컬러 + 컬러바, orbit·단면으로 내부 핫스팟"),
    ("mesh-deformed-3d", "deform", "3D CAD/메시 ★신규(J·WebGL)", "3D 변형형상 — 변위 warp(배율 슬라이더)·원형상 오버레이·|U| 컬러"),
    ("mode-shape-3d", "modeshape", "3D CAD/메시 ★신규(J·WebGL)", "3D 모드형상 — 모드 드롭다운 + 재생/정지 진동 애니"),
    ("pdf-kde", "kde", "분포/신호/다변량 ★신규(W1)", "커널밀도(KDE) — 매끈한 PDF, 그룹 분포 비교"),
    ("ridgeline", "ridge", "분포/신호/다변량 ★신규(W1)", "능선도(joyplot) — 그룹별 분포를 세로 오프셋으로 비교"),
    ("spectrogram", "spectro", "분포/신호/다변량 ★신규(W1)", "스펙트로그램(STFT) — 시간×주파수 진폭 히트맵"),
    ("scatter-matrix", "splom", "분포/신호/다변량 ★신규(W1)", "산점도 행렬(SPLOM) — 변수쌍 산점+회귀(셀=실제 그래프)"),
    ("area-plot", "area", "면적/워터폴/바이올린 ★신규(W2)", "면적 곡선 — baseline까지 채움"),
    ("stacked-area", "stackedarea", "면적/워터폴/바이올린 ★신규(W2)", "누적 면적 — 구성 비중의 시간 변화"),
    ("waterfall-chart", "waterfall", "면적/워터폴/바이올린 ★신규(W2)", "워터폴 — 증감 분해(누적 떠있는 막대 + 연결선)"),
    ("violin-plot", "violin", "면적/워터폴/바이올린 ★신규(W2)", "바이올린 — 그룹별 KDE 분포 형태 + 중앙값"),
    ("nichols-chart", "nichols", "제어/다변량/방향 ★신규(W3)", "Nichols 선도 — 이득/위상 여유, 0dB·−180° 기준 + 임계점"),
    ("parallel-coordinates", "parcoord", "제어/다변량/방향 ★신규(W3)", "평행좌표 — 다변량 패턴/트레이드오프(수직축별 실제 min/max)"),
    ("wind-rose", "windrose", "제어/다변량/방향 ★신규(W3)", "윈드로즈 — 방향별 스택 섹터(풍향/배향 분포) + 범례"),
    ("smith-chart", "smith", "제어/다변량/방향 ★신규(W3)", "스미스 차트(RF) — R/X 격자 + S11 Γ 궤적, 호버 시 z·|Γ|·RL"),
    ("pole-zero-map", "polezero", "공학 2D 보강 ★신규(W4)", "극점-영점 맵 — 복소평면 등비율 + 극(×)/영점(○)"),
    ("cusum-chart", "cusum", "공학 2D 보강 ★신규(W4)", "CUSUM 관리도 — 누적합 C±/±H 결정선(작은 이동 탐지)"),
    ("goodman-haigh", "goodman", "공학 2D 보강 ★신규(W4)", "Goodman 피로선도 — σm vs σa + 파괴선, 동작점"),
    ("psd-welch", "psd", "공학 2D 보강 ★신규(W4)", "PSD(Welch) — 세그먼트 평균 주기도, log-log"),
    ("multitrack-stack", "multitrack", "멀티트랙/RSM ★신규(W5)", "멀티트랙 — N채널 공유 시간축 세로 스택(셀=실제 그래프)"),
    ("response-surface-2d", "rsm", "멀티트랙/RSM ★신규(W5)", "반응표면(RSM) — 2차 적합 컨투어(최적영역 탐색)"),
    ("treemap", "treemap", "멀티트랙/RSM ★신규(W5)", "트리맵 — 면적=값 squarified 구성 비중"),
    ("eye-diagram", "eye", "신호/MSA ★신규(W6)", "아이 다이어그램 — UI 폴딩 persistence 히트맵(신호무결성)"),
    ("gauge-r-r", "gaugerr", "신호/MSA ★신규(W6)", "Gauge R&R — EV/AV/GRR/PV %기여 + 30%/10% 기준선"),
    ("correlation-matrix", "corrmat", "다양한 표 ★신규(W7)", "상관행렬 — Pearson r 발산 히트맵"),
    ("confusion-matrix", "confmat", "다양한 표 ★신규(W7)", "혼동행렬 — 분류 카운트 + 정확도"),
    ("kpi-scorecard", "kpi", "다양한 표 ★신규(W7)", "KPI 스코어카드 — 값(▲▼)/목표/상태/달성도 바(리치셀)"),
    ("decision-matrix", "decision", "다양한 표 ★신규(W7)", "의사결정표(Pugh) — 조건부 색 점수 + 가중합계/최고안"),
    ("flowchart", "flowchart", "순서도/다이어그램 ★신규(F)", "비정형 순서도 — 노드에 그래프/이미지/표/지표 내장 · 자동배치 · 팬/줌/모달"),
    ("bubble-timeline", "bubble", "시간축 애니메이션 ★신규(A)", "버블 타임라인(Gapminder) — ▶재생/슬라이더, 위치·크기 프레임 보간"),
    ("animated-trajectory", "trajectory", "시간축 애니메이션 ★신규(A)", "궤적/위상평면 재생 — 마커가 path를 따라 이동하며 자취"),
    ("bar-chart-race", "race", "시간축 애니메이션 ★신규(A)", "막대 경주 — 프레임별 순위/값 보간 가로막대"),
    ("sankey-diagram", "sankey", "관계·흐름 ★신규(C)", "Sankey 흐름도 — 레이어 자동배치 + 폭∝흐름량 리본 + 호버 강조"),
    ("network-graph", "network", "관계·흐름 ★신규(C)", "네트워크(force) — 물리 시뮬 자동전개 + 노드 드래그, 그룹=색/연결=크기"),
    ("chord-diagram", "chord", "관계·흐름 ★신규(C)", "코드 다이어그램 — 원형 그룹호 + 관계 리본(전이/상호참조 행렬)"),
    ("gauge", "gauge", "게이지·지표 ★신규(F)", "게이지 — 270° 다이얼+바늘+구간색, 로드 애니메이션(지표 그리드)"),
    ("radial-progress", "ring", "게이지·지표 ★신규(F)", "도넛 진행률 — 달성률 링 + 중앙 큰 값(KPI 패널)"),
    ("bullet-chart", "bullet", "게이지·지표 ★신규(F)", "불릿 차트 — 정성밴드 + 실적막대 + 목표틱(목표 대비)"),
    ("point-cloud-3d", "pointcloud", "3D 데이터 ★신규(E·WebGL)", "3D 점군/산점 — 색=스칼라(컬러바), orbit·단면"),
    ("surface-3d", "surface", "3D 데이터 ★신규(E·WebGL)", "3D 곡면 z=f(x,y) — 높이·색=z, orbit로 돌려보기"),
    ("stat-card", "statcard", "대시보드/계층 ★신규(B·D)", "KPI 스탯카드 — 빅넘버 카운트업 + 추세 ▲▼ + 스파크라인"),
    ("stream-graph", "stream", "대시보드/계층 ★신규(B·D)", "스트림그래프(themeriver) — 중앙정렬 누적 흐름 밴드"),
    ("sunburst", "sunburst", "대시보드/계층 ★신규(B·D)", "선버스트 — 방사 계층, 세그먼트 클릭 드릴다운/중앙 상위로"),
    ("treemap-drilldown", "treemapdrill", "연동·드릴다운 ★신규(B)", "계층 트리맵 — 타일 클릭 드릴다운 + breadcrumb 상위로"),
    ("overview-detail", "overviewdetail", "연동·드릴다운 ★신규(B)", "focus+context — 하단 개요의 창을 드래그하면 상단 상세가 줌"),
    ("isosurface-3d", "isosurface", "3D 데이터 ★신규(E·WebGL)", "등위면 — 3D 스칼라장의 등치면(marching tetrahedra), orbit"),
    ("srs-spectrum", "srs", "E-CAE 검증·시험 ★신규(EC)", "낙하충격 SRS(JESD22-B111) — Smallwood maximax + 규격 half-sine 비교"),
    ("emi-spectrum", "emi", "E-CAE 검증·시험 ★신규(EC)", "EMI 스펙트럼 vs CISPR 한계선 — 위반 마커 + 최소 마진"),
    ("zth-transient", "zth", "E-CAE 검증·시험 ★신규(EC)", "과도 열임피던스 Zth(t)(JESD51-14) — TDI 분기=RthJC"),
    ("pdn-impedance", "pdn", "E-CAE 검증·시험 ★신규(EC)", "PDN 임피던스 vs target — 초과율 자동 표기(전원무결성)"),
    ("temp-cycle-profile", "tempcycle", "E-CAE 검증·시험 ★신규(EC)", "온도 사이클 프로파일(JESD22-A104) — 사다리꼴 자동 생성"),
    ("spec-margin-chart", "specmargin", "E-CAE 검증·시험 ★신규(EC)", "규격 마진 차트 — 항목별 측정 vs 한계 + PASS/FAIL"),
    ("derating-curve", "derating", "E-CAE 검증·시험 ★신규(EC)", "derating 곡선 + 동작점 합부(적합/위반 자동 색)"),
    ("battery-discharge", "battery", "E-CAE 검증·시험 ★신규(EC)", "배터리 방전곡선 — C-rate 멀티 + cutoff 점선"),
    ("mesh-convergence", "meshconv", "구조·열·측정 ★신규(MTE)", "격자 수렴성 — Richardson 외삽·관측차수 p·GCI% 자동"),
    ("stress-linearization", "stresslin", "구조·열·측정 ★신규(MTE)", "응력 선형화(SCL) — membrane/bending 자동 적분"),
    ("hysteresis-loop", "hysteresis", "구조·열·측정 ★신규(MTE)", "반복하중 이력곡선 — 사이클별 소산에너지 자동"),
    ("thermal-response", "thermalresp", "구조·열·측정 ★신규(MTE)", "열 응답 — 1차 RC 적합으로 τ·T∞ 자동 추출"),
    ("nusselt-correlation", "nusselt", "구조·열·측정 ★신규(MTE)", "Nu–Re 상관 — 멱법칙 적합(R²) + 문헌 상관식 오버레이"),
    ("frf-coherence", "frf", "구조·열·측정 ★신규(MTE)", "FRF+coherence(우축) — 공진 피크 자동 마커(모달시험)"),
    ("allan-deviation", "allan", "구조·열·측정 ★신규(MTE)", "Allan deviation — σ(τ) 자동 계산 + -1/2 기울기 가이드"),
    ("calibration-curve", "calibration", "구조·열·측정 ★신규(MTE)", "교정곡선 — 선형적합(R²)+잔차(우축)+허용오차 밴드"),
    ("cie-chromaticity", "cie", "디스플레이·음향·확장 ★신규(EXT)", "CIE 1931 색도도 — 공식 궤적 내장 + 색역 삼각형 + 면적비"),
    ("octave-band", "octave", "디스플레이·음향·확장 ★신규(EXT)", "1/3 옥타브 밴드(IEC 61260) — 협대역 에너지 합산 자동"),
    ("tornado-chart", "tornado", "디스플레이·음향·확장 ★신규(EXT)", "민감도 토네이도 — 스팬 정렬 + baseline 점선"),
    ("motor-tn-curve", "motortn", "디스플레이·음향·확장 ★신규(EXT)", "모터 T-N — 토크/효율(우축)/동작점"),
    ("vswr-curve", "vswr", "디스플레이·음향·확장 ★신규(EXT)", "VSWR — S11 dB 자동 변환 + 한계선 + 합부 제목"),
    ("dma-curve", "dma", "디스플레이·음향·확장 ★신규(EXT)", "DMA — E'/E'' log + tanδ(우축) + Tg 자동 마커"),
    ("test-report", "testreport", "디스플레이·음향·확장 ★신규(EXT)", "시험성적서 — 개요+판정마진+결과그래프+종합판정(멀티엔진)"),
    ("gantt-chart", "gantt", "일정·계획 ★신규(P)", "간트차트 — 그룹밴드·진척·의존화살표·주말음영·오늘선"),
    ("milestone-timeline", "timeline", "일정·계획 ★신규(P)", "마일스톤 타임라인 — 교차 콜아웃 + 상태색 + 오늘 마커"),
    ("calendar-heatmap", "calheat", "일정·계획 ★신규(P)", "캘린더 히트맵 — 주×요일 격자, 색=활동량(잔디)"),
    ("task-table", "tasktable", "일정·계획 ★신규(P)", "업무 목록표 — 담당/기간/진척bar/상태/우선순위/D-day(명시 기준일)"),
    ("work-plan", "workplan", "일정·계획 ★신규(P)", "종합 업무계획서 — 개요+KPI+간트+마일스톤+업무분장+리스크 결합(3엔진 1파일)"),
]

cards, fails = [], []
for typ, fix, group, blurb in MAP:
    payload = json.loads((FIX / f"{fix}.json").read_text(encoding="utf-8"))
    if typ == "polar-plot" and "radius" not in payload:
        payload["radius"] = {"label": "Amplitude", "unit": ""}
    try:
        r = builder.render(typ, payload, out_path=str(GAL / f"{typ}.html"))
        if not r["lint"]["ok"]:
            raise RuntimeError("lint failed")
        h = catalog.resolve_type(typ).height_px or 480
        title = TITLES.get(typ, {}).get("title", typ)
        cards.append((typ, group, blurb, title, h, r["bytes"]))
    except Exception as e:  # noqa: BLE001
        fails.append((typ, str(e)[:140]))
        print("FAIL", typ, "->", e)

# ---- build index.html ------------------------------------------------------
parts = []
last_group = None
for typ, group, blurb, title, h, nbytes in cards:
    if group != last_group:
        parts.append(f'<h2 class="grp">{html.escape(group)}</h2>')
        last_group = group
        parts.append('<div class="grid">')
        # close previous grid handled below by tracking; simpler: always one grid per group
    # we open a grid per group: detect group change to also close
parts = []
last_group = None
for typ, group, blurb, title, h, nbytes in cards:
    if group != last_group:
        if last_group is not None:
            parts.append("</div>")           # close previous grid
        parts.append(f'<h2 class="grp">{html.escape(group)}</h2><div class="grid">')
        last_group = group
    kb = f"{nbytes/1024:.0f} KB"
    parts.append(
        '<div class="card">'
        f'<div class="cap"><span class="ty">{html.escape(typ)}</span>'
        f'<a class="open" href="./{typ}.html" target="_blank" rel="noopener">전체화면 ↗</a></div>'
        f'<div class="ti">{html.escape(title)}</div>'
        f'<div class="bl">{html.escape(blurb)}</div>'
        f'<iframe src="./{typ}.html" loading="lazy" style="height:{h}px" title="{html.escape(typ)}"></iframe>'
        f'<div class="meta">{kb} · self-contained</div>'
        "</div>"
    )
if cards:
    parts.append("</div>")
body = "\n".join(parts)

fail_html = ""
if fails:
    items = "".join(f"<li><code>{html.escape(t)}</code> — {html.escape(m)}</li>" for t, m in fails)
    fail_html = f'<div class="fails"><b>렌더 실패 {len(fails)}건:</b><ul>{items}</ul></div>'

doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>graph-skill 갤러리 — {len(cards)} 그래프 양식</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:14px/1.5 "Segoe UI",system-ui,sans-serif;
         background:#0e1116; color:#e6e6e6; }}
  header {{ padding:22px 28px; border-bottom:1px solid #2a2f3a; position:sticky; top:0;
           background:#0e1116ee; backdrop-filter:blur(6px); z-index:5; }}
  header h1 {{ margin:0 0 4px; font-size:19px; }}
  header p {{ margin:0; color:#9aa4b2; font-size:13px; }}
  .wrap {{ padding:18px 28px 60px; max-width:1500px; margin:0 auto; }}
  h2.grp {{ font-size:14px; letter-spacing:.02em; color:#7dd3fc; margin:30px 0 12px;
           border-left:3px solid #38bdf8; padding-left:9px; }}
  .grid {{ display:grid; gap:18px; grid-template-columns:repeat(auto-fill,minmax(460px,1fr)); }}
  .card {{ background:#161b22; border:1px solid #2a2f3a; border-radius:10px; overflow:hidden;
          display:flex; flex-direction:column; }}
  .cap {{ display:flex; justify-content:space-between; align-items:center;
         padding:9px 12px 0; }}
  .ty {{ font-family:ui-monospace,Consolas,monospace; font-size:12.5px; color:#f0b429; }}
  .open {{ font-size:12px; color:#7dd3fc; text-decoration:none; }}
  .open:hover {{ text-decoration:underline; }}
  .ti {{ padding:2px 12px 0; font-weight:600; }}
  .bl {{ padding:2px 12px 8px; color:#9aa4b2; font-size:12.5px; }}
  iframe {{ width:100%; border:0; border-top:1px solid #2a2f3a; background:#fff; }}
  .meta {{ padding:6px 12px; font-size:11px; color:#6b7280;
          border-top:1px solid #2a2f3a; background:#11151c; }}
  .fails {{ margin:24px 0; padding:12px 16px; background:#2a1518; border:1px solid #7f1d1d;
           border-radius:8px; color:#fca5a5; font-size:12.5px; }}
  .fails code {{ color:#fecaca; }}
  a.top {{ color:#7dd3fc; }}
</style></head>
<body>
<header>
  <h1>graph-skill 갤러리 · {len(cards)} 그래프 양식</h1>
  <p>각 카드는 외부 의존 0의 self-contained 인터랙티브 HTML이다. 카드 안에서 직접 호버·줌·토글할 수 있고, “전체화면 ↗”로 단독 파일을 연다. report-write <code>html_embed</code>로 글에 그대로 임베드되는 것과 동일한 산출물.</p>
</header>
<div class="wrap">
{fail_html}
{body}
</div>
</body></html>
"""

idx = GAL / "index.html"
idx.write_text(doc, encoding="utf-8", newline="\n")
print(f"\nOK  rendered {len(cards)} types, {len(fails)} failed")
print("INDEX:", idx)
