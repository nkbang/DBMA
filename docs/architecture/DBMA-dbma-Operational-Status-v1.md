---
title: DBMA dbma.py Operational Status Analysis
category: architecture
sprint: SPRINT17-RG-2
purpose: dbma.py를 "보호"해야 하는지 "격리 가능"한지 최종 판단하기 위한 운영 상태 감사.
status: research (조사 전용 — 코드 미수정)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정, 삭제/rename/import 변경 없음)
based_on:
  - docs/architecture/DBMA-Legacy-EntryPoint-Analysis.md (SPRINT16-B-2)
  - docs/architecture/DBMA-SPRINT17-Implementation-Plan-v1.md (§3 Phase 5 게이트, §6 Risk)
---

# DBMA dbma.py Operational Status Analysis

## 1. Current Status

| 항목 | 상태 |
|---|---|
| 문서 상태 | `docs/releases/v1.1.0/CHANGELOG.md:48` — 명시적으로 **"deprecated"** 선언 |
| Git 상태 | **2026-07-15** (오늘 2026-07-16 기준 하루 전)까지 수정 기록 존재 |
| Architecture 상태 | SPRINT16-B-2가 "legacy — archive candidate"로 잠정 분류, 단 "사람 판단 선행 조건" 명시 |

이번 조사(RG-2)는 SPRINT16-B-2(`DBMA-Legacy-EntryPoint-Analysis.md`)가 이미 수행한
분석을 재검증하고, 그 문서가 다루지 않은 **신규 발견 1건**(`dbma_ui.py`)과
**최근 커밋의 성격 분류**(요청된 조사 항목 2)를 추가한다.

---

## 2. Official Documentation References

기존 SPRINT16-B-2 조사와 동일한 결과를 재확인했다 — 문서 간 실행 명령 불일치가
여전히 존재한다:

| 문서 | 실행 명령 | 세대 |
|---|---|---|
| `README.md:67` | `streamlit run dbma.py` | 구버전(미갱신) |
| `.github/instructions/streamlit.instructions.md:241` | `streamlit run dbma.py` | 구버전(미갱신) |
| `.github/instructions/documentation.instructions.md:75` | `streamlit run dbma.py` | 구버전(미갱신) |
| `docs/UI_GUIDE.md:363` | `streamlit run ui/app.py` | 현재 세대 |
| `docs/releases/v1.1.0/USER_GUIDE.md:12,23` | `streamlit run ui/app.py` | 공식 v1.1.0 |
| `docs/releases/v1.1.0/OPERATIONS.md:148,204` | `streamlit run ui/app.py` | 공식 v1.1.0 |

**신규 발견 — 세 번째 진입점 `dbma_ui.py`**:

```python
# dbma_ui.py (전체, 16줄)
"""DBMA v1.1.0 — Production Streamlit Entry Point.

Resolves nested module import path instability when running
`streamlit run ui/app.py` directly from the project root.
...
Usage:
    streamlit run dbma_ui.py
"""
from ui.app import main
if __name__ == "__main__":
    main()
```

- 이 파일은 `ui/app.py`의 `main()`을 그대로 위임 실행하는 **얇은 wrapper**이며,
  docstring 자체가 "Production Streamlit Entry Point"라고 명시한다.
- 생성 커밋은 `28cf98e "DBMA v1.1.0 UI Release Candidate — Production baseline"`
  단 한 번뿐이며 이후 수정 이력이 없다 — 안정적으로 고정된 상태.
- 그러나 **README.md, USER_GUIDE.md, OPERATIONS.md, UI_GUIDE.md 어디에도
  `dbma_ui.py`에 대한 언급이 없다.** 즉 "공식 production entry point"라고 스스로
  주장하는 파일이 공식 문서 어디에서도 안내되지 않는 상태다.
- **위험**: `dbma.py`와 `dbma_ui.py`는 파일명이 한 글자 차이로 유사하다
  (CLAUDE.md 파일 관리 규칙 "이름이 비슷한 임시 파일은 정리 대상" 원칙과 정면으로
  충돌하는 사례). 신규 사용자나 AI 어시스턴트가 둘을 혼동할 위험이 실재한다.

---

## 3. Git Activity Analysis

`dbma.py`에 대한 최근 15개 커밋을 조사 항목 2의 분류 기준으로 분류했다:

| 커밋 | 메시지 | 분류 | 의미 |
|---|---|---|---|
| `bf30e8b` (2026-07-15) | feat: extend Chroma metadata schema for retrieval scope | **bug fix 아님, 신규 기능 추가** | 운영 가능성 확정 신호 |
| `b6890d3` (2026-07-15) | feat: preserve document metadata for retrieval scope | **신규 기능 추가** | 동일 |
| `b3bd9bb` (2026-07-15) | fix: correct embedding validation target for generation models | bug fix | 아직 운영 중 |
| `73b8a41` | fix: separate Ollama embedding and generation model selection | bug fix | 아직 운영 중 |
| `b00890c` | fix(dbma.py): resolve ChromaDB embedding dimension mismatch **crash** | bug fix (크래시 수정) | 실사용 중 발생한 장애 대응 정황 |
| `ccd2e6f` | merge: resolve conflict between MD reflow fix and SPRINT15-DEBUG logging | merge | 병행 브랜치 작업 존재 |
| `6771894` | feat(dbma.py): add sidebar reset button for stuck is_processing state | **신규 UX 기능** | "멈춘 상태"를 실사용자가 겪었다는 의미 |
| `2eff94d` | feat: re-enable SPRINT2_FEATURES; fix sidebar layout | feat/fix | 기능 플래그 재활성화 — 의도적 운영 결정 |
| `8e63dbd` | fix(dbma.py): guard unconditional COLLECTION_NAME reference in RAG chat tab | bug fix | 아직 운영 중 |
| `04de52c` | merge: reconcile origin's DBMA-ECP baseline sync with today's fixes | merge | — |
| `ce8fd83`, `1f3326d`, `ccde1f4` | baseline sync / engineering checkpoint | migration helper 성격 | 구조적 체크포인트 |
| `6aa15bf`, `6ca2335` | CI / 문서 자동화 추가 | infra | dbma.py 직접 로직과 무관 |

**분류 요청 표(bug fix / refactor / migration helper / dead cleanup) 적용 결과**:
15개 중 **"dead cleanup"에 해당하는 커밋은 0건**이다. 오히려 `bf30e8b`,
`b6890d3`, `6771894`, `2eff94d`는 **명백한 신규 기능 추가(feat)**이며,
`b00890c`는 **실사용 중 발생한 크래시**를 수정한 것이다. "migration helper"류는
`ce8fd83`/`1f3326d`(baseline sync/checkpoint) 정도이며 이것도 dbma.py를
폐기 방향으로 옮기는 커밋이 아니라 구조 동기화다.

**결론**: 최근 활동은 "죽어가는 legacy에 대한 정리 작업"이 아니라
**"살아있는 기능에 대한 지속적 개발"** 패턴이다. 특히 가장 최근 2개 커밋
(`bf30e8b`, `b6890d3`, 2026-07-15)이 **크래시 수정이 아닌 신규 기능 추가**라는
점이 SPRINT16-B-2가 이미 지적한 모순("deprecated 선언 이후에도 활발히 수정됨")을
한 단계 더 강하게 확인한다 — 단순 수정이 아니라 **기능 확장이 어제도 있었다.**

---

## 4. Runtime Dependency

`rg "dbma"` 전체 검색 결과, `dbma.py`를 코드 레벨에서 참조하는 곳은
**정확히 1곳**이다 (SPRINT16-B-2 확인 사항과 동일, 재검증 완료):

```python
# scripts/backup_chroma.py:32
from dbma import CHROMA_DIR
```

- `try/except ImportError`로 감싸여 폴백 경로가 있는 **느슨한 결합**.
- `core/`, `ui/`, `tests/` 어디에도 `import dbma` 형태 참조 없음(0건, 재확인).
- `dbma.py` 내부의 `query_rag()`/`build_rag_store()`는 완전히 self-contained —
  외부에서 호출되지 않는다(SPRINT16-B-2 3절과 동일 결론).
- CI(`ci.yml`)는 `scripts/validate_pipeline.py`만 실행하며 `dbma.py`를 직접
  실행하거나 import하지 않는다 — **CI 파이프라인은 dbma.py에 의존하지 않는다.**
- `tests/test_dbma.py`는 README에 언급만 있고 실제 파일은 존재하지 않음(재확인) —
  즉 dbma.py에 대한 **자동 회귀 테스트가 전혀 없다.**

**분류**: 코드 레벨 의존은 1건(느슨한 결합)뿐이나, **문서(README, `.github/instructions/*`)
레벨 의존은 3건** 존재하여 신규 유입 경로로 여전히 안내되고 있다.

---

## 5. User Workflow

두 가지 독립된 실행 경로가 실제로 동작 가능한 상태로 공존한다:

```text
경로 A (legacy, 자체 스택):  streamlit run dbma.py
경로 B (current, 문서 공식): streamlit run ui/app.py  (또는 streamlit run dbma_ui.py)
```

- 경로 A와 B는 임베딩 모델, 청킹 로직, 벡터 저장소(Chroma vs Qdrant), 검색 알고리즘,
  생성 방식이 전부 다른 **완전히 분리된 두 애플리케이션**이다(SPRINT16-B-2 §4 재확인).
- `dbma.py`가 2026-07-15까지 **기능이 추가되고 있었다**는 사실(§3)은 최소 한 명의
  실사용자(코드 작성자 본인 포함)가 **현재도 경로 A를 실행하며 그 결과로 발견한
  문제(크래시, UX 이슈)를 고치고 있다**는 강한 정황이다 — 단순 이론적 가능성이 아니다.
- 반대로 경로 B(`ui/app.py`)가 공식 문서(v1.1.0 USER_GUIDE/OPERATIONS)의 유일한
  안내 대상이라는 점은 "공식적으로 지향하는 사용자 경로"가 B임을 보여준다.

**판단**: 현재 **두 workflow가 동시에 살아있다** — 문서상 공식 경로(B)와 실제
활발히 수정되는 경로(A)가 다르다. 이는 조사 항목 4("dbma.py를 실행하는 workflow가
있는가, 아니면 ui/app.py만 쓰는가")에 대해 **"둘 다"**라는 답을 내리게 한다.

---

## 6. Migration Risk

| 리스크 | 등급 | 근거 |
|---|---|---|
| dbma.py를 archive하면 실사용 중인 기능 손실 가능 | **높음** | §3에서 확인된 2026-07-15 신규 기능 커밋(Chroma metadata schema) — 아직 아무 곳에도 마이그레이션되지 않은 기능일 수 있음 |
| `scripts/backup_chroma.py`가 조용히 깨질 가능성 | 낮음 | 폴백 경로 존재(느슨한 결합) — 즉시 실패하지 않음 |
| CI 파이프라인 영향 | 없음 | CI가 dbma.py를 참조하지 않음(§4 확인) |
| 신규 사용자가 문서(README/.github) 때문에 legacy 경로로 유입 | 중간 | 문서 정정은 저위험 별도 작업으로 분리 가능(SPRINT16-B-2 §6-2 이미 권고) |
| `dbma_ui.py`와 `dbma.py`의 이름 혼동으로 인한 실수 | 중간 | 격리/archive 작업 시 실수로 `dbma_ui.py`(현행 production wrapper)를 함께 건드릴 위험 — 반드시 구분해서 다뤄야 함 |

---

## 7. Final Classification

```text
Option A — Active User Entry Point   ← 해당
```

**판정 근거**:
- "deprecated" 선언(v1.1.0 CHANGELOG) 이후에도 **어제(2026-07-15)까지 신규 기능이
  추가**되고 있다 — 이는 "죽지 않은 legacy"를 넘어 "적극적으로 유지보수되는 병행
  경로"에 가깝다.
- 다만 이 활동이 **"프로젝트 공식 방향에서 승인된 개발"인지, 아니면 "문서 갱신이
  누락된 채 관성적으로 이어진 개인 작업 습관"인지는 코드/git 이력만으로는
  구분할 수 없다** — 이 구분은 사람 확인이 필요하다(SPRINT16-B-2가 이미 동일하게
  지적).
- 외부 코드 의존은 1건(느슨한 결합)뿐이므로, **"보호"가 필요한 대상은 코드
  의존성이 아니라 "아직 다른 곳으로 이관되지 않은 기능 그 자체"**다.

---

## 8. Recommendation for SPRINT17

1. **Phase 5(`dbma.py` isolation) 게이트는 계속 닫아둔다.** SPRINT17 계획서
   §3 Phase 5가 이미 "사람 확인 완료 후 착수"로 명시했고, 이번 조사는 그 게이트를
   닫아둘 근거를 강화했을 뿐 해제할 근거를 전혀 제공하지 못했다.
2. **사람에게 확인이 필요한 단일 질문**: "2026-07-15 커밋(`bf30e8b`, `b6890d3`,
   Chroma metadata schema 확장)은 계속 유지해야 하는 활성 작업인가, 아니면
   `ui/app.py`/`RetrievalEngine` 경로로 이미 대체된 실험이었나?" — 이 답에 따라
   Option A(보호 필요) 또는 Option B(freeze 가능)로 분기된다.
3. **`dbma_ui.py`를 문서에 등록**할 것을 권고한다(별도 저위험 티켓, 코드 변경 아님,
   README/USER_GUIDE에 언급 추가만) — 세 번째 진입점의 존재를 공식화해야
   `dbma.py`와의 혼동을 줄일 수 있다.
4. **Phase 1(DocumentContext) 착수에는 영향 없음**: `core/document_context.py`는
   `dbma.py`를 import하지 않고 어떤 기존 모듈에서도 참조되지 않는 완전히 격리된
   신규 파일이다(SPRINT17 계획 §7 Definition of Done). 이번 조사 결과가 Option A로
   나왔다고 해서 Phase 1 착수를 막을 이유는 없다 — Phase 1은 dbma.py의 운영 지위와
   무관하게 안전하다.

---

# 완료 보고

```text
Created files:
  docs/architecture/DBMA-dbma-Operational-Status-v1.md

dbma.py classification:
  Option A — Active User Entry Point
  (deprecated 선언 이후에도 2026-07-15까지 신규 기능 추가, 최근 15개 커밋 중
   "dead cleanup" 0건)

Current users:
  최소 1명(코드 작성자 본인) — 크래시 수정/신규 기능 커밋이 실사용 정황을 시사.
  공식 문서(v1.1.0)는 ui/app.py(또는 dbma_ui.py)를 유일한 공식 경로로 안내하나,
  실제로는 두 경로(dbma.py / ui/app.py)가 병행 운영 중.

Active references:
  코드: scripts/backup_chroma.py (느슨한 결합, 폴백 있음) — 1건
  문서: README.md, .github/instructions/*(2건) — legacy 안내 지속 중
  CI: 의존 없음

Migration risk:
  높음 — 2026-07-15 신규 기능(Chroma metadata schema)이 아직 core/retrieval.py
  경로로 이관되지 않은 상태에서 archive하면 기능 손실 위험

Recommendation:
  Phase 5 게이트 유지(닫힘). "2026-07-15 커밋이 계속 유지할 활성 작업인지"를
  사람에게 확인하기 전까지 dbma.py 격리/archive 착수 금지.
  dbma_ui.py를 공식 문서에 등록하는 저위험 작업을 별도 티켓으로 권고.

Impact on Phase 1:
  없음. core/document_context.py는 dbma.py와 완전히 격리되어 있어
  DocumentContext 구현(Phase 1) 착수는 이번 조사 결과와 무관하게 진행 가능.
```
