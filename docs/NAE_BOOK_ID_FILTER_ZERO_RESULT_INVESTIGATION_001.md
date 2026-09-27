# 성경책 이름 질의 0건 — 원인 조사 001

- 날짜: 2026-09-26 · 브랜치 `claude/tsu-data-processing-query-8f79fe` · 코드 변경 없음(조사만)

## 증상 (UI 경로 `HybridRetriever`, 실데이터 읽기전용)
| 질의 | detected_books | route | 후보 | book 필터 제거 시 |
|---|---|---|---|---|
| 로마서의 이신칭의 | ROM | hybrid | 0 | 30 |
| Romans justification by faith | ROM | hybrid | 0 | 30 |
| 로마서 8장 28절 | ROM | bible | 0 | 30 |
| 요한복음 강해 | JHN | hybrid | 0 | 30 |
| sermon on the Psalms | PSA | hybrid | 0 | 30 |

→ 한국어/영어 무관, **성경책 이름이 들어간 모든 질의가 0건.** 번역 단계(PR #88)와 무관.

## 원인
1. `book_id`는 **문서 단위** 값이다. `core/tsu_builder.py`에서
   `doc.get("book") or _resolve_book_id(source_file) or "UNK"` — 파일명이 성경책
   주석서일 때만 채워지고, `verse_mapping`은 `book_id != "UNK"`일 때만 채워진다.
2. 현 코퍼스(Spurgeon 설교집·Broadus 등 125출처)는 책 단위 주석서가 아니므로
   **119,595건 전부 `TSU-UNK-*`, `verse_mapping == {}`** (실측 100%).
3. `CandidateGenerator.search()`는 `parsed_query.detected_books`를 Tantivy `book_id`
   **Must 필터**로 건다. 필터만 남긴 폴백도 같은 필터라 역시 0건.
4. 구절 질의(route=bible)는 `bible_index`를 쓰는데, 이것도 `verse_mapping`으로 만들어져
   `bible_posting` **0행** → 항상 0건. 이 경로엔 텍스트 검색 폴백이 없다.
5. 레거시 `RetrievalEngine._metadata_filter()`는 필터 결과가 비면 전체 풀로 돌아가서
   이 문제가 없다 → UI 기본 경로(`USE_INVERTED_INDEX=true`, 2026-09-18 전환)에서만 발생.

## 수정안
- **A (권장, 최소):** 검색 경로 폴백
  - `CandidateGenerator.search()`: 자동 도출된 book 필터(`book_ids` 미지정)로 텍스트+필터,
    필터-only가 모두 0건이면 book 필터를 빼고 재검색(`source_files` 사용자 범위는 유지).
  - `HybridRetriever.retrieve()`: bible 경로가 0건이면 hybrid 자유검색으로 폴백.
  - 데이터 변경·재색인 없음. 책 주석서가 들어오면 필터가 그대로 작동.
- **B (근본, 별도 트랙):** 청크 본문의 성경 참조로 청크 단위 `verse_mapping`을 채움 —
  TSU Pipeline 변경 + 전체 재빌드 → C1 Review·별도 승인 필요.

## 상태
- [x] 원인 확정 (실측)
- [ ] 수정안 A 승인 대기 (Retrieval Engine 변경)
- [ ] 수정안 B 검토
