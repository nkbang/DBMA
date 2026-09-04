# NAE Manual Crosswalk Review Package 001

**Project:** NAE-MANUAL-CROSSWALK-POPULATION-DESIGN-001
**작성일:** 2026-08-05
**대상 독자:** C1 — 구현 지시 아님, 절차 설계 검증만 요청.

---

## 검토 대상

```
docs/NAE_MANUAL_CROSSWALK_POPULATION_DESIGN_001.md (본 설계 전체)
docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md (선행 승인 정책, 참조)
docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md (선행 승인 스키마, 참조)
```

---

## 요약

Crosswalk Records가 여전히 0건인 상태에서, **첫 매핑을 사람이 어떻게
안전하게 확정할 것인가**의 절차(Candidate 선정 → Evidence 수집 →
Reviewer 검토 → 확정 → 등록 → TSU Eligible 재확인)를 설계했다.
실제 매핑은 0건 생성했다 — 이번 문서는 절차만 정의한다.

**실측 재조사에서 흥미로운 발견**: Canonical 3건 중 2건
(`PBC1765`/`SLBC1689`)이 이전 조사 시점(Preflight)보다 실제로
콘텐츠(`canonical.json`)가 채워져 있음을 확인했다. 그러나 RAW
메타데이터 경로가 비어있어 제목/저자 등 1차 대조 자료가 없다 —
Candidate Selection Policy(Phase2)가 "최소 2가지 독립 근거"를
요구하는 것과 맞물려, 지금 당장은 이 3건에 대해 충분한 근거를 가진
후보를 만들기 어렵다는 것도 함께 확인됐다.

또한 identifier `AF1815`가 Registry의 Andrew Fuller(사망 1815) 항목과
이름상 절묘하게 겹친다는 우연을 발견했는데, 이것이 정확히 Mapping
Policy가 금지하는 "이름 유사성만으로 추측하는" 패턴의 실제 사례라서
설계 문서에 반면교사로 기록해 두었다(실제 매핑 후보로 채택하지
않음).

---

## Required Questions(원문 그대로, 답은 본문 참고)

| 질문 | 답 |
|---|---|
| Q1. Manual Mapping 후보는 어떻게 선정하는가? | 5가지 근거 중 최소 2가지 독립 일치(설계 문서 §Phase2) |
| Q2. Evidence가 충분하다는 기준은 무엇인가? | Source Evidence + File Evidence 둘 다(§Phase3) |
| Q3. manual-confirmed 승인은 누가 할 수 있는가? | 사람(Reviewer), 자동 승인 없음(§Phase4) |
| Q4. Duplicate Mapping은 어떻게 처리하는가? | 자동 선택 금지, 더 강한 근거를 사람이 선택 또는 unmapped 유지(§Phase5) |
| Q5. TSU Activation 최소 조건은 무엇인가? | records≥1 ∧ manual-confirmed ∧ confidence=high ∧ TSU_ELIGIBLE=READY(§Phase6, 이미 구현됨) |
| Q6. Retrieval Architecture에 영향이 있는가? | 없음(§Phase7) |

---

## C1에게 요청하는 것

1. **"최소 2가지 독립 근거" 기준(Phase2)이 충분히 보수적인지** —
   더 엄격해야 할 이유가 있는지, 혹은 실용적으로 지나치게 엄격해
   Pilot 규모(10건)에서 단 1건도 확정하지 못하게 만들 위험이 있는지
2. **Evidence 필드 구조(Phase3, `evidence` 문자열 필드 안에 6개
   항목을 서술로 담는 방식)가 Schema 001의 기존 `evidence: string`
   필드와 호환되는지** — 구조화된 다중 항목을 단일 문자열 필드에
   담는 것이 향후 조회/검증에 지장이 없는지
3. **Duplicate/Multiple Candidate 처리(Phase5)에서, 서로 다른
   source가 같은 target을 가리키는 것을 Validator가 막지 않는다는
   점을 "의도된 것으로 남겨둔 판단"이 타당한지** — 실제 그런 사례가
   나올 가능성이 있는 아키텍처인지 재검토 요청
4. **Activation Requirement(Phase6)가 이미 구현된 코드와 정확히
   일치하는지 재확인** — 설계 문서가 인용한 4개 AND 조건이
   `check_tsu_gate()`/`is_gate_eligible()`의 실제 로직과 어긋나지
   않는지

**C1은 이 설계에 대한 구현을 지시받지 않는다** — 승인 후에만 실제
`manual-confirmed` 레코드를 생성하는 구현 단계로 진행한다.
