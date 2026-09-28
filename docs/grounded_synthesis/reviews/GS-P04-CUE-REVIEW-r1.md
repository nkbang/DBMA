# CUE 교차검증 — Phase 4 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P04-C1-REPORT-r1.md`(C1이 `/Users/David/DBMA`에 직접 작성, 이 파일로 사본 보존)
- 원본 WO: `docs/grounded_synthesis/GS-P04-WO-Synthesis-Input-Boundary.md`, ADR-036 B3/B8
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 4 완료. HQ 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
14fccb5478eca71ec756f1b69869ec65a902d2f0   (P3+P3A 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml / core/candidate_generator.py / core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py / process_unprocessed_nae.py / test_default_corpus_query.py  (G0)
?? core/grounded_synthesis_input.py
?? tests/test_grounded_synthesis_input.py
?? docs/grounded_synthesis/
```
G0 4연속 격리 확인. GS 변경은 허용 파일 2개와 정확히 일치.

## V3/V4 — 코드 정독

`core/grounded_synthesis_input.py`(150줄) 전문을 읽었다. `SynthesisInput`은 ADR-036 B8
시그니처와 필드명·타입이 정확히 일치. `build_synthesis_input()`의 라운드로빈 절단
로직을 손으로 트레이스:

- `remaining = [[e1,e2,e3], [e4,e5]]`, `max_evidence=3`일 때:
  1라운드 q0→e1, q1→e4 (len=2) / 2라운드 q0→e2(len=3) → q1 진입 시
  `len(included)>=max_evidence` True로 break → **`[e1, e4, e2]`**, WO AC4 예시와 정확히 일치.
- 중복 evidence_id는 `seen` set으로 처음 등장한 질의 순서만 유지, 두 번째부터는
  included·excluded 어디에도 추가되지 않고 조용히 스킵됨(수량 손실 없음).
- `prompt_text`는 `included` 순서대로만 구성 — `excluded` 텍스트는 구조적으로 섞일 수 없음.
- 출처 라벨: `ev.source_file` → `ev.document_title` → `"미상"` 순. (WO 원문은
  `Evidence.provenance.source_file`을 언급했으나, `RankedCandidateEvidenceAdapter.adapt()`가
  top-level `source_file`과 `provenance.source_file`에 항상 같은 값을 넣으므로
  — `core/evidence_adapters/tsu_adapter.py:245-249` — 기능적으로 동일하다. 결함 아님,
  참고 사항으로만 기록.)

`import` 목록에 금지 대상 없음(ADR-036 B9). 점수 필드(`final_score` 등) 접근 0건.

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_grounded_synthesis_input.py -v --tb=short
...
============================== 16 passed in 0.06s ==============================
```
C1 보고("16 passed")와 정확히 일치. 16개 테스트 이름을 AC1~AC9에 전부 대응시켜
확인 — 커버리지 누락 없음.

## V6 — 수치 대조

| 항목 | C1 보고 | CUE 재실행 | 일치 |
|---|---|---|---|
| 테스트 통과 | 16/16 | 16/16 | 일치 |
| AC1~AC9 충족 | 9/9 | 9/9(코드+독립 재현) | 일치 |
| 기존 파일 수정 | 0건 | 0건(git status 확인) | 일치 |

## V7 — 적대적 프로브 (WO 테스트에 없던 시나리오, 실제 P3A 파이프라인과 통합)

C1의 테스트는 손으로 만든 `AssemblyManifest`만 사용한다. CUE는 실제
`assemble_evidence_pool_with_manifest()`(P3A)로 만든 pool+manifest를 P4에
그대로 연결해서 end-to-end로 확인했다 — 특히 P3A가 고쳤던 "tsu_id 결측" 케이스와
"동일 evidence_id를 여러 질의가 찾는" 케이스를 함께 넣었다:

```python
c1a = RankedCandidate(tsu_id="e1", content="A1 text", final_score=0.9)
c1b = RankedCandidate(tsu_id="e2", content="A2 text", final_score=0.8)
c2a = RankedCandidate(tsu_id="e1", content="B1 text (dup of e1)", final_score=0.7)  # 중복
c2b = RankedCandidate(tsu_id="", content="B2 text (tsu_id missing)",
                       metadata={"document_id":"d9","chunk_id":"c9","source_file":"f9.pdf"})

pool, manifest = assemble_evidence_pool_with_manifest([
    (QuerySpec(query="A"), [c1a, c1b]), (QuerySpec(query="B"), [c2a, c2b]),
])
si = build_synthesis_input(pool, manifest, max_evidence=10)
```
결과:
```
included: ['e1', 'e2', 'evid:baa4940d2f790004']
excluded: []
union(included,excluded) == pool_ids: True
중복 없음: True
```
tsu_id 결측 evidence(`evid:baa4940d2f790004`)가 manifest·pool·synthesis input
전 구간에서 identity가 일관되게 유지됨 — P3A REWORK가 P4까지 안전하게 전달됨을 확인.

절단 케이스(`max_evidence=1`)와 `max_evidence=0`(ValueError) 별도 재현도 통과.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 included∪excluded = pool 전체, 중복 없음 | 충족(코드+CUE 통합 재현) |
| AC2 pool ≤ max → truncated=False, excluded=[] | 충족 |
| AC3 pool > max → truncated=True, len(included)=max | 충족 |
| AC4 라운드로빈 정확한 순서(WO 예시 그대로) | 충족 |
| AC5 중복 evidence_id 1회만 등장 | 충족(+CUE 통합 재현) |
| AC6 prompt_text에 included만, excluded 없음 | 충족 |
| AC7 source_file 없으면 "[출처: 미상]" | 충족(참고: top-level 필드 사용, provenance와 항상 동치) |
| AC8 점수 접근 코드 없음 | 충족(grep 0건, CUE 별도 grep 재확인) |
| AC9 금지 import 없음 | 충족 |

9개 AC 전부 충족. STOP 조건 해당 없음.

## 결론

Phase 4는 첫 제출에서 GREEN. WO의 예시 케이스를 정확히 재현했고, CUE의 독립
통합 테스트(P3A 실제 파이프라인 + tsu_id 결측 + 중복 evidence_id 동시 결합)에서도
결함이 발견되지 않았다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `core/grounded_synthesis_input.py` +
`tests/test_grounded_synthesis_input.py`를 경로 지정 커밋으로 확정하고, GS-P05
(Claim–Evidence Binding)를 발급한다.**
