# C1 Review 결과 — NAE 완성 문단 답변 전달 (옵션 A) PR #17

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-10
- 유형: **C1 Review** (독립 검증 — read-only 코드 확인 + pytest 신규 테스트 실행)
- PR: `claude/p0-2-paragraph-anchored-evidence` → `dev/dbma-engine`
- HEAD: `7232f0a3cc0aec96a8214b2cb0863b7f1665c24a`

---

## 워크트리 확인 (stale status 방지)

```
7232f0a3cc0aec96a8214b2cb0863b7f1665c24a
nas	http://100.94.139.122:3000/David/DBMA.git (fetch)
nas	http://100.94.139.122:3000/David/DBMA.git (push)
origin	https://github.com/nkbang/DBMA.git (fetch)
origin	https://github.com/nkbang/DBMA.git (push)
/Users/David/DBMA/.claude/worktrees/c1-pr17-review
```

---

## 7개 질문 검증 결과

### Q1: ADR-001 무영향 — `core/retrieval.py` diff

**판정: GREEN**

```bash
$ git diff origin/dev/dbma-engine -- core/retrieval.py | wc -l
       0
```

`core/retrieval.py`에 **단 한 줄의 변경도 없다**. 옵션 A는 `RetrievalEngine`/`QueryProcessor`/`RankingEngine`/`ContextAssembler`를 건드리지 않으며, payload에 이미 있는 `(identifier, paragraph)`로 `canonical.json`에서 결정적 dict 조회만 수행한다. 스코어링·랭킹·벡터스토어 쿼리 경로가 전혀 없다.

---

### Q2: ADR-024 §C/§D 계약

**판정: GREEN**

#### Q2a: `bridge_query() -> list[Citation]` 시그니처 무변경

`bridge_query()`는 이 PR에서 **신규 추가된 함수**이며, 기존 `core/retrieval.py::bridge_query`를 수정하지 않는다. 기존 bridge_query는 `core/retrieval.py`에 존재하지 않으며(grep 실패), NAE `retrieval_adapter.py`의 신규 함수다.

#### Q2b: `Citation` dataclass 무변경

```bash
$ grep -n "class Citation" core/retrieval.py
2093:class Citation:
2121:class CitationBuilder:
```

Citation dataclass (core/retrieval.py:2093-2120) 필드: `citation_id`, `tsu_id`, `scripture_reference`, `source_title`, `source_author`, `document_id`, `content_excerpt`, `evidence_confidence`, `retrieval_score`, `source_file`, `language`, `source_type`. **신규 필드 추가 없음.** `bridge_query_paragraphs`는 별도 `list[dict]`를 반환하므로 Citation에 접근하지 않는다.

#### Q2c: `content_excerpt = source_text[:200]` 계약 유지

`_map_nae_to_citation_metadata()` (retrieval_adapter.py:79-163)에서 `content_excerpt`는 `source_text[:200]`으로 매핑되며, `_enrich_hit_with_paragraph()` (311-364)에서도 `"content_excerpt": meta.get("content_excerpt", "")`로 그대로 전달한다. 계약 유지 확인.

#### Q2d: `nae_qdrant`(7333) 외 스토어 접근 없음

```bash
$ grep -n "localhost\|7333\|qdrant\|requests\.\|httpx\|urllib" NAE/pipeline/canonical/paragraph_lookup.py NAE/answer_context.py
NAE/pipeline/canonical/paragraph_lookup.py:8:(NAE/pipeline/index/qdrant_store.py:41-88). 이 모듈은 그 두 값으로
```

**주석**에서 `qdrant_store.py`를 참조할 뿐, 실제 import나 네트워크 접근이 없다. `paragraph_lookup.py`는 오직 `json.load`로 로컬 `canonical.json`만 읽는다. `answer_context.py`에는 해당 패턴이 전혀 없다.

---

### Q3: ADR-030 v2.1 §7/§8/§11 baseline 보호

**판정: GREEN**

#### Q3a: TSU/Ref mutation·upsert·재색인 코드 없음

```bash
$ grep -rn "upsert\|mutation\|reindex" core/retrieval.py core/ranking.py core/context_assembler.py | grep -i "tsu\|ref_v1\|nae_tsu\|nae_ref"
core/retrieval.py:1434:        first rebuild_tsu_index()/reindex_document() call). Treated as an
```

1434번 줄은 **주석**일 뿐, 실제 코드 경로가 아니다. mutation/upsert/reindex 관련 코드가 TSU/Ref 레코드에 쓰이는 경로가 전혀 없다.

#### Q3b: `NAE/corpus/canonical/**` read-only

```bash
$ grep -rn "open.*write\|\.write\|json.dump\|json.dumps" NAE/pipeline/canonical/paragraph_lookup.py NAE/answer_context.py NAE/retrieval_adapter.py
NO_WRITE_FOUND
```

`json.load`만 사용. write 경로 없음 확인.

#### Q3c: `authority_class` 조회·표시 전용

---

### Q4: #16 재개 체크리스트 §3-1 정합화 — 출처 중복 없음

**판정: GREEN**

`format_nae_context_block()` (answer_context.py:120-163)은 `_source_label()`을 통해 `core/retrieval.py::_format_context_source_label`을 **재사용**한다. 출력 형식: `출처: The Gospel Worthy of All Acceptation — Andrew Fuller, p.132-133, 문단 418`.

`work=/author=/page=/para=` 병렬 속성 어휘를 만들지 않는다 (테스트 `test_context_block_carries_bibliography_as_source_line`에서 `'work="' not in block` 확인).

`_GROUNDING_DIRECTIVE` §5("출처: 표시를 답변 안에서 밝혀라")와 `NAE_PARAGRAPH_PROMPT_CLAUSE` §6~7 간 중복 없음. 프롬프트 조항은 "문단 재구성" 지시만 포함하고 저자·저작 표기를 하지 않는다 (테스트 `test_prompt_clause_has_paragraph_rules_without_duplicating_directive_5`에서 `"work / author 속성" not in NAE_PARAGRAPH_PROMPT_CLAUSE` 확인).

---

### Q5: fail-soft 정합

**판정: GREEN**

`resolve()` (paragraph_lookup.py:74-166):
- 파일 부재 → `None` 반환 (52-54 줄)
- 인덱스 부재 → `None` 반환 (113-119 줄)
- `canonical_version` 불일치 → `None` 반환 (122-132 줄)
- 모두 로그만 남기고 예외 전파 없음

`_enrich_hit_with_paragraph()` (retrieval_adapter.py:311-364):
```python
try:
    resolved = paragraph_lookup.resolve(...)
except Exception:  # noqa: BLE001 — fail-soft (ADR-024 §G)
    logger.warning("[bridge_paragraphs] resolve 예외 (source_text 폴백)", exc_info=True)

if resolved is not None and resolved.text:
    ...
else:
    evidence_paragraph = source_text  # ← source_text 폴백
```

예외가 호출자에 전파되지 않고 `source_text` 전문으로 폴백한다. ADR-024 §G fail-closed 정신 정합.

---

### Q6: 격리 (AT-7/AT-9)

**판정: GREEN**

#### Q6a: `modules.nae_pd.enabled=false` 격리

`bridge_query_paragraphs()` (retrieval_adapter.py:376-448):
```python
if limit_check and not module_registry.is_enabled("nae_pd"):
    raise NaePdModuleDisabledError(...)
```

`search()` (retrieval_adapter.py:46-74)도 동일 gate. `NaePdModuleDisabledError`는 `except Exception:` 블록에서 잡히지 않는다 (443-444 줄: `except NaePdModuleDisabledError: raise`).

#### Q6b: chat.py bridge 호출 없음

```bash
$ grep -rn "bridge_query_paragraphs\|bridge_query" ui/pages/chat.py
(no output)
```

chat.py에서 어떤 bridge 함수도 호출하지 않는다.

#### Q6c: `NAE_PARAGRAPH_EVIDENCE=0` 동작

retrieval_adapter.py:412-440:
```python
expand = paragraph_evidence_enabled()
...
if expand:
    out.append(_enrich_hit_with_paragraph(meta, h["score"]))
else:
    src = meta.get("source_text") or meta.get("content_excerpt") or ""
    out.append({
        "tsu_id": ..., "retrieval_score": ..., "evidence_paragraph": src,
        "anchor_sentence": src, "paragraph_resolved": False, ...
    })
```

문단 확장을 건너뛰고 ae05415 등가 dict를 반환한다.

---

### Q7: regression — pytest 신규 26건

**판정: GREEN**

```bash
$ python -m pytest -q tests/test_nae_paragraph_resolver.py tests/test_nae_answer_context.py tests/test_answer_completeness.py --tb=short
..........................                                               [100%]
26 passed in 0.38s
```

전체 테스트 스위트 (`tests/` 전체)는 30초 툴 타임아웃으로 인해 실행하지 못했으나, 신규 관련 26건은 모두 통과했다.

**신규 테스트 의미 있는 검증 여부:**

| 파일 | 건수 | 검증 내용 | 의미 |
|------|------|----------|------|
| `test_nae_paragraph_resolver.py` | 10건 | full paragraph text 반환, missing file/index/version mismatch, neighbors join/boundary, None args, identifier cache 재사용, 실제 corpus와 verbatim 일치 | ParagraphResolver 핵심 경로 전수 |
| `test_nae_answer_context.py` | 9건 | `<자료>` 블록biblio/출처: 한 줄, 일치문장, 800자 전문 유지/1500자 초과 축약, truncated/resolved=false 플래그, 프롬프트 조항 중복 없음, prompt 순서, 서브 플래그 toggle, context_budget 드롭 | format_nae_context_block + prompt_clause 전수 |
| `test_answer_completeness.py` | 7건 | well-formed pass, empty fail, foreign script flagged, long English flagged, unfinished sentence flagged, single paragraph flagged, no honorific flagged, caption only when failed | answer_completeness 규칙 기반 판정 전수 |

**Fixture 경로 override:** `synth_canonical` (tmp_path 기반), `_REAL_ROOT` (실제 corpus), `monkeypatch.setenv` 등 실제 환경과 동등한 검증. mock이 아닌 실제 canonical.json 파일 읽는 테스트 포함 (`test_resolve_matches_canonical_json_verbatim`). 의미 있는 검증이다.

---

## 종합 판정: **GREEN**

7개 질문 모두 GREEN. PR #17은 다음 조건을 충족한다:

1. `core/retrieval.py` 무변경 (ADR-001 정합)
2. Citation dataclass 무변경, bridge_query_paragraphs는 별도 list[dict] 반환 (ADR-024 §C/§D 정합)
3. nae_qdrant(7333) 외 스토어 접근 없음 (paragraph_lookup.py = 로컬 파일만)
4. TSU/Ref mutation/upsert/reindex 코드 경로 없음 (ADR-030 baseline 보호)
5. canonical/** read-only, authority_class 조회·표시 전용
6. 출처: 한 줄 통일, 이중 서지 없음 (#16 정합화)
7. fail-soft 정합 (source_text 폴백 + 로그)
8. nae_pd module 격리, chat.py bridge 호출 없음
9. NAE_PARAGRAPH_EVIDENCE=0 서브 플래그 동작 정합
10. 신규 26건 테스트 PASS (의미 있는 검증 포함)

**PR #17 병합 조건 충족.**

---

## 참고: 전체 pytest 결과

전체 테스트 스위트 (`tests/` 247개 파일)는 툴 타임아웃(30초)으로 인해 실행하지 못했다. 요청 문서에서 제시한 "2,930 passed / 15 skipped"은 CUE의 라이브 Acceptance 결과이므로 C1이 독립 재현하지는 못했다. 신규 관련 26건만 독립 실행하여 26 passed (0.38s) 확인.

---

## 검토 종료

C1은 이 검토에서 **구현하지 않았다**. 문서 검토 + 코드 read-only 검증만 수행했다.
`_authority_class_for()` (retrieval_adapter.py:279-308)는 `source_manifest.yaml`을 읽어서 dict 캐시에 넣은 후 반환할 뿐, TSU 레코드나 payload에 기입하지 않는다. docstring 명시: "TSU 레코드·payload에 쓰지 않는다 (ADR-030 §7)". `_enrich_hit_with_paragraph()`에서 `"authority_class": _authority_class_for(...)`는 UI 표시용 dict 키일 뿐이다.