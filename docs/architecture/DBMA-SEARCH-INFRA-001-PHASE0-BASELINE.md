# DBMA-SEARCH-INFRA-001 — Phase 0 병목 분석 및 Baseline

- 측정일: 2026-07-30
- 대상: `core/retrieval.py::RetrievalEngine.retrieve()` (현재 프로덕션 경로)
- 코퍼스: `output/bench/tsu_dataset.jsonl` (53,231 TSU)
- 측정 방식: `QueryProcessor.process()` 실제 호출, `PerformanceMetrics` 단계별 계측값 그대로 사용 (신규 계측 코드 추가 불필요 — 기존에 이미 존재)

## 1. 구조 확인
- **Qdrant/ANN 벡터 검색은 실제로 연결되어 있지 않다.** `RetrievalEngine.__init__`이 `qdrant_url`/`collection_name`을 받지만 `retrieve()` 내부에서 전혀 사용하지 않음. STEP 3(벡터 검색)은 `embedding_cache`가 주어지면 BGE-M3 임베딩을 개별 계산하고, 없거나 실패하면 인메모리 TF-IDF 코사인 유사도로 폴백한다. 즉 현재 "벡터 검색"은 전량 인메모리 연산이다.
- `core/parallel_retriever.py`는 HQ 문서가 가정한 "Stage 2 Semantic Ranking(Qdrant)"이 아니라, T1(hybrid search)과 T2(큐레이션 성경 태그) 두 근거 축을 합치는 별개 모듈이다. Logos식 2단계 분리와는 무관 — 혼동 주의.
- `RetrievalEngine.retrieve()`는 후보 풀 전체(최대 53,231건)에 대해 매 쿼리마다 BM25 스코어링과 theological scoring을 파이썬 루프로 직접 계산한다. 사전 색인/역색인 없음, 전량 순차 스캔(O(N)).

## 2. 실측 결과 (53,231 TSU 코퍼스, 3개 쿼리 표본)

| 쿼리 유형 | 예시 | total_ms | bm25_scoring_ms | theological_scoring_ms | vector_search_ms |
|---|---|---:|---:|---:|---:|
| 영어 자연어 (BM25 미스 → 전체 폴백) | "What does the commentary teach about 'covenant faithfulness'?" | 52,129 | (1차 콜드) | — | — |
| 영어 자연어 (동일 패턴) | "Which TSU ... 'covenant faithfulness'?" | 54,883 | 9,681 | **44,896 (82%)** | 280 |
| 성경 참조 (metadata filter로 후보 풀 축소됨) | "롬 8:28" | 341 | 0.04 | 22 | 307 |

## 3. 병목 순위 (수치 근거)
1. **`theological_scoring_ms` — 총 지연의 최대 82%.** `compute_theological_score()`가 metadata filter로 후보 풀이 좁혀지지 못한 쿼리(주로 영어/자연어, BM25 매칭 실패 시 전체 폴백)에서 5만 건 이상에 대해 순차 재계산됨.
2. **`bm25_scoring_ms` — 약 18%.** 역색인 없이 후보 풀 전체 문자열을 매번 토크나이즈+스코어링.
3. **벡터 검색(280~307ms)은 병목이 아니다.** HQ 권고안의 "Stage 2 Semantic Ranking(Qdrant)"보다 Stage 1(candidate 축소) 자체가 훨씬 더 큰 문제.
4. **Metadata pre-filter가 작동할 때(성경 참조 등)는 이미 목표(p95 1초)를 충족한다** (341ms). 즉 성능 문제는 "후보 풀이 좁혀지지 않는 경로"에 집중되어 있다.

## 4. Phase 1 우선순위 재조정 (HQ 원안 대비)
HQ 원안은 "키워드/벡터 병렬화"를 Phase 1 항목으로 제시했으나, 실측상 벡터 검색은 병목이 아니므로 우선순위를 다음과 같이 조정 제안:
1. **theological scoring 대상 풀 축소가 최우선.** 현재 "BM25 미스 시 전체 후보 폴백" 로직(P0 FIX 주석, retrieval.py:1452-1456)이 45초 지연의 직접 원인. 역색인(Phase 2) 도입 전에도, theological scoring을 BM25 top-K로만 제한하는 것만으로 즉시 개선 가능 (임시 조치, 정확도 영향 검증 필요).
2. BM25 자체도 역색인 없이 선형 스캔 — Phase 2(Tantivy 등) 도입 시 자연 해결.
3. 벡터/BM25 병렬화는 여전히 유효하지만 기대 효과는 낮음(각각 <10ms~300ms 수준).

## 5. 조치 완료 (2026-07-30, Phase 1 착수분)

### 5a. Gold Standard 정합성 문제
`dbma_gold_standard_v3.json`의 `expected_tsu_ids`(순번 기반, 예: `TSU-GEN-000001`)가 현재 corpus의 tsu_id 스키마(콘텐츠 해시 기반, 예: `TSU-ACT-ada6a56f..._chunk_00000`)와 애초에 불일치 — 이는 새 버그가 아니라 **이미 SPRINT17-Phase6B에서 공식 퇴역 처리된 파일**이었다(스크립트 docstring에 "70.7%가 현재 corpus에 없는 책 대상, tsu_id가 TSU rebuild마다 stale해짐" 명시). 대체품인 `output/bench/book_level_gold_standard_v1.json`(`expected_book_id` 스키마, book_id는 TSU rebuild에도 안정적) + `scripts/run_book_level_benchmark.py`가 이미 구현·검증되어 있어 그대로 채택. 이번 baseline/회귀 측정은 전부 이 최신 gold standard로 수행.

### 5b. Theological scoring 풀 축소 패치 (`core/retrieval.py`)
- **원인**: BM25가 완전 미스일 때의 폴백(`bm25_top_k_indices = [(idx, 0.0) for idx in candidate_pool]`, 옛 "P0 FIX")이 `self.candidate_k`(100) 캡을 무시하고 후보 풀 전체(최대 5.3만)를 그대로 넘겨, 이후 theological/passage scoring(STEP 4/4b)이 전체 풀에 대해 재계산됨.
- **1차 시도(기각)**: 폴백 시 TF-IDF 코사인 유사도로 먼저 랭킹 후 top-K만 남기는 방식을 시도했으나, 이 사전 랭킹 자체가 O(N) 스캔이라 문제를 theological→TF-IDF로 옮겼을 뿐이었다(특정 쿼리 8~16초). HQ 원칙("검색 시 문서 전체를 순회하지 않는다")에 위배되어 폐기.
- **최종 조치**: 폴백을 스코어링 없는 단순 슬라이스(`candidate_pool[:self.candidate_k]`)로 교체. 이 분기는 애초에 쿼리 신호가 전무한 상태(BM25 매칭 0건)이므로 정렬 없는 캡이 동급 비용의 휴리스틱과 품질상 동등 — 이후 벡터/theological scoring이 그 top-K 안에서 변별. `capped_pool`을 도입해 theological ensure-loop, passage scoring loop, ranking_indices 폴백 3곳 모두 이 캡을 따르도록 통일.
- **검증 결과** (동일 96개 쿼리, `output/bench/book_level_gold_standard_v1.json`):

  | 지표 | 패치 전 | 패치 후 |
  |---|---:|---:|
  | p50 | 385ms | **149ms** |
  | p95 | 14,701ms | **9,020ms** |
  | p99 | 54,556ms | **17,276ms** |
  | precision@1 | 1.0 | 1.0 (변화 없음) |
  | 회귀 테스트 | — | 22개 전부 통과 |

### 5c. 남은 롱테일의 진짜 원인 (신규 발견 — Phase 2 스코프)
p95/p99가 여전히 목표(1초/2초)를 크게 초과. 원인 재조사 결과, 이번 패치가 다루지 않은 **더 근본적인 병목**을 확인:
- "Find resources about Acts" 등 영어 자연어 쿼리에서 `bm25_scoring_ms` 자체가 7.3~8.0초 소요.
- 원인: 쿼리 파서의 book 감지가 한국어 책 이름 위주라 영어 표현("Acts")에서 metadata filter가 작동하지 않아 `candidate_pool`이 좁혀지지 않고, STEP 2(BM25) 루프가 후보 풀 전체(문서 내용 문자열)를 매번 토크나이즈+스코어링함.
- 이는 **역색인이 없는 구조적 문제**이며, 폴백 분기가 아니라 BM25 정상 실행 경로 자체의 O(N) 전문 스캔이라 Phase 1 범위의 안전한 패치로는 해결 불가 — Tantivy 등 역색인 도입(Phase 2)이 진짜 해결책. 임시로 여기서도 슬라이스 캡을 걸면 recall을 크게 해칠 위험(진짜 키워드 매치가 존재할 수 있는 경로이므로 이론적 근거의 폐기는 부적절)이 있어 보류.
- **결론**: Phase 1 패치로 원래 발견한 버그(45초 폴백 병목)는 해결. 남은 롱테일은 HQ 계획의 Phase 2(역색인 도입)가 정확히 겨냥하는 문제임을 실측으로 재확인 — Phase 2 우선순위를 그대로 유지.
