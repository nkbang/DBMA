---
title: "ADR-004: Research Workspace Layer"
category: architecture
sprint: SPRINT27-B-1
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-002-Document-Identity-and-Retrieval-Unit.md
  - docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md
created: 2026-07-18
status: Architecture Decision (구현 전, 승인 대기)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-004: Research Workspace Layer

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-18 |
| Deciders | CUE (Claude Sonnet) — architecture review |
| Input | C1(로컬 qwen3-coder:30b) 탐색 결과, PM 지시 |
| Supersedes | — |
| Superseded by | — |

---

## Context

DBMA는 현재:

```
Query → Retrieval → Result Display
```

로 끝나는 **단발성 검색 시스템**이다. 검색 결과는 `st.session_state`(`ui/state/store.py::StateStore`)에만 존재하며 브라우저 세션이 끝나면 소멸한다 — "이전에 무엇을 찾았는지"를 나중에 다시 볼 방법이 없다.

DBMA의 목적은 신학 연구 지능 플랫폼(Theological research intelligence platform)이며, 향후 **MIE(Ministry Intelligence Engine)** — DBMA가 단순 검색에서 연구 지능 플랫폼으로 진화하는 우산 아키텍처 — 의 기반이 될 예정이다. MIE의 구체 요구사항은 아직 미정이므로, 이번 결정은 **MIE를 특정 형태로 가정하지 않고, 미래에 read-only 소비자로 얹을 수 있는 최소 기반**을 만드는 데 집중한다.

**절대 변경 금지:** `core/retrieval.py`, `core/processing.py`, `core/identity_registry.py`, TSU schema, `documents.json`. 이 5가지는 SPRINT20~25에 걸쳐 확정된 Authority이며, ADR-001/002가 이미 그 경계를 확정했다.

---

## Decision

### 1. Research Workspace Layer 위치

```
core/research_workspace.py   (신규, core/ 최상위)
```

기존 Authority(Processing/Identity/Index/TSU/Retrieval/Generation)와 나란히 두되, **완전히 독립된 6번째 레이어**로 신설한다. `core/extraction_failures.py`(SPRINT21-H-1)가 이미 확립한 선례 — "기존 Authority의 스키마를 건드리지 않는 별도 모듈" — 를 그대로 재사용한다.

Research Workspace는 `core/retrieval.py::QueryProcessor.process()`를 **기존 public 인터페이스로만 호출**한다. 새 retrieval 메서드를 만들거나 우회 경로를 열지 않는다 → **"One Retrieval Engine" 원칙 유지**.

UI는 신규 페이지를 만들지 않고 기존 `ui/pages/research.py`를 확장한다(세션 저장/불러오기 UI 추가). Research 기능이 두 UI 표면으로 쪼개지는 것을 방지.

### 2. Research Session Storage 위치

```
{DEFAULT_OUTPUT_DIR}/research/sessions.json   (신규)
```

`extraction_failures.json`과 동일한 atomic write 패턴(`.tmp` + `os.replace`)을 재사용한다(**"One Config" 원칙** — 새 저장 메커니즘을 발명하지 않고 기존 패턴 재사용).

**TSU 콘텐츠를 복제 저장하지 않는다.** 세션 레코드는 `query`, `timestamp`, 결과의 **참조**(`tsu_id` / `document_id` / `citation_id`)만 저장한다. 실제 콘텐츠는 항상 TSU dataset에서 조회 — TSU schema 변경 없이 "그때 무엇을 찾았는지" 재현 가능.

```json
{
  "sessions": [
    {
      "session_id": "...",
      "created_at": "...",
      "queries": [
        {"query": "...", "timestamp": "...", "result_refs": ["tsu_id_1", "tsu_id_2", ...]}
      ],
      "notes": ""
    }
  ]
}
```

### 3. 기존 Core 보호 규칙 준수 확인

| 대상 | 상태 |
|---|---|
| `core/retrieval.py` | 무수정 — `QueryProcessor.process()` 기존 인터페이스만 호출 |
| `core/processing.py` | 무접점 |
| `core/identity_registry.py` | 무접점 — document_id를 참조만, 등록/조회 함수 신규 호출 없음 |
| TSU schema | 무수정 — 참조 필드만 저장, TSU 레코드 자체는 안 건드림 |
| `documents.json` | 무접점 |

`core/research_workspace.py`가 유일한 신규 모듈이며, 기존 5개 Authority 어디에도 import 방향이 역전되지 않는다(Research Workspace → QueryProcessor 단방향, 역방향 없음) → **"One Execution State" 원칙 유지**(검색 실행 상태의 단일 소유자는 여전히 QueryProcessor/RetrievalEngine).

### 4. Minimal Implementation Scope (1차, 승인 후 별도 구현 단계에서 진행)

```
core/research_workspace.py:
  create_session() / add_query_result(session_id, query, response_package)
  / load_session(session_id) / list_sessions()
  → 순수 함수, append-only, sessions.json 1개 파일, 원자적 쓰기

ui/pages/research.py:
  "세션에 저장" 버튼 1개 (이미 받은 ResponsePackage 재사용, 신규 retrieval 호출 없음)
  세션 목록/불러오기 패널 1개
```

**1차 범위 제외(명시적으로 보류):** 멀티유저, 세션 공유, 세션 기반 재랭킹/개인화, 자유형 메모 편집 UI 이상의 기능, MIE 연동 자체. Rule of Three 원칙 — 실사용 수요가 확인되기 전 확장하지 않는다.

### 5. Future MIE Compatibility

`sessions.json`을 **append-only + 참조 기반**으로 유지하면, 향후 MIE(또는 그 하위 구성요소)는 이 데이터를 **read-only로 소비만** 하면 된다 — 기존 5개 Authority가 서로에게 그렇듯, Research Workspace도 "쓰기는 소유자만, 읽기는 누구나" 원칙을 따른다.

MIE의 정확한 요구사항(예: 세션 간 링크, 외부 시스템 ID 매핑, 협업 기능)은 아직 미정이므로, 이번 결정은 그 요구사항들을 **선반영하지 않는다** — 참조 기반 설계 자체가 이미 미래 확장에 열려 있으므로, MIE 요구사항이 구체화된 시점에 스키마를 additive하게 확장하면 된다(SPRINT21-B의 `pipeline_state` additive migration 패턴과 동일한 방식 재사용 가능).

---

## Consequences

- `docs/architecture/` 외 코드 변경 없음(이번 ADR 자체는 설계 문서만).
- 향후 구현 시 `core/research_workspace.py` + `ui/pages/research.py` 확장만 필요, 5개 기존 Authority 파일은 diff 0을 유지해야 한다(이 ADR의 검증 기준).
- Agent 역할 분담: 이 ADR(Architecture Decision)은 CUE가 소유. 실제 구현은 승인 후 C1(로컬, qwen3-coder:30b)에게 위임 가능한 범위로 설계됨(단일 신규 파일 + 기존 파일에 소규모 UI 추가 — `docs/operations/LOCAL_LLM_HANDOFF.md`의 "로컬 모델에 적합한 작업 단위" 기준 충족).

---

## Validation

```
변경 파일: docs/architecture/ADR-004-Research-Workspace-Layer.md (본 문서) 1건
코드 변경: 0 files
```

---

*본 문서는 SPRINT27-B-1 범위(`docs/architecture/`)에서 작성되었으며, 어떤 코드도
수정하지 않았다. 구현은 이 ADR 승인 이후 별도 단계에서 진행한다.*
