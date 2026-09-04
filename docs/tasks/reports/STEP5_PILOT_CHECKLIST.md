# STEP5 Pilot Execution Checklist

작성일: 2026-07-31
목적: 실제 원문 확보 승인 이후 진행할 6단계 실행 순서. 계획 문서이며 실행하지 않음.

## 1. Source Verification

- [ ] Preferred source(CCEL)에서 원문 확보, 실패 시 Backup source(Internet Archive)로 전환
- [ ] STEP4_PD_VERIFICATION.md 4단계 검증 실행: 발행일 확인 / PD 근거 확인 / 최소 2개 독립 출처 대조(조항 수 18개 일치 등) / 저장소 신뢰성 확인
- [ ] `provenance` 블록(STEP5_SOURCE_REGISTRY_ENTRY.md) 실측값으로 채움 — `acquired_from`/`acquired_url`/`acquired_date`/`checksum` 등
- [ ] 확보 파일을 `data/nae/sources/baptist/nhc_1833.txt`에 저장 (STEP5_SOURCE_ACQUISITION_RECORD.md Local Storage Plan)
- 완료 기준: `acquisition_status: VERIFIED`

## 2. Registry Entry

- [ ] STEP5_SOURCE_REGISTRY_ENTRY.md 레코드를 NAE manifest JSON 형식(scripts/ingest_nae_source.py 입력 형식)으로 변환
- [ ] manifest 필수 필드(`source_filename`, `title`, `copyright_status`, `content_genre`) 확인
- [ ] manifest 파일을 `data/nae/metadata/`에 저장
- 완료 기준: manifest JSON 파일 존재, 스키마 검증 통과

## 3. Ingestion

- [ ] `python -m scripts.ingest_nae_source --manifest <manifest_path> --dry-run` 먼저 실행 — document_id/chunk 수 확인
- [ ] dry-run 결과 이상 없으면 실제 실행(`--dry-run` 제거) 승인 요청
- [ ] `identity_registry.json`에 `nae_theological_position` 등 4개 필드가 additive로 기록되었는지 확인
- 완료 기준: `acquisition_status: INGESTED`

## 4. TSU Generation

- [ ] `python -m scripts.build_tsu_dataset --output-dir <해당 경로> --dry-run`으로 먼저 확인
- [ ] dry-run 출력에서 `nae_metadata` 블록이 STEP5_SOURCE_REGISTRY_ENTRY.md 값과 정확히 일치하는지 확인
- [ ] 실제 TSU 파일 쓰기(`--dry-run` 제거)는 **별도 승인 필요** — 이번 STEP5 범위에서도 다루지 않음
- 완료 기준: dry-run 출력 검증 완료 (실제 파일 생성은 후속 단계)

## 5. Metadata Validation

- [ ] STEP4_TSU_QUALITY_CRITERIA.md 5개 기준(theological claim preservation / confession statement completeness / citation traceability / metadata inheritance / retrieval usefulness)으로 채점
- [ ] 채점 결과를 원문 실측 기준(합성 픽스처가 아닌 실제 New Hampshire Confession 전문)으로 재작성 — STEP4D_TEST_REPORT.md는 synthetic fixture 기준이었으므로 이번이 최초의 실측 검증
- 완료 기준: 5개 기준 중 FAIL 없음 (WARNING은 사유 기록 후 진행 가능)

## 6. Retrieval Readiness

- [ ] 생성된 TSU record가 `core/retrieval.py::RetrievalEngine`의 필수 필드(`tsu_id`/`content`/`document_id`/`chunk_id`)를 모두 충족하는지 확인
- [ ] `verse_mapping`이 비정상적으로 채워지지 않는지 확인 — STEP4D_TEST_REPORT.md에서 관찰된 파일명 기반 오탐(`book_id: EST`) 재현 여부 재확인 필요
- 완료 기준: 검색 인덱싱 가능한 형태로 TSU record 확인, 오탐 사례 있으면 별도 기록

## 순서 준수 원칙

- 각 단계는 이전 단계 완료(체크리스트 전항목 확인) 후에만 진행 — 특히 1(Source Verification)이 미완료 상태로 2 이후 단계를 진행하지 않음
- 4(TSU Generation)와 5(Metadata Validation)는 이번 STEP5 범위에서도 **dry-run/계획까지만** — 실제 파일 생성은 여전히 별도 승인 대상
