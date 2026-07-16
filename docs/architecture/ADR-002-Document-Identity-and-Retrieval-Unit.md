---
title: "ADR-002: Document Identity and Retrieval Unit"
category: architecture
sprint: SPRINT16-C-2
status: accepted
based_on:
  - docs/architecture/DBMA-DocumentContext-Design-v1.md (SPRINT16-C-1, §0/§5)
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (SPRINT16-B-3)
  - core/document_identity.py, core/identity_registry.py, core/retrieval.py,
    scripts/repair_tsu_book_id.py (읽기 전용 분석)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-002: Document Identity and Retrieval Unit

| | |
|---|---|
| Status | Accepted |
| Date | 2026-07-16 |
| Deciders | SPRINT16-C-1에서 이월된 미해결 항목 기반 (구현 착수 전 사람 확인 필요 항목 별도 표시) |
| Supersedes | — |
| Superseded by | — |
| Related | ADR-001 (Retrieval Engine Authority) |

---

## 1. document_id 정의

**정의(변경 없음, 기존 코드 그대로 인정)**: `core/document_identity.py::generate_document_id()`가
발급하는 32자 SHA-256 prefix. 문서 **콘텐츠 기반** 결정적 식별자다.

- 동일 콘텐츠 → 동일 `document_id` (파일명/경로가 달라져도 불변)
- 콘텐츠 변경 → 새 `document_id`
- 공백 정규화(`_normalize_for_identity`) 후 해싱 — 개행/여백 차이는 ID를 바꾸지 않음
- 범위: **처리 파이프라인(추출→정제→청킹) 단위의 "문서 한 건"**을 가리킨다.
  `core/identity_registry.py`가 이 ID로 중복/변경을 판정한다.

이 ADR은 `document_id`의 발급 방식을 변경하지 않는다 — DocumentContext 설계
(SPRINT16-C-1)가 이미 이를 "owns" 목록에 포함시켰고, 이번 ADR은 그 위에
`chunk_id`/`tsu_id`와의 관계만 확정한다.

---

## 2. chunk_id 정의

**정의(변경 없음)**: `core/document_identity.py::generate_chunk_id(document_id, chunk_index)`가
만드는 `"{document_id}_chunk_{chunk_index:05d}"` 형식의 문자열.

- `document_id`에서 **파생**되는 하위 단위 식별자 — 독립적으로 존재할 수 없다
  (반드시 상위 `document_id`가 있어야 생성 가능).
- 범위: `core/processing.py::process_one_file()`이 `optimize_chunks()` 결과에
  대해 0부터 순차 부여한다(§0, SPRINT16-C-1 문서 확인). **처리 파이프라인이
  생성한 md 청크**를 가리키며, 검색 엔진의 어떤 자료구조와도 현재 연결되어
  있지 않다(§0 관찰 3, 아래 4절에서 재확인).

---

## 3. tsu_id 정의

**정의(변경 없음, 코드에서 확인)**: `"TSU-{book_id}-{sequence:06d}"` 형식
(예: `TSU-1PE-000936`, `scripts/repair_tsu_book_id.py:161-169` 확인).

- `book_id`(성경책 약어) + 순번으로 구성 — **콘텐츠 해시나 `document_id`와
  무관하게 독립 발급**된다.
- 범위: `core/retrieval.py::RankedCandidate.tsu_id`가 검색 결과의 유일한
  식별자로 사용한다. `core/retrieval.py` 전체를 확인한 결과 **`document_id`나
  `chunk_id`를 참조하는 코드가 단 한 줄도 없다** (`grep -n "document_id" core/retrieval.py` 결과 0건).
- TSU(Theological Semantic Unit로 추정, 정식 정의는 이번 조사 범위에서
  확인되지 않음)는 신학적 의미 단위(성경 구절 매핑 등)를 표현하는
  **검색 전용 자료 단위**이며, `core/processing.py`의 md 처리 파이프라인
  산출물(md 파일, chunk)과는 별도 생성 경로를 갖는 것으로 판단된다
  (TSU 생성 스크립트의 정확한 위치는 이번 조사에서 특정하지 못함 —
  **사람 확인 필요 항목**으로 4절에 명시).

---

## 4. 관계 모델 (Relationship Model)

### 확인된 사실

```text
document_id  ──generate_chunk_id()──▶  chunk_id
     │                                     │
     │  (연결 없음 — 코드상 매핑 부재)         │  (연결 없음)
     ▼                                     ▼
   [??? 공백 ???]                    [??? 공백 ???]
     ▲
     │  (연결 없음)
tsu_id  ◀── book_id + sequence (독립 발급)
```

`document_id`/`chunk_id` 계열과 `tsu_id`는 **현재 코드상 어떤 필드로도 서로를
참조하지 않는 두 개의 독립 네임스페이스**다. 이는 버그가 아니라 두 시스템이
서로 다른 시점에, 서로 다른 목적으로 설계된 결과로 보인다:
- `document_identity.py`/`identity_registry.py` — Sprint 15 전후 "Metadata
  Foundation" 작업(본 저장소 커밋 `bf30e8b`, `b6890d3`, `fd8a2aa`, `336fa5e` 등)
- TSU/`retrieval.py` — Knowledge Map의 "Phase 5: MIE Architecture"(sprint 13-14)
  시점에 이미 확립된 검색 자료 구조

### Decision: 관계 모델을 "매핑 테이블" 방식으로 채택한다

SPRINT16-C-1 §5-1이 제시한 두 옵션 중 **(b) 매핑 테이블 방식**을 채택한다.
(a) 발급 규칙 통일(chunk_id를 tsu_id로 겸용)은 채택하지 않는다.

**이유**:
1. TSU는 성경 구절 매핑(`book_id`+`chapter`+`verse`)이라는 **신학적 의미 단위**
   기준으로 발급되는 반면, `chunk_id`는 **텍스트 분량 기준**(청킹 알고리즘의
   chunk_size/overlap)으로 발급된다. 두 단위의 경계가 원천적으로 다르므로
   1:1 발급 규칙 통일은 한쪽 개념을 왜곡한다(예: 청크 하나가 여러 구절에
   걸치거나, 한 구절이 여러 청크에 걸치는 경우 대응 불가).
2. TSU 생성 파이프라인의 정확한 위치가 이번 조사에서 확인되지 않아
   (§3 마지막 문단), 발급 규칙을 통일하려면 그 파이프라인을 먼저 찾아
   수정해야 한다 — 이는 이번 ADR이 다룰 수 있는 범위를 넘어선다.
3. 매핑 테이블 방식은 **기존 두 체계를 건드리지 않고** 다리만 놓으므로,
   `core/retrieval.py`(ADR-001에서 Authority로 확정)와
   `core/identity_registry.py`(SPRINT16-C-1에서 DocumentContext 기반으로
   확정) 양쪽 모두에 대한 회귀 위험이 가장 낮다.

```text
[신규] DocumentContext.tsu_refs: list[str]
   문서/청크가 어떤 tsu_id(들)에 대응하는지 기록하는 부가 필드.
   방향: DocumentContext → tsu_id (단방향 참조)
   TSU 데이터셋 스키마 자체는 변경하지 않는다.
```

이 매핑을 **누가, 언제 채우는가**는 이번 ADR에서 결정하지 않는다 —
5절(Migration Impact)에서 후속 작업으로 명시한다.

---

## 5. Retrieval Citation Strategy

`core/retrieval.py::CitationBuilder.build_citations()`를 직접 확인한 결과,
현재 인용(citation) 생성은 다음 필드만 사용한다:

```python
vm = candidate.metadata.get("verse_mapping", {})
book_id, chapter, verse_start, verse_end  # 전부 verse_mapping 하위 필드
```

**`document_id`, `chunk_id`, `tsu_id` 중 어느 것도 인용 문자열 자체에는
노출되지 않는다** — 인용은 이미 "성경 구절 참조(book/chapter/verse)" 형식이며
내부 식별자와 무관하다.

### Decision: Citation Strategy는 현행 유지 + 추적성 필드 추가

- **표시(display) 계층**: `CitationBuilder`가 만드는 `book_id:chapter:verse`
  형식은 그대로 유지한다. 사용자에게 노출되는 인용 포맷을 바꿀 이유가 없다.
- **추적성(traceability) 계층**: DocumentContext가 도입되면, 각 `RankedCandidate`가
  참조하는 `tsu_id`로부터 원본 `document_id`/`source_file`을 역추적할 수 있어야
  한다 — 현재는 이 역추적이 불가능하다(코드상 연결 없음). 이는 "이 검색 결과가
  어느 원본 문서에서 왔는가"를 감사(audit)할 수 없다는 뜻이며, 신학 문서
  RAG 시스템에서 출처 추적 가능성은 `CLAUDE.md`가 명시한 "추적 가능성" 원칙에
  직결된다.
- **전략**: 4절의 매핑 테이블(`tsu_refs`)이 채워지면, `CitationBuilder`가
  선택적으로 `source_file`을 인용 하단에 부기(예: 각주 형태)할 수 있는
  **확장 지점**을 열어둔다. 이번 ADR은 이 확장을 설계만 하고 구현하지 않는다.

---

## 6. Migration Impact

| 항목 | 영향 | 코드 변경 필요 여부 |
|---|---|---|
| `document_id`/`chunk_id` 발급 방식 | 변경 없음 | 없음 |
| `tsu_id` 발급 방식 | 변경 없음 | 없음 |
| `CitationBuilder` 출력 포맷 | 변경 없음 (표시 계층 유지) | 없음 |
| DocumentContext에 `tsu_refs: list[str]` 필드 추가 | SPRINT16-C-1 설계에 필드 1개 추가 | SPRINT17 구현 시 필요 (스키마 확장) |
| 매핑 테이블을 채우는 프로세스 신설 | TSU 생성 시점 또는 별도 후처리 배치에서 `document_id ↔ tsu_id` 대응표를 만들어야 함 | **신규 코드 필요 — 이번 ADR 범위 밖, 별도 스프린트** |
| `identity_registry.py` schema_version | `tsu_refs` 저장을 위해 3.0으로 확장 검토 (SPRINT16-C-1 §6-3과 동일 항목) | SPRINT17 구현 시 필요 |
| TSU 생성 파이프라인 자체 | 위치/책임 불명확 — 발견 및 문서화 필요 | **선행 조사 필요 (다음 스프린트 후보 작업)** |
| `core/retrieval.py::RankedCandidate` | 변경 없음 (매핑은 DocumentContext 쪽에서만 유지, retrieval.py는 그대로) | 없음 (읽기 전용 참조만 가능하도록 설계) |

**사람 확인 필요 항목 (이 ADR이 단정하지 않고 이월하는 것)**:
1. TSU 데이터셋이 실제로 어느 스크립트/프로세스에서 생성되는지 특정.
2. 매핑 테이블을 배치로 한 번에 채울지, 아니면 처리 파이프라인 실행 시점에
   실시간으로 채울지 운영 방식 결정.
3. 기존에 이미 생성된 TSU 레코드(과거분)에 대한 소급 매핑이 필요한지,
   아니면 이후 신규 문서부터만 적용할지 범위 결정.

---

## 7. Impact on SPRINT16-C DocumentContext (§ 보강)

이 ADR은 `DBMA-DocumentContext-Design-v1.md` §5-1의 미해결 항목에 대한
공식 답변이다:
- 옵션 (b) 채택 확정 → SPRINT16-C-1 설계 문서의 "owns" 목록(§1)에
  `tsu_refs: list[str]`를 **부가 필드**로 추가해야 함이 이 ADR로 확정됐다.
- SPRINT17 Implementation Requirements 항목 4("document_id ↔ tsu_id 매핑
  정책 확정")는 이 ADR로 **완료**됐다 — 남은 것은 "누가 채우는가"의 구현
  설계(§6에서 별도 후속 작업으로 명시)뿐이다.

---

*본 문서는 SPRINT16-C-2 범위(`docs/architecture/`)에서 작성되었으며, 어떤
코드도 수정하지 않았다. §6의 "코드 변경 필요" 항목은 결정의 기록일 뿐
이번 스프린트에서 실행되지 않았다.*
