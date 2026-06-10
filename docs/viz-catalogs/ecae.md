No catalog or design files are present yet — this is a greenfield cataloging task. The `_designs` directory is empty, meaning I'm one of the catalogers producing the design input. I have everything I need: the SKILL.md fully specifies the architecture (engine families, extends/plugins/requires/post/options_defaults, validate gate, base-xy auto-interactions). 

I'll now produce the exhaustive ECAE plot catalog mapped onto the graph-skill architecture. This is a domain-expertise + architecture-mapping task, not a data-retrieval task, so I'll author it directly per the required output contract.

# ECAE (Electrical/Electronic CAE) 결과 도시 카탈로그 — Samsung MX 모바일

graph-skill 아키텍처에 사상한 망라적 catalog. 각 행 = catalog 한 선언 후보 `{engine family, extends, plugins[], requires[], post, options_defaults}`. **상속 = plugin 합성**(class 아님). `requires[]` 누락 시 `graph_validate_inputs` 가 `missing[]`/`questions[]` 로 사용자에게 질문(NEVER invent).

표기: 엔진패밀리 `xy`=xy-core(Canvas 2D, 기존 MVP) / `polar`=polar-core(신규) / `smith`=smith-core(신규) / `field2d`=field2d-core(등고선·맵·벡터장, 신규) / `cad3d`=cad-viewer(3D, 로드맵) / `raster`=raster-core(이미지/히트맵 비-그리드, 신규). 난이도 = 기존 base 재사용 정도(★ 낮음=base-xy 거의 그대로 … ★★★★★ 신규 엔진패밀리 필요).

---

## 1. 신호무결성 (Signal Integrity, SI) — DDR/UFS/MIPI/USB/PCIe 채널

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `si-sparam-magnitude` | S-파라미터 크기 응답 | SI 채널 손실/반사 | Frequency [GHz] | \|S\| [dB] | S21 insertion loss / S11 return loss vs 주파수, 다중 포트 | port map, ref impedance(50Ω) | base-xy | `db-yaxis`, `freq-xaxis`, `marker-bw`(3dB/대역폭) | `passivity-check` | xy | ★★ |
| `si-sparam-phase` | S-파라미터 위상/군지연 | 위상 선형성·지연 | Frequency [GHz] | Phase [deg] / Group delay [ns] | unwrap 위상, group delay | unwrap 기준, ref Z | base-xy | `phase-unwrap`, `freq-xaxis` | `groupdelay-derive` | xy | ★★ |
| `si-insertion-loss-budget` | 삽입손실 버짓 | 채널 손실 마진 | Frequency [GHz] | Loss [dB] | IL vs spec mask(한계선) 오버레이 | spec mask 포인트, Nyquist freq | base-xy | `limit-mask`, `freq-xaxis` | `margin-calc` | xy | ★★ |
| `si-tdr-impedance` | TDR 임피던스 프로파일 | 임피던스 불연속 위치 | Time [ns] / Distance [mm] | Impedance Z [Ω] | 경로상 Z 변동(커넥터/비아/스텁) | rise time, Dk(전파속도), Z0 target | base-xy | `dual-x`(time↔distance), `ztarget-band` | `tdr-from-s11`(S11→TDR) | xy | ★★★ |
| `si-tdt-step` | TDT 스텝 응답 | 전송 스텝 | Time [ns] | Normalized V | 채널 스텝 투과 | rise time | base-xy | `step-style` | — | xy | ★ |
| `si-eye-diagram` | 아이 다이어그램 | 데이터 아이 개폐 | UI(unit interval) 0–1 | Voltage [V] | 비트 중첩 eye, eye height/width/jitter, mask hit | UI(ps), 비트열/PRBS, sample rate, mask | (신규) eye-base | `eye-fold`, `eye-mask`, `density-heat`, `eye-metrics` | `eye-measure`(H/W/jitter) | raster | ★★★★★ |
| `si-eye-contour` | 아이 BER 컨투어 | 통계적 아이 (등BER선) | Time [UI] | Voltage [V] | BER 등고선(10⁻⁶…10⁻¹²) 중첩 | BER levels, 통계 아이 데이터 | (신규) field2d-base | `contour-log`, `eye-mask` | — | field2d | ★★★★★ |
| `si-ber-bathtub` | BER 욕조곡선 | 타이밍/전압 마진 | Time offset [UI] / V offset | BER (log) | 좌우 욕조→눈 개구 마진 @ target BER | target BER, UI | base-xy | `log-yaxis`(forced), `bathtub-fit`, `margin-marker` | `eye-opening@BER` | xy | ★★ |
| `si-jitter-decomp` | 지터 분해(RJ/DJ) | 지터 성분 분리 | Time [ps] | Probability / Count | TJ=RJ+DJ, 히스토그램+이중 가우시안 | RJ/DJ 분해 파라미터 | base-xy | `histogram`, `dualdirac-fit` | `tj@BER` | xy | ★★★ |
| `si-crosstalk-nextfext` | 크로스토크 NEXT/FEXT | 인접선 결합 | Frequency [GHz] / Time [ns] | Coupled \|S\| [dB] / V | 근단/원단 누화 | aggressor/victim map, coupling | base-xy | `freq-xaxis`, `db-yaxis`, `aggressor-group` | — | xy | ★★ |
| `si-pulse-response` | 펄스 응답(SBR) | ISI/탭 가중 | Time [UI] | Voltage [V] | single-bit response, cursor/precursor/postcursor 탭 | UI, sample/UI | base-xy | `cursor-stem`, `tap-markers` | `isi-sum` | xy | ★★ |
| `si-channel-impulse` | 채널 임펄스 응답 | 채널 특성 시간영역 | Time [ns] | h(t) | impulse h(t), 반사 꼬리 | sample rate | base-xy | `impulse-stem` | — | xy | ★ |
| `si-step-response` | 채널 스텝 응답 | 셋틀링/오버슈트 | Time [ns] | V | 스텝 settling | rise time | base-xy | `step-style` | `settle-metrics` | xy | ★ |
| `si-equalization-fom` | 이퀄라이저 성능(CTLE/DFE/FFE) | EQ 전후 비교 | Frequency/UI | dB / V | EQ on/off 채널, eye 개선 | EQ 설정(탭/peaking) | base-xy | `before-after`, `db-yaxis` | — | xy | ★★ |
| `si-mode-conversion` | 모드 변환(Scd/Sdc) | 차동↔공통 변환 | Frequency [GHz] | \|Scd21\| [dB] | 차동쌍 비대칭→EMI 위험 | mixed-mode 정의 | base-xy | `freq-xaxis`, `db-yaxis` | `mixedmode-convert` | xy | ★★★ |
| `si-skew-budget` | 스큐 버짓 | 차동/버스 정렬 | Lane | Skew [ps] | 레인별 within-pair/lane-to-lane skew bar | lane map, spec skew | base-xy | `bar-categorical`, `limit-line` | — | xy | ★ |

## 2. 전력무결성 (Power Integrity, PI) — PDN/PMIC

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `pi-pdn-impedance` | PDN 임피던스 프로파일 | target-Z 만족 | Frequency [Hz/MHz] | \|Z\| [Ω] | PDN Z(f) vs target-Z 선, anti-resonance peak | target-Z, Vdd, ripple%, Imax | base-xy | `loglog`(forced), `targetz-line`, `peak-annot` | `antiresonance-find` | xy | ★★ |
| `pi-decap-effect` | 디캡 효과 비교 | decap 최적화 | Frequency [Hz] | \|Z\| [Ω] | decap 추가 전/후 Z(f) 다중 시나리오 | decap BOM/시나리오 | base-xy(extends pi-pdn-impedance) | `before-after`, `loglog` | — | xy | ★★ |
| `pi-ir-drop-map` | IR drop 분포 맵 | 전원면 전압강하 | X [mm] | Y [mm] / ΔV [mV] (color) | 플레인 IR-drop 2D 히트맵, 핫스팟 | mesh 좌표, Vnom, ΔV limit | (신규) field2d-base | `heatmap`, `colorbar`, `limit-iso`, `hotspot-pin` | `vmin-locate` | field2d | ★★★★★ |
| `pi-current-density-map` | 전류밀도 맵 | EM/발열 위험 | X [mm] | Y [mm] / J [A/mm²] (color) | via/trace 전류밀도, EM 한계 | geometry, J limit | (신규) field2d-base | `heatmap`, `vectorfield`(전류 흐름), `colorbar` | `jmax-locate` | field2d | ★★★★★ |
| `pi-voltage-droop-transient` | 전압 droop 과도 | load-step 응답 | Time [ns/µs] | Vdd [V] | di/dt 부하 스텝→droop/overshoot, 1st/2nd droop | load profile, Vdd, ripple spec | base-xy | `droop-markers`, `spec-band` | `droop-metrics` | xy | ★★ |
| `pi-ripple-spectrum` | 리플 스펙트럼 | 스위칭 노이즈 | Frequency [MHz] | Ripple [mV/dBµV] | PMIC 스위칭 하모닉 | switching freq | base-xy | `freq-xaxis`, `harmonic-marker` | `fft` | xy | ★★ |
| `pi-resonance-modal` | 플레인 공진 모드 | 캐비티 공진 | Frequency [MHz] | Mode amplitude / mode shape | 전원/접지 플레인 공진 주파수·모드형상 | board dim, Dk | base-xy(/field2d 모드형상) | `modal-markers` | — | xy/field2d | ★★★ |

## 3. RF / 안테나 (Antenna & RF Front-End) — sub-6/mmWave/UWB

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `rf-s11-return-loss` | 입력 반사손실 S11 | 정합 대역 | Frequency [GHz] | \|S11\| [dB] | 안테나 매칭, -6/-10dB 대역 | ref Z, band 정의 | base-xy | `freq-xaxis`, `db-yaxis`, `band-marker` | `bw@-6dB` | xy | ★★ |
| `rf-vswr` | VSWR 곡선 | 정재파비 | Frequency [GHz] | VSWR (≥1) | VSWR vs 2:1/3:1 한계 | ref Z | base-xy(from S11) | `vswr-line`, `limit-line` | `vswr-from-s11` | xy | ★★ |
| `rf-smith-chart` | 스미스 차트 | 임피던스 정합 | Re(Γ) | Im(Γ) (정규화 임피던스 그리드) | S11 궤적, 매칭 경로, 등Q·등VSWR원 | ref Z(50Ω), freq sweep | (신규) smith-base | `smith-grid`, `freq-sweep-trace`, `q-circle`, `match-network` | `z2gamma` | smith | ★★★★★ |
| `rf-radiation-pattern-polar` | 방사 패턴(2D polar) | 빔 형상 | Angle θ/φ [deg] | Gain [dBi] (반경) | E/H-plane 컷, HPBW, SLL, F/B비 | freq, cut plane, 단위 | (신규) polar-base | `polar-grid`, `hpbw-marker`, `sll-annot`, `multicut` | `hpbw-fbr` | polar | ★★★★★ |
| `rf-radiation-pattern-3d` | 방사 패턴(3D) | 전방향 빔 | θ,φ 구면 | Gain [dBi] (반경/색) | 3D 방사구, 빔 방향/널 | 구면 샘플 데이터, freq | (신규) cad3d-base | `sphere-mesh`, `gain-colormap`, `cut-overlay` | — | cad3d | ★★★★★ |
| `rf-gain-efficiency-freq` | 이득/효율 vs 주파수 | 대역 성능 | Frequency [GHz] | Gain [dBi] / Efficiency [%] | peak/realized gain, total/radiation eff(이중축) | freq, eff 정의 | base-xy | `dual-yaxis`, `freq-xaxis`, `band-shade` | — | xy | ★★ |
| `rf-beam-scan` | 빔스캔/스캔손실 | 위상배열 빔포밍 | Scan angle [deg] | Gain [dBi] / Scan loss [dB] | 배열 스캔각별 이득·스캔손실·그레이팅 로브 | array geometry, element pattern | base-xy(+polar) | `scan-overlay` | — | xy/polar | ★★★ |
| `rf-eirp-ccdf` | EIRP CCDF | 규제 EIRP 분포 | EIRP [dBm] | CCDF (prob, log) | mmWave EIRP 통계 분포 | codebook, 측정/시뮬 set | base-xy | `ccdf`, `log-yaxis` | `ccdf-compute` | xy | ★★ |
| `rf-sar-map` | SAR 분포 맵 | 인체 흡수율 규제 | X [mm] | Y [mm] / SAR [W/kg] (color) | 1g/10g 평균 SAR 핫스팟, 한계 | tissue model, mass avg, limit, freq | (신규) field2d-base | `heatmap`, `colorbar`, `limit-iso`, `peak-pin` | `psar-1g10g` | field2d | ★★★★★ |
| `rf-equivalent-circuit` | 등가회로 응답 | 정합 회로 모델 | Frequency [GHz] | \|Z\|/Q / S | RLC 등가모델 vs full-wave 상관 | 회로 토폴로지/소자값 | base-xy | `model-vs-em`, `freq-xaxis` | — | xy | ★★ |
| `rf-isolation-coupling` | 안테나 간 격리(S21) | MIMO/공존 | Frequency [GHz] | \|S21\| [dB] | 안테나쌍 격리, ECC 입력 | port map | base-xy | `freq-xaxis`, `db-yaxis` | `ecc-derive` | xy | ★★ |
| `rf-envelope-correlation` | ECC/다양성 | MIMO 성능 | Frequency [GHz] | ECC (0–1) | 포락선 상관계수 vs 한계(0.5) | 패턴/S-param set | base-xy | `limit-line` | — | xy | ★★ |
| `rf-group-delay-flatness` | 군지연 평탄도 | 필터/대역 왜곡 | Frequency [GHz] | Group delay [ns] | 통과대역 GD ripple | 필터 정의 | base-xy(from phase) | `freq-xaxis`, `ripple-band` | `gd-from-phase` | xy | ★★ |
| `rf-noise-figure` | 잡음지수 NF | 수신 감도 | Frequency [GHz] | NF [dB] | LNA/체인 NF | 체인 정의 | base-xy | `freq-xaxis` | — | xy | ★ |
| `rf-loadpull-contour` | 로드풀 컨투어 | PA 정합 최적점 | Re(Γ) | Im(Γ) / Pout·PAE 등고선 | PA 최적 부하 임피던스 영역 | PA 측정/시뮬, contour levels | (신규) smith+field2d | `smith-grid`, `contour-overlay` | — | smith/field2d | ★★★★★ |
| `rf-current-distribution` | 표면 전류 분포 | 방사 메커니즘 | geometry X/Y(/Z) | \|J_surf\| (color) | 안테나 표면 전류, 공진 모드 | mesh, freq | (신규) field2d/cad3d | `surface-current`, `colormap` | — | field2d/cad3d | ★★★★★ |

## 4. EMI / EMC — 방사/전도 노이즈·차폐

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `emi-emission-spectrum` | 방사/전도 방출 스펙트럼 | 규제 적합성 | Frequency [MHz/GHz] | Level [dBµV/m, dBµV] | 방출 vs CISPR/FCC 한계선(QP/Avg), 마진 | limit standard, detector, distance | base-xy | `limit-mask`(다중), `peak-hold`, `margin-color`, `log-xaxis` | `margin-worst` | xy | ★★★ |
| `emi-near-field-map` | 근접장 맵 | 노이즈 소스 위치 | X [mm] | Y [mm] / \|E\|or\|H\| (color) | 보드 위 근접장 핫스팟, 소스 식별 | scan plane, freq, 단위 | (신규) field2d-base | `heatmap`, `colorbar`, `overlay-board`, `vectorfield` | `hotspot-rank` | field2d | ★★★★★ |
| `emi-shielding-effectiveness` | 차폐 효과 SE | 쉴드캔/개스킷 | Frequency [MHz/GHz] | SE [dB] | SE vs 주파수, 슬롯/개구 영향 | aperture geometry | base-xy | `freq-xaxis`, `db-yaxis` | — | xy | ★★ |
| `emi-conducted-emission` | 전도 방출 | 전원/케이블 노이즈 | Frequency [kHz–MHz] | dBµV | CM/DM 분리, 한계선 | LISN, 한계 | base-xy | `limit-mask`, `cm-dm-split`, `log-xaxis` | `fft` | xy | ★★ |
| `emi-tvs-esd-clamp` | ESD 클램프 응답 | ESD/서지 보호 | Time [ns] | V / I | TLP I-V, 클램프 전압, 8kV 파형 | TLP/IEC pulse, device | base-xy | `pulse-style`, `clamp-marker` | `it2-find` | xy | ★★ |
| `emi-radiated-immunity` | 방사 내성 맵 | 결합 경로 | Frequency [MHz] | Coupled V/field | 외부 필드→내부 결합 응답 | field strength | base-xy | `limit-line` | — | xy | ★★ |
| `emi-cable-coupling` | 케이블 결합/FFT | 하네스 EMI | Time/Freq | V / dBµV | 케이블 결합 시간·주파수 | harness model | base-xy | `time-freq-toggle` | `fft` | xy | ★★ |

## 5. 배터리 (Cell/Pack 전기화학) — 충방전·수명·임피던스·안전

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bat-voltage-capacity` | 충방전 전압-용량 | 셀 거동 | Capacity [mAh] / SOC [%] | Voltage [V] | C-rate별 충/방전 곡선, 플래토 | C-rate, nominal cap, V-window | base-xy | `crate-series`, `hyst-fill`(충방전 히스테리시스) | — | xy | ★★ |
| `bat-voltage-time` | 전압-시간 프로파일 | 프로토콜 | Time [h] | Voltage/Current [V/A] | CC-CV 단계, 전압·전류 이중축 | protocol, cap | base-xy | `dual-yaxis`, `stage-shade` | — | xy | ★ |
| `bat-capacity-fade` | 용량 fade vs cycle | 수명/SOH | Cycle number | Capacity retention [%] | 사이클 열화, EOL 80% 선 | EOL%, C-rate, temp | base-xy | `eol-line`, `fit-curve` | `cyclelife@80%` | xy | ★★ |
| `bat-dqdv` | dQ/dV (미분용량) | 상전이/열화 진단 | Voltage [V] | dQ/dV [mAh/V] | 상전이 피크, 피크 시프트=열화 | smoothing window | base-xy | `derivative`, `peak-track` | `dqdv-derive` | xy | ★★★ |
| `bat-dvdq` | dV/dQ | 활물질 손실 진단 | Capacity [mAh] | dV/dQ [V/mAh] | 음/양극 밸런싱, LLI/LAM | smoothing | base-xy | `derivative` | `dvdq-derive` | xy | ★★ |
| `bat-eis-nyquist` | EIS Nyquist | 임피던스 모델 | Re(Z) [Ω] | -Im(Z) [Ω] | 반원(전하이동)+Warburg 꼬리, equal-aspect | freq range, SOC/temp, equal aspect | base-xy | `equal-aspect`(forced), `freq-color`, `arc-fit`(ECM) | `ecm-fit` | xy | ★★★ |
| `bat-eis-bode` | EIS Bode | 임피던스 vs 주파수 | Frequency [Hz] | \|Z\| [Ω] / Phase [deg] | 임피던스 크기·위상 이중축, log | freq range | base-xy | `loglog`, `dual-yaxis` | — | xy | ★★ |
| `bat-rate-capability` | 율특성(Ragone) | 에너지-파워 | Power/C-rate (log) | Energy/Capacity [%] (log) | Ragone, 고율 용량 유지 | C-rate set | base-xy | `loglog`, `crate-marker` | — | xy | ★★ |
| `bat-ocv-soc` | OCV-SOC | 잔량 추정 모델 | SOC [%] | OCV [V] | 정적 OCV 곡선, 온도 의존 | temp, rest time | base-xy | `temp-series` | — | xy | ★ |
| `bat-thermal-runaway` | 열폭주 거동 | 안전(ARC/nail) | Time [s] / Temp [°C] | Temp [°C] / dT/dt [°C/min] | 자가발열 onset, 폭주 가속(이중축 log) | onset criteria, test type | base-xy | `dual-yaxis`, `onset-marker`, `log-rate` | `onset-detect` | xy | ★★★ |
| `bat-swelling` | 스웰링/두께 vs cycle | 가스/팽창(전기-기계) | Cycle / SOC | Thickness [µm] / ΔV | 셀 두께 증가(ECAE↔MCAE 경계) | baseline thickness | base-xy | `fit-curve` | — | xy | ★★ |
| `bat-soc-temp-map` | SOC-온도 안전영역 맵 | 운용 안전영역 | SOC [%] | Temp [°C] / risk (color) | 안전/위험 영역 2D 맵 | safe-window 정의 | (신규) field2d-base | `heatmap`, `safe-region` | — | field2d | ★★★★ |

## 6. 전자 열해석 (Electro-Thermal / Thermal of electronics) — AP/PMIC/PA junction

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `et-junction-temp-transient` | 정션온도 과도 | 스로틀링 위험 | Time [s] | Tj [°C] | 부하 시나리오별 Tj 상승, Tjmax 한계 | power profile, Tjmax, Rth | base-xy | `limit-line`, `scenario-series` | `tjmax-margin` | xy | ★★ |
| `et-chip-temp-contour` | 칩 온도 컨투어 | 핫스팟 분포 | X [mm] | Y [mm] / T [°C] (color) | die/PCB 표면 온도 등고선, 핫스팟 | mesh, ambient, power map | (신규) field2d-base | `contour-fill`, `colorbar`, `iso-lines`, `hotspot-pin` | `tmax-locate` | field2d | ★★★★★ |
| `et-thermal-resistance-network` | 열저항 네트워크 | RC 열모델 | (node/path) | Rth [°C/W] / Cth | Foster/Cauer RC 사다리, θJC/θJA 경로 | network 토폴로지 | (신규) graph-node 또는 base-xy(bar) | `network-diagram` 또는 `bar-path` | — | field2d/xy | ★★★ |
| `et-zth-transient` | 과도 열임피던스 Zth | 열모델 추출 | Time [s] (log) | Zth [°C/W] (log) | structure function 입력, Foster fit | pulse, power step | base-xy | `loglog`, `foster-fit` | `structure-func` | xy | ★★★ |
| `et-structure-function` | 구조 함수 | 열경로 진단(델람) | Cumulative Rth [°C/W] | Cumulative Cth [Ws/°C] (log) | 누적 구조함수→계면/델라미네이션 | Zth 데이터 | base-xy | `loglog`, `cumulative` | `struct-derive` | xy | ★★★★ |
| `et-power-map` | 전력밀도 맵 | 발열원 입력 | X [mm] | Y [mm] / P [W/mm²] (color) | 칩 전력밀도 분포(열입력) | floorplan, power | (신규) field2d-base | `heatmap`, `colorbar` | — | field2d | ★★★★★ |
| `et-thermal-coupling-matrix` | 열 결합 매트릭스 | 멀티칩 상호가열 | Source chip | Victim chip / ΔT (color) | 칩간 열결합 계수 행렬 | chip list | (신규) field2d-base | `matrix-heatmap`, `colorbar` | — | field2d | ★★★★ |
| `et-throttle-frequency` | 스로틀 주파수-온도 | 성능 거버닝 | Time [s] | Freq [GHz] / Tj [°C] | DVFS 주파수 vs Tj 이중축 | DVFS table | base-xy | `dual-yaxis`, `step-style` | — | xy | ★★ |
| `et-airflow-vector` | 유동/열유속 벡터장 | 방열 경로 | X [mm] | Y [mm] / vector (heat flux) | 열유속/유동 화살표장 | velocity field | (신규) field2d-base | `vectorfield`, `streamline` | — | field2d | ★★★★★ |

## 7. 디스플레이 구동 (Display Driver Electronics) — OLED/LTPO

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `disp-gamma-curve` | 감마(전압-휘도) | 계조 보정 | Gray level / V_data [V] | Luminance [cd/m²] | V-L 감마(보통 2.2), R/G/B 채널 | gamma target, panel | base-xy | `gamma-fit`, `rgb-series`, `log-yaxis` | `gamma-extract` | xy | ★★ |
| `disp-vt-curve` | TFT V-I (Id-Vg) | 구동 TFT 특성 | Vgs [V] | Id [A] (log) | 트랜스퍼 곡선, Vth/이동도/SS | W/L, Vds | base-xy | `log-yaxis`, `vth-marker` | `vth-ss-extract` | xy | ★★ |
| `disp-pixel-transient` | 픽셀 구동 과도 | 응답속도/스미어 | Time [µs] | V_node / Luminance | 픽셀 충전·발광 settling | frame rate, pixel ckt | base-xy | `settle-marker` | — | xy | ★★ |
| `disp-luminance-uniformity` | 휘도 균일도 맵 | mura/IR-drop | X [px/mm] | Y / Luminance (color) | 패널 휘도 분포, mura/전압강하 | panel grid | (신규) field2d-base | `heatmap`, `colorbar` | — | field2d | ★★★★ |
| `disp-flicker-fft` | 플리커 스펙트럼 | DC/저주파 플리커 | Frequency [Hz] | Amplitude [dB] | 플리커 성분, JEITA 가중 | refresh, weighting | base-xy | `freq-xaxis`, `weighting-overlay` | `fft` | xy | ★★ |
| `disp-power-vs-apl` | 소비전력 vs APL | 발광 전력 | APL [%] | Power [mW] | 평균화상레벨별 전력 | panel, brightness | base-xy | `fit-curve` | — | xy | ★ |
| `disp-color-gamut` | 색역(CIE) | 색재현 | CIE x | CIE y | 색삼각형 vs sRGB/DCI-P3 영역 | color space ref | base-xy(scatter+poly) | `gamut-poly`, `ref-overlay`, `equal-aspect` | `coverage%` | xy | ★★ |

## 8. 터치 / 센서 (Touch & Sensors) — 정전용량/햅틱/MEMS

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `touch-cap-heatmap` | 정전용량 맵 | 터치/그립 감지 | Node X | Node Y / ΔC [fF] (color) | 채널별 정전용량 변화, 터치 위치 | sensor grid, baseline | (신규) field2d-base | `heatmap`, `colorbar`, `touch-blob` | `centroid` | field2d | ★★★★ |
| `touch-snr-vs-freq` | 터치 SNR vs 주파수 | 노이즈 면역 | Frequency [kHz] | SNR [dB] | 구동주파수별 SNR, 디스플레이 노이즈 회피 | drive set | base-xy | `freq-xaxis`, `noise-overlay` | — | xy | ★★ |
| `touch-mutual-cap-freq` | 상호용량 vs 주파수 | 센서 응답 | Frequency [kHz] | C [pF] / Z [Ω] | 센서 임피던스 응답 | sensor model | base-xy | `freq-xaxis` | — | xy | ★ |
| `sensor-haptic-response` | 햅틱 진동 응답(LRA) | 진동 튜닝(전기-기계) | Time [ms] / Freq [Hz] | Accel [g] / V | LRA 가속도 임펄스·공진(전기↔MCAE) | resonance f, drive | base-xy | `freq-time-toggle`, `resonance-marker` | `fft` | xy | ★★ |
| `sensor-mems-bode` | MEMS 센서 보드선도 | 자이로/가속 특성 | Frequency [Hz] | Gain [dB] / Phase [deg] | MEMS 공진·대역폭(이중축) | sensor params | base-xy | `loglog`, `dual-yaxis` | — | xy | ★★ |
| `sensor-piezo-charge` | 압전 전하/전압 응답 | 압력/포스터치 | Force [N] / Time | Charge [pC] / V | 압전 소자 전하 응답 선형성 | piezo const | base-xy | `linearity-fit` | — | xy | ★ |
| `sensor-hall-field` | 홀센서 자계 응답 | 폴더블 힌지/펜 | Position [mm] / B [mT] | V_hall [mV] | 자계-출력, 히스테리시스 | magnet model | base-xy | `hyst-loop` | — | xy | ★★ |

## 9. 회로/소자/일반 ECAE (Circuit & Device level)

| type-id | 한글명 | 도메인/용도 | x축 | y축(/z) | 무엇을 보여주나 | 필수 배경정보(requires) | 상속 베이스 | feature plugin | post | 엔진패밀리 | 난이도 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ckt-bode-plot` | 보드 선도 | 필터/루프 안정도 | Frequency [Hz] (log) | Gain [dB] / Phase [deg] | 크기·위상, gain/phase margin | 회로 정의 | base-xy | `loglog`, `dual-yaxis`, `margin-marker` | `pm-gm` | xy | ★★ |
| `ckt-nyquist-stability` | 나이퀴스트(안정도) | 제어/PMIC 루프 | Re(L) | Im(L) | 개루프 궤적, -1점 둘러쌈 | loop gain | base-xy | `equal-aspect`, `unit-circle`, `crit-point` | — | xy | ★★★ |
| `ckt-pole-zero` | 폴-제로 맵 | 전달함수 진단 | Re(s) [rad/s] | Im(s) | s-평면 극·영점, 안정 영역 | TF | base-xy(scatter) | `splane-grid`, `pz-markers` | — | xy | ★★ |
| `ckt-transient-waveform` | 과도 파형 | SPICE 결과 | Time [s] | V / I | 노드 전압·전류 다중 시리즈 | node map | base-xy | `dual-yaxis`, `cursor-measure` | — | xy | ★ |
| `ckt-dc-sweep-iv` | DC IV 스윕 | 소자 특성 | V [V] | I [A] (log opt) | I-V 곡선, 동작점 | device | base-xy | `log-yaxis-opt`, `opp-marker` | — | xy | ★ |
| `ckt-monte-carlo-hist` | 몬테카를로 분포 | 공정변동/수율 | Parameter / spec | Count / density | 변동 히스토그램+spec, Cpk | spec limits, N | base-xy | `histogram`, `spec-lines`, `gauss-fit` | `cpk` | xy | ★★ |
| `ckt-corner-spread` | 코너/PVT 스프레드 | 코너 비교 | Frequency/Time | 출력 | SS/TT/FF 코너 밴드(min-max fill) | corner set | base-xy | `band-fill`, `corner-series` | — | xy | ★★ |
| `ckt-efficiency-vs-load` | 효율 vs 부하(DC-DC) | 컨버터 성능 | Load current [A] (log) | Efficiency [%] | 부하별 효율 곡선, peak | converter | base-xy | `log-xaxis`, `peak-marker` | — | xy | ★ |
| `ckt-em-reliability` | EM 수명 분포 | 일렉트로마이그레이션 | Time-to-fail [h] (log) | CDF (Weibull prob) | Black 식, MTTF, 와이블 plot | J, temp, n | base-xy | `weibull-axes`, `mttf-marker` | `weibull-fit` | xy | ★★★ |
| `wire-rlc-vs-freq` | 배선 RLC vs 주파수 | 패키지/PDN 추출 | Frequency [Hz] | R/L/C | 추출 RLGC 주파수 의존 | extraction | base-xy | `loglog`, `multi-param` | — | xy | ★★ |

---

## (a) 도메인 특유의 인터랙션 / 오버레이 (base-xy 자동 인터랙션 위에 +α)

base-xy 가 자동 제공(멀티시리즈·호버·크로스헤어·툴팁·HUD·줌/팬/박스줌·로그토글·범례 isolate·다크모드·PNG/CSV) 하므로 **plugin 은 도메인 의미 오버레이만** 추가한다:

- **한계선/마스크 (limit-mask, spec-lines)** — EMI 한계선(CISPR/FCC QP·Avg), PDN target-Z, IL budget mask, Tjmax, VSWR 2:1, BER target, EOL 80%, Cpk spec. 마스크 위반 구간 자동 적색 음영 + 마진 HUD. **EMI/PI/열/배터리 전반 공용.**
- **마커/측정 오버레이** — `bw@-NdB`(대역폭), `hpbw/SLL/F-B`(패턴), `pm-gm`(안정도 여유), `eye H/W/jitter`, `vth/SS`(TFT), `droop metrics`, `tjmax-margin`, `cyclelife@80%`. 호버 시 측정값 라이브 표기.
- **주파수축 전용** — `freq-xaxis`(SI/RF/EMI/EIS): 자동 GHz/MHz/kHz 스케일, 로그 기본, 밴드 음영(n78/n257 등), 하모닉 마커.
- **dB/위상 이중축** — `db-yaxis`+`phase-unwrap`+`dual-yaxis`: S-param·Bode·EIS·MEMS 공통 magnitude/phase 동시 표시.
- **before/after 토글** — decap on/off, EQ on/off, 모델 vs full-wave(EM), 코너 비교. 시리즈 그룹 토글.
- **이중 X축 매핑** — TDR의 time↔distance(Dk 기반 전파속도 변환), 햅틱/센서 time↔freq 토글.
- **파생 후처리(post)** — `fft`, `derivative`(dQ/dV), `weibull-fit`, `tdr-from-s11`, `vswr-from-s11`, `gd-from-phase`, `structure-func`. raw → 도메인 곡선 변환을 post 단계에서 수행(LLM이 손계산 안 함).
- **fit/포락선** — `arc-fit`(EIS ECM 반원), `dualdirac-fit`(지터), `gauss-fit`(MC), `foster-fit`(Zth), `bathtub-fit`. 피팅 파라미터를 HUD 표기.
- **equal-aspect 강제** — Nyquist(EIS/제어), Smith, pole-zero, color gamut: 1:1 종횡비 필수(원이 원으로). base-xy에 `equal-aspect` 옵션 필요.

## (b) 새 엔진패밀리가 필요한 항목 (2D xy-core로 표현 불가)

xy-core(직교 라인/스캐터)로 **표현 불가능**하여 신규 engine family 가 필요한 것들 — 패밀리별로 묶음:

1. **`polar-core` (극좌표)** — 반경=값, 각도=θ/φ. 필수 대상: `rf-radiation-pattern-polar`(방사 패턴 E/H-plane), `rf-beam-scan`(극좌표 모드). 신규: 극좌표 그리드/등이득원/HPBW 각도 마커/멀티컷 오버레이. **우선순위 높음**(안테나 핵심 산출물).

2. **`smith-core` (스미스 차트)** — 정규화 임피던스 곡선좌표. 필수: `rf-smith-chart`(S11 정합 궤적), `rf-loadpull-contour`. 신규: 등R/등X 원형 그리드, Γ↔Z 변환(post `z2gamma`), 주파수 스윕 궤적 색, 등Q/등VSWR원, 매칭 네트워크 경로. **RF 필수, 직교로 절대 대체 불가.**

3. **`field2d-core` (등고선/히트맵/벡터장 — 2D 스칼라/벡터장)** — 가장 광범위 신규 패밀리. 그리드(x,y)→스칼라 z(color)/벡터. 필수 대상 다수:
   - **히트맵/컨투어(스칼라)**: `pi-ir-drop-map`, `pi-current-density-map`, `rf-sar-map`, `emi-near-field-map`, `et-chip-temp-contour`, `et-power-map`, `et-thermal-coupling-matrix`, `disp-luminance-uniformity`, `touch-cap-heatmap`, `si-eye-contour`(BER 등고선), `bat-soc-temp-map`, `rf-loadpull-contour`.
   - **벡터장/스트림라인**: `et-airflow-vector`(열유속), `pi-current-density-map`(전류 흐름), `emi-near-field-map`(E/H 벡터).
   - 신규 필요: 비정형 mesh→그리드 보간, colorbar, iso-contour(채움/선), 핫스팟 자동 핀, 보드 geometry 오버레이, log 컬러스케일(BER). **개수상 ROI 최대** — SI/PI/RF/EMI/열/디스플레이/터치 모두 여기에 의존.

4. **`raster-core` (밀도/누적 래스터 — 비-그리드)** — 수만 트레이스 중첩을 픽셀 밀도로. 필수: `si-eye-diagram`(아이 다이어그램 — UI 폴딩 + 밀도 히트). 직교 라인 수천 개로는 성능·가독성 불가. eye-mask 충돌 검사 오버레이. **SI 시그니처 산출물.**

5. **`cad3d-core` / cad-viewer (3D)** — 로드맵 패밀리(STEP→GLB) 위에 필드. 필수: `rf-radiation-pattern-3d`(3D 방사구), `rf-current-distribution`(3D 표면전류), 3D 온도/SAR 볼륨. 신규: 구면/표면 메쉬 + 값 컬러맵, 단면 컷. **MCAE cad-viewer와 엔진 공유 가능**(같은 3D 뷰어에 필드 컬러 plugin).

6. **`graph-node` (네트워크 다이어그램, 소규모)** — `et-thermal-resistance-network`(Foster/Cauer RC 사다리 토폴로지). 노드-엣지 도식. 대안: bar(`bar-path`)로 xy-core 근사 가능(완전 신규 아님, 난이도 절충).

### 엔진패밀리 신규 도입 우선순위 (ROI 기준)
1. **field2d-core** — 압도적 다수(IR drop/온도/SAR/근접장/터치 등 ~15+ 타입)가 의존. 최우선.
2. **smith-core + polar-core** — RF/안테나 도메인 필수, 직교 대체 절대 불가. 묶어서 "RF engine pack".
3. **raster-core(eye)** — SI 시그니처. eye 없이는 SI 도메인 불완전.
4. **cad3d-core** — MCAE cad-viewer와 공유, 3D 필드 plugin으로 확장.

### base-xy 만으로 즉시 가능 (신규 엔진 불필요, MVP 위 plugin 합성만)
SI(S-param/TDR/bathtub/pulse/jitter-hist), PI(PDN-Z/decap/droop/ripple), RF(S11/VSWR/gain-eff/NF/ECC), EMI(emission spectrum/SE/conducted), 배터리(전압-용량/fade/dQdV/EIS Nyquist·Bode/Ragone/runaway), 열(Tj transient/Zth/structure func/throttle), 디스플레이(gamma/Vt/flicker/power-APL/gamut), 터치/센서(SNR/Bode/haptic/piezo/hall), 회로(Bode/Nyquist/PZ/transient/IV/MC/corner/효율/EM-Weibull) — **약 60% 이상이 base-xy + plugin 으로 커버**되며, 나머지 ~40%가 위 신규 4개 패밀리(field2d / smith / polar / raster / cad3d)를 요구한다.

---
참고: 본 카탈로그는 graph-skill SKILL.md 아키텍처(engine family·extends=plugin 합성·requires=validate 게이트·post 후처리)에 직접 사상한 설계 입력이다. 실제 catalog 선언화 시 각 `requires[]` 는 `graph_validate_inputs` 의 `missing[]/questions[]` 로 연결되어, 축 단위·물리 파라미터(ref Z, target-Z, Tjmax, UI, mass-avg SAR, EOL% 등) 누락 시 사용자에게 질문하도록 게이트한다(NEVER invent).