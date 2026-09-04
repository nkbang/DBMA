# NAE Live Progress Dashboard — Build Report

- 작업일: 2026-08-15
- 작업자: CUE
- 대상: Fuller Vol.01 TSU extraction(PID 88689, `NAE.pipeline.tsu.runner`) 을
  건드리지 않는 read-only 실시간 모니터링 대시보드

## 1. 목표

현재 무중단으로 진행 중인 Fuller Complete Works Vol.01 TSU 추출(및 이어질
Vol.02-08 큐)의 진행 상황을 Vue.js 대시보드로 시각화한다. Production
process에는 어떠한 명령도 보내지 않는다(STOP/RESTART/DELETE/REQUEUE 버튼
없음).

## 2. 아키텍처

```
NAE.pipeline.tsu.runner (PID 88689, 무변경)
        │  (파일만 씀 — tsu_report.json/tsu.json/tsu_id_state.json)
        ▼
NAE/corpus/tsu/<identifier>/tsu_report.json  ─┐
.automation/.../queue-vol02-08.log            ├─ read-only
ps aux (active identifier)                    ├─ read-only
Ollama :11434/api/version                    ─┘  (GET health check)
        │
        ▼
Monitor API (FastAPI, GET만, 127.0.0.1:8799)
  .automation/night-shift/dashboard/backend/{collector.py, app.py}
        │  poll every 5s (background thread) → in-memory snapshot
        ▼
Vue 3 대시보드 (Vite build, 같은 포트에서 static 서빙)
  .automation/night-shift/dashboard/frontend/
        │  fetch('/api/status') every 7s (polling)
        ▼
브라우저 (http://127.0.0.1:8799)
```

**Write 경로 없음**: `app.py`에는 GET 라우트(`/api/status`, `/api/health`,
static file serving) 외 어떤 라우트도 존재하지 않는다 — 프론트엔드가 명령을
보내려 해도 받아줄 엔드포인트 자체가 없다. `collector.py`는 파일 읽기,
`ps aux`, Ollama health GET 외 어떤 IO도 하지 않는다.

## 3. 실시간 갱신 방식 — polling 선택 (SSE/WebSocket 대신)

- 로컬 단일 사용자, 인프라가 단순(리버스 프록시 없음)한 조건에서 SSE/WS의
  연결 유지·재연결 로직보다 매 7초 `fetch`가 더 견고함.
- launchd가 프로세스를 재시작해도 다음 polling에서 자동 복구(연결
  재수립 로직 불필요).
- 원본 `tsu_report.json`은 `checkpoint_every=100`마다만 갱신되므로(현재
  페이스 기준 약 18분 간격), 5-10초보다 더 촘촘히 갱신해도 실질적 이득이
  없음 — 7초 간격으로 결정.

## 4. 큐 상태 판정 로직

`Fuller_Complete_Works_Vol01..08` 각각에 대해:
1. 현재 `ps aux`의 active identifier와 같으면 `RUNNING`
2. 아니고 `tsu_report.json`이 존재하며 `partial=false`면 `COMPLETE`
3. 아니고 `queue-vol02-08.log`에 FAILED 라인이 있으면 `FAILED`
4. 그 외 `QUEUED`

`STOP.md` 존재 여부로 큐 전체 정지 상태도 표시(읽기만, 해제하지 않음).

## 5. 검증 결과 (실제 runtime 대조)

| 항목 | tsu_report.json (원본) | Dashboard API | 일치 |
|---|---|---|---|
| candidates_evaluated / processed | 2300 | 2300 | ✅ |
| candidates_total / total | 5452 | 5452 | ✅ |
| percentage | (계산값) 42.19% | 42.19% | ✅ |
| llm_errors / errors | 0 | 0 | ✅ |
| process alive | PID 88689 `ps` 확인됨 | `true` | ✅ |
| Ollama online | `ollama serve` 응답 | `true` | ✅ |

브라우저(desktop/mobile viewport)에서 렌더링 확인 완료, 콘솔 에러 없음,
polling(7s) 네트워크 요청 정상.

### launchd 자동시작/재시작 검증

- `launchctl bootstrap gui/<uid> ~/Library/LaunchAgents/com.dbma.nae.dashboard.plist`
  로 등록 → `state = running` 확인
- `kill -9 <dashboard pid>` 로 강제 종료 → 약 4초 내 새 PID로 자동 재기동,
  `/api/status` 응답 즉시 정상 복구 확인 (KeepAlive)
- 재기동 전후로 Vol.01 production process(PID 88689)와 Ollama 프로세스
  개수(2개) 불변 확인 — 대시보드 재시작이 production에 어떠한 영향도 주지
  않음을 실측 확인

## 6. 상시 실행 구성

- `~/Library/LaunchAgents/com.dbma.nae.dashboard.plist` (`RunAtLoad` +
  `KeepAlive` true) — workstation 로그인 시 자동 시작, 장애 시 자동 재시작
- 고정 포트 `127.0.0.1:8799` — 기존 사용 포트(Streamlit 8501/8502/8530/8599,
  n8n 5678, Ollama 11434, Meilisearch 7700 등)와 충돌 없음 확인(`lsof` 사전
  점검)
- `.claude/launch.json`에 `nae-dashboard`(url attach) 항목 추가 — 기존
  `dbma-ui` 항목은 무변경

## 7. 테스트

`tests/test_nae_dashboard_collector.py` — 16 passed. 모두 `tmp_path` 기반
fixture와 주입된 `ps_reader`/`ollama_checker`로 실제 `NAE/corpus/tsu/`,
실제 프로세스, 실제 네트워크를 전혀 건드리지 않음(순수 함수 파싱 로직 +
`MonitorState` 상태 계산 로직 커버).

회귀 범위: 이번 변경은 `NAE/pipeline/`, `NAE/corpus/tsu/` 등 Protected
Path를 전혀 수정하지 않는 순수 추가(new files) + `requirements.txt`/
`.gitignore`/`.claude/launch.json`에 대한 3줄 미만의 비침습적 추가뿐이므로,
전체 스위트 재실행 대신 신규 유닛 테스트 통과 + production 프로세스
무변경 확인으로 회귀 검증을 갈음함.

## 8. 진행률

- [x] Monitor API (read-only, GET only)
- [x] Vue 3 대시보드 UI
- [x] 실 runtime 값 일치 검증
- [x] launchd 상시 실행/자동 재시작 검증
- [x] 유닛 테스트
진행률: 100%

## 9. 다음 조치 (필요 시)

- Vol01 완료 → Vol02 전환 시 대시보드가 자동으로 큐 상태를 갱신하는지
  볼륨 전환 시점에 한 번 더 육안 확인 권장(로직은 테스트로 커버됨)
- `queue-vol02-08.log`의 `STOP.md` 발생 시 대시보드에 정지 사유가 정확히
  뜨는지는 실제 실패 사례가 아직 없어 유닛 테스트로만 검증됨

## 10. Addendum (2026-08-15) — 시스템 리소스 패널 추가

사용자 요청으로 메모리/CPU/GPU/Ollama 로드 모델 현황을 추가했다. 전부 읽기
전용, 신규 write 경로 없음.

- **메모리/CPU**: `psutil.virtual_memory()` / `psutil.cpu_percent()` /
  `os.getloadavg()` — OS 커널 카운터 읽기만.
- **GPU**: `ioreg -r -d 1 -c IOAccelerator` (Apple Silicon 전용). `powermetrics`
  와 달리 **sudo 불필요** — IORegistry 조회 플래그(`-r`/`-d`/`-c`)만 사용해
  장치에 어떤 명령도 보내지 않는다. `Device Utilization %`, `In use system
  memory`, GPU 모델명/코어 수를 텍스트 파싱으로 추출(ioreg는 JSON 모드가
  없음). 실측: Apple M5 Max, 40-core, 87~99% 사용률(Ollama 추론 중이므로
  높은 게 정상), ~55GB in use.
- **Ollama 로드 모델**: `GET /api/ps`(Ollama 자체 read-only 엔드포인트) —
  현재 로드된 모델명, VRAM 점유량, context length, TTL(`expires_at`)을
  보여준다. 실측: `my-theology-bot-v2:latest`(70.6B, 53.5GB)와
  `qwen3.6:35b-DBMAcode`(36B, 24.9GB) 2개 동시 로드 확인.

**버그 발견 및 수정**: 최초 구현에서 Memory 바의 채움 비율을 psutil의
`percent` 필드(가용 메모리 기준 "메모리 압력" 지표, 이번 실측 83.1%)로
계산했는데, 옆에 표시되는 "82.6 GB / 137.4 GB" 텍스트는 60.1%에 해당해서
막대와 숫자가 서로 다른 값을 시각화하는 모순이 있었다. 막대 채움을
`used_bytes/total_bytes`로 바꿔 텍스트와 항상 일치하도록 수정(프론트엔드만
수정, `system.memory.percent` 필드 자체는 API에 그대로 유지).

**견고성**: GPU 리더가 예외를 던져도(예: 다른 하드웨어에서 `ioreg` 부재)
TSU 진행률 폴링은 계속 정상 동작함을 유닛 테스트로 확인
(`test_one_bad_system_reader_does_not_break_tsu_progress_polling`) — 4개
신규 리더(memory/cpu/gpu/ollama_models) 전부 개별 try/except로 격리.

테스트: `tests/test_nae_dashboard_collector.py` 16 → 23 passed. 실 runtime
값 재확인 및 launchd 재기동 완료, Vol01 프로세스(PID 88689)·Ollama 프로세스
수 불변 재확인.

## 11. Operations Dashboard 확장 (2026-08-15/16) — Grafana/DCGM 벤치마킹

사용자 지시로 "progress bar" 수준에서 Grafana/Prometheus/NVIDIA DCGM 계열
운영 대시보드의 정보 구조(Overview/Health/Pipeline/Resource/Bottleneck/
Time-series/Queue/Events)를 벤치마킹해 확장했다. Prometheus/Grafana 자체는
설치하지 않음(사용자 명시적 보류 — "지금은 Vue 대시보드 우선, 정식
observability layer 승격은 나중에").

### 11.1 신규 백엔드 모듈 (전부 read-only, 순수 판정 로직)

| 모듈 | 역할 | 근거 |
|---|---|---|
| `pipeline_stages.py` | Registration→TSU Extraction→Quality Gate→Review→Embedding→Qdrant 6단계 판정 | `registration_state.json`(RegistrationState enum 미러링), `tsu.json`의 `review_status` 집계(GENERATED/REVIEWED/VERIFIED/REJECTED), `index_report.json`. 실행 안 된 단계는 항상 QUEUED |
| `bottleneck.py` | GPU/CPU/RAM 임계값(85%) 기반 결정론적 병목 판정 | 측정값 전무 시 UNKNOWN, 전부 임계값 미만이면 NONE |
| `gpu_health.py` | HEALTHY/WARNING/ERROR/UNKNOWN 판정 | **utilization 단독 사용 금지** — `pmset -g therm` 열 경고 플래그만 근거. temp/power/clock/pstate/XID는 구조적으로 UNKNOWN·N/A |
| `events.py` | 체크포인트/큐 전환/에러 증가/프로세스 downup 이벤트 로그(최근 200건/4시간) | 폴링 간 스냅샷 diff, 변화 없으면 무이벤트(flooding 방지) |
| `monitor_state.py` | 위 전부를 오케스트레이션(원래 `collector.py`에 있던 `MonitorState`/`PollLoop` 분리 이전) | `snapshot()`은 lock 아래 캐시만 읽고 IO 없음 |

### 11.2 GPU Telemetry 조사 결과 (실제 확인, 추측 아님)

- `powermetrics`: sudo 필수 확인(`must be invoked as the superuser`) — 사용 안 함.
- `ioreg -r -d 1 -c IOAccelerator`: sudo 불필요, **실시간** `Device
  Utilization %`/`In use system memory`/모델명/코어수 제공 확인(Apple M5
  Max, 40-core). 전체 덤프의 `IOReportLegend`에 GPU Power/Performance
  States **채널 스키마**는 존재하지만 실제 수치 샘플링은 private
  `IOReport` API(`powermetrics`가 내부적으로 쓰는 것과 동일 계열) 또는
  커스텀 네이티브 클라이언트가 필요 — 이는 "새 모니터링 인프라"에
  해당해 만들지 않음.
- SMC 온도 센서: `smc`/`istats`/`osx-cpu-temp`/`asitop` 등 미설치 확인,
  신규 설치 안 함(운영 중인 production LLM 옆에 새 의존성 추가 회피).
- **결론**: temperature/power/power_limit/clock/performance_state는
  `gpu_extended`에 항상 `null`로 노출, 프론트엔드는 `UNKNOWN`으로 표시.
  XID는 Apple Silicon에 개념 자체가 없어 `N/A (Apple Silicon)`로 구분
  표시(UNKNOWN과 의미 다름 — "잴 수 없음" vs "해당 없음").
- GPU 100% utilization 상태에서 `gpu_health.status == "HEALTHY"`임을
  실측 확인(유닛 테스트 `test_high_utilization_with_nominal_thermal_is_healthy`
  + 실 runtime `curl` 응답 둘 다 확인) — utilization만으로 WARNING
  처리하지 않는다는 요구사항 충족.

### 11.3 Acceptance Checklist (21개 항목, 2026-08-16T04:07Z 기준 실측)

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| 1 | Vue Dashboard 정상 표시 | **PASS** | 브라우저 스크린샷/accessibility tree로 전 섹션 렌더 확인, 콘솔 에러 없음(과거 재시작 순간의 일시적 ERR_CONNECTION_REFUSED 제외) |
| 2 | Fuller Vol.01 실시간 processed/total/percentage | **PASS** | `curl`↔`tsu_report.json` 직접 대조: 2,600/5,452(47.69%) 일치 |
| 3 | throughput 및 ETA | **PASS** | 314/hour, ETA 9h5m — `elapsed_seconds/processed` 기반, builder.py 자체 ETA 공식과 동일 방식 |
| 4 | Pipeline stage 표시 | **PASS** | Registration COMPLETE(`registration_state.json` 실측)/TSU Extraction RUNNING/Quality Gate BLOCKED(verified=0)/Review·Embedding·Qdrant QUEUED — 전부 실제 파일 근거 |
| 5 | C1/process 상태 | **PASS** | PID 88689 `ps` 매칭 → `C1 RUNNING` |
| 6 | Ollama/llama-server 상태 및 `-np 1` | **PASS** | OLLAMA ONLINE, "Concurrency (-np): 1, 1" — 실행 중인 두 llama-server 프로세스 커맨드라인에서 직접 파싱 |
| 7 | GPU utilization | **PASS** | 99~100%, `ioreg` 실시간 값과 일치 |
| 8 | GPU Health/Telemetry — 불가 항목 UNKNOWN | **PASS** | Temperature/Power/GPU Clock/Performance State = UNKNOWN, XID = N/A(Apple Silicon), 100% util에도 HEALTHY 판정 확인(§11.2) |
| 9 | CPU/RAM | **PASS** | Resource 패널 실측치(82.x GB/137.4GB, CPU %) |
| 10 | Disk/Network | **PASS** | Disk 사용량 + read/write 속도, Network ↑↓ 속도 모두 표시(psutil 카운터 델타) |
| 11 | n8n health | **PASS** | `GET /healthz` → `{"status":"ok"}` 실측, N8N ONLINE 표시 |
| 12 | Queue 상태 | **PASS** | Vol.01 RUNNING + Vol.02-08 QUEUED, 실제 큐 로그/파일 기반 |
| 13 | Error/Event log | **PARTIAL** | 로직은 유닛 테스트 16건(체크포인트/에러증가/프로세스·Ollama down-up/큐 전환)으로 검증되고 API에 정상 연결됨. 단, 이번 관측 구간(대시보드 재시작 이후 수 분)에는 실제 상태 전이가 없어 **실시간으로 캡처된 이벤트 사례는 없음**(체크포인트 간격이 현재 페이스로 ~18분이라 자연 발생 대기 필요) — 추측 없이 있는 그대로 보고 |
| 14 | 5초 기본 polling | **PASS** | 기본값 5s, 네트워크 요청 간격 실측 일치 |
| 15 | 5/10/30/60초 refresh 선택 | **PASS** | 드롭다운에서 10s 선택 → "next" 표시가 실제로 10초 뒤로 이동함을 확인 |
| 16 | LIVE MONITOR ON/OFF | **PASS** | 클릭 시 헤더 LIVE→PAUSED, 버튼 ON→OFF 전환 확인 |
| 17 | Monitor OFF가 production에 영향 없음 | **PASS** | OFF 상태에서 프론트 폴링 정지(네트워크 요청 미증가) 확인 + **동시에** 백엔드 `curl` 직접 호출은 정상 응답(`last_poll_ok:true`), Vol01 PID/Ollama 프로세스 수 불변 확인 |
| 18 | Last Update / Next Update 표시 | **PASS** | 헤더에 `last HH:MM:SS · next HH:MM:SS` 표시, refresh 간격 변경에 따라 next 값 변화 확인 |
| 19 | 전체 refresh 없이 API polling | **PASS** | `fetch()`만 사용, `location.reload`/`window.location` 코드 전무(grep 확인) |
| 20 | read-only, production control route 없음 | **PASS** | `app.py`에 GET 라우트 2개(`/api/status`,`/api/health`)만 존재, backend 전체에 POST/PUT/DELETE/PATCH 라우트 0건(grep 확인) |
| 21 | Dashboard 재시작/장애가 production에 영향 없음 | **PASS** | `kill -9` 직후 launchd 자동 재기동(4~5초) 확인, 재기동 전후 Vol01 PID(88689) elapsed time 연속 증가·Ollama 프로세스 수(2) 불변 재확인(이번 세션 중 3회 반복 검증) |

**요약**: PASS 20 / PARTIAL 1(Event log — 메커니즘은 검증됨, 실시간 캡처
사례만 관측 대기 중) / FAIL 0 / UNKNOWN 0.

### 11.4 범위 제한 준수

- Prometheus/Grafana/DCGM 미설치(사용자 명시 보류)
- GPU telemetry용 신규 native 도구/서드파티 패키지 설치 안 함
- 이번 확장 전 구간(§1-§10)에서 추가한 unit test 외 신규 테스트 suite
  확장 없음(§11 진행 중 발견한 버그 수정 2건 — HealthBar 시각 버그,
  `-np` 미표시 누락 — 은 기존 커버리지로 충분해 신규 테스트 추가하지
  않음)
- Vol01 production(PID 88689)·Ollama·TSU·Registration에 mutation 없음
  (전 구간 GET/read만 사용, 코드 레벨에서 write 라우트 자체가 존재하지
  않아 구조적으로 불가능)
