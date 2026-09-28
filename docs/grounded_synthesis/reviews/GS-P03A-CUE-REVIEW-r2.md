# CUE 교차검증 — Phase 3A (r2)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P03A-C1-REPORT-r2.md`
- 원본 WO / REWORK: `GS-P03A-WO-Assembly-Manifest.md`, `GS-P03A-REWORK-r1.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — 진전 있으나 미해결 결함 1건, REWORK r3 필요**

r1 대비 크게 개선됐다. `AssemblyManifest`가 실제로 구현됐고, r1에서 보인 "요구사항
미이행" 문제는 해소됐다. 다만 구현 자체에서 **새로운 정확성 결함**을 CUE 적대적
프로브(V7)로 발견했다.

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
db677ac64b32830b6ae68f427c0d19f4389b0313   (r1과 동일, 정상)
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml                        (G0, 격리 유지)
 M core/candidate_generator.py        (G0, 격리 유지)
 M core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py        (G0)
A  scripts/process_unprocessed_nae.py (G0)
A  scripts/test_default_corpus_query.py (G0)
?? core/evidence_assembly.py
?? docs/grounded_synthesis/
?? tests/test_evidence_assembly.py
```
G0 6건은 여전히 격리됨. GS 변경 범위는 허용 파일과 일치. **정상.**

## V3/V4 — 코드 정독

`AssemblyManifest`, `_build_manifest()`, `_extract_evidence_ids()`,
`assemble_evidence_pool_with_manifest()`가 모두 REWORK r1의 설계대로 구현됨.
`assemble_evidence_pool()`은 새 함수를 감싸는 얇은 wrapper로 리팩터링되어 코드
중복이 없다. AC6 요구(EvidencePool 내부 상태 미접근)도 grep으로 확인: `_evidences`,
`_index` 접근 없음.

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_evidence_assembly.py -q
...................                                                      [100%]
19 passed in 0.76s
```
C1 보고("19 passed, 0 failed")와 **정확히 일치.** r1에서 있었던 subprocess 재현성
문제(`"python"` 하드코딩)도 `sys.executable`로 교체되어 해소됨(V6에서 재확인).

## V6 — 수치 대조

| 항목 | C1 보고 | CUE 재실행 | 일치 |
|---|---|---|---|
| 전체 테스트 | 19 passed | 19 passed | 일치 |
| AC1/AC2/AC3 | PASS | PASS(코드 확인) | 일치 |

## AC 대조표

| AC | 요구사항 | 결과 |
|---|---|---|
| AC1 | 질의 A→B가 같은 evidence_id를 찾으면 `queries_for(id) == ["A","B"]` | **충족** (`test_manifest_queries_for_duplicate_evidence`, tsu_id="E1" 고정값으로 검증) |
| AC2 | `by_query_order` 내부 순서 = 원 순위 순서 | 충족(코드·테스트 확인) |
| AC3 | 빈 candidates → `(spec, [])` 등장 | 충족 |
| AC4 | 기존 `assemble_evidence_pool()` 동작 불변 | 충족 (내부적으로 `with_manifest()`를 호출하는 wrapper로 재작성됐으나 반환값 동일, 기존 10개 테스트 PASS 유지) |
| AC5 | P1/P2 모듈 무수정 | 충족 |
| AC6 | manifest가 EvidencePool 내부 상태를 읽지 않음 | 충족(입력 `query_candidates`만 사용) |

**AC1~AC6 전부 형식적으로 충족.** 그러나 아래 V7에서 이 충족이 **불완전한 입력
범위(고정된 tsu_id 값)에서만 검증됐다는 것**을 발견했다.

## V7 — 적대적 프로브: tsu_id 없는 candidate에서 manifest가 실제 evidence_id와 어긋남

`_extract_evidence_ids()`는 `c.tsu_id`를 그대로 evidence_id로 사용한다:

```python
def _extract_evidence_ids(candidates: list[RankedCandidate]) -> list[str]:
    return [c.tsu_id for c in candidates]
```

그러나 실제 Pool에 저장되는 evidence_id는 `RankedCandidateEvidenceAdapter._resolve_evidence_id()`가
결정한다 — `tsu_id`가 비어 있으면 `source_file+document_id+chunk_id`의 해시,
그다음 `document_id`, `chunk_id` 순으로 폴백한다(P1 승인 시점부터 존재하는 로직,
`core/evidence_adapters/tsu_adapter.py:113-145`, P1 승인 메모에도 "tsu_id 없을 때
sha256 fallback identity"로 기록된 알려진 경로).

CUE가 이 폴백 경로로 재현:
```python
c = RankedCandidate(tsu_id="", content="...",
    metadata={"document_id": "doc1", "chunk_id": "c1", "source_file": "f.pdf"},
    final_score=0.9)
pool, manifest = assemble_evidence_pool_with_manifest([(QuerySpec(query="Q1"), [c])])

pool_ids = [e.evidence_id for e in pool.all()]
# → ['evid:2d127395921e8a34']   (실제 Pool의 evidence_id)

manifest.by_query_order
# → [(QuerySpec(query='Q1', ...), [''])]   (manifest는 빈 문자열을 evidence_id로 기록)

manifest.queries_for(pool_ids[0])   # 실제 evidence_id로 조회
# → []   ← 이 질의가 이 근거를 찾았다는 사실이 다시 사라짐

manifest.queries_for('')            # manifest가 실제로 기록한 키
# → ['Q1']
```

**이것은 GS-P03A가 애초에 고치려던 결함과 정확히 같은 종류의 결함이다** —
질의→근거 연결이 소실된다. 발생 조건만 바뀌었다: r1의 결함은 "같은 evidence_id를
두 질의가 찾을 때"였고, 이번 결함은 "TSU 레코드에 `tsu_id`가 없을 때"다. 두 경우
모두 실제 운영 데이터(TSU 204,262건 중 `tsu_id` 결측 레코드가 존재할 가능성 — P1
승인 메모가 이 폴백 경로를 "실제로 쓰이는 경로"로 이미 언급했다)에서 재현 가능하다.

r2의 AC1 테스트(`test_manifest_queries_for_duplicate_evidence`)는 `tsu_id="E1"`
고정값만 사용해서 이 폴백 경로를 테스트하지 않았다 — 그래서 19개 테스트가 전부
PASS해도 이 결함이 드러나지 않았다.

## 근본 원인과 수정 방향

`_extract_evidence_ids()`가 identity 해석을 독자적으로(단순 `c.tsu_id`) 수행하지
않고, Pool이 실제로 사용하는 것과 **동일한 identity 해석 함수**를 재사용해야 한다.
`RankedCandidateEvidenceAdapter._resolve_evidence_id`는 `@staticmethod`이므로
import해서 재사용 가능하다(새 로직을 만들 필요 없음, STOP 조건 아님).

## 결론

STOP 조건에 해당하지 않는다(EvidencePool/Evidence 모델 수정 불필요 — 기존
staticmethod를 재사용하면 되는 국소 수정). 그러나 이 결함은 P3A의 존재 이유
자체를 훼손하므로 REWORK 없이 다음 Phase로 넘어갈 수 없다.

**recommendation: HOLD — GS-P03A REWORK r3 필요**
