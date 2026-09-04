# STEP5-C Report — Human Source Acquisition Package

작성일: 2026-07-31

## 판정

**WAITING_FOR_SOURCE**

## 근거

`data/nae/sources/baptist/` 디렉토리를 재확인한 결과 여전히 비어 있음 — 원문 파일 미확보. STEP5-C의 목표는 "사람이 확보한 원문을 즉시 투입할 수 있도록 준비"였으며, 이 준비(가이드/검증계획/전환절차)는 완료되었으나 **원문 자체는 여전히 존재하지 않음**. `READY`가 아니라 사람의 다음 행동(원문 확보·전달)을 기다리는 상태이므로 `WAITING_FOR_SOURCE`로 판정.

## 작성 파일

- [STEP5_HUMAN_ACQUISITION_GUIDE.md](STEP5_HUMAN_ACQUISITION_GUIDE.md) — 필요 파일/저장 위치/파일명 규칙/UTF-8 변환/provenance 기록 방법
- [STEP5_SOURCE_VALIDATION_SCRIPT.md](STEP5_SOURCE_VALIDATION_SCRIPT.md) — encoding/empty section/article numbering/checksum 4개 자동 검증 계획 (스크립트 미구현, 계획만)
- [STEP5_REGISTRY_TRANSITION.md](STEP5_REGISTRY_TRANSITION.md) — PREPARED→ACQUIRED→VERIFIED→INGESTED 각 전환의 절차·완료기준·역행 원칙
- 본 보고서

## 금지 사항 준수 확인

- 원문 생성: 미실행
- 원문 추정 작성: 미실행 — STEP5-B에서 WebFetch 요약 결과를 원문으로 채택하지 않았던 원칙을 계속 유지, 이번 STEP5-C에서도 어떠한 형태로도 원문 텍스트를 스스로 작성하거나 추정하지 않음
- 요약본 사용: 미실행
- TSU 생성: 미실행
- Embedding: 미실행
- Vector DB 변경: 미실행
- Commit: 미실행

## 다음 단계

- 사람(HQ 또는 담당자)이 STEP5_HUMAN_ACQUISITION_GUIDE.md에 따라 원문을 확보해 `data/nae/sources/baptist/nhc_1833.txt`에 전달
- 전달 후 STEP5_REGISTRY_TRANSITION.md의 `PREPARED → ACQUIRED` 절차부터 재개
- `scripts/validate_nae_source.py`(STEP5_SOURCE_VALIDATION_SCRIPT.md 계획) 실제 구현은 별도 승인 필요 — 원문 확보와 별개로 언제든 진행 가능한 독립 작업
