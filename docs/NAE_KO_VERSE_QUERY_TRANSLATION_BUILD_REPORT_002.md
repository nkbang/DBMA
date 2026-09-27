# 한국어 구절 질의 장·절 번역 — Build Report 002

- 날짜: 2026-09-26 · 브랜치 `claude/tsu-data-processing-query-8f79fe` · PR #88
- 승인: 사용자 채팅 "작업 승인"(Report 001 다음 과제 권고안)
- 선행: `NAE_KO_EN_QUERY_TRANSLATION_BUILD_REPORT_001.md`, `NAE_INDEX_PAGE_DOWNWEIGHT_BUILD_REPORT_001.md`

## 문제
"로마서 8장 28절"의 영어 번역어가 `romans` 하나뿐 → 1~3위가 색인 잔여물·주석서 목록.

## 발견
- 운영 `QueryParser`는 `core.retrieval` 말미에서 `EnhancedQueryParser`로 교체된다.
  한국어 장·절("8장 28절")은 그 하위 파서가 **부모 parse() 이후** 추가 → v1 번역 단계가 참조를 못 봄.
- 코퍼스 구절 표기(주요 14권): 로마숫자 장 `Romans viii. 28` 4,854건(79%), `8:28` 1,133건, `8. 28` 222건.

## 수정
| 파일 | 내용 |
|---|---|
| `core/query_translation.py` | v2: `to_roman`, `scripture_ref_terms`(로마 장+아라비아 장+절), `scripture_ref_phrases`(ASCII 3자+ 별칭 × 장 표기 구문, 최대 12). VERSION 1→2 |
| `core/retrieval.py` | 번역 단계를 `_apply_translation()`으로 분리(멱등), `ParsedQuery.translated_phrases` 추가 |
| `core/query_enhancements.py` | `EnhancedQueryParser.parse()` 끝에서 `_apply_translation()` 재실행 |
| `core/candidate_generator.py` | 번역 구문을 Tantivy phrase query(boost 3.0, Should)로 가중 |
| `tests/test_query_translation.py`, `tests/test_candidate_generator.py` | v2 단위 5건 + 구문 가중 1건 |

영어 질의 동작은 불변(번역·구문 모두 한글 질의에만).

## 검증
- 관련 회귀 600 passed / 1 skipped
- 실데이터(UI 경로) 상위 결과:

| 질의 | 전(v1) | 후(v2) |
|---|---|---|
| 로마서 8장 28절 | Maclaren 색인 잔여물 / 주석서 목록 | **1위 Spurgeon 8/5 묵상(롬 8:28 본문)** |
| 시편 23편 | 일반 설교 | 3위 Spurgeon "My cup runneth over"(시 23:5) 설교 |
| 요한복음 3장 16절 | Maclaren 목차 / 마 3:16 묵상 / OCR 잡음 | Spurgeon 설교(요일 3:16 추정) — 부분 개선 |
| 칭의와 성화의 관계 | 변화 없음 | 변화 없음 |

지연 12~16ms.

## 한계 / 다음
- [ ] `john iii 16` 구문이 `1 John iii. 16`에도 일치 → 앞 토큰이 숫자/로마숫자일 때 제외하는 정밀화 검토
- [ ] 레거시 `RetrievalEngine` 경로는 구문 가중 없음(번역어만)
- [ ] 영어 질의에도 로마숫자 장 표기 확장 여부 — 영어 동작 변경이라 별도 판단

진행률: 한국어 구절 질의 품질 약 70%
