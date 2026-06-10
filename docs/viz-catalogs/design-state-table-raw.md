I now have the complete, real architecture. I have everything needed to design the meta-artifact family precisely on top of the actual wiring (catalog block schema, engine-family dispatch via `window.GraphEngines[family]`, plugin composition, validate gate with `requires[]`, deterministic `safe_js_literal` serializer, self-contained lint gate, and the report-write `html_embed`/file-upload/bundle contract). Here is the full design.

---

# design-state review/comparison matrix — 메타-아티팩트 패밀리 상세 설계

이것은 graph-skill 위에 얹는 **새 engine family `matrix-grid`** 와, 그 위에서 다른 graph-skill 아티팩트(특히 `xy-core` 산출물)를 **셀로 합성**하는 메타-아티팩트 패밀리다. PPT의 "설계 state 점검표"를 인터랙티브 self-contained HTML로 만든다.

핵심 한 줄: **`matrix-grid` 엔진은 "셀 렌더러 + 표 인터랙션"만 책임지고, 그래프 셀은 기존 `xy-core` 엔진을 같은 문서 안에서 재호출(in-document re-instantiation)한다.** 새 차트 코드를 쓰지 않는다 — 기존 `window.GraphEngines["xy-core"]` 를 셀 컨테이너에 마운트할 뿐이다.

---

## A. cataloger 출력 표 (요구된 컬럼 규약)

이 패밀리에 속하는 artifact-type 들. `extends` 는 class 상속이 아니라 plugin 합성(catalog `_chain` parent→child 누적)이며, 모든 타입의 **engine family = `matrix-grid`**.

| type-id(kebab) | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `review-matrix` | 설계 검토 매트릭스(기본) | 범용 점검표/리뷰표 | 열=state/버전 | 행=점검항목 | state별 항목값(텍스트·수치·상태·링크) 격자 | `states[]`(최소 1열 라벨), `items[]`(group·label·type) | (없음, 루트) | `cell-status`, `cell-text`, `cell-number` | `embed-index`(JSON 라운드트립 인덱스 임베드) | matrix-grid | 낮음 |
| `design-state-compare` | 설계 state 비교표 | MCAE/ECAE 설계안 A/B/C 비교 | 열=설계 state(≥2) | 행=점검항목 | 다열 비교 + state간 diff 하이라이트 | `states[]`(≥2), `items[]`, `spec`(항목별 threshold/판정 기준) | `review-matrix` | + `diff-highlight`, `cell-status`(spec 판정) | + `spec-evaluate` | matrix-grid | 중 |
| `single-state-checklist` | 단일 state 점검표 | 하나의 설계안 항목별 합격/불합 | 열=1(현재 state) | 행=점검항목 | 단일 열 점검(비교표의 특수형 N=1) | `states[]`(=1), `items[]`, `spec` | `design-state-compare` | (diff 비활성, 단일열 레이아웃) | `spec-evaluate` | matrix-grid | 낮음 |
| `cae-correlation-matrix` | CAE-시험 상관 매트릭스 | CAE vs 시험 항목별 상관/오차 | 열=CAE/Test/Δ/판정 | 행=계측·응답 항목 | 모델별 CAE-test 오차%·상관계수·판정 배지 | `states[]`(CAE·Test 쌍), `items[]`, `spec.error_pct`(허용오차) | `design-state-compare` | + `cell-graph`(상관 산점도 임베드), `delta-column`(자동 Δ열) | + `correlation-stat`(Δ%·R² 계산) | matrix-grid | 중상 |
| `doe-tradeoff-matrix` | DOE 트레이드오프 매트릭스 | DOE run/설계안 다목적 비교 | 열=run/factor 조합 | 행=반응(response)·KPI | run별 반응값 + 목표대비 색스케일(heat) | `states[]`(run), `items[]`(response+goal: max/min/target), `spec.targets` | `design-state-compare` | + `heat-cell`(값→색), `pareto-flag`(비지배 표시) | + `pareto-rank` | matrix-grid | 상 |
| `multiphysics-summary-matrix` | 멀티피직스 요약 매트릭스 | 구조·열·낙하·EMI 통합 점검 | 열=설계 state | 행=물리도메인 그룹 항목 | 도메인 그룹별 KPI + 그래프/이미지 혼합 셀 | `states[]`, `items[]`(group=물리도메인), `spec` | `design-state-compare` | + `cell-graph`, `cell-image`, `group-collapse-default` | `spec-evaluate` | matrix-grid | 상 |
| `gate-review-scorecard` | 게이트 리뷰 스코어카드 | DR/게이트 통과 판정표 | 열=게이트 기준 | 행=설계 항목 | 항목×기준 통과율 + 종합 배지 + 가중치 | `states[]`(기준), `items[]`, `spec`, `weights`(항목 가중치) | `design-state-compare` | + `score-rollup`(가중 합산), `verdict-badge` | + `score-rollup` | matrix-grid | 중 |
| `bom-variant-matrix` | 부품/변형 비교 매트릭스 | 모델 변형(variant) 부품·물성 비교 | 열=variant/모델 | 행=부품·물성 항목 | variant별 부품·치수·물성, 변경분 diff | `states[]`(variant), `items[]` | `design-state-compare` | + `diff-highlight`, `cell-image`(부품 썸네일) | `embed-index` | matrix-grid | 중 |

표기: `states[]` = 열 정의(설계 state/버전/시나리오/run/CAE·Test), `items[]` = 행 정의(점검항목, group으로 카테고리화), `spec` = 항목별 threshold/판정 기준(없으면 validate가 질문).

---

## B. 도메인 특유 인터랙션 / 오버레이

`matrix-grid` 엔진이 **설정 없이 자동으로** 켜는 표 인터랙션(= `xy-core` 의 "자동 켜짐"에 대응):

- **검색/필터**: 항목 라벨·태그·셀 텍스트 전역 검색(상단 박스), group/카테고리 다중필터, 상태필터(pass/fail/warn만 보기), state(열) 필터.
- **정렬**: 행을 group 내 / 전역으로 정렬(label·특정 state 수치값·diff 크기·판정 우선). 헤더 클릭 토글(asc/desc/none).
- **행 접기/펼치기**: group 헤더 단위 collapse, 전체 펼침/접힘 토글. `group-collapse-default` plugin이 초기 접힘 그룹 지정.
- **state 열 토글/고정(freeze)**: 열 숨김/표시 체크박스, baseline 열 1개 sticky freeze(좌측 고정), 행 라벨 열 항상 freeze.
- **diff 하이라이트**(`diff-highlight`): baseline state 대비 값이 다른 셀에 색 배지(증가↑/감소↓/변경). 수치는 Δ·Δ% 툴팁, 텍스트는 added/removed/changed.
- **셀 확대(모달)**: 모든 셀 클릭→확대 모달.
  - 그래프 셀 → **인터랙티브 모달**: 셀 안의 작은 `xy-core` 인스턴스를 모달에서 풀사이즈로 재마운트(호버/줌/팬/로그토글/PNG·CSV export 전부 살아있음 — `xy-core` 자동 인터랙션 그대로).
  - 이미지 셀 → 라이트박스(핀치/휠 줌).
  - 수치/텍스트 셀 → spec·threshold·메타·diff 상세 패널.
- **spec 오버레이**(`spec-evaluate`/`cell-status`): 셀 값을 항목 spec(min/max/target/tol)과 비교해 pass/fail/warn 배지 자동 부여. 셀에 "값 / 기준" 동시표시 토글.
- **heat 오버레이**(`heat-cell`): 행별(반응별) min-max 정규화 색스케일(DOE/트레이드오프). 색맹 안전(Okabe-Ito 발산형) 사용.
- **다크모드**: auto/light/dark 토글(`xy-core` 와 공유 토큰). 그래프 셀의 테마도 동기 전파.
- **print-to-PPT 친화 모드**: "표 펼침 + 인터랙션 chrome 숨김 + 그래프 셀은 정적 스냅샷(canvas→고정 PNG)으로 평탄화 + 페이지 분할 힌트" 모드. report-write 의 `page_slide_guide`/`page_slide_ratio` 와 호환되도록 16:9 폭 가정 레이아웃. 브라우저 인쇄(@media print)에서 freeze/모달 비활성, 셀 전체 표시.
- **재편집 라운드트립**: `embed-index` plugin이 정규화된 데이터모델 JSON을 `<script type="application/json" id="matrix-source">` 로 인라인 → "Export source(JSON)" 버튼. 그 JSON을 그대로 `matrix_render` 에 재투입하면 동일 표 재생성(결정론).

---

## C. 새 엔진패밀리가 필요한 항목 (2D xy-core로 안 되는 것)

이 메타-패밀리 자체가 **`xy-core` 로 안 되는 신규 엔진패밀리 `matrix-grid`** 다(차트가 아니라 DOM 격자 + 셀 합성기). 그 외, 이 매트릭스의 **셀로 임베드될** 그래프 중 `xy-core`(Canvas 2D 단일 plot)로 표현 못 해 별도 패밀리가 필요한 것:

| 셀에 필요한 그래프 | 왜 xy-core 불가 | 필요한 엔진패밀리(후보) |
|---|---|---|
| 등고선/필드맵(응력·온도 분포) | 2D 스칼라장 색맵 | `field-2d`(Canvas/WebGL 히트·컨투어) |
| 벡터장(유동·자기장) | 화살표/스트림라인 | `field-2d` |
| 3D surface / CAE 단면 / STEP 뷰 | 3D 카메라·메시 | `cad-viewer`(three.js, 기존 로드맵) |
| polar / 방사(안테나 패턴, 진동 모드) | 극좌표계 | `polar-core` |
| Smith chart(RF 임피던스, ECAE) | 임피던스 곡선 좌표 | `smith-core` |
| eye-diagram / 신호 무결성(ECAE) | 다중 오버레이·밀도 | `signal-eye`(density Canvas) |
| 스펙트로그램/STFT | 2D 시간-주파수 밀도 | `field-2d` |
| Bode(2-pane mag/phase) | 듀얼 축 동기 패널 | `xy-core` 확장 plugin(`dual-pane`)로 가능 — 경계선 |

원칙: **매트릭스는 셀의 엔진패밀리를 모른다.** 셀은 `{kind:"graph", graph_ref:{type, payload}}` 로만 선언되고, 빌드 시 각 graph_ref를 해당 패밀리로 렌더해 임베드한다. 따라서 `field-2d`/`polar-core`/`smith-core` 가 추가되면 매트릭스 코드 변경 없이 그 산출을 셀로 받아들인다(합성 아키텍처 D 참조).

---

## D. 합성 아키텍처 — 그래프 아티팩트를 "셀로" 합성하는 법

### D.1 엔진패밀리 분해 (catalog/플러그인/파일 매핑)

`matrix-grid` 는 기존 `xy-core` 와 동급의 새 engine family. 기존 `assets.py` 의 `data/engines/<engine>/` 규약에 그대로 올라간다.

```
src/graph_skill/
  data/
    catalog/types.json                      # ← matrix-* 블록 8개 추가 (B절 표)
    engines/
      xy-core/        (기존)
      matrix-grid/                           # ← 새 엔진패밀리
        ENGINE_VERSION                       # "0.1.0"
        engine.css                           # 격자/freeze/배지/모달 스타일
        engine.js                            # window.GraphEngines["matrix-grid"] 팩토리
        plugins/
          cell-status.js        # spec→pass/fail/warn 배지 셀
          cell-text.js          # 텍스트/링크 셀
          cell-number.js        # 수치(단위·유효숫자) 셀
          cell-graph.js         # ★ 그래프 셀: xy-core 재마운트 (핵심)
          cell-image.js         # 이미지 셀(base64/번들 ref)
          diff-highlight.js     # baseline 대비 diff
          spec-evaluate.js      # spec 판정 로직(클라 측 표시)
          heat-cell.js          # 값→색 스케일
          delta-column.js       # 자동 Δ열
          pareto-flag.js        # 비지배 표시
          score-rollup.js       # 가중 점수 합산
          verdict-badge.js      # 종합 판정
          group-collapse.js     # 초기 접힘 그룹
          embed-index.js        # source JSON 인라인 + export
  recipes/
    matrix_review.py            # review-matrix normalize (states/items/cells 정규화)
    matrix_compare.py           # design-state-compare (diff/spec 전처리)
    matrix_correlation.py       # cae-correlation (Δ/R² 계산 = post)
    matrix_doe.py               # doe-tradeoff (pareto rank = post)
  tools.py                      # matrix_* 도구(or graph_* 확장) — D.5
```

`boot.js` 는 **무변경**. 이미 `registry[cfg.engine]` 로 디스패치하므로 `cfg.engine:"matrix-grid"` 면 `window.GraphEngines["matrix-grid"]` 팩토리가 잡힌다. 팩토리는 `inst.use(plugin)`, `inst.setAssets({states,items,cells,spec,...})`, `inst.autoFit()` 인터페이스(기존 boot 계약)만 구현하면 된다.

### D.2 그래프 셀 임베드 — 3가지 모드 결정 (결정론·self-contained 유지)

셀 그래프를 문서에 넣는 방법 3가지를 검토하고 **모드별로 다르게 채택**:

| 방식 | 동작 | 장점 | 단점 | 채택 |
|---|---|---|---|---|
| **(1) inline re-instantiation (기본)** | graph_ref의 정규화 payload를 매트릭스 config에 그대로 담고, `cell-graph` plugin이 셀 div에 `window.GraphEngines["xy-core"](div, options)` 를 직접 마운트 | 단일 엔진 번들 1회 로드로 N개 그래프 셀 공유(중복 0), 모달 확대 시 같은 데이터 재마운트만 하면 됨, 완전 결정론, **셀당 추가 바이트 = 데이터뿐** | 셀 엔진패밀리가 매트릭스 문서에 포함돼야 함(xy-core js를 같이 번들) | **★ 동일 엔진패밀리(xy-core) 셀에 채택** |
| **(2) iframe srcdoc (격리)** | 각 그래프를 독립 self-contained HTML로 렌더 → 그 문자열을 `iframe.srcdoc` 으로 셀에 주입 | 엔진패밀리 혼용(field-2d/polar 등)에도 충돌 0, CSS/전역 격리 | 셀마다 엔진 번들 중복 → 바이트 폭발, 모달 확대 시 srcdoc 재파싱, 입력 경계 escape 주의 | **이종 엔진패밀리 셀(field-2d/polar/smith)에 채택** — 혼용 안전 우선 |
| **(3) 썸네일 PNG + 클릭 확대** | 셀에는 정적 PNG(엔진의 PNG export 결과)만, 클릭 시 (1) 또는 (2)로 인터랙티브 모달 마운트 | 초기 렌더 가벼움, print-to-PPT에 그대로 평탄화 | 인라인 PNG가 base64로 무거움 | **print 모드 / 셀 수 매우 많을 때 fallback** |

**결정 규칙(빌드 시 자동)**:
- 모든 그래프 셀이 `xy-core` 한 패밀리 → 모드(1). 엔진 js 1벌만 번들, 셀은 데이터 payload만.
- 그래프 셀에 이종 패밀리 혼재 → 그 셀만 모드(2) srcdoc(해당 패밀리 번들 포함), 동일 패밀리는 (1).
- `print_mode=true` 또는 그래프 셀 > N(기본 40) → 모드(3) 썸네일, 모달에서 (1)/(2).

self-contained 보장: 어느 모드든 산출 HTML은 외부 URL 0. 모드(2) srcdoc 내부도 각 그래프가 이미 `lint_self_contained` 통과한 self-contained 문서. 최종 매트릭스 HTML도 동일 `serialize.lint_self_contained` 게이트를 통과해야 게시 가능. srcdoc 주입은 `safe_js_literal` 의 `<`/`` ` ``/U+2028 이스케이프로 경계 깨짐 방지(이미 구현됨).

### D.3 합성 데이터 흐름 (build 시)

```
matrix payload (states, items, cells[].graph_ref{type,payload})
        │
   matrix_*.normalize()  ──► 각 graph_ref 를 그 타입의 recipe.normalize 로 정규화
        │                     (xy-core 면 base_xy.normalize → {assets.series, options.axes})
        │                     ※ 그래프도 자체 validate.check 통과해야 함(축/단위 누락 시 매트릭스 validate가 함께 질문)
   assemble():
     - engine.js = matrix-grid
     - 셀에 xy-core 그래프가 있으면 → xy-core engine.js + 필요한 xy plugin 도 함께 번들(중복 제거)
     - config.assets = {states, items, cells, spec, graph_payloads{cellId: 정규화된 xy config}}
     - safe_js_literal 로 인라인
        │
   lint_self_contained  ──►  out .html
```

즉 매트릭스 빌더는 **다른 타입의 recipe를 재사용**해 셀 그래프를 정규화한다(코드 중복 0). `cell-graph.js` 는 런타임에 `config.assets.graph_payloads[cellId]` 를 꺼내 `GraphEngines["xy-core"](cellDiv, payload.options)` + `inst.setAssets(payload.assets)` 로 마운트 — boot.js가 최상위에서 하는 일과 동일한 절차를 셀 단위로 반복.

### D.4 이미지 셀 (base64 인라인 vs 번들)

`xy-core` PNG export·report-write `files upload`/`html_embed` 규약에 맞춤:

- **작은 이미지(합계 ≤ ~1.5MB, 셀당 ≤ ~200KB)**: base64 data-URI 인라인. 완전 self-contained, 단일 .html. `cell-image.js` 가 `<img src="data:...">`.
- **큰 이미지 다수 / 합계 초과**: **번들 모드**. 산출이 .html + `assets/` 디렉터리(이미지 파일들) 묶음. 매트릭스는 상대경로 참조 → 단, 이는 self-contained 위반이므로 report-write 게시는 **bundle 업로드 경로**로(아래 G). 인라인 한계 초과를 빌더가 감지하면 자동 번들 전환 + `bundle:true` 플래그 반환.
- data-URI는 `lint_self_contained` 의 `(?:src|href)=//` 패턴에 안 걸림(외부 URL 아님) → 인라인 모드는 게이트 통과. 번들 모드는 게이트가 외부참조로 잡으므로 게시 계약을 bundle로 전환.

### D.5 도구(tool) 표면 — 기존 grammar에 합류

기존 `graph_*` 6도구 패턴을 그대로 따른다(3-view 골든 규칙). 두 가지 선택지 중 **A안(동일 도구 확장)** 권장: `matrix-*` 도 `graph_type` 일 뿐이므로 `graph_types_list/schema_get/validate_inputs/render/lint_output/embed_block` 가 그대로 처리. 입력 스키마만 `series/axes` 외에 `states/items/spec` 을 받도록 `_PAYLOAD_PROPS` 확장(matrix 타입일 때만 required).

- `graph_validate_inputs(graph_type:"design-state-compare", states, items, spec)` → states/items/spec/각 그래프 셀의 축·단위 누락을 한 번에 `missing[]` 로 수집.
- `graph_render` → 단일 self-contained 매트릭스 .html(+ 필요 시 bundle).
- `graph_embed_block` → `html_embed` 조각(또는 bundle 조각).

별도 도구가 필요한 단 하나: **`matrix_attach_graph`**(선택) — 이미 렌더된 graph .html 경로/또는 graph payload를 특정 `cells[itemId][stateId]` 에 끼워넣는 헬퍼(편의용, 없어도 됨).

---

## E. requires (validate 게이트가 물을 것)

validate.check 의 `requires[]`(catalog 블록의 requires) + 매트릭스 전용 게이트 로직. 누락 시 `missing[].ask` 로 질문(NEVER invent — 기존 규칙 동일):

| 누락 항목 | why | ask(질문 문구 예) |
|---|---|---|
| `states[]` 비었음/라벨 없음 | 비교할 열(설계 state)이 정의 안 됨 | "비교할 설계 state(열)들을 알려주세요. 각 state의 라벨/버전/시나리오 이름은? (단일 점검표면 state 1개)" |
| `states` 1개인데 타입이 `design-state-compare` | 비교표인데 비교대상 부족 | "비교표는 state가 2개 이상 필요합니다. 추가 state를 주시거나 `single-state-checklist` 로 전환할까요?" |
| `items[]` 비었음 | 점검할 행(항목)이 없음 | "점검 항목(행)들을 알려주세요. 각 항목의 그룹/라벨/단위/타입(수치·상태·그래프·이미지·텍스트)은?" |
| `spec`/threshold 누락(타입이 spec 요구) | pass/fail 판정 기준 없음 → 배지 못 만듦 | "각 항목의 합격 기준(min/max/target/허용오차)을 알려주세요. 기준이 없으면 상태 배지 없이 값만 표시할까요?" |
| `baseline` state 미지정(diff 타입) | diff 기준열 모호 | "diff 비교의 기준(baseline) state는 어느 것인가요? (예: 'AS-IS' 또는 'v1')" |
| **그래프 셀의 축/단위 누락** | 셀 그래프가 xy-core인데 축 미상 | (xy-core validate가 던지는 그대로) "○○ 항목 그래프의 x/y축 물리량·단위는?" |
| `cae-correlation` 의 `spec.error_pct` | 허용오차 기준 없음 | "CAE-시험 상관의 허용오차(%)와 판정 기준(R² 하한 등)은?" |
| `doe-tradeoff` 의 `targets`(goal/방향) | 반응별 최대/최소/목표 미상 → heat·pareto 불가 | "각 반응(KPI)의 목표 방향(max/min/target)과 목표값을 알려주세요." |

게이트는 매트릭스 누락 + **모든 그래프 셀의 하위 validate를 재귀 수집**해 한 번에 질문(왕복 최소화). 추정값으로 판정 배지를 다는 것은 "자신있게 틀린" 최악 — 금지.

---

## F. report-write 게시

- **기본(인라인 모드)**: 산출은 단일 self-contained .html → **`html_embed` 단일 블록으로 충분**. `graph_embed_block(html_path, height_px)` → report-write draft `extra_blocks` 에 추가(local_path→file_id 자동 업로드, sandbox iframe). 매트릭스는 높이가 크므로 `height_px` 권장값을 행수 기반으로 산출(예: header 80 + 행수×34, clamp 60–4000). 모든 그래프 셀이 한 문서 안에 살아있어 iframe 안에서 그대로 인터랙티브.
- **큰 이미지 다수(번들 모드)**: 단일 html_embed로 self-contained 불가 → **bundle 게시**. 매트릭스 html + `assets/` 를 zip/디렉터리로 report-write `files upload` 후, 매트릭스가 `file_id` 들을 참조하도록 재작성하거나, report-write가 bundle을 호스팅. 빌더가 `bundle:true` 면 `graph_embed_block` 이 bundle 조각(여러 file_id)을 생성.
- **print-to-PPT**: 사용자가 PPT로 뽑을 거면 `print_mode` 산출(평탄화 PNG 셀 + 16:9 폭) → report-write `page_slide_guide:true`, `page_slide_ratio:"16:9"`, `page_blend_blocks:true` 와 함께 게시하면 슬라이드 그리드에 정렬.
- lint 게이트: 게시 전 `graph_lint_output` 필수. 인라인 모드는 통과해야 게시. 번들 모드는 의도된 외부참조이므로 bundle 경로로 우회(게이트가 막지 않도록 bundle 플래그로 분기).

---

## G. "구조화 조회"용 내부 인덱스 / JSON 임베드 (재편집 라운드트립)

`embed-index` plugin(모든 매트릭스 타입의 post에 포함):

1. **source JSON 인라인**: 정규화된 데이터모델 전체(states/items/cells/spec/meta/graph_payloads)를 `<script type="application/json" id="matrix-source">…</script>` 로 임베드(`safe_js_literal` 로 안전 직렬화). → "Export source" 버튼이 이 JSON을 다운로드. 그 JSON을 `graph_render` 에 그대로 재투입하면 **byte-동일** 표 재생성(결정론, 기존 golden-test 규약과 동일).
2. **조회 인덱스**: 런타임에 빌드하는 역색인(검색·필터·정렬 가속) — `byGroup{group:[itemId]}`, `byStatus{pass/fail/warn:[cellId]}`, `byTag{tag:[itemId]}`, `byState{stateId:[cellId]}`, `diffSet{cellId:Δ}`. 검색박스/필터/정렬이 이 인덱스를 사용.
3. **round-trip 보장**: export한 JSON ↔ 재렌더가 결정론적이어야 하므로, normalize는 입력을 canonical form(정렬된 키, 정규화된 셀 kind)으로 고정. 재편집 시 사람이 JSON 일부만 고쳐 재투입 가능(예: 한 셀의 spec 변경 → 배지 재계산).

---

## H. 데이터 모델 — JSON 스케치 (요구된 정확한 형태)

```jsonc
{
  "graph_type": "design-state-compare",      // matrix-grid family
  "title": "HFP-X1 미드프레임 설계안 비교 (MCAE)",
  "meta": {
    "domain": "MCAE",                        // MCAE | ECAE | system | correlation | doe
    "model": "HFP-X1", "author": "...", "date": "2026-06-06",
    "baseline": "v1",                        // diff 기준 state id
    "source_records": ["DOC-HE-CAE-2026-0000000001"]  // aidatahub 출처(인용)
  },

  // ── 열: 설계 state / 버전 / 시나리오 / run / CAE·Test ─────────────
  "states": [
    { "id": "v1", "label": "AS-IS (v1)",   "tags": ["baseline"], "frozen": true },
    { "id": "v2", "label": "TO-BE (v2)",   "tags": ["candidate"] },
    { "id": "v3", "label": "TO-BE (v3)",   "tags": ["candidate"], "hidden_default": false }
  ],

  // ── 행: 점검 항목 (group=카테고리) ───────────────────────────────
  "items": [
    {
      "id": "drop_face",
      "group": "낙하(Drop)", "label": "Face drop 1.5m 최대응력",
      "unit": "MPa", "type": "number",
      "tags": ["safety", "structural"],
      "spec": { "max": 320, "warn_at": 300, "goal": "min" },   // ← threshold
      "cells": {                              // cells[stateId] → 셀
        "v1": { "kind": "number", "value": 341, "ref": "DOC-...§4" },
        "v2": { "kind": "number", "value": 298 },
        "v3": { "kind": "number", "value": 285 }
      }
    },
    {
      "id": "drop_curve",
      "group": "낙하(Drop)", "label": "충격 가속도 시간이력",
      "unit": "g", "type": "graph",
      "cells": {
        "v1": { "kind": "graph", "graph_ref": {        // ★ 그래프 셀
          "type": "base-xy",
          "payload": {                                  // 그대로 xy-core 입력
            "axes": { "x": {"label":"Time","unit":"ms"},
                      "y": {"label":"Accel","unit":"g"} },
            "series": [ {"name":"v1","data":[[0,0],[2,820],[4,310]]} ]
          }
        }},
        "v2": { "kind": "graph", "graph_ref": { "type":"base-xy",
          "payload": { "axes":{"x":{"label":"Time","unit":"ms"},"y":{"label":"Accel","unit":"g"}},
                       "series":[{"name":"v2","data":[[0,0],[2,610],[4,250]]}] } }}
      }
    },
    {
      "id": "rib_photo",
      "group": "구조(Structure)", "label": "리브 형상",
      "type": "image",
      "cells": {
        "v1": { "kind": "image", "image": { "mode":"inline",
                "mime":"image/png", "data":"<base64…>" } },
        "v2": { "kind": "image", "image": { "mode":"bundle",   // 큰 이미지
                "ref":"assets/rib_v2.png" } }
      }
    },
    {
      "id": "emi_pass",
      "group": "EMI/ECAE", "label": "방사 EMI 마진",
      "unit": "dB", "type": "number",
      "spec": { "min": 3, "goal": "max" },
      "cells": {
        "v1": { "kind": "status", "status": "fail", "value": 1.8 },
        "v2": { "kind": "status", "status": "warn", "value": 3.2 },
        "v3": { "kind": "status", "status": "pass", "value": 5.1,
                "link": { "href": "mention://report/137?ws=ecae", "text": "상세" } }
      }
    },
    {
      "id": "note",
      "group": "메타", "label": "설계 코멘트", "type": "text",
      "cells": {
        "v1": { "kind": "text", "value": "리브 보강 전" },
        "v2": { "kind": "text", "value": "리브 2개 추가" }
      }
    }
  ],

  // ── 항목 외부 공통 spec/가중치(타입별) ──────────────────────────
  "spec": {                                   // gate-review/doe 등에서 사용
    "targets": { "drop_face": {"max":320} },
    "error_pct": 10,                          // cae-correlation 허용오차
    "weights": { "drop_face": 0.4, "emi_pass": 0.6 }  // gate-review 가중
  },

  "options": {                                // 선택적 외형/거동 override
    "freeze_baseline": true, "diff": true, "heat": false,
    "collapsed_groups": ["메타"], "print_mode": false,
    "theme": "auto"
  },

  "out_path": "d:/.../graph-out/state-compare.html"
}
```

런타임에 각 `cells[state]` 는 다음 **셀 kind 합집합** 중 하나로 정규화된다:
`{kind:"number", value, unit?, ref?}` / `{kind:"status", status:"pass|fail|warn", value?, reason?}` / `{kind:"text", value, link?}` / `{kind:"graph", graph_ref:{type,payload}}`(→정규화 시 `graph_payloads[cellId]` 로 분리) / `{kind:"image", image:{mode:"inline",mime,data} | {mode:"bundle",ref}}` / `{kind:"link", href, text}` / `{kind:"empty"}`.

---

## I. 파일/타입 매핑 요약 (한눈에)

| 신규 산출물 | 위치 | 역할 |
|---|---|---|
| catalog 블록 8개 | `data/catalog/types.json` | matrix-* 타입 선언(engine=matrix-grid, extends 체인, requires, options_defaults) |
| `matrix-grid` 엔진 | `data/engines/matrix-grid/{engine.js,engine.css,ENGINE_VERSION}` | `window.GraphEngines["matrix-grid"]` 팩토리 + 표 인터랙션 |
| 14개 plugin | `data/engines/matrix-grid/plugins/*.js` | cell-graph(★ xy-core 재마운트), cell-image, diff-highlight, spec-evaluate, heat-cell, embed-index … |
| recipes 4개 | `recipes/matrix_*.py` | states/items/cells 정규화 + 그래프 셀은 **하위 타입 recipe 재사용** + post(Δ/R²/pareto/score) |
| 도구 | `tools.py` `_PAYLOAD_PROPS` 확장 | 기존 `graph_*` 6도구가 matrix 타입도 처리(states/items/spec 추가) |
| boot/serialize/builder/validate/catalog | **무변경** | 엔진-패밀리 디스패치·lint·extends·safe_js_literal 가 이미 일반화돼 그대로 수용 |

핵심 결론: 이 패밀리는 graph-skill의 기존 불변식(engine family 디스패치, plugin 합성 상속, validate-게이트 NEVER-invent, deterministic safe_js_literal, self-contained lint, html_embed/bundle 게시)을 **하나도 깨지 않고** 위에 얹힌다. 새로운 점은 단 하나 — **셀이 다른 graph artifact를 재귀적으로 품는 메타-아티팩트**라는 것, 그리고 그 합성을 "동일 패밀리=inline 재마운트 / 이종 패밀리=iframe srcdoc / print·대량=썸네일+모달" 3모드로 결정론적·self-contained하게 처리한다는 것이다.

참고한 실제 소스 경로(load-bearing): `d:/graph-skill/src/graph_skill/data/catalog/types.json`(catalog 블록 형식), `d:/graph-skill/src/graph_skill/catalog.py`(extends `_chain` 누적), `d:/graph-skill/src/graph_skill/data/shell/boot.js`(엔진-패밀리 디스패치 `registry[cfg.engine]`·`inst.use/setAssets/autoFit` 계약), `d:/graph-skill/src/graph_skill/serialize.py`(`safe_js_literal` 경계 이스케이프·`lint_self_contained`), `d:/graph-skill/src/graph_skill/validate.py`(requires→missing 게이트), `d:/graph-skill/src/graph_skill/builder.py`(assemble·render·embed_block), `d:/report-skill/.claude/skills/report-write/SKILL.md`(html_embed height 60–4000·file upload·bundle·page_slide 게시 계약).