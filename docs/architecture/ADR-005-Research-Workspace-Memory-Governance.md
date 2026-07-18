---
title: "ADR-005: Research Workspace Memory Governance"
category: architecture
sprint: SPRINT27-D
based_on:
  - docs/architecture/ADR-004-Research-Workspace-Layer.md
created: 2026-07-18
status: Architecture Decision (구현 전, 승인 대기)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-005: Research Workspace Memory Governance

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-18 |
| Deciders | CUE (Claude Sonnet) — architecture review |
| Supersedes | — |
| Superseded by | — |

---

## Context

ADR-004(SPRINT27-B/C)로 `core/research_workspace.py`가 신설되어 검색 세션을
`{DEFAULT_OUTPUT_DIR}/research/sessions.json`에 참조 기반으로 저장하는 기능이
운영에 들어갔다. SPRINT27-D Preflight(코드/운영 데이터 직접 확인, 무수정)에서
다음 5개 구조적 gap이 발견되었다:

1. **Lifecycle 불일치**: `ui/pages/research.py`의 저장 버튼이 클릭마다
   `create_session()`을 새로 호출 — "세션"이 실제로는 항상 쿼리 1건짜리로만
   생성됨(운영 데이터 5건 전부 `queries` 길이 1로 확인). 데이터 모델은 세션당
   다중 쿼리를 지원하지만 실제로 쓰인 적이 없다.
2. **Identity 충돌 위험**: `create_session()`이 초 단위 timestamp 문자열만
   반환, UUID 없음 — 같은 초에 두 번 호출되면 동일 ID로 병합됨.
3. **운영 데이터 오염**: 실제 `sessions.json`에 `ref_test`/`debug_test` 등
   구현 검증 중 생성된 테스트 레코드가 섞여 있음.
4. **소비 경계 미정의**: 현재 유일한 소비자는 `ui/pages/research.py`(4개
   public 함수 경유)이나, 향후 MIE가 이 데이터를 어떻게 소비해도 되는지에
   대한 명시적 경계가 없었다.
5. **마이그레이션 규칙 부재**: `sessions.json`에 스키마 버전 필드가 없어
   `identity_registry.py`가 쓰는 additive-migration 패턴(SPRINT21-B 선례)을
   아직 적용할 수 없다.

본 ADR은 이 5개 항목에 대한 최종 결정을 기록한다. **코드 변경 없음** — 결정
사항의 실제 구현은 별도 승인 이후 진행한다.

---

## Decision

### 1. Lifecycle Decision

**채택: 브라우저 세션당 1개의 research session.**

페이지 진입 시 `st.session_state`에 `session_id`를 1회 생성해 보관하고,
이후 모든 "세션에 저장" 클릭은 `add_query_result(existing_session_id, ...)`로
동일 세션에 누적한다. `create_session()`을 클릭마다 재호출하지 않는다.
이로써 "세션"이 실제 연구 흐름(한 방문 내 여러 쿼리)을 의미하게 되어
데이터 모델과 실제 동작이 일치한다.

### 2. Identity Model

**채택: `f"{timestamp}-{uuid4().hex[:8]}"` 형태.**

시간 prefix로 정렬 가능성을 유지하면서 `uuid4` suffix로 동일 초 충돌을
제거한다. 순수 UUID4(제안 Option B)는 채택하지 않는다 — `created_at`
필드가 이미 정렬 근거로 존재하므로 시간 prefix의 추가 이득이 적고,
가독성(로그/디버깅 시 timestamp만으로 대략적 시점 파악 가능) 이점이 더 크다.

### 3. Data Governance Policy

**채택:**
- `sessions.json`에 `schema_version` 필드를 additive로 추가(없으면 `1`로
  간주).
- 운영 데이터에 이미 섞인 테스트/디버그 레코드(`session_id`가
  `ref_test`/`debug_test`인 것, `query`가 정확히 `"test query"`/
  `"debug query"`/`"reference test query"`인 것)는 **본 ADR 범위에서
  삭제하지 않는다** — 실제 운영 파일을 수정하는 작업이므로 별도 승인을
  받은 후 독립된 작업(코드 변경과 분리)으로 수행한다.
- 향후 정리 작업은 스키마 변경(마이그레이션)과 반드시 분리한다 — 같은
  커밋/같은 함수에서 스키마도 바꾸고 데이터도 지우지 않는다(§5 참고).

### 4. Memory Consumption Boundary

**채택:**
- 모든 소비자(현재 `ui/pages/research.py`, 향후 MIE 포함)는
  `core/research_workspace.py`의 public 함수(`create_session`,
  `add_query_result`, `load_session`, `list_sessions`)로만 접근한다.
  `sessions.json` 파일을 직접 여는 코드는 허용하지 않는다.
- **Memory Layer는 retrieval 랭킹/스코어링에 자동으로 피드백하지
  않는다.** 세션 기반 개인화·재랭킹·쿼리 자동 보정은 이번 결정 범위에서
  명시적으로 제외한다. 저장된 과거를 "보여주는" 것까지만 허용되고,
  과거가 현재 검색 결과에 영향을 주려면 별도 ADR이 필요하다.
- 이 경계는 `core/retrieval.py`가 여전히 유일한 Retrieval Engine
  Authority(ADR-001)라는 원칙의 직접적 연장이다.

### 5. Migration Strategy

- 모든 스키마 확장은 **additive**. 기존 5개 운영 레코드가 깨지지
  않아야 하며, `schema_version` 부재 시 `1`로 취급하는 하위 호환 방식을
  따른다.
- 테스트 데이터 정리(§3)는 마이그레이션이 아니라 별도 승인된 운영 데이터
  정리 작업으로 취급한다 — 코드 변경 커밋과 데이터 정리 작업은 항상
  분리한다(SPRINT21-G에서 코드 변경과 운영 데이터 백업/검증을 분리했던
  선례와 동일 원칙).
- Lifecycle 변경(§1)은 기존 레코드 구조(`queries: list`)를 그대로
  재사용하므로 데이터 마이그레이션이 불필요하다 — UI 쪽 로직만 변경하면
  된다.
- Identity 모델 변경(§2)은 신규 세션부터 새 형식을 적용하고, 기존
  timestamp-only ID를 가진 레코드는 그대로 유효한 것으로 취급한다(재발급
  하지 않음) — `session_id`는 불투명 문자열로만 다뤄지므로 형식 변경이
  하위 호환을 깨지 않는다.

---

## Consequences

- 본 ADR 자체는 문서만 추가 — 코드 변경 0건.
- 향후 구현 시 영향 범위: `ui/pages/research.py`(lifecycle 변경),
  `core/research_workspace.py`(identity 모델, `schema_version` 필드).
  5개 기존 Core Authority(retrieval/processing/identity_registry/TSU
  schema/documents.json)는 계속 무접점을 유지해야 한다(ADR-004 §3 검증
  기준 재확인).
- 운영 데이터 정리(§3)는 이 ADR 승인과 별개로, 실행 전 재확인 후 진행한다.

---

## Validation

```
변경 파일: docs/architecture/ADR-005-Research-Workspace-Memory-Governance.md (본 문서) 1건
코드 변경: 0 files
운영 데이터 변경: 0 files
```

---

*본 문서는 SPRINT27-D 범위(`docs/architecture/`)에서 작성되었으며, 코드와
운영 데이터(`sessions.json`) 모두 무수정 상태다. 구현 및 데이터 정리는
이 ADR 승인 이후 별도 단계에서 각각 진행한다.*
