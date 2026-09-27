# 권말 색인 페이지 감점 — Build Report 001

- 날짜: 2026-09-26 · 브랜치 `claude/tsu-data-processing-query-8f79fe` · PR #88
- 승인: 사용자 채팅 지시("색인 페이지 감점 방안 진행해")

## 문제
"로마서 8장 28절" 상위 10건이 전부 Maclaren Expositions 권말 색인("Romans, 179 ; Romans, 191").
1. UI 경로 `HybridRetriever`는 `content_quality`를 전혀 쓰지 않음(레거시 엔진은 0.7~1.0 감점 적용).
2. `noise_classifier`에 색인 유형이 없어 색인 청크 절반이 `NORMAL_CONTENT`(quality 1.0).
3. 후보 30건 중 25건이 색인 → 순위 감점만으로는 후보 풀 오염 해결 불가.

## 신호 검증 (실코퍼스 119,595건, 30토큰 이상 117,862건)
| 조건 | 건수 | 표본 판독 |
|---|---|---|
| 숫자비율 ≥0.20 AND 로케이터("이름, 쪽") ≥5/100토큰 | 669 | Maclaren·Broadus·Dargan 색인 |
| 숫자비율 ≥0.35 (로케이터 없음) | 212 | Spurgeon 성경색인·OCR 쓰레기 |
| 제외: 숫자비율 0.25~0.35, 로케이터 <5 | 64 | Keach 1681 참조 밀집 **본문** → 판정 안 됨 ✔ |

판정 합계 약 880건(0.75%).

## 수정
| 파일 | 내용 |
|---|---|
| `core/index_page_detector.py` (신규) | `is_index_page()` — 위 규칙, 검색 시점 판정(TSU 재빌드 없음) |
| `core/hybrid_candidate_pipeline.py` | ① 후보 3배 과다조회 후 색인 페이지를 뒤로 보내고 candidate_k로 자름(점수 계산은 여전히 30건) ② 최종점수에 `content_quality` 계수 적용 + 색인은 DOWNWEIGHT(0.3→계수 0.79) |
| `tests/test_index_page_detector.py` (신규) | 실코퍼스 발췌 판정 7건 + 계수/강등/백필 4건 |

원칙: 제거가 아니라 강등 — 색인밖에 없으면 그대로 채운다(noise_classifier "classifier, not a deleter").

## 검증
- 신규 11 passed · 관련 회귀 477 passed / 1 skipped
- 실데이터(UI 경로), 상위 10건 중 색인:

| 질의 | 전 | 후 | 지연 |
|---|---|---|---|
| 로마서 8장 28절 | 10 | 0 | 16ms |
| Romans 8:28 all things work together for good | — | 0 (1위 Spurgeon 8/5 묵상) | 16ms |
| 요한복음 강해 / 칭의와 성화의 관계 / sermon on the Psalms | — | 0 | 17~18ms |

## 남은 과제
- [ ] 한국어 구절 질의는 번역어가 `romans`뿐 → 영어 본문 표기("Romans viii. 28", "8:28")로 장·절 번역 추가
- [ ] 임계값 바로 아래 색인 조각 일부 잔존(과적합 방지 위해 임계값 유지)
- [ ] ingest 단계 `noise_classifier`에 INDEX 유형 추가는 TSU Pipeline 변경 → 별도 승인

진행률: 색인 강등 100% / 한국어 구절 질의 품질 약 50%
