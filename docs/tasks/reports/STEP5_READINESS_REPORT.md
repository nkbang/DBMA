# STEP5 Readiness Report

작성일: 2026-07-31
갱신일: 2026-07-31 (STEP5-B-REVIEW, Verbatim 확보 실패 및 도구 한계 반영)

## 판정

**NOT READY** (유지 — 사유 갱신)

## 근거 (갱신)

| 선행 조건 | 상태 | STEP5-B-REVIEW 반영 |
|---|---|---|
| 원문 확보(다운로드) 승인 | 승인됨(STEP5-B) — 그러나 실행이 도구 한계로 실패 | **신규**: `WebFetch`가 verbatim 텍스트를 반환하지 않고 항상 요약하는 구조적 한계 확인 (STEP5_SOURCE_COMPARISON.md) |
| 원문 확보 실행 | **실패** | 3개 URL(Wikisource 페이지/raw export, Reformed Reader) 시도 전부 요약본만 반환 — 저장하지 않음(원문 아닌 것을 원문으로 기록하지 않기 위함) |
| STEP4_PD_VERIFICATION.md 4단계 검증 | 미실행 (원문 없이 불가) | 변경 없음 |
| Registry manifest 실제 작성 | 미실행 | 변경 없음 — `STEP5_SOURCE_REGISTRY_ENTRY.md`는 여전히 `PREPARED` |
| **(신규) 확보 방식 자체의 재설계** | 완료 | STEP5_IMPORT_FORMAT_DECISION.md(TXT 채택) + STEP5_SOURCE_MANUAL_VERIFY.md(사람 개입 확보 절차)로 대안 경로 확정 |

STEP4-D 코드 인프라(`scripts/ingest_nae_source.py`, `core/tsu_builder.py`)는 여전히 준비 완료 상태 — 변경 없음. 이번 갱신의 핵심은 "원문 확보를 자동화 도구(WebFetch)로 할 수 없다"는 사실이 확인되었다는 점.

## 준비 완료된 것 (문서/계획 단계, 누적)

- 확보 계획: [STEP5_SOURCE_ACQUISITION_RECORD.md](STEP5_SOURCE_ACQUISITION_RECORD.md)
- 최종 등록 템플릿: [STEP5_SOURCE_REGISTRY_ENTRY.md](STEP5_SOURCE_REGISTRY_ENTRY.md) — 상태 `PREPARED` (변경 없음, `ACQUIRED`로 전환 못함)
- 실행 체크리스트: [STEP5_PILOT_CHECKLIST.md](STEP5_PILOT_CHECKLIST.md)
- 저장소 비교: [STEP5_SOURCE_COMPARISON.md](STEP5_SOURCE_COMPARISON.md) — CCEL/Internet Archive/Wikisource 등 비교, 결론은 "저장소 문제가 아니라 도구 문제"
- 형식 결정: [STEP5_IMPORT_FORMAT_DECISION.md](STEP5_IMPORT_FORMAT_DECISION.md) — TXT 채택
- 수동 검증 절차: [STEP5_SOURCE_MANUAL_VERIFY.md](STEP5_SOURCE_MANUAL_VERIFY.md) — 4개 항목(heading/numbering/missing text/encoding), 사람 개입 확보 절차 권장
- 코드 인프라: `scripts/ingest_nae_source.py` + `core/tsu_builder.py`의 `nae_metadata` 블록 (커밋 `d32b716`, 46개 테스트 통과 확인됨)

## READY 전환을 위한 다음 단계 (경로 변경)

1. **(변경)** 자동 도구(WebFetch) 기반 확보는 배제 — 사람(HQ 또는 담당자)이 직접 CCEL/Wikisource/Internet Archive 중 한 곳에서 원문을 복사/다운로드하여 전달
2. 전달된 텍스트를 STEP5_SOURCE_MANUAL_VERIFY.md 4개 항목으로 검증
3. 검증 통과 시 `data/nae/sources/baptist/nhc_1833.txt`로 저장, STEP5_SOURCE_VERIFICATION.md 작성(실측값)
4. Registry 상태를 `PREPARED → ACQUIRED → VERIFIED`로 갱신
5. 이후 STEP5_PILOT_CHECKLIST.md 2단계(Registry Entry)부터 재개

## 금지 사항 준수 확인

- 원문 없는 ingestion: 미실행
- TSU 생성: 미실행
- Embedding: 미실행
- Vector DB 변경: 미실행
- Commit: 미실행
