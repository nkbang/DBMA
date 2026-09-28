# REWORK WORK ORDER — Phase 3A (r2)

- 사유: r1 보고가 요구사항(AssemblyManifest)을 구현하지 않고 WO 발급 이전 상태의
  코드/보고서를 그대로 제출함. 상세: `docs/grounded_synthesis/reviews/GS-P03A-CUE-REVIEW-r1.md`
- 원본 WO는 여전히 유효하다: `docs/grounded_synthesis/GS-P03A-WO-Assembly-Manifest.md`.
  이 문서는 원본 WO를 **대체하지 않고 보강**한다 — 원본 WO 전체를 다시 읽어라.

## 지난 제출에서 빠진 것 (반드시 이번에 만들 것)

`core/evidence_assembly.py`에 원본 WO §설계에 정의된 그대로 추가:

```python
@dataclass(frozen=True)
class AssemblyManifest:
    by_query_order: list[tuple[QuerySpec, list[str]]]
    evidence_to_queries: dict[str, list[str]]

    def queries_for(self, evidence_id: str) -> list[str]:
        return self.evidence_to_queries.get(evidence_id, [])


def assemble_evidence_pool_with_manifest(
    query_candidates: MultiQueryInput,
) -> tuple[EvidencePool, AssemblyManifest]:
    ...
```

기존 `assemble_evidence_pool()`(r1에서 제출한 것, 변경 없이 유지)은 내부에서
`assemble_evidence_pool_with_manifest()`를 호출해서 pool만 반환하도록 리팩터링해도 되고,
두 함수가 독립적으로 존재해도 된다 — 단, 코드 중복 없이 조립 로직은 한 곳에만 있어야 한다.

## §7 오해 정정

r1 §7이 "EvidencePool의 build_query 한계는 결함이 아니며 Evidence model/EvidencePool을
수정해서 해결하지 않는다"고 적은 것은 **맞는 말이지만 이 WO의 요구와 무관하다.**
GS-P03A는 EvidencePool을 수정하라고 요구한 적이 없다. `core/evidence_assembly.py`
안에 EvidencePool과 완전히 별개인 새 자료구조(`AssemblyManifest`)를 추가하라는
요구다. §7을 그대로 반복하지 말고, 이번에는 실제로 AssemblyManifest를 구현한 뒤
"이제 이 한계가 manifest로 해결됐다"고 답하거나, 정말 구현이 불가능하다고 판단되면
그 이유를 기술적으로 설명하고 STOP으로 보고하라(단, 이 WO를 검토한 결과 구현
불가능할 기술적 이유는 없다 — QuerySpec/MultiQueryInput 입력만으로 충분히 구성 가능하다).

## 추가 지시 — 회귀 테스트 재현성

`tests/test_evidence_assembly.py:512, 521`의 `subprocess.run(["python", "-m", "pytest", ...])`를
`subprocess.run([sys.executable, "-m", "pytest", ...])`로 고쳐라(`sys.executable`을
import해서 사용 — 현재 실행 중인 인터프리터를 그대로 재사용하기 위함). "python"이라는
문자열 하드코딩은 실행 환경에 따라 다른 결과를 낸다(CUE 환경에서 재현 실패 확인됨).

## Acceptance Criteria (원본 WO AC1~AC6 그대로 — 다시 옮김, 전부 이번에 충족할 것)

- AC1: 같은 evidence_id를 질의 A와 B가 둘 다 찾으면 `manifest.queries_for(id) == ["A", "B"]`
  (CUE 재현 케이스와 동일 입력: E1을 질의 A, 이후 B가 찾음 — 이 정확한 시나리오를
  테스트로 작성할 것. r1에는 이 테스트가 없었다)
- AC2: `by_query_order`의 각 질의 안에서 evidence_id 순서가 원본 `RankedCandidate` 순위 순서와 동일
- AC3: 빈 candidates 리스트를 가진 QuerySpec은 `by_query_order`에 `(spec, [])`로 등장
- AC4: `assemble_evidence_pool()`(r1 제출분)의 동작이 이번 변경으로 바뀌지 않음(기존 16개 테스트 그대로 PASS)
- AC5: `core/evidence_pool.py`, `core/evidence_model.py`, `core/evidence_adapters/*` 무수정
- AC6: manifest 구성 로직이 `EvidencePool` 인스턴스의 내부 속성(`_evidences`, `_index`)에
  접근하지 않음(입력 `query_candidates`만으로 구성) — grep으로 확인 가능해야 함

## 보고

이전과 동일 양식(GS-00 §7). 보고서 파일명은 `GS-P03A-C1-REPORT-r2`로 CUE에게 전달할 것.
마지막 줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.
