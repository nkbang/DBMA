# C1 Task Order 050 — 검색 신뢰도 경고 오탐 근본원인: 신규 하이브리드 파이프라인 스코어/결과 결함 조사·수정

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거**: CUE가 오늘 세션에서 직접 재현·검증한 결과 (아래 §0 요약), C1이 먼저
제기한 "검색 결과 신뢰도가 낮습니다" 경고 오탐 이슈의 후속

---

## 0. 지금까지 확인된 사실 (재조사하지 말고 이 결과를 출발점으로 삼을 것)

**증상**: `ui/pages/chat.py`의 `_render_low_confidence_warning()`("검색
결과 신뢰도가 낮습니다")이 관련 있는 신학 질문에서도 과도하게 뜬다.

**1차 원인(레거시 경로, `core/retrieval.py` — 절대 손대지 말 것, §4 참고)**:
`QueryParser._extract_keywords()`(retrieval.py:457~481)의 정규식이 영문만
매칭해서 순수 한국어 쿼리는 예외 없이 `keywords=[]`를 반환 → BM25 후보
생성이 매번 실패 → `retrieve()`의 무순위 폴백(파일 순서상 앞쪽
`candidate_k`개)만 검색됨. 8개 쿼리(신학 4 + 일상 4)로 100% 재현 확인.
이 버그를 고치려고 시도하는 과정에서 2차 문제(BM25 문서 토큰화가
쿼리마다 캐시 없이 반복돼 코퍼스 전체 기준 쿼리당 ~19분)까지 드러났으나,
**`core/retrieval.py`는 Task Order 024/033에서 "절대 미접촉"으로 동결되어
있고 `tests/test_parallel_retriever.py::TestCoreRetrievalUnmodified`가 이를
회귀 테스트로 강제한다** — 이 파일은 `DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md`
§2-6에 따라 신규 Tantivy 파이프라인(`core/candidate_generator.py`)으로
대체될 예정이라 동결된 것으로 보인다. 그래서 CUE는 이 1차 원인을 **문서화만
하고 코드는 원복**했다.

**2차 발견(신규 경로, `USE_INVERTED_INDEX=true` → `HybridQueryProcessor`,
현재 default off라 프로덕션 미사용 — 이게 이번 Task Order의 실제 대상)**:
같은 8개 쿼리를 `core/hybrid_candidate_pipeline.py::HybridQueryProcessor`로
재실행한 결과:

```
category         top1_score            elapsed_s  query
관련 있음(신학)   None                  0.00       로마서 3장의 칭의 교리에 대해 설명해줘
관련 있음(신학)   0.04817150063051703   0.13       예수님의 부활의 의미는 무엇인가
관련 있음(신학)   0.04696394686907021   0.06       성령의 은사에 대한 바울의 가르침
관련 있음(신학)   0.048915917503966164  0.01       은혜와 율법의 관계
관련 없음(일상)   0.04817150063051703   0.02       오늘 서울 날씨 어때?
관련 없음(일상)   0.048915917503966164  0.02       파이썬으로 정렬 알고리즘 짜는 법
관련 없음(일상)   0.04787506400409626   0.02       저녁 메뉴 추천해줘
관련 없음(일상)   0.04918032786885246   0.00       비트코인 가격 전망
```

속도는 훌륭하지만(최대 0.13초 vs 레거시 경로 최악 19분), 두 가지 문제:

- **(A) "로마서 3장의 칭의 교리에 대해 설명해줘"가 결과 0건**(예외도 없이
  `top_k_results=[]`). 레거시 경로에서는 이 쿼리가 성경 구절 메타데이터
  필터 덕에 가장 높고 뚜렷한 점수(0.5196)를 받았던 것과 대조적 — 새
  경로에서 명백한 회귀.
- **(B) 관련 쿼리와 무관 쿼리의 `final_score`가 사실상 구분 안 됨**
  (0.0470~0.0492, 전부 비슷). `final_score`는 `core/rrf.py`의
  `reciprocal_rank_fusion()`(RRF, k=60 기본) 결과다 —
  `DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md` §8에 따르면 RRF는 **순위만
  반영하는 융합 점수**라 애초에 0~1 스케일 코사인/가중합과 스케일이 다르다.
  §8은 book-level gold standard 96개 쿼리에서 precision@1 1.0을
  보고했으므로, **실제 검색 정확도는 문제없을 가능성**이 있고, 문제는
  "RRF 점수를 `_LOW_CONFIDENCE_SCORE_THRESHOLD=0.45`(레거시 스케일 기준)와
  그대로 비교하는 것 자체가 카테고리 오류"일 수 있다. 이 가설을 검증하는
  것이 이번 Task Order의 핵심이다.

## 1. 목표

`USE_INVERTED_INDEX=true` 경로(신규 하이브리드 파이프라인)를 실사용
가능한 상태로 만든다 — (A) 회귀 원인 규명·수정, (B) "검색 신뢰도 낮음"
경고를 신규 경로에서도 의미 있게 동작하게 만든다. **플래그를 실제
프로덕션 기본값으로 뒤집는 것은 이번 범위가 아니다** — 그건 이 작업
완료 후 별도 승인 사안.

## 2. 조사·수정 범위

### 2-1. (A) "로마서 3장" 쿼리 결과 0건 — 원인 규명 (최우선)

- `core/query_planner.py::classify()`가 이 쿼리를 어떤 route로 분류하는지
  확인 (Bible/Exact/Metadata/일반 중 어디로 가는지).
- `core/hybrid_candidate_pipeline.py::HybridRetriever`가 해당 route에서
  호출하는 경로(BibleIndex? CandidateGenerator?)를 추적해서 왜 0건이
  나오는지 규명. 예외가 조용히 삼켜지고 있다면(`except Exception: return
  []` 류) 그 지점부터 의심.
- `output/bench/tantivy_index`와 `output/bench/tantivy_index_100k` 두
  인덱스 디렉터리가 존재하고 각각 `.tantivy-writer.lock` 파일이 남아있는
  것을 CUE가 확인함 — 어느 인덱스가 실제로 열리는지
  (`DEFAULT_CANDIDATE_INDEX_DIR` 설정값), 락 파일이 이전 프로세스가
  비정상 종료된 흔적인지, 인덱스가 최신 TSU 데이터셋과 일치하는지
  (`tsu_dataset.jsonl`이 6억 바이트인데 인덱스가 그만큼 최신인지) 확인.
  가능한 원인 중 하나로 다뤄라 — 이게 전부는 아닐 수 있음.

### 2-2. (B) RRF `final_score`를 신뢰도 신호로 쓰는 것의 타당성 재검토

- `_LOW_CONFIDENCE_SCORE_THRESHOLD`(`ui/pages/chat.py:79`)가 레거시
  가중합 스코어(코사인 유사도 기반, 0.35~0.52 관측 범위) 기준으로 잡힌
  값임을 확인했다 — RRF 스코어(0.04~0.05대 관측)에는 그대로 못 쓴다.
- `HybridQueryProcessor.process()`가 반환하는 `ResponsePackage`에 RRF
  `final_score` 외에 신뢰도 판단에 쓸 만한 다른 신호가 있는지 확인
  (예: 개별 bm25/theological/passage 원점수, RRF 합산 전 각 리스트에서의
  순위 자체, Tantivy BM25 원점수 등).
- **레거시와 신규 두 경로를 모두 지원해야 하는 상황**을 고려해 다음 중
  하나를 선택하고 근거를 보고서에 남겨라:
  1. `_is_low_confidence()`가 어떤 엔진 경로로 만들어진 결과인지 감지해서
     경로별로 다른 임계값/신호를 쓰게 분기, 또는
  2. 두 경로 모두에서 의미가 통하는 정규화된 신호(예: RRF 결과를
     0~1로 재정규화하거나, top1과 top2의 점수 격차 같은 상대적 신호)로
     교체
  - 어느 쪽이든 **레거시 경로(`core/retrieval.py`)의 동작은 변경하지
    않는다** — `chat.py`/`hybrid_candidate_pipeline.py` 쪽에서만 조정.
- 결정한 방식으로 위 8개 쿼리(§0 표)를 다시 돌려서 관련/무관 쿼리가
  실제로 구분되는지 확인. (재현 스크립트는 CUE가 쓴 것을 참고해 새로
  작성해도 되고, 아래 §6에 원본을 남겨둔다.)

## 3. 하지 않을 것

- `core/retrieval.py` 무변경 (Task Order 024/033과 동일 제약,
  `TestCoreRetrievalUnmodified` 테스트로 강제됨 — 이 테스트가 실패하면
  즉시 원복하고 보고할 것).
- `USE_INVERTED_INDEX` 기본값을 `true`로 바꾸는 것(config/rollout 변경) —
  이번 범위 아님.
- Stage 2 스코어링 로직(`compute_theological_score`,
  `compute_passage_match_score`, `core/retrieval.py`에서 그대로 import해서
  재사용 중) 자체의 재구현 — RRF 병합/신뢰도 신호 계층에서만 다뤄라.

## 4. 완료 조건

- [ ] §2-1: "로마서 3장" 쿼리 0건 회귀의 근본원인 규명 + 수정, 수정 전/후
      결과 비교를 보고서에 남길 것
- [ ] §2-2: 신뢰도 신호 방식 결정 + 구현, §0 표의 8개 쿼리(신학 4 +
      일상 4) 재실행 결과를 표로 제시해서 관련/무관이 실제로 구분됨을
      증명
- [ ] `USE_INVERTED_INDEX=true`로 96개 book-level gold standard 재실행해서
      precision@1이 여전히 1.0인지 확인 (Phase 2-6 §8 회귀 기준 유지)
- [ ] `git diff core/retrieval.py`가 빈 diff임을 커밋 전 반드시 확인
      (`tests/test_parallel_retriever.py::TestCoreRetrievalUnmodified` 통과)
- [ ] `pytest tests/` 전체 실행 — 결과 그대로 붙여넣기
- [ ] `docs/agents/c1/C1-TASK-ORDER-050-REPORT.md` 작성 — §2-1/§2-2 각각
      원인·결정 근거·재현 결과 포함

## 5. 완료 후

CUE가 §0 표 재현 + `TestCoreRetrievalUnmodified` + gold standard 재실행 +
전체 pytest로 독립 검증한다.

## 6. 부록 — CUE가 사용한 재현 스크립트 원본

```python
import sys, time
sys.path.insert(0, "/Users/David/DBMA")
from core.hybrid_candidate_pipeline import HybridQueryProcessor

hqp = HybridQueryProcessor()
queries = [
    ("관련 있음(신학)", "로마서 3장의 칭의 교리에 대해 설명해줘"),
    ("관련 있음(신학)", "예수님의 부활의 의미는 무엇인가"),
    ("관련 있음(신학)", "성령의 은사에 대한 바울의 가르침"),
    ("관련 있음(신학)", "은혜와 율법의 관계"),
    ("관련 없음(일상)", "오늘 서울 날씨 어때?"),
    ("관련 없음(일상)", "파이썬으로 정렬 알고리즘 짜는 법"),
    ("관련 없음(일상)", "저녁 메뉴 추천해줘"),
    ("관련 없음(일상)", "비트코인 가격 전망"),
]
for cat, q in queries:
    t0 = time.perf_counter()
    resp = hqp.process(q, query_id="verify-hybrid", k=5)
    elapsed = time.perf_counter() - t0
    results = resp.top_k_results
    top1 = results[0].final_score if results else None
    print(f"{cat:<16} {top1!s:<10} {elapsed:<10.2f} {q}")
```

실행 시 `USE_INVERTED_INDEX=true` 환경변수 필요 여부는 직접 코드 확인해서
판단할 것(`HybridQueryProcessor`를 직접 인스턴스화하면 플래그 체크를
우회할 수도 있음 — `is_enabled()`가 실제로 어디서 쓰이는지부터 확인).
