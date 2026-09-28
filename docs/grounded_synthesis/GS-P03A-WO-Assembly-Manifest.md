# WORK ORDER — Phase 3A: Multi-Query Assembly Manifest (P3 보정)

- 우선순위: **즉시** — 현재 진행 중인 P3(`core/evidence_assembly.py`, 아직 커밋 전)에 적용
- 대상: C1
- 선행 문서: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`(공통 규칙·STOP 조건 전체 적용),
  `docs/architecture/DBMA-Grounded-Synthesis-P4-Final-Journey-CUE-Review-2026-09-27.md` F1

## 배경 — 발견된 결함 (CUE 실측)

`core/evidence_pool.py:84-86`는 같은 `evidence_id`가 다시 들어오면 `(eid, evidence, build_query)`
튜플 전체를 덮어쓴다. 즉 같은 근거를 두 질의가 찾아내면, 먼저 찾은 질의와의 연결이 사라진다.

CUE가 실행한 재현:
```python
p = EvidencePool()
p.add(Evidence(evidence_id="E1", corpus_type="default", text="t"), build_query="A")
p.add(Evidence(evidence_id="E3", corpus_type="default", text="u"), build_query="C")
p.add(e1, build_query="B")   # 같은 E1을 다른 질의로 재삽입
print(p.by_query("A"))  # → []  (질의 A가 E1을 찾았다는 사실 소실)
```

`core/evidence_assembly.py`(P3, 현재 untracked)의 `assemble_evidence_pool()`은
`EvidencePool`만 반환하므로 이 결함을 그대로 물려받는다. `EvidencePool`은 수정하지 않는다
(P2 승인 계약, STOP #3) — P3가 **별도로** 질의→근거 연관을 기록해야 한다.

## 목표

`assemble_evidence_pool()`과 나란히, EvidencePool과 무관하게 "어떤 질의가 어떤
evidence_id를 찾았는가"를 완전히 보존하는 manifest를 만든다.

## 허용 파일

- 수정: `core/evidence_assembly.py` (기존 `QuerySpec`, `MultiQueryInput`, `assemble_evidence_pool` 유지 — 함수 추가만)
- 수정: `tests/test_evidence_assembly.py` (기존 16개 테스트 유지 — 추가만)
- 신규 생성 금지 (이 두 파일 내에서 해결)

## 설계

```python
@dataclass(frozen=True)
class AssemblyManifest:
    """질의 → evidence_id 연관을 EvidencePool의 overwrite 정책과 무관하게 보존한다.

    EvidencePool.by_query()는 evidence_id당 마지막 build_query만 안다.
    이 manifest는 그 반대 방향(질의 → 이 질의가 찾은 모든 evidence_id, 원 순위 순서)과
    정방향(evidence_id → 이 근거를 찾은 모든 질의) 둘 다 완전히 보존한다."""

    # 질의 순서대로: (QuerySpec, [evidence_id, ...])  — candidates의 원 순위 순서 유지
    by_query_order: list[tuple[QuerySpec, list[str]]]
    # evidence_id → 이 근거를 찾은 모든 QuerySpec.query (발견 순서)
    evidence_to_queries: dict[str, list[str]]

    def queries_for(self, evidence_id: str) -> list[str]:
        return self.evidence_to_queries.get(evidence_id, [])


def assemble_evidence_pool_with_manifest(
    query_candidates: MultiQueryInput,
) -> tuple[EvidencePool, AssemblyManifest]:
    """assemble_evidence_pool()과 동일하게 Pool을 만들되, manifest도 함께 반환한다.
    기존 assemble_evidence_pool()은 내부에서 이 함수를 호출하도록 리팩터링하거나,
    코드 중복 없이 이 함수가 유일한 조립 로직이 되도록 한다 (기존 공개 시그니처는 유지)."""
```

## Acceptance Criteria

- AC1: 같은 evidence_id를 질의 A와 B가 둘 다 찾으면 `manifest.queries_for(id) == ["A", "B"]`
  (CUE 재현 케이스와 정확히 같은 입력으로 테스트: E1을 질의 A, 이후 B가 찾음)
- AC2: `by_query_order`의 각 질의 안에서 evidence_id 순서가 그 질의의 원본 `RankedCandidate` 순위 순서와 동일
- AC3: 빈 candidates 리스트를 가진 QuerySpec은 `by_query_order`에 `(spec, [])`로 등장(누락되지 않음)
- AC4: `assemble_evidence_pool()`(기존 함수)의 반환값·동작이 이번 변경으로 바뀌지 않음
  (기존 16개 테스트 그대로 PASS)
- AC5: `core/evidence_pool.py`, `core/evidence_model.py`, `core/evidence_adapters/*` 무수정
- AC6: manifest는 EvidencePool 내부 상태(`_evidences`, `_index`)를 읽지 않고,
  `query_candidates` 입력만으로 독립적으로 구성됨 (grep으로 확인 가능해야 함)

## 금지

- `EvidencePool.add`/`add_batch`/`by_query`의 동작·시그니처 변경
- `RankedCandidate`, `Evidence` 필드 추가/변경
- STOP 조건 발생 시 `STOP CONDITION TRIGGERED`로 보고, 수정하지 말 것

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식. 마지막 줄은 `HOLD` 또는
`CUE READ-ONLY REVALIDATION REQUESTED`. 이 WO 완료 전에는 P3 커밋을 하지 않는다.
