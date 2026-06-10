I now have a complete and precise picture of the graph-skill architecture: engine families (xy-core 2D / future cad-viewer 3D / table), catalog blocks declaring {engine, extends, plugins, requires, post, options_defaults}, plugin composition (not class inheritance), the validate/missing gate, and the existing type roadmap (base-xy, scatter, stress-strain, fft-spectrum, bode, contour/heatmap, s-n, etc.).

The roadmap already names plugins I should reuse as inheritance bases (scatter, stress-strain, fft-spectrum, time-series, contour/heatmap, s-n) and identifies what 2D can't do (contour, polar, smith, eye-diagram, 3D surface). I have everything I need to produce the exhaustive MCAE catalog mapped onto this architecture. I'll now compose the full answer.

I produce the exhaustive catalog below, mapped onto the graph-skill architecture (engine families + catalog block per type: extends / plugins / requires / post). I group by MCAE domain, ordered common→specialized within each. Type-ids are kebab-case and namespaced where useful. "상속 베이스" reuses the existing roadmap bases (base-xy, scatter, stress-strain, time-series, fft-spectrum, bode, contour-heatmap, s-n) so new types = 1 catalog block (+ occasional plugin file).

Engine-family legend: **xy** = xy-core (Canvas 2D, exists) · **field** = 2D scalar/contour family (등고선·heatmap, roadmap #13) · **polar** = polar/radial 2D family (NEW) · **mesh3d** = 3D surface/contour-on-geometry family (cad-viewer 계열, NEW) · **cad** = cad-viewer 3D geometry (planned) · **matrix** = grid/cell heatmap-table family (NEW) · **eye/smith** = specialized 2D families (NEW).

---

## A. 구조해석 (Structural / Static Stress)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stress-strain | 응력-변형률 곡선 | 재료/시편 인장·압축 | 변형률 ε [-] | 응력 σ [MPa] | 탄성·항복·소성·UTS, eng↔true | A0[mm²], L0[mm] (or already σ/ε) | base-xy | unit-convert, region-shading, named-markers, live-tangent, props-table | units.eng_stress_strain | xy | ★★★ |
| force-displacement | 하중-변위 곡선 | 버튼/힌지/케이스 강성 시험상관 | 변위 d [mm] | 하중 F [N] | 기구 응답·항복·파단점 | x/y 단위, (강성 추출 시 선형구간) | base-xy | live-tangent(=강성 dF/dd), region-shading, named-markers | calculus.secant_slope | xy | ★★ |
| stiffness-curve | 강성 곡선 | 강성 K(d) 비선형화 | 변위/하중 [mm/N] | 강성 K [N/mm] | 국소·할선 강성, soft/stiff 천이 | 미분 구간, 단위 | force-displacement | live-tangent, regression | calculus.derivative | xy | ★★ |
| 3point-bend | 3점 굽힘 곡선 | 글래스/하판 bending stiffness | 처짐 [mm] | 하중 [N] (→ flexural σ) | 굽힘강성 EI, 파단 | span L, b, h (flexural 환산 시) | force-displacement | unit-convert(flexural), live-tangent, named-markers | units.flexural_stress | xy | ★★★ |
| bending-stiffness | 굽힘 강성/모멘트-곡률 | 폴더블 패널 강성 | 곡률 κ [1/m] | 모멘트 M [N·mm] | EI = M/κ, 적층 영향 | 단면 형상/단위 | force-displacement | live-tangent(EI), regression | calculus.derivative | xy | ★★★ |
| load-path-bar | 부품별 하중분담 막대 | load path 분배 | 부품(범주) | 하중분담 [N] or [%] | 어느 경로로 힘이 흐르나 | 분담 정의 단위 | base-xy(bar) | bar-aggregate, value-labels | — | xy | ★ |
| stress-contour | 응력 컨투어(필드) | von Mises/주응력 분포 맵 | X [mm] | Y [mm] / z=σ [MPa] | 핫스팟·집중부 위치 | z 의미·단위, grid 규칙성, 색맵 한계(σ_y) | contour-heatmap | grid-field, color-scale-legend, iso-lines, hotspot-marker | field.interp2d, field.isocontour | field | ★★★★★ |
| stress-contour-3d | 3D 표면 응력 컨투어 | 메시 위 σ 컬러맵 | 3D geom | z=σ on surface | 실제 부품 형상 위 응력 | 메시(STL/GLB), σ 필드, 단위계 | cad-3d-viewer | surface-colormap, color-scale-legend, section-plane, probe-pick | cad.map_field_to_mesh | mesh3d | ★★★★★ |
| warpage-map | 휨/워피지 맵 | PCB/하우징 평탄도, 사출 휨 | X [mm] | Y [mm] / z=w [µm] | out-of-plane 변형 분포 | z=변위 단위, 기준평면(best-fit), 규칙성 | contour-heatmap | grid-field, iso-lines, ref-plane-subtract, color-scale-legend | field.bestfit_plane, field.interp2d | field | ★★★★ |
| deformation-contour | 변형/변위 컨투어 | 총변위 magnitude 맵 | X [mm] | Y[mm]/z=|u|[mm] | 변형 형태·최대점 | z 단위, deform scale | contour-heatmap | grid-field, color-scale-legend, deform-scale | field.interp2d | field | ★★★★ |
| safety-factor-contour | 안전계수 컨투어 | SF=σ_allow/σ 분포 | X[mm] | Y[mm]/z=SF | SF<1 위험영역(역색맵) | σ_allow, 위험 임계 | stress-contour | grid-field, threshold-mask, iso-lines | field.ratio_field | field | ★★★★ |

(a) 도메인 인터랙션/오버레이: live-tangent를 강성/Et 모드로 재라벨(dF/dd [N/mm], dσ/dε [GPa]); region-shading으로 탄성/소성/네킹 자동 구간; named-markers(yield, UTS, fracture); contour 계열은 **probe-pick**(클릭 시 z값 HUD)·**iso-line 호버 추적**·**σ_y 초과셀 강조**·deform-scale 슬라이더(과장배율).
(b) 새 엔진패밀리 필요: stress-contour/warpage/deformation/safety-factor(=field), stress-contour-3d(=mesh3d on cad). 2D xy로 불가.

---

## B. 낙하/충격 (Drop / Shock / Impact)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| drop-accel-time | 가속도-시간 펄스 | 낙하/충격 가속도 이력 | 시간 t [ms] | 가속도 a [g] | 충격 펄스·피크 g·지속시간 | t 단위(ms/s), g 정의, (필터 CFC면 fs) | time-series | peak-detect, pulse-width-marker, cfc-filter | filters.cfc, calculus.peak | xy | ★★ |
| drop-stress-time | 응력-시간 이력 | 임팩트 부위 σ(t) | 시간 [ms] | 응력 σ [MPa] | 충격 중 최대 응력 시점 | σ 단위, 시간 | time-series | peak-detect, threshold-line, named-markers | calculus.peak | xy | ★★ |
| drop-energy-time | 에너지-시간 | 운동/변형/내부 에너지 분배 | 시간 [ms] | 에너지 E [mJ] | KE→IE 전환, 흡수에너지 | 에너지 단위, 성분 구분 | time-series | multi-band-fill, area-fill, legend-stack | calculus.cumulative | xy | ★★ |
| drop-velocity-time | 속도-시간 | 충돌 속도·반발 | 시간 [ms] | 속도 v [m/s] | 임팩트 속도, 반발(COR) | v 단위 | time-series | named-markers(impact/rebound), zero-cross | calculus.derivative | xy | ★★ |
| srs-spectrum | 충격응답스펙트럼(SRS) | 충격 심각도 주파수화 | 고유진동수 f [Hz] | 최대응답 [g] | 충격이 어느 주파수에 위험한가 | fs, Q(damping), 로그축 | fft-spectrum | log-log, srs-compute, knee-marker | spectral.srs | xy | ★★★★ |
| hic-indicator | HIC 유사 손상지표 | Head-Injury류 누적지표 | 시간창 [ms] | HIC/severity index | 적분기반 손상지표·임계 | a(t), 적분창, 임계값 | drop-accel-time | integrate-window, threshold-band, value-badge | calculus.hic_integral | xy | ★★★ |
| drop-contour-time | 충격 응력맵(시점별) | 특정 ms의 σ 분포 | X[mm] | Y[mm]/z=σ[MPa] | 충격파 전파·핫스팟 변화 | z 단위, time slice, 규칙성 | stress-contour | grid-field, time-slider, color-scale-legend | field.interp2d | field | ★★★★★ |
| drop-orientation-polar | 낙하자세 민감도 | 각도별 최대응력 | 낙하각 θ [deg] | 최대 σ/g [MPa/g] | worst-case 자세 식별 | 각도 정의, 반경량 단위 | (polar) | radial-grid, worst-marker | — | polar | ★★★★ |
| cumulative-energy-bar | 부품별 에너지흡수 | 흡수에너지 분담 | 부품(범주) | 흡수 E [mJ]/[%] | 어디서 충격에너지 흡수 | 성분 정의 | base-xy(bar) | bar-aggregate, value-labels | — | xy | ★ |

(a) 인터랙션: drop 계열은 **time-slider 연동**(시간선택→contour 동기), peak-detect HUD(peak g·pulse width·Δt), SRS는 로그-로그 + Q 토글, HIC는 적분창 드래그→실시간 지표. drop-contour-time은 field 위에 시간 스크럽.
(b) 새 패밀리: srs는 xy로 되나 drop-contour-time(field), drop-orientation-polar(polar)은 신규. 충격파 3D 전파는 mesh3d+time-slider.

---

## C. 진동/모달 (Vibration / Modal / NVH)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frf-bode | FRF / 전달함수 (Bode) | 가진→응답 주파수응답 | 주파수 f [Hz] | mag[dB]+phase[deg] | 공진·반공진·위상 | 입출력쌍 or H(f), fs, 로그축 | bode | dual-log-axis, mag-phase-stack, peak-detect, q-factor | spectral.tf_estimate | xy | ★★★★ |
| frf-nyquist | FRF Nyquist | 전달함수 복소평면 | Re(H) | Im(H) | 모달 원·감쇠 식별 | H(f) 복소, 단위 | bode | nyquist-mode, mode-circle-fit, freq-marker | spectral.complex_h | xy | ★★★★ |
| mode-shape-3d | 모드 형상 | 고유진동 변형형상 | 3D geom | 변위(컬러+변형) | n번째 모드 형태 | 메시, 모드 변위, 모드#, scale | cad-3d-viewer | modal-deform, surface-colormap, mode-selector, animate-toggle | cad.modal_displace | mesh3d | ★★★★★ |
| mode-shape-2d | 모드 형상(2D 단면) | 평면 모드 컬러맵 | X[mm] | Y[mm]/z=|φ| | 단면 모드 분포 | 모드 필드, 규칙성 | contour-heatmap | grid-field, mode-selector, color-scale-legend | field.interp2d | field | ★★★★ |
| campbell-diagram | 캠벨 다이어그램 | 회전수 vs 고유진동수 | 회전수 [rpm] | 주파수 [Hz] | 공진교차(crossing), order line | order 정의, rpm 범위 | scatter | order-lines, crossing-marker, resonance-band | — | xy | ★★★ |
| psd-random | PSD (랜덤 진동) | random vib 응답/입력 | 주파수 f [Hz] | PSD [g²/Hz] | 스펙트럼 밀도·RMS·grms | fs, window, ENBW, 로그-로그 | fft-spectrum | log-log, grms-badge, profile-overlay, breakpoint-marker | spectral.psd | xy | ★★★★ |
| sine-sweep | 사인 스윕 응답 | sweep 가진 응답 | 주파수 f [Hz] | 응답 [g] or [mm] | 공진 추종·전달률 peak | sweep 범위, fs, 로그축 | frf-bode | sweep-track, peak-detect, transmissibility | spectral.tf_estimate | xy | ★★★ |
| transmissibility | 전달률 | 입력 대비 출력 비 | 주파수 [Hz] | T = out/in [-] | 절연/증폭 대역 | 입출력쌍, fs | frf-bode | dual-log-axis, unity-line, peak-detect | spectral.tf_estimate | xy | ★★★ |
| waterfall-spectrogram | 워터폴/스펙트로그램 | 시간-주파수 진화 | 주파수[Hz] | 시간[s]/z=mag[dB] | order·공진 시간변화 | fs, window, hop, 색맵 | contour-heatmap | stft-field, color-scale-legend, order-overlay | spectral.stft | field | ★★★★★ |
| mac-matrix | MAC 매트릭스 | 모드 상관(CAE-test) | 모드# (i) | 모드# (j)/z=MAC | 모드쌍 일치도(0–1) | 모드벡터 두 세트 | (matrix) | cell-heatmap, diag-highlight, value-labels | modal.mac | matrix | ★★★ |
| modal-bar | 고유진동수 막대 | 모드별 주파수/유효질량 | 모드# | 주파수[Hz]/질량[%] | 모드 분포·참여질량 | 모드 데이터 | base-xy(bar) | bar-aggregate, value-labels, target-band | — | xy | ★ |

(a) 인터랙션: Bode/Nyquist는 mag-phase 동기 크로스헤어·Q-factor 호버·공진 마커; PSD/random은 grms 실시간 적분·프로파일(시험 규격) 오버레이; Campbell은 order line 위 crossing 강조; mode-shape는 mode-selector + animate + deform scale; waterfall/MAC는 cell/probe 픽킹.
(b) 새 패밀리: mode-shape-3d(mesh3d/cad), mode-shape-2d·waterfall-spectrogram(field), mac-matrix(matrix), frf-nyquist는 xy 가능. Campbell/PSD/Bode/sine-sweep은 xy-core 위에서 충분.

---

## D. 피로/내구 (Fatigue / Durability) — 폴더블 힌지 포함

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s-n-curve | S-N 곡선 (Wöhler) | 응력기반 수명 | 수명 N [cycles] | 응력진폭 S [MPa] | 피로한도·기울기·run-out | 응력비 R, run-out 임계, 로그-로그 | scatter | log-log, runout-marker, basquin-fit, scatter-band | fatigue.basquin | xy | ★★★ |
| e-n-curve | ε-N 곡선 | 변형률기반 저주기피로 | 반전수 2Nf | 변형률진폭 Δε/2 | 탄성+소성 변형 수명 | 재료 ε-N 계수, 로그축 | s-n-curve | log-log, elastic-plastic-split, coffin-manson-fit | fatigue.coffin_manson | xy | ★★★★ |
| goodman-haigh | Goodman/Haigh 선도 | 평균응력 보정 | 평균응력 σm [MPa] | 응력진폭 σa [MPa] | 안전영역·Goodman/Gerber line | σ_u, σ_y, σ_e | scatter | safe-envelope, goodman-gerber-lines, operating-point | fatigue.mean_stress | xy | ★★★★ |
| rainflow-matrix | 레인플로우 행렬 | 사이클 카운팅 결과 | 평균(or range) | 진폭/z=count | 하중 히스토리 사이클 분포 | bin 정의, 단위 | (matrix) | cell-heatmap, value-labels, marginal-bars | fatigue.rainflow | matrix | ★★★★ |
| damage-accumulation | 누적손상 (Miner) | 손상 누적 곡선 | cycle/block | 누적 D [-] | D→1 도달, 잔여수명 | S-N, 하중블록 | base-xy | threshold-line(D=1), step, named-markers | fatigue.miner | xy | ★★★ |
| hinge-life-cycle | 폴더블 힌지 수명 | folding 내구 cycle | 폴딩 횟수 [cycles] | 응력/강성/토크 잔존[%] | 수명열화·목표 cycle 도달 | 목표 cycle, 열화 지표 단위 | base-xy | target-line, degradation-fit, runout-marker | fatigue.degradation | xy | ★★★ |
| hinge-torque-cycle | 힌지 토크-각도 (사이클) | folding 토크 이력 | 폴딩각 θ [deg] | 토크 [N·mm] | free-stop·히스테리시스·열화 | 각도/토크 단위, 사이클# | hysteresis | cycle-color, loop-area, cycle-slider | fatigue.cycle_split | xy | ★★★ |
| weld-solder-damage | 손상 분포 컨투어 | 피로손상 핫스팟 맵 | X[mm] | Y[mm]/z=D | 어디서 먼저 파손 | D 필드, 규칙성, 임계 | stress-contour | grid-field, threshold-mask, hotspot-marker | field.interp2d | field | ★★★★★ |
| life-contour-3d | 수명 컨투어(3D) | 메시 위 Nf 맵 | 3D geom | z=log Nf | 최단수명 위치 | 메시, Nf 필드 | cad-3d-viewer | surface-colormap, min-life-marker, section-plane | cad.map_field_to_mesh | mesh3d | ★★★★★ |
| fatigue-knockdown | 피로 감소계수 | 표면/노치/크기 보정 | 보정인자(범주/연속) | knockdown [-] | Kf, 노치/크기/표면 영향 | 인자 정의 | base-xy | bar-aggregate or curve | — | xy | ★★ |

(a) 인터랙션: S-N/ε-N은 로그-로그 + 산포밴드(50/90%) + run-out 화살표 마커 + Basquin/Coffin-Manson 피팅 호버(계수 HUD); Goodman/Haigh는 safe-envelope fill + operating-point 안전여유 표시; rainflow는 cell 픽킹 + marginal 히스토그램; damage/hinge-life는 D=1·target line 교차 강조 + 잔여수명 badge; hinge-torque는 cycle-slider로 사이클별 loop.
(b) 새 패밀리: rainflow-matrix(matrix), weld-solder-damage(field), life-contour-3d(mesh3d). 나머지 xy-core(로그-로그 plugin).

---

## E. 열-기구 (Thermal-Mechanical / Thermal)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temp-transient | 온도-시간 (transient) | 발열/방열 과도응답 | 시간 t [s] | 온도 T [°C] | 정착시간·피크온도 | T 단위, 시간, (한계온도) | time-series | threshold-line(Tmax), peak-detect, named-markers | — | xy | ★★ |
| temp-contour | 온도 컨투어 | 표면 온도 분포 맵 | X[mm] | Y[mm]/z=T[°C] | 핫스팟·온도구배 | T 단위, 규칙성, 색맵 한계 | contour-heatmap | grid-field, iso-lines, hotspot-marker, color-scale-legend | field.interp2d, field.isocontour | field | ★★★★★ |
| temp-contour-3d | 3D 온도 컨투어 | 메시 위 T 맵 | 3D geom | z=T on surface | 실제 형상 위 발열분포 | 메시, T 필드, 단위 | cad-3d-viewer | surface-colormap, section-plane, probe-pick | cad.map_field_to_mesh | mesh3d | ★★★★★ |
| thermal-deformation | 열변형 | 온도→변형 곡선/맵 | 온도 ΔT [°C] | 변형 [µm] | CTE 기반 팽창·휨 | CTE, ΔT, 단위 | base-xy | live-tangent(=CTE), regression | calculus.derivative | xy | ★★ |
| cte-mismatch | CTE 미스매치 응력 | 이종재 계면 응력 | 온도 ΔT [°C] | 계면응력 [MPa] | bimetal 응력·박리위험 | 재료쌍 CTE, E, 두께 | base-xy | named-markers, threshold-line, region-shading | thermal.cte_stress | xy | ★★★ |
| thermal-cycle-hysteresis | 열사이클 히스테리시스 | T-변형 루프 | 온도 [°C] | 변형/응력 | 열피로 루프·잔류 | 사이클#, 단위 | hysteresis | cycle-color, loop-area, cycle-slider | fatigue.cycle_split | xy | ★★★ |
| heatflux-contour | 열유속 벡터/맵 | 방열경로 시각화 | X[mm] | Y[mm]/z=q벡터 | 열흐름 방향·경로 | q 단위, 벡터필드 | contour-heatmap | grid-field, vector-arrows, streamline | field.vector | field | ★★★★★ |
| warpage-thermal | 리플로우 휨(열) | 솔더리플로우 PCB 휨 | 온도/시간 | 휨 [µm] / z 맵 | reflow 중 워피지 진화 | 온도프로파일, 휨 단위 | warpage-map | grid-field, time-slider, ref-plane-subtract | field.bestfit_plane | field | ★★★★ |

(a) 인터랙션: transient는 한계온도 라인·정착시간 마커; contour는 iso-therm 호버·probe T값·핫스팟; thermal-def는 live-tangent를 CTE[ppm/°C]로 재라벨; heatflux는 vector-arrows + streamline 토글; warpage-thermal은 온도프로파일과 휨맵 time-slider 동기.
(b) 새 패밀리: temp-contour·heatflux·warpage-thermal(field, 특히 heatflux는 벡터장), temp-contour-3d(mesh3d). transient/thermal-def/cte는 xy.

---

## F. 접촉/압력 · 좌굴 · 굽힘 · gasket/seal · 표면압흔

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| contact-pressure-map | 접촉압력 분포 맵 | gasket/버튼/커넥터 접촉 | X[mm] | Y[mm]/z=P[MPa] | 접촉면 압력·미접촉부 | P 단위, 규칙성, 색맵 | contour-heatmap | grid-field, contact-mask, color-scale-legend, hotspot-marker | field.interp2d | field | ★★★★★ |
| contact-pressure-line | 접촉압력 단면선 | 단면 따라 압력 | 위치 [mm] | 압력 P [MPa] | seal line 압력 균일성 | P 단위, 경로 | base-xy | region-shading, threshold-line(seal min), named-markers | — | xy | ★★ |
| gap-contour | 갭/이격 맵 | 조립 갭·간섭 | X[mm] | Y[mm]/z=gap[µm] | 들뜸·간섭(음수) 영역 | gap 단위, 규칙성 | contour-heatmap | grid-field, zero-cross-iso, color-scale-legend | field.interp2d | field | ★★★★ |
| buckling-load | 좌굴 하중계수 | 좌굴 eigenvalue | 모드# / 하중 | 좌굴계수 λ | 임계하중·모드별 | λ 정의, 하중기준 | base-xy(bar) | bar-aggregate, critical-line(λ=1), value-labels | — | xy | ★★ |
| buckling-mode-3d | 좌굴 모드 형상 | 좌굴 변형형상 | 3D geom | 변위(컬러+변형) | 좌굴 형태 | 메시, 모드 변위, scale | mode-shape-3d | modal-deform, surface-colormap, mode-selector | cad.modal_displace | mesh3d | ★★★★★ |
| load-deflection-postbuckling | 하중-처짐 (좌굴후) | snap-through/post-buckle | 처짐 [mm] | 하중 [N] | 임계점·snap·후좌굴 | 단위 | force-displacement | live-tangent, limit-point-marker, region-shading | calculus.derivative | xy | ★★★ |
| gasket-pressure-curve | 가스켓 압축 곡선 | seal 압축-반력 | 압축량 [mm] | 반력/선압 [N/mm] | seal force·set | seal min line, 단위 | force-displacement | region-shading(seal band), named-markers, live-tangent | — | xy | ★★ |
| indentation-curve | 압흔/경도 곡선 | 표면 압입(나노인덴)| 압입깊이 h [nm] | 하중 P [mN] | load-unload, 경도/E | 면적함수, unloading 구간 | force-displacement | load-unload-split, oliver-pharr-fit, live-tangent | mechanics.oliver_pharr | xy | ★★★★ |
| indentation-map | 압흔 깊이 맵 | 표면 압흔 분포 | X[µm] | Y[µm]/z=depth | 압흔 형상·잔류 | depth 단위, 규칙성 | contour-heatmap | grid-field, profile-section, color-scale-legend | field.interp2d | field | ★★★★ |
| bend-stiffness-curve | 굽힘 강성 곡선 | 패널 3점/4점 굽힘 | 처짐/각도 | 하중/모멘트 | flexural rigidity | span, 단면 | 3point-bend | live-tangent, named-markers | units.flexural_stress | xy | ★★★ |

(a) 인터랙션: 압력맵은 contact-mask(미접촉 회색)·probe P·seal-line 단면 추출(맵→선 연동); gap은 zero-crossing iso(간섭=음수 역색); 좌굴은 λ=1 임계선·모드 애니메이션; indentation은 load/unload 분리 + Oliver-Pharr 피팅 HUD(H, Er); gasket은 seal min band fill.
(b) 새 패밀리: contact-pressure-map·gap-contour·indentation-map(field), buckling-mode-3d(mesh3d). 선/곡선형(contact-line, gasket, indentation-curve, buckling-load)은 xy.

---

## G. 크리프 · 솔더조인트 신뢰성 · 도금/박리 · 음향(NVH)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| creep-strain-time | 크리프 변형-시간 | 장기 변형(상온/고온) | 시간 t [h] (log) | 변형 ε [%] | 1·2·3차 크리프 단계 | 온도, 응력, 로그축 | time-series | log-x, stage-region, creep-rate-tangent | calculus.derivative | xy | ★★★ |
| creep-rate-stress | 크리프 속도-응력 | Norton 법칙 | 응력 [MPa] (log) | ε̇ [1/s] (log) | 응력지수 n | 온도, 로그-로그 | s-n-curve | log-log, norton-fit | creep.norton | xy | ★★★ |
| stress-relaxation | 응력 완화 | 볼트/스냅핏 풀림 | 시간 [h] (log) | 응력 [MPa] | 잔류응력 감소·잔존 클램프 | 단위, 로그축 | creep-strain-time | log-x, residual-badge, fit | calculus.fit | xy | ★★ |
| solder-creep-fatigue | 솔더 크리프-피로 수명 | BGA/SMT 신뢰성 | 사이클 N (log) | Δγ or Wp | Coffin-Manson/Darveaux 수명 | 변형범위, 재료계수, 로그축 | e-n-curve | log-log, darveaux-fit, runout-marker | fatigue.darveaux | xy | ★★★★ |
| solder-damage-map | 솔더 조인트 손상맵 | 조인트별 손상 분포 | 조인트 X | 조인트 Y/z=D | 어느 볼이 먼저 crack | D 필드, 임계 | (matrix) | cell-heatmap, threshold-mask, value-labels, worst-marker | — | matrix | ★★★ |
| solder-life-3d | 솔더 수명(3D) | 패키지 위 Nf 맵 | 3D geom | z=log Nf | 최단수명 조인트 위치 | 메시, Nf 필드 | life-contour-3d | surface-colormap, min-life-marker, section-plane | cad.map_field_to_mesh | mesh3d | ★★★★★ |
| delamination-energy | 박리 에너지 / G-curve | 도금/접착 박리 | 균열길이 a [mm] | G or G/Gc [J/m²] | 박리저항·임계 Gc | Gc, 단위 | base-xy | threshold-line(Gc), region-shading, named-markers | fracture.energy_release | xy | ★★★ |
| peel-force-curve | 박리력 곡선 | 필름/도금 peel test | 변위/위치 [mm] | 박리력 [N] | peel 평균력·불안정 | 폭 b(N/mm 환산 시) | force-displacement | unit-convert(N/mm), plateau-band, named-markers | units.peel_strength | xy | ★★ |
| adhesion-bar | 접착/도금 밀착 막대 | 부위별 밀착강도 | 부위(범주) | 강도 [MPa]/[N] | 약한 부위 식별 | 단위 | base-xy(bar) | bar-aggregate, threshold-line, value-labels | — | xy | ★ |
| acoustic-frf | 음향 FRF | NVH 음압 전달 | 주파수 [Hz] | SPL [dB] / phase | 가진→음압, 공진 booming | fs, ref 압력(dB), 로그축 | frf-bode | dual-log-axis, mag-phase-stack, a-weighting, peak-detect | spectral.tf_estimate, spectral.aweight | xy | ★★★★ |
| acoustic-radiation-3d | 음향 방사맵(3D) | 표면 방사음압 | 3D geom | z=SPL[dB] on surface | 어느 면이 소리 방사 | 메시, SPL 필드 | cad-3d-viewer | surface-colormap, freq-selector, section-plane | cad.map_field_to_mesh | mesh3d | ★★★★★ |
| order-track | 오더 트래킹 | 회전기인 NVH order | rpm or 주파수 | order 진폭 [dB] | order 성분 분리 | rpm, order 정의, fs | waterfall-spectrogram | order-extract, order-lines | spectral.order | field | ★★★★ |

(a) 인터랙션: creep/relaxation은 로그-시간축 + stage region(1·2·3차) + creep-rate 접선; solder는 Darveaux/Coffin-Manson 피팅 HUD; delamination/peel은 Gc 임계선·plateau band; acoustic-frf는 A-weighting 토글·dB 기준·SPL peak; order-track은 waterfall 위 order line 호버.
(b) 새 패밀리: solder-damage-map(matrix), solder-life-3d·acoustic-radiation-3d(mesh3d), order-track(field/waterfall). creep/relaxation/solder수명곡선/delamination/peel/acoustic-frf는 xy-core(로그축 plugin).

---

## H. 시험상관(CAE-test correlation) · 통계/DOE · 멀티피직스 (횡단)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cae-test-overlay | CAE-시험 상관 | 예측 vs 실측 겹침 | 공통 x | 공통 y | 상관·오차대역 | 두 데이터셋 단위 일치 | base-xy | dual-series-style(sim/test), error-band, residual-panel | stats.residual | xy | ★★ |
| correlation-scatter | 상관 산점 (1:1) | CAE vs test 점도 | test 값 | sim 값 | 1:1선·R²·편향 | 단위 | scatter | unity-line, regression, r2-badge, error-band | stats.regression | xy | ★★ |
| tolerance-band | 허용오차 밴드 | spec ± 한계 비교 | x(공정/조건) | 측정값 | spec 이탈 | USL/LSL | base-xy | spec-band, out-of-spec-mark | — | xy | ★ |
| histogram-dist | 히스토그램/분포 | 산포·정규성 | 값 (bin) | 빈도/밀도 | 분포·치우침·Cpk | bin, USL/LSL | base-xy(bar) | bin-aggregate, normal-fit, cpk-badge, spec-lines | stats.histogram | xy | ★★ |
| boxplot-group | 박스플롯(그룹) | 조건별 산포비교 | 그룹(범주) | 값 분포 | 중앙/IQR/이상치 | 그룹 정의 | scatter | box-whisker, outlier-mark, mean-diamond | stats.quartiles | xy | ★★ |
| pareto-chart | 파레토 | 기여인자 우선순위 | 인자(범주, 정렬) | 기여+누적[%] | vital few | 인자 정의 | base-xy(bar) | sorted-bar, cumulative-line, 80pct-line | stats.pareto | xy | ★★ |
| tornado-sensitivity | 토네이도(민감도) | DOE 인자 영향 | 효과크기 | 인자(정렬) | 어떤 인자가 지배적 | 인자, 기준선 | base-xy(bar) | centered-bar, baseline-line, sorted | doe.main_effects | xy | ★★ |
| main-effects | 주효과도 | DOE 수준별 평균 | 인자수준 | 응답평균 | 수준별 효과 | DOE 설계 | base-xy | level-markers, grand-mean-line, multi-panel | doe.main_effects | xy | ★★ |
| interaction-plot | 교호작용도 | DOE 2-factor 상호작용 | 인자A 수준 | 응답 (B별 선) | 교호작용 유무 | DOE 설계 | base-xy | grouped-lines, parallel-check | doe.interaction | xy | ★★ |
| response-surface | 반응표면(RSM) | 2인자 응답맵 | 인자A | 인자B/z=응답 | 최적영역·등고 | 인자범위, z 단위 | contour-heatmap | grid-field, iso-lines, optimum-marker | doe.rsm_fit | field | ★★★★ |
| response-surface-3d | 반응표면 3D | RSM surface | A | B/z=응답(높이) | 곡면·안장점 | 인자범위, z | (mesh3d) | surface-mesh, optimum-marker, contour-floor | doe.rsm_fit | mesh3d | ★★★★ |
| multiphysics-coupled | 멀티피직스 듀얼축 | 열-구조-전기 동시 | 공통 x | 좌/우 다물리량 | 연성 응답 비교 | 좌우 단위 | dual-axis | secondary-y, axis-color-match, sync-cursor | — | xy | ★★ |

(a) 인터랙션: cae-test-overlay/correlation은 sim=실선·test=점, residual 패널 동기, R²·bias badge, 오차밴드; histogram은 normal-fit + Cpk + spec line; Pareto/tornado는 정렬 막대 + 80%/baseline; main-effects/interaction은 멀티패널 + grand-mean; RSM은 등고+최적점 마커.
(b) 새 패밀리: response-surface(field), response-surface-3d(mesh3d). 나머지(상관/히스토/박스/파레토/토네이도/주효과/교호/멀티피직스 듀얼축)는 모두 xy-core 위 plugin 합성으로 가능.

---

## (a) 도메인 특유의 인터랙션/오버레이 — 횡단 정리

- **field 패밀리 공통 (모든 contour/heatmap)**: probe-pick(클릭 z값 HUD), iso-line 호버 추적, color-scale-legend(역색맵 토글: SF·gap은 낮을수록 위험), threshold-mask(σ_y/Gc/SF=1 초과셀 강조), hotspot/min-marker 자동, deform-scale·time-slider, 단면 추출(field→xy 선 연동).
- **mesh3d/cad 패밀리 공통**: orbit/pan/zoom, view-cube(iso/front/top), section-plane(clipping + capping), surface-colormap, modal-deform + animate, exploded-view, measure(거리/각/반경 픽킹), probe-pick.
- **time 계열 (drop/vibration/thermal/creep)**: time-slider가 field/3d 컨투어와 동기(시점→분포), peak/pulse-width 마커, threshold/limit line, 적분창 드래그(HIC·grms·toughness 실시간).
- **로그축 계열 (S-N/ε-N/PSD/Bode/creep/solder)**: log-log/log-x + decade minor grid + 피팅 호버(Basquin/Coffin-Manson/Norton/Darveaux 계수 HUD) + run-out 화살표 마커.
- **cycle/hysteresis 계열 (hinge torque/thermal cycle/solder)**: cycle-slider, cycle-color 그라데이션, loop-area 적분 badge.
- **correlation/DOE 계열**: sim/test 스타일 분기 + residual 패널 + R²/Cpk/bias badge, 정렬막대(Pareto/tornado), spec-band out-of-spec 강조.
- **live-tangent 재라벨 재사용**: stress-strain=Et[GPa], force-disp=강성[N/mm], thermal=CTE[ppm/°C], creep=ε̇[1/s], EI=굽힘강성 — 같은 plugin, 단위만 recipe가 교체.

## (b) 새 엔진패밀리가 필요한 항목 (2D xy-core로 불가)

기존 로드맵은 **field(contour/heatmap, #13)** 와 **cad-viewer(3D, §18)** 만 명시. 본 MCAE 카탈로그는 추가로 아래 패밀리를 요구한다.

1. **field — 2D 스칼라/벡터 필드 (등고선·heatmap)** [로드맵 #13 확장]: stress/temp/warpage/deformation/safety-factor/contact-pressure/gap/indentation/damage contour, mode-shape-2d, drop-contour-time, response-surface. 핵심: 2D 보간 + iso-contour 추출 + 색맵 legend. **벡터장 변종(heatflux/streamline)** 은 vector-arrows 서브엔진 필요.
2. **mesh3d / cad-viewer — 3D 형상 위 필드 컬러맵 + 모달 변형** [§18 cad-viewer 계열]: stress/temp/life/acoustic contour-3d, mode-shape-3d, buckling-mode-3d, solder-life-3d, response-surface-3d. three.js + GLTFLoader + surface-colormap + section-plane. STEP→GLB(postprocess/cad.py), 단위계 requires.
3. **matrix — 격자 셀 heatmap-table** [신규, table 패밀리 인접]: rainflow-matrix, mac-matrix, solder-damage-map. 이산 셀 + 값 라벨 + marginal bars. waterfall/spectrogram도 시간-주파수 grid라 field로 사상 가능하나 STFT 전용 plugin 필요.
4. **polar / radial — 극좌표 2D** [신규]: drop-orientation-polar(낙하자세 민감도), 방사형 민감도/방향성 응답. 각도-반경 좌표계라 xy-core 좌표변환으로 불가(별도 scaleR/scaleθ).
5. **specialized 2D (저빈도, ECAE 인접)**: **smith-chart**(RF 임피던스 — ECAE 안테나/RF 정합), **eye-diagram**(고속 시그널 인테그리티 — ECAE), **bathtub-curve**(BER vs 샘플시점 — SI). MCAE 본류는 아니나 "스마트폰 system/multiphysics + ECAE" 맥락에서 자매 패밀리. smith/eye는 각자 전용 좌표계·렌더라 별도 패밀리.

**xy-core로 충분(신규 패밀리 불필요)한 것**: A·B·C·D·E·F·G·H의 모든 선/곡선/막대/로그-로그/듀얼축/히스토그램/박스플롯/Bode/Nyquist/PSD/Campbell/sine-sweep — 즉 **데이터가 (x,y) 시리즈로 표현되는 모든 것**은 base-xy + plugin 합성 + 로그축/dual-axis/bar/hysteresis plugin으로 커버된다. 신규 패밀리는 오직 **필드(2D z)·3D 형상·이산 매트릭스·극좌표·전용 좌표계(smith/eye)** 에서만 필요하다.

---

참조 파일(절대경로): 카탈로그 SSOT `D:\graph-skill\src\graph_skill\data\catalog\types.json` (현재 base-xy 1블록만 — 위 타입들을 블록으로 추가), 로드맵·field/cad 패밀리 근거 `D:\graph-skill\docs\SKILL-PLAN.md` (§6 extends 평탄화, §12.2 타입 로드맵 16행, §18 엔진패밀리 일반화), 엔진 자산 `D:\graph-skill\src\graph_skill\data\engines\xy-core\engine.js`, 부팅 디스패치 `D:\graph-skill\src\graph_skill\data\shell\boot.js`, 스킬 명세 `D:\graph-skill\.claude\skills\graph-skill\SKILL.md`.