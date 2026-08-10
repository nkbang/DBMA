# NAE-REGRESSION-001 Report

작성일: 2026-07-31
작성자: CUE
범위: Source Manifest v1.2 검증 / Validator Regression / TSU Dataset Isolation Regression / Existing DBMA Pipeline 영향 확인 / git status 안전성 확인

## 결과 요약

| # | 항목 | 결과 |
|---|---|---|
| 1 | Source Manifest v1.2 검증 | PASS (검증 중 불일치 1건 발견·수정) |
| 2 | Validator Regression | PASS |
| 3 | TSU Dataset Isolation Regression | PASS |
| 4 | Existing DBMA Pipeline 영향 확인 | PASS |
| 5 | git status 안전성 확인 | PASS |

## 1. Source Manifest v1.2 검증

- `scripts/source_validator.py` 실행: **PASS=21, WARNING=0, FAIL=0**
- `resources/theological_sources/baptist/source_manifest.yaml`을 PyYAML로 직접 로드해 확인: `NHBC1833.aliases == ["baptist-confession-001"]`, 총 7건 source 유지
- **발견 및 수정**: 검증 중 `source_manifest.yaml`의 `schema_version` 필드가 여전히 `"1.1"`로 남아있음을 발견(스키마 정의 파일만 v1.2로 올리고 실데이터 파일 갱신을 누락했던 것 — NAE-SOURCE-DEDUP-001 작업 중 생긴 불일치). `"1.2"`로 수정 후 재검증 — PASS=21 유지 확인.
- 부수적으로 `source_manifest.schema.yaml` 내 `example:` 블록도 `schema_version: "1.1"`로 낡아 있던 것을 함께 `"1.2"`로 갱신, `aliases: []` 예시 필드 추가.

## 2. Validator Regression

- 이전 세션에서 만든 결함 fixture(스크래치패드, `source_id` 누락/`status` 오탈자/`license` 누락/`source_id` 중복 4종)를 재실행
- **결과 완전히 동일**: PASS=11, WARNING=0, FAIL=5, exit=1 — status enum을 4개→7개로 확장한 뒤에도 기존 4가지 결함 탐지 로직에 회귀 없음.

## 3. TSU Dataset Isolation Regression

- `tests/test_build_tsu_dataset_output_path.py` 3건 재실행: **3 passed**
  - `--dataset-path` override 시 지정 경로에만 기록, 기본 경로 미접촉
  - `--dataset-path` 생략 시 기존 기본 경로 그대로 사용
  - `--help`에 플래그 노출 확인

## 4. Existing DBMA Pipeline 영향 확인

- 관련 회귀 스위트 16개 파일 실행(`test_tsu_structure`, `test_tsu_manifest`, `test_build_tsu_dataset_*`, `test_tsu_content_quality`, `test_tsu_sermon_fields`, `test_tsu_builder_heading_integration`, `test_reindex_document`, `test_dedupe_tsu_dataset`, `test_scripture_evidence_resolver`, `test_index_orchestrator`, `test_config_loading`, `test_build_tsu_dataset_output_path`, `test_document_context`, `test_pipeline_state` 등): **96 passed, 0 failed**
- **실제 프로덕션 코퍼스 dry-run**(요청 전 세션에서 백그라운드로 시작해 이번 세션 중 완료됨): `python -m scripts.build_tsu_dataset --dry-run` (인자 없음, 기존 방식 그대로) → **81개 문서, 53,238개 TSU record**를 메모리상으로만 생성. 출력 샘플 확인 결과 전부 `"nae_metadata": null"` — NAE 관련 신규 필드가 비-NAE 문서에 대해 정확히 no-op으로 동작함을 대규모로 재확인.
- `output/bench/tsu_dataset.jsonl`(600MB), `output/bench/tsu_manifest.json` 파일의 mtime을 dry-run 전후로 비교: **`Jul 28 16:17`로 동일** — 이번 세션 동안 어떤 쓰기도 발생하지 않았음을 파일시스템 레벨에서 확인.

## 5. git status 안전성 확인

- `git status --short`: 이번 세션에서 만든 문서·스크립트만 untracked로 나타남(`docs/NAE_*`, `docs/tasks/reports/STEP5_*`, `docs/agents/c1/C1-TASK-ORDER-036.md`, `resources/theological_sources/`, `scripts/source_validator.py`, `tests/test_build_tsu_dataset_output_path.py`)
- `git diff --stat`: 추적 대상 파일 중 수정된 것은 **`scripts/build_tsu_dataset.py` 1개뿐**(+17/-1, `--dataset-path` 추가) — 다른 기존 추적 파일 변경 없음
- **RAW 파일 생성 여부**: `data/nae/sources/{baptist,theology,public_domain,commentary}/`를 직접 확인 — `.gitkeep` 외 파일 없음. 원문 파일이 생성되지 않았음을 확인.
  - (참고: 최초 `find -newer`로 `data/RAW` 전체를 훑었을 때 다수 기존 파일이 "newer"로 나왔으나, 이는 잘못된 기준시각(오래된 산출물 파일의 mtime) 때문에 발생한 노이즈였음 — `data/RAW`는 사용자의 일상적 프로덕션 워크플로가 계속 사용하는 디렉토리이며 이번 세션과 무관. 올바른 검사(대상 디렉토리를 `data/nae/sources/`로 한정)로 재확인해 결론을 정정함.)
- **기존 TSU dataset 변경 여부**: 위 4번 항목에서 mtime 불변 확인 — 변경 없음
- **output overwrite 여부**: 동일 — `output/bench/` 하위 파일 변경 없음

## 조건 준수 확인

- RAW 파일 생성 금지: 준수 (data/nae/sources/ 비어 있음 확인)
- 기존 TSU dataset 변경 금지: 준수 (mtime 불변 확인)
- output overwrite 금지: 준수 (output/bench/ 무변경 확인)

## 발견된 이슈 및 조치

| 이슈 | 조치 |
|---|---|
| `source_manifest.yaml`의 `schema_version`이 `aliases` 필드 추가 시 "1.1"에 머물러 있었음 | "1.2"로 수정, 재검증 완료 |
| `source_manifest.schema.yaml`의 예시 블록도 동일하게 낡아 있었음 | "1.2" + `aliases: []` 예시로 갱신 |

두 건 모두 이번 회귀 검증 과정에서 발견되어 즉시 수정했으며, manifest 데이터 자체(7건의 source 항목, license/status/tradition 등)는 변경하지 않았습니다.

## 다음 단계 제안

- C1의 NAE-CORPUS-FIX-001(CSV 정합성 복구) 완료 보고 대기 중
- 위 완료 후 NAE-SOURCE-DEDUP-001/NAE-REGRESSION-001 모두 통과했으므로, SLBC1689 RAW Acquisition 착수 여부를 HQ가 최종 승인할 수 있는 상태
