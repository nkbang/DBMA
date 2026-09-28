# CUE 교차검증 — Phase 3A (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P03A-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P03A-WO-Assembly-Manifest.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — WO 미이행, REWORK 필요**

## V1 환경 확인

```
$ git -C /Users/David/DBMA rev-parse --show-toplevel
/Users/David/DBMA
$ git -C /Users/David/DBMA branch --show-current
feat/peb-v0.1
$ git -C /Users/David/DBMA rev-parse HEAD
db677ac64b32830b6ae68f427c0d19f4389b0313
```
저장소/브랜치/HEAD가 GS-00 전제와 일치. 정상.

## V2 범위 확인

```
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml
 M core/candidate_generator.py
 M core/hybrid_candidate_pipeline.py
A  scripts/merge_nae_corpus.py
A  scripts/process_unprocessed_nae.py
A  scripts/test_default_corpus_query.py
?? core/evidence_assembly.py
?? tests/test_evidence_assembly.py
```
G0(비-GS 변경 6건)은 격리 유지됨. GS 변경은 허용 파일 2개와 정확히 일치. **범위는 정상.**

## V3/V4 — 핵심 결함: AssemblyManifest 부재

```
$ grep -n "class \|^def \|AssemblyManifest\|assemble_evidence_pool_with_manifest\|queries_for" \
    core/evidence_assembly.py
46:class QuerySpec:
63:def assemble_evidence_pool(
```

WO가 요구한 `AssemblyManifest` 클래스와 `assemble_evidence_pool_with_manifest()` 함수가
**둘 다 존재하지 않는다.** `core/evidence_assembly.py`는 WO 발급 전 CUE가 이미 읽었던
바로 그 파일(116줄, `assemble_evidence_pool` 단일 함수)과 **한 글자도 다르지 않다** —
WO 발급 이전에 존재하던 P3 baseline을 그대로 제출한 것이다.

`tests/test_evidence_assembly.py`의 테스트 16개 목록에도 manifest 관련 테스트가 없다
(`queries_for`, `AssemblyManifest`, `evidence_to_queries` 등 어떤 이름도 없음).

## GS-P03A Acceptance Criteria 대조

| AC | 요구사항 | 결과 |
|---|---|---|
| AC1 | `manifest.queries_for(id)`가 두 질의를 모두 보존 | **미구현** |
| AC2 | `by_query_order` 내부 순서가 원 순위와 동일 | **미구현**(manifest 자체가 없음) |
| AC3 | 빈 candidates도 `(spec, [])`로 등장 | **미구현** |
| AC4 | 기존 `assemble_evidence_pool()` 동작 불변 | 충족(변경 없음이므로 당연히 불변 — 별도 증명 아님) |
| AC5 | P1/P2 모듈 무수정 | 충족 |
| AC6 | manifest가 EvidencePool 내부 상태를 읽지 않음 | **미구현**(대상 없음) |

**6개 중 실질 충족 2개(AC4, AC5) — 둘 다 "손대지 않았다"는 소극적 충족이다.
WO의 핵심 목적(AC1~AC3, AC6)은 전혀 이행되지 않았다.**

또한 C1은 §7 "Remaining issues"에서 CUE가 원래 지적한 결함(F1, 질의 A→B 재삽입 시
by_query("A")가 사라짐)을 정확히 재진술하면서 "이는 결함이 아니라 알려진 설계
한계이며 Evidence model이나 EvidencePool을 수정해서 해결하지 않는다"고 적었다.
이는 WO를 오독한 것이다 — GS-P03A는 **EvidencePool을 수정하라고 요구한 적이 없다**
(오히려 명시적으로 금지). 요구한 것은 EvidencePool과 **별개인 새 manifest 구조**였다.
C1이 이 구분을 인지하지 못했거나, WO 본문을 실제로 반영하지 않고 이전 P3 보고를
재사용한 것으로 보인다.

## V5 독립 재실행 — 수치 불일치 발견

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_evidence_assembly.py -q
...
FAILED tests/test_evidence_assembly.py::TestPhase1Phase2Regression::test_evidence_model_tests_pass
FAILED tests/test_evidence_assembly.py::TestPhase1Phase2Regression::test_evidence_pool_tests_pass
2 failed, 14 passed in 0.32s
```

C1 보고: "16 passed, 0 failed". CUE 재실행: **14 passed, 2 failed.**

원인: `tests/test_evidence_assembly.py:512, 521`이 회귀 테스트를 `subprocess.run(["python",
"-m", "pytest", ...])`로 실행하는데, `"python"`이 이 환경(pyenv shim)에서
`pytest` 미설치 상태로 해석된다(GS-00 R9가 요구한 `~/envs/dbma311/bin/python`이 아님).
```
/Users/David/.pyenv/versions/3.11.14/bin/python: No module named pytest
```
이것은 날조가 아니라 **환경 의존적 테스트 설계 결함**으로 판단한다(C1의 환경에는
`python`이 dbma311로 연결돼 있었을 가능성). 그러나 GS-00 R9("`~/envs/dbma311/bin/python`
으로 실행한다")를 충족하지 못하는 subprocess 하드코딩이며, CUE 환경에서 재현되지
않는 PASS 수치를 보고서에 실었다는 점에서 V6 불일치로 기록한다.

## V6 수치 대조 요약

| 항목 | C1 보고 | CUE 재실행 |
|---|---|---|
| 전체 테스트 | 16 passed | 14 passed, 2 failed |
| AssemblyManifest 관련 테스트 | (보고에 없음) | 코드에도 없음 — 일치 |

## V7 적대적 프로브

WO 발급 시 CUE가 이미 실행한 재현 케이스를 다시 확인 — 결함이 그대로 남아 있음을 재확인.

```python
p = EvidencePool()
p.add(Evidence(evidence_id="E1", corpus_type="default", text="t"), build_query="A")
p.add(Evidence(evidence_id="E3", corpus_type="default", text="u"), build_query="C")
p.add(e1, build_query="B")
p.by_query("A")  # → [] (여전히 그대로, manifest가 없으므로 이 정보를 복구할 다른 경로도 없음)
```

## 결론

C1은 GS-P03A가 요구한 신규 산출물(AssemblyManifest)을 만들지 않고, WO 발급 이전
상태의 P3 코드와 보고서를 그대로 다시 제출했다. STOP 조건에 해당하는 사안은 아니다
(아키텍처 위반이나 금지 행위가 아니라 단순 미이행) — **HOLD로 REWORK를 재발급한다.**

부수 결함(subprocess 하드코딩으로 인한 회귀 테스트 비재현성)도 REWORK에 포함한다.

**recommendation: HOLD — GS-P03A REWORK 필요**
