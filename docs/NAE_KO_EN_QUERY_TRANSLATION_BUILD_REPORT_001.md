# NAE 한국어 질의 번역 단계 — Build Report 001

- 날짜: 2026-09-26
- 브랜치: `claude/tsu-data-processing-query-8f79fe`
- 승인: 사용자 채팅 지시("한국어 질의 번역 단계 추가 진행해") — Retrieval Engine 변경

## 문제
TSU 코퍼스(119,595건)는 대부분 영어 본문. 1단계 후보 생성(BM25/Tantivy)이
질의 원문 낱말로만 매칭해 한국어 질의는 후보 0건(UI 경로) 또는 무관한 청크만 반환.

## 수정
| 파일 | 내용 |
|---|---|
| `core/query_translation.py` (신규) | 한→영 신학 용어 사전 + `translate_query_terms()` (최장일치, 한글 없으면 no-op) |
| `core/retrieval.py` | `ParsedQuery.translated_terms` 추가, `QueryParser.parse()` 7단계에서 번역어를 `keywords`에 추가(한국어 원어 유지), 감지된 책 이름 영문명 포함 |
| `core/candidate_generator.py` | Tantivy 자유검색 질의 텍스트에 번역어 추가(exact-phrase 경로 불변) |
| `core/search_cache.py` | 캐시 키에 `QUERY_TRANSLATION_VERSION` 포함 → 이전 한국어 결과 캐시 무효화 |

설계 선택: LLM 번역 대신 닫힌 사전 — 결정적(캐시·회귀 가능), 지연 0, 날조 여지 없음.
의미 재랭킹(BGE-M3)은 원문 질의 그대로 사용(다국어 모델).

## 검증
- 신규 `tests/test_query_translation.py` 8 passed
- 파서/후보생성/캐시/하이브리드 관련 회귀 385 passed, 1 skipped
- 실데이터(UI 경로 HybridRetriever, 읽기전용):

| 질의 | 전 | 후 |
|---|---|---|
| 칭의와 성화의 관계 | 0 | 30 (Spurgeon 성화 본문) |
| 하나님의 주권과 인간의 책임 | 0 | 30 |
| 침례의 의미 | 0 | 30 (침례 본문) |
| 로마서의 이신칭의 | 0 | 0 ← 별건(아래) |

## 남은 과제
- [ ] 책 이름만 있고 구절이 없는 질의: `detected_books`가 Tantivy `book_id` Must 필터로 걸려
      book_id가 빈 TSU 대부분이 배제됨(번역과 무관한 기존 동작) — 별도 조사 필요
- [ ] 사전 미수록 용어는 번역 안 됨 → 실사용 로그 보고 확장(확장 시 VERSION 증가)

진행률: 번역 단계 100% / 한국어 질의 품질 전반 약 60%
