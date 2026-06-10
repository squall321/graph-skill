I have all the verification I need. The report-write `html_embed` is a single-block "replace" widget — it takes one embedded HTML, not a bundle of files. This confirms a critical gap in the design-state-table's "bundle mode" assumption. I now have enough to deliver the exhaustive completeness critique.

# 완결성 비평 — 5개 산출 전체 점검

검증 기반: `types.json`(현재 base-xy 1블록), `validate.py`(requires→missing 게이트, `_dig` dotted-path), `serialize.py`(`lint_self_contained`는 `src=//`·`href=//`만 차단 — `srcdoc`/`data:`는 통과, `safe_js_literal`이 `<` 이스케이프), report-write SKILL.md(`html_embed`는 **단일 블록 replace, 번들 없음**; `image/attachment`만 `file_id` 다중 append).

---

## (1) 어디에도 없는 결과 도시 방법 — 실무자가 그리는데 5개 카탈로그 누락

| type-id | 도메인 | 왜 필요 | 엔진패밀리 |
|---|---|---|---|
| `histogram-2d-jointplot` | 통계/DOE·SI | 산점 가장자리에 주변(marginal) 히스토그램 결합 — DOE 변수쌍·지터 분포의 표준 도시인데 SPLOM/density-2d만 있고 marginal 결합형이 빠짐 | field/xy 합성 |
| `ridgeline-joyplot` | NVH·열·시계열 | RPM/조건별 분포를 세로로 적층(스펙트럼 진화의 라인 버전) — waterfall의 통계판, 어디에도 없음 | xy |
| `time-history-multitrack` | 낙하/진동/전력 | 한 시간축에 가속도·응력·전류·온도를 **수직 분할 스택 패널**(공유 x, 개별 y)로 — drop/vibration 실측의 기본 도시. dual-axis(2개)만 있고 N-track 스택 없음 | xy |
| `tornado-waterfall-bridge` | DOE/마진 | 민감도→마진소모 연결(기여 누적). tornado와 waterfall은 따로 있으나 둘을 잇는 budget bridge 없음 | xy |
| `nichols-chart` | 제어/PI 루프 | open-loop gain[dB] vs phase[deg], Bode/Nyquist 삼형제 중 빠짐(PMIC 루프 안정도 실무 표준) | xy |
| `polar-spectrogram` / `angle-rpm-map` | NVH order | order-track은 있으나 각도(크랭크각)-RPM 2D 맵 누락 | field |
| `strain-rosette-mohr` | 구조 | Mohr 원(주응력/전단) — 구조 실무 필수 작도인데 전 카탈로그 부재. 전용 원좌표 | polar/specialized |
| `weibull-CI-multispec` | 신뢰성 | rel-weibull-prob 있으나 다(多)표본 겹침+95% CI 밴드 동시 비교형 누락 | prob-paper |
| `cdf-survival-overlay` | 신뢰성 | KM 생존곡선과 Weibull CDF **겹쳐** 비교 — 따로는 있고 overlay 부재 | xy |
| `pole-zero-rootlocus` | 제어/소자 | ckt-pole-zero는 정적, gain 변화 따른 root-locus 궤적 누락 | xy |
| `digital-timing-waveform` | ECAE/SI | 다채널 디지털 버스 타이밍도(0/1/Z/X 레인 + 셋업/홀드 마커) — step-plot로 불충분, 전용 레인 렌더 | xy(레인) |
| `confusion-matrix` / `roc-pr-curve` | 통계/ML 분류 | DOE/통계 횡단인데 ML 평가 도시 전무. AI 진단모델 결과에 필요 | matrix / xy |
| `calendar-heatmap` | system/신뢰성 | 시간(일·주) 기반 발열/필드고장 빈도 맵 — 누락 | field/matrix |
| `cumulative-flow-burndown` | system 일정 | gantt/timeline 있으나 누적 진척/번다운 없음 | xy |

**가장 치명적 누락 3개**: ① `time-history-multitrack`(낙하·진동의 1순위 실측 도시인데 N-패널 스택이 없음 — dual-axis 2개로는 4신호 불가), ② `mohr-circle`(구조 해석 기본 작도), ③ `nichols-chart`(Bode/Nyquist 짝).

---

## (2) 새 엔진패밀리 필요한데 분류 안 된 것 (polar/smith/eye/field/3d/flow)

5개 카탈로그가 합의한 패밀리: `field-2d` · `polar` · `smith` · `eye/raster` · `3d/mesh3d/cad` · `flow` · `matrix-grid` · `prob-paper` · `parallel-coords` · `chromaticity` · `vector-field` · `ternary`.

**여전히 분류 안 됐거나 패밀리 미배정인 viz 타입:**

| type-id | 도메인 | 왜 새 패밀리 필요 | 엔진패밀리 |
|---|---|---|---|
| `mohr-circle` | 구조 | 원-좌표 + 응력변환, xy/polar 어느 쪽도 정확히 못함 | **polar 확장 or 전용** |
| `nichols-chart` | 제어 | gain-phase 평면 + 등M/등N 곡선격자(Smith류 비직교 격자) | **smith-core 일반화로 흡수** |
| `digital-timing/logic-waveform` | SI/ECAE | 레인별 디지털 상태(0/1/Z/X) + 전이 엣지 — Canvas 라인 아님, 전용 레인 렌더 | **신규 `logic-wave`** |
| `volume-render-3d` (체적장) | 열/RF/SAR | isosurface는 표면, **반투명 체적 누적**(ray-cast)은 별개 | **3d-core 확장(volume)** |
| `geo-pcb-overlay` | EMI/PI/열 | 보드 geometry(실루엣) 위 필드 정합 — field-2d에 "비정형 mask/board outline 오버레이" 서브엔진 필요 명시 부족 | **field-2d 서브엔진** |
| `density-persistence-raster` | SI eye + 일반 | eye와 별개로 "수만 trace persistence" 자체가 raster 엔진 — 카탈로그2는 raster, 카탈로그4는 eye를 field-core로, 카탈로그5는 signal-eye로 **3가지로 분열 분류**(아래 (5) 중복 참조) | **`raster-core` 단일화 필요** |
| `tree/icicle/sunburst` 좌표 분열 | system | flow-core인데 sunburst는 polar 좌표 — flow-core 내부 좌표계가 직교/극 혼재. 미해결 | **flow-core 좌표 추상 미정의** |

**미배정/경계 미결정으로 남은 것**: `ternary-plot`(카탈로그4가 polar-core냐 field-core냐 **본인이 결론 못 냄**), `nyquist`(xy+unit-circle vs polar로 **카탈로그2/4 불일치**), `waterfall-spectrum`(2.5D xy vs true-3d로 **분열**). 이들은 "패밀리 미정"으로 명시적 결정 필요.

---

## (3) design-state-table 설계(카탈로그5)에서 빠진 요구 — 갭 목록

요구별로 점검:

**A. "셀이 그래프/사진" — 부분 충족, 핵심 갭 있음**
- ✅ cell-graph(xy-core 재마운트), cell-image(inline/bundle) 설계됨.
- ❌ **셀에 들어갈 그래프가 이종 패밀리(field-2d/polar/smith/3d)일 때 iframe srcdoc 모드**를 제안했으나, 그 패밀리들이 **아직 존재하지 않음**(types.json엔 base-xy 1개뿐). 즉 "field-2d 컨투어 셀"은 그 엔진이 구현돼야 성립 — 설계가 미래 의존성에 silent하게 기댐. **선행조건(어느 셀-패밀리가 MVP에 필요한가) 미명시.**
- ❌ **그래프 셀의 height/aspect 협상 부재**: 셀은 작은데 xy-core는 `height_px:520` 가정. 셀 안 축소 렌더 시 HUD/접선/범례가 깨지는 문제(미니 모드 plugin) 미설계.
- ❌ **사진 셀의 `data:` URI가 lint를 통과**하는 건 맞으나(검증함), **번들 모드는 report-write가 받지 못함**(아래 B 참조) — inline 한계 초과 시 게시 경로가 실제로 끊김.

**B. "report-write 게시" — 설계의 가장 큰 결함**
- ❌ **`html_embed`는 단일 블록 replace 위젯**(SKILL.md L551 확인). 카탈로그5의 "bundle 게시 = html + assets/ 디렉터리를 files upload" 경로는 **report-write에 존재하지 않음**. `image/attachment`만 다중 `file_id` append 가능하고, `html_embed`는 하나의 self-contained HTML만 받음. → **번들 모드 매트릭스는 게시 불가.** 설계가 가정한 우회로가 실재하지 않음. **인라인(self-contained) 단일 .html만 게시 가능**이 진짜 제약.
- ❌ height_px 산출식(`80 + 행수×34`) 제안했으나 report-write `height_px` 허용범위(60–4000 clamp) 초과 시(대형 매트릭스) **잘림/스크롤 거동 미정의**.

**C. "구조화 조회" — 충족하나 누락 있음**
- ✅ `embed-index`(byGroup/byStatus/byTag/byState 역색인) 설계됨.
- ❌ **외부(프로그램) 조회 API 부재**: 임베드 JSON은 사람이 Export 버튼으로 받는 용도. report-write/aidatahub가 **렌더 없이 매트릭스 상태를 질의**(예: "fail 셀만 추출")하는 서버측 경로 없음. "구조화 조회"가 클라이언트 런타임에만 존재.
- ❌ **셀 출처(provenance) 조회 인덱스 미설계**: 데이터모델에 `ref:"DOC-...§4"` 필드는 있으나 `bySource` 역색인 없음 — "이 record에서 온 셀 전부" 조회 불가(인용 추적 요구와 충돌).

**D. "여러 state 비교" — 대체로 충족, 갭 2개**
- ✅ states[]≥2, diff-highlight, baseline freeze 설계됨.
- ❌ **state가 N>5일 때 가로 스크롤/열 페이지네이션·열 그룹화** 미설계(미드프레임 v1~v8 같은 다열). 
- ❌ **state 간 그래프 셀 비교**: 같은 항목의 v1/v2 그래프를 **한 셀에 오버레이**(겹쳐 비교)하는 모드 부재 — 현재는 열마다 별도 작은 그래프. 실무 1순위 비교 도시(겹친 곡선)가 빠짐.

**E. "self-contained" — 충족, 단 미세 갭**
- ✅ lint 게이트 통과 경로 검증됨(`data:`/`srcdoc` 통과 확인).
- ❌ **srcdoc 내부의 중첩 `</script>`/`</html>` 충돌**: 카탈로그5는 `safe_js_literal`이 `<` 이스케이프한다고 했으나, srcdoc은 **HTML 속성값**이지 JS 리터럴이 아님 — srcdoc 주입 시 `"` 와 `</script>` 이스케이프 책임이 `safe_js_literal`로 안 덮임. **별도 attribute-escape 필요**(설계가 잘못된 도구에 위임).
- ❌ **`lint_self_contained`의 `single_root` 체크**: 매트릭스 HTML이 내부에 그래프 `<html>`(srcdoc)을 품으면 정규식 `^\s*<html`이 다중 매치할 위험 — srcdoc 안 `<html>`은 들여쓰기로 회피 가능하나 **명시적 검증 미설계**.

**F. "재편집" — 충족, 갭 1개**
- ✅ embed-index의 source JSON round-trip(byte-동일 재렌더) 설계됨.
- ❌ **부분 재편집의 충돌 해소 미정의**: 사람이 JSON 한 셀 spec만 바꿔 재투입 시, 그래프 셀 payload는 정규화된 형태로 **고정**돼 원본 raw 데이터 추적 불가 — "raw로 되돌려 재편집" 경로 없음(정규화 일방향).
- ❌ **재편집 시 validate 재실행 강제 부재**: 수정된 JSON이 requires를 깨도(예: 축 단위 삭제) 재렌더가 막히는지 불명확.

---

## (4) validate requires(필수 배경정보)가 불명확한 타입

`validate.check`는 `requires[].field`를 **dotted-path**로 `_dig`하여 payload에서 찾는다. 따라서 requires는 **단일 스칼라 경로**여야 명확. 아래는 그 모델로 표현 안 되거나 모호한 타입:

- **그리드 규칙성(field 전체)**: 다수 카탈로그가 "규칙성"을 requires로 적었으나 이는 **데이터 구조 속성**이지 payload 필드가 아님 — `_dig`로 못 잡음. "비정형 mesh→그리드 보간 필요 여부"를 어떤 field/path로 물을지 불명확. (stress-contour, temp-contour, 모든 field 타입)
- **색맵 한계(σ_y, Gc, SF=1, BER levels)**: "임계값"을 requires로 적었으나 **항목별 배열**(여러 iso-level)일 수 있음 — 단일 `_dig` 경로 모델과 불일치.
- **메시(STL/GLB)**: 모든 *-3d 타입이 "메시"를 requires로 하나 이는 **바이너리 자산 경로**이지 payload 스칼라 아님 — validate가 파일 존재/단위계를 어떻게 검사할지 미정의.
- **`fs`(샘플레이트)**: fft/bode/srs/psd/spectrogram 전부 fs 필수인데 카탈로그마다 `requires` 명시 위치가 제각각(어떤 건 표에, 어떤 건 plugin에). **canonical field 경로(`params.fs`?) 미통일.**
- **`spec`(매트릭스)**: 카탈로그5의 spec는 `{min/max/target/tol}` 또는 `{error_pct}` 또는 `{targets,weights}`로 **타입마다 형태가 다름** — 단일 requires 경로로 못 잡음. `_dig("spec.error_pct")` vs `_dig("spec.targets")` 분기 로직이 validate에 없음(현재 validate는 평탄한 requires 리스트만 순회).
- **`states`/`items` 비배열·길이 조건**: "states≥2"는 **개수 조건**이지 존재 조건 아님 — `_dig`는 None만 검사하므로 "길이 2 미만"을 못 잡음. validate 확장 필요(현재 `series` 존재 체크처럼 특수 로직 추가해야 함).
- **`baseline`이 states 중 하나를 가리키는지(참조 무결성)**: diff 타입의 baseline은 **교차 참조 검증** 필요 — 현 validate에 없음.
- **dual-axis/multitrack의 "우축 quantity+unit"**: `axes.y`만 검사하는 현 `require_axes` 로직은 **2번째 y축(`axes.y2`)을 검사 안 함** — dual-axis 타입의 우축 단위 누락이 게이트를 통과해버림.

---

## (5) 중복 / 이름충돌

**type-id 충돌(서로 다른 카탈로그가 같은 이름, 다른/같은 정의):**
- `rf-sar-map` — 카탈로그2(ECAE)와 카탈로그3(system) **양쪽 정의**. requires 다름(2: tissue model/mass avg; 3: 평균질량/한계/밴드). **병합 필요.**
- `rf-smith-chart` — 카탈로그2·3 중복.
- `rf-vswr`, `rf-return-loss/s11` — 카탈로그2·3 중복.
- `rf-radiation-pattern-polar/3d` (2) vs `rf-antenna-pattern-polar/3d` (3) — **같은 것, 다른 이름**(radiation vs antenna). 이름 통일 필요.
- `rf-eye-diagram`(3) vs `si-eye-diagram`(2) vs `eye-diagram`(4) — **3중 이름충돌**.
- `mac-matrix`(C, 카탈로그1) vs `corr-mac-matrix`(카탈로그3) — 동일.
- `response-surface`/`response-surface-3d`(1,H) vs `doe-response-surface-3d`/`doe-response-contour`(3) — 중복.
- `waterfall-spectrogram`(1,C) vs `spectrogram-stft`(4) vs `acoustic-spectrogram`(3) vs `disp-flicker`등 — STFT 맵이 도메인별로 4개 이름.
- `histogram`/`histogram-dist`(1,H) vs `histogram`(4) vs `doe-montecarlo-hist`/`ckt-monte-carlo-hist`(3,2) — 히스토그램이 5개 변종 이름.
- `parallel-coordinates`(4) vs `doe-parallel-coords`/`opt-design-space-parallel`(3) — 중복.
- `correlation-scatter`/`cae-test-overlay`(1) vs `corr-scatter-r2`/`corr-overlay`(3) vs `correlation-heatmap`(4) — correlation 계열 이름 난립.
- `pareto-chart`(1,4) vs `pareto-failure`/`doe-pareto-effects`(3) — 중복.
- `bode`(1) vs `bode-plot`(4) vs `ckt-bode-plot`(2) vs `sensor-mems-bode`/`bat-eis-bode`(2) — bode 5개.

**엔진패밀리 이름충돌:**
- `field-2d`(2,5) vs `field-core`(4) vs `field`(1) — **같은 패밀리 3개 이름**.
- `polar`(1,3) vs `polar-core`(2,4) — 통일 필요.
- `smith`(1,3) vs `smith-core`(2,4).
- `mesh3d`(1) vs `cad3d`/`cad3d-core`(2) vs `3d-core`(4) vs `surface-3d`(3) vs `cad-viewer`(5) — **3D 패밀리 5개 이름** — 가장 심한 분열.
- `matrix`(1) vs `matrix-grid`(5) — 카탈로그1의 `matrix`(rainflow/mac/solder cell-heatmap)와 카탈로그5의 `matrix-grid`(메타-아티팩트 표)는 **개념이 다른데 이름이 충돌**: 전자는 데이터 셀 히트맵, 후자는 그래프-품는 표. **명확히 분리 명명 필요**(예: `cell-matrix` vs `review-matrix`).
- `raster`/`raster-core`(2,4) vs `eye-base`(2) vs `signal-eye`(5) vs `field-core`(4, eye를 여기로) — **eye-diagram 엔진 배정이 4개 카탈로그에서 4가지**.
- `flow-core`(4) vs `graph-node`(2, RC네트워크) — flow/network 패밀리 부분중복.

**plugin 이름충돌:** `peak-detect`(B/C), `color-scale-legend`/`colorbar`(여러), `grid-field`/`heatmap`/`field-image`(같은 일), `live-tangent`(재라벨 재사용은 의도적이나 단위 recipe 분기 미명시) — plugin 정규화 사전 필요.

---

## 종합 — 최우선 조치 (망라 요약)

1. **게시 경로 근본 결함**: design-state-table의 번들 모드는 report-write `html_embed`가 못 받음 → **inline self-contained 단일 .html만이 실현 가능한 게시 경로**. 큰 이미지/대량 셀은 게시 불가이므로 "썸네일+inline" 강제 또는 report-write 측 번들 위젯 신설이 선결.
2. **패밀리 명명 통일(SSOT)**: field/polar/smith/3d/eye/matrix가 카탈로그마다 2~5개 이름 → `types.json` 등록 전 **canonical family 사전** 필수(특히 3D 5개·field 3개·matrix 2개념 충돌).
3. **validate 모델 확장**: dotted-path 단일 스칼라 모델로는 (그리드 규칙성·메시 자산·배열 임계·states≥2 개수조건·baseline 참조무결성·dual-axis y2·spec 다형태)를 못 잡음 → `series`/축처럼 **타입별 특수 게이트 로직** 추가 필요.
4. **누락 viz 1순위**: `time-history-multitrack`(N-패널 스택), `mohr-circle`, `nichols-chart`, 그래프 셀 **오버레이 비교** 모드.
5. **srcdoc 이스케이프 책임 오배정**: HTML 속성 이스케이프는 `safe_js_literal`(JS 리터럴용)로 못 덮음 — 별도 attribute-escape + 중첩 `<html>` single-root 검증 필요.