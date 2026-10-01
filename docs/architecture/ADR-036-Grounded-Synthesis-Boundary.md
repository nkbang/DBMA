---
title: "ADR-036: Grounded Synthesis Boundary (P4 → Final)"
category: architecture
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/DBMA-Grounded-Synthesis-P4-Final-Journey-CUE-Review-2026-09-27.md
created: 2026-09-27
status: Accepted (HQ 승인 2026-09-27, GS-P03A GREEN 승인과 함께 처리)
scope_modified: core/grounded_synthesis_input.py, core/grounded_claims.py,
  core/grounded_answer.py, core/grounded_citation.py (전부 신규,
  P4~P7에서 순차 생성), docs/grounded_synthesis/, tests/test_grounded_*.py
---

# ADR-036: Grounded Synthesis Boundary

| | |
|---|---|
| Status | **Accepted** (2026-09-27) |
| Date | 2026-09-27 |
| Deciders | HQ (승인, 2026-09-27) / CUE (설계) / C1 (구현) |
| Supersedes | — |
| Amends | 없음 — `core/generation.py`의 운영 근거-강제 경로(`_GROUNDING_DIRECTIVE`, ClaimGuard)는 그대로 둔다 |

## Context

P1(Evidence Data Model)·P2(EvidencePool)·P3(Multi-Query Assembly)는 검색 결과를
정규화·저장·조립하는 계층까지만 다뤘다. P4부터는 그 위에 LLM을 얹는다 — 이는
`docs/architecture/DBMA-Grounded-Synthesis-P4-Final-Journey-CUE-Review-2026-09-27.md`가
지적한 대로 새 Architecture Layer이며, ADR 없이 구현하면 CUE Operating Policy의
Architecture Freeze Rule 취지에 어긋난다.

이 ADR은 P4~P9 구현이 공유하는 경계를 미리 고정한다. 각 Phase WO는 이 ADR의
번호(B1, B2, ...)를 인용하고, 구현은 이 번호에 대응해야 한다.

또한 이미 운영 중인 근거-강제 생성 경로가 있다(`core/generation.py:188` 이하
`_GROUNDING_DIRECTIVE`, `core/generation.py:244` `_run_claim_guard`,
`core/claim_guard.py`). Grounded Synthesis는 이를 대체하는 것이 아니라 —
검증 가능한 별도 경로를 만들어 두는 것이다(D2, 아래 참고).

## Decision

### B1 — 두 경로 공존, 병합은 별도 ADR

Grounded Synthesis(`core/grounded_*.py`)는 P12까지 `ui/`나 운영 생성 경로에
연결하지 않는다. 독립적으로 실행 가능한 라이브러리 + 스크립트로만 존재한다.
`core/generation.py`, `core/claim_guard.py`는 이 여정에서 수정·대체·우회하지 않는다.
운영 경로 교체가 필요해지면 P12 이후 새 ADR과 HQ 승인을 받는다.

### B2 — Evidence 경계

LLM에 줄 수 있는 정보는 정확히 하나의 `EvidencePool`(P3 assembly 결과)의
내용뿐이다. 허용: EvidencePool에 들어간 Evidence의 `text`, `source_file`,
`document_title`, `document_id`, `chunk_id`, 점수 필드. 금지: 웹 검색, 숨은
retrieval, 임의 코퍼스 접근, 학습된 암묵 지식을 사실처럼 제시하는 것.
LLM이 이 경계 밖 정보를 사실처럼 답하면 P8 실패 케이스로 취급한다(그 자체는
막을 수 없다 — P7/P8이 사후 검증한다).

### B3 — 합성 입력은 EvidencePool 전체가 아니다

`EvidencePool` ≠ LLM 프롬프트 전체. 다중 질의 결과가 컨텍스트 예산을 넘으면
**새 점수 계산이나 재정렬 없이** 결정적 규칙으로 절단한다:
질의 순서(P3 assembly 입력 순서) → 각 질의 내부 원 순위 순서로 라운드로빈,
호출자가 정한 상한(`max_evidence`)까지. 넣고 뺀 evidence_id 전체를
`SynthesisInput.manifest`에 기록한다(P4).

### B4 — Claim은 Evidence 밖으로 나가지 않는다

각 Claim은 `evidence_ids: list[str]`을 가지며, 이 목록은 전부
`SynthesisInput.manifest`(B3)에 포함된 evidence_id의 부분집합이어야 한다.
포함되지 않은 evidence_id를 참조하는 Claim은 유효하지 않은 것으로 표시한다
(P5, "invalid citation" — 폐기하지 않고 표시만 한다. 폐기는 정보 손실이다).

### B5 — 근거 부족은 정상 결과다

- 빈 EvidencePool, 관련 없는 Evidence만 있는 경우, 질의 중 일부만 결과가 있는 경우
  전부 `InsufficientEvidence` 결과로 명시적으로 표현한다(예외를 던지지 않는다).
- 서로 다른 Evidence가 상충하면 LLM이 임의로 하나를 택하지 않는다 —
  두 입장을 각각의 출처와 함께 병기하는 형태로만 답한다(P6).
- 중복 Evidence 정책은 P2/P3의 정책(마지막 것 유지)을 그대로 따른다 — 이 ADR에서
  바꾸지 않는다.

### B6 — 검증은 두 층으로 나눈다

- **결정적 검사**(자동, 코드로 검증 가능): evidence_id 실재 여부, manifest 소속
  여부, 인용 구간이 `Evidence.text`에 실제로 존재하는지 — P7이 구현.
- **의미 지지 판정**(사람 또는 CUE 표본 검토): 인용된 Evidence가 실제로 그 Claim을
  뒷받침하는지 — 자동 채점 결과에 섞지 않고 별도 수치로 보고한다.

### B7 — 결정성

P4~P8 단위/통합 테스트는 stub LLM(고정 응답을 반환하는 callable)으로 작성한다.
실제 Ollama 모델 실행은 P9에서만 하고, 별도 섹션으로 보고한다(품질 근거로
자동 테스트 PASS 수치와 합산하지 않는다).

### B8 — 데이터 구조 (정본 시그니처 — 각 Phase가 정확히 이 형태로 구현)

```python
# core/grounded_synthesis_input.py (P4)
@dataclass(frozen=True)
class SynthesisInput:
    query_specs: list[QuerySpec]          # P3 QuerySpec 재사용
    included_evidence_ids: list[str]      # 순서 = 프롬프트에 들어간 순서
    excluded_evidence_ids: list[str]      # 예산 초과로 뺀 것들
    truncated: bool                       # excluded가 있으면 True
    prompt_text: str                      # 실제로 LLM에 전달될 텍스트

# core/grounded_claims.py (P5)
@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    evidence_ids: list[str]
    valid: bool          # 전체 evidence_ids가 included_evidence_ids의 부분집합이면 True

# core/grounded_answer.py (P6)
@dataclass(frozen=True)
class GroundedAnswer:
    status: Literal["grounded", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim]
    text: str
    insufficiency_reason: Optional[str]

# core/grounded_citation.py (P7)
@dataclass(frozen=True)
class CitationCheckResult:
    claim_id: str
    evidence_id: str
    id_exists: bool          # SynthesisInput.included_evidence_ids에 있는가
    span_found_in_text: bool # 인용 구간이 Evidence.text에 실재하는가
    provenance_traceable: bool
```

### B9 — 금지 import (P4~P8 신규 모듈 공통)

`ollama`, `qdrant_client`, `tantivy`, 네트워크 모듈(`requests`/`httpx`/`urllib`),
`subprocess`, `socket`. `QueryProcessor`/`HybridQueryProcessor`/`RetrievalEngine`/
`HybridRetriever`/`CandidateGenerator`/`GenerationService`. 예외는
`core/grounded_synthesis*_executor.py`(P9, 실행 스크립트 — 호출자 자격으로 허용).

## 검증 계획

각 Phase WO(`docs/grounded_synthesis/GS-Pn-WO-*.md`)의 Acceptance Criteria가
B1~B9에 대응한다. CUE는 매 Phase 보고를 받을 때마다
`docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md` §5의 절차로 독립 재실행 검증한다.

## Consequences

- 장점: LLM 계층 추가가 기존 retrieval/운영 생성 경로와 완전히 분리되어, 실패해도
  운영 서비스에 영향이 없다. Claim→Evidence→Source 역추적이 설계 시점부터 보장된다.
- 비용: P12까지는 사용자에게 보이지 않는 병렬 구현이다(D2). 운영 통합은 별도 승인 과정을 다시 거쳐야 한다.
- 위험: B3의 절단 규칙이 너무 단순하면(라운드로빈) 관련성 높은 근거가 빠질 수 있다 —
  P9 실측으로 재검토 대상(이번 ADR 범위 밖, 후속 Amendment 후보로 기록만 한다).

## Next Steps

1. HQ가 B1~B9 승인 또는 수정 지시
2. 승인 시 P4 WO 발행 (`GS-P04-WO-Synthesis-Input-Boundary.md`)
3. 각 Phase 종료 시 이 ADR의 승격 조건(구현 완료 + 회귀 통과 + CUE 독립 리뷰 + 사용자 승인)을
   P9 종료 시점에 한 번에 판단한다 — Phase마다 개별 승격하지 않는다(B1~B9는 세트로 검증)
