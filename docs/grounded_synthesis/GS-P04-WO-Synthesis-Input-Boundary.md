# WORK ORDER — Phase 4: Grounded Synthesis Input Boundary

- 선행 게이트: P3+P3A GREEN·HQ 승인, `docs/architecture/ADR-036-Grounded-Synthesis-Boundary.md` 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

`EvidencePool` + `AssemblyManifest`(P3A)를 받아, LLM에 실제로 전달할 입력
(`SynthesisInput`, ADR-036 B8)을 **새 점수 계산이나 재정렬 없이** 결정적 규칙으로 구성한다.
이 Phase는 LLM을 호출하지 않는다 — 입력을 구성하는 순수 함수만 만든다.

## 허용 파일

- 신규: `core/grounded_synthesis_input.py`
- 신규: `tests/test_grounded_synthesis_input.py`
- 무수정: `core/evidence_model.py`, `core/evidence_pool.py`, `core/evidence_assembly.py`,
  `core/retrieval.py`, `core/generation.py`

## 설계 (ADR-036 B3, B8 그대로)

```python
@dataclass(frozen=True)
class SynthesisInput:
    query_specs: list[QuerySpec]
    included_evidence_ids: list[str]
    excluded_evidence_ids: list[str]
    truncated: bool
    prompt_text: str


def build_synthesis_input(
    pool: EvidencePool,
    manifest: AssemblyManifest,
    max_evidence: int,
) -> SynthesisInput:
    """절단 규칙: 질의 순서(manifest.by_query_order) → 각 질의 내부 원 순위 순서로
    라운드로빈하며 evidence_id를 채운다. 이미 included에 들어간 evidence_id는
    건너뛴다(중복 방지, 순서는 최초 등장 기준). max_evidence에 도달하면 멈추고
    나머지는 전부 excluded_evidence_ids에 담는다. 점수를 읽거나 비교하지 않는다
    — evidence_id 자체의 존재 여부와 순서만 사용한다.

    prompt_text는 included_evidence_ids 순서대로 EvidencePool.get(id).text를
    이어붙여 만든다. 각 항목 앞에 "[출처: {source_file 또는 document_title 또는
    '미상'}]"을 붙인다 (가짜 출처를 만들지 않는다 — 값이 없으면 '미상'이라고
    명시적으로 쓴다. ADR-036 B2, Evidence 모델의 '가짜 provenance 금지' 원칙 계승).
    """
```

## Acceptance Criteria

- AC1: `included_evidence_ids`와 `excluded_evidence_ids`를 합치면 pool의 전체
  evidence_id 집합과 정확히 같다(누락·중복 없음)
- AC2: `max_evidence`보다 pool이 작으면 `truncated == False`, `excluded_evidence_ids == []`
- AC3: `max_evidence`보다 pool이 크면 `truncated == True`이고
  `len(included_evidence_ids) == max_evidence`
- AC4: 라운드로빈 순서 검증 — 질의 A가 [e1,e2,e3], 질의 B가 [e4,e5]를 찾고
  `max_evidence=3`이면 `included_evidence_ids == [e1, e4, e2]`
  (질의 순서 A→B→A→B..., 각 질의 내부는 원 순위 순서)
- AC5: 같은 evidence_id를 여러 질의가 찾아도(P3A manifest로 확인) `included`에 1회만 등장
- AC6: `prompt_text`에 `included_evidence_ids`의 모든 텍스트가 등장하고
  `excluded_evidence_ids`의 텍스트는 등장하지 않음
- AC7: `Evidence.provenance.source_file`이 None인 항목의 prompt_text에는
  "[출처: 미상]"이 그대로 나타남(위치를 지어내지 않음)
- AC8: 점수(final_score/retrieval_score/bm25_score 등)를 읽거나 비교하는 코드가
  없음(grep으로 `.final_score`, `.retrieval_score`, `sorted(`, `sort(` 부재 확인)
- AC9: `import ollama`, retrieval 클래스 import가 이 파일에 없음(ADR-036 B9)

## STOP 트리거 (이 Phase 특유)

- 절단 규칙에 점수 비교가 필요하다고 판단되면 → STOP #20
- EvidencePool의 반복 순서(`all()`)가 manifest의 질의 순서와 다르게 필요해서
  EvidencePool을 수정해야 한다고 판단되면 → STOP #3

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식.
