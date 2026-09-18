# C1 Task Order 061 — ADR-034 Design Review (구현 전 설계 검토)

**상태**: 발급됨 — 구현 착수 전 독립 설계 리뷰
**우선순위**: P1 (구현 착수 차단 조건)
**선행 작업**: 없음 — 이 ADR은 아직 코드가 없다(설계 문서만 존재)
**근거 문서**: [docs/architecture/ADR-034-Sentence-Window-Context-Expansion.md](../architecture/ADR-034-Sentence-Window-Context-Expansion.md)
**작성일**: 2026-09-18
**역할**: Independent Design Reviewer (구현 전 단계 — 코드 감사 아님)

---

## 1. 배경

사용자가 청킹 overlap 정밀도를 높이는 방법으로 "Sentence-Window(이웃 청크
문맥 보강)" 방식 도입을 지시했다. `core/retrieval.py::RetrievalEngine`은
ADR-001이 지정한 유일한 Retrieval Engine Authority이며 CLAUDE.md CUE
Operating Policy상 "반드시 지켜야 하는 사항(명령 없이는 절대 변경 금지)"
보호 대상이다. 사용자가 "작업을 진행하라"로 설계를 승인했으나(2026-09-18),
Retrieval Engine을 건드리는 신규 Architecture 제안이므로 실제
`core/retrieval.py` 코드 변경 착수 전에 C1 독립 리뷰를 먼저 받는다.

**이번 Task Order는 코드 리뷰가 아니라 설계 리뷰다** — 아직 구현된 코드가
없다. C1은 ADR-034의 설계가 안전하고 타당한지, CUE가 놓친 위험이 없는지를
검토한다.

---

## 2. 검증 범위 (Scope)

### 2.1 필수 검토 항목

| # | 항목 | 방법 |
|---|---|---|
| D1 | ADR-001 준수 여부 | ADR-034가 `RetrievalEngine.retrieve()`의 랭킹/스코어링 로직을 실제로 변경하지 않는 설계인지 문서 재확인 |
| D2 | 삽입 지점 검증 | `core/retrieval.py:2078 ContextAssembler.assemble()`이 실제로 LLM 컨텍스트 조립의 유일한 지점인지 직접 grep/read로 재확인(CUE 주장을 그대로 신뢰하지 말 것) |
| D3 | TSU 스키마 무변경 근거 검증 | `core/tsu_builder.py:build_tsu_records()`의 `chunk_id = generate_chunk_id(document_id, idx)` 및 레코드가 idx 순서로 append된다는 CUE의 주장을 `core/document_identity.py` 소스 직접 확인으로 재검증 |
| D4 | Citation/스코어링 무영향 검증 | 제안된 변경이 `RankedCandidate.content`, `CitationBuilder.build_citations()`에 영향을 주지 않는 설계인지 확인 |
| D5 | 리스크 평가 | 문서 §Consequences 리스크(토큰 예산 증가, dedup 불완전) 외에 CUE가 놓친 위험이 있는지 판단 |
| D6 | ADR 충돌 검사 | ADR-008(청킹), ADR-030(Sermon Corpus FROZEN) 등 기존 ADR과 충돌하지 않는지 |

### 2.2 제외 항목

- 실제 코드 구현 검증 — 아직 코드 없음(구현 후 별도 Task Order 필요)
- 성능/토큰 비용 실측 — 설계 승인 이후 구현 단계에서 측정

---

## 3. 판정 기준

- **APPROVE**: 설계 그대로 구현 착수 가능
- **CHANGES REQUESTED**: 구체적으로 무엇을 바꿔야 하는지 명시
- **REJECT**: 구현 착수 부적절 — 근거 명시

---

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-061-REPORT.md`에 판정과 근거를 기록.

---

*모드 제약: 검토(§2) 자체는 PLAN MODE로 수행 — `core/`, `ui/`, `scripts/`,
`tests/` 등 소스 코드 파일은 어떤 모드에서도 수정 금지(읽기만). 단,
§4 산출물(`docs/agents/c1/C1-TASK-ORDER-061-REPORT.md`) 신규 작성은
PLAN MODE로 불가능하므로 **그 파일 하나만** ACT MODE로 전환해 작성한다
— ACT MODE 전환은 리포트 파일 생성/수정 목적에 한정하고, 다른 파일은
건드리지 않는다.*
