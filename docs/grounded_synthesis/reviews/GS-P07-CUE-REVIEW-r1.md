# CUE 교차검증 — Phase 7 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P07-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P07-WO-Citation-Provenance.md`, ADR-036 B6
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — AC1 위반 1건 발견, REWORK 필요**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
2e3eaeea401e9e726ca4888c52e628567cef5703   (P6 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml / core/candidate_generator.py / core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py / process_unprocessed_nae.py / test_default_corpus_query.py  (G0)
?? core/grounded_citation.py
?? tests/test_grounded_citation.py
?? docs/grounded_synthesis/
```
G0 7연속 격리. GS 변경은 허용 파일 2개와 정확히 일치.

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_citation.py -q
..........................                                               [100%]
26 passed in 0.05s
```
C1 보고("26 passed")와 정확히 일치.

## V3/V4 — 코드 정독

`core/grounded_citation.py`(155줄) 전문을 읽었다. `import`는 P2/P4/P6 심볼만,
금지 목록 없음. `_check_span_in_text()`의 span 판정 기준(5자 미만 자동 실패,
case-sensitive exact substring)은 명시적이고 재현 가능하다 — CUE는 이 기준이
다소 관대하다고 보지만(5자는 매우 짧음, false positive 위험) STOP 대상은
아니다. `check_citation_provenance()`가 WO AC1을 어떻게 구현했는지가 핵심:

```python
id_exists = eid in included_ids
ev = evidence_pool.get(eid)
if ev is not None:
    span_found = _check_span_in_text(claim.text, ev.text)
else:
    span_found = False
provenance_ok = ev.has_provenance if ev is not None else False
```

**`id_exists`와 `span_found`/`provenance_ok`가 서로 독립적으로 계산된다.**
`ev is not None` 여부로만 후자 둘이 결정되고, `id_exists`가 `False`인 경우를
별도로 단락(short-circuit)하지 않는다.

## V7 — 적대적 프로브: AC1이 명시한 단락 규칙 위반 재현

WO AC1 원문: "evidence_id가 `included_evidence_ids`에 없으면 `id_exists=False`이고,
**이 경우 `span_found_in_text`, `provenance_traceable`도 자동으로 False**
(존재하지 않는 근거의 하위 검사를 수행하지 않음)."

`EvidencePool`은 검색된 모든 근거를 담고 있고, `SynthesisInput.included_evidence_ids`는
그중 `max_evidence` 예산 내로 절단된 부분집합이다(P4). 즉 **Pool에는 있지만
`included`에는 없는(=`excluded`) evidence_id가 정상적으로 존재한다.** 이 경우를
재현:

```python
pool.add(Evidence(evidence_id="e_excluded", text="This is a real evidence text ...",
                   source_file="real_source.pdf",
                   provenance=EvidenceProvenance(source_file="real_source.pdf")))

si = SynthesisInput(included_evidence_ids=["e1"], excluded_evidence_ids=["e_excluded"], ...)
claim = Claim(claim_id="c1", text="This is a real evidence text ...",
              evidence_ids=["e_excluded"], valid=False)

report = check_citation_provenance(ga, si, pool)
r = report.results[0]
```

결과:
```
id_exists: False
span_found_in_text: True     ← WO AC1 위반 (False여야 함)
provenance_traceable: True   ← WO AC1 위반 (False여야 함)
```

**id_exists=False인데 span_found_in_text와 provenance_traceable이 둘 다 True로
나온다.** C1의 테스트(`test_ac1_id_exists_false`, `test_ac1_multiple_eids_mixed`)는
전부 "Pool에도 없는" 완전히 가짜인 id(`e999`)만으로 `id_exists=False` 케이스를
만들었다 — 그래서 `ev is None`이 되어 우연히 span/provenance도 False가 나왔을
뿐, **"Pool에는 실재하지만 이번 답변엔 전달 안 된 근거"라는 훨씬 더 현실적인
케이스는 테스트되지 않았다.**

### 왜 이게 중요한가

이 결함을 방치하면, LLM이 실제로 컨텍스트에 주어지지 않은(예산 초과로 잘린)
근거를 마치 인용한 것처럼 주장해도, 검증 보고서에 "id_exists=False"만 조용히
찍히고 "span_found_in_text=True, provenance_traceable=True"가 함께 표시된다.
이건 사람이 훑어볼 때 citation이 "거의 맞다"는 오해를 준다 — WO가 단락 규칙을
명시한 이유가 정확히 이것을 막기 위함이다. STOP 조건은 아니다(국소 코드 수정으로
해결 가능).

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 id_exists=False → 하위 검사 자동 False | **위반** (독립 계산 확인, 재현됨) |
| AC2 span_found_in_text 정확 판정 | 충족(단, 5자 최소 길이는 관대한 편 — 비차단 관찰) |
| AC3 provenance_traceable = Evidence.has_provenance | 충족 |
| AC4 의미적 판정 없음 | 충족 |
| AC5 valid=False claim도 검사에서 안 빠짐 | 코드상 `if not claim.evidence_ids: continue`만 있고 valid 필드로 건너뛰지 않음 — 충족 |

## 결론

AC1 하나만 위반이지만, 이 Phase의 존재 이유(사후 검증의 신뢰성)와 직결되는
결함이라 REWORK 없이 넘어갈 수 없다. 나머지 구현·테스트 품질은 양호하다.

**recommendation: HOLD — GS-P07 REWORK 필요.**
