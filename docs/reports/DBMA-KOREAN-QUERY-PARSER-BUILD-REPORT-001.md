---
title: Build Report — 한국어 QueryParser
created: 2026-09-10
status: 구현 완료 · 전체 회귀 통과 · 커밋됨 (가드 교체 및 커밋 승인: Rev. Bang, 2026-09-10)
scope: core/retrieval.py, core/query_enhancements.py, tests/
baseline: `068ecfe`
venv: `~/envs/dbma311`
---

# Build Report — 한국어 QueryParser

감사 문서
[THEOLOGICAL-RESPONSE-QUALITY-AUDIT-2026-09-10](./THEOLOGICAL-RESPONSE-QUALITY-AUDIT-2026-09-10.md)
§9 우선순위 1번(§5 결함 A) 이행.

## 문제

한국어 질의가 랭킹에 들어갈 때의 상태:

| 항목 | 값 | 영향 |
|---|---|---|
| `intent` | 항상 `"unknown"` | 후속 랭킹 신호 손실 |
| `themes` | 항상 `[]` | TRS 테마 항 사망 |
| `keywords` | 항상 `[]` | **BM25 점수 항상 0** (하이브리드 가중치 0.25) |
| TRS 자카드 | 항상 0 | 한국어 문서 상대로도 0 |

`keywords`가 비던 것이 가장 컸다. `_extract_keywords()`가
`\b[a-zA-Z]{3,}\b`만 뽑았고, 그 결과가 `retrieve()` STEP 2에서
`bm25_score(parsed_query.keywords, content)`로 그대로 들어간다.

**핵심은 이것이 비대칭이었다는 점이다.** 문서 쪽 토큰화를 맡는
`_tokenize()`는 이미 kiwipiepy 형태소 분석기를 쓰고 있었다(P1 fix,
docs/TODO.md). 색인 쪽은 한국어를 알고 질의 쪽만 몰랐다.

## 변경

| 파일 | 내용 |
|---|---|
| `core/retrieval.py::_extract_keywords` | `_tokenize()` 재사용 — 질의/문서 토큰화 일치. 새 토크나이저를 만들지 않는다(같은 텍스트가 양쪽에서 다르게 쪼개지면 BM25가 성립하지 않음) |
| `core/retrieval.py::KOREAN_STOP_WORDS` | 신규 — kiwi가 남기는 기능적 어간·의문사·장절 마커 제거 |
| `core/retrieval.py::THEME_KEYWORDS` | 14개 테마 전부에 한국어 어휘 병기 — **교차언어 다리** |
| `core/retrieval.py::INTENT_PATTERNS` | 5개 intent에 한국어 표현 병기 |
| `core/retrieval.py::_detect_intent` 폴백 | 한국어 신학 용어 추가 |
| `core/retrieval.py::_lexical_tokens` | 신규 — TRS 자카드용. **한글이 있을 때만** 형태소 분석 |
| `core/query_enhancements.py` | 장 구분자 `장` → `[장편]` (2곳) — `시편 23편` |

### 설계 판단 두 가지

**1. 교차언어는 자카드가 아니라 테마가 담당한다.** `_thematic_relevance_score()`는
질의 쪽과 본문 쪽을 각각 검사해 둘 다 걸리면 1.0을 준다. 테마 어휘에 양쪽
언어를 병기하면 한국어 "은혜"와 영어 "grace"가 같은 테마에서 만난다. 반면
자카드는 한국어×영어에서 여전히 0인데, 이건 결함이 아니라 정직한 값이다.

**2. 한 음절을 길이로 자르지 않는다.** 두 음절 규칙을 세우면 "죄", "주"(주님),
"영"이 통째로 사라진다. 무의미한 한 음절 어간은 길이가 아니라
`KOREAN_STOP_WORDS`로 걸러낸다. 반대로 테마 어휘에는 한 음절을 넣지 않았다 —
부분 문자열 매칭이라 "영"이 "영어/영원"에, "법"이 "방법"에 걸린다.

## 실측 (수정 전 로직 재현 대조)

| 질의 | 대상 본문 | TRS 전 → 후 | BM25 전 → 후 |
|---|---|---|---|
| 고난 중의 인내와 하나님의 은혜 | 영어 | 0.3000 → **0.6000** | 0.0 → 0.0 |
| 고난 중의 인내와 하나님의 은혜 | 한국어 | 0.0000 → **0.8286** | 0.0 → **1.0** |
| grace and patience in tribulation | 영어 | 0.7455 → **0.7455** | 1.0 → **1.0** |
| grace and patience in tribulation | 한국어 | 0.3000 → **0.6000** | 0.0 → 0.0 |

**영어×영어는 완전히 불변**이다(회귀 없음). 개인 서재 경로(한국어×한국어)는
두 지표 모두 0에서 살아났다.

### 성능

| 구간 | 값 |
|---|---|
| 최초 파싱(Kiwi 모델 로드 포함) | 957 ms — 프로세스당 1회. `bm25_score`가 이미 같은 로드를 유발하므로 **신규 비용 아님** |
| 이후 파싱 | 0.23 ms/질의 |
| 영어 본문 `_lexical_tokens` | 17 µs/회 (한글 없음 → 기존 정규식 경로) |

theological scoring은 이미 측정된 병목이라(53k TSU에서 end-to-end의 82%)
`_lexical_tokens`를 한글 유무로 분기시켰다. NAE 영어 코퍼스는 기존 경로
그대로 돌아 추가 비용이 0이다.

## 가드 테스트 교체 — 확인 요청

`tests/test_parallel_retriever.py::TestCoreRetrievalUnmodified`가
`git diff core/retrieval.py`의 공백 여부를 검사하고 있어 이번 작업에서
실패했다. 의도(Sprint C의 ParallelRetriever 작업이 core/retrieval.py를
건드리지 않을 것)는 옳으나 구현이 의도와 어긋나 있었다:

1. **누가 고쳤는지 구분하지 못한다** — ParallelRetriever와 무관한 작업도 실패시킨다
2. **커밋하면 통과한다** — `git diff`는 작업 트리와 인덱스 비교라, 같은 변경도
   커밋 뒤엔 빈 diff다. 실제로 강제하던 것은 "수정하지 마라"가 아니라
   "커밋하지 않은 채 두지 마라"였다

대리 지표 대신 규약 자체(ParallelRetriever가 `ParsedQuery`/`RankedCandidate`를
재정의하지 않고 core에서 import해 쓰는가)를 검사하도록 교체하고
`TestCoreRetrievalReusedNotRedefined`로 이름을 바꿨다. core/retrieval.py를
누구도 임의로 수정하면 안 된다는 규칙은 ADR-001과 CLAUDE.md 승인 절차가
관장한다.

**교체 승인: Rev. Bang, 2026-09-10** — 의도적으로 설치된 가드였으므로 확인을 거쳤다.

## 검증

```
pytest tests/test_query_parser_korean.py   → 27 passed (신규)
pytest tests/ (전체)                        → 2,745 passed, 15 skipped, 0 failed (75s)
```

신규 테스트 27건 중 5건은 **영어 동작 보존** 전용이다 — 이게 깨지면 이 수정
자체가 회귀다.

## 범위 밖으로 남긴 것

- `_sermon_usability_score()`의 `academic_terms`가 영어 전용이다(SUS,
  theological 내 가중치 0.20). 한국어 문서는 이 항에서 점수를 못 받는다.
- 문맥 블록에 서지 정보 없음(감사 §5 결함 B) — ADR-024 영향 확인 필요
- 테마 14종 자체는 확장하지 않았다. "칭의/성화" 같은 조직신학 주제는
  여전히 어느 테마에도 안 걸린다 — 테마 목록 확장은 별도 판단 사항

## Git

CLAUDE.md CUE Operating Policy의 예외 조항이 "Retrieval Engine 변경"을 Git
자동화에서 제외하고 항상 승인을 요구한다. 2026-09-10 Rev. Bang 승인("가드
교체 승인한다. 커밋하고 푸시하라") 후 커밋·푸시했다.
