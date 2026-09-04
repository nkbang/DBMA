---
title: "ADR-012: DBMA-SEQ — Sermon Evaluation & Quality"
category: architecture
sprint: DBMA-SEQ Phase 1
based_on:
  - docs/architecture/ADR-009-SIL-Theology-Engine.md
  - docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md
created: 2026-07-24
status: Architecture Decision (구조 제안 — Phase 1 착수는 별도 승인 필요)
scope_modified: docs/architecture/ 신규 (코드 미수정)
---

# ADR-012: DBMA-SEQ — Sermon Evaluation & Quality

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-24 |
| Deciders | HQ(사용자) 명명·프로젝트화 승인 / CUE 설계 |
| Supersedes | — |
| Superseded by | — |

---

## Context

`DBMA-SIL`(ADR-009, Sermon Intelligence Layer)이 설교 개요/확장
생성 기능 자체를 다루는 동안, **생성된 설교문의 품질을 어떻게
검증하고 개선할지**는 별도로 다뤄지지 않았다. 사용자가 "설교문 작성
같은 고차원 생성 작업엔 결국 이런 검증 루프가 필요하다"는 논의 끝에,
이 작업을 `DBMA-REQ`(ADR-010, RAG 검색·생성 품질 평가)와 동일한
명명 패턴으로 별도 프로젝트화하기로 승인했다.

`DBMA-REQ`가 "검색된 청크에 답변이 근거했는가"(groundedness)를
`rag_judge.py`로 측정하는 것과 같은 방식으로, `DBMA-SEQ`는 "생성된
설교 개요/본문이 검색 자료·본문 중심 진리에 실제로 근거했는가"를
측정하는 계층이다. 즉:

```
DBMA-REQ = RAG 답변 품질 평가 (질문-답 단위)
DBMA-SEQ = 설교문 생성 품질 평가 (설교 개요/확장 단위)
```

두 축 모두 최종적으로는 같은 `core/evaluation/` 모듈 아래 공존할 수
있으나, 평가 대상의 구조(단발 Q&A vs 다단계 설교 워크플로)가 달라
별도 ADR로 분리한다.

---

## Decision

### 이 ADR이 확정하는 것 — 명명과 범위만

- 프로젝트명: **DBMA-SEQ (Sermon Evaluation & Quality)**
- 범위: `DBMA-SIL`이 생성한 설교 개요/확장 결과물의 **사후 품질
  검증**만 다룬다. 생성 자체(프롬프트, 워크플로)는 `DBMA-SIL`(ADR-009)
  범위로 유지 — 이 ADR에서 건드리지 않는다.
- 코드는 아직 없음 — 이 ADR은 명명·스코프 확정만, 착수는 별도 승인.

### 제안 — 지난 대화에서 정리된 4가지 방향 (착수 순서 초안)

1. **Self-critique / judge 루프**: `core/evaluation/rag_judge.py`
   패턴을 재사용해 `sermon_judge.py`(가칭) 신설 — "이 대지가
   검색된 자료에 근거했는가"를 groundedness와 동일한 방식으로 채점.
2. **Few-shot 예시 뱅크 공식화**: 이미 존재하는 "문체 참고용 과거
   설교문 선택" 기능을 잘 쓴 사례 큐레이션으로 확장.
3. **단계형 생성 검증**: 개요→확장 각 단계마다 judge 채점을 끼워
   넣어, 나쁜 개요가 확장 단계까지 전파되지 않게 함.
4. **Eval harness**: `tests/fixtures/rag_eval_golden_set.json`과
   동일한 패턴으로 설교문 품질용 골든셋 구성 — 프롬프트 변경을
   감으로 판단하지 않고 수치로 비교.

이 순서·우선순위는 초안이며, Phase 1 착수 시 ADR-010과 동일하게
골든셋 라벨링 담당·소요시간을 먼저 HQ가 정해야 한다(ADR-010
Decision-미확정 §1과 동일한 선례).

### 명시적으로 다루지 않는 것

- Fine-tuning/LoRA — 프롬프트+RAG+judge 조합을 먼저 최대한 시도한
  뒤에만 고려 대상(지난 대화에서 논의된 순서).
- `DBMA-SIL`의 생성 워크플로 자체 변경 — 별도 ADR 필요.

---

## Consequences

- `DBMA-REQ`와 `DBMA-SEQ`가 유사한 judge 패턴을 공유하므로 코드
  중복 위험이 있다 — Phase 1 설계 시 `core/evaluation/` 안에서
  공통 로직(judge 호출 래퍼, JSON 파싱 방어 등)을 분리할지 검토.
- 이 ADR만으로는 아무 코드도 바뀌지 않는다 — Next Steps의 HQ 결정
  이후 Phase 1 착수.

---

## Next Steps

1. Phase 1 착수 여부 HQ 승인
2. 골든셋 라벨링 담당·일정 결정(ADR-010 §1과 동일 절차)
3. `sermon_judge.py` 최소 구현(groundedness 하나만, TDD)
4. Few-shot 예시 뱅크 큐레이션 기준 정의
