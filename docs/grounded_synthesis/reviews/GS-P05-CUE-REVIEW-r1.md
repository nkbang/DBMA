# CUE 교차검증 — Phase 5 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P05-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P05-WO-Claim-Evidence-Binding.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 5 완료. HQ 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
9eae516781e0e3610cdd8715aa502d6cef21365a   (P4 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml / core/candidate_generator.py / core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py / process_unprocessed_nae.py / test_default_corpus_query.py  (G0)
?? core/grounded_claims.py
?? tests/test_grounded_claims.py
?? docs/grounded_synthesis/
```
G0 5연속 격리 확인. GS 변경은 허용 파일 2개와 정확히 일치.

## V3/V4 — 코드 정독

`core/grounded_claims.py`(128줄) 전문을 읽었다. `Claim`, `ClaimExtractor`,
`bind_claims()`, `StubClaimExtractor`가 WO 설계 그대로 구현됨.

- `bind_claims()`: `evidence_ids == []` → `valid=False`(AC3), 그 외에는
  `all(eid in included_set for eid in cited_eids)`로 부분집합 여부 판정(AC1/AC2).
  유효하지 않은 Claim도 리스트에서 제외되지 않음 — 정보 손실 없음(ADR-036 B4 그대로).
- `import` 목록에 `core.claim_guard` 없음, `prompt_text`/`Evidence.text` 접근 코드 없음
  (주석에서만 언급). grep 검사(AC5/AC6)도 tautology 없이 실제 소스 라인을 검사함.
- `StubClaimExtractor`는 네트워크·LLM 호출 없이 `claims_map` 딕셔너리 매칭만 수행 —
  결정적(R8 충족).

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_claims.py -q
....................                                                     [100%]
20 passed in 0.06s
```
C1 보고("20 passed")와 정확히 일치.

## V6 — 수치 대조

| 항목 | C1 보고 | CUE 재실행 | 일치 |
|---|---|---|---|
| 테스트 통과 | 20/20 | 20/20 | 일치 |
| AC1~AC6 충족 | 6/6 | 6/6(코드+CUE 통합 재현) | 일치 |

## V7 — 적대적 프로브 (실제 P3A+P4 파이프라인과 통합, WO 테스트에 없던 시나리오)

C1의 테스트는 손으로 만든 `SynthesisInput`만 사용한다. CUE는 실제
`assemble_evidence_pool_with_manifest()` → `build_synthesis_input()`으로 만든
진짜 `SynthesisInput`을 `bind_claims()`에 연결해서 확인했다. 특히 **"evidence가
Pool에는 존재하지만 예산 초과로 잘려나간(excluded) 경우"**를 인용하는 Claim이
정확히 무효 처리되는지가 핵심이었다(WO에는 명시적 테스트가 없던 경계 사례):

```python
si2 = build_synthesis_input(pool, manifest, max_evidence=1)  # e1만 included, e2는 excluded
claims2 = bind_claims([("cites excluded e2", ["e2"])], si2)
# claims2[0].valid == False   ← e2는 실제 Pool에 존재하지만 이 SynthesisInput
#                                에서는 LLM에 주어지지 않았으므로 무효 처리가 맞다
```

결과: `valid=False`로 정확히 처리됨 — "존재하는 근거"와 "이번에 실제로 LLM에
전달된 근거"를 혼동하지 않는다(ADR-036 B2/B3의 경계를 P5가 올바르게 존중함).

추가로 날조 evidence_id 혼입, 빈 evidence_ids, `StubClaimExtractor` 5회 반복
결정성도 재확인 — 전부 정상.

## Remaining issues 검토 (C1 §8)

- StubClaimExtractor 단순 패턴 매칭: P9에서 교체 대상, 이번 Phase 범위 밖. 문제 없음.
- G0 격리: 기존과 동일, 문제 없음.
- **Claim ID 충돌(여러 `bind_claims()` 호출 간 `claim_{idx:03d}` 재사용 가능성)**:
  타당한 지적이다. 현재 WO(P5)는 단일 호출 내 고유성만 요구했으므로 AC 위반은
  아니다. 다만 P6/P9에서 여러 번의 synthesis 결과를 하나의 GroundedAnswer로
  합칠 때 이 문제가 실제로 드러날 수 있다 — **P6 WO에 이 사항을 전달 필요**
  (전역 고유 ID 생성 방식은 P6 설계 시점에 CUE가 판단).

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 evidence_ids ⊆ included → valid=True | 충족 |
| AC2 evidence_ids 중 하나라도 미포함 → valid=False, Claim 유지 | 충족(+CUE의 truncated-citation 케이스로 강화 검증) |
| AC3 evidence_ids=[] → valid=False | 충족 |
| AC4 stub 결정적(3회 이상 반복 동일) | 충족(+CUE 5회 반복 재확인) |
| AC5 claim_guard.py import 없음 | 충족(grep 0건) |
| AC6 prompt_text/Evidence.text 미접근 | 충족(grep 0건 + CUE 구조적 재확인) |

6개 AC 전부 충족. STOP 조건 해당 없음.

## 결론

Phase 5는 첫 제출에서 GREEN. WO가 요구한 것보다 엄격한 경계 사례(예산 초과로
잘린 근거를 인용하는 경우)까지 CUE가 직접 확인했고 정상 처리됨을 확인했다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `core/grounded_claims.py` +
`tests/test_grounded_claims.py`를 경로 지정 커밋으로 확정하고, GS-P06
(Grounded Answer)을 발급한다. P6 WO에 "Claim ID 전역 고유성" 이슈를 함께
전달할 것.**
