# 분석 산출물 상태 인덱스 (as-of v0.46.0, 2026-06-14)

`docs/_*_raw.json` 들은 **그 시점의** 멀티에이전트 분석 원본이다. 이후 구현으로 **이미 닫힌 항목**을 다시
백로그로 착수하지 않도록 여기서 해결 상태를 표시한다. (원본 JSON 은 역사적 기록으로 보존 — 수정하지 않음.)

| 산출물 | 시점 | 상태 |
|---|---|---|
| `_health_audit_raw.json` | v0.45.0 점검 | **대부분 해결.** 닫힘: scale:"log"(leftovers/playback), 엔진버전 범프, 문서숫자(9→8엔진·396→тests), ingest_s2p DISPATCH 누락, image.ref self-contained 우회. 추가 해결(v0.46.0): stress-linearization·multitrack 단위 게이트, SRS 경계가드, SPC within-σ, self-check 3종, 신선도 바인딩 게이트. 잔여: 없음(또는 P2 백로그로 이관). |
| `_conversion_quality_raw.json` | v0.46.0 실측 | **약점 해소.** grouped-bar/막대+선 콤보 신설(#2 B→A), SPC 한계 within-σ로 교정(#8), types_find 랭킹 강화, top-level export(DX 마찰). |
| `_web_mcp_plan_raw.json` | v0.46.0 설계 | **P0/P1 구현 완료** — server 패키지(REST+원격MCP+아티팩트), 인증/레이트리밋/스토어. 닫힘: ingest_s2p DISPATCH, image.ref SSRF 우회, 이벤트루프 블로킹, 스토어/버킷 무한증가, body-size 우회, 상수시간 비교. **잔여(P2 인프라)**: 오브젝트스토리지/CDN, OAuth, cad3d 워커격리, **report-archive file_id 연동**(embed url 모드 ↔ html_embed 계약). |
| `_improvement_roadmap_raw.json` | v0.46.0 | **P0 전체 + P1-A/B/C 완료.** 잔여: P2(미구현 T1 그래프 타입, 웹 인프라). |
| `_gap_analysis_raw.json` | v0.45.0 | **완료(v0.48.0).** T1 정형 그래프 11종 전부 구현: bland-altman(0.47) + loop-gain-margin·conducted-emission·tdr-impedance-profile·jitter-bathtub·battery-cycle-fade·cc-cv-charge-profile·thermal-resistance-stack·hardness-profile·xbar-r-chart·fmea-worksheet(0.48). T2/T3 후보는 미착수. |

**다음 작업 후보(잔여)**: 웹 인프라(S3/CDN·OAuth·cad3d 워커격리) · T2 그래프 타입 · report-archive file_id 풀 연동(현재 local_path 브릿지까지).
