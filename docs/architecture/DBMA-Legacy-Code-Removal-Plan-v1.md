---
title: DBMA Legacy Code Removal Plan v1
category: architecture
sprint: SPRINT20-H-5
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (SPRINT16-B-3, Correction: SPRINT20-H-3)
  - docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md (SPRINT20-H-4C)
  - docs/architecture/DBMA-Retrieval-Migration-Matrix-v1.md (SPRINT16-B-4, Updated: SPRINT20-H-4B)
status: executed (commit ce6b05a, 2026-07-17)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정) — 계획 수립 시점 기준
---

# DBMA Legacy Code Removal Plan v1

이 문서는 원래 계획 문서로 작성되었다(SPRINT20-H-5, 코드 미수정, read-only 조사).
이후 커밋 `ce6b05a` (archive: isolate legacy RAG modules from v1.1 architecture,
2026-07-17)에서 이 계획이 실행되었다: `dbma.py`, `core/search.py`,
`core/ingest.py`, `core/qdrant_init.py`가 `git rm`이 아니라 `archive/legacy/`로
이동(격리)되었고, `scripts/backup_chroma.py`는 archived 모듈을 import하지 않도록
legacy Chroma 경로를 직접 명시하는 방식으로 수정되었다. 아래 inventory는 실행 시점
기준의 판단 근거로 보존한다.

---

## 1. dbma.py Legacy Surface Inventory

### A. 완전 제거 후보

| 함수 | 외부 호출자 | 내부 호출자 | production path | 대체 경로 |
|---|---|---|---|---|
| `embed_text_ollama()` | 0 | **0(완전 dead code)** | 없음 | `core/embedder.py` |
| `query_qdrant()` | 0 | `query_rag()`(715행) 1건 | 없음(query_rag 경유만) | 없음 — 기능 자체가 불필요(ADR-001 Correction) |
| `upsert_to_qdrant()` | 0 | `build_rag_store()`(644행) 1건 | 없음(build_rag_store 경유만) | `core/ingest.py::insert()` (단, production에서 미사용) |

**중요한 제약**: `query_qdrant()`/`upsert_to_qdrant()`는 "외부 호출 0"이지만 **독립적으로 먼저 삭제할 수는 없다** — 각각 `query_rag()`/`build_rag_store()` 내부에서 여전히 호출되므로, 호출자가 제거되거나 그 호출부가 함께 정리되어야 실제로 dead code가 된다. `embed_text_ollama()`만 내부 호출조차 없어 **즉시, 독립적으로 제거 가능**하다.

### B. Migration 완료 후보 — `query_rag()`

```
query_rag()
 │
 ├── retrieval        (Chroma 유사도 질의 + query_qdrant(), store 파라미터로 분기)
 │       → QueryProcessor.process()로 대체 가능 (이미 구현·검증됨, SPRINT17-20)
 │
 ├── prompt construction  (단순 f-string, "문맥:\n{context}\n\n질문:\n{question}")
 │       → GenerationService.generate() 내부 프롬프트 조립과 동등(core/generation.py:78 참고,
 │         원래 query_rag()을 그대로 미러링해 만든 코드)
 │
 ├── generation        (ollama.generate() 직접 호출)
 │       → GenerationService.generate()로 대체 가능 (이미 구현·검증됨, SPRINT20-B)
 │
 └── citation          (없음 — sources 리스트만 반환, Citation 객체 없음)
         → Citation Layer로 대체 시 순수 기능 향상(source_file/evidence_confidence 등 신규 획득)
```

**결론**: `query_rag()`의 3개 구성요소(retrieval/prompt/generation) 전부 대상 모듈이 이미 존재하고 검증되어 있다. Citation은 기존에 없던 기능이라 "대체"가 아니라 "순수 추가"다. **`query_rag()` = obsolete orchestration** 판정을 검증 완료로 확정한다.

단, `query_rag()`를 실제로 제거하려면 그 유일한 호출자인 `render_trendy_chat_tab()`(UI 탭)도 함께 정리해야 한다 — UI가 여전히 이 함수를 호출하는 한 "죽은 코드"가 아니라 "활성 레거시 UI 경로"다.

### C. 보류 후보 — `build_rag_store()`

현재 `core/`에 다음 오케스트레이션을 대체할 모듈이 **존재하지 않는다**:
```
document ingestion → embedding → vector/index creation
```
`core/ingest.py`(Qdrant 쓰기), `core/embedder.py`(임베딩), `core/chunking_optimizer.py`(청킹)는 각각 개별 책임을 갖고 있지만, 이들을 엮어 "선택한 문서를 색인한다"는 사용자 workflow를 제공하는 오케스트레이터는 SPRINT16-B-4(Migration Matrix 최초 작성) 시점에도, 이번 재조사 시점에도 존재하지 않는다.

**판정**: `REMOVE ❌` / `ARCHIVE ⭕` — 대체 없이 제거하면 "선택 문서 재색인" 기능 자체가 사라진다.

---

## 2. External Dependency Audit

```
rg "dbma.py|query_rag|build_rag_store|query_qdrant|upsert_to_qdrant|embed_text_ollama" .
```

| 참조 위치 | 내용 | 분류 | 처리 |
|---|---|---|---|
| `tests/test_dbma_embed_texts_hardening.py` | `import dbma`, `dbma._embed_texts()` 직접 테스트(RC-HOTFIX-02 회귀 테스트, 실제 production 장애 재발 방지용) | tests 참조 | **migration 필요** — `dbma.py` 제거/archive 전에 이 테스트를 이관하거나 폐기 결정 필요. 단순 삭제 시 실제 발생했던 Ollama 배치 크기 장애의 회귀 가드가 사라짐 |
| `scripts/backup_chroma.py` | `from dbma import CHROMA_DIR` (try/except, 폴백 있음) | scripts 참조 | **수정 불요** — 느슨한 결합이라 dbma.py 제거해도 폴백 경로(`Path("chroma_db")`)로 정상 동작 |
| **`CLAUDE.md`** (프로젝트 최상위 지침 문서) | "DBMA의 핵심 진입점은 `dbma.py`" (5개 위치) | docs 참조 | **[해소, SPRINT20-H-6]** `dbma_ui.py`(→`ui/app.py`) 공식화 + `dbma.py` deprecated 명시로 갱신 완료 |
| `scripts/create_docs.py` | CLAUDE.md 등 15개 문서 템플릿 포함 | scripts 참조 | **[해소 + 신규 위험 발견, SPRINT20-H-6]** dbma.py 문구는 갱신했으나, 이 스크립트의 `main()`이 `docs/STATE.md`/`docs/TODO.md`/`docs/CHANGELOG.md`를 포함한 15개 문서를 **존재 여부 확인 없이 무조건 덮어쓴다**(`path.write_text()`, 조건 없음). 재실행 시 SPRINT20-G-4에서 갱신한 문서 전부가 조용히 파괴될 수 있음 — §6 참고, 이번 CUE 범위 밖이라 코드는 미수정 |
| `README.md:105-106` | `build_rag_store()`/`query_rag()`를 "기능 목록"으로 여전히 문서화 | docs 참조 | **정리 필요** — Removal 진행 시 함께 갱신 |
| `docs/architecture/*` (다수) | Migration Matrix, ADR-001, ADR-003, Legacy-EntryPoint-Analysis 등 | docs 참조 | 처리 불요 — 이미 정정된 분석/계획 문서 자체, 역사적 기록으로 유지 |
| `docs/debug/debug_embedding_issue.md` | 과거 디버깅 메모 | docs 참조 | 낮은 우선순위, 필요 시 정리 |
| `dbma.py` 자기 자신 (947, 763, 702, 970행 등) | 함수 정의 + 내부 호출 | 자기 자신만 참조 | §1 참고 |

**README.md의 `test_dbma.py` 언급(L12)은 실체가 없는 경로**다 — `test_dbma.py`는 저장소에 존재하지 않는다(README 자체의 오탈자/구식 정보로 추정, 실제 테스트 파일명은 `tests/test_dbma_embed_texts_hardening.py`).

---

## 3. Entry Point Impact

```
rg "import dbma|from dbma" . (core/, ui/, scripts/, tests/)
```

결과: `core/*`, `ui/*`에서 `dbma.py`를 import하는 곳 **0건** — ADR-001/ADR-003이 전제한 "공식 경로(`dbma_ui.py`→`ui/app.py`)와 legacy(`dbma.py`)의 완전 분리"가 코드 레벨에서 사실로 확인됨. 유일한 2건은 `scripts/backup_chroma.py`(느슨한 결합, 처리 불요)와 `tests/test_dbma_embed_texts_hardening.py`(hard import, migration 필요 — §2 참고).

---

## 4. Removal Strategy (SPRINT20-H-6에서 4-Phase로 확정)

### Phase 1 — Dead Function Removal

```
embed_text_ollama()
```
**Blocker: 없음** — 내부 호출조차 없는 완전한 dead code. 즉시 실행 가능한 유일한 항목.

### Phase 2 — Qdrant/Chroma Write Path Removal

```
query_qdrant()
upsert_to_qdrant()
get_vector_client()
get_collection()
```
**Blocker**:
1. `query_qdrant()`는 `query_rag()`(Phase 3) 내부 호출, `upsert_to_qdrant()`/`get_vector_client()`/`get_collection()`은 `build_rag_store()`(§1-C, ARCHIVE 판정) 내부 호출 — **호출자가 살아있는 한 제거 불가**. Phase 3 완료 및 `build_rag_store()` archive 처리 이후에만 실행 가능.
2. Chroma/Qdrant 데이터 자체는 ADR-003에 따라 보존(KEEP) — 이 Phase는 **쓰기 경로 코드 제거**일 뿐, 데이터 삭제가 아님.

### Phase 3 — Legacy UI & query_rag Removal

```
query_rag()
render_trendy_chat_tab()
(및 하위: render_noise_bar, init_chat_state, chat_user_bubble,
 chat_assistant_bubble, pick_docs_for_embedding)
```
**Blocker**:
1. **`tests/test_dbma_embed_texts_hardening.py` 이관 미완료** — 단순 테스트 이동이 아니라, 이 테스트가 지키는 oversized-input guard(`_MAX_SAFE_EMBED_TOKENS`)와 selective retry policy(`_is_retryable_ollama_error`)가 **`core/embedder.py`(실제 production 경로)에 아예 존재하지 않음**을 SPRINT20-H-6에서 확인(§6 참고) — 코드 포팅이 선행되어야 함.
2. `dbma.py`가 실제로 활성 사용자에게 노출되고 있는지 최종 확인 — 2026-07-15 커밋(`bf30e8b`/`b6890d3`)이 활성 작업인지 여전히 미해결(CUE-20H-1/ADR-003 이후 계속 남아있는 질문).

### Phase 4 — dbma.py Archive

```
dbma.py
    ↓
archive/legacy/dbma_v1.py
```

**Blocker 상태**:
- ✅ Chroma backup 완료 (`backups/chroma_backup_20260716_233708/`, ADR-003)
- ✅ Qdrant snapshot 완료 (`backups/qdrant_snapshot_20260717/`, ADR-003)
- ✅ **CLAUDE.md/`scripts/create_docs.py` 갱신 완료 (SPRINT20-H-6)**
- ⚠️ Phase 2/3의 모든 선행조건 충족 이후에만 착수 가능
- 🔴 **신규 발견**: `scripts/create_docs.py`가 `docs/STATE.md`/`TODO.md`/`CHANGELOG.md`를 포함한 15개 문서를 무조건 덮어쓰는 구조 — 이 스크립트의 안전장치 부재 자체는 Phase 4의 직접 블로커는 아니나, Phase 4 착수 전(또는 별도 CUE로) 반드시 해결 권장

---

## 5. Validation

```
git status --short → 신규 계획 문서 1건(본 파일)만 존재해야 함
코드 변경: 0 files
```

---

## 6. SPRINT20-H-6 Update — Legacy Removal Readiness

### 6.1 CLAUDE.md Authority Correction

`CLAUDE.md`(프로젝트 최상위 지침)와 `scripts/create_docs.py`(CLAUDE.md 등 15개 문서를 생성하는 스크립트)의 "dbma.py=핵심 진입점" 문구를 전부 `dbma_ui.py`(→`ui/app.py`)로 갱신, `dbma.py`는 명시적으로 deprecated 처리했다.

**신규 위험 발견**: `scripts/create_docs.py::main()`이 `FILES` 딕셔너리의 모든 항목(`CLAUDE.md`, `docs/STATE.md`, `docs/TODO.md`, `docs/CHANGELOG.md` 등 15개)을 **존재 여부 확인 없이 `path.write_text()`로 무조건 덮어쓴다.** 이 스크립트를 재실행하면 SPRINT20-G-4에서 공들여 갱신한 STATE/TODO/CHANGELOG가 이 스크립트에 내장된 3~5줄짜리 초기 템플릿으로 조용히 되돌아간다. 이번 CUE 범위(문구 동기화)를 넘어서는 동작 변경이라 코드는 수정하지 않았으나, **별도 CUE로 안전장치(예: 대상 파일이 이미 존재하면 스킵하거나 확인 프롬프트) 추가를 강력히 권장**한다.

### 6.2 `_embed_texts()` Test Migration Plan

`tests/test_dbma_embed_texts_hardening.py`가 지키는 계약은 3가지다: (1) oversized-input guard — 추정 토큰 수가 `_MAX_SAFE_EMBED_TOKENS`(1800)를 넘으면 `ollama.embed()` 호출 전에 `ValueError`, (2) selective retry — EOF/HTTP 500/timeout류는 `_EMBED_MAX_ATTEMPTS`(3)까지 재시도, 404류는 즉시 실패, (3) `_is_retryable_ollama_error()`의 에러 분류 로직 자체.

**`core/embedder.py` 대조 확인 결과, 이 세 가지 안전장치가 전혀 존재하지 않는다** — 실제 production 임베딩 경로(`RetrievalEngine` → `core/embedder.py`)가 이 테스트가 막고 있는 실제 발생 이력이 있는 장애(RC-HOTFIX-01, Ollama llama-server 배치 크기 초과 크래시)에 무방비 상태다.

**판정: MOVE.** 단, "테스트 파일 이동"이 아니라 **가드 로직(`_MAX_SAFE_EMBED_TOKENS`, `_is_retryable_ollama_error`, 재시도 루프)을 `core/embedder.py`로 먼저 포팅**해야 하는 코드 작업이 선행된다. 테스트는 이번 CUE에서 수정하지 않았다(삭제 금지 지시 준수).

### 6.3 `build_rag_store()` Replacement Decision

재확인 결과 변동 없음: `build_rag_store()`는 여전히 `render_trendy_chat_tab()`(947행)에서 활발히 호출되며, `core/`에 대체 가능한 색인 오케스트레이터가 없다.

**판정: ARCHIVE.** KEEP(장기 유지 대상 아님)도 REPLACE(대체재 부재)도 아니다.

### 6.4 Legacy Removal Sequence

§4를 4-Phase로 확정했다(Phase 1 Dead Function Removal / Phase 2 Qdrant·Chroma Write Path Removal / Phase 3 Legacy UI & query_rag Removal / Phase 4 dbma.py Archive) — Phase별 Blocker는 §4 참고.

---

## 완료 조건 체크

```
☑ Task 1: Legacy Surface Inventory (A/B/C 분류 완료)
☑ Task 2: External Dependency Audit (tests/scripts/docs 분류 완료)
☑ Task 3: Entry Point Impact (core/ui import 0건 확인)
☑ Task 4: Removal Strategy 3-Phase 문서 작성 (SPRINT20-H-6에서 4-Phase로 확정)
☑ Task 5: 코드 변경 0건 (SPRINT20-H-5 시점)

SPRINT20-H-6:
☑ 공식 Entry Point 문서 완전 일치 (CLAUDE.md, scripts/create_docs.py)
☑ CLAUDE 재생성 위험 제거 — 단, create_docs.py의 무조건 덮어쓰기 자체는 별도 CUE 필요(위험 식별만 완료)
☑ _embed_texts() 테스트 처리 방향 확정 (MOVE, 단 core/embedder.py 코드 포팅 선행)
☑ build_rag_store 처리 전략 확정 (ARCHIVE)
☑ Legacy Removal Phase 확정 (4-Phase, Blocker 명시)
☑ 코드 영향 최소화 유지 (CLAUDE.md/create_docs.py 문구만 변경, core/ui/dbma.py/tests 무변경)
☑ git diff 예상 범위 일치
```

---

*본 문서는 SPRINT20-H-5/H-6 범위(`docs/architecture/`, `CLAUDE.md`, `scripts/create_docs.py`)에서
작성되었으며, `core/`, `ui/`, `dbma.py`, `tests/`는 수정하지 않았다. 실제 삭제/이동은
이 계획의 승인 이후 별도 CUE(H-7 이후)에서 진행한다.*
