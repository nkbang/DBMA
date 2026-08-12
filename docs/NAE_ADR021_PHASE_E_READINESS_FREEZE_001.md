# ADR-021 Phase E/F FREEZE — Readiness Record

작성일: 2026-08-11
목적: C1의 독립적 Phase E/F 감사가 진행되는 동안 CUE는 dry-run/Evidence
Package 생성을 수행하지 않는다(독립 검증 훼손 방지). 이 문서는 그 대기
기간 동안의 준비 상태만 기록한다 — 코드 변경, Production/Qdrant/TSU
mutation, quality threshold 변경, dry-run 실행, Evidence Package 생성
전부 수행하지 않았다.

```
ADR-021 = CONDITIONAL GREEN
Phase B/C = IMPLEMENTED
Phase E/F = NOT YET AUTHORIZED — HOLD
```

---

## E. 현재 git HEAD 및 Production baseline hash

```
git HEAD: b2489e24bf0badd0e3efd4700d6d520f52eff045
          (b2489e2 docs(nae): update work plan progress — Phase B/C complete, Phase D partial)
직전 구현 커밋: b1ebc3a (feat(nae): ADR-021 Phase B — NAE/pipeline/registration/ module implementation)

Production TSU 파일 SHA256:
  NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json = 1da2d7dd75d5235f645d5d2b22c19f865723134754e08028c93fc7d3943ceb2a
  NAE/corpus/tsu/Dagg_Church_Order/tsu.json      = 10fc58ef2f80902c967a6cf24409be78a04e993303ffcb7228853a1698516ea5
  총 레코드 수 = 4,117 (verified=3,319 / generated=776 / rejected=22)

Qdrant:
  URL = http://localhost:7333
  collection = nae_tsu_v1
  points_count = 3,319
  status = green
```

이 값들은 이번 FREEZE 시점의 기준점이다 — Phase E/F 재개 시 이 문서의
값과 재대조해 그 사이 어떤 mutation도 없었음을 증명하는 데 사용한다.

---

## A. 8개 모듈 Interface/Documentation 재검토

| 모듈 | 라인 수 | 공개 인터페이스 요약 |
|---|---|---|
| `identity.py` | 105 | `slugify()`, `resolve_collision()`, `make_author_id/work_id/edition_id()`, `check_source_id_unique()`, `issue_identity() -> NewIdentity` |
| `source_validator.py` | 75 | `SourceValidationResult`(errors/warnings/passed), `validate_raw_integrity()`, `validate_identity()`, `validate_metadata()`, `validate_provenance()`, `validate() -> SourceValidationResult` |
| `raw_preservation.py` | 139 | `sha256_of_file()`, `ChecksumLedger`(append-only, `entries()`/`append()`/`first_checksum_for()`/`find_duplicate_source_id()`), `preserve() -> PreservationResult`, `verify() -> VerificationResult`, `is_catalog_duplicate()` |
| `authority.py` | 111 | `find_author_candidates()`/`register_author()`, `find_work_candidates()`/`register_work()` — legacy snapshot는 항상 읽기만, 신규 registry만 write |
| `manifest_writer.py` | 45 | `existing_source_ids()`, `write_entry()` — 명시적 `manifest_path` 필수, 하드코딩 기본경로 없음 |
| `state.py` | 97 | `RegistrationState`(9 상태: 5 성공 + 4 실패), `RegistrationStateStore`(source_id별 독립 상태), `ExceptionQueue`(Production 큐와 물리적 분리) |
| `quality_gate.py` | 101 | `QualityGateVerdict`(PASS/WARNING/FAIL), `FAIL_REASONS`(7항목 고정), `WARNING_REASONS`(5항목, 임계값 미확정), `evaluate() -> QualityGateResult` |
| `pipeline.py` | 182 | `RegistrationRequest`/`RegistrationResult`, `register_source()` — `extract_pages()`(기존, 무수정)만 호출, **TSU Builder 호출 없음**(명시적 정지 지점) |

재검토 결과 특이사항 없음 — 각 모듈이 ADR-021 §16의 책임 분담과 정확히
일치. `pipeline.py`가 Quality Gate 직후, TSU Builder 호출 이전에
`return`하는 것을 코드 레벨에서 재확인함(182행, `register_source()`
마지막 블록).

---

## B. ADR-021 §16 ↔ 실제 구현 대응표

| ADR-021 §16 명세 | 실제 파일 | 상태 |
|---|---|---|
| `identity.py` — 발급 + 충돌 처리 | `NAE/pipeline/registration/identity.py` | 구현 완료, 테스트됨(collision suffix) |
| `source_validator.py` — 신규 upstream validator | `NAE/pipeline/registration/source_validator.py` | 구현 완료, 기존 `scripts/source_validator.py`와 호출 관계 없음 확인 |
| `raw_preservation.py` — 체크섬 + duplicate 2계층 | `NAE/pipeline/registration/raw_preservation.py` | 구현 완료, 테스트됨(tamper 감지, Level 2 duplicate) |
| `authority.py` — Option C 대조/등록 | `NAE/pipeline/registration/authority.py` | 구현 완료, legacy snapshot 비write 확인(코드상 write 호출 없음) |
| `manifest_writer.py` — entry 작성 | `NAE/pipeline/registration/manifest_writer.py` | 구현 완료, source_id 중복 시 예외 발생 확인 |
| `state.py` — 상태 머신 + exception queue | `NAE/pipeline/registration/state.py` | 구현 완료, ADR-020 `ingest/state.py`·`NAE/review/human/exception_queue.json`과 파일 경로 물리적 분리 확인 |
| `quality_gate.py` — PASS/WARNING/FAIL | `NAE/pipeline/registration/quality_gate.py` | 구현 완료, FAIL 7항목 고정 그대로 코드화, WARNING 임계값 미설정(하드코딩 안 됨 — 호출자가 boolean으로 전달) |
| `pipeline.py` — 오케스트레이션 | `NAE/pipeline/registration/pipeline.py` | 구현 완료, `extract_pages()` 1곳만 외부 호출, TSU Builder 호출 없음 |

8/8 대응 완료. §16 대비 누락된 모듈 없음, 초과 구현(module 증식) 없음.

---

## C. 106/106 테스트 — Test-to-Requirement Mapping

| 테스트 | 파일 | 검증 대상(ADR-021 조항) |
|---|---|---|
| `test_happy_path_reaches_quality_passed` | `test_pipeline_smoke.py` | §2 전체 파이프라인 흐름, §8 PASS 판정, manifest 작성 |
| `test_identity_collision_gets_suffix` | 〃 | §4 ID 충돌 시 숫자 suffix 규칙 |
| `test_missing_raw_file_routes_to_exception_queue` | 〃 | §10 `RAW_CHECKSUM_MISMATCH` 상태 전이, §11 Exception Queue 기록 |
| `test_checksum_reverify_detects_tamper` | 〃 | §6 체크섬 재검증(접근 시점 재계산 vs 최초 기록) |
| `test_duplicate_detection_level2_same_content_different_id` | 〃 | §9 Level 2(raw content checksum) duplicate 탐지 |
| `test_production_untouched` | 〃 | §14 Dry-run Isolation 원칙의 코드 레벨 보증(Production TSU 파일 해시 불변 guard) |
| 기존 ADR-020 테스트 100건 | `tests/`(ingest/manifest/incremental 관련) | ADR-020 downstream 무수정 확인(회귀) — 이번 Phase B 구현이 이 스위트에 영향 주지 않음 |

**커버리지 갭(§17 Test Specification 대비, 미착수 영역)**: Source
Validation 개별 항목(Raw/Metadata/Provenance/Integrity 각각의 FAIL/
WARNING 분기), Quality Gate WARNING 5항목 개별 검증, Authority
`find_author_candidates`/`find_work_candidates` 자체의 단위 테스트,
Idempotent re-run(동일 source 재실행), manifest 유일성 검사 자체의
단위 테스트. 이번 6건은 Phase B "wiring이 실제로 동작하는가"를 증명하는
smoke test이며, §17이 요구하는 14개 영역 전체 커버리지가 아니다 — 이
갭은 Phase D 본작업(현재 부분 완료, work plan §1 `[~]`로 표기됨) 대상.

---

## D. Phase E 실행에 필요한 Command/Config/Dependency 목록 (준비만, 미실행)

```
실행 환경:
  venv: ~/envs/dbma311 (yaml, qdrant-client 등 의존성 확인됨)
  Qdrant: http://localhost:7333 (NAE/pipeline/index/config.py 기준, 실행 불필요 — Phase E는 TSU Builder 이전에 정지하므로 Qdrant 접속 자체가 발생하지 않음)

Phase E 대상 후보 (ADR-021 §13, 3건 조사 완료, 다운로드 미수행):
  1. forwardmission00giff (Gifford, 1897, 36p) — 1순위 추천
  2. mrsestherkimpakk00hall (Hall, n.d., 18p)
  3. kimchangsikkorea00unse (저자정보 결여, 10p) — FAIL 경로 검증용

실행 시 필요할 것으로 예상되는 단계(실행하지 않음, 목록만):
  1. 후보 원자료 다운로드 (Archive.org, https://archive.org/download/<identifier>/)
     — 이 단계 자체가 "실제 다운로드"이므로 Phase E 승인 전까지 수행 안 함
  2. NAE/corpus/raw/archive_org/<category>/<work>/ 에 배치 (hocr.html 등
     extract.py가 기대하는 파일명 규칙 준수 필요 — 코드 재확인 완료: hocr.html/ocr.txt/original.pdf)
  3. RegistrationRequest 구성 (surname/given_name/title/edition_slug/
     publication_year/copyright_status/archive_source/source_id/manifest_path)
  4. NAE/pipeline/registration/pipeline.py::register_source() 호출
  5. 결과(RegistrationResult.final_state)가 QUALITY_PASSED 또는
     QUALITY_GATE_FAILED(Candidate 3 예상)인지 확인
  6. TSU Builder 호출 없이 여기서 정지(§14 Dry-run Isolation)

Config 변경 필요 여부: 없음(quality_gate.py 임계값은 boolean 플래그로
받으므로 코드 수정 없이 실측값을 넘길 수 있음 — 이번 FREEZE 기간 동안
quality threshold 변경 금지 원칙과 상충 없음, 애초에 하드코딩된
숫자 임계값이 없어 "변경"할 대상 자체가 없음).
```

---

## F. HOLD

C1의 독립 Phase E/F 감사가 반환될 때까지 위 A~E 준비 상태를 유지하며
대기한다. 이후 재개 시 이 문서의 E(git HEAD/baseline hash) 값과
재대조하여 그 사이 mutation이 없었음을 먼저 증명한 뒤 C1 findings를
반영해 Phase E/F 실행 여부를 다시 결정한다.
