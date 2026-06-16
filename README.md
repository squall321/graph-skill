# graph-skill

**LLM 스킬로 구동되는 self-contained 인터랙티브 HTML 그래프 생성기.**
데이터 + 축 메타(+필요 시 물리 배경값)를 받아 **외부 의존 0, 바이트 결정적**인 단일 `.html`
아티팩트를 만든다. report-archive 등 `html_embed` 기반 사이트에 그대로 게시한다.

핵심 원칙: **LLM은 차트 코드를 쓰지 않는다.** 렌더 엔진·인터랙션은 버전관리된 고정 자산이고,
LLM의 일은 (a) 데이터 수집 (b) 축·배경값 확인(부족하면 *질문* — 추측 금지) (c) 타입 선택
(d) 렌더 호출뿐이다. 같은 입력이면 항상 같은 고품질 인터랙션이 나온다.

## 현재 규모 — v0.45.0

- **167 그래프 타입 / 8 엔진 패밀리(+linked-view 버스) / 19 분류 카테고리**
- 엔진: `xy-core`(Canvas 2D, 113 타입·플러그인 25종, grouped/stacked 막대·콤보·T1/T2 정형 판정그림 포함) · `field-core`(컨투어/히트맵 + 오버레이 레이어: 효율맵·오더맵·아이마스크) · `polar-core` · `smith-core`
  · `review-matrix`(DOM 표·셀=값/상태/heat/bar/그래프/이미지) · `flow-core`(순서도·sankey·network
  ·chord·sunburst) · `gauge-core`(게이지·마진·카드) · `cad3d-core`(WebGL, three.js 벤더링)
  · linked-view 플러그인 버스(focus+context·공유 크로스헤어·SPLOM 브러싱)
- 도메인 정형 플롯: E-CAE(SRS·EMI·Zth·PDN·온도사이클·spec-margin·derating·배터리),
  구조·열·측정(격자수렴 GCI·응력선형화·이력곡선·열응답 τ·Nu-Re·FRF+coherence·Allan·교정),
  디스플레이·음향·RF·재료(CIE 색역·1/3옥타브·VSWR·DMA·모터 T-N·토네이도),
  일정/계획(간트·타임라인·업무계획서), **컴포지트**(work-plan·test-report — 멀티엔진 1파일)
- 자동 인터랙션: 호버/크로스헤어/툴팁/HUD, Ctrl+휠 줌(임베드 스크롤 통과)·핀치·키보드,
  로그 토글, 범례 isolate, 다크모드(+부모 postMessage 동기화), PNG/CSV/source 내보내기,
  LTTB 자동 다운샘플, 도움말(?) 오버레이, 접근성(aria/focus-visible/reduced-motion)

## 사용 (LLM 스킬 / 도구)

`.claude/skills/graph-skill/SKILL.md`가 LLM-facing 계약(SSOT)이다. 도구 흐름:

```text
graph_types_list / graph_find  →  graph_schema_get(hint=입력 키 SSOT)
  →  graph_validate_inputs (missing이면 렌더 금지, 사용자에게 질문)
  →  graph_render  →  graph_lint_output  →  graph_embed_block (report-write 게시)
```

데이터 인입 보조: `ingest_csv`(장비 CSV/TSV), `ingest_s2p`(Touchstone S-파라미터),
`resample`, `smooth`.

Python 직접 호출:

```python
from graph_skill import tools
tools.types_find("낙하 충격")                     # → srs-spectrum …
tools.render_payload("gantt-chart", payload, out_path="out.html")
```

## 웹 / 원격 MCP 서빙

`graph_skill.server`가 **단일 ASGI 앱**으로 세 표면을 한 배포에 노출한다(코어 `tools.DISPATCH`·
엔진 자산·결정성·self-contained 게이트는 무수정 재사용). 전송·아티팩트 서빙·보안만 이 레이어에 있다.

```bash
pip install -e ".[postprocess,cad3d,web]"
graph-skill-web                       # uvicorn 기동 (GRAPH_HOST/GRAPH_PORT)
```

| 엔드포인트 | 용도 |
| --- | --- |
| `POST /v1/render` | 렌더 → **콘텐츠주소 아티팩트**. `{hash, artifact_url, lint, ...}` 반환(배경값 부족 시 422 `needs_input`) |
| `GET /artifacts/<sha256>` | self-contained HTML 서빙(immutable 캐시 + CSP). 산출이 바이트결정적이라 hash가 자연 캐시키 |
| `POST /v1/lint` · `/v1/embed` | 저장된 아티팩트(hash)에 대한 lint / report-write 조각 |
| `POST /v1/<tool>` | 순수 도구 passthrough(types/find/schema/validate/ingest_csv/ingest_s2p/resample/smooth) |
| `/mcp` | **원격 MCP**(Streamable HTTP). 로컬 stdio MCP(`graph-skill-mcp`)는 그대로 유지 |

보안(env-gated): `GRAPH_API_KEY`(Bearer/X-API-Key) · `GRAPH_MAX_BODY` · `GRAPH_RATE_RPS` ·
`GRAPH_ARTIFACT_DIR`(디스크 영속). `needs_input` 게이트는 서버가 절대 우회하지 않는다(NEVER-invent).
P2(인프라): 오브젝트스토리지/CDN, OAuth, cad3d 워커 격리, report-archive file_id 연동.

## 개발

```bash
pip install -e ".[postprocess,cad3d,test]"
python -m playwright install chromium

python build_gallery.py     # graph-out/gallery — 엔진 버전 범프 시 필수(신선도 게이트)
pytest tests/ -q            # 465+ tests (수치 검증·게이트·결정성·실브라우저 시각·웹/MCP 서빙; optional deps 없으면 일부 skip)
for f in tests/node_*.mjs; do node "$f"; done
python tests/playwright_smoke.py   # 119/119 실 Chromium 부팅+무에러 스모크
```

검증 4층: ① Python(결정성·lint·NEVER-invent 게이트) ② Node(헤드리스 엔진 실행)
③ **실 Chromium**(전 타입 부팅·콘솔 0에러·인터랙션 픽셀 검증 verify_ux_p0/p1/p2)
④ 갤러리 신선도 CI 게이트. CI: `.github/workflows/ci.yml`.

## 문서

- [docs/UX-ROADMAP.md](docs/UX-ROADMAP.md) — UX 감사(73건)→로드맵 30건 전체 구현 기록
- [docs/PUBLISH-INSIGHTS.md](docs/PUBLISH-INSIGHTS.md) — report-archive 실전 게시 검증/인사이트
- [docs/DYNAMIC-VIZ-IDEAS.md](docs/DYNAMIC-VIZ-IDEAS.md) — 표현법 백로그
- [CHANGELOG.md](CHANGELOG.md)
