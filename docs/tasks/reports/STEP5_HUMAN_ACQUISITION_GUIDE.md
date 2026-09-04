# STEP5 Human Source Acquisition Guide

작성일: 2026-07-31
대상: 사람(HQ 또는 담당자)이 직접 원문을 확보해 NAE Pipeline에 전달하기 위한 안내서.
배경: STEP5-B에서 `WebFetch` 도구가 verbatim 텍스트를 반환하지 못함을 확인(STEP5_SOURCE_COMPARISON.md) — 자동화 대신 사람이 직접 저장소에서 복사/다운로드하는 경로로 전환.

## 필요한 파일

- **The New Hampshire Confession of Faith (1833)** 전문
- 형식: 순수 텍스트(TXT) — STEP5_IMPORT_FORMAT_DECISION.md 결정 사항
- 포함 범위: 도입부(preamble, 작성 경위 설명)가 있다면 함께, 그리고 전체 조항(알려진 구조 기준 18개, 정확한 개수는 확보한 원문으로 재확인) 전부

## 저장 위치

```
data/nae/sources/baptist/nhc_1833.txt
```

- STEP1/STEP2에서 이미 생성된 디렉토리 구조 — 별도 생성 불필요
- 이 경로는 `scripts/ingest_nae_source.py`의 기본 inbox 경로(`data/nae/sources`) 하위와 일치

## 파일명 규칙

- `{source_id_slug}.txt` 형식 — 이번 대상은 `nhc_1833.txt` (NAE_SOURCE_REGISTRY_SCHEMA_v1.md `source_id: baptist-confession-001`의 축약형)
- 소문자, 언더스코어 구분, 공백/특수문자 금지 — `core/utils.py::make_safe_stem()`이 어차피 정규화하지만, 원본부터 규칙을 지키면 추적이 쉬움

## UTF-8 변환 방법

1. 텍스트 편집기(VS Code, TextEdit 등)로 파일을 열어 인코딩 확인
2. macOS 기준: `file --mime-encoding nhc_1833.txt` 명령으로 확인 (터미널)
3. UTF-8이 아니면 편집기의 "Save with Encoding → UTF-8"로 재저장 (BOM 없이)
4. 저장 후 재확인: `file --mime-encoding nhc_1833.txt` 결과가 `utf-8` 또는 `us-ascii`(UTF-8의 부분집합)인지 확인

## Provenance 기록 방법

STEP5_SOURCE_ACQUISITION_RECORD.md의 provenance 블록을 실측값으로 채운다:

```yaml
acquired_from: ""        # 예: "Wikisource" 또는 "CCEL" — 실제 사용한 저장소명
acquired_url: ""          # 실제 접속한 페이지 URL
acquired_date: "2026-07-31"
verification_method: "manual copy-paste + STEP5_SOURCE_MANUAL_VERIFY.md 4항목 대조"
verification_result: ""   # 예: "18개 조항 확인, 도입부 포함, 누락 없음"
checksum: ""               # 파일 확보 후 sha256sum 실행 결과
```

- `checksum` 계산: `shasum -a 256 data/nae/sources/baptist/nhc_1833.txt` (macOS 터미널)
- 이 provenance 기록은 STEP5_SOURCE_VERIFICATION.md(다음 반복에서 실측값으로 작성) 및 registry manifest에 반영될 예정

## 확보 후 다음 단계 (참고)

1. STEP5_SOURCE_MANUAL_VERIFY.md 4개 항목(heading/조항번호/누락텍스트/인코딩)으로 자체 검증
2. 검증 통과 시 STEP5_REGISTRY_TRANSITION.md 절차대로 상태 전환
3. `scripts/ingest_nae_source.py --dry-run` 실행은 별도 승인 필요 — 이 가이드 자체는 파일 준비까지만 다룸
