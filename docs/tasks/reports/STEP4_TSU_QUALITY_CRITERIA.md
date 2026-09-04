# STEP4 Expected TSU Quality Criteria

작성일: 2026-07-31
목적: STEP4_PIPELINE_DRYRUN.md 실행(승인 시) 결과를 채점할 기준. STEP3_VALIDATION_PLAN.md의 5개 기준을 이번 Pilot 대상 문서(New Hampshire Confession 1833)에 맞게 구체화.

## 검증 기준

### 1. Theological Claim Preservation

- 각 chunk가 조항(article)의 신학적 진술을 문맥 손실 없이 담고 있는가
- 특히 "믿음의 조항(Article of Faith)"이 chunk 경계에서 문장 중간에 잘리지 않는가
- 판정 척도: PASS(완전 보존) / WARNING(경계 근접, 문맥 일부 분산) / FAIL(진술이 절단되어 의미 손실)

### 2. Confession Statement Completeness

- 원문 18개 조항 전체가 어느 chunk에도 누락 없이 포함되는가 (Chunk Completeness의 문서 특화 버전)
- 서문(preamble)이 있다면 별도로 완전성 확인
- 판정 척도: PASS(18개 전부 확인) / WARNING(일부 조항 경계 모호) / FAIL(조항 누락)

### 3. Citation Traceability

- `tsu_id` → `document_id` → `source_file` → STEP4_SOURCE_REGISTRATION.md 명세까지 역추적 가능한가
- 인용 시 "1833 New Hampshire Confession, Article N" 형태로 특정 조항을 가리킬 수 있는가 — 이번 문서는 `chapter`/`page` 필드가 조항 번호를 담기에 적합한지 확인 필요(신앙고백서는 chapter 개념이 없으므로 기존 필드 재해석 여지 검토)
- 판정 척도: PASS / WARNING / FAIL

### 4. Metadata Inheritance

- 검증 가능 범위(코드 반영된 필드만): `title`, `author`, `language`, `document_id`가 모든 chunk에 일관되게 전파되는가
- **검증 불가 범위(사전 인지)**: `theological_position`, `content_genre`, `denomination_context` 등 `nae_metadata` 하위 필드는 코드 미반영이므로 이번 dry-run에서 확인할 수 없음 — 이는 FAIL이 아니라 "N/A (코드 미반영)"으로 별도 표기
- 판정 척도: 코드 반영 필드는 PASS/WARNING/FAIL, 미반영 필드는 N/A

### 5. Retrieval Usefulness

- 생성된 TSU record가 `core/retrieval.py::RetrievalEngine`이 요구하는 최소 필드(`tsu_id`, `content`, `document_id`, `chunk_id`)를 모두 갖추어 검색 인덱싱 가능한 형태인가
- `verse_mapping`이 빈 상태로 남는 것이 에러 로그 없이 정상 처리되는가 (STEP3에서 확인된 정상 케이스의 실제 재현 확인)
- 판정 척도: PASS / WARNING / FAIL

## 종합 판정 방식

- 5개 기준 중 코드 반영 범위 내(1, 2, 3, 5 + 4의 일부)에서 PASS가 다수이고 FAIL이 없으면 "Pilot 성공"으로 간주
- 기준 4의 N/A 항목은 실패로 집계하지 않음 — 별도로 "정책은 확정되었으나 코드 미반영" 상태로 보고

## 비고

- 이 채점 기준은 이번 STEP4에서 **적용 계획만** 세운 것이며, 실제 채점은 STEP4_PIPELINE_DRYRUN.md 실행 승인 이후 수행
