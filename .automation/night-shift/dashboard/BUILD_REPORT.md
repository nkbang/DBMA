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
