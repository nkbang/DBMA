---
title: "ADR-024: NAE Production Retrieval Bridge (Module-Gated Adapter)"
category: architecture
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-017-NAE-ID-Governance-Standard.md
  - docs/NAE_OPTIONAL_MODULE_PACKAGING_v1.md
  - .automation/requests/C1-TASK-ORDER-NAE-RETRIEVAL-BRIDGE-FEASIBILITY.md
  - .automation/requests/C1-TASK-ORDER-NAE-RETRIEVAL-BRIDGE-CLOSEOUT.md
  - .automation/audit/NAE-RETRIEVAL-BRIDGE-CUE-INDEPENDENT-AUDIT.md
  - .automation/evidence/night-shift/nae-retrieval-bridge/ (Phase 1-9 + closeout evidence)
created: 2026-08-15
scope_modified: docs/architecture/ only — 코드 미수정 (본 ADR은 설계 문서, 구현은 별도 작업 명령 필요)
---

# ADR-024: NAE Production Retrieval Bridge (Module-Gated Adapter)

| | |
|---|---|
| Status | **Approved** |
| Date | 2026-08-15 (Proposed) / 2026-08-17 (Approved) |
| Deciders | C1 Night Shift Investigation + CUE Independent Audit (2026-08-15) — 최종 승인 Rev. Bang (2026-08-17) |
| Supersedes | — |
| Superseded by | — |
| Promotion 조건 | 구현 완료 + 회귀 테스트 통과 + C1 Review 완료 + 사용자 승인 (전부 충족) |
| 구현 착수 승인 | Rev. Bang, 2026-08-15 — "C1의 NAE Production Retrieval Bridge 구현 작업 착수를 승인한다" (CUE DIRECTIVE — NAE OVERNIGHT AUTONOMOUS COMPLETION). |
| Promotion 승인 | Rev. Bang, 2026-08-17 — "ADR-024 Promotion을 실행하라" 지시에 따라 4개 조건(구현 완료/회귀 통과/C1 리뷰 완료/사용자 승인)을 CUE가 기존 증거로 재검증(신규 코드 변경 없음) 후 Approved로 승격. 근거: 커밋 `4a3e616`(구현), Phase 10 Closeout 10/10 테스트 + 5/5 production safety PASS(회귀), `.automation/audit/NAE-BRIDGE-IMPLEMENTATION-CUE-WATCH-LOG.md`(C1/CUE 검증), 재확인 시점(2026-08-17) `git status core/retrieval.py` 무수정·`NAE/retrieval_adapter.py`에 `dbma_qdrant`/`6333` 접근 코드 없음·`config.yaml`의 `modules.nae_pd.enabled: false` 기본값 유지 확인. |

---

## Context

ADR-013은 NAE Qdrant(`nae_qdrant`, 포트 7333, `nae_tsu_v1`)를 `core/retrieval.py::RetrievalEngine`의
production 경로와 완전히 분리했고, "향후 NAE corpus를 RetrievalEngine의 production 경로에
통합하려면 이 ADR을 개정하는 신규 ADR이 필요하다"고 명시했다. 이 ADR이 그 신규 ADR이다.

2026-08-15 Night Shift(C1 실행, CUE 검증)에서 다음을 **실제 코드 실행 증거**로 확인했다
(evidence: `.automation/evidence/night-shift/nae-retrieval-bridge/`):

1. **임베딩 호환성** (실측): DBMA/NAE 모두 `bge-m3:latest`, 1024차원, Cosine distance —
   완전 동일.
2. **NAE Qdrant 실측**: `nae_tsu_v1` 컬렉션, 3,319 points, vector size 1024, distance Cosine.
3. **RetrievalEngine 실측**: `core/retrieval.py::RetrievalEngine.__init__`의 `qdrant_url`/
   `collection_name` 파라미터는 저장만 되고 실제 쿼리에 쓰이지 않는다(ADR-003 정정 사항
   재확인) — RetrievalEngine은 TSU dataset + in-memory 유사도 검색만 수행한다.
4. **기존 adapter 실측**: `NAE/retrieval_adapter.py`(34줄)가 이미 존재 — `core/module_registry.py`의
   `nae_pd` 모듈 게이트로 보호되며, `config.yaml`에 `modules.nae_pd.enabled: false`(기본 비활성)
   로 확인. `RetrievalEngine`은 이 모듈을 import하지 않고, 이 모듈도 `RetrievalEngine`을
   import하지 않는다 — 양방향 완전 분리.
5. **실제 검색 실행 증거**: 3개 질의로 실제 `nae_qdrant`를 read-only 검색, 5 hits/질의,
   평균 latency 385.9ms, evidence rate 100%, production mutation 0건.
6. **Citation/Provenance round-trip 실행 증거**: NAE Qdrant payload(`tsu_id`, `source_id`,
   `work_id`, `edition_id`, `metadata_provenance` 등)를 mapping layer로 변환해
   `core/retrieval.py::CitationBuilder().build_citations()`를 **실제로 호출**, 3개의
   `Citation` 객체가 정상 반환됨을 CUE가 독립적으로 재현 확인(동일 커맨드 재실행, exit 0,
   동일 값 재현: `evidence_confidence: 0.8`, `retrieval_score: 0.5782851` 등).
   `CitationBuilder` 자체는 수정 없이 그대로 사용 가능.
7. **회귀 테스트**: `tests/test_book_alias_resolution.py`,
   `tests/test_query_enhancements_full_regression.py` 28건 전부 PASS, `core/retrieval.py`
   git diff 없음(미수정 확인).

### 확인된 제약 (숨기지 않고 명시)

- **Hybrid retrieval 비대칭**: DBMA RetrievalEngine은 Vector + BM25 + theological
  scoring(SSA/TRS/SUS) 하이브리드 랭킹을 쓰지만, NAE adapter는 **vector-only**다.
  NAE 결과에는 BM25/theological score가 적용되지 않는다. 이 ADR은 이 비대칭을
  Decision에서 명시적으로 다룬다(§Decision B 참고) — 숨기거나 나중으로 미루지 않는다.
- **Citation 필드 11개 중 6개만 NAE payload에서 직접 매핑되고, 5개(`source_title`,
  `document_id`, `evidence_confidence`, `source_file`, `language`)는 근사/대체 필드로
  채워야 한다** (실측: `.automation/evidence/night-shift/nae-retrieval-bridge/phase7/PHASE7-EVIDENCE.md`).
  기능은 하지만 완전한 1:1 매핑은 아니다.
- Embedding 경로가 Ollama를 경유해 ~300ms 오버헤드 발생 (in-memory TF-IDF fallback보다 느림).
- NAE corpus와 DBMA corpus 간 중복 제거는 검증되지 않음.

---

## Decision

### A. Integration pattern: Module-gated adapter (RetrievalEngine 비수정)

`core/retrieval.py::RetrievalEngine`을 **수정하지 않는다.** 대신 다음 구조를 채택한다:

```
UI (또는 별도 호출자)
    → module_registry.is_enabled("nae_pd") 확인 (기본 false, 명시적 opt-in 필요)
        → NAE/retrieval_adapter.py::search() [기존 함수, 이미 존재]
            → Ollama BGE-M3 embedding
            → NAE Qdrant(nae_qdrant, 7333) read-only search
            → 결과 payload
        → 신규: NAE/retrieval_adapter.py 내부에 mapping 함수 추가
          (nae payload → RankedCandidate 호환 dict, Night Shift에서 검증된
          map_nae_to_citation_metadata() 패턴을 프로덕션 함수로 승격)
        → core/retrieval.py::CitationBuilder (기존 클래스, 수정 없이 호출)
            → Citation 객체 (source_id/work_id/edition_id/tsu_id/provenance 포함)
    → 호출자(UI)가 DBMA 결과와 NAE 결과를 **별도 섹션으로 병렬 표시**
      (§Decision B에서 병합하지 않는 이유 설명)
```

이 경로는 ADR-001(RetrievalEngine 유일 정본)을 위반하지 않는다 — `RetrievalEngine`의
공개 계약이나 내부 랭킹 로직을 전혀 건드리지 않기 때문이다. ADR-003(신규 Qdrant
의존성에 신규 ADR 필요)의 요구 조건을 이 ADR 자체가 충족한다.

### B. Hybrid retrieval 비대칭 처리: 결과를 병합(merge)하지 않는다

DBMA 결과(BM25+theological+vector)와 NAE 결과(vector-only)를 **같은 순위 리스트에
병합하지 않는다.** 서로 다른 스코어링 기준으로 만들어진 점수를 하나의 랭킹에
섞으면 랭킹 품질이 왜곡된다(예: NAE 항목이 vector score만으로 DBMA의
theological-weighted 항목보다 부당하게 상위/하위로 밀릴 수 있음).

대신 **NAE corpus를 별도 결과 섹션("NAE Public Theology" 등)으로 분리 표시**한다.
사용자가 명시적으로 `nae_pd` 모듈을 활성화했을 때만 이 섹션이 나타난다.

이후 NAE에도 BM25/theological scoring을 구현해 진짜 hybrid 통합을 할지는
**별도 Architecture Decision(후속 ADR 대상)**으로 남긴다 — 이번 ADR 범위 밖.

### C. Citation 필드 완전성 및 mapping layer 정의 (§D가 참조하는 대상)

**§C가 정의하는 것**: NAE Qdrant payload(flat dict, 필드는 Context §6 참고: `tsu_id`,
`content`, `book`, `author`, `verse_mapping`, `themes`, `source_id`, `edition_id`,
`work_id`, `quality_score` 등)를 `core/retrieval.py::CitationBuilder.build_citations()`가
요구하는 `RankedCandidate.metadata` dict로 변환하는 **단일 함수**다. Night Shift
`citationbuilder-execution.py`에서 실행 검증된 `map_nae_to_citation_metadata()`가
그 참조 구현이며, 구현 시 이를 `NAE/retrieval_adapter.py`의 production 함수로
그대로 승격한다(재설계하지 않음).

**필드 매핑 (11개 중 6 직접 + 5 근사, 실측 확정)**:

| Citation 필드 | 소스 | 매핑 방식 |
|---|---|---|
| `tsu_id` | `tsu_id` | 직접 |
| `source_author` | `author` | 직접 |
| `retrieval_score` | Qdrant hit의 `score` (NAE `search()` 반환값) | 직접 — `RankedCandidate.final_score = score`로 전달, `CitationBuilder`가 이를 그대로 `retrieval_score`에 복사(코드 수정 없이 기존 동작) |
| `source_type` | `themes[0]` | 직접(첫 테마) |
| `content_excerpt` | `content[:200]` | 직접 |
| `scripture_reference` | `verse_mapping.book_id/chapter/verse_start` | `CitationBuilder` 기존 로직이 이 3개 필드로 `"{book_id} {chapter}:{verse_start}"` 형식 생성 — NAE의 book/paragraph/sentence를 그대로 book_id/chapter/verse_start에 채우면 기존 포맷 로직이 그대로 작동함(실측 확인: `"Church Order 1298:2"`) |
| `source_title` | 없음 — `f"{book} by {author}"`로 합성 | 근사 |
| `document_id` | `work_id` | 근사(대체) |
| `evidence_confidence` | `quality_score` | 근사(대체) |
| `source_file` | `source_id` | 근사(대체) |
| `language` | `source_text.isascii()` 휴리스틱 | 근사(추론) |

근사 매핑임을 UI에서 숨기지 않는다 — 예: `source_title`이 NAE에는 없어 합성됨을
표시 시 구분 가능하게 한다(구체적 UI 표기는 구현 작업 명령에서 정한다).

**필드 정확성 검증 기준**: §J-4에서 "Citation 리스트 반환"만으로는 부족하다 —
반환된 각 `Citation` 객체에 대해 위 표의 6개 직접 매핑 필드가 소스 payload와
정확히 일치하는지(`tsu_id`, `source_author`, `retrieval_score`, `source_type`,
`content_excerpt`, `scripture_reference` 각각 assert)까지 실행 검증에 포함한다.

### D. `bridge_query()` contract

`NAE/retrieval_adapter.py`에 기존 `search()`(query_vector 입력, raw Qdrant hit 반환)와는
별개로, DBMA 호출자가 쓰는 신규 함수를 추가한다 — 기존 `search()`는 수정하지 않는다:

```python
def bridge_query(
    query_text: str,
    *,
    top_k: int = 10,
    limit_check: bool = True,
) -> list[Citation]:
    """query_text(자연어) → embedding → NAE Qdrant search → Citation 리스트.

    module gate(limit_check)를 통과하지 못하면 NaePdModuleDisabledError.
    Qdrant/Ollama 장애 시 §G(fail-closed)에 따라 빈 리스트 반환, 예외를
    호출자까지 전파하지 않는다(단, module-disabled 예외는 예외로 남긴다 —
    이건 설정 오류이지 런타임 장애가 아니므로 호출자가 알아야 한다).
    """
```

입력은 벡터가 아니라 텍스트로 받는다 — embedding 책임을 adapter 내부에 캡슐화해
호출자(UI)가 embedding 모델을 알 필요가 없게 한다. 반환 타입은 `core/retrieval.py::Citation`
그대로 사용 — §C의 mapping layer를 내부에서 호출한 결과.

**명시적 의존성**: `NAE/retrieval_adapter.py`는 `bridge_query()` 구현을 위해
`core/retrieval.py`에서 `CitationBuilder`와 `RankedCandidate`를 **import해야 한다**
(단방향 — `core/retrieval.py`는 여전히 `NAE/`를 import하지 않는다, §A의 "양방향
분리"는 "NAE가 core를 읽기 전용으로 import하는 것"까지 막지 않는다. 이는 ADR-001이
금지하는 "병행 검색 경로 생성"이 아니라 기존 정본 클래스의 재사용이다). 내부 흐름:

**Embedding 함수 명시** (C1 재검토에서 확인된 gap — "기존 경로 재사용"만으로는
불충분했음): `NAE/pipeline/embed/client.py::embed_text(text, *, content_hash, model=...)`를
재사용한다 — 새 embedding 경로를 만들지 않는다. 단, 이 함수는 **예외를 던지지 않고
실패 시 `None`을 반환**한다(내부에서 이미 `except Exception: return None` 처리,
로그만 남김) — §G의 "예외 catch"만으로는 이 실패를 잡을 수 없다는 뜻이므로, `bridge_query()`는
`None` 반환도 명시적으로 확인해야 한다(아래 코드 참고). `content_hash`는 질의
캐싱을 위해 `hashlib.sha256(query_text.encode()).hexdigest()`로 생성한다(문서
청크가 아닌 사용자 질의이므로 캐시 키를 질의 텍스트 자체로 정의).

```python
def bridge_query(query_text: str, *, top_k: int = 10, limit_check: bool = True) -> list[Citation]:
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError(...)
    try:
        content_hash = hashlib.sha256(query_text.encode()).hexdigest()
        vector = embed_text(query_text, content_hash=content_hash)  # NAE/pipeline/embed/client.py 재사용
        if vector is None:  # embed_text는 예외 대신 None을 반환 — 명시적으로 확인 필요
            return []
        hits = search(vector, top_k=top_k, limit_check=False)  # 기존 search(), 이미 module gate 통과함
        candidates = [
            RankedCandidate(
                tsu_id=h["tsu_id"], content=h["content"],
                metadata=map_nae_to_citation_metadata(h),  # §C
                vector_score=h["score"], bm25_score=0.0, theological_score=0.0,
                passage_score=0.0, final_score=h["score"],
                explanation=f"NAE Qdrant vector search (score={h['score']:.4f})",
            )
            for h in hits
        ]
        return CitationBuilder().build_citations(candidates)  # core/retrieval.py, 수정 없이 호출
    except NaePdModuleDisabledError:
        raise
    except Exception:  # Qdrant/Ollama 장애 — §G fail-closed
        return []
```

### E. UI integration point

`ui/pages/research.py`(ADR-001이 명시한 현재 `RetrievalEngine` 소비처)를 **수정하지 않는다.**
대신 신규 UI 요소(탭 또는 접이식 섹션, 예: "NAE Public Theology (Beta)")를 추가하고,
그 요소에서만 `bridge_query()`를 호출한다. `nae_pd`가 비활성 상태면 이 UI 요소 자체를
숨긴다(§F). 정확한 배치(탭 vs 섹션)는 구현 작업 명령에서 결정 — 이 ADR은 "기존 DBMA
결과 흐름과 분리된 위치에서만 노출한다"는 제약만 고정한다.

### F. Module gating (opt-in 재확인)

`config.yaml`의 `modules.nae_pd.enabled`(기본값 `false`)가 유일한 진입 스위치다.
`core/module_registry.py::is_enabled("nae_pd")`가 `false`를 반환하면:
- `bridge_query()`는 `NaePdModuleDisabledError`를 던진다(기존 `search()`와 동일 동작 유지).
- UI 요소는 렌더링하지 않는다.

이 스위치 하나로 전체 bridge를 완전히 끌 수 있어야 한다 — 별도의 두 번째 스위치를
만들지 않는다(§I 참고).

### G. Error / timeout / fail-closed behavior

- **현재 `search()`는 예외를 전파한다** (실측: `NAE/retrieval_adapter.py`, Qdrant client
  에러를 그대로 raise) — `bridge_query()`가 이를 **명시적으로 catch**해야 한다(§D 코드
  참고: `except Exception: return []`). `search()` 자체는 수정하지 않는다 — 예외를
  삼키는 책임은 새 함수 `bridge_query()`의 wrapper 로직에만 둔다.
- **Qdrant 연결 실패, timeout, embedding 실패**: `bridge_query()`는 예외를 호출자에
  전파하지 않고 빈 리스트(`[]`)를 반환한다 — UI는 "NAE 결과 없음"으로 표시하며,
  DBMA 자체 검색 결과 표시는 이 실패로 영향받지 않는다(fail-closed, DBMA 경로 격리 유지).
- **Timeout/성능 허용 기준** (Night Shift 실측 기반, 구체적 수치로 고정):
  - 실측 평균 latency 385.9ms(embed ~300ms + Qdrant ~18-25ms), 실측 최대 946.5ms.
  - **Warn threshold**: 1,500ms 초과 시 로그에 경고 기록(기능은 계속 반환).
  - **Hard timeout**: 3,000ms — 이 시점까지 응답이 없으면 요청을 취소하고 빈 리스트
    반환(§G 1번과 동일 처리). Qdrant client의 timeout 파라미터로 구현.
  - 이 수치는 구현 후 실측으로 재조정 가능 — 이 ADR은 "명시적 수치가 존재해야 한다"는
    요건만 고정하고, 정확한 값은 구현 작업 명령에서 최초 배포 전 벤치마크로 확정한다.
- **Module-disabled 예외만은 그대로 전파**한다(§D) — 이는 설정 문제이며 UI가
  이 상태를 구분해서 "비활성화됨" 안내를 보여줘야 하기 때문이다.
- 이 오류 처리 전부는 `NAE/retrieval_adapter.py` 내부에 국한된다 — `core/retrieval.py`는
  이 실패를 알지도, 처리하지도 않는다(RetrievalEngine 경로와 완전 분리 유지).

### H. DBMA/NAE corpus isolation (재확인)

§F/§A의 module gate와 §B의 "결과 병합 금지"가 격리의 두 축이다. 추가로:
- `bridge_query()`는 `nae_qdrant`(7333)만 접근한다 — `dbma_qdrant`(6333) 접근 코드를
  포함하지 않는다(구현 시 코드 리뷰에서 확인).
- NAE 결과에는 출처가 NAE corpus임을 나타내는 명시적 배지/라벨을 UI에서 표시한다
  (DBMA corpus 결과와 시각적으로 혼동되지 않게).

**중복 제거(dedup) 정책 — 명시적으로 없음**: 이 ADR은 NAE corpus와 DBMA corpus
간 콘텐츠 중복 제거를 **수행하지 않는다.** §B가 이미 두 결과셋을 병합하지 않고
별도 섹션으로 분리 표시하기로 결정했으므로, 같은 원문이 양쪽에 다르게 청킹되어
존재하더라도 사용자에게는 "DBMA 섹션 결과"와 "NAE 섹션 결과"로 각각 그대로
보여준다 — 이것이 이번 ADR의 명시적 정책이다("정의 안 됨"이 아니라 "의도적으로
dedup 없음"). 두 corpus의 실제 콘텐츠 중복도를 측정해 dedup이 필요한지 판단하는
것은 이번 범위 밖이며, 필요성이 확인되면 별도 ADR 대상이다.

### I. Enable/disable 및 rollback

- **Enable**: `config.yaml`의 `modules.nae_pd.enabled: true`로 전환 — 코드 배포와
  분리된 설정 변경만으로 가능.
- **Disable/rollback**: 같은 값을 `false`로 되돌리면 즉시 비활성화 — 코드 롤백이나
  재배포 불필요. 이것이 module-gated adapter 패턴을 선택한 핵심 이유 중 하나다:
  문제 발생 시 config 값 하나로 즉시 차단 가능하다.
- 코드 레벨 rollback이 필요한 경우(예: `bridge_query()` 자체에 결함)도 `NAE/retrieval_adapter.py`
  단일 파일 revert로 충분 — `core/retrieval.py`가 이 파일을 import하지 않으므로
  DBMA production 경로에 연쇄 영향 없음.

### J. Regression / acceptance criteria (구현 완료 판정 기준)

구현이 다음을 **전부** 만족해야 "구현 완료"로 인정하고 Promotion 조건(§Status 표)의
첫 항목을 충족한 것으로 본다:

1. `git diff core/retrieval.py` — 빈 결과 (무수정)
2. `tests/test_book_alias_resolution.py`, `tests/test_query_enhancements_full_regression.py` — 전부 PASS (구현 전후 동일 결과)
3. `modules.nae_pd.enabled: false`(기본값) 상태에서 신규 UI 요소가 렌더링되지 않음을 확인
4. `modules.nae_pd.enabled: true` 상태에서 실제 질의 → `bridge_query()` → `Citation` 리스트 반환까지 실제 실행 증거(§Evidence Index 방식과 동일하게 stdout/JSON 캡처, 서술적 설명 아님).
   **주의**: 4~5번은 `bridge_query()`가 구현된 이후에만 실행 가능한 기준이다 — 이 ADR
   승인 시점에는 "무엇을 어떻게 검증할지"만 확정하고, 실제 PASS/FAIL 판정은 구현
   작업 완료 후 별도로 수행한다.
5. NAE Qdrant 강제 차단(예: 컨테이너 정지) 상태에서 `bridge_query()`가 예외를 전파하지 않고
   빈 리스트를 반환하며 DBMA 자체 검색은 정상 동작함을 실행으로 확인(§G fail-closed 검증,
   §G에서 명시한 `except Exception: return []`가 실제로 이 경로를 타는지 확인)
6. `dbma_qdrant`(6333) 접근 코드가 `NAE/retrieval_adapter.py`에 없음을 grep으로 확인
7. **Citation 필드 정확성**: §C 표의 6개 직접 매핑 필드(`tsu_id`, `source_author`,
   `retrieval_score`, `source_type`, `content_excerpt`, `scripture_reference`)가
   반환된 각 `Citation` 객체에서 소스 NAE payload 값과 정확히 일치하는지 실행 결과로
   assert — 값이 채워졌다는 것만으로는 불충분, 값이 올바른지까지 확인
8. **성능 허용 기준**: §G의 warn threshold(1,500ms)/hard timeout(3,000ms)이 실제
   Qdrant client 설정에 반영되어 있는지 코드 확인 + 정상 상태에서 실제 질의 latency가
   Night Shift 실측 범위(평균 ~386ms, 최대 ~950ms)와 같은 자릿수인지 실행 확인

---

## Consequences

**긍정적**:
- `core/retrieval.py` production 경로 무변경 — ADR-001 authority 유지.
- NAE corpus가 DBMA corpus와 격리된 채로 opt-in 검색 가능 — ADR-013 격리 원칙 유지.
- 기존 회귀 테스트 전부 무영향(실측 확인).
- Citation/Provenance 최소 요건 충족 — 근사 매핑이지만 출처 추적 가능.

**제약/후속 과제**:
- NAE 결과는 DBMA의 theological scoring 혜택을 받지 못한다 — 검색 품질이
  DBMA corpus보다 단순함. 사용자에게 "다른 corpus, 다른 스코어링"임을
  UI에서 명확히 해야 한다.
- Citation 5개 필드가 근사값 — 완전한 provenance 정합성을 원하면 NAE
  metadata 스키마 자체를 확장하는 후속 작업이 필요하다(이 ADR 범위 밖).
- `nae_pd` 모듈 활성화(`config.yaml`) 및 UI 통합(신규 탭/버튼)은 이 ADR
  승인 후 별도 구현 작업 명령으로 진행한다 — 이 ADR 자체는 설계만 정의한다.
- 중복 제거(dedup)는 §H에서 "의도적으로 수행하지 않음"으로 확정(미정 아님) — 필요성이
  나중에 확인되면 별도 ADR 대상.

### C1 2차 검토(2026-08-15) 결과 — CUE 재확인

C1이 §C/§D/§G/§H/§J 개정본을 검토해 9개 gap 중 8개는 해소로 판정, 1개(§D
`RankedCandidate.bm25_score/theological_score` 처리 방식)는 **CUE가 코드 직접
확인 결과 근거 없음으로 기각** — `CitationBuilder.build_citations()`는 `final_score`만
읽고 `bm25_score`/`theological_score`는 전혀 참조하지 않는다(실측:
`core/retrieval.py:1843-1874`).

C1이 지적한 진짜 gap 1건(`embed()` 함수가 실제로는 예외가 아니라 `None`을 반환)은
§D/§G에 반영해 해소했다(`NAE/pipeline/embed/client.py::embed_text()` 명시,
`None` 반환 명시적 확인 추가).

**이 ADR 범위에서 의도적으로 구현 작업 명령으로 미룬 나머지 3개**(Architecture
Decision이 아니라 구현 세부사항으로 판단):
1. NAE payload 스키마 drift 시 mapping layer fallback (§C) — corpus ingestion이
   실제로 스키마를 바꿀 때 대응, 지금은 발생하지 않은 가상 시나리오.
2. Warn threshold(1,500ms) 로깅 메커니즘 구체적 구현(§G) — `logging` 표준 사용
   여부는 코드 스타일 문제.
3. §J-4 테스트 질의/JSON 스키마 구체화, §J-8 latency baseline을 구현 시점 값으로
   갱신 — 실행 시점에만 확정 가능.

## Compliance

- **ADR-001**: 무영향 — `RetrievalEngine` 공개 계약/내부 로직 수정 없음(git diff 확인됨).
- **ADR-003**: 본 ADR이 그 자체로 "NAE Qdrant를 production에 연결하는 신규 ADR"
  요건을 충족한다. Legacy Chroma/Qdrant(`dbma_qdrant`, 6333)는 여전히 미접근.
- **ADR-013**: NAE Qdrant 격리 원칙 유지 — `nae_qdrant`/`nae_tsu_v1`만 사용,
  기존 legacy 컨테이너/볼륨/컬렉션 무영향. 통합은 opt-in 모듈 게이트를 통해서만.
- **ADR-017**: NAE payload의 `source_id`/`work_id`/`edition_id`가 ADR-017
  canonical ID 규칙을 그대로 따름을 실측 확인 — 별도 변환 불필요.

## Validation

구현 후 확인해야 할 것(구현 작업 명령서에서 구체화):

```
config.yaml: modules.nae_pd.enabled 값에 따라 UI 섹션 노출/비노출 확인
core/retrieval.py: git diff 없음 확인 (매 구현 커밋마다)
tests/test_book_alias_resolution.py, tests/test_query_enhancements_full_regression.py: PASS 유지
NAE/retrieval_adapter.py 신규 mapping 함수: CitationBuilder 실제 호출 → Citation 객체 반환 확인
```

## Evidence Index

- `.automation/evidence/night-shift/nae-retrieval-bridge/` — Phase 1-9 전체 조사 evidence
- `.automation/evidence/night-shift/nae-retrieval-bridge/nae_bridge_probe_evidence.json` — 실제 검색 실행 원본
- `.automation/evidence/night-shift/nae-retrieval-bridge/phase7/PHASE7-EVIDENCE.md` — Citation 매핑 상세
- `.automation/evidence/night-shift/nae-retrieval-bridge/prototype/citationbuilder-execution.py` — CUE가 직접 재실행하여 재현 확인한 스크립트
- `.automation/audit/NAE-RETRIEVAL-BRIDGE-CUE-INDEPENDENT-AUDIT.md` — CUE 1차 독립 감사
