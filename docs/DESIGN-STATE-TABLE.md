# 설계 state 점검/비교표 아티팩트 — `review-matrix` 패밀리

PPT에서 표로 만들던 "하나의 설계 state에 대한 항목별 점검표 / 여러 설계 state 비교표"를, **셀이 그래프·사진·값·상태·텍스트가 될 수 있고 구조화 조회가 되는 인터랙티브 단일 HTML**로 만드는 메타-아티팩트 패밀리.

> 한 줄 요약: **`review-matrix` 엔진은 "셀 렌더러 + 표 인터랙션"만 책임지고, 그래프 셀은 기존 graph-skill 엔진(`xy-core` 등)을 같은 문서 안에서 재마운트한다.** 새 차트 코드 0 — `window.GraphEngines[family]` 를 셀 div에 마운트할 뿐. graph-skill 의 기존 불변식(엔진-패밀리 디스패치·plugin 합성·validate 게이트·deterministic 직렬화·self-contained lint·html_embed 게시)을 하나도 깨지 않고 위에 얹힌다.

본 문서는 도메인 에이전트 원안(`docs/viz-catalogs/design-state-table-raw.md`)에 **완결성 비평(`_critique.md` §3)에서 발견된 결함을 반영**한 확정 설계다.

---

## 1. 타입(catalog 블록) — engine family = `review-matrix`

| type-id | 용도 | 핵심 plugin | requires(스칼라) | structural_requires |
|---|---|---|---|---|
| `review-matrix` | 범용 점검표(루트) | cell-status, cell-text, cell-number, embed-index | items[] | items≥1 |
| `single-state-checklist` | 단일 설계안 합격/불합 | + spec-evaluate | states(=1) | spec 형태검증 |
| `design-state-compare` | 설계 state A/B/C 비교 | + diff-highlight, cell-graph, cell-image | — | **states≥2**, **baseline∈states** |
| `cae-correlation-matrix` | CAE vs Test 항목별 상관/오차 | + cell-graph, delta-column | spec.error_pct | states=CAE·Test 쌍 |
| `doe-tradeoff-matrix` | DOE run 다목적 비교 | + heat-cell, pareto-flag | spec.targets | targets 방향(max/min/target) |
| `gate-review-scorecard` | 게이트 통과 판정표 | + score-rollup, verdict-badge | spec.weights | weights 합 |
| `bom-variant-matrix` | variant 부품/물성 비교 | + diff-highlight, cell-image | — | states≥2 |
| `multiphysics-summary-matrix` | 구조·열·낙하·EMI 통합 점검 | + cell-graph, cell-image, group-collapse | — | — |

`extends` 체인: `review-matrix` ← `design-state-compare` ← (correlation/doe/gate/bom/multiphysics). 단일열 `single-state-checklist` = 비교표의 N=1 특수형.

---

## 2. 데이터 모델 (정규화 형태)

```jsonc
{
  "graph_type": "design-state-compare",          // engine family = review-matrix
  "title": "HFP-X1 미드프레임 설계안 비교 (MCAE)",
  "meta": {
    "domain": "MCAE",
    "model": "HFP-X1", "baseline": "v1",          // diff 기준 state id (∈ states)
    "source_records": ["DOC-HE-CAE-2026-0000000001"]   // aidatahub 인용 출처
  },
  "states": [                                     // 열 = 설계 state/버전/시나리오/run/CAE·Test
    { "id": "v1", "label": "AS-IS (v1)", "tags": ["baseline"], "frozen": true },
    { "id": "v2", "label": "TO-BE (v2)", "tags": ["candidate"] },
    { "id": "v3", "label": "TO-BE (v3)", "tags": ["candidate"] }
  ],
  "items": [                                      // 행 = 점검 항목 (group=카테고리)
    { "id": "drop_face", "group": "낙하(Drop)", "label": "Face drop 1.5m 최대응력",
      "unit": "MPa", "type": "number", "tags": ["safety","structural"],
      "spec": { "max": 320, "warn_at": 300, "goal": "min" },
      "cells": {
        "v1": { "kind": "number", "value": 341, "ref": "DOC-...§4" },
        "v2": { "kind": "number", "value": 298 },
        "v3": { "kind": "number", "value": 285 }
      }
    },
    { "id": "drop_curve", "group": "낙하(Drop)", "label": "충격 가속도 시간이력",
      "unit": "g", "type": "graph",
      "overlay_states": true,                     // ★ 한 셀에 v1/v2/v3 겹쳐 비교 (비평 #D)
      "cells": {
        "v1": { "kind": "graph", "graph_ref": { "type": "base-xy",
          "payload": { "axes": {"x":{"label":"Time","unit":"ms"},"y":{"label":"Accel","unit":"g"}},
                       "series": [ {"name":"v1","data":[[0,0],[2,820],[4,310]]} ] } } },
        "v2": { "kind": "graph", "graph_ref": { "type":"base-xy",
          "payload": { "axes":{"x":{"label":"Time","unit":"ms"},"y":{"label":"Accel","unit":"g"}},
                       "series":[{"name":"v2","data":[[0,0],[2,610],[4,250]]}] } } }
      }
    },
    { "id": "rib_photo", "group": "구조(Structure)", "label": "리브 형상", "type": "image",
      "cells": {
        "v1": { "kind": "image", "image": { "mode":"inline", "mime":"image/png", "data":"<base64…>" } },
        "v2": { "kind": "image", "image": { "mode":"inline", "mime":"image/png", "data":"<base64…>" } }
      }
    },
    { "id": "emi_pass", "group": "EMI/ECAE", "label": "방사 EMI 마진",
      "unit": "dB", "type": "number", "spec": { "min": 3, "goal": "max" },
      "cells": {
        "v1": { "kind": "status", "status": "fail", "value": 1.8 },
        "v2": { "kind": "status", "status": "warn", "value": 3.2 },
        "v3": { "kind": "status", "status": "pass", "value": 5.1,
                "link": { "href": "mention://report/137?ws=ecae", "text": "상세" } }
      }
    },
    { "id": "note", "group": "메타", "label": "설계 코멘트", "type": "text",
      "cells": { "v1": { "kind": "text", "value": "리브 보강 전" },
                 "v2": { "kind": "text", "value": "리브 2개 추가" } } }
  ],
  "spec": { "targets": { "drop_face": {"max":320} }, "error_pct": 10,
            "weights": { "drop_face": 0.4, "emi_pass": 0.6 } },
  "options": { "freeze_baseline": true, "diff": true, "heat": false,
               "collapsed_groups": ["메타"], "print_mode": false, "theme": "auto" },
  "out_path": "d:/.../graph-out/state-compare.html"
}
```

**셀 kind 합집합**: `{kind:"number",value,unit?,ref?}` / `{kind:"status",status:"pass|fail|warn",value?,reason?}` / `{kind:"text",value,link?}` / `{kind:"graph",graph_ref:{type,payload}}` / `{kind:"image",image:{mode:"inline",mime,data}}` / `{kind:"link",href,text}` / `{kind:"empty"}`.

---

## 3. 자동 표 인터랙션 (`xy-core` 의 "자동 켜짐"에 대응 — 설정 불필요)

- **검색/필터**: 라벨·태그·셀 텍스트 전역 검색, group 다중필터, 상태필터(pass/fail/warn), state(열) 필터.
- **정렬**: 행을 label·특정 state 수치·diff 크기·판정 우선으로(헤더 클릭 asc/desc/none).
- **행 접기/펼치기**: group 단위 collapse, 전체 토글, 초기 접힘(`collapsed_groups`).
- **state 열 토글/고정**: 열 숨김/표시, baseline 1열 sticky freeze, 행 라벨 열 항상 freeze, **N>5 열은 가로 스크롤 + 열 페이지네이션**(비평 #D).
- **diff 하이라이트**: baseline 대비 셀 변경 배지(↑/↓/변경), 수치 Δ·Δ% 툴팁, 텍스트 added/removed/changed.
- **셀 확대(모달)**:
  - 그래프 셀 → **인터랙티브 모달**: 셀 안 미니 그래프를 모달에서 풀사이즈 재마운트(호버/줌/팬/로그토글/PNG·CSV 전부 살아있음).
  - 이미지 셀 → 라이트박스(휠/핀치 줌).
  - 수치/텍스트 셀 → spec·threshold·메타·diff·**출처(ref)** 상세 패널.
- **spec 오버레이**: 셀 값 vs spec(min/max/target/tol) → pass/fail/warn 배지, "값/기준" 동시표시 토글.
- **heat 오버레이**(DOE): 행별 min-max 정규화 색(색맹안전 발산형).
- **다크모드**: auto/light/dark, 그래프 셀 테마 동기.
- **그래프 셀 mini-mode**(비평 #A 갭): 작은 셀에서는 HUD/접선/범례를 자동 축약(스파크라인 모드), 모달에서 풀 인터랙션 복원. `xy-core` 에 `compact:true` 옵션 추가 필요.
- **print-to-PPT 모드**: 표 펼침 + chrome 숨김 + 그래프 셀 정적 PNG 평탄화 + 16:9 폭 가정. report-write `page_slide_guide`/`page_slide_ratio:"16:9"` 호환. `@media print` 에서 freeze/모달 비활성.

---

## 4. 그래프 셀 합성 — 임베드 모드

| 방식 | 동작 | 채택 |
|---|---|---|
| **(1) inline 재마운트** | graph_ref 정규화 payload를 매트릭스 config에 담고, `cell-graph` plugin이 셀 div에 `GraphEngines["xy-core"](div, options)` 직접 마운트 | **★ 동일 패밀리(xy-core) 셀 — 기본·MVP** (엔진 js 1벌만 번들, 셀당 추가 바이트=데이터뿐, 완전 결정론) |
| **(2) iframe srcdoc** | 각 그래프를 self-contained **fragment**(`<html>` 없이)로 렌더 → `iframe.srcdoc` 주입 | **이종 패밀리(field-core/polar-core/cad3d) 셀** — field/polar 패밀리가 생긴 뒤 도입. **HTML 속성 이스케이프**(`&`→`&amp;`,`"`→`&quot;`) 별도 필요(`safe_js_literal` 아님), 중첩 `<html>` 금지로 `single_root` lint 보호 (비평 #E) |
| **(3) 썸네일 PNG + 모달** | 셀=정적 PNG, 클릭 시 (1)/(2)로 모달 | print 모드 / 그래프 셀 > N(기본 40) fallback |

**빌드 시 자동 결정**: 전부 xy-core → (1). 이종 혼재 → 그 셀만 (2). `print_mode` 또는 셀 과다 → (3).

**합성 데이터 흐름**: 매트릭스 recipe가 각 `graph_ref` 를 **그 타입의 recipe.normalize 로 재사용** 정규화(코드 중복 0) → `config.assets.graph_payloads[cellId]` 로 분리 인라인. 각 그래프도 **자체 validate.check 통과해야** 함(축/단위 누락 시 매트릭스 validate가 함께 질문). `cell-graph.js` 가 런타임에 boot.js와 동일 절차를 셀 단위 반복.

**`overlay_states`(겹쳐 비교)**: `true` 면 한 항목의 모든 state graph_ref 를 **하나의 멀티시리즈 xy-core 그래프**(state당 시리즈 1개)로 병합 — 단순 멀티시리즈라 추가 엔진 불필요. 실무 1순위 비교 도시.

---

## 5. report-write 게시 — **인라인 단일 파일만** (비평 #B, 검증됨)

`html_embed` 는 단일 self-contained HTML 만 받는다(번들 위젯 없음). → **확정 제약:**

- 산출은 **외부참조 0 단일 `.html`**. `graph_lint_output` 통과해야 게시.
- 모든 그래프 셀 = inline 재마운트(데이터만 인라인). 모든 이미지 셀 = **base64 `data:` 인라인**(`data:` 는 lint 통과). 큰 이미지는 **빌더가 자동 다운스케일**(셀 표시 크기 기준) — "html + assets/ 번들" 경로는 폐기(report-write가 못 받음).
- 인라인 합계가 과대(예 >8MB)면 빌더가 **썸네일+모달(모드3)** 강제 + 경고. (원본 고해상 이미지가 꼭 필요하면 그 이미지만 report-write `image` 위젯으로 별도 블록 게시 — 매트릭스 밖.)
- `graph_embed_block(html_path, height_px)` → `extra_blocks` 의 `html_embed` 단일 블록(local_path→file_id 자동 업로드, sandbox iframe). `height_px` = header + 행수×행높이, 60–4000 clamp(초과 시 내부 스크롤).
- 매트릭스 HTML 내부에 그래프 `<html>` 을 품지 않음(inline 재마운트는 div 마운트라 `<html>` 없음) → `single_root` lint 안전.

---

## 6. 구조화 조회 / 재편집 라운드트립 (`embed-index` plugin)

1. **source JSON 인라인**: 정규화 데이터모델 전체를 `<script type="application/json" id="matrix-source">` 로 임베드(`safe_js_literal` 안전 직렬화) → "Export source" 버튼. 그 JSON을 `graph_render` 에 재투입 = **byte-동일** 재생성(결정론, golden 규약).
2. **조회 역색인**(런타임): `byGroup` · `byStatus` · `byTag` · `byState` · `diffSet{cellId:Δ}` · **`bySource{record_id:[cellId]}`**(출처 추적 — 비평 #C 갭 반영, 인용 무결성). 검색/필터/정렬이 이 인덱스 사용.
3. **재편집 검증 강제**: 수정된 JSON 재투입 시 validate 재실행(축 단위 삭제 등 requires 위반이면 렌더 차단). 정규화는 canonical form(정렬키)으로 고정.

> 미해결(향후): graph 셀은 정규화형으로 고정돼 raw 원본 역추적 불가(정규화 일방향). raw 재편집이 필요하면 source JSON에 `raw_ref` 보존 옵션 검토.

---

## 7. 파일/타입 매핑 — graph-skill 기존 골격에 합류

```
data/catalog/types.json                 # ← review-matrix 블록 8개 추가
data/engines/review-matrix/             # ← 새 엔진패밀리 (assets.py 규약 그대로)
  ENGINE_VERSION / engine.css / engine.js   # window.GraphEngines["review-matrix"] 팩토리
  plugins/  cell-status · cell-text · cell-number · cell-graph(★재마운트) · cell-image ·
            diff-highlight · spec-evaluate · heat-cell · delta-column · pareto-flag ·
            score-rollup · verdict-badge · group-collapse · embed-index
recipes/  matrix_review.py · matrix_compare.py · matrix_correlation.py · matrix_doe.py
tools.py  # _PAYLOAD_PROPS 에 states/items/spec 추가 (matrix 타입일 때 required)
validate.py  # structural_requires 훅 (states≥2 / baseline∈states / spec 다형태)
boot.js / serialize.py / builder.py / catalog.py   # ← 무변경 (이미 일반화됨)
```

- 도구: 기존 `graph_*` 6도구가 그대로 처리(3-view). `graph_validate_inputs(graph_type:"design-state-compare", states, items, spec)` 가 states/items/spec + **모든 그래프 셀의 하위 validate를 재귀 수집**해 한 번에 `missing[]` 질문(왕복 최소화).
- 선택 헬퍼 `matrix_attach_graph`(이미 렌더된 graph payload를 특정 셀에 끼움) — 없어도 됨.

**핵심 불변식 유지**: 엔진-패밀리 디스패치 · plugin 합성 상속 · validate NEVER-invent · deterministic `safe_js_literal` · self-contained lint · html_embed 게시 — 전부 그대로. 새로운 점은 **셀이 다른 graph 아티팩트를 재귀적으로 품는 메타-아티팩트**라는 것 하나뿐.

---

## 8. validate 게이트가 물을 것 (NEVER invent — 추정 배지 금지)

| 누락 | ask 예 |
|---|---|
| `states` 없음/라벨 없음 | "비교할 설계 state(열)들을 알려주세요. 각 라벨/버전/시나리오는? (단일 점검표면 1개)" |
| `states`=1 인데 비교표 | "비교표는 state ≥2 필요. 추가 state를 주시거나 single-state-checklist로 전환할까요?" |
| `items` 없음 | "점검 항목(행)들을? 각 항목의 그룹/라벨/단위/타입(수치·상태·그래프·이미지·텍스트)은?" |
| `spec` 누락(spec 요구 타입) | "각 항목 합격 기준(min/max/target/허용오차)은? 없으면 배지 없이 값만 표시할까요?" |
| `baseline` ∉ states | "diff 기준(baseline) state는 어느 것? (예: 'v1')" |
| 그래프 셀 축/단위 누락 | (xy-core validate 그대로) "○○ 항목 그래프의 x/y축 물리량·단위는?" |
| correlation `spec.error_pct` | "CAE-시험 허용오차(%)와 판정(R² 하한)은?" |
| doe `spec.targets` 방향 | "각 반응(KPI)의 목표 방향(max/min/target)과 목표값은?" |

게이트는 매트릭스 누락 + 모든 그래프 셀 하위 validate를 **재귀 수집**해 한 번에 질문. 추정값으로 pass/fail 배지를 다는 것은 "자신있게 틀린" 최악 — 금지.
