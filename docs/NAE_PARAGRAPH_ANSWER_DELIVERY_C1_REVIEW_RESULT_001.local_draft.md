# NAE PARAGRAPH ANSWER DELIVERY — C1 Independent Review Result

**Task ID:** PR #17 (claude/p0-2-paragraph-anchored-evidence)  
**Review Type:** C1 Independent Review (read-only, implementation excluded)  
**Reviewer:** C1 (Independent Forensic Auditor)  
**Date:** 2026-09-10  
**브랜치:** `claude/p0-2-paragraph-anchored-evidence` (HEAD `447054e`, base `origin/dev/dbma-engine`)  
**판정:** 🟡 **YELLOW (조건부)** — Y-1 해소 시 GREEN

---

## 작업 환경

```
pwd: /Users/David/DBMA
HEAD: d86b60a48aedda59ab46c214b9d63b03fe298e45
toplevel: /Users/David/DBMA (worktree 아님 — 메인 체크아웃)
origin: https://github.com/nkbang/DBMA.git
```

---

## Executive Summary

PR #17은 NAE 브리지 전용 "완성 문단 형태 답변 전달"(옵션 A) 기능입니다.
`bridge_query()` 시그니처/반환 타입 무변경, `core/retrieval.py` 무접촉,
Qdrant/canonical.json 접근 read-only로 ADR-001/024/030 정합 확인.

**단, C1 Review(NAE-TSU-BUILDER-RESUME-001)에서 권고한 "torn write 명시 테스트"가
이 PR에서 삭제됨 — resume 안전성의 핵심 검증이 손실.**

---

## 질문별 판정 (§3 검토 질문 7항)

### 질문 1: `core/retrieval.py` 무변경 (ADR-001) — 🟢 GREEN

**검증:**
```bash
$ git diff origin/dev/dbma-engine..447054e -- core/retrieval.py | wc -l
       0
```

**결과:** `core/retrieval.py`에 변경 0줄. ADR-001("One Pipeline, One Config, One Retrieval Engine") 위반 없음.

---

### 질문 2: `bridge_query()` / Citation dataclass / content_excerpt 계약 무변경 (ADR-024 §C·§D) — 🟢 GREEN

**검증:**
- `bridge_query()` 시그니처 + 반환 타입(`list[Citation]`) **무변경**. 기존 호출자 영향 없음.
- `bridge_query_paragraphs()`는 **신규 함수** — dict 리스트 반환. Citation dataclass 건드리지 않음.
- `_map_nae_to_citation_metadata()`: ADR-024 §C 매핑 표에 `source_text`(전체) 추가. 기존 `content_excerpt`(200자) 유지. **계약 위반 아님** — `content_excerpt`는 그대로 200자 계약 유지, `source_text`는 계약 밖 추가(주석 명시).
- `bridge_query()`에서 `RankedCandidate.content = meta.get("source_text")` — `content_excerpt`를 `source_text`로 재사용하던 기존 버그 수정. 주석에 "계약 밖 편법의 수정" 명시.

---

### 질문 3: nae_qdrant 외 접근 없음 (리졸버는 canonical.json 로컬 파일만) — 🟢 GREEN

**검증:**
```bash
$ grep -n "localhost\|7333\|qdrant\|requests\.\|httpx\|urllib" NAE/pipeline/canonical/paragraph_lookup.py
8:(NAE/pipeline/index/qdrant_store.py:41-88). 이 모듈은 그 두 값으로  ← 주석만, import 아님

$ grep -n "localhost\|7333\|qdrant\|requests\.\|httpx\|urllib" NAE/answer_context.py
(nothing)
```

**결과:** `paragraph_lookup.py` line 8의 qdrant_store.py 참조는 **주석**일 뿐 import 아님. `answer_context.py` 네트워크 참조 전무. 리졸버는 `canonical.json` 로컬 파일만 읽음.

---

### 질문 4: `nae_tsu_v1`/`nae_ref_v1` mutation/upsert/reindex 코드 경로 0, `NAE/corpus/canonical/**` read-only (ADR-030) — 🟢 GREEN

**검증:**
```bash
$ git diff origin/dev/dbma-engine..447054e -- NAE/corpus/canonical/ | wc -l
       0  ← 변경 없음

$ grep "nae_tsu_v1\|nae_ref_v1\|upsert\|mutation\|reindex" NAE/retrieval_adapter.py
(nothing)
```

**결과:** `NAE/corpus/canonical/**`에 변경 0줄. mutation/upsert/reindex 참조 전무. 모든 Qdrant 접근은 `search`/`query_points`(read-only).
---

### 질문 5: #16 §3-1 정합화 — `_format_context_source_label` 재사용, work=/author= 병렬 속성 없음, 서지 이중 표기 없음 — 🟢 GREEN

**검증:**
```python
# answer_context.py line 77-90
def _source_label(bib: dict) -> str:
    """[#16 재개 체크리스트 §3-1] 서지 라벨은 PR #14가 이미 만든
    core/retrieval.py::_format_context_source_label 하나로 통일한다 —
    브리지가 별도 work=/author=/page= 속성 어휘를 만들지 않는다."""
    from core.retrieval import _format_context_source_label
    return _format_context_source_label({...})
```

**결과:** `_source_label()`이 `_format_context_source_label` 재사용. `work=`/`author=` 병렬 속성 없음. UI에서 `bib.get("work")`, `bib.get("author")`는 **카드 표시용**이며 서지 라벨 생성과 무관 — `_source_label()`이 단일 출처 라인 생성.

---

### 질문 6: 테스트 회귀 — torn write 테스트 삭제 — 🟡 YELLOW

**검증:**
```bash
$ git diff origin/dev/dbma-engine..447054e -- tests/test_nae_tsu_builder.py | grep "^-def test_"
-def test_build_tsu_resume_tolerates_torn_write_tsu_ahead_of_report(tmp_path: Path):
```

**발견:** C1 Review(NAE-TSU-BUILDER-RESUME-001)에서 권고한 "torn write 명시 테스트"가 **삭제됨**. 이 테스트는 64줄로 resume의 핵심 안전성 시나리오를 커버 — tsu.json이 report보다 많은 경우의 resume 정확성을 검증.

**영향:** 이 테스트가 없으면 resume의 torn write 보호가 명시적으로 검증되지 않음. 설계 문서 §4의 논증은 수학적이나, 명시 테스트 부재는 C1 권고를 미이행.

**해소 방안:** `test_build_tsu_resume_tolerates_torn_write_tsu_ahead_of_report` 재추가.

---

### 질문 7: `bridge_query_paragraphs()` dict 반환이 UI/호출자에 안전한가 — 🟢 GREEN

**검증:**
```python
# ui/pages/research.py line 552-554
for i, item in enumerate(nae_results, 1):
    if isinstance(item, dict):
        _render_nae_paragraph_card(i, item)
    else:
        _render_nae_legacy_card(i, item)
```

**결과:** UI가 `isinstance(item, dict)`로 타입 분기 — Citation 객체(legacy)와 dict(paragraph)를 구분. 폴백 경로 존재. 안전.

---

## 추가 발견 (C1 독립 검증)

### A-1: verse_mapping 근사 (중요도: 중)

`_map_nae_to_citation_metadata()`에서 `verse_mapping["chapter"] = paragraph`,
`verse_mapping["verse_start"] = sentence` — paragraph/sentence index를 성구
chapter/verse로 매핑. CitationBuilder가 이를 실제 성구로 해석할 경우 잘못된
인용 생성 가능.

**현재 영향:** 이 함수는 `bridge_query_paragraphs()` 경로에서만 쓰이며,
`bridge_query()` 경로는 기존 동작 유지. 하지만 downstream에서 이를 성구로
해석할 경우 위험.

**해소 방안:** 별도 이슈로 추적. 필요 시 paragraph_lookup.py에서 scripture
reference를 별도 필드로 전달하는 방식으로 수정.

---

### A-2: 테스트 수 불일치 (중요도: 저)

CUE 요청 "2930 passed / 15 skipped" vs 실제 수집 "2844 tests collected".
PR #17에서 +19 신규 -1 삭제 = +18 net. 기존 2826 → 2844 추정.

**해소 방안:** CUE 측 재검증. PR merge 전 실제 테스트 실행 권장.

---

### A-3: `nae_para_reconcile.py` — Qdrant 의존 (중요도: 저)

스크립트가 라이브 nae_qdrant(포트 7333) 필요. CI/유닛테스트에서 돌릴 수 없음.
수동 실행만 가능.

---

## 판정 요약

| 항목 | 판정 |
|---|---|
| 질문 1 (core/retrieval.py 무변경) | 🟢 GREEN |
| 질문 2 (bridge_query/Citation 계약 무변경) | 🟢 GREEN |
| 질문 3 (nae_qdrant 외 접근 없음) | 🟢 GREEN |
| 질문 4 (mutation/upsert 코드 경로 0) | 🟢 GREEN |
| 질문 5 (#16 §3-1 정합화) | 🟢 GREEN |
| 질문 6 (torn write 테스트 삭제) | 🟡 YELLOW |
| 질문 7 (bridge_query_paragraphs dict 안전성) | 🟢 GREEN |

**최종 판정: 🟡 YELLOW (조건부)**

### 조건부 GREEN 조건

**Y-1 해소 시 → GREEN.** `test_build_tsu_resume_tolerates_torn_write_tsu_ahead_of_report` 재추가 필요. A-1/A-2는 현재 PR의 안전성에 직접적 영향 없음.

---

## Gate Assessment

| 조건 | 상태 |
|---|---|
| ADR-001 정합 (core/retrieval.py 무변경) | ✅ |
| ADR-024 정합 (bridge_query/Citation 계약 무변경) | ✅ |
| ADR-030 정합 (mutation/upsert 0, canonical read-only) | ✅ |
| #16 §3-1 정합화 | ✅ |
| C1 권고 #1 이행 (torn write 테스트) | ❌ 삭제됨 |
| HQ 승인 | ⏳ 대기 |

---

## Summary

본 C1 Review에서 7개 질문 중 6개 GREEN, 1개 YELLOW(Y-1: torn write 테스트 삭제).
PR #17의 핵심 변경(옵션 A 문단 앵커드 근거)은 ADR 정합, 계약 무변경, read-only
접근 모두 확인됨. **Y-1(torn write 테스트 재추가) 해소 시 GREEN 승격 가능.**

**권고:** Y-1 해소 전 PR merge는 보류. torn write 테스트는 resume 안전성의 핵심이므로
재추가 필수. A-1(verse_mapping 근사)은 별도 이슈로 추적하되 현재 PR의 blocker는 아님.
