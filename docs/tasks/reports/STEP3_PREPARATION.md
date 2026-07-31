# STEP3 Preparation — TSU Conversion Pipeline Validation

작성일: 2026-07-31
목적: STEP 3 착수 전 준비 항목 정리. 실행은 별도 HQ 승인 후 Task Order로 진행.

## 다음 단계

**STEP 3 — TSU Conversion Pipeline Validation**
NAE Baptist Knowledge Base 자료를 기존 DBMA TSU(Theological Source Unit) 파이프라인에 태울 수 있는지 검증하는 단계. 실제 TSU 생성/Vector 생성은 이번 준비 단계에 포함되지 않음.

## 준비 항목

### 1. Source Ingestion Format
- STEP2 후보 자료(TASK 4)는 대부분 영문 텍스트/스캔본 예상 — 기존 DBMA 추출 파이프라인(`core/`)이 지원하는 입력 포맷(PDF, TXT, DOCX 등) 확인 필요
- 스캔본 OCR 필요 자료와 순수 텍스트 자료를 사전 구분해야 처리 방식 분기 가능

### 2. Document Normalization
- 고어체 영어(17~19세기 문헌) 정제 기준 필요 — 기존 신학 문서 정제 규칙과 다를 수 있음
- 헬라어/히브리어 원문 포함 여부에 따른 인코딩/정규화 검토 (NAE_SOURCE_SCHEMA_v1.md의 `language` 필드와 연동)

### 3. Chunking 기준
- 기본 chunk size 1200 / overlap 200 (CLAUDE.md 기준)이 신앙고백서·설교집 등 문서 유형별로 그대로 적용 가능한지, 혹은 `source_type`별 조정이 필요한지 검토 대상
- 신앙고백서는 조항(article) 단위 청킹이 더 적합할 가능성 — 기존 청킹 로직과의 정합성 확인 필요

### 4. TSU Extraction Mapping
- NAE_SOURCE_SCHEMA_v1.md의 10개 필드가 기존 TSU 메타데이터 구조와 어떻게 매핑되는지 확인 필요
- `source_id`, `processing_status` 필드가 기존 파이프라인의 문서 추적 방식과 충돌 없는지 검증 대상

### 5. Metadata Inheritance
- `sources/` → `processed/` → `embeddings/` 단계 이동 시 메타데이터가 유실 없이 전달되는 구조 설계 필요
- 기존 DBMA 문서 메타데이터 상속 방식(코드 레벨) 조사 선행 필요 — 이번 STEP3 준비 단계에서는 조사 항목으로만 기록

## 제한 사항 준수

- git push: 미실행
- TSU 생성: 미실행
- Vector 생성: 미실행
- 실제 자료 다운로드: 미실행

## 다음 추천

- STEP 3 착수 전 기존 `core/` 파이프라인의 ingestion/chunking 코드 조사(읽기 전용)를 별도 Task Order로 승인 요청
- STEP 3는 "검증"이 목적이므로 실제 자료 1건(예: 1689 Confession 원문 일부)만 시범 사용하는 소규모 파일럿으로 범위 제한 권장
