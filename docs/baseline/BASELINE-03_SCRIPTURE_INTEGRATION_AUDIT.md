# BASELINE-03 — Scripture Corpus Integration Architecture Audit

STATUS: COMPLETE

## 1. TSU Schema

### A. 실제 record field 목록 (E1 — output/bench/tsu_dataset.jsonl Record 0~4 직접 확인)

```
tsu_id          str   "TSU-{book_id}-{chunk_id}"
document_id     str   document_identity hash
chunk_id        str   chunk identity hash
content         str   chunk text
verse_mapping   dict  {"book_id": str|None, "chapter": int|None, "verse_start": int|None, "verse_end": int|None}
themes          list  []
title           str   document title
author          str   document author
metadata_source str   "sidecar" 등
chapter         int|None  document-level chapter (registry에서 온 것, chunk와 무관)
page            int|None
source_file     str   원본 파일명
language        str   "en"|"ko"
source_type     str   "txt"|"pdf" 등
provenance      dict|None  {"resolver": "scripture_evidence_resolver_v1", ...}
content_quality dict  {"noise_type", "quality_score", "section_type"}
structure       dict  {"heading_path", "heading_depth", "heading_confidence", "heading_source"}
theological_claim None
doctrine_category []
baptist_theme   []
```

**총 23개 field** (verse_mapping 내부 4개 포함 시 27개).

### B. TSU ID 형식 (E1)

```
TSU-{book_id}-{chunk_id}
예: TSU-UNK-1bf5653a9316d384917176fd49daee41_chunk_00000
```

book_id가 "UNK"인 것은 filename에서 book을 resolution 못 한 경우. Scripture corpus에서는 `TSU-BIBLE-{book_id}-{chapter}-{verse}-{chunk_id}` 또는 기존 chunk_id 기반 형식 유지 가능.

### C. text/content field (E1)

`content` — chunk의 원문 텍스트. Scripture corpus에서도 동일 필드 사용 가능.

### D. source_file / source/document/title (E1)

`source_file`, `title`, `author` — 모두 document-level metadata. Scripture corpus에서는 source_file="KJV_NASB_parallel.txt", title="Holy Bible (KJV/NASB)" 등 사용 가능.

### E. language (E1)

`language: "en"` 또는 `"ko"`. Scripture corpus는 multilingual 지원 필요 시 각 chunk에 개별 language 필드 설정.

### F. doc_type (E3 — 현재 TSU schema에 doc_type field 없음)

현재 TSU record에 `doc_type` field는 **존재하지 않음**. commentary/sermon vs scripture를 구별하려면 새 field 추가 필요 또는 `source_file` 패턴으로 판별.

### G. book_id (E1/E2)

**핵심 발견:** `book_id`는 TSU record의 **top-level field가 아님**. `verse_mapping.book_id`에 들어감.

```python
# tsu_builder.py L330-354
if book_id != "UNK":
    verse_mapping["book_id"] = book_id
    ref, provenance = _resolve_evidence(content, book_id)
    if ref is not None and ref.book_id == book_id:
        verse_mapping["chapter"] = ref.chapter
        if ref.verse_start and ref.verse_start > 0:
            verse_mapping["verse_start"] = ref.verse_start
            if ref.verse_end is not None:
                verse_mapping["verse_end"] = ref.verse_end
```

**`book_id=None`이 schema limitation이 아님:** verse_mapping은 TSU schema의 **확장 지점(extension point)**으로 설계됨. 현재 `None`인 이유는 corpus에 Scripture text가 없어서 `_resolve_evidence()`가 참조를 못 찾기 때문.

### H. chapter / verse field (E1)

top-level `chapter`은 document-level metadata (registry에서 온 것). chunk-level chapter/verse는 **오직** `verse_mapping` 내부에 저장됨.

### I. provenance field (E1)

`provenance` dict: `{"resolver": "scripture_evidence_resolver_v1", "confidence": float, "candidate_count": int, "selected_reason": list[str]}`. Scripture corpus에서도 동일 구조 사용 가능.

### TSU Schema 판정

| 질문 | 답 | Evidence Level |
|------|-----|----------------|
| Scripture를 현재 TSU와 동일한 단위로 표현 가능한가? | **예** — content, verse_mapping, language, source_file 등 모든 필드 호환 | E3 |
| 현재 schema에 book/chapter/verse를 넣을 field가 이미 있는가? | **예** — `verse_mapping` (book_id, chapter, verse_start, verse_end) | E1 |
| 없다면 어떤 기존 extension point가 있는가? | `verse_mapping`, `provenance`, `raw_metadata` (Evidence layer) | E1 |
| `book_id=None`이 schema limitation인가 corpus metadata 부재인가? | **corpus metadata 부재** — schema는 이미 verse_mapping으로 설계됨 | E2 |

## 2. Evidence Schema

### A. Evidence의 source/type/metadata contract (E1 — core/evidence_model.py 직접 확인)

```python
@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    corpus_type: str          # "default" | "personal" | future-proof
    text: str
    source_type: Optional[str]
    source_file: Optional[str]
    document_id: Optional[str]
    document_title: Optional[str]
    chunk_id: Optional[str]
    retrieval_query: Optional[str]
    retrieval_method: Optional[str]
    retrieval_score: float
    bm25_score: float
    theological_score: Optional[float]
    passage_score: Optional[float]
    final_score: float
    provenance: EvidenceProvenance
    raw_metadata: dict[str, Any]  # FULL TSU record preserved
```

### B. provenance 저장 방식 (E1)

`EvidenceProvenance`: source_file, document_id, chunk_id, source_type, metadata_source, nae_metadata, source_provenance, content_quality, structure. **실제 값만 보존 — fake 생성 없음.**

### C. source reference 저장 방식 (E1)

`raw_metadata`에 **원본 TSU record 전체**가 복사됨. 따라서 `verse_mapping.book_id`, `verse_mapping.chapter`, `verse_mapping.verse_start`, `verse_mapping.verse_end`가 그대로 보존됨.

### D. evidence ID contract (E1)

TSUEvidenceAdapter._resolve_evidence_id():
1. tsu_id (if non-empty)
2. source_file + document_id + chunk_id hash
3. document_id alone
4. chunk_id alone

Scripture corpus에서도 동일한 tsu_id 형식을 쓰면 자동 호환.

### E. citation 연결 방식 (E1 — core/grounded_citation.py)

CitationCheckResult: claim_id, evidence_id, id_exists, span_found_in_text, provenance_traceable. Evidence.has_provenance로 출처 추적 가능 여부 판정.

### F. Scripture-specific metadata extension point (E3)

`raw_metadata["verse_mapping"]`이 이미 book/chapter/verse를 보존하는 extension point. 추가적으로 `corpus_type`을 "bible"로 설정하면 commentary와 구별 가능.

### G. commentary/sermon vs Scripture evidence 구별 (E3)

현재: `corpus_type == "default"`인 모든 evidence가 동일하게 처리됨.
구별 방법: `raw_metadata["verse_mapping"]["book_id"]`가 None이 아니면 Scripture, 아니면 commentary. 또는 `corpus_type`을 "bible"로 설정.

### Evidence Schema 판정

| 질문 | 답 | Evidence Level |
|------|-----|----------------|
| Scripture를 기존 Evidence model에 넣을 수 있는가? | **예** — raw_metadata가 verse_mapping 보존, corpus_type으로 구별 가능 | E3 |
| evidence_type 또는 equivalent discriminator가 존재하는가? | **예** — `corpus_type` field ("default"|"personal"|future) | E1 |
| book/chapter/verse를 metadata로 보존할 수 있는가? | **예** — raw_metadata["verse_mapping"]에 이미 저장됨 | E1 |
| citation verifier가 Scripture reference를 그대로 보존할 수 있는가? | **예** — has_provenance + raw_metadata 접근 가능 | E3 |

## 3. Tantivy Schema

### 실제 스키마 (E1 — core/candidate_generator.py L123-141 직접 확인)

```python
# Text fields (stored, default tokenizer)
"title"        stored=True
"content"      stored=True
"author"       stored=True

# Search-only fields (not stored, kiwi morpheme pre-segmented)
"title_search"  stored=False
"content_search" stored=False
"author_search" stored=False

# Raw tokenizer fields (stored, exact-match term filter)
"tsu_id"       stored=True, tokenizer_name="raw"
"document_id"  stored=True, tokenizer_name="raw"
"source_file"  stored=True, tokenizer_name="raw"
"book_id"      stored=True, tokenizer_name="raw"   <-- 이미 존재!
"language"     stored=True, tokenizer_name="raw"

# Integer field (stored)
"page"         stored=True
```

### _tsu_to_tantivy_doc 매핑 (E1 — L144-158)

```python
doc.add_text("book_id", (tsu.get("verse_mapping") or {}).get("book_id") or "")
```

**book_id는 이미 Tantivy schema에 있고, verse_mapping.book_id에서 읽어옴.**

### Tantivy Schema 판정

| 질문 | 답 | Evidence Level |
|------|-----|----------------|
| 현재 schema에 Scripture metadata를 저장할 field가 이미 있는가? | **예** — book_id, language, tsu_id, document_id, source_file 모두 이미 존재 | E1 |
| 기존 schema를 변경하지 않고 Scripture를 추가할 수 있는가? | **예** — verse_mapping.book_id가 채워지면 자동으로 인덱싱됨 | E3 |
| schema 변경이 필요하다면 정확히 어느 field가 필요한가? | **불필요** — 현재 schema로 충분 | E3 |
| 기존 index와 Scripture를 하나의 index에 넣는 구조가 가능한가? | **예** — book_id term filter로 구별 가능 | E3 |
| 별도 Scripture index가 가능한 구조인가? | **예** — tsu_id prefix나 source_file pattern으로 분리 가능 | E3 |

## 4. Retrieval Path

### 실제 경로 추적 (E1 — core/hybrid_candidate_pipeline.py 직접 확인)

```
RAW QUERY
  -> HybridQueryProcessor.process()
    -> QueryPlan.classify(query_text, parsed_query)   # Stage 0
      -> "bible" route if parsed_query.scripture_refs exists
      -> "hybrid" route otherwise
    -> _generate_candidates(parsed_query, ...)         # Stage 1
      -> bible route: self.bible_index.lookup_scripture_ref(ref)
      -> hybrid route: self.candidate_generator.search(...)
    -> Stage 2 scoring (reused from RetrievalEngine)
      -> compute_theological_score()
      -> compute_passage_match_score()
      -> compute_content_quality_factor()
    -> merge candidates (RRF if multiple routes)
    -> Evidence assembly (TSUEvidenceAdapter)
```

### detected_books 생성 위치 (E1)

`core/retrieval.py::QueryParser.parse()` L429: `standalone_books = self._detect_books_standalone(query)`
`core/query_enhancements.py::EnhancedQueryParser.parse()` L654-670: chapter-only refs 추가

### scripture_refs 생성 위치 (E1)

`core/retrieval.py::QueryParser._extract_scripture_refs()` L495-566:
- Pattern 1: Full book name + chapter:verse (e.g., "Romans 5:3")
- Pattern 2: Abbreviated book name + chapter:verse (e.g., "롬 5:3", "요3:16")

### book/chapter/verse 전달 경로 (E3)

1. QueryParser -> ParsedQuery.scripture_refs (ScriptureReference 객체)
2. HybridRetriever._generate_candidates() -> BibleIndex.lookup_scripture_ref(ref)
3. BibleIndex -> tsu_id list 반환
4. TSUEvidenceAdapter.adapt(tsu_record) -> Evidence.raw_metadata["verse_mapping"] 보존
5. CitationBuilder -> evidence_id로 citation 연결

### RankedCandidate metadata 보존 (E1)

```python
@dataclass
class RankedCandidate:
    tsu_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)  # TSU record fields 포함 가능
    ...
```

metadata dict에 TSU record의 모든 필드가 포함되므로 verse_mapping 보존 가능.

### Scripture integration 방식 비교 (E3)

| 방식 | 현재 code 연결점 | 장단점 |
|------|-----------------|--------|
| A. 동일 corpus 포함 | tsu_dataset.jsonl에 추가, build_index() 자동 인덱싱 | 가장 단순. Bible Index도 자동 업데이트 |
| B. 별도 Scripture path | BibleIndex + 새로운 index 필요 | 복잡도 증가. 현재 architecture에는 불필요 |
| C. deterministic lookup + semantic 병행 | BibleIndex.lookup_scripture_ref() 이미 구현됨 | **현재 이미 구현된 경로** |

**결론:** 현재 code 구조상 방식 A (동일 corpus)가 가장 자연스럽게 연결됨. Bible Index는 이미 TSU dataset에서 빌드되며, HybridRetriever는 bible_index parameter로 받음.

## 5. Scripture Reference Lookup

### 실제 reference 처리 확인 (E1/E2)

| Reference | book code normalization | chapter parsing | verse parsing | verse range | normalized repr | exact lookup |
|-----------|------------------------|-----------------|---------------|-------------|-----------------|--------------|
| GEN 2:1-3 | NAME_TO_BOOK_ID["genesis"] -> "GEN" | \d+ 매칭 | \d+ 매칭 | (?:-(\d+))? | ScriptureReference("GEN", 2, 1, 3) | BibleIndex keys_for_scripture_ref() |
| EXO 20:8-11 | NAME_TO_BOOK_ID["exodus"] -> "EXO" | 동일 | 동일 | 동일 | 동일 | 동일 |
| DEU 5:12-15 | NAME_TO_BOOK_ID["deuteronomy"] -> "DEU" | 동일 | 동일 | 동일 | 동일 | 동일 |
| MAT 12:1-8 | NAME_TO_BOOK_ID["matthew"] -> "MAT" | 동일 | 동일 | 동일 | 동일 | 동일 |
| MRK 2:23-28 | NAME_TO_BOOK_ID["mark"] -> "MRK" | 동일 | 동일 | 동일 | 동일 | 동일 |
| LUK 6:1-5 | NAME_TO_BOOK_ID["luke"] -> "LUK" | 동일 | 동일 | 동일 | 동일 | 동일 |
| HEB 4:1-11 | NAME_TO_BOOK_ID["hebrews"] -> "HEB" | 동일 | 동일 | 동일 | 동일 | 동일 |

### HEB 4 (chapter-only) 문제 확인 (E2)

**Base QueryParser:** `_extract_scripture_refs()`는 `(\d+):(\d+)` 패턴만 지원. "HEB 4"는 colon이 없으므로 **감지 안 됨**.

**EnhancedQueryParser:** `parse_chapter_only()`가 "HEB 4" 또는 "히 4장" 형식을 감지함. verse_start=0 (no verse specified sentinel).

**Bible Index lookup:** verse_start=0일 때 `keys_for_scripture_ref()`는 verse-level key를 생성하지 않고 chapter-level key만 사용. BibleIndex.lookup_scripture_ref()가 chapter fallback을 지원하므로 **작동함**.

### "HEB 4:0" 문제 확인 (E3)

ScriptureReference.verse_start=0은 "no verse specified" sentinel. Bible Index lookup에서 verse_start=0이면 verse-level key를 건너뛰고 chapter-level로 fallback. **현재 코드에서 문제 없음** — 다만 verse_mapping에 verse_start=0이 저장되면 TSU record가 "verse 0"으로 오해받을 수 있음 (tsu_builder.py L351: `if ref.verse_start and ref.verse_start > 0` 게이트가 이를 방지).

### Scripture Reference Lookup 판정

| 질문 | 답 | Evidence Level |
|------|-----|----------------|
| book code normalization | NAME_TO_BOOK_ID 매핑으로 처리 | E1 |
| chapter parsing | \d+ 매칭 (Pattern 1/2) 또는 EnhancedReferenceParser | E1 |
| verse parsing | \d+ 매칭 (Pattern 1/2) | E1 |
| verse range parsing | (?:-(\d+))? 매칭 | E1 |
| normalized reference representation | ScriptureReference(book_id, chapter, verse_start, verse_end) | E1 |
| exact lookup 가능 여부 | BibleIndex.lookup_scripture_ref()로 O(1)ish lookup | E1 |
| candidate generation에 reference 전달 | HybridRetriever._generate_candidates()에서 bible_index.lookup_scripture_ref(ref) | E1 |
| retrieval 이후 citation 복원 | Evidence.raw_metadata["verse_mapping"] 보존 -> CitationBuilder 사용 | E3 |

## 6. Multilingual Capability

### translation field 존재 여부 (E4)

현재 TSU schema에 `translation` field는 **없음**. Scripture corpus에서 parallel translation (KJV/NASB/개역개정 등)을 구분하려면 추가 필요.

### language field (E1)

`language: "en"` 또는 `"ko"`. Tantivy schema에 raw tokenizer로 인덱싱됨. BGE-M3 multilingual embedding과 호환.

### 같은 verse의 여러 translation을 동일 reference로 묶을 수 있는 구조 (E3)

현재: 아님. 각 chunk가 독립된 TSU record이므로, 같은 verse의 다른 translation은 별도 tsu_id를 가짐.
구별 방법: `raw_metadata["translation"]` field 추가 또는 tsu_id 패턴 (예: `TSU-BIBLE-ROM-5-3-KJV`, `TSU-BIBLE-ROM-5-3-NASB`).

### citation/provenance가 translation까지 보존되는지 (E4)

현재 corpus에 Scripture text가 없으므로 미검증. 하지만 raw_metadata가 전체 TSU record를 복사하므로, translation field가 TSU record에 있으면 자동 보존됨.

### BGE-M3 multilingual embedding 호환성 (E3)

BGE-M3은 다국어 임베딩 모델로, 한국어/영어 chunk가 모두 동일한 vector space에 매핑됨. Tantivy BM25는 언어와 무관하게 작동하므로 multilingual corpus 추가 시 별도 조정 불필요.

## 7. Q3/Q4 Query Expansion

### Q3: "복음서에서 예수님은 안식일에 대해 무엇을 가르치셨는가?"

**문제:** "복음서"가 MAT/MRK/LUK/JHN으로 확장되지 않음.

**확장 지점 (E1):** `core/retrieval.py::BOOK_ID_TO_NAMES`에 "복음서" -> ["matthew", "mark", "luke", "john"] 또는 별도 mapping 추가 필요.

현재 BOOK_ID_TO_NAMES의 Gospel entries:
```python
"MAT": ["matthew", "matt", "mt", "mat", "마태복음", "마태", "마"],
"MRK": ["mark", "mk", "mrk", "마가복음", "마가", "막"],
"LUK": ["luke", "lk", "luk", "누가복음", "눅"],
"JHN": ["john", "jn", "jhn", "요한복음", "요한", "요"],
```

"복음서"는 어느 book_id의 names list에도 없음. `_detect_books_standalone()`이 longest-match로 alias를 찾는데, "복음서"가 매칭되지 않으므로 detected_books에 포함 안 됨.

### Q4: "사도들은 안식일을 어떻게 이해하고 가르쳤는가?"

**문제:** "사도"가 ACT로 확장되지 않음.

**확장 지점 (E1):** `core/retrieval.py::BOOK_ID_TO_NAMES`의 ACT entry에 "사도" 추가 필요.

현재:
```python
"ACT": ["acts", "act", "사도행전", "행"],
```

"사도"만으로는 ACT를 uniquely 매칭할 수 없음 (다른 책에도 "사도"가 포함될 수 있음). "사도행전"은 이미 있음. "사도들"도 추가 가능하지만 unique 매칭 보장 필요.

### Q3/Q4 Query Expansion 판정

| 질문 | 답 | Evidence Level |
|------|-----|----------------|
| `복음서`를 MAT/MRK/LUK/JHN으로 확장할 extension point? | BOOK_ID_TO_NAMES에 "복음서" alias 추가 (다중 book_id 매핑 필요) | E1 |
| `사도/사도들`을 ACT로 확장할 extension point? | BOOK_ID_TO_NAMES["ACT"]에 "사도", "사도들" 추가 | E1 |
| query_translation.py 확장 지점? | KO_EN_THEOLOGY_TERMS에 추가 가능 (하지만 book alias 아님) | E1 |
| EnhancedQueryParser 확장 지점? | _detect_books_standalone()의 alias cache가 BOOK_ID_TO_NAMES에서 빌드 | E1 |

## 8. A/B/C Classification

### A Corpus: Scripture text 부재

| Class | Finding | Evidence Level | Status |
|-------|---------|----------------|--------|
| A Corpus | TSU corpus에 Scripture text 없음 (119,595 chunks 중 0%가 verse_mapping.book_id를 가짐) | E1/E2 | CONFIRMED |

**근거:**
- output/bench/tsu_dataset.jsonl Record 0~4: verse_mapping={} (모두 빈 dict)
- output/bench/bible_index.sqlite3 bible_posting 테이블: 0 rows
- tsu_builder.py L330: `if book_id != "UNK":` 게이트 — book_id가 UNK이면 verse_mapping에 넣지 않음
- 현재 corpus의 source files는 모두 commentary/sermon (Broadus, Dargan, Spurgeon 등 67개)

### B Metadata/Schema: Scripture metadata 보존 구조

| Class | Finding | Evidence Level | Status |
|-------|---------|----------------|--------|
| B Metadata/Schema | TSU schema의 verse_mapping field가 book/chapter/verse를 이미 보존. Evidence.raw_metadata가 전체 TSU record 복사. Tantivy schema에 book_id field 이미 존재. | E1/E3 | CONFIRMED |

**근거:**
- tsu_builder.py L328-354: verse_mapping 생성 로직
- evidence_adapters/tsu_adapter.py L95: `raw_metadata = dict(tsu_record)` — 전체 복사
- candidate_generator.py L138, L155: book_id field 이미 Tantivy schema에 있고 verse_mapping.book_id에서 매핑

### C Query Expansion: 개념어 -> canonical book mapping

| Class | Finding | Evidence Level | Status |
|-------|---------|----------------|--------|
| C Query Expansion | "복음서", "사도" 등 개념어가 BOOK_ID_TO_NAMES에 없음. _detect_books_standalone()이 매칭 실패. | E1 | CONFIRMED |

**근거:**
- retrieval.py L216-293: BOOK_ID_TO_NAMES 직접 확인 — "복음서", "사도" 없음
- retrieval.py L639-719: _detect_books_standalone()이 BOOK_ID_TO_NAMES의 names에서 longest-match

## 9. Minimal Integration Path

### 1. Scripture corpus의 최소 단위 (E3)

**TSU chunk 1개 = Bible book chapter verse 1구절 (또는 소규모 구절 그룹)**

```json
{
  "tsu_id": "TSU-BIBLE-ROM-5-3-chunk_00000",
  "document_id": "bible_kjv",
  "chunk_id": "bible_kjv_ROM_5_3_chunk_00000",
  "content": "For there is no condemnation now for those who are in Christ Jesus.",
  "verse_mapping": {"book_id": "ROM", "chapter": 5, "verse_start": 3, "verse_end": 3},
  "title": "Holy Bible (KJV)",
  "author": "Various",
  "source_file": "bible_kjv.txt",
  "language": "en",
  "source_type": "txt"
}
```

### 2. 필요한 metadata (E3)

| 필드 | 현재 TSU에 있는가? | Scripture corpus에서 필요 |
|------|-------------------|--------------------------|
| tsu_id | 예 | 예 (TSU-BIBLE-{book}-{chap}-{verse}-{chunk}) |
| document_id | 예 | 예 (bible_kjv, bible_nasb, bible_kor 등) |
| chunk_id | 예 | 예 |
| content | 예 | 예 |
| verse_mapping | 예 (확장 지점) | **필수** — book_id, chapter, verse_start, verse_end |
| title | 예 | 예 |
| author | 예 | 예 |
| source_file | 예 | 예 (translation 식별용) |
| language | 예 | 예 |
| source_type | 예 | 예 |
| translation | **아니오** | **추가 필요** — "KJV", "NASB", "개역개정" 등 |
| doc_type | **아니오** | **추가 권장** — "scripture" vs "commentary" 구별용 |

### 3. 기존 TSU와의 관계 (E3)

- **동일 tsu_dataset.jsonl에 추가** 가능 — verse_mapping.book_id가 None이 아닌 chunk로 자동 식별
- **별도 index 불필요** — Tantivy는 book_id term filter로 구별 가능
- **Bible Index 자동 빌드** — rebuild_tsu_index()가 bible_posting 테이블에 자동 삽입

### 4. Evidence layer 연결 위치 (E1)

**TSUEvidenceAdapter.adapt()** (core/evidence_adapters/tsu_adapter.py L50-116):
- raw_metadata에 verse_mapping 포함 -> Evidence.raw_metadata["verse_mapping"] 자동 보존
- corpus_type="bible" 설정 시 commentary와 구별 가능

### 5. Retrieval 연결 위치 (E1)

**HybridRetriever._generate_candidates()** (core/hybrid_candidate_pipeline.py L210-280):
- bible route: BibleIndex.lookup_scripture_ref(ref) -> tsu_id list
- hybrid route: CandidateGenerator.search() -> book_id filter 가능
- Scripture corpus가 동일 index에 있으면 두 경로 모두 자동 호환

### 6. Citation/provenance 연결 위치 (E1)

**CitationBuilder** (core/retrieval.py):
- Evidence.raw_metadata["verse_mapping"]에서 book/chapter/verse 읽음
- has_provenance로 출처 추적 가능
- Scripture corpus에서도 동일 mechanism 작동

### 7. index 변경 필요 여부 (E3)

**불필요.** 현재 Tantivy schema에 book_id, language, tsu_id field가 이미 있음. verse_mapping.book_id가 채워지면 자동으로 인덱싱됨.

### 8. query expansion 위치 (E1)

**core/retrieval.py::BOOK_ID_TO_NAMES** (L216-293):
- "복음서" -> MAT/MRK/LUK/JHN mapping 추가
- "사도"/"사도들" -> ACT mapping 추가
- 또는 별도 concept-to-books mapping 생성

## 10. UNKNOWN / UNVERIFIED

| 항목 | 이유 |
|------|------|
| Scripture corpus의 실제 chunking granularity | 현재 코드에 없음 — 1구절 vs 소규모 그룹 vs chapter 단위 |
| translation field의 정확한 schema 위치 | raw_metadata에 넣을지 top-level에 넣을지 미정 |
| doc_type field 추가 시 Tantivy schema 영향 | 현재 Tantivy rebuild 없이 추가 가능하지만, search filter로 쓰려면 schema 변경 필요 |
| BGE-M3 embedding의 Scripture chunk quality | Scripture text가 없으므로 embedding cache에 없음 — 새 corpus ingestion 후 재계산 필요 |
| multilingual verse alignment (KJV/NASB/개역개정 동일 verse 묶기) | 현재 architecture에 없음 — tsu_id 패턴 또는 별도 alignment table 필요 |

## 11. Runtime Verification Required

| 검증 항목 | 명령/방법 |
|-----------|----------|
| TSU corpus의 verse_mapping.book_id 분포 | `jq -r '.verse_mapping.book_id // "None"' output/bench/tsu_dataset.jsonl \| sort \| uniq -c` |
| Bible Index의 actual posting count | `sqlite3 output/bench/bible_index.sqlite3 'SELECT COUNT(*) FROM bible_posting'` |
| EnhancedQueryParser의 chapter-only parsing | `python -c "from core.query_enhancements import EnhancedQueryParser; p = EnhancedQueryParser(); print(p.parse('히브리서 4장').scripture_refs)"` |
| BOOK_ID_TO_NAMES에 "복음서"/"사도" 부재 확인 | `grep -n "복음서\|사도" core/retrieval.py` |
| HybridRetriever의 bible_index wiring | `grep -n "bible_index" core/hybrid_candidate_pipeline.py core/index_orchestrator.py` |

## 12. Mutation Status

CODE MUTATION: NO
CORPUS MUTATION: NO
INDEX REBUILD: NO
COMMIT: NO
PUSH: NO
