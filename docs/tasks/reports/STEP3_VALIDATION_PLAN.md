# STEP3 Validation Plan

작성일: 2026-07-31
목적: STEP3_SAMPLE_DOCUMENT_SPEC.md의 시범 문서를 실제 파일럿(별도 승인 후)에 사용할 때 적용할 검증 기준. 이번 STEP3에서는 계획만 수립하며 실행하지 않음.

## 검증 기준

### 1. Chunk Completeness
- 원문 조항(article) 수와 생성된 chunk 수를 대조 — 조항이 누락되거나 두 개 이상이 한 chunk에 뭉개지지 않았는지 확인
- 판정: 원문 조항 경계와 chunk 경계가 일치하거나, 불일치 시 그 이유(길이 초과로 인한 재분할 등)가 설명 가능한가

### 2. Theological Claim Preservation
- 각 chunk가 원문의 신학적 진술을 문맥 손실 없이 담고 있는지 육안 대조
- 특히 조항 중간에 인용된 성경 구절이 chunk 경계에서 잘리지 않는지 확인
- 판정: 청킹으로 인해 특정 교리 진술의 의미가 왜곡되거나 불완전해지는 사례가 없는가

### 3. Citation Traceability
- 각 TSU record에서 원문(`source_file`)·저자(`author`)·발행연도(제안 필드 `nae_metadata.publication_year`)까지 역추적 가능한지 확인
- `tsu_id` → `document_id` → registry → 원본 파일 경로까지 체인이 끊기지 않는지 확인

### 4. Metadata Inheritance
- NAE_SOURCE_SCHEMA_v1.md 필드(TASK 3 매핑 기준)가 ingest → registry → TSU record까지 유실 없이 전달되는지 확인
- 특히 `denomination`, `theological_position` 등 신규 제안 필드가 실제로 registry 등록 시점부터 끝까지 살아남는지가 핵심 — 이 필드들이 아직 코드에 없으므로, 파일럿 시점에는 "필드 부재로 인한 유실"이 예상된 정상 결과임을 사전 인지

### 5. Retrieval Readiness
- 생성된 TSU record가 `core/retrieval.py::RetrievalEngine`이 기대하는 필수 필드(`tsu_id`, `content`, `document_id`, `chunk_id`)를 모두 갖추었는지 확인
- `verse_mapping`이 비어 있는 것이 정상인지(비-성경 문서이므로) 재확인 — 에러가 아니라 예상된 빈 값임을 검증 로그에 명시

## 실행 방식 (파일럿 승인 시)

1. STEP3_SAMPLE_DOCUMENT_SPEC.md의 1순위 후보 1건만 `data/raw/`(또는 상응 ingest 경로)에 투입
2. 기존 `core/processing.py` ingest 경로 그대로 실행 (코드 변경 없음)
3. `python -m scripts.build_tsu_dataset --dry-run`으로 실제 파일 쓰기 없이 결과만 확인
4. 위 5개 기준을 dry-run 출력 기준으로 체크리스트 형태 채점 (PASS/WARNING/FAIL)
5. 결과를 별도 보고서(`STEP3_PILOT_RESULT.md` 등, 다음 반복)로 기록

## 제한

- 이번 STEP3에서는 위 실행 방식을 계획만 하며 수행하지 않음
- 파일럿 실행은 자료 확보(다운로드) 승인과 별개로 추가 HQ 승인 필요
