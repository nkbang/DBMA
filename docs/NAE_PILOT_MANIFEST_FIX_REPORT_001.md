# NAE Pilot Manifest Fix Report 001

**Project:** NAE-PILOT-MANIFEST-FIX-001
**Date:** 2026-08-02
**Nature:** Pilot artifact 보완 — Validator 수정도 Corpus Migration도 아님
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. 발견 문제 (Phase 1 Manifest Review)

실제 `scripts/source_validator.py --root resources/theological_sources/authority/pilot` 실행 결과(수정 전):

```
=== 결과 요약: PASS=0 WARNING=1 FAIL=0 ===
```

**근본 원인**: FAIL이 아니라 **검사 자체가 실행되지 않았다.** Validator는
`MANIFEST_FILENAME = "source_manifest.yaml"`만 `rglob`으로 탐색하는데,
Pilot-001/002의 실제 파일명은 `manifest_pilot.yaml`이었다 — 필드 문제
이전에 **파일명 불일치로 validator 탐색 대상에서 아예 누락**되어 있었다.

파일명을 바로잡은 뒤 필드 단위로 다시 확인한 결과, 실제 필드 누락도
있었다:

| 대상 | schema_version | title | status | access_control | 비고 |
|---|---|---|---|---|---|
| Pilot-001(Dagg/Hiscox) | `2.0.0`(구버전 표기) | 있음 | 있음 | **없음** | access_control만 누락 |
| Pilot-002(Fuller, 8건) | `2.0.0-pilot-volume-ext`(잠정 확장 표기) | **없음** | **없음** | **없음** | 3개 필드 전부 누락 |

---

## 2. 수정 내용 (Phase 2)

파일: `resources/theological_sources/authority/pilot/source_manifest.yaml`(구 `manifest_pilot.yaml`),
`resources/theological_sources/authority/pilot/fuller/source_manifest.yaml`(구 `manifest_pilot.yaml`)

- **Pilot-001**: `access_control: public` 추가(2개 entry) — PD 자료,
  노출 제한 근거 없음. `schema_version`을 `2.0.0` → `2.1.0`으로 갱신.
- **Pilot-002**: 8개 entry 전부에 `title`(RAW title page 실측 기반,
  기존 `authority/pilot/fuller/volumes.yaml`의 `volume_title` 값 재사용
  — 새로 조사하지 않고 이미 검증된 값을 그대로 인용), `status: ACQUIRED`
  (기존 `NAE_SOURCE_MANIFEST_v1.csv`의 `BAP-MISS-FULLER` 항목 값 계승),
  `access_control: public` 추가. `volume_number`도 함께 추가(스키마
  선택 필드지만 이미 `volumes.yaml`에 확정된 값이 있어 손실 없이 반영).
  `schema_version`을 `2.0.0-pilot-volume-ext` → `2.1.0`으로 갱신(volume
  필드가 이제 ADR-016 정식 스키마이므로 "확장 제안" 표기가 더 이상
  필요 없음).

값은 전부 **기존 Registry(`authority/pilot/*.yaml`) 또는 RAW OCR 원문
실측치**를 그대로 재사용했다 — 새로운 사실 조사나 추정을 추가하지
않았다(요청사항 그대로).

---

## 3. Filename Policy 확인 (Phase 3)

**결정: 파일명을 `manifest_pilot.yaml` → `source_manifest.yaml`로 변경한다.**

- 사유: `scripts/source_validator.py`의 탐색 대상 파일명이 고정
  (`MANIFEST_FILENAME = "source_manifest.yaml"`, 이번 작업에서도 이
  상수는 수정하지 않음 — 금지 사항 준수)이므로, 파일명이 다르면
  Validator가 원천적으로 검사를 수행하지 못한다. 운영 Manifest와의
  구분은 **파일명이 아니라 디렉토리 경로**(`authority/pilot/`,
  `authority/pilot/fuller/`)로 이미 충분히 이루어지고 있다 — 두 pilot
  파일 모두 실제 파이프라인이 참조하는 `baptist/source_manifest.yaml`,
  `modern/{category}/source_manifest.yaml`과 물리적으로 다른 경로에
  있어 혼동 위험이 낮다.
- 문서화: 두 파일 모두 헤더 주석에 "Pilot 검증용, 실제 검색/파이프라인
  에서 참조되지 않음"을 명시(기존 문구 유지) + 이번 파일명 변경 사유를
  주석으로 추가.

---

## 4. Validator 결과 (Phase 4)

**Pilot 전용 재실행** (`--root resources/theological_sources/authority/pilot`):

```
=== 결과 요약: PASS=68 WARNING=0 FAIL=0 ===
```

- Pilot-001(Dagg/Hiscox) 2개 entry, Pilot-002(Fuller) 8개 entry —
  **전부 PASS**, FAIL/WARNING 없음.
- 신규 v2.1.0 검증 항목(필수 필드/4개 enum 필드/status) 전부 정상 통과
  확인(실제 로그에 `access_control=public`, `volume_number=1`~`8` 등
  개별 라인으로 기록됨).

**전체 저장소 재실행**(`--root` 생략, 기본 경로):

```
=== 결과 요약: PASS=89 WARNING=0 FAIL=0 ===
```

기존 `baptist/source_manifest.yaml`(21 PASS)에 이번에 새로 탐색 대상이
된 pilot 2개 파일(68 PASS)이 더해져 89 — **기존 v1.2 결과는 그대로
보존**되었고 회귀 없음. `source_id` 네임스페이스 충돌도 없음(확인:
`BAP-CHURCH-*`/`BAP-MISS-FULLER-*`가 `baptist/source_manifest.yaml`에는
존재하지 않음, CSV에만 있던 값).

---

## 5. Remaining Risk

| # | 리스크 | 설명 | 권고 |
|---|---|---|---|
| 1 | Pilot 데이터가 기본 전체 검증 범위에 포함됨 | 파일명 변경으로 인해 `--root` 생략 시(기본 실행) pilot 10개 entry가 이제 "정상 저장소 검증 결과"에 함께 집계된다(89 PASS 중 68이 pilot). 향후 실제 Corpus 검증 리포트를 볼 때 이 사실을 인지하지 않으면 수치가 부풀려 보일 수 있음 | 향후 CI/자동화에서 pilot 결과를 별도 표기하거나 `--root`를 명시적으로 분리 지정하는 관례를 권고(validator 코드 변경 없이 운영 절차로 해결 가능) |
| 2 | Pilot-001이 이번까지 한 번도 Git에 커밋되지 않았던 사실 확인 | `authority/pilot/*.yaml`, `docs/NAE_METADATA_PILOT_REPORT_001.md`가 작성 이후 지금까지 미커밋 상태였음(실측: `git log`에 이력 없음) — 이번 수정과 함께 최초로 커밋 대상이 됨 | 이번 커밋에 반드시 포함(§완료 조건과 별개로 확인 필요 — 아래 커밋 목록 참고) |
| 3 | `source_type=reference` 잠정치가 그대로 남음 | Pilot-001/002 원 보고서의 F-P1(enum gap) 논의가 재확인만 되었을 뿐 해소되지 않음 — `public_archive`가 v2.1.0에 이미 정식 추가되었으므로(ADR-016) 이번 기회에 `reference` → `public_archive`로 갱신할 수도 있었으나, 이번 명령서 범위(title/status 등 누락 필드 보완)를 벗어나는 판단이라 **손대지 않았다** | 별도 승인 시 `source_type` 값을 `public_archive`로 갱신하는 소규모 후속 작업 권고 |

---

## 완료 조건 답변

1. **Pilot-001 Manifest PASS 여부** — **PASS**(2/2 entry, 0 FAIL).
2. **Pilot-002 Manifest PASS 여부** — **PASS**(8/8 entry, 0 FAIL).
3. **Validator 수정 필요 여부** — **불필요**. `scripts/source_validator.py`는 이번 작업에서 코드 한 줄도 수정하지 않았다(git diff 없음) — 문제는 전적으로 Pilot manifest 쪽(파일명 + 누락 필드)이었음이 확인됐다.
4. **Metadata Migration 전 추가 위험 존재 여부** — **경미한 위험 3건**(§5 Remaining Risk) — 전부 비차단(BLOCKER 아님). Migration Guide Step 4(Pilot 재검증)는 이번 작업으로 **사실상 완료**됐다고 볼 수 있다(실제 Validator로 Pilot-001/002를 재검증해 PASS 확인).

---

## 커밋 대상 파일 목록 (참고)

- `resources/theological_sources/authority/pilot/source_manifest.yaml`(신규 파일명, 구 `manifest_pilot.yaml`) — **최초 커밋**
- `resources/theological_sources/authority/pilot/fuller/source_manifest.yaml`(신규 파일명, 구 `manifest_pilot.yaml`)
- `resources/theological_sources/authority/pilot/{authors,works,editions,sources}.yaml` — **최초 커밋**(§5 Risk #2, 이번에 처음 커밋 대상이 됨)
- `docs/NAE_METADATA_PILOT_REPORT_001.md` — **최초 커밋**
- `docs/NAE_PILOT_MANIFEST_FIX_REPORT_001.md`(본 보고서)

---

*Validator 코드, `source_manifest.schema.yaml`, RAW Corpus, `NAE/corpus/raw/`,
Authority Registry 구조 — 전부 수정하지 않음. Metadata Migration/TSU/
Embedding/Retrieval — 전부 수행하지 않음. Git Commit은 사용자 승인 후에만
수행한다.*
