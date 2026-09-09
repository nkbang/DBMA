# NAE Observatory — Changelog

내부 관찰용(observability) 도구. Semver: `MAJOR.MINOR.PATCH`.
MAJOR는 도구가 "안정"으로 선언될 때까지 `0` 유지. MINOR = 새 패널/메트릭/기능,
PATCH = 버그 수정·시각 조정. 버전 문자열 단일 출처 = `frontend/package.json::version`
(`App.vue` 헤더가 이를 읽어 표시).

| 버전 | 커밋 | 날짜 | 내용 |
|---|---|---|---|
| **0.5.1** | `2afb183` | 2026-09-08 | 활동 스피너 가시성 수정 — 16px·3px·고대비 아크·0.7s 회전, stalled 앰버 리플, error 깜빡임 |
| **0.5.0** | `fd82201` | 2026-09-08 | 활동 인디케이터 추가 — 백엔드 `activity`(idle/starting/working/stalled/error/stopped) + `report_age_seconds`, 프런트 `ActivityIndicator.vue` 스피너 |
| **0.4.0** | `ba60f0c` | 2026-09-08 | 진행률 스케일 안정화 — `_known_totals`(재-run 사이 total 유지, `0 / N`), `awaiting_first_checkpoint`, 첫 checkpoint 대기 시 인디터미네이트 바 |
| **0.3.1** | `7c089aa` | 2026-09-08 | 스테일 리포트 서빙 버그 수정 — active 리포트 소실 시 이전 수치 무한 서빙 → 폐기 후 0 표시 |
| **0.3.0** | `2cb5614` | 2026-08-15 | Help 기능 — 전 metric 설명 + production 안전성 고지 |
| **0.2.1** | `6af5e7f` | 2026-08-15 | 헤더 브랜딩 — 내서재 작업현황모니터 / NAE Observatory |
| **0.2.0** | `4ec80ea` | 2026-08-15 | Operations Dashboard 확장 — Pipeline / GPU Health / Bottleneck / Time-series / Events |
| **0.1.0** | `f3541d2` | 2026-08-15 | 시스템 패널 — 메모리 / CPU / GPU / Ollama 로드 모델 |
| **0.0.1** | `787c594` | 2026-08-15 | 최초 — NAE Live Progress Dashboard (Vue, read-only Monitor API `:8799`) |

## 버전 부여 규칙

- 새 릴리스: `frontend/package.json` 의 `version` 을 올리고 → 이 표에 한 줄 추가 → `npm run build` → 대시보드 재시작.
- **PATCH** (`0.5.1` → `0.5.2`): 버그 수정, 시각/문구 조정, 성능.
- **MINOR** (`0.5.x` → `0.6.0`): 새 패널·메트릭·API 필드·컴포넌트.
- **MAJOR** (`0.x` → `1.0.0`): `/api/status` 응답 스키마를 "안정"으로 확정하고 하위호환을 약속할 때만.
