# 실전 게시 인사이트 (2026-06-11, report-archive v0.25.0 / graph-skill 0.42.1)

리포트 **#54** "graph-skill 실전 임베드 검증 — 96종/0.42.0 쇼케이스"(개인 공간, 8개 임베드: bode ·
work-plan · gantt · sankey · bubble-timeline · design-state-compare · mesh-result-3d · stat-card)를
실제 report-archive에 게시하고 실 Chromium으로 검사한 결과. 검사 스크립트: `tests/verify_publish.py`.

## ✅ 검증된 것 (전 항목 통과)

| 검증 | 결과 |
|---|---|
| 업로드 사슬 | embed_block(local_path)→file_id 자동 업로드, **785KB 3D 포함 8/8 성공** |
| 임베드 렌더 | 8/8 카드 렌더(캡션+전체화면 버튼), 부모 콘솔 에러 0 |
| **sandbox 동작** | `sandbox="allow-scripts"` srcdoc iframe에서 **전 기능 동작** — self-contained 설계 입증 |
| **Ctrl+휠 줌** | 모달 iframe **안에서** 줌 동작(픽셀 diff 검증) — P0 휠 게이트가 실환경에서 정상 |
| **WebGL orbit** | 3D 드래그 회전 동작(픽셀 diff 검증) |
| 컴포지트 | work-plan(3엔진: 개요+KPI 카드+Gantt 오늘선/의존/진척) 모달에서 완벽 렌더 |
| 애니메이션 | stat-card 카운트업·스파크라인 라이브 동작 |

## 🔎 플랫폼 동작의 발견 (설계 가정과 달랐던 것)

1. **html_embed는 인라인 iframe이 아니다** — 본문에는 placeholder(파일 아이콘+캡션+전체화면 버튼)로
   렌더되고, **전체화면 클릭 시에만** 모달 iframe으로 라이브 렌더된다(v0.25.0 기준).
   → 함의: ① `recommended_height_px`는 현 버전에서 모달(~화면 높이)에 영향이 적음.
   ② **캡션이 placeholder의 전부** — 캡션 품질(무엇을 보여주는 그래프인지+조작 힌트)이 매우 중요.
   ③ 그래프는 "작은 인라인"이 아니라 **큰 모달 크기에서 좋아 보여야** 한다.
2. **view URL 구조**: 실제 경로는 `/w/<workspace>/reports/<id>` (예: /w/personal-3/reports/54).
   CLI가 출력하는 `:3001/reports/<id>`를 직접 열면 "페이지를 찾을 수 없습니다" — receiver 측 개선 후보.
3. **템플릿 웜업**: 첫 열람 직후 잠시 본문이 "템플릿 불러오는 중…"에서 멈출 수 있음(재방문 시 정상).
   진단 시 오판 주의(이번에 이분 진단까지 갔던 원인).

## 🐛 실전이 잡은 graph-skill 버그/개선 (모두 수정 반영, 0.42.1)

| # | 발견 | 수정 |
|---|---|---|
| 1 | `embed_block` 산출에 `id` 없음 → report-write extra_blocks가 거부 | builder.embed_block이 `graph-<stem>` id 자동 생성 |
| 2 | **bode 모달 툴팁: 우축 시리즈 "Phase: -90 dB"** — 좌축 단위가 전 시리즈에 부착 | xy-core 툴팁이 `axis:"right"` 시리즈에 `axes.y2.unit` 사용 (1.8.1) |
| 3 | **gauge-core 타이틀이 카드 라벨과 겹침**(stat-card 모달에서 확인) | 그리드가 타이틀/툴바 높이(34px)를 상단 예약 (0.2.1) |
| 4 | `.env` 이원화 함정 — CLI는 `%LOCALAPPDATA%\report-skill\.env`(koo.park), `d:\report-skill\.env`는 별도 봇 계정 | 문서화(이 파일). 자동화 시 반드시 LOCALAPPDATA 쪽 사용 |

## 📋 백로그 (다음 차수)

- **mesh-result-3d 정점색이 조명에 묻혀 어두움** — CAE 컨투어는 관례상 unlit. 색 mesh에
  unlit(or emissive=vertexColor) 재질 옵션 검토(시각 영향 커서 별도 차수).
- 모달 높이(~840px)에서 stat-card 등 고정 비율 콘텐츠의 과신장 — kind별 콘텐츠 max-height 검토.
- receiver: view URL을 워크스페이스 포함 경로로 출력.

## 🧪 LLM 블라인드 사용성 테스트 (동일 차수 실행, 10 시나리오)

SKILL.md+도구만으로(소스 열람 금지) 자연어 과제 수행: **타입 선택 10/10 · validate/render/lint 10/10,
추정값 렌더 0건**(s1에서 A0/L0 게이트가 렌더를 차단하고 질문 → 설계 의도 입증).
마찰 3계열을 hint에 반영(0.42.1): ① 참조형/생략형 hint 자체완결화(work-plan tasks 필드,
design-state skeleton, radial-progress items 키), ② stress-strain **escape hatch**(이미 σ-ε면
base-xy 안내 — hint/ask/use_when 3곳), ③ 암묵 규약 명시(FFT zero-padding, bubble size 자동 정규화,
capability target 기본값, point-cloud `z`=컬러바 메타 + `scalar_meta` alias, sankey 단위 표기법,
SKILL.md에 비-MCP python API 매핑).
