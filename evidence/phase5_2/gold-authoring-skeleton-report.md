# Phase 5.2 Gold Authoring — Skeleton Report (Approach B)

**Status:** `SKELETON — Corpus Indexing Required for Valid Evaluation`

**Date:** 2026-07-31

**Gate:**
```text
Phase 5.2 Gold Authoring:
SKELETON (registry metadata 기반 가상 gold set)

Benchmark retrieval evaluation:
BLOCKED — corpus indexing (Qdrant nae_tsu_v1) 필요

Gold set validity:
NOT VALIDATED — corpus에 실제 TSU 존재 여부 확인 불가
```

## 개요

Approach B: identity registry의 metadata(book_id, doc_type, chunk_count)를
사용해 gold set skeleton을 생성했습니다. 그러나 corpus indexing이 전혀
안 된 상태이므로, 생성된 gold TSU ID가 실제 corpus에 존재하는지 검증 불가.

## 생성된 Gold Set

**[CUE-RECONCILIATION-010, 2026-08-01]** 아래 서술은 원본 작성 당시 기준이었으나
실제 파일 및 스크립트 재실행 결과와 맞지 않아 정정함. 전체 경위는
`docs/agents/cue/CUE-STATUS-010-NAE-PHASE5.1-5.2-REVIEW.md` Finding 5,
`evidence/phase5_2/pbc1765_acquire_009/CUE-RECONCILIATION-010.md` 참고.

- **파일:** `NAE/benchmark/datasets/gold_benchmark_v1.jsonl`
- **질문 수:** 5개 (B001-B005)
- **gold_tsu_ids (정정):** 각 질문당 **5개** TSU ID — `scripts/author_gold_set.py --output ...`를
  현재 코드/registry로 재실행해 바이트 단위로 동일한 파일이 재생성됨을 확인(스크립트와 파일이
  실제로 일치함, 데이터 조작은 아님). 5개 ID는 `TSU-ACT-ada6a56f8ea13582` 1개 +
  `TSU-SOL-*` 4개로 구성.
- **⚠️ `TSU-SOL-*` 근본 원인 — `core/tsu_builder.py::_resolve_book_id()`의 실제 버그**:
  이 4개 문서는 registry에서 실제로는 **"5 SOLAS시리즈01~05"**(오직 믿음/오직 하나님의 영광/
  오직 하나님의 말씀/오직 그리스도/오직 은혜 — 종교개혁 5대 솔라를 다룬 조직신학 도서, **성경
  아가서와 무관**)라는 파일명을 가진 문서들이다. `_resolve_book_id()`가 `core/retrieval.py`의
  `NAME_TO_BOOK_ID["SOL"] = ["song of solomon", "sol", ...]` 별칭 "sol"(3자)을 파일명
  "**sol**as시리즈"에 대해 단순 부분문자열 매칭해 아가서(SOL)로 오판정한 것 — 과거 단일문자
  별칭("마"→MAT) false positive를 막기 위해 `len(name) >= 2` 가드가 이미 있으나, 3~4자
  별칭의 단어경계 없는 부분매칭까지는 막지 못함. 즉 **TSU-SOL-\* 4개 gold ID는 실제로는 아가서가
  아닌 조직신학 도서를 가리키는, book_id 자체가 잘못 태깅된 문서 참조**.
- **[2026-08-01 후속 수정 완료]** `core/tsu_builder.py::_resolve_book_id()`를 letter-only
  경계 lookaround 방식으로 수정 — 짧은 별칭이 다른 글자와 바로 붙어 있으면(예: "sol"+"as") 더
  이상 매칭되지 않지만, 이 코퍼스의 실제 명명 관행인 "책이름+숫자"(예: "사도행전1")는 계속
  정상 매칭됨(숫자는 경계 예외로 허용). `tests/test_build_tsu_dataset_book_id.py`에 회귀
  테스트 2건 추가(SOLAS 오매칭 방지 확인 + 사도행전1/2 정상 동작 확인), 관련 회귀 65개 전부
  통과 확인.
  `scripts/author_gold_set.py` 재실행 결과 `gold_benchmark_v1.jsonl`에서 `TSU-SOL-*` 완전히
  사라짐(0건) — 5개 질문 모두 실제 성경 책(ACT, LUK 등)에서 파생된 gold_tsu_ids로 갱신됨.
  단, 여전히 corpus indexing(Qdrant nae_tsu_v1)이 안 된 상태이므로 이 gold_tsu_ids들이
  실제 TSU 데이터셋에 존재하는지는 별도로 검증 필요 — "Gold set validity: NOT VALIDATED"
  게이트는 그대로 유효함.

## 제약 사항

### 1. registry book_id 분포 제한

registry (`data/제련완성본/registry/documents.json`) 에 book_id가 있는 문서는
ACT(사도행전) 1개뿐입니다:

| book_id | 문서 수 | 비고 |
|---|---|---|
| ACT | 1 | 7. 사도행전1.pdf (주석, chunk_count=350) |
| None | 80 | filename-based resolution 실패 |

### 2. Baptist tradition 원문 없음

`resources/theological_sources/baptist/` 에는 metadata(source_candidates.csv)만
있고, 실제 PDF/TXT 원문이 없습니다. local_path 모두 null.

### 3. Qdrant nae_tsu_v1: 0 points

corpus indexing이 전혀 안 된 상태입니다. TSU chunk content가 vector DB에
없으므로 retrieval evaluation 불가.

## gold_benchmark_v1.jsonl 구조

```jsonl
{"benchmark_id": "B001", "question": {"text": "예수님이 십자가에서 이루신 속죄의 의미는 무엇인가요?", ...}, "expected": {"gold_tsu_ids": ["TSU-ACT-ada6a56f8ea13582"], ...}, "evaluation": {"status": "pending"}, ...}
{"benchmark_id": "B002", "question": {"text": "성경에서 용서의 교리는 어떻게 설명되나요?", ...}, "expected": {"gold_tsu_ids": ["TSU-ACT-ada6a56f8ea13582"], ...}, "evaluation": {"status": "pending"}, ...}
{"benchmark_id": "B003", "question": {"text": "What is the role of the Holy Spirit in salvation?", ...}, "expected": {"gold_tsu_ids": ["TSU-ACT-ada6a56f8ea13582"], ...}, "evaluation": {"status": "pending"}, ...}
{"benchmark_id": "B004", "question": {"text": "구약 시대에 제사는 어떻게 수행되었나요?", ...}, "expected": {"gold_tsu_ids": ["TSU-ACT-ada6a56f8ea13582"], ...}, "evaluation": {"status": "pending"}, ...}
{"benchmark_id": "B005", "question": {"text": "믿음으로 의에 이르는 과정은 무엇인가요?", ...}, "expected": {"gold_tsu_ids": ["TSU-ACT-ada6a56f8ea13582"], ...}, "evaluation": {"status": "pending"}, ...}
```

모든 질문이 동일한 TSU ID를 가리키는 것은 registry book_id 분포 제한 때문입니다.

## 생성 스크립트

- **파일:** `scripts/author_gold_set.py`
- **사용법:** `python scripts/author_gold_set.py --output NAE/benchmark/datasets/gold_benchmark_v1.jsonl`
- **로직:** doc_type 매핑 → book_id 필터링 → TSU ID 생성 (TSU-{book_id}-{document_id prefix})

## 다음 단계 (corpus indexing 후)

1. `scripts/build_tsu_dataset.py` 실행하여 TSU dataset 생성
2. Qdrant nae_tsu_v1에 TSU chunk content 인덱싱
3. 실제 존재하는 TSU ID로 gold set 재작성
4. benchmark retrieval evaluation 실행

## 결론

Phase 5.2 Gold Authoring은 skeleton 생성으로 완료했지만, corpus indexing이
필수적입니다. 현재 gold set은 "가상"이며 실제 benchmark evaluation에
사용할 수 없습니다.

---

**Approved by:** [Core Engineer]
**Next Review:** After corpus indexing complete