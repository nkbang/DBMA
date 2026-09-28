# CUE 교차검증 — Phase 6 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P06-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P06-WO-Grounded-Answer.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9
- 참고: 이 Phase의 첫 전달(r0)은 C1이 P5 재검증 보고를 잘못 제출한 사고였음
  (`GS-P06-CUE-REVIEW-r0-wrong-target.md`). 이번 r1은 재지시 후 정상 제출.

## 판정: **GREEN — Phase 6 완료. HQ 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
20bf6dddf363cde0ca4bb071c369e76004781bfd   (P5 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml / core/candidate_generator.py / core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py / process_unprocessed_nae.py / test_default_corpus_query.py  (G0)
?? core/grounded_answer.py
?? tests/test_grounded_answer.py
?? docs/grounded_synthesis/
$ ls -la core/grounded_answer.py tests/test_grounded_answer.py
(존재 확인됨 — r0과 달리 이번엔 실제 파일 생성)
```
G0 6연속 격리 확인. GS 변경은 허용 파일 2개와 정확히 일치.

## V3/V4 — 코드 정독

`core/grounded_answer.py`(136줄) 전문을 읽었다. `GroundedAnswer`는 ADR-036 B5/B8
그대로. `assemble_grounded_answer()`의 상태 판정 순서:

1. `included_evidence_ids == []` → insufficient/no_evidence
2. `conflicting=True` → conflicting_evidence(호출자 명시 플래그만, 자동 판정 없음)
3. 전체 claim이 invalid → insufficient/no_valid_claim
4. valid claim 존재 → grounded(invalid claim text는 배제, 객체 자체는 보존)
5. (claims 빈 리스트 등) 폴백 → insufficient/no_claims

이 순서에서 **"evidence 자체가 없음"이 "conflicting 플래그"보다 우선**한다는
설계 판단이 코드에 있다(WO가 명시하지 않은 부분) — CUE가 V7에서 이 우선순위를
직접 테스트해 타당함을 확인(아래).

`import`에 `core.generation` 없음, `_GROUNDING_DIRECTIVE`/`_DENOMINATION_DIRECTIVE`
접근 없음(주석 언급뿐). 자동 충돌 탐지(텍스트 유사도, 어휘 비교 등) 코드 없음 —
`conflicting` 플래그 분기만 존재.

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_answer.py -q
.................                                                        [100%]
17 passed in 0.07s
```
C1 보고("17/17 PASSED")와 정확히 일치.

## V6 — 수치 대조

| 항목 | C1 보고 | CUE 재실행 | 일치 |
|---|---|---|---|
| 테스트 통과 | 17/17 | 17/17 | 일치 |
| AC1~AC6 충족 | 6/6 | 6/6(코드+CUE 통합 재현) | 일치 |

## V7 — 적대적 프로브 (실제 P3A→P4→P5→P6 전체 파이프라인 통합)

C1의 테스트는 손으로 만든 `Claim`/`SynthesisInput`만 사용한다. CUE는
`assemble_evidence_pool_with_manifest()` → `build_synthesis_input()` →
`bind_claims()` → `assemble_grounded_answer()`를 실제로 연쇄 호출해서 5가지
케이스를 확인했다:

```
Case empty pool:        insufficient_evidence / no_evidence
Case all-invalid claim:  insufficient_evidence / no_valid_claim (invalid claim 보존 확인)
Case mixed valid+invalid: grounded, invalid claim text 배제·객체는 claims에 남음
Case conflicting(evidence 있음): conflicting_evidence, 두 견해 모두 evidence_id와 병기
Case conflicting=True + 근거 0건(경계): insufficient_evidence(no_evidence)로 처리
                                         — "근거 없음"이 "충돌 표시"보다 우선하는 것이 맞다
                                           (근거가 없으면애초에 비교할 두 입장 자체가 없음)
```

5가지 전부 기대대로 동작. 특히 마지막 경계 케이스는 WO가 명시하지 않았던
우선순위 판단인데, C1의 구현 순서가 논리적으로 타당하다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 빈 evidence → insufficient/no_evidence | 충족(+CUE 파이프라인 재현) |
| AC2 전체 invalid → insufficient/no_valid_claim, invalid claim 보존 | 충족(+CUE 재현) |
| AC3 valid 존재 → grounded, invalid text 배제 | 충족(+CUE 재현) |
| AC4 insufficient text에 금지 표현 없음 | 충족 |
| AC5 자동 충돌 탐지 없음, 명시 플래그만 | 충족(grep + CUE 우선순위 경계 테스트) |
| AC6 core/generation.py 함수 미호출 | 충족(grep 0건) |

6개 AC 전부 충족. STOP 조건 해당 없음.

## 결론

r0의 잘못된 제출(P5 재검증 보고 오전달) 이후, 재지시된 r1은 실제로
`core/grounded_answer.py`를 구현했고 검증 결과 GREEN이다. WO가 명시하지 않은
우선순위 경계(빈 근거 vs conflicting 플래그)도 CUE가 직접 확인했고 타당했다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `core/grounded_answer.py` +
`tests/test_grounded_answer.py`를 경로 지정 커밋으로 확정하고, GS-P07
(Citation/Provenance)을 발급한다.**
