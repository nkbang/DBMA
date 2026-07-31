# STEP4 Pipeline Dry Run Plan

작성일: 2026-07-31
목적: STEP4_SOURCE_REGISTRATION.md 대상 문서를 실제 파이프라인에 태우기 전 단계별 실행 계획. 계획 문서이며 실행 없음.

## 검증 흐름

```
Source (원문 파일)
  ↓ Normalize
  ↓ Chunk
  ↓ TSU
  ↓ Metadata inheritance
```

### 1. Source

- 입력: 확보된 원문 파일 (형식 미정 — `txt` 또는 `pdf` 가능성 높음, STEP4_SOURCE_REGISTRATION.md 기준 확보 전)
- 배치 위치: `DEFAULT_RAW_DIR` (config.yaml `raw_dir`) — 기존 ingest 경로 그대로 사용, 신규 경로 생성 안 함
- 사전 조건: 원문 확보(다운로드) — **이번 STEP4 범위 밖**, 별도 승인 필요

### 2. Normalize

- 실행 모듈: `core/processing.py` (조사됨, STEP3_TSU_PIPELINE_ANALYSIS.md 참고) — 코드 변경 없이 기존 경로 그대로 통과
- 확인 사항: 고어체 영어(1833년 문헌) 정제 시 원문 훼손 없는지, 조항(article) 구분자가 정제 과정에서 소실되지 않는지
- 예상 산출: `identity_registry.json`에 문서 레코드 1건 등록 (`title`, `author`, `language=en`, `source_type`=파일 포맷)

### 3. Chunk

- 실행 모듈: `core/processing.py` 청킹 로직 (기본 chunk size 1200 / overlap 200, CLAUDE.md 기준)
- 확인 사항: 신앙고백서 특성상 18개 조항(article)이 청크 경계와 자연스럽게 맞물리는지 — 짧은 문서이므로 전체가 소수(1~5개 내외 예상) chunk로 나뉠 가능성
- 산출: `output/{stem}_chunks.txt`

### 4. TSU

- 실행 모듈: `core/tsu_builder.py::build_tsu_records()` (코드 변경 없음)
- 예상 결과: `verse_mapping`은 대부분 빈 dict (성경 본문이 아니므로 정상, STEP3_TSU_PIPELINE_ANALYSIS.md에서 이미 확인된 정상 케이스)
- `title`/`author`/`language`/`source_file` 등 기존 필드는 registry 값 그대로 전파 예상
- `nae_metadata` 블록: **이번 STEP4 시점에 코드 미반영 상태이므로 TSU record에 나타나지 않음** — 이는 실패가 아니라 예상된 결과 (NAE_METADATA_POLICY_v1.md는 정책 확정이지 코드 반영이 아님)

### 5. Metadata inheritance

- 검증 대상: `title`, `author`, `language`, `document_id` → 모든 chunk에 일관되게 전파되는지
- `theological_position`(document-level, chunk 상속) 정책은 **코드에 필드가 없으므로 이번 dry-run에서는 검증 불가** — dry-run 출력에는 나타나지 않음을 사전 인지하고 실행해야 함. 이 항목은 STEP4_TSU_QUALITY_CRITERIA.md에서 "코드 미반영으로 인한 예상된 미달성"으로 명시 예정

## 실행 방식 (승인 시)

```bash
python -m scripts.build_tsu_dataset --dry-run
```

- `--dry-run` 플래그로 실제 파일 쓰기 없이 콘솔 출력만 확인 (STEP3_VALIDATION_PLAN.md 실행 방식 재사용)
- 출력된 TSU record 3건(스크립트 기본 미리보기 개수)을 STEP4_TSU_QUALITY_CRITERIA.md 기준으로 채점

## 제한

- 이번 문서는 계획만 다루며 실행하지 않음
- 실행 전 반드시 (a) 원문 확보 승인, (b) registry 등록 승인 두 가지가 선행되어야 함
