# UX 개선 로드맵 (감사 기반)

> 2026-06-10 멀티에이전트 전수 감사(7개 차원 × 코드+실 렌더 스크린샷, 91타입) — 원시 발견 73건 → 근본원인 병합 30건.
> **진행 상태: P0 12 + P1 11 + P2 7 — 로드맵 30건 전체 구현·검증 완료 (0.42.0).** 검증=verify_ux_p0(13)/p1(14)/p2(10) 실 Chromium 인터랙션 체크 + 갤러리 신선도 CI 게이트(test_ux_p2). 이연: 제목 좌상단 통일(시각 임팩트 커서 별도 차수), Barnes-Hut 대규모 네트워크, flowchart PNG(DOM 래스터화).
> 원시 데이터: `docs/_ux_audit_raw.json`. 감사 차원: xy 인터랙션 / DOM 엔진 / 시각 일관성 / 임베드 맥락 / 접근성·모션 / 견고성·성능 / LLM API 인체공학.

**요약:** 73건 감사 결과를 근본 원인 기준으로 병합해 30건으로 압축했다(주요 중복: flow-core 타이틀/툴바 겹침 6회, html/body 리셋 부재 3회, network 무한 시뮬 3회, 휠 트랩·sticky 헤더·embed 높이·모달 Esc·xy 좁은폭 겹침 각 2~3회 보고). '이상 없음' 확인 2건(다크 토큰 대비, 3D 로드/검색 성능)은 제외. 핵심 병합 근거는 소스에서 직접 재확인했다(flow-core engine.js:681의 bar.appendChild + engine.css:22 absolute, gauge-core css의 리셋 부재). P0 12건은 '임베드에서 즉시 보이는 깨짐 + S~M 국소 수정' — flow 타이틀 1줄 수정, flow/gauge CSS 리셋 2줄, Ctrl+휠 게이팅(유일 sev5 임베드 트랩), playback 4종 빈 화면(sev5)+캐리어 범례 묶음, review-matrix 셀 크기 폭발 CSS 오버라이드, 모달 Esc, network 시뮬 정지, _panned 1줄, embed_block 권장높이 연결, SKILL.md 현행화, tools.py 스키마 모순+hint 폴백(동일 파일 묶음), xy-core 오버레이 레이아웃 예약(6건 병합의 단일 근본 원인이라 M임에도 포함). P1 11건은 설계가 필요한 것들 — LOD 갭/log 경로(알고리즘), 터치/핀치(입력 모델), 테마 동기화(부모 프로토콜 합의), review-matrix 마감 묶음, 플러그인 크롬 옵션 체계, 발견가능성 UX, 임베드 모달 적응, flowchart fit 정책, 에러·빈 상태 표준화, 접근성 1차 패스, taxonomy 재설계. P2 7건은 낮은 빈도/영향 — 키보드 풀 지원(L), 내보내기 공통 세트, 시각 규약 통일, 라벨 halo, 한글 동의어, 질문 dedupe, 갤러리 재생성 절차. 동일 파일 원칙에 따라 flow-core engine.js는 P0에서 4개 항목(타이틀·휠·시뮬·_panned)이 함께 닿으므로 한 PR로 처리 권장하고, P0 완료 후 build_gallery 전체 재생성(P2 마지막 항목)을 1회 실행해야 graph-out 데모에 반영된다.


## P0 — 즉시 (이번 차수 구현) (12건)

### P0.1 flow-core 타이틀을 툴바 밖(root)으로 이동 — 버튼 겹침 해소  `S`
- **영역:** flow-core 레이아웃
- **이유:** 감사에서 6회 중복 보고된 최다 발견 결함(severity 4). flowchart/sankey/network/chord/sunburst 등 제목 있는 모든 flow 산출물의 첫 화면이 깨져 보인다. 원인이 단일하고(engine.js:681이 타이틀 div를 absolute 툴바 안에 append → containing block이 툴바가 됨) 수정이 사실상 1줄이라 효과 대비 비용이 가장 낮다.
- **파일:** engine.js, engine.css
- **수정:** engine.js:681의 `bar.appendChild(el("div","gs-fl-title",this.opts.title))`를 `this.root.appendChild(...)`로 변경해 .gs-fl-title(absolute top:8 left:12)이 root 기준으로 좌상단에 배치되게 한다. 긴 제목 대비 max-width:calc(100% - 220px) + text-overflow:ellipsis를 CSS에 추가. 검증: flowchart/sankey/network 3종 900px·360px 스크린샷에서 타이틀-버튼 rect overlap=False 확인.

### P0.2 flow-core·gauge-core engine.css에 html/body 리셋 추가 — 높이 붕괴·8px 테두리·iframe 미채움 일괄 해소  `S`
- **영역:** flow-core/gauge-core CSS
- **이유:** 3건 병합(360px 띠 붕괴, 다크 8px 검은 액자, iframe 죽은 여백/잘림). 순수 flow 산출물 4종 + gauge 전부가 임베드에서 항상 깨져 보이는 severity 4 문제인데, 다른 6개 패밀리에 이미 있는 리셋 2줄을 복사하는 수준이라 즉시 가능.
- **파일:** engine.css, engine.css, types.json
- **수정:** 두 engine.css 맨 위에 `*,*::before,*::after{box-sizing:border-box} html,body{margin:0;padding:0;height:100%}` 추가(xy-core/review-matrix와 동일 문구). gauge min-height:320px→240px, flow min-height:360px→240px로 완화. types.json의 bullet-chart height_px(300) vs min-height 불일치를 함께 정리(권장 높이 320으로 올리거나 min-height 240 적용으로 해소). 검증: sankey/gauge를 520px·300px iframe에서 루트 clientHeight==iframe 높이 확인.

### P0.3 휠 스크롤 트랩 제거 — Ctrl(⌘)+휠일 때만 줌, 일반 휠은 페이지 스크롤 통과  `M`
- **영역:** 임베드 전 엔진 공통
- **이유:** 감사 유일의 severity 5 임베드 결함. 보고서를 스크롤하던 독자가 그래프마다 걸려 멈추고 자기도 모르게 차트를 파괴(bode가 10^-8~10^12Hz로 줌아웃)하는 실측 재현 문제. 임베드가 이 스킬의 주 사용처라 체감 1순위. 패턴(지도 임베드 표준)이 확립돼 있어 M이지만 위험이 낮다.
- **파일:** engine.js, engine.js, engine.js, engine.js, engine.css
- **수정:** wheel 핸들러 4곳(xy-core:773, field-core:343·378, flow-core:595-602, cad3d OrbitControls)에 공통 게이트: `if(!e.ctrlKey && !e.metaKey){ showZoomHint(); return; }`(preventDefault 안 함 → 페이지 스크롤 유지), Ctrl+휠일 때만 기존 줌 + preventDefault. showZoomHint는 'Ctrl+스크롤로 확대' 반투명 오버레이를 1.5초 표시 후 페이드. cad3d는 controls.enableZoom을 동일 게이트로 토글. xy/field canvas의 touch-action:none→pan-y로 완화해 모바일 세로 스크롤 통과. 검증: 부모 페이지에 3개 iframe 넣고 휠 5회에 scrollY 증가 + 차트 view 불변 확인.

### P0.4 playback/stream 4종 빈 화면 복구 + 내부 캐리어 시리즈 숨김 + 범례 토글 시 줌 유지  `S`
- **영역:** xy-core 시리즈/범례
- **이유:** 3건 병합(같은 캐리어 메커니즘·같은 engine.js). bubble-timeline 등 4타입이 완전히 빈 화면으로 출하 중인 severity 5 기능 결함이고, _carrier/_pc/_tm 범례 노출(sev4)과 토글 시 autoFit 줌 리셋(sev2)도 같은 시리즈/범례 코드 경로라 한 번에 수정하는 게 효율적. 모두 S급 국소 수정.
- **파일:** engine.js, playback.py, leftovers.py, validate.py
- **수정:** (1) engine.js setData(186행)에 폴백: s.x가 없고 s.data가 [[x,y],...]면 unzip해 s.x/s.y 생성(base_xy.py의 변환과 동일 규칙). (2) _buildLegend·_hitTest·툴팁에서 이름이 '_'로 시작하거나 style==='none'인 시리즈 제외. (3) _toggleSeries(870)·_isolateSeries(874)에서 현재 view가 full 도메인과 다르면 autoFit 대신 render()만 호출(잠금·커서 보존). (4) validate.py에 playback 계열 스모크: 렌더 후 view 도메인이 [0,1] 기본값이 아닌지 검사. 검증: bubble-timeline/bar-chart-race/animated-trajectory/stream-graph 재생성 후 점 개수>0, 범례에 '_' 항목 0개.

### P0.5 review-matrix 셀 그래프 크기 폭발 차단 (.gs-root 규칙 침식 오버라이드)  `S`
- **영역:** review-matrix CSS
- **이유:** 셀 미니그래프가 220x130이 아닌 528x240으로 렌더되어 비교표가 뷰포트 2배(1814px)로 넘치고 v3 열이 아예 안 보이는 severity 4 결함 — review-matrix의 존재 이유(나란히 비교)를 부정한다. CSS 한 블록으로 해결되는 S 수정. 셀이 정상 크기가 되면 wide 그래프 셀 초과 문제(P1)도 상당 부분 완화된다.
- **파일:** engine.css
- **수정:** engine.css에 `.gs-cell-graph.gs-root{width:220px;height:130px;min-height:0;aspect-ratio:auto;}` 오버라이드 추가(xy-core의 .gs-root{width:100%;min-height:240px;aspect-ratio:16/9}보다 특이도 높음). 모달 내 마운트(.gs-modal 내부)는 영향 없도록 셀렉터를 셀 한정으로 유지. 검증: design_state.html 재생성 후 셀 그래프 3개 rect 220x130, 테이블 폭 ≤ 뷰포트 확인.

### P0.6 모달 Escape 닫기 + role=dialog/aria-label (flow-core·review-matrix 공통)  `S`
- **영역:** DOM 엔진 모달
- **이유:** 2건 병합(인터랙션 감사 + 접근성 감사가 같은 결함 보고). 86vw×82vh 준전체화면 오버레이가 표준 닫기 키를 무시하는 건 모든 사용자가 즉시 부딪히는 마찰이고, 두 엔진에 동일 패턴 ~15줄이면 끝나는 S 수정.
- **파일:** engine.js, engine.js
- **수정:** 두 엔진의 _buildModal/open 경로에 동일 패턴: open 시 `this._esc=(e)=>{if(e.key==='Escape')this._closeModal()}; document.addEventListener('keydown',this._esc)` 등록, close 시 removeEventListener. 모달 박스에 role="dialog" aria-modal="true", × 버튼(gs-fl-x/gs-x)에 aria-label="닫기" 추가, open 시 × 버튼 focus()·close 시 트리거 요소로 포커스 복원. 검증: Playwright로 모달 open→Escape→classList에 open 부재 확인(두 엔진).

### P0.7 network force 시뮬레이션 종료 조건 추가 — 무한 rAF/CPU 상주 제거  `S`
- **영역:** flow-core 성능/모션
- **이유:** 3건 병합(인터랙션·모션·성능 감사 동일 근본 원인: engine.js:277의 alpha 하한 0.03 + 무조건 raf 재호출). 탭을 열어두기만 해도 O(n²) 계산이 60fps로 영구 가동되고 노드가 상시 잔떨림 — 보고서에 임베드되면 페이지 전체 배터리를 소모한다. 정지 조건 추가는 수 줄짜리 S 수정.
- **파일:** engine.js
- **수정:** engine.js:277의 `if(sim.alpha<0.03) sim.alpha=0.03` floor를 제거하고 step() 말미를 `if(sim.alpha>0.005) raf(step); else sim.running=false;`로 변경. 노드 pointerdown(드래그 시작)·리사이즈 시 `sim.alpha=0.6; if(!sim.running){sim.running=true; raf(step);}`로 재가열. 검증: network-graph.html 로드 5초 후 2초간 attribute 변경 0회, 노드 드래그 시 레이아웃 재가동 확인. (Barnes-Hut 근사 등 대규모 최적화는 P2로 분리)

### P0.8 flow-core 팬 후 노드 클릭 죽음 수정 (_panned 플래그 리셋)  `S`
- **영역:** flow-core 인터랙션
- **이유:** 팬은 flow 다이어그램의 가장 흔한 첫 조작인데 그 직후 노드 클릭이 전부 막혀 '클릭이 안 된다'는 인상을 준다(Playwright 재현 확정). early-return 앞에 리셋 한 줄이면 되는 전형적 P0.
- **파일:** engine.js
- **수정:** engine.js:583-585 stage mousedown 핸들러에서 .gs-fl-clickable 대상 early-return 이전에 `self._panned=false;`를 항상 실행. 더 견고하게는 카드 자신의 pointerdown 좌표와 click 좌표 거리(>4px)로 팬 여부를 판정해 전역 플래그 의존을 제거. 검증: 배경 팬 → 노드 클릭 → 모달 open=True (기존 재현 시나리오 역검증).

### P0.9 embed_block() 기본 높이를 아티팩트의 recommended_height_px에서 읽기  `S`
- **영역:** builder/임베드 API
- **이유:** 2건 병합. 타입별 권장 높이(240~640)가 이미 HTML meta에 박혀 있는데 호출자가 안 넘기면 무조건 520 — gauge는 200px 죽은 여백, review-matrix는 내부 스크롤. 같은 모듈에 정답이 있어 연결만 하면 되는 S 수정이고, 위 CSS 수정들과 합쳐져야 임베드 기본 경험이 완성된다.
- **파일:** builder.py
- **수정:** builder.py embed_block(139행)에서 height_px가 None이면 대상 html을 열어 #graph-config JSON(builder.py:62에서 쓰는 meta)의 meta.recommended_height_px를 파싱해 기본값으로 사용, 파싱 실패 시에만 520 폴백. 검증: gauge.html embed_block() 기본 호출이 height=320, review-matrix류가 600을 내는 단위 테스트 추가.

### P0.10 SKILL.md 스테일 해소 — 8개 엔진 패밀리/91타입 현행화 + Tools 표 보강  `S`
- **영역:** LLM-facing 문서
- **이유:** '엔진은 xy-core 하나'라는 7행 문구를 믿은 LLM이 3D/표/게이지/플로우 요청을 '미지원'으로 오판하거나 base-xy로 우회하는 severity 4 라우팅 결함. 문서 수정이라 비용이 가장 낮으면서 스킬 전체 활용도를 좌우한다.
- **파일:** SKILL.md, tools.py
- **수정:** SKILL.md 7행을 '8개 엔진 패밀리(xy/field/polar/smith/cad3d/flow/gauge/review-matrix), 91타입; 비-xy 패밀리 입력 키는 graph_schema_get hint를 따른다'로 갱신. Tools 표(20-31행)에 누락된 ingest_csv/resample/smooth 3종 추가. 분류표(38-54행) 대표 타입에 sankey/gauge/flowchart/cad-3d-viewer 등 신규 타입 반영. 재발 방지로 '엔진 디렉터리 수 == 문서 기재 수' 검증 테스트를 tests에 추가.

### P0.11 tools.py 묶음: MCP 스키마 additionalProperties 자기모순 해소 + validate_inputs hint 폴백  `S`
- **영역:** MCP/LLM API
- **이유:** 2건 병합(동일 파일 tools.py). 스키마가 validate.check의 ask 문구가 요구하는 키(links/tree/frames 등)를 금지하는 자기모순은 91타입 중 절반의 입력을 막을 수 있는 severity 4. hint 폴백(69/91 타입에서 빈 문자열)은 1줄. 최소 수정(additionalProperties 완화 + or-폴백)은 모두 S급.
- **파일:** tools.py, prompt.py, types.json
- **수정:** (1) VALIDATE_SCHEMA/RENDER_SCHEMA에서 additionalProperties:false 제거(또는 _PAYLOAD_PROPS에 nodes/edges/links/items/frames/tree/level/steps/values/categories/groups/freqs/mag/phase 명시 추가)하고 description에 '타입별 최상위 키는 graph_schema_get hint를 따름' 명기. (2) validate_inputs의 hint를 `prompt.hint_for(gt) or catalog.get_schema(gt)['hint']`로 폴백. (3) 회귀 테스트: types.json hint에 등장하는 모든 최상위 키가 스키마에서 허용되는지 검사. hint SSOT 일원화는 P2로 이연.

### P0.12 xy-core 오버레이 레이아웃 예약 — 컨트롤바·범례·재생바·filter-panel 겹침 일괄 해소 + y2 제목 잘림  `M`
- **영역:** xy-core 레이아웃
- **이유:** 6건 병합(좁은 폭 컨트롤바/제목 가림 3회 보고, filter-panel이 범례 완전 덮음, 재생바가 x축 가림, y2 제목 캔버스 밖 잘림). 근본 원인이 하나 — _layout(318행)이 absolute 오버레이들의 높이를 전혀 예약하지 않음. 보고서 본문 컬럼 폭(500-700px)에서 매번 보이는 문제라 임베드 체감이 크고, offsetHeight 측정→마진 가산은 기계적인 수정. M이지만 P0에 포함할 가치가 충분.
- **파일:** engine.js, engine.css, filter-panel.js, playback.js
- **수정:** (1) _layout(318행)에서 controlbar.offsetHeight를 top 마진에, legend.offsetHeight + (playbar?playbar.offsetHeight:0) + (filterPanel?높이:0)를 bottom 마진에 가산하고, 오버레이 크기 변화 시 ResizeObserver로 재레이아웃. (2) filter-panel 사용 시 범례를 우측 하단으로 이동(좌하단 좌표 충돌 제거). (3) y2 제목(450행) translate 기준을 W-4→W-14로 옮기고 right 마진에 제목 폭 16px 반영. (4) 캔버스 제목 폭을 (전체폭-툴바폭)으로 제한해 말줄임. 검증: bode 360px·filter 900px·bubble-timeline 900px에서 오버레이 rect와 plot/축라벨 rect overlap=False. (좁은 폭 ⋯ 메뉴 접기는 P1로 분리)


## P1 — 다음 차수 (11건)

### P1.1 LTTB LOD가 null 갭/log축에서 꺼지는 경로 수리 — bode/fft/psd 대용량 5fps 해소  `M`
- **영역:** xy-core 성능
- **이유:** severity 4 실측 성능 결함(200k점 + null 1개 또는 log축 → 호버 4~6fps)이고 log-주파수 + 대량 포인트가 표준인 타입들이 정확히 이 경로에 떨어진다. 다만 세그먼트별 LTTB·log 공간 샘플링은 시각 충실도 검증이 필요한 알고리즘 작업이라 다음 차수.
- **파일:** engine.js
- **수정:** _lod()의 `if (s._hasNull || this.xLog || this.yLog) return s;` 조기 탈출 제거. 갭 시리즈는 기존 _segments 분할 로직을 _lod 앞단으로 옮겨 세그먼트별 LTTB 후 null로 재결합. log축은 log10(x) 좌표계에서 LTTB 수행. 회귀: 200k점+null·log-x 케이스에서 lodPts≤8000, 호버 p50<33ms 성능 스모크 테스트 추가.

### P1.2 터치 입력 1급 지원 — flow-core pointer events 전환 + xy/field 핀치줌 + 탭 툴팁  `M`
- **영역:** 입력장치(터치)
- **이유:** 3건 병합. flow-core는 터치에서 팬·드래그가 완전 불가(sev4)하고 xy/field는 touch-action:none으로 브라우저 핀치까지 막으면서 자체 핀치줌이 없어 모바일 확대 수단이 0(WCAG 1.4.4 계열). 중요하지만 멀티포인터 추적·핀치 수학·실기기 검증이 필요한 설계 작업.
- **파일:** engine.js, engine.js, engine.js
- **수정:** flow-core _bindPanZoom과 network 노드 드래그를 mousedown/mousemove/mouseup → pointerdown/pointermove/pointerup + setPointerCapture로 교체(stage touch-action:none). xy/field는 활성 포인터를 Map으로 추적해 2포인터 거리 비율로 기존 커서 중심 _zoom 재사용 핀치줌 구현. xy 클릭-락 직후 _showTooltip() 호출로 탭에서도 시리즈 값 표시. 폴백으로 ＋/－ 줌 버튼을 xy/field 툴바에 추가. P0의 Ctrl+휠 게이트와 핀치 줌 제스처가 충돌하지 않게 설계.

### P1.3 테마 통일 패키지 — 부모 보고서와 테마 동기화 채널 + 다크 팔레트 단일화 + smith Okabe-Ito  `M`
- **영역:** 테마/시각 일관성
- **이유:** 4건 병합(postMessage 채널 부재, 다크 팔레트 #0f1419 vs #0f172a 분열 + flow 임베드 여부 따라 배경/폰트 변동, smith 비색맹안전 팔레트, cad3d matchMedia 1회 읽기). 임베드 보고서가 다크인데 iframe만 흰색인 문제는 체감이 크지만 부모 측 프로토콜 정의·report-write와의 합의가 필요해 설계 차수.
- **파일:** boot.js, template.html, engine.css, engine.css, engine.js, engine.js
- **수정:** (1) boot.js에 message 리스너({type:'gs-theme',theme:'light|dark|auto'} → 루트 data-theme 갱신)와 ?theme= 쿼리 지원 추가, embed_block() 산출 스니펫/문서에 부모 postMessage 예시 명시. (2) 전 엔진 다크 토큰을 #0f1419/#e8eaed/#60a5fa로 통일하고 flow/gauge 다크 블록에 --gs-accent:#60a5fa 추가. (3) xy-core 루트 셀렉터를 .gs-root:not(.gs-flow):not(.gs-matrix)로 좁혀 임베드 침식 차단. (4) smith PALETTE를 Okabe-Ito(#0072B2,#D55E00,#009E73,#CC79A7,#E69F00,#56B4E9)로 교체. (5) cad3d는 matchMedia('(prefers-color-scheme)') change 이벤트 구독.

### P1.4 review-matrix 마감 묶음 — sticky 헤더 변수화·검색 0건 메시지·셀 컨트롤 격리·wide 셀 초과·heat 대비  `M`
- **영역:** review-matrix
- **이유:** 5건 병합(동일 엔진 파일들). 각각 S~M이지만 sticky 47px 하드코딩(2회 보고), 미니그래프 버튼 클릭 시 모달 오발(기능 충돌), wide 그래프 뷰포트 216px 초과, WCAG 1.9:1 대비 실패 등 표 계열 전반의 품질 문제라 한 차수에 모아 처리하는 게 효율적. wide 셀과 셀 컨트롤 격리는 P0의 셀 크기 수정 결과를 보고 범위를 정해야 해서 다음 차수.
- **파일:** engine.css, engine.js, engine.css
- **수정:** (1) ResizeObserver로 toolbar.offsetHeight를 --gs-toolbar-h CSS 변수로 주입, thead th top:var(--gs-toolbar-h). (2) _applyFilter에서 가시 행 0이면 colspan 전체 '"{query}" 검색 결과 없음' 행 표시. (3) 셀 마운트 시 xy-core에 {controlbar:false} 옵션을 추가해 미니그래프 컨트롤/HUD 제거(상호작용은 모달 전용), 셀 div에 title="클릭하여 확대"+⤢ 아이콘. (4) .gs-mx-table table-layout:fixed 또는 wide 셀 max-width:calc(100% - 라벨열폭). (5) heat 글자색을 배경 상대 휘도 기반(luminance>0.45→#111, else #fff)으로 교체.

### P1.5 비-데카르트 플러그인 크롬 정리 — treemap 축/HUD/log 버튼 숨김 옵션 + parcoord min/max 라벨 가시화  `M`
- **영역:** xy-core 플러그인
- **이유:** 2건 병합. treemap에 0..1 축과 ': 0.1024' HUD가 노출되고 parcoord는 브러시 기준값이 전혀 안 보이는 문제 — 플러그인 주도 그래프에 대한 엔진 크롬 on/off 옵션 체계(hideAxes 등)를 새로 설계해야 해서 P1. parcoord 라벨만 떼면 S지만 같은 플러그인 표시 계층 작업이라 함께 처리.
- **파일:** treemap-drill.js, parcoord.js, engine.js
- **수정:** (1) xy-core options에 hideAxes/hideLogButtons/hideHUDxy 추가, treemap/parcoord 레시피가 이를 출력. (2) HUD 빈 라벨 시 'x'/'y' 폴백(engine.js:641). (3) 브레드크럼을 HUD와 안 겹치게 우측 이동. (4) 엔진에 클립 해제 후 호출되는 onDrawOutside 훅 추가, parcoord 라벨(52-53행)을 이 훅 또는 플롯 안쪽(pl.top+10/pl.bottom-4)으로 이동. 브러시 중 현재 범위 실값 HUD 표시.

### P1.6 인터랙션 발견가능성 패키지 — '?' 치트시트·커서 어포던스·sunburst 드릴다운 힌트·flow 팬줌 토스트  `M`
- **영역:** 전 엔진 발견가능성
- **이유:** 4건 병합. shift+박스줌/휠 수정키/더블클릭 리셋/범례 dblclick/축 브러시/드릴다운 등 핵심 기능이 화면 어디에도 안내되지 않아 기능 자체가 묻힌다. 중요하지만 어떤 안내 패턴(치트시트/토스트/상시 힌트)을 쓸지 UX 설계가 선행돼야 하고 좁은 폭 ⋯ 메뉴 접기(P0에서 분리)도 여기서 함께 설계.
- **파일:** engine.js, xbrush.js, parcoord.js, engine.js
- **수정:** (1) xy 컨트롤바에 '?' 버튼 → 단축키/제스처 치트시트 오버레이. (2) xbrush 핸들·parcoord 축 근처에서 cursor를 ew-resize/crosshair로 전환. (3) sunburst 세그먼트 <title>에 '클릭하여 드릴다운' 추가 + 드릴 경로 브레드크럼 표시. (4) flow 최초 로드 시 2초 '드래그: 이동 · Ctrl+휠: 확대' 토스트(P0 휠 게이트 힌트와 통합) + 빈 배경 더블클릭=fit. (5) 480~640px 미만에서 PNG/CSV/{} 버튼을 ⋯ 단일 메뉴로 접기. 버튼 title 한국어 통일.

### P1.7 임베드 모달 크기 적응 — 작은 iframe에서 모달 잘림/이중 스크롤 해소  `M`
- **영역:** 임베드 모달
- **이유:** 300px iframe에서 '크게 보기' 모달이 iframe보다 커져 잘리고 내부 스크롤이 강제되는 실측 문제. vh 기반 고정값을 컨테이너 상대값으로 바꾸고 임계 미만 시 새 탭 폴백을 정하는 등 동작 정의가 필요해 P1.
- **파일:** engine.css, engine.css, engine.js
- **수정:** .gs-fl-modal-graph의 min-height:340px를 max(180px, 60%)류 컨테이너 상대값으로, 모달 박스를 inset:8px 기반으로 변경해 항상 컨테이너 안에 수납. review-matrix .gs-modal-box(86vw×82vh)도 동일 원칙 적용. 컨테이너 높이 <360px이면 모달 대신 '새 탭에서 열기' 링크 폴백 제공.

### P1.8 flowchart fit/스케일 정책 재설계 — 판독 가능한 전체 보기 + 대형 그래프 탐색  `L`
- **영역:** flow-core 레이아웃
- **이유:** 2건 병합(기본 fit에서 라벨 판독 불가 + 300노드에서 scale 0.05 클램프로 fit 자체가 불가, 노드 검색 부재). 최소 스케일 보장·semantic zoom·검색은 상호 트레이드오프가 있는 설계 문제라 P1.
- **파일:** engine.js
- **수정:** (1) 기본 rank_gap 120→60. (2) _fit()이 스케일 0.7 미만이 필요하면 폭 기준 fit + 세로 팬 유도로 전환. (3) 575·599행의 0.05 하한을 1/64 수준으로 완화하되 일정 스케일 이하에선 카드 본문 숨기고 헤더만 표시(semantic zoom), 라벨도 임계 이하 숨김. (4) 노드 수 임계 초과 시 툴바에 검색 input 추가 → 일치 노드로 pan+하이라이트.

### P1.9 에러·빈 상태 표준화 — .gs-error 공통화, 'engine?/graph err' 제거, 빈 데이터 워터마크, 깨진 graph ref 검증, sankey 0값  `M`
- **영역:** 견고성/에러 상태
- **이유:** 5건 병합(모두 '실패/빈 상태가 무언·오도'라는 같은 주제). 개별로는 S~M이지만 에러 표시 규약(.gs-error를 셸로 이동)과 validate referential-integrity 추가 등 계층 간 정리가 필요해 한 차수로 묶는다.
- **파일:** template.html, boot.js, engine.js, engine.js, matrix_compare.py, validate.py
- **수정:** (1) .gs-error CSS를 각 엔진에서 template.html 공통 <style>로 이동. (2) flow/review-matrix mountGraph 실패 시 'engine?'/'graph err' 대신 `<div class="gs-error">내장 그래프 렌더 실패: {엔진명/원인}</div>` + console.error(err) — 두 엔진의 mountGraph를 공통 헬퍼로 추출. (3) xy/flow 데이터 0건 시 중앙 '표시할 데이터 없음' 워터마크. (4) matrix_compare.py structural_requires에 graph 셀 ref→graph_payloads 무결성 검사 추가(MissingFieldsError로 회송), 엔진은 gp 누락 시 'graph 정의 누락(ref)' placeholder. (5) sankey maxLayerVal이 유효값 없이 폴백뿐이면 최소 높이 8px + '유효한 흐름 데이터 없음' 안내, 미존재 노드 id 링크는 집계 전 필터+콘솔 경고.

### P1.10 접근성 1차 패스 — canvas role=img/aria-label, 아이콘 버튼 aria-label, focus-visible, reduced-motion  `M`
- **영역:** 접근성
- **이유:** 4건 병합(전부 S급 기계적 수정이지만 6~8개 엔진 파일에 걸친 횡단 작업). 스크린리더에 빈 화면(sev3), 글리프 버튼 무음, 포커스 링 식별 불가, prefers-reduced-motion 0건 — 법적/정책 요구가 걸릴 수 있는 기본기라 다음 차수에 일괄 처리.
- **파일:** boot.js, engine.js, engine.js, engine.css, engine.css
- **수정:** (1) boot.js mount 직후 canvas에 role='img' + aria-label(title+축 라벨) 일괄 부여, gauge는 label/value/unit·xy는 시리즈명을 sr-only 요약 div로 출력. (2) 각 엔진 _btn 헬퍼에 b.setAttribute('aria-label', title) 추가(6개 파일 각 1줄), gauge 영어 title을 한국어로 통일, 토글 버튼에 aria-pressed. (3) 전 엔진 CSS에 .gs-btn:focus-visible{outline:2px solid var(--gs-accent);outline-offset:2px} + pressed용 이중 링. (4) 공용 REDUCED=matchMedia('(prefers-reduced-motion: reduce)').matches — gauge 로드 애니 t=1 즉시 그리기, network 동기 수렴 후 1회 paint, playback/cad3d 프레임 점프.

### P1.11 taxonomy 카테고리 재설계 — relations/hierarchy/kpi-status/playback 신설로 신규 패밀리 라우팅 복구  `M`
- **영역:** LLM-facing API
- **이유:** sankey/gauge/network/flowchart이 'ranking'·'table'에 강제 편입되어 의도→카테고리 동선으로 도달 불가(sev3). 카테고리 체계 변경은 SKILL.md 분류표·기존 LLM 프롬프트 호환성에 영향을 줘 설계·검증이 필요한 M 작업.
- **파일:** taxonomy.json, SKILL.md, taxonomy.py
- **수정:** taxonomy.json에 'relations(흐름·관계)', 'hierarchy(계층·구성)', 'kpi-status(지표·현황)', 'playback(시간 재생)' 카테고리를 추가하고 sankey/network/chord/flowchart→relations, treemap/sunburst→hierarchy, gauge/stat-card/bullet→kpi-status, bar-chart-race/bubble-timeline→playback으로 재분류. SKILL.md 분류표 대표 타입 동기화. 카테고리 desc와 소속 타입의 의미 정합성 + 91타입 전수 커버리지 테스트 추가.


## P2 — 후순 (7건)

### P2.1 키보드 전용 조작 지원 — 인터랙티브 요소 tabindex/role + 차트 본체 키맵  `L`
- **영역:** 접근성(키보드)
- **이유:** 2건 병합. 범례/카드/그룹행/드릴다운의 키보드 도달과 줌·팬·커서 키맵은 영향 사용자층이 상대적으로 좁고 엔진 전반의 포커스 모델 설계가 필요한 L 작업. 단 cad3d는 controls.listenToKeyEvents(canvas)+tabindex 한 줄 퀵윈이 있어 P1 접근성 패스에 끼워 넣어도 된다.
- **파일:** engine.js, engine.js, engine.js, engine.js
- **수정:** 범례 항목·flow 카드·그룹 행을 button화(또는 tabindex=0+role=button+Enter/Space). sunburst path에 tabindex+aria-label('이름: 값'). xy canvas에 tabindex=0 + 화살표=팬/커서 스텝, +/-=줌, Home=autoFit 키맵(base-xy 60여 타입 일괄 수혜). cad3d는 listenToKeyEvents(canvas)+tabindex로 화살표 팬 활성화.

### P2.2 내보내기 최소 공통 세트(PNG+source+테마) 전 패밀리 보장 — smith 툴바 신설 포함  `M`
- **영역:** 툴바/내보내기
- **이유:** 패밀리별 PNG/CSV/{} 편차는 비일관 경험이지만 기능 부재일 뿐 깨짐은 아니어서 빈도 대비 영향이 중간 이하. flow SVG→canvas 직렬화 등 신규 구현이 필요해 후순위. smith 테마 토글 부재만 P1 테마 패키지에서 선처리 권장.
- **파일:** engine.js, engine.js, engine.js
- **수정:** 공통 툴바 빌더를 shell 유틸로 추출 후: smith-core에 툴바(PNG/◐/{}) 추가, flow-core에 SVG 직렬화→canvas PNG 내보내기, review-matrix에 표 CSV 내보내기 추가. 모든 패밀리가 PNG+{}+◐ 최소 세트를 갖는지 테스트.

### P2.3 버튼 스타일·제목 배치 등 패밀리 간 시각 규약 통일  `M`
- **영역:** 시각 디자인 일관성
- **이유:** 2건 병합(버튼 호버/aria-pressed/radius/폰트 스택 편차, 제목 중앙 vs 좌측 혼재). 나란히 임베드될 때만 드러나는 미관 문제로 영향이 낮고, 공통 CSS 조각 주입 체계는 builder 변경이 필요. cad3d :hover 부재와 flow/gauge aria-pressed만 먼저 추가하는 퀵윈 가능.
- **파일:** engine.css, engine.css, engine.css, engine.js, builder.py
- **수정:** 공용 버튼 규칙(11~12px, panel 배경, 그림자, :hover, [aria-pressed]) CSS 조각을 builder.py가 전 패밀리에 주입. 제목 배치는 좌상단 고정으로 통일(xy 캔버스 제목 좌측 정렬, cad3d .gs-cad-title left:12px). 폰트 스택을 'Segoe UI' 계열로 단일화.

### P2.4 network/sankey 라벨 가독성 — halo·겹침 숨김·0값 노드 구분  `M`
- **영역:** flow-core 렌더 품질
- **이유:** 라벨 겹침·리본 위 라벨은 가독성 저하(sev2)이지만 기능을 막지는 않고, 겹침 판정/halo 렌더는 신중한 시각 튜닝이 필요. P1의 fit/스케일 재설계 결과에 따라 증상이 달라지므로 그 후에 처리.
- **파일:** engine.js
- **수정:** SVG 텍스트에 paint-order:stroke 흰색 halo(다크는 배경색) 적용. network는 라벨 bbox 겹침 시 숨기고 hover 툴팁 대체. sankey 값 0 노드는 스킵 또는 최소 높이+회색 처리(P1 에러·빈 상태 항목의 sankey 수정과 연계). 노드 수백 개 대비 반발력 그리드 버킷/Barnes-Hut 근사도 이때 함께.

### P2.5 graph_find 한글 동의어 보강 (샌키/계기판/네트워크/상자그림/폭포/조직도)  `S`
- **영역:** LLM-facing API
- **이유:** 검색 0건 6패턴은 LLM이 graph_types_list 폴백으로 우회 가능해 영향이 제한적이고, taxonomy.json 키워드 추가만으로 끝나는 S 작업이라 P1 taxonomy 재설계에 편승해도 된다.
- **파일:** taxonomy.json, taxonomy.py
- **수정:** taxonomy.json 키워드에 샌키/생키, 계기판, 네트워크, 상자그림/박스플롯, 폭포차트, 조직도/관계도 추가. 대표 한국어 질의 목록의 find 적중 회귀 테스트 추가.

### P2.6 validate 중복 누락 질문 dedupe (bubble-timeline/overview-detail axes.x 2회)  `S`
- **영역:** LLM-facing API
- **이유:** 같은 필드에 다른 문구의 질문 2개는 경미한 혼란(sev2)이고 2타입에만 발생. 필드 기준 dedupe 한 줄이라 다른 validate.py 작업(P1 무결성 검사)에 편승 가능.
- **파일:** validate.py, playback.py
- **수정:** validate.check 말미에 missing을 field 키 기준 dedupe(첫 항목 유지). 또는 require_axes=true 타입의 structural_requires에서 axes 검사 제거. hint SSOT를 types.json으로 일원화(prompt._INPUT_HINTS 제거)도 이때 함께.

### P2.7 graph-out 갤러리 재생성 절차/CI — 구세대 엔진 산출물 해소  `S`
- **영역:** 빌드/운영
- **이유:** 데모 폴더가 1.0.0~1.4.0 혼재라 수정사항이 안 보이는 운영 문제(sev2). 사용자 대면 결함은 아니지만 P0/P1 수정 후 갤러리 일괄 재생성이 필수이므로 그 시점에 절차로 고정하면 됨.
- **파일:** build_gallery.py, ENGINE_VERSION
- **수정:** ENGINE_VERSION 범프 시 build_gallery.py로 graph-out 전체 재생성하는 절차(또는 pre-commit/CI 훅) 추가. 갤러리 인덱스에 engine_version 노출. P0 머지 직후 1회 전체 재생성 실행. 성능 스모크(부트<1s, 검색 키스트로크<16ms)도 이때 tests에 고정.


## 부록 — 원시 발견 73건 (요약)

| # | 심각도 | 영역 | 제목 |
|---|---|---|---|
| 1 | 5 | xy-core 인터랙션 U | playback/stream 계열 4종(bubble-timeline·bar-chart-race·animated-trajectory·stream- |
| 2 | 5 | 임베드(report ifr | 휠 스크롤 트랩 — 보고서 페이지 스크롤 중 그래프 위에 커서가 오면 페이지가 멈추고 그래프가 의도치 않게 줌되어 파괴됨 |
| 3 | 4 | xy-core 인터랙션 U | 좁은 폭(360px)에서 컨트롤바가 제목·플롯 위를 덮고, 범례가 x축 눈금·축제목과 겹침 |
| 4 | 4 | xy-core 인터랙션 U | 내부 캐리어 시리즈(_carrier/_pc/_tm)가 범례·툴팁에 그대로 노출되고 클릭까지 가능 |
| 5 | 4 | DOM 엔진(review- | flow-core 페이지가 뷰포트를 채우지 못하고 360px 띠로 붕괴됨 (html/body height 미설정) |
| 6 | 4 | DOM 엔진(review- | flow-core 타이틀이 툴바 버튼 위에 겹쳐 렌더되어 둘 다 읽을 수 없음 |
| 7 | 4 | DOM 엔진(review- | review-matrix 셀 그래프가 xy-core .gs-root 크기 규칙에 침식되어 220x130이 아닌 528x240으로 폭발, 표가 뷰 |
| 8 | 4 | 시각 디자인 일관성 | flow-core 제목이 우상단 툴바 버튼 위에 겹쳐 렌더되어 제목·버튼 모두 읽을 수 없음 |
| 9 | 4 | 시각 디자인 일관성 | gauge-core만 html/body 리셋이 없어 다크모드에서 8px 검은 테두리와 화면 아래 절반이 검게 갈라짐 |
| 10 | 4 | 임베드(report ifr | flow-core·gauge-core가 iframe 고정 높이를 채우지 못함 — 권장 높이로 임베드해도 죽은 여백/잘림 발생 |
| 11 | 4 | 입력장치(터치) | flow-core 전 모드가 터치 기기에서 팬·드래그 완전 불가 (mouse 이벤트만 사용) |
| 12 | 4 | 입력장치(터치) | 핀치줌 전무 + 전면 canvas touch-action:none — 모바일에서 확대 수단 자체가 없음 |
| 13 | 4 | 레이아웃(렌더 확인 중 발 | flow-core 타이틀이 우상단 툴바 버튼 위에 겹쳐 렌더됨 (모든 titled flow 산출물) |
| 14 | 4 | 견고성/성능/에러 상태 | 시리즈에 null 갭 1개 또는 log축이면 LTTB LOD가 통째로 꺼져 대용량 호버가 ~5fps로 저하 |
| 15 | 4 | LLM/사용자-facing | SKILL.md가 '엔진은 지금 xy-core 하나'라고 주장 — 실제는 8개 패밀리/91타입 체계로 심각한 스테일 |
| 16 | 4 | LLM/사용자-facing | MCP 입력 스키마(additionalProperties:false)가 신규 패밀리의 필수 입력 키를 금지 — validate가 시키는 입력을  |
| 17 | 3 | xy-core 인터랙션 U | treemap 등 플러그인 주도 그래프에 무의미한 엔진 크롬(0..1 축, ': 0.1024' HUD, log x/y 버튼)이 노출되고 HUD가 |
| 18 | 3 | xy-core 인터랙션 U | 우측 보조 y축 제목(Phase [deg])이 캔버스 밖으로 그려져 글자가 세로로 잘림 |
| 19 | 3 | xy-core 인터랙션 U | parallel-coordinates 축 상·하단의 min/max 값 라벨이 플롯 클리핑에 잘려 전혀 안 보임 — 값 기준 없이 브러시해야 함 |
| 20 | 3 | xy-core 인터랙션 U | 핵심 인터랙션(shift+드래그 박스줌, 휠 축별 줌, 더블클릭 리셋, 범례 더블클릭 isolate, 축 브러시)이 화면 어디에도 안내되지 않음 |
| 21 | 3 | xy-core 인터랙션 U | 터치 환경: touch-action:none인데 핀치 줌 미구현이라 모바일에서 줌 수단이 없고, 탭해도 시리즈 툴팁이 안 뜸 |
| 22 | 3 | xy-core 인터랙션 U | FFT filter 그래프에서 filter-panel이 범례를 완전히 덮어 original/filtered 토글이 불가능 |
| 23 | 3 | xy-core 인터랙션 U | review-matrix 셸에 임베드된 xy-core 그래프(overview-detail·multitrack-stack)가 뷰포트 폭을 넘어 우 |
| 24 | 3 | DOM 엔진(review- | flow-core: 한 번 팬(드래그)한 뒤에는 노드 클릭이 죽어 모달이 열리지 않음 (_panned 플래그 미초기화) |
| 25 | 3 | DOM 엔진(review- | 두 엔진 모두 모달을 Esc로 닫을 수 없음 |
| 26 | 3 | DOM 엔진(review- | review-matrix 셀 미니그래프의 자체 컨트롤(log x/log y/↺/◐)을 누르면 의도와 달리 모달이 열림 + 셀 클릭=확대라는 힌트 |
| 27 | 3 | DOM 엔진(review- | review-matrix 고정 헤더 offset이 47px 하드코딩이라 툴바가 줄바꿈되는 좁은 화면에서 헤더가 툴바 뒤로 숨음 |
| 28 | 3 | DOM 엔진(review- | network 포스 시뮬레이션이 영원히 멈추지 않음 — alpha 하한 0.03 + 무한 rAF 루프 |
| 29 | 3 | DOM 엔진(review- | flowchart을 기본 fit으로 보면 노드 라벨·내장 그래프·표가 판독 불가 수준으로 축소됨 |
| 30 | 3 | 시각 디자인 일관성 | 다크 팔레트가 두 계열(#0f1419 vs #0f172a)로 분열되어 있고, flow-core는 그래프 임베드 여부에 따라 배경·폰트가 달라짐 |
| 31 | 3 | 시각 디자인 일관성 | xy-core 좁은 폭에서 제목이 툴바 버튼에 완전히 가려지고 범례가 X축 제목과 겹침 |
| 32 | 3 | 시각 디자인 일관성 | smith-core만 색맹 안전 Okabe-Ito 팔레트를 쓰지 않고 빨강·초록이 같이 든 자체 팔레트 사용 |
| 33 | 3 | 시각 디자인 일관성 | review-matrix 고정 헤더 오프셋이 47px로 하드코딩되어 좁은 화면에서 헤더가 툴바 뒤로 숨음 |
| 34 | 3 | 임베드(report ifr | 작은 임베드 높이(300px)에서 모달이 iframe에 갇혀 잘리고 이중 스크롤 발생 |
| 35 | 3 | 임베드(report ifr | 내보내기 버튼이 엔진 패밀리마다 제각각 — smith-core는 툴바 자체가 없음 |
| 36 | 3 | 임베드(report ifr | 다크모드가 OS prefers-color-scheme만 따름 — 부모 보고서 앱의 테마와 동기화할 채널이 전혀 없음 |
| 37 | 3 | 임베드(report ifr | flow-core 제목이 툴바 컨테이너 안에 absolute로 들어가 우상단 버튼들과 항상 겹쳐 보임 |
| 38 | 3 | 모션 | network force 시뮬레이션이 영원히 멈추지 않음 — 상시 미세 흔들림 + CPU 상주 |
| 39 | 3 | 모션(접근성) | prefers-reduced-motion 처리 0건 — 게이지 로드 애니·force 레이아웃·재생 애니가 무조건 동작 |
| 40 | 3 | 접근성(키보드) | 모달이 Escape로 닫히지 않고 포커스 관리도 없음 (flow-core·review-matrix) |
| 41 | 3 | 접근성(키보드) | 클릭 전용 비버튼 인터랙션 다수 — 키보드로 도달 불가 |
| 42 | 3 | 접근성(키보드) | 차트 본체 키보드 조작 수단 전무 (줌/팬/커서/3D 회전) |
| 43 | 3 | 접근성(SR) | canvas에 role/aria-label/대체 콘텐츠 전무 — 스크린리더에 빈 화면 |
| 44 | 3 | 접근성(색 대비) | review-matrix heat 셀의 흰 글자 대비 1.9~2.1:1 (WCAG 실패) |
| 45 | 3 | 견고성/성능/에러 상태 | network-graph 힘 시뮬레이션이 영원히 멈추지 않음 — 정착 후에도 O(n²)+SVG 전체 갱신을 매 프레임 계속, 600노드에서 43 |
| 46 | 3 | 견고성/성능/에러 상태 | 내장 그래프 셀 실패 시 원시 문자열 'engine?' / 'graph err'가 스타일·설명 없이 노출 |
| 47 | 3 | 견고성/성능/에러 상태 | flow-core 타이틀이 툴바 버튼 위에 겹쳐 렌더 — 모든 titled flowchart/sankey/network 산출물에서 발생 |
| 48 | 3 | 견고성/성능/에러 상태 | 대형 flowchart는 전체 보기가 불가능 — fit/줌아웃이 scale 0.05에서 클램프되고 노드 검색 수단이 없음 |
| 49 | 3 | 견고성/성능/에러 상태 | 깨진 graph 셀 참조가 조용히 '—'로 렌더 — builder가 경고 없이 통과시킴 |
| 50 | 3 | LLM/사용자-facing | graph_validate_inputs 실패 시 69/91 타입에서 hint가 빈 문자열 — 입력 형태 안내가 정작 필요한 순간에 사라짐 |
| 51 | 3 | LLM/사용자-facing | taxonomy 카테고리가 신규 패밀리를 수용 못 함 — sankey/gauge/network/stat-card가 'ranking(순위·구성)' |
| 52 | 2 | xy-core 인터랙션 U | 범례 토글/isolate가 무조건 autoFit을 호출해 사용자가 잡아둔 줌·잠금 상태를 날려버림 |
| 53 | 2 | xy-core 인터랙션 U | 재생바(gs-playbar)가 x축 눈금과 축 제목을 가림 |
| 54 | 2 | DOM 엔진(review- | review-matrix 검색 결과 0건이면 표가 통째로 사라지고 아무 피드백이 없음 |
| 55 | 2 | DOM 엔진(review- | sunburst 드릴다운이 발견 불가능에 가까움 — 커서 변화 외 어떤 힌트도 없음 |
| 56 | 2 | DOM 엔진(review- | network 노드 라벨이 서로·노드와 겹치고, sankey 중간열 라벨은 리본 위에 얹혀 가독성이 떨어짐 |
| 57 | 2 | DOM 엔진(review- | flow-core 팬·줌 발견가능성 부족: 휠이 페이지 스크롤을 가로채고 '드래그=이동' 안내가 없음 |
| 58 | 2 | 시각 디자인 일관성 | 툴바 버튼 스타일·호버 피드백이 패밀리마다 제각각이고 cad3d 버튼은 호버 효과가 아예 없음 |
| 59 | 2 | 시각 디자인 일관성 | 제목 배치 규칙이 패밀리마다 달라(중앙 vs 좌측) 산출물을 나란히 놓으면 헤더가 들쭉날쭉함 |
| 60 | 2 | 임베드(report ifr | 좁은 임베드 폭에서 xy-core 캔버스 제목과 DOM 툴바가 겹침 |
| 61 | 2 | 임베드(report ifr | embed_block()이 타입별 recommended_height_px를 무시하고 무조건 520을 기본값으로 사용 |
| 62 | 2 | 접근성(SR) | 아이콘 전용 버튼이 title 속성에만 의존 (aria-label 없음, 일부는 영어 title) |
| 63 | 2 | 접근성(키보드) | 커스텀 focus-visible 스타일 부재 — pressed(파란) 버튼에서 포커스 위치 식별 곤란 |
| 64 | 2 | 견고성/성능/에러 상태 | flow-core 단독·gauge-core 아티팩트에는 .gs-error 스타일이 없어 부트 실패 메시지가 무스타일 맨 텍스트 |
| 65 | 2 | 견고성/성능/에러 상태 | 빈 데이터·검색 0건 상태에 아무 안내가 없음 (xy 빈 축 / flow-core 백지 / review-matrix 헤더만) |
| 66 | 2 | 견고성/성능/에러 상태 | sankey: 링크 유효 합계가 0이면 모든 노드가 최대 높이 막대로 그려져 '값 0'이 가장 커 보임 |
| 67 | 2 | 견고성/성능/에러 상태 | graph-out 산출물 91종이 서로 다른 구세대 엔진으로 빌드되어 있어 현행 엔진 수정사항이 반영 안 됨 |
| 68 | 2 | LLM/사용자-facing | graph_find 한글 동의어 공백 — '샌키/생키', '계기판', '네트워크', '상자그림', '폭포', '조직도' 검색 0건 |
| 69 | 2 | LLM/사용자-facing | bubble-timeline/overview-detail에서 같은 축 필드에 누락 질문이 두 번(서로 다른 문구로) 생성 |
| 70 | 2 | LLM/사용자-facing | graph_embed_block 기본 높이가 타입 불문 520px 고정 — HTML meta의 recommended_height_px(240~6 |
| 71 | 2 | LLM/사용자-facing | flowchart 제목이 우상단 툴바 버튼과 겹쳐 렌더됨 (높이 검증 중 관찰된 렌더 결함) |
| 72 | 1 | 접근성(색 대비) | 다크모드 토큰 대비는 양호 (이상 없음 확인) |
| 73 | 1 | 견고성/성능/에러 상태 | [실측 이상 없음] 대형 3D 아티팩트 로드·review-matrix 검색·scatter LOD는 점검 결과 양호 |