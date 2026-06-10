I have everything needed. The `xy-core` engine is Canvas-2D, XY-only (multi-series line/markers/step). Now I'll produce the comprehensive system/multiphysics/statistics cataloging, mapped onto the catalog block model (engine family + extends + plugins + requires + post), flagging which items need new engine families beyond 2D xy-core.

---

# System / Multiphysics / 통계·DOE 결과 도시 카탈로그 (MX 모바일)

전제: `xy-core`(Canvas 2D, base-xy)는 **다중 XY 시리즈**(line/markers/step) + 자동 인터랙션만 보장한다. 등고선/벡터장/3D surface/polar/smith/eye-diagram/색도다이어그램/맵 등은 **새 엔진 패밀리**가 필요하므로 표의 `엔진패밀리` 열에 명시하고, 표 아래 (b)에 별도 집계했다. "상속 베이스"는 catalog `extends` 체인, "feature plugin"은 합성할 plugin 파일, "post"는 후처리 훅이다. 난이도 = xy-core로 바로 되면 낮음 / plugin 추가 중간 / 새 엔진패밀리 높음.

---

## 1) 열 (Thermal / Skin-temp)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(validate requires) | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| thermal-skin-map | 표면온도 맵 | 발열 검증, 손닿음 한계 | X 위치(mm) | Y 위치(mm) / T(°C) | 후면/측면 표면 온도 2D 히트맵 | 그리드 해상도, T범위(min/max), 외기온, 발열 시나리오 | heatmap-2d | colormap, isotherm-overlay | hotspot-extract | **field-2d**(신규) | 높음 |
| thermal-skin-contour | 등온선도 | 손닿음 온도 영역 분류 | X(mm) | Y(mm) / T(°C) | 등온선 + 45°C 손닿음 한계선 | 한계온도(예 45°C), 등온 간격 | thermal-skin-map | contour-lines, threshold-band | area-over-threshold | **field-2d** | 높음 |
| thermal-rise-curve | 승온 곡선 | 시간별 온도 상승/포화 | 시간(s/min) | 온도(°C) | 부위별 T(t), 포화·시정수 | 부위 레이블, 외기온, 측정점 | base-xy | annotate-tau, spec-line | tau-fit, steady-state | xy-core | 낮음 |
| thermal-thermocouple-corr | 열전쌍 상관 | CAE vs 측정 부위별 | 측정 T(°C) | 해석 T(°C) | y=x 대각 + R², 부위 산점 | 측정점 매핑, 허용오차 | corr-scatter | identity-line, error-band, r2-badge | r2-compute | xy-core | 중간 |
| thermal-image-overlay | 열화상 대비 | IR 카메라 vs CAE | X(mm) | Y(mm) / ΔT(°C) | IR 이미지 위 CAE 차이맵 | IR 이미지 해상도/정렬, 색맵 범위 | thermal-skin-map | image-underlay, diff-map | registration | **field-2d** | 높음 |
| thermal-budget-bar | 열 버짓 | 발열원 기여 분해 | 발열원(SoC/PMIC/Cam) | 전력(W)/ΔT(°C) | 컴포넌트별 발열 기여 스택 | 컴포넌트 리스트, 단위 | base-xy(bar) | stacked-bar, pct-label | sum-check | xy-core | 중간 |

도메인 특유 인터랙션/오버레이: 마우스 hover 시 (x,y) 위치의 절대 T 읽기, 45°C 손닿음 한계 toggle, isotherm 단계 슬라이더, IR↔CAE blend 슬라이더, hotspot top-N 핀, ΔT(diff) 모드 토글.

---

## 2) 음향 (Acoustic)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| acoustic-spl-freq | SPL 주파수응답 | 스피커 음압 튜닝 | 주파수(Hz, log) | SPL(dB) | SPL(f), 목표 대비 편차 | 기준거리, 입력전압, 목표곡선 | base-xy | log-x-default, target-band | smooth-octave | xy-core | 낮음 |
| acoustic-thd-freq | THD 곡선 | 왜곡 평가 | 주파수(Hz, log) | THD(%) | 고조파 왜곡 vs 주파수 | 입력레벨(dB SPL), 한계% | acoustic-spl-freq | limit-line, dual-axis | thd-peak | xy-core | 낮음 |
| acoustic-directivity-polar | 지향성 폴라 | 방사 패턴 | 각도(0–360°) | SPL(dB) 반경 | 주파수별 지향 폴라 | 측정 각도스텝, 주파수 셋 | polar-base | freq-rings, db-radial | beamwidth | **polar**(신규) | 높음 |
| acoustic-impedance | 임피던스 곡선 | 공진/Fs 식별 | 주파수(Hz, log) | |Z|(Ω) & phase(°) | 전기 임피던스 크기·위상 | Fs 기대범위, 측정셋업 | base-xy | dual-y-phase, fs-marker | fs-detect | xy-core | 중간 |
| acoustic-waterfall | 워터폴(CSD) | 누적 스펙트럼 감쇠 | 주파수(Hz) | 시간(ms) / SPL(dB) | 시간감쇠 3D 폭포도 | 시간윈도, dB동적범위 | surface-3d | time-slices, db-z | decay-fit | **surface-3d**(신규) | 높음 |
| acoustic-spectrogram | 스펙트로그램 | 시간-주파수 에너지 | 시간(s) | 주파수(Hz) / dB | STFT 에너지 맵 | FFT윈도, 샘플레이트 | heatmap-2d | colormap, db-scale | stft | **field-2d** | 높음 |

도메인 특유: 폴라에서 주파수 ring isolate, dB 동적범위 슬라이더, beamwidth(-6dB) 자동 표기, 임피던스 Fs/Qts 핀, 옥타브 스무딩 토글, 목표 곡선 overlay.

---

## 3) 광학/디스플레이 (Display Optics)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| display-cie1931-gamut | CIE 1931 색역 | 색재현/gamut 비교 | CIE x | CIE y | 말굽 + 패널 삼각형 vs sRGB/DCI-P3 | 측정 primaries(R/G/B xy), 기준 gamut | chromaticity-base | spectral-locus, gamut-triangle, coverage-fill | gamut-coverage% | **chromaticity**(신규) | 높음 |
| display-luminance-map | 휘도 균일도 맵 | 9/25점 균일도 | X 위치 | Y 위치 / L(nit) | 화면 휘도 분포·균일도% | 측정점 그리드, 목표 균일도 | heatmap-2d | grid-points, uniformity | uniformity-calc | **field-2d** | 높음 |
| display-viewing-angle-polar | 시야각 폴라 | 각도별 휘도/색변화 | 방위각(°) | 극각(°) / L 또는 ΔE | 시야각에 따른 휘도·ΔE 등고 | 각도 그리드, 메트릭(L/ΔE) | polar-base | iso-contour, half-luminance | ang-half | **polar** | 높음 |
| display-reflectance-spectrum | 반사율 스펙트럼 | 반사/AG·AR 평가 | 파장(nm) | 반사율(%) | 파장별 반사율, SCI/SCE | 측정 파장범위, 광원 | base-xy | visible-band-shade | avg-reflect | xy-core | 낮음 |
| display-gamma-curve | 감마 곡선 | 계조 선형성 | 입력 계조(0–255) | 휘도(정규화) | 측정 감마 vs 목표 2.2 | 비트심도, 목표감마 | base-xy | target-gamma, log-toggle | gamma-fit | xy-core | 낮음 |
| display-color-volume-3d | 색입체(색량) | 색재현 부피 | a* | b* / L* | 3D 색입체(CIELAB) | 색공간(Lab), 기준 부피 | volume-3d | lab-axes, ref-shell | volume-calc | **surface-3d** | 높음 |
| display-deltaE-map | ΔE 분포 맵 | 색정확도 공간분포 | X 위치 | Y 위치 / ΔE00 | 패치/위치별 색오차 | 기준색, ΔE식(00/76) | heatmap-2d | colormap, tolerance-line | deltaE-stats | **field-2d** | 높음 |

도메인 특유: gamut에서 기준 색역 토글(sRGB/P3/Rec.2020) + coverage% 배지, 백색점 핀, 시야각 polar에서 half-luminance 각 자동표기, ΔE 한계(보통 3) 임계 band.

---

## 4) 카메라/광학계 (Camera Optics)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| camera-mtf-freq | MTF 곡선 | 렌즈 해상력 | 공간주파수(lp/mm) | MTF(0–1) | sagittal/tangential MTF | 필드위치(center/0.7F), 파장 | base-xy | sag-tan-pair, nyquist-line | mtf50 | xy-core | 낮음 |
| camera-mtf-field | MTF vs 상고 | 화면 전체 해상력 | 상고(%/mm) | MTF@freq | 상고별 MTF 저하 | 평가 주파수, 필드 정의 | base-xy | sag-tan-pair | field-avg | xy-core | 중간 |
| camera-aberration-ray | 광선수차도 | 수차 분석 | 동공좌표 | 횡수차(µm) | 파장별 ray fan | 파장 셋, 동공정의 | base-xy | wavelength-series | rms-spot | xy-core | 중간 |
| camera-spot-diagram | 스폿 다이어그램 | 결상 점상 | 동공 X | 동공 Y / 강도 | 필드/파장별 스폿 산포 | 필드각, Airy 반경 | scatter-2d | airy-circle, rms-ring | spot-rms | **field-2d** | 높음 |
| camera-distortion-grid | 왜곡 그리드 | 기하 왜곡 | X(상면) | Y(상면) | 격자 왜곡(핀쿠션/배럴) | 격자정의, %왜곡 | vector-field | grid-deform, ref-grid | distortion% | **vector-field**(신규) | 높음 |
| camera-relative-illum | 상대조도(비네팅) | 주변광량 저하 | 상고(%) | 상대조도(%) | 중심대비 주변 밝기 | 상고정의 | base-xy | cos4-ref | corner-illum | xy-core | 낮음 |
| camera-wavefront-map | 파면수차 맵 | 동공 위상오차 | 동공 X | 동공 Y / OPD(λ) | Zernike 파면 등고 | 파장, Zernike 차수 | heatmap-2d | zernike-contour | rms-wfe | **field-2d** | 높음 |

도메인 특유: MTF에 Nyquist/센서 주파수 수직선, sag/tan 페어 동시 isolate, 파장 시리즈 토글, 스폿에 Airy disk 원, 왜곡 grid에 reference grid overlay + 배율.

---

## 5) 안테나-인체 / 무선 (RF / SAR / Wireless)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rf-sar-map | SAR 분포 맵 | 인체 전자파흡수 | X 위치 | Y 위치 / SAR(W/kg) | 1g/10g 평균 SAR 핫스팟 | 평균질량(1g/10g), 한계(1.6/2.0), 주파수밴드 | heatmap-2d | colormap, limit-contour | peak-sar | **field-2d** | 높음 |
| rf-antenna-pattern-polar | 방사패턴 폴라 | 안테나 지향성 | 각도(°) | gain(dBi) 반경 | E/H-plane 방사 패턴 | 평면(E/H), 주파수, dB범위 | polar-base | e-h-plane, hpbw | hpbw-calc | **polar** | 높음 |
| rf-antenna-pattern-3d | 3D 방사패턴 | 입체 방사 | θ(°) | φ(°) / gain(dBi) | 구면 gain 패턴 | 각도 그리드, 주파수 | sphere-3d | gain-shell | directivity | **surface-3d** | 높음 |
| rf-return-loss | 반사손실(S11) | 임피던스 정합 | 주파수(GHz) | S11(dB) | 대역별 정합, -6/-10dB | 대상 밴드, 임계(dB) | base-xy | band-shade, limit-line | bandwidth | xy-core | 낮음 |
| rf-smith-chart | 스미스 차트 | 임피던스 정합 궤적 | Re(Γ) | Im(Γ) | 정규화 임피던스 궤적 | Z0, 주파수 스윕 | smith-base | constant-r-x, freq-markers | match-point | **smith**(신규) | 높음 |
| rf-vswr | VSWR 곡선 | 정재파비 | 주파수(GHz) | VSWR | 대역별 VSWR, 2:1 한계 | 대상밴드, 한계비 | base-xy | limit-line, band-shade | vswr-bw | xy-core | 낮음 |
| rf-efficiency-freq | 안테나 효율 | 방사/전체효율 | 주파수(GHz) | 효율(%) | 대역별 total/radiation eff. | 밴드정의 | base-xy | dual-series | band-avg | xy-core | 낮음 |
| wireless-throughput-range | 처리량 vs 거리 | 무선 성능 | 거리(m, log옵션) | Throughput(Mbps) | 거리별 TPUT 감소, RSSI | 환경(LOS/NLOS), 밴드, 기준값 | base-xy | rssi-dual-axis, knee | range-at-spec | xy-core | 중간 |
| wireless-tput-vs-rssi | TPUT vs RSSI | 링크 감도 | RSSI(dBm) | Throughput(Mbps) | 신호세기 대비 처리량 | 변조/MCS, 밴드 | base-xy | mcs-steps | sensitivity | xy-core | 낮음 |
| rf-eye-diagram | 아이 다이어그램 | 고속 신호 품질 | 시간(UI) | 전압(V) / 밀도 | 중첩 비트 아이 개구 | UI, 비트레이트, 임계 | eye-base | eye-mask, density-map | eye-height/width | **eye-diagram**(신규) | 높음 |
| rf-ber-curve | BER 곡선 | 비트오류율 | SNR/Eb·N0(dB) | BER(log) | SNR 대비 오류율 | 변조방식, 목표 BER | base-xy | log-y-default, target-ber | snr-at-ber | xy-core | 낮음 |

도메인 특유: SAR에 1.6/2.0 W/kg 한계 등고 + peak 핀, 폴라에 HPBW 자동표기 + E/H-plane isolate, 스미스에 등저항/등리액턴스 원 + 주파수 마커, 아이에 mask 합부 판정, throughput에 spec 거리 자동표기.

---

## 6) 배터리-시스템 / 전력 (Battery / Power)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| power-profile-time | 전력 프로파일 | 시나리오 소비전력 | 시간(s) | 전력(W)/전류(mA) | 사용시나리오 전력 파형 | 시나리오, 샘플레이트, 단위 | base-xy | step-style, avg-line | avg-power, energy∫ | xy-core | 낮음 |
| power-battery-discharge | 방전 곡선 | 용량/런타임 | 용량(mAh)/시간 | 전압(V) | 방전 전압 vs 용량, cutoff | C-rate, cutoff 전압 | base-xy | cutoff-line | runtime-est | xy-core | 낮음 |
| power-soc-time | SoC 추이 | 배터리 잔량 | 시간(h) | SoC(%) | 사용중 잔량 곡선 | 시나리오, 용량 | base-xy | spec-band | drain-rate | xy-core | 낮음 |
| power-thermal-coupled | 전력-발열 연성 | 전력↔온도 연성 | 시간(s) | 전력(W) & T(°C) | 전력과 온도 동시(이중축) | 부위, 단위, 외기온 | base-xy | dual-y-axis, lag-marker | thermal-lag | xy-core | 중간 |
| power-efficiency-load | 효율 vs 부하 | PMIC/충전 효율 | 부하전류(A) | 효율(%) | 부하별 변환효율 곡선 | 입력전압, 토폴로지 | base-xy | peak-eff | peak-eff-pt | xy-core | 낮음 |
| power-charge-curve | 충전 곡선 | CC-CV 충전 | 시간(min) | 전류(A)·전압(V)·SoC | CC/CV 구간, 충전시간 | 충전 프로토콜, 목표SoC | base-xy | cc-cv-region, dual-axis | time-to-80% | xy-core | 중간 |

도메인 특유: 전력 파형 위 이동평균/구간 에너지(∫) 표기, dual-axis 전력↔온도 동기 hover, CC→CV 전이점 마커, cutoff/spec band, 시나리오 구간 라벨링.

---

## 7) 시험상관 (CAE ↔ Test Correlation)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| corr-overlay | CAE-Test 오버레이 | 곡선 직접 대비 | (공통 x) | (공통 y) | CAE vs Test 곡선 중첩 | 동일 축/단위, 측정조건 | base-xy | test-vs-cae-style, residual-strip | rmse, max-err | xy-core | 낮음 |
| corr-scatter-r2 | 상관 산점도 | 일치도 정량 | 측정값 | 해석값 | y=x 대각 + R²/RMSE | 매칭 페어, 단위 | base-xy | identity-line, error-band, r2-badge | r2, slope | xy-core | 중간 |
| corr-error-bar | 오차 막대 | 항목별 편차 | 항목/케이스 | 오차(%/abs) | 케이스별 CAE-Test 오차 + bar | 오차정의, 허용범위 | base-xy(bar) | error-whisker, tol-band | within-tol% | xy-core | 중간 |
| corr-residual | 잔차 플롯 | 편향/추세 진단 | 예측/x | 잔차 | 잔차 분포, 0선, 추세 | 페어, 단위 | corr-scatter-r2 | zero-line, trend | bias-test | xy-core | 중간 |
| corr-bland-altman | Bland-Altman | 측정-해석 일치도 | 평균 | 차이 | 평균±1.96SD 한계 | 페어 | corr-scatter-r2 | loa-lines | bias, loa | xy-core | 중간 |
| corr-frf-overlay | FRF 상관(MAC) | 모달/주파수응답 상관 | 주파수(Hz) | |H|(dB)/MAC | CAE vs Test FRF + MAC | 모드매칭, 주파수범위 | base-xy | mac-badge, mode-markers | mac-matrix | xy-core | 중간 |
| corr-mac-matrix | MAC 행렬 | 모드형상 상관 | Test 모드# | CAE 모드# / MAC | 모드형상 일치 행렬 히트맵 | 모드셋, 자유도 | heatmap-2d | diag-highlight | mac-diag | **field-2d** | 높음 |

도메인 특유: overlay 하단 residual strip 동기, scatter에 R²/slope/RMSE 배지 + 허용 error band, error-bar within-tolerance 자동 음영, Bland-Altman LoA, MAC 대각 강조.

---

## 8) 신뢰성 (Reliability)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rel-weibull-prob | 와이블 확률지 | 수명분포 추정 | 수명(log) | 누적고장(Weibull 변환) | 와이블 직선화 + β,η | 고장데이터, 검열정보 | prob-paper | weibull-axis, fit-line, ci-band | beta-eta, B10 | **prob-paper**(신규) | 높음 |
| rel-weibull-cdf | 와이블 CDF/PDF | 분포 형상 | 시간/사이클 | F(t) 또는 f(t) | 누적/밀도 분포 곡선 | β, η 또는 데이터 | base-xy | pdf-cdf-toggle | median-life | xy-core | 중간 |
| rel-bathtub-hazard | 욕조 곡선 | 고장률 수명단계 | 시간 | 고장률 h(t) | 초기/우발/마모 3구간 | 구간 정의, 단위 | base-xy | phase-shade | phase-bounds | xy-core | 중간 |
| rel-prob-normal | 정규 확률지 | 정규성 검정 | 데이터값 | 정규 분위수(z) | Q-Q 직선 + 적합 | 데이터, 분포가정 | prob-paper | normal-axis, fit-line | r2, normality | **prob-paper** | 높음 |
| rel-survival-km | 생존곡선(KM) | 생존/신뢰도 | 시간 | 생존확률 S(t) | Kaplan-Meier 계단 + 검열 | 검열, 그룹 | base-xy | step-style, censor-ticks, ci-band | median-surv | xy-core | 중간 |
| rel-accel-life | 가속수명(Arrhenius) | 가속→사용조건 환산 | 1/T 또는 응력 | 수명(log) | 가속모델 직선 + 외삽 | 모델(Arrhenius/Eyring), 응력 | base-xy | log-y, extrap-band | activation-E | xy-core | 중간 |
| rel-pareto-failure | 고장 파레토 | 고장모드 우선순위 | 고장모드 | 빈도 & 누적% | 빈도 막대 + 누적선(80%) | 고장 분류, 기간 | base-xy(bar) | pareto-combo, 80-line | vital-few | xy-core | 중간 |

도메인 특유: 와이블지의 비선형 y축(ln(-ln(1-F))), 적합선 + β/η/B10 배지 + 신뢰구간, 검열점 censor tick, 욕조 3구간 음영, 파레토 80% 컷 라인.

---

## 9) DOE / 민감도 (Design of Experiments)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| doe-pareto-effects | 효과 파레토 | 유의 인자 선별 | 인자/교호작용 | 표준화 효과 | 효과 크기 막대 + 유의선 | 인자 라벨, α(유의수준) | base-xy(bar) | sig-line, sorted-bar | significant[] | xy-core | 중간 |
| doe-main-effects | 주효과도 | 인자 영향 방향 | 인자 수준 | 응답 평균 | 인자별 평균응답 기울기 | 인자/수준, 응답 | base-xy | grand-mean-line, multi-panel | effect-size | xy-core | 중간 |
| doe-interaction | 교호작용도 | 인자 상호작용 | 인자 A 수준 | 응답(인자 B 계열) | 비평행=교호작용 | 두 인자/수준, 응답 | base-xy | parallel-test | interaction-p | xy-core | 중간 |
| doe-response-surface-3d | 반응표면 3D | 최적영역 탐색 | 인자1 | 인자2 / 응답 | 2인자 응답 surface | 인자범위, 모델식 | surface-3d | rsm-shell, optimum-pin | stationary-pt | **surface-3d** | 높음 |
| doe-response-contour | 반응표면 등고 | 최적영역(2D) | 인자1 | 인자2 / 응답 | 응답 등고선 + 최적점 | 인자범위, 모델 | heatmap-2d | contour-lines, optimum, constraint | feasible-region | **field-2d** | 높음 |
| doe-tornado | 토네이도 | 민감도 순위 | 영향(저↔고) | 인자(정렬) | 인자별 응답 변동폭 막대 | 인자 범위, 기준값 | base-xy(bar) | centered-bar, baseline | rank[] | xy-core | 중간 |
| doe-sensitivity-spider | 민감도 스파이더 | 다인자 민감도 | 인자(각) | 정규화 민감도(반경) | 방사형 민감도 | 인자셋, 정규화 | radar-base | normalized-radial | top-driver | **polar** | 높음 |
| doe-montecarlo-hist | 몬테카를로 분포 | 출력 변동 | 응답값(bin) | 빈도/밀도 | 출력 히스토그램 + 분포적합 | 시료수, bin, spec | base-xy(bar) | hist-bins, fit-overlay, spec-line | mean,std,Cpk | xy-core | 중간 |
| doe-montecarlo-cdf | 몬테카를로 누적 | 백분위/신뢰 | 응답값 | 누적확률 | CDF + P5/P95, spec | 시료수, spec | base-xy | percentile-marks, spec-line | P5,P50,P95 | xy-core | 중간 |
| doe-tolerance-hist | 공차분석 분포 | 조립공차/스택업 | 치수(bin) | 빈도 | 공차 스택업 분포 + USL/LSL | 공차한계, 분포 | doe-montecarlo-hist | usl-lsl-lines, cpk-badge | Cp,Cpk,yield | xy-core | 중간 |
| doe-correlation-matrix | 상관행렬 | 인자간 상관 | 변수 | 변수 / r | 상관계수 히트맵 | 변수셋 | heatmap-2d | corr-colormap, r-label | high-corr | **field-2d** | 높음 |
| doe-scatter-matrix | 산점도 행렬 | 다변량 페어플롯 | 변수i | 변수j | 변수쌍 산점 격자(SPLOM) | 변수셋, 샘플 | scatter-grid | diag-hist, panel-grid | pair-r | **field-2d** | 높음 |
| doe-parallel-coords | 평행좌표 | 다차원 설계공간 | 변수(축들) | 정규화 값 | 다축 평행 라인, 브러싱 | 변수셋, 범위 | parallel-base | brush-filter, axis-reorder | filtered-set | **parallel-coords**(신규) | 높음 |

도메인 특유: 효과 파레토 유의선(α), 교호작용 평행성 검정 하이라이트, 토네이도 baseline 중심 정렬, 몬테카를로에 spec/USL-LSL + Cpk 배지, 평행좌표 축 브러싱·재정렬, contour에 feasible region 음영.

---

## 10) 최적화 (Optimization)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| opt-convergence | 수렴 이력 | 최적화 진행 | iteration | 목적함수/제약 | 반복별 목적·제약 수렴 | 목적정의, 제약, 방향 | base-xy | best-so-far, constraint-band | converged-it | xy-core | 낮음 |
| opt-pareto-front-2d | 파레토 프론트 2D | 다목적 트레이드오프 | 목적1 | 목적2 | 비지배 해 프론트 + 지배해 | 목적정의(방향) | scatter-2d | pareto-line, dominated-fade, knee | knee-point | xy-core | 중간 |
| opt-pareto-front-3d | 파레토 프론트 3D | 3목적 트레이드오프 | 목적1 | 목적2 / 목적3 | 3D 비지배 표면 | 3 목적 정의 | surface-3d | pareto-surface | hypervolume | **surface-3d** | 높음 |
| opt-design-space-parallel | 설계공간 평행좌표 | 변수-목적 관계 | 변수/목적(축) | 정규화 값 | 설계변수+목적 평행좌표 | 변수/목적셋, 범위 | parallel-base | pareto-highlight, brush | selected | **parallel-coords** | 높음 |
| opt-doe-sampling | 샘플링 분포 | 설계점 커버리지 | 변수1 | 변수2 | LHS/sampling 산포 | 변수범위, 샘플법 | scatter-2d | bounds-box | coverage | xy-core | 낮음 |
| opt-objective-tradeoff | 트레이드오프 곡선 | 단일 트레이드 | 설계변수 | 목적1 & 목적2 | 변수에 따른 목적 상충(이중축) | 변수, 목적들 | base-xy | dual-y, crossover | crossover-pt | xy-core | 중간 |

도메인 특유: 수렴 best-so-far envelope + 제약 위반 음영, 파레토 knee 자동, dominated 해 흐림, 평행좌표에서 파레토 해 하이라이트 + 브러싱, hypervolume 지표.

---

## 11) Spec 대비 마진 (Margin / Scorecard)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보 | 상속 베이스 | feature plugin | 후처리(post) | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| margin-bullet | 마진 불릿차트 | spec 대비 실측 | 값 | 항목(행) | 측정 막대 + target + 양호/경고 band | spec target, 양호/경고 임계, 방향 | base-xy(bar) | bullet-bands, target-tick | margin%, pass | xy-core | 중간 |
| margin-gauge | 게이지 | 단일 지표 마진 | (반경각) | 값 | 반원 게이지 + spec 존 | min/max, spec zones | gauge-base | zone-arcs, needle | status | **polar** | 높음 |
| margin-radar | 마진 레이더 | 다지표 스코어카드 | 지표(각) | 정규화 마진(반경) | 다항목 spec 대비 레이더 | 지표셋, spec 정규화 | radar-base | spec-ring, fill | weakest | **polar** | 높음 |
| margin-waterfall | 마진 워터폴 | 마진 소모 분해 | 기여항목 | 누적 마진 | budget→소모→잔여 폭포 | 초기마진, 기여항목 | base-xy(bar) | waterfall-connect, residual | remaining | xy-core | 중간 |
| margin-spec-table-heat | 스펙 합부 히트 | 다항목 합부 매트릭스 | 항목 | 케이스 / 마진% | 합부 색코딩 매트릭스 | 항목×케이스, 임계 | heatmap-2d | pass-fail-colormap | fail-count | **field-2d** | 높음 |

도메인 특유: 불릿의 양호/경고/한계 3-band + target tick + 방향성(클수록좋음/작을수록좋음), 게이지 spec zone arc, 레이더 spec ring 안쪽=미달 음영, 워터폴 잔여 마진 강조.

---

## (a) 도메인 공통 인터랙션/오버레이 요약 (base 자동 위에 추가되는 것)

- **임계/스펙 오버레이**: limit-line, spec-band, target-tick, USL/LSL, threshold-contour — 거의 전 도메인 공통. hover 시 "마진 = 값 − spec" 실시간 표기.
- **이중축(dual-y)**: 전력↔온도, SPL↔THD, 임피던스 |Z|↔phase, throughput↔RSSI, 충전 전류↔전압. 동기 hover.
- **로그축 기본값**: SPL/THD/임피던스/MTF(옵션)/BER/와이블/가속수명 — plugin이 기본 scale=log 지정(사용자 토글은 자동 유지).
- **적합/통계 배지**: R², RMSE, slope(상관), β/η/B10(와이블), Cp/Cpk/yield(공차), mean/std/Pxx(몬테카를로), MTF50, HPBW, Fs/Qts — post 단계 계산 후 HUD 배지.
- **영역 음영**: feasible region(DOE contour), pass/warn/fail band(margin), 욕조 3구간, 가시광 밴드(반사율), 검열 구간.
- **그룹/시리즈 isolate**: 주파수 ring(폴라), 파장(수차), 모드(FRF), 시나리오(전력) — 범례 isolate(자동) 위에 도메인 그룹 토글.
- **2-이미지/맵 blend**: IR↔CAE, 측정맵↔해석맵 — blend 슬라이더 + diff 모드(ΔT/ΔE/Δ).
- **브러싱/필터**: 평행좌표·산점행렬에서 한 축 범위 브러시→다른 패널 연동.
- **핀/주석**: hotspot top-N, peak SAR, knee point(파레토), crossover, stationary point(RSM), Fs(임피던스).

---

## (b) 2D xy-core 로 안 되는 항목 — 신규 엔진 패밀리 제안 (망라)

xy-core(다중 XY 라인/마커/스텝)로 **불가능**하여 새 engine family가 필요한 것들. catalog 블록은 동일 모델(`engine` 키만 교체)이지만 엔진 자산(렌더러)이 신규다. 우선순위는 재사용 빈도 순.

| 신규 엔진 패밀리 | 무엇을 렌더 | 이 패밀리로 흡수되는 type-id(예) | 핵심 렌더 능력 | 백엔드 후보 | 우선순위 |
|---|---|---|---|---|---|
| **field-2d** | 스칼라장 히트맵 + 등고선 + 이미지 underlay + diff | thermal-skin-map/contour/image-overlay, display-luminance/deltaE, acoustic-spectrogram, rf-sar-map, camera-spot/wavefront, corr-mac-matrix, doe-response-contour/correlation-matrix/scatter-matrix, margin-spec-table-heat | 2D 그리드 보간, colormap, isoline(marching squares), 이미지 정합/blend | Canvas2D(+WebGL 대형) | **최상**(가장 많은 타입 흡수) |
| **polar** | 극좌표/방사형(폴라·레이더·게이지) | acoustic-directivity-polar, rf-antenna-pattern-polar, display-viewing-angle-polar, doe-sensitivity-spider, margin-gauge/radar | 각도-반경 좌표계, dB radial, ring/sector, HPBW/beamwidth 자동 | Canvas2D | **상** |
| **surface-3d** | 3D 표면/체적/구면 | acoustic-waterfall, display-color-volume-3d, rf-antenna-pattern-3d, doe-response-surface-3d, opt-pareto-front-3d | 3D 메시, 카메라 궤도/줌, 라이팅, z-colormap, 단면 | WebGL/Three | **상** |
| **prob-paper** | 비선형 확률지(축 변환) | rel-weibull-prob, rel-prob-normal (+lognormal/exponential) | 분포별 비선형 y축(ln(-ln), Φ⁻¹), median rank, 적합선+CI | Canvas2D | 중 |
| **parallel-coords** | 다축 평행좌표(+브러싱) | doe-parallel-coords, opt-design-space-parallel | N개 정규화 수직축, polyline, 축 재정렬/브러시 필터 | Canvas2D/SVG | 중 |
| **smith** | 스미스 차트 | rf-smith-chart | 등저항/등리액턴스 원 좌표계, 임피던스 궤적, 주파수 마커 | Canvas2D | 중 |
| **eye-diagram** | 아이 다이어그램 | rf-eye-diagram | UI-folding, 다중 trace 밀도(persistence) 누적, mask 합부 | Canvas2D/WebGL | 중 |
| **vector-field** | 벡터장/격자 변형 | camera-distortion-grid (+유동/변위 quiver) | quiver/streamline, 격자 deform, reference overlay | Canvas2D | 중하 |
| **chromaticity** | 색도 다이어그램 | display-cie1931-gamut (+CIE 1976 u'v') | 말굽(spectral locus), 색역 삼각형, 색채움, coverage% | Canvas2D | 중하 |

추가로 xy-core 위 **plugin 합성만으로** 해결되는(신규 엔진 불필요) 대표군: 모든 시계열·스펙트럼·곡선(thermal-rise, spl/thd, return-loss/vswr/efficiency, mtf, aberration-ray, 전력/배터리/충전, BER, weibull-cdf, bathtub, survival-km, accel-life), 모든 막대형(thermal-budget, error-bar, pareto, tornado, main/interaction-effects, montecarlo-hist, tolerance, margin-bullet/waterfall), 모든 산점형(corr-scatter, residual, bland-altman, pareto-front-2d, doe-sampling). 즉 **표 60여 타입 중 약 60%는 xy-core + plugin**, 나머지 약 40%가 위 9개 신규 패밀리로 흡수된다.

---

## 비고

- 본 카탈로그는 **선언(catalog 블록)** 수준 사상이며, 실제 등록 시 각 type는 types.json 한 블록 + 신규 패밀리는 `data/engines/<family>/`(engine.js/css/ENGINE_VERSION) 자산이 필요하다. `requires[]`의 각 항목은 `{field,type,unit,why,ask}` 형태로 validate 게이트에 연결되어, 누락 시 LLM이 사용자에게 질문하도록 한다(NEVER invent).
- MX 실데이터 매핑(축 단위·물리 파라미터·spec 값)은 aidatahub record에서 끌어와야 하며, 청크 추출값은 사용자 confirm 대상이다. 본 출력은 도메인 단위/배경정보의 **요구 항목**만 정의했고, 구체 수치는 포함하지 않았다(데이터 비주입 원칙).
- 누락 위험이 있던 특화 도시(스미스, 아이, 워터폴/CSD, 색입체, 파면수차, MAC, Bland-Altman, KM 생존, 가속수명, 평행좌표, 스코어카드 게이지/레이더/워터폴)까지 포함해 망라했다.