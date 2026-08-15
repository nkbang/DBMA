# C1 Night Shift Order — NAE Production Retrieval Bridge Implementation

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's authorization (2026-08-15) |
| Mission | NAE Production Retrieval Bridge |
| Priority | P0 |
| Mode | Autonomous / No Questions |
| Deadline | Tomorrow morning |
| Design basis | `docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md` (§A-J) |
| Prior evidence | `.automation/evidence/night-shift/nae-retrieval-bridge/` (feasibility + closeout, GREEN) |

---

## Note on supervision (read before starting)

CUE cannot programmatically trigger this session or read its live output — there is
no automated connection between CUE (Claude Code) and C1 (Cline) in this environment.
This order was manually relayed by Rev. Bang. CUE will periodically wake itself and
inspect `.automation/evidence/`, `.automation/requests/`, and `git status`/`diff` for
progress, and will write its audit findings to
`.automation/audit/NAE-BRIDGE-IMPLEMENTATION-CUE-WATCH-LOG.md` — but cannot send you
new instructions in real time. Complete the phases below in order, on your own
judgment, using the Self-Correction and Stop/Handoff rules — do not wait for a
reply between phases.

---

## Goal

ADR-024 승인 범위에 따라 NAE Retrieval Bridge를 실제 Production 사용 가능한 상태까지
구현한다. 이미 완료된 feasibility investigation은 반복하지 않는다. 조사보다 구현과
통합을 우선한다.

## PHASE 1 — IMPLEMENTATION

1. 기존 `NAE/retrieval_adapter.py` 구조를 기준으로 production bridge 구현.
2. `bridge_query()` contract 구현 — ADR-024 §D의 코드 스케치를 그대로 기반으로 사용:
   - 입력: `query_text: str`, `top_k: int = 10`, `limit_check: bool = True`
   - Embedding: `NAE/pipeline/embed/client.py::embed_text()` 재사용, `content_hash = sha256(query_text)`, `None` 반환 시 빈 리스트 반환(예외 아님 — ADR-024 §D/§G 참고)
   - Qdrant search: 기존 `search()` 함수 재사용(`limit_check=False`, module gate는 `bridge_query()`에서 이미 확인)
   - Mapping: ADR-024 §C의 필드 매핑 표(`map_nae_to_citation_metadata()`, Night Shift `citationbuilder-execution.py`의 검증된 로직을 production 함수로 승격)
   - `core/retrieval.py::CitationBuilder`, `RankedCandidate`를 import해 재사용(§D "명시적 의존성")
3. NAE module gating 확인/구현: `modules.nae_pd.enabled`(기본 `false`) — disabled 상태에서는 NAE retrieval 호출 금지, `NaePdModuleDisabledError` 전파.
4. NAE Qdrant read-only retrieval 연결 — `nae_qdrant`(7333)만 접근, `dbma_qdrant`(6333) 접근 코드 없음.
5. NAE payload를 DBMA-compatible retrieval result로 mapping.
6. `source_id`/`tsu_id`/`work_id`/citation/provenance를 결과에 보존.
7. `CitationBuilder` integration — 실제 호출, 반환된 `Citation` 객체의 필드 정확성 확인(ADR-024 §J-7).
8. timeout/connection failure/malformed result에 대한 fail-closed 처리 — ADR-024 §G: warn threshold 1,500ms, hard timeout 3,000ms, `except Exception: return []`.

## PHASE 2 — INTEGRATION

9. 실제 DBMA UI의 적절한 integration point를 확인하고, NAE module이 enabled일 때만 bridge가 호출되도록 연결(ADR-024 §E — `ui/pages/research.py` 비수정, 별도 신규 UI 요소만 추가).
10. 기존 `RetrievalEngine`의 architecture boundary를 불필요하게 변경하지 않는다 — `git diff core/retrieval.py`는 항상 비어 있어야 한다.
11. DBMA corpus와 NAE corpus를 혼합 저장하거나 기존 Production Qdrant를 mutation하지 않는다.

## PHASE 3 — TESTING (실제 실행, 서술 금지)

A. NAE module disabled → NAE retrieval 호출 없음
B. NAE module enabled → 실제 NAE Qdrant retrieval 성공
C. 영어 query
D. 한국어 query
E. citation/provenance 존재 확인 (ADR-024 §J-7 필드별 assert)
F. malformed/empty result
G. Qdrant connection failure (컨테이너 정지 등으로 실제 유발)
H. timeout
I. 기존 DBMA retrieval regression (`tests/test_book_alias_resolution.py`, `tests/test_query_enhancements_full_regression.py`)
J. 기존 NAE benchmark regression

각 테스트는 실제 실행 output과 exit code를 evidence로 저장한다.

## PHASE 4 — PRODUCTION SAFETY

다음은 변경하지 않는다: `core/retrieval.py` architecture, Production Qdrant data,
DBMA corpus, NAE raw corpus, ADR-001/003/013 boundary. NAE Qdrant는 READ ONLY.
Production mutation이 필요하다고 판단되면 임의로 실행하지 말고 BLOCKER로 기록한다.

## PHASE 5 — EVIDENCE

저장 위치: `.automation/evidence/night-shift/nae-retrieval-bridge-implementation/`

1. implementation summary, 2. changed files, 3. git diff, 4. test commands,
5. raw stdout/stderr, 6. exit codes, 7. retrieval results, 8. citation/provenance
output, 9. regression results, 10. production mutation = 0 확인.

PASS/GREEN은 실제 실행 evidence가 있을 때만 사용한다.

## PHASE 6 — PRIORITY (시간 부족 시)

P0: Adapter → module gating → Qdrant retrieval → result mapping → Citation/Provenance
P1: UI integration → failure handling → regression
P2: cleanup/refactoring/documentation — P0/P1을 지연시키지 않는다.

## NO-QUESTION RULE

질문하지 않는다. 불확실한 사항은 ADR-024와 현재 코드에서 근거를 찾아 결정한다.
안전한 결정이 불가능하면 해당 작업을 중단하고 BLOCKER를 evidence에 기록한 뒤
다음 독립 작업으로 진행한다.

## FINAL MORNING STATE

다음 중 하나로 명확히 판정한다: `PRODUCTION_READY` / `INTEGRATION_READY` /
`PARTIALLY_COMPLETE` / `BLOCKED`. 근거 없는 COMPLETE/GREEN 판정 금지.
