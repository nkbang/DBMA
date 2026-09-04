# STEP5 Source Acquisition Record

작성일: 2026-07-31
대상: The New Hampshire Confession of Faith (1833)
목적: 실제 원문 확보 승인 이전에, 확보 시 따를 계획을 확정. 이번 문서는 계획이며 다운로드는 수행하지 않음.

## Preferred Source

**CCEL (Christian Classics Ethereal Library)** — STEP4_PD_VERIFICATION.md에서 1순위로 검토된 저장소.

- 사유: 기독교 고전 전문 아카이브로 신앙고백서 텍스트 품질이 상대적으로 높고, 전사(transcription) 오류가 적은 편으로 알려짐
- 확보 시 정확한 URL/판본은 실제 접근 승인 후 확인 예정 — 이번 문서에서는 저장소만 지정, 구체 링크는 미기재(다운로드 미실행 원칙 준수)

## Backup Source

**Internet Archive**

- 사유: 원본 스캔 이미지와 OCR 텍스트를 함께 제공 — CCEL 텍스트와 대조 검증(STEP4_PD_VERIFICATION.md "Source Reliability" 항목)에 사용 가능
- CCEL 접근 불가 시 1차 대체 경로로 지정

## Copyright Basis

- 1833년 뉴햄프셔 침례교단(집단 저작) 발행
- Public Domain 근거: 미국 기준 1928년 이전 출판물 일반 원칙 적용 가능(STEP4_PD_VERIFICATION.md 재확인)
- 확보 시 **원문 그대로의 전사본만 사용** — 현대 편집자의 서문/각주가 추가된 판본은 별도 편집저작권 존재 가능성이 있으므로 배제 (STEP4_PD_VERIFICATION.md 위험 항목 재확인)
- 실제 확보 후 STEP4_PD_VERIFICATION.md의 4단계 검증 절차(발행일/PD근거/신뢰성/저장소)를 반드시 실행

## Provenance Recording Method

확보된 원문에 대해 다음을 기록:

```yaml
acquired_from: ""        # 실제 저장소명 (CCEL 또는 Internet Archive)
acquired_url: ""          # 실제 접근 URL
acquired_date: ""         # 확보 일자
verification_method: ""   # 최소 2개 독립 출처 대조 여부 (STEP4_PD_VERIFICATION.md 방법)
verification_result: ""   # 조항 수(18개)/핵심 문구 일치 확인 결과
checksum: ""               # 확보 파일의 SHA-256 (재현성/무결성 추적용)
```

- 이 provenance 기록은 STEP4_SOURCE_REGISTRATION.md의 `provenance` 블록 및 NAE_SOURCE_REGISTRY_SCHEMA_v1.md 스키마와 정합되도록 확장한 형태
- `checksum`은 registry 등록 시 `file_hash`(core/document_identity.py 기존 로직)와 별개로 원본 확보 단계의 무결성 추적용으로 별도 보관 권장

## Local Storage Plan

- 저장 경로: `data/nae/sources/baptist/nhc_1833.txt` (STEP1/STEP2에서 이미 생성된 디렉토리 구조, 신규 경로 생성 불필요)
- 파일명 규칙: `{source_id_slug}.{ext}` — 이번 문서 대상은 `nhc_1833.txt` (STEP4_PILOT_SOURCE_ENTRY.md `source_id: baptist-confession-001` 기준 축약)
- ingest 시 `scripts/ingest_nae_source.py --inbox-dir data/nae/sources`가 이 경로를 기본으로 참조 (STEP4-D 구현 기준)
- 원본 확보 직후에는 저장만 하고 자동 ingest 트리거는 없음 — 별도 명령 실행 승인 필요

## 비고

- 이 문서는 확보 **계획**만 제공하며, 실제 다운로드는 별도 HQ 승인 이후 수행
