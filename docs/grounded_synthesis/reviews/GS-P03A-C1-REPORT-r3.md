# C1 보고 원문 — Phase 3A REWORK Report (r3, 2026-09-27)

> V0(보고 원문 보존). 요약 형태로 전달받은 내용을 그대로 옮긴 것이다. 전체 보고서는
> `/Users/David/DBMA/docs/grounded_synthesis/reviews/GS-P03A-C1-REPORT-r3.md`에
> C1이 직접 작성.

---

## 완료 요약

### r3 수정 내용

**`core/evidence_assembly.py`** — `_extract_evidence_ids()` fix:
- `c.tsu_id` 직접 반환 -> `RankedCandidateEvidenceAdapter._resolve_evidence_id(c.tsu_id or "", c)` 재사용
- import 추가: `from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter`

**`tests/test_evidence_assembly.py`** — AC7 테스트 추가:
- `TestAC7TSUMissingManifestKeyMatch::test_manifest_key_matches_pool_evidence_id_when_tsu_id_missing`
- tsu_id="" candidate에서 manifest key가 pool의 실제 evidence_id와 정확히 일치하는지 검증

### 검증 결과

- **20/20 테스트 PASS** (기존 19 + AC7)
- Phase 1 regression: 84/84 PASS
- Phase 2 regression: 84/84 PASS
- 무변경 파일: 0개 변경 (tsu_adapter.py 포함)
- retrieval 호출: NONE

### 보고서

`docs/grounded_synthesis/reviews/GS-P03A-C1-REPORT-r3.md` 작성 완료.
