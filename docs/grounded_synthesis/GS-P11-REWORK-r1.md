# REWORK WORK ORDER — Phase 11 (r2)

- 사유: 항목 4·6의 검증 명령이 `git diff 0d265afc HEAD`인데, 현재 HEAD가
  정확히 `0d265afc` 자신이다 — 자기 자신과 비교하는 동어반복이라 무엇이
  들어있든 항상 빈 출력이 나온다. 상세: `docs/grounded_synthesis/reviews/GS-P11-CUE-REVIEW-r1.md`
- 결론("0", "해당 없음")은 CUE가 재확인한 바 실제로 맞다 — 명령만 고치면 된다.
  전체 보고서를 다시 쓸 필요 없이 항목 4·6 두 곳만 교체해라.

## 항목 4 — Corpus regeneration 재검증

WO가 실제로 요구한 것은 "GS 관련 스크립트/테스트가 이 두 스크립트를
**호출한 이력**이 없음"이다. git diff가 아니라 grep으로 확인해라:

```bash
cd /Users/David/DBMA && grep -rn "merge_nae_corpus\|process_unprocessed_nae" \
    core/grounded_*.py core/evidence_*.py tests/test_grounded_*.py \
    tests/test_evidence_*.py scripts/grounded_synthesis_integration_demo.py \
    || echo "NO_MATCH"
```
(CUE가 이미 실행해서 `NO_MATCH` 확인함 — 그대로 실행해서 보고서에 옮기면 된다.)

보고서에 다음을 덧붙여라: `scripts/merge_nae_corpus.py`,
`scripts/process_unprocessed_nae.py`는 G0(비-GS, staged 상태)의 일부이며
Grounded Synthesis 작업과 무관하다는 것, 그리고 이 두 파일 자체가
`git diff --cached --stat -- scripts/merge_nae_corpus.py
scripts/process_unprocessed_nae.py`로 여전히 staged 상태임을(GS가 이걸
커밋하지 않았다는 의미) 명시해라.

## 항목 6 — No new retrieval path 재검증

비교 기준을 `0d265afc`(P10 자신, HEAD와 동일)가 아니라 `1c0117a7`(P1 시작
직전, GS-00과 P10이 이미 확정한 진짜 pre-GS 기준)로 바꿔라:

```bash
cd /Users/David/DBMA && git diff --stat 1c0117a7..HEAD -- core/retrieval.py \
    core/hybrid_candidate_pipeline.py core/candidate_generator.py
```
(CUE가 이미 실행해서 0줄 변경 확인함 — 그대로 실행해서 보고서에 옮기면 된다.
이 결과는 GS-P10-REGRESSION-REPORT.md에서 이미 검증된 사실이므로, 그 보고서를
근거로 인용해도 된다.)

## 일반 지시

앞으로 "GS가 무언가를 바꾸지 않았다"를 git diff로 증명할 때는, 비교 대상이
**항상 GS 시작 이전 커밋(`1c0117a7`)이어야 한다** — 현재 작업 중인 Phase의
직전 커밋(예: `0d265afc`)과 HEAD를 비교하면, 그 Phase 자체가 아직 새 커밋을
만들지 않은 상태에서는 자기 자신과 비교하게 되어 의미가 없어진다.

## 보고

이전과 동일 양식(§6 "종합 판정" 표와 §Acceptance Criteria는 그대로 두고,
항목 4·6 섹션만 교체). 파일명은 그대로 `GS-P11-PRODUCTION-SAFETY-REPORT.md`를
덮어써도 된다(별도 리비전 파일 불필요 — 이 Phase의 유일한 산출물이므로).
마지막 줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.
