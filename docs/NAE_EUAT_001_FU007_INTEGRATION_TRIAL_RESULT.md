# FU-007 결과: 임시 통합 시도 (`main` ⊕ `dev/dbma-engine`) — 한국어 질의 번역 두 방식 비교

기준일 2026-09-29. 선행 문서: [FU-007 기준선 분기 조사](NAE_EUAT_001_FU007_BASELINE_DIVERGENCE_RESULT.md).
작업은 전부 별도 워크트리의 임시 브랜치에서 했다. `origin/main`·`origin/dev/dbma-engine`·`origin/feat/peb-v0.1`,
메인 체크아웃(`~/DBMA`), RAW·임베딩·Qdrant·Production Registry·ADR은 건드리지 않았다.
측정용 TSU 데이터셋·Tantivy 인덱스는 세션 scratchpad에 복사·신규 빌드했다(앱의 `output/bench` 미사용).

| 항목 | 값 |
|---|---|
| 병합 기준 | `origin/main` `d1c06d25` + `origin/dev/dbma-engine` `195189b8` (분기점 `39026424`) |
| 변형 A (main 번역 유지) | `tmp/fu007-keep-main-translation` `ab4f021c` (origin 푸시) |
| 변형 B (dev 번역 유지) | `tmp/fu007-keep-dev-translation` `97ec140e` (origin 푸시) |
| 변형 C (결합안, 8절) | `tmp/fu007-combined-translation` `b39572aa` (B 위 1커밋) |
| 측정 코퍼스 | `output/bench/tsu_dataset.jsonl` 사본, 119,595 TSU / 92문서, `dataset_sha256=bd246f22…` |
| 질의 | P0-5 24건(`scripts/p0_5_run_all.py::QUERIES` 그대로 import), k=5, 검색 단계만(생성 미실행) |

## 결론

1. **실제 충돌은 예측대로 3파일**이며 모두 해결 가능했다. 둘 중 하나를 고르는 것은 **호출부**(`hybrid_candidate_pipeline.retrieve`, `candidate_generator.search`)뿐이고, 번역과 무관한 양쪽 수정(dev 한국어 형태소 `_search` 필드, main 권말 색인 강등·UNK 폴백·구절 구문 가중)은 공존한다.
2. **후보 수·유보 수로는 두 방식이 구별되지 않는다.** 둘 다 24/24건 후보 30개, 근거 0건 유보 0건. 번역 없음 대조군은 10건 유보.
3. **관련성 대리 지표는 B(dev LLM) 55/120 > A(main 사전) 45/120 > 대조군 23/120**. 단 우열이 질의 유형별로 갈린다: A는 구절 표기·영어 병기 질의(B1·C1·C2·F1)에서, B는 목회·자연어 질의(A3·B3·C3·E1·E2·H2·H3)에서 앞선다. 상위 5건 겹침은 대부분 0~1건 — 두 방식은 사실상 다른 결과를 낸다.
4. **두 방식 모두 "없어야 할 근거"를 채운다.** 코퍼스에 없는 주제(G1~G3)에서 둘 다 5건을 반환했고, 대조군이 정직하게 유보하던 G3(화성 이주)도 번역 후 5건이 됐다(내용은 무관한 설교 본문).
5. **결합안 C(8절, 2026-09-29 재측정)**: B의 LLM 번역 + 원문 파싱의 구절 표기 확장 + 교단명 사전 보정. 대리 지표 **60/120**(A 45, B 55), 구절 장 표기 적중 **15/25**(A 17, B 3), 전체 회귀 **3,554 passed / 0 failed**. 세 방식 중 유일하게 회귀 무결이다.
6. **권고(결정은 사용자)**: 번역 방식은 **C 채택**. 단 검색 단계 대리 지표만 측정했으며 사람 채점·생성 단계 유보는 미측정이다. 병합 방향(방안 I/II)은 릴리스 라인 판단이 필요해 권고만 한다(7절).

## 1. 충돌 해결 내용

| 파일 | 충돌 형태 | 해결 (양 변형 공통) | 변형별 차이 |
|---|---|---|---|
| `core/query_translation.py` | add/add | 두 API가 이름이 겹치지 않아 한 모듈에 공존. dev의 `_HANGUL_RE`(자모 포함)만 `_HANGUL_ANY_RE`로 개명(main의 `_HANGUL_RE`와 충돌 회피) | 없음(모듈 동일) |
| `core/candidate_generator.py` | 3 hunk | import 양쪽(`verse_phrase_match_kind`, `_tokenize`). dev의 `_tokenize_for_index` + `_search` 필드 질의(형태소 대칭)는 유지 | A: 형태소 질의 앞에 `translated_terms` 덧붙임 + 구절 구문 가중(`_VERSE_PHRASE_BOOST`). B: dev 원본(번역어 덧붙임·구문 가중 없음) |
| `core/hybrid_candidate_pipeline.py` | 2 hunk | main의 `_demote_index_pages`(권말 색인 강등)·`fetch_k` 과다 수집 유지 | A: main 원본 Stage-1 분기. B: dev의 `_generate_candidates` + 언어 불일치 시 **Stage-1 전** LLM 번역 + 0건 시 재번역, `fetch_k` 적용 |

- 두 모듈을 공존시킨 이유: 자동 병합된 `core/retrieval.py`가 main API(`translate_query_terms`, `scripture_ref_phrases`)를, 자동 병합된 `ui/pages/chat.py`·`sermon_draft.py`가 dev API(`corpus_language_notice`)를 import한다. 어느 한쪽 모듈만 남기면 import가 깨진다.
- 인덱스 영향: dev의 형태소 토큰화는 Tantivy 스키마에 `title_search/content_search/author_search` 필드를 추가한다. **병합 후 앱의 기존 `output/bench/tantivy_index`는 재빌드가 필요하다**(이번 측정은 scratchpad에 새로 빌드).

## 2. 두 번역 구현 비교 (코드 판독)

| 항목 | A: main (`ae822afd`·`6bd97b2f`·`877b19b0`·`48502d9d`·`3f64027f`) | B: dev (`398bc5cd`) |
|---|---|---|
| 방식 | 닫힌 한→영 신학 용어 사전(120항목), 최장 일치 부분 문자열 | `llama3.1:8b`로 질의 전체 문장 번역(temperature 0) |
| 적용 시점 | `QueryParser.parse()` 단계, 원문 한국어는 유지하고 영어 용어를 **추가** | `HybridRetriever.retrieve()` Stage-1 **전**. 코퍼스 한국어 비율 < 20%면 한글 질의를 번역문으로 **교체** 후 재파싱. 0건이면 한 번 더 시도 |
| 구절 참조 | 로마숫자 장(“Romans viii. 28”) + 아라비아 숫자 + 구문 질의 가중, 서수 접두(요일 등) 강등 | 번역문 재파싱의 일반 구절 파싱만. 로마숫자 표기 확장 없음 |
| 적용 경로 | 두 경로 모두(`RetrievalEngine` 키워드, `CandidateGenerator` 질의) | `HybridRetriever`만. `USE_INVERTED_INDEX=false`의 `RetrievalEngine` 경로에는 적용 안 됨 |
| 결정성·캐시 | 결정적. `QUERY_TRANSLATION_VERSION`이 캐시 키에 포함 | 비결정 가능(모델 버전·데몬 상태). 캐시 키에 번역 모델·모드가 **없다** |
| 지연 | 실측 중앙값 15ms(검색 전체) | 실측 중앙값 266ms, 최대 336ms(검색 전체, 모델 상주 상태) |
| 실패 동작 | 사전에 없으면 번역어 0개(원문만) | 실패·비활성 시 None → 원문으로 검색(순손실 없음) |
| 병용 시 이중 번역 | B가 먼저 번역문으로 교체하면 재파싱된 영어 질의에 한글이 없어 A의 사전은 no-op이다. **이중 추가는 일어나지 않는다**(코드 판독). B의 LLM이 실패하면 A가 폴백처럼 동작한다 | 〃 |

## 3. 측정 결과 (P0-5 24건, 검색 단계)

### 3.1 후보·유보·지연

| 지표 | 대조군(번역 없음)¹ | A: main 사전 | B: dev LLM |
|---|---|---|---|
| 근거 0건 유보 | **10**건 (D1·D2·D3·E1·E2·E3·G3·H1·H2·H3) | 0건 | 0건 |
| 후보 수 합계(최대 30×24=720) | 420 | 720 | 720 |
| 번역 발동 | 0 | 사전 적중 24/24 | LLM 번역 24/24 |
| 검색 지연 중앙값 / 최대 | 13 / 52ms | 15 / 19ms | 266 / 336ms |

¹ 대조군 = 변형 B + `QUERY_TRANSLATION_FALLBACK=false`. A의 구절 구문 **재순위**(자동 병합된 `verse_phrase_match_kind` 부분)는 대조군에도 남아 있어 완전한 무번역은 아니다(후보 선정에는 영향 없음).

### 3.2 관련성 대리 지표 (상위 5건 중 질의 핵심 영어 용어 포함 건수)

**주의: CUE가 질의별로 정한 정규식 용어 적중이며 사람 채점이 아니다.** 용어가 있어도 내용이 무관할 수 있고(색인·OCR 잡음), 없어도 관련될 수 있다.

| 질의 | 대조군 | A | B | A∩B (상위 5 중복) |
|---|---|---|---|---|
| A1 로마서 8:1-4 | 0/5 | 4/5 | 5/5 | 1 |
| A2 창 1:26-27 형상 | 2/5 | 0/5 | 2/5 | 0 |
| A3 마 28:19-20 | 0/5 | 1/5 | 4/5 | 1 |
| B1 신자의 침례 | 1/5 | **5/5** | 1/5 | 0 |
| B2 칭의·성화 | 5/5 | 5/5 | 5/5 | 1 |
| B3 권징 | 5/5 | 1/5 | 3/5 | 0 |
| C1 롬 8장 설교 대지 | 0/5 | **5/5** | 1/5 | 0 |
| C2 히 11장 | 0/5 | **5/5** | 2/5 | 0 |
| C3 교회 언약 | 5/5 | 0/5 | 5/5 | 0 |
| D1 유아세례 비교 | 0/0 | 1/5 | 1/5 | 0 |
| D2 예정론 | 0/0 | 5/5 | 4/5 | 0 |
| D3 성찬 | 0/0 | 5/5 | 5/5 | 2 |
| E1 외도·이혼 상담 | 0/0 | 0/5 | **5/5** | 0 |
| E2 우울증 | 0/0 | 0/5 | 1/5 | 0 |
| E3 자녀 잃은 부모 | 0/0 | 0/5 | 0/5 | 0 |
| F1 Hiscox 집사 | 0/5 | 3/5 | 0/5 | 2 |
| F2 Dagg 교회 표지 | 0/5 | 0/5 | 0/5 | 0 |
| F3 Fuller 믿을 의무 | 5/5 | 5/5 | 4/5 | 3 |
| G1 AI 윤리 | 0/5 | 0/5 | 0/5 | 0 |
| G2 존 스미스 3세 | 0/5 | 0/5 | 0/5 | 0 |
| G3 화성 이주 | 0/0 | 0/5 | 1/5 | 0 |
| H1 악과 고통 | 0/0 | 0/5 | 0/5 | 0 |
| H2 가나안 진멸 | 0/0 | 0/5 | **4/5** | 0 |
| H3 창조·진화 | 0/0 | 0/5 | 2/5 | 0 |
| **합계(24건)** | **23/120** | **45/120** | **55/120** | |
| 합계(G 제외 21건) | 23/105 | 45/105 | 54/105 | |

### 3.3 관찰된 실패 양상 (상위 결과 판독)

- **A 사전의 부분 문자열 오역**: `침례교`→`baptism, immersion`(B3 권징·G1 AI 윤리), `장로교`→`elder`(D1). 최장 일치가 교단명 안의 용어를 잡는다. B3의 A 결과가 권징이 아니라 침례 본문으로 끌려간 원인.
- **A 사전의 어휘 공백**: 목회 질의(E1 `이혼/외도`, E2 `우울증`, H2 `가나안`, H3 `진화`)는 사전에 없어 `scripture, bible`·`god`·`theology` 같은 일반어만 붙고, 결과는 무관한 설교 본문이다.
- **B의 구절 표기 손실**: C1 “로마서 8장 … 설교 대지” → B 번역문 “Sermons based on Romans 8 …”이 `sermon`류 어휘로 끌려 『A History of Preaching』·설교학 교재가 상위를 차지했다. A는 `romans viii 8`로 Spurgeon 설교 본문을 잡았다. 코퍼스의 구절 표기는 79%가 로마숫자 장이다(main `scripture_ref_terms` 주석의 2026-09-26 실측).
- **양쪽 공통 — 없는 주제에도 5건**: G1~G3에서 둘 다 무관 본문 5건. 번역이 대조군의 정직한 0건(G3)을 잡음 5건으로 바꾼 사례가 있다. 생성 단계의 근거 지시문이 이를 유보로 처리하는지는 **미확인**(생성 미실행).
- F1·F2(Hiscox·Dagg)는 이 코퍼스(`output/bench`, 92문서)에 해당 문헌이 있는지 **미확인** — 두 방식 모두 해당 문헌을 상위에 올리지 못했다.

## 4. 전체 회귀

명령: `~/envs/dbma311/bin/python -m pytest tests -q --ignore=tests/test_nae_retrieval_bridge_integration.py` (각 변형 워크트리에서).

| 변형 | 결과 | 실패 내역 |
|---|---|---|
| A (main 번역) | 3 failed / 3,545 passed / 17 skipped | `test_query_translation_fallback.py`의 3건: 업프론트 번역 2건 + `test_book_filter_skipped_when_corpus_has_no_book_ids`. **모두 dev 설계를 검증하는 테스트**로, A 채택 시 설계상 실패 |
| B (dev 번역) | 1 failed / 3,547 passed / 17 skipped | `test_book_filter_unk_corpus_fallback.py::…::test_verse_query_falls_back_to_text_search` — 텔레메트리 라벨 표기 차이(main `route="hybrid"`+`route_fallback_from="bible"` vs dev `route="bible->hybrid"`). 동작 차이 아님 |

main 단독 기준선 3,490 passed 대비 증가분은 dev 쪽 테스트 유입분이다. 어느 변형도 무결 GREEN이 아니다 — 채택안에 맞춰 상대 쪽 테스트를 정리·수정하는 작업이 남는다.

부수 발견(책 필터): 같은 결함(`book_id`가 전부 UNK라 책 이름 질의가 0건)을 main은 “0건이면 책 필터를 빼고 재검색”(`candidate_generator`), dev는 “코퍼스에 book_id가 없으면 처음부터 필터를 얹지 않음”(`_corpus_has_book_ids`)으로 고쳤다. A는 main 방식만, B는 두 방식 모두 가진다(main 폴백은 자동 병합됨). 이것도 선택 사항이다.

## 5. `core/generation.py` 의미 중복 점검

- 텍스트 충돌 없음(병합 시 자동 병합 확인).
- **OBSERVED**: dev의 오염 처리 두 커밋 — `2a326b2b`(비한글 문자체계 오염을 삭제 대신 `□` 표식+고지), `78e51c7e`(근거 문맥에 없는 **소문자 라틴 단어** 고지). main의 `core/citation_verifier.py`는 `(출처: …)` 인용 문장 안의 3~4자리 숫자·**라틴 단어(4자 이상, 대문자 포함)**가 인용된 후보 본문에 있는지 경고한다.
- **EVIDENCE**: 병합본에서 `_run_citation_check`는 두 고지(오염·라틴)가 붙은 **뒤의** 답변을 검사한다(`generation.py` 블로킹·스트리밍 두 경로). 탐침 2건(인용 문장 + 라틴 고지 부착, 마침표 유무)에서 인용 검증 결과는 고지 유무와 무관하게 동일했다. `□` 표식은 라틴·숫자 판정 대상이 아니다.
- **IMPACT**: 기능은 서로 깨뜨리지 않는다. 다만 **같은 현상(근거에 없는 라틴 단어)을 두 기준으로 경고**한다 — dev는 답변 전체·소문자·사전 면제, main은 인용 문장·대문자 포함·인용 후보 본문 기준. 인용 문장 안의 근거에 없는 소문자 비사전어는 **두 경고가 동시에** 뜰 수 있다(실제 생성으로는 미확인).
- **RECOMMENDATION**: 병합 후 UI에서 두 경고의 문구·위치를 한 번 정리(중복 표시 방지)하는 후속 작업. 차단 로직은 둘 다 없으므로 급하지 않다.

## 6. 남은 위험

1. **번역이 정직한 유보를 잡음으로 바꾼다**(G3). 번역을 어느 쪽으로 택하든 “없는 주제는 없다고 말한다”는 원칙은 검색 단계가 아니라 생성 단계 게이트에 의존하게 된다 — 생성까지 포함한 재측정 필요.
2. B 채택 시: 모든 한국어 질의에 LLM 호출(+약 250ms, Ollama 상주 필요). 캐시 키에 번역 모델이 없어 모델 교체 후 이전 번역 결과가 캐시에서 재사용될 수 있다. `RetrievalEngine` 경로(`USE_INVERTED_INDEX=false`)에는 번역이 없다.
3. A 채택 시: 사전 부분 문자열 오역(교단명)과 목회 어휘 공백. 사전 확장은 끝이 없는 작업이다.
4. 병합 후 Tantivy 인덱스 재빌드 필수(스키마 변경). 앱 기동 시 자동 재빌드 여부는 **미확인**(`open_or_build_index`는 레코드 수 불일치 시 재빌드 — 스키마 불일치 감지 여부 미확인).
5. 대리 지표는 CUE 정의 정규식이다. 사람 채점(P0-5 방식)으로 확인하지 않았다.

## 7. 권고 (결정은 사용자)

**번역 방식** — OBSERVED: B가 대리 지표 우위(55 vs 45)이나 구절 표기 질의에서는 A가 우위, 두 결과는 거의 겹치지 않는다. EVIDENCE: 3.2·3.3절. IMPACT: 어느 한쪽만 택하면 다른 쪽이 잘 잡던 질의 유형을 잃는다. RECOMMENDATION:
- 1안(권고, **8절에서 측정 완료 — 변형 C**): B의 LLM 전체 번역을 기본으로 하되, **원문 파싱에서 얻은 A의 구절 표기 확장(`scripture_ref_terms`·`scripture_ref_phrases`)과 구문 가중을 번역 질의에 이어 붙인다.** A의 용어 사전은 LLM 실패 시 폴백으로만 남긴다(사전의 교단명 오역은 `침례교`·`장로교` 등을 사전 앞단에서 제외해 보정). 채택 전 같은 24건 + 생성 단계 유보까지 재측정.
- 2안: B 단독(대리 지표 최고, 구현 그대로). 구절 질의 품질 손실을 감수.
- 3안: A 단독(지연 0·결정적). 목회 질의 손실과 사전 유지비를 감수.

**병합 방향** — 방안 I(`dev → main`)와 II(`main → dev`)는 **이번 시도에서 결과 트리가 같다**(3-way 병합은 방향과 무관하게 같은 충돌·같은 해결을 요구한다). 차이는 어느 브랜치 이력에 병합 커밋이 남고 어느 라인이 릴리스 기준이 되느냐뿐이다. 베타 태그 계보(`beta-v1.3.0-rc6`)는 dev 쪽, GitHub 기본 브랜치·최근 PR은 main 쪽이므로 **릴리스 라인에 대한 HQ 판단이 선행돼야 한다.** 판단이 없다면, 기본 브랜치를 단일 통합 라인으로 만드는 방안 I 후 dev를 main으로 fast-forward하는 순서가 이후 분기 재발을 막는 데 유리하다는 정도로만 권고한다.

## 부록: 재현

```
git worktree add -b tmp/fu007-keep-main-translation <dir> origin/main && git -C <dir> merge origin/dev/dbma-engine
# 충돌 해결은 1절 표대로 (브랜치 ab4f021c / 97ec140e 참고)
# 측정 하네스·채점 스크립트: docs/fu007_trial/fu007_compare.py, fu007_score.py
#   (같은 디렉터리의 bench/에 tsu_dataset.jsonl·tsu_manifest.json 사본을 두고 변형 워크트리에서 실행)
#   python fu007_compare.py main cmp_main.json  → fu007_score.py none main dev comb, fu007_passage.py none main dev comb
```

## 8. 결합안(C) 재측정 — 2026-09-29

브랜치 `tmp/fu007-combined-translation` `b39572aa` (= 변형 B `97ec140e` + 1커밋). 같은 코퍼스 사본·인덱스·24건·k=5.

### 8.1 변경 내용

| 파일 | 변경 |
|---|---|
| `core/hybrid_candidate_pipeline.py` | `_carry_scripture_notation()` 신설: LLM 번역문 재파싱 결과에 **원문 한국어 파싱의 구절 참조** 기준으로 로마숫자 장 terms(`scripture_ref_terms`)·구문(`scripture_ref_phrases`)을 잇는다. 업프론트 번역·0건 재번역 두 곳에 적용. 사전 번역어는 잇지 않는다(이중 추가 방지). bible 폴백 텔레메트리를 main 표기(`route`+`route_fallback_from`)로 통일 |
| `core/candidate_generator.py` | A의 `translated_terms` 추가·구절 구문 가중(`_VERSE_PHRASE_BOOST`) 복원(형태소 토큰화와 공존). LLM 번역 실패 시 원문 파싱의 사전 번역어가 그대로 쓰여 **사전이 폴백**이 된다 |
| `core/query_translation.py` | 교단명 항목 추가(`침례교`→baptist, `장로교`→presbyterian, `감리교`, `루터교`, `성공회`) — 3.3절 부분 문자열 오역 보정. `QUERY_TRANSLATION_VERSION` 3→4 |
| `tests/test_fu007_combined_translation.py` | 신규 6건: 로마숫자 장·구문 이어붙이기, 사전어 비전파, 구절 없는 질의 no-op, 번역문이 참조를 누락해도 원문 참조 사용, 교단명 오역 방지, LLM 실패 시 사전 폴백 |

### 8.2 결과

| 지표 | 대조군 | A main | B dev | **C 결합** |
|---|---|---|---|---|
| 근거 0건 유보 | 10 | 0 | 0 | 0 |
| 후보 수 합계 | 420 | 720 | 720 | 720 |
| 관련성 대리 지표(24건) | 23/120 | 45/120 | 55/120 | **60/120** |
| 〃 (G 제외 21건) | 23/105 | 45/105 | 54/105 | **59/105** |
| 구절 장 표기 적중(구절 질의 5건 × 상위 5)¹ | 0/25 | **17/25** | 3/25 | 15/25 |
| 검색 지연 중앙값 | 13ms | 15ms | 266ms | 약 290ms² |
| 전체 회귀 | — | 3 failed / 3,545 passed | 1 failed / 3,547 passed | **0 failed / 3,554 passed** / 17 skipped |

¹ `docs/fu007_trial/fu007_passage.py`: 상위 5건 본문에 대상 장 표기(“Romans viii”, “Rom. 8”, “Hebrews xi” 등)가 있는 건수. 서수 접두(1 John 등)는 구분하지 않는다. CUE 정의 지표이며 사람 채점이 아니다.
² 24건 로그 값 187~390ms. B 측정과 다른 시점이라 지연 차이(약 +20ms)는 오차 범위일 수 있다(미확정).

구절 장 표기 적중 세부:

| 질의 | A | B | C |
|---|---|---|---|
| A1 롬 8:1-4 | 5 | 2 | 5 |
| A2 창 1:26-27 | 0 | 0 | 0 |
| A3 마 28:19-20 | 2 | 0 | 0 |
| C1 롬 8장 | 5 | 1 | 5 |
| C2 히 11장 | 5 | 0 | 5 |

### 8.3 판독

- **LLM 번역문은 B와 24/24건 동일**했다(temperature 0). 따라서 B↔C 차이는 구절 표기 확장만의 효과다. 상위 5건이 B와 달라진 질의는 구절 참조가 있는 A1·A2·C1·C2 4건뿐이고, 나머지 20건은 B와 5/5 동일하다 — **목회·자연어 질의의 B 이점은 그대로 유지된다.**
- C1: B는 『A History of Preaching』·설교학 교재가 상위였으나 C는 로마서 8장 Spurgeon 설교·『Morning by morning』(Romans viii. 12) 등으로 바뀌었다. C2: B는 히 3·10·12장, C는 히 xi. 9/22/24 본문.
- A1은 키워드 대리 지표가 5→4로 줄었지만 장 표기 적중은 2→5로 늘었다(C의 상위 5건 중 4건이 Romans viii. 1 본문, B는 권말 색인 1건 포함).
- A3(마 28:19-20)은 A만 2/5를 얻었고 C는 0/5다. 구절 확장은 C에서도 적용됐고(`xxviii`·구문 4개 확인) 경로도 셋 다 `hybrid`였다. Stage-2 순위 단계에서 밀린 것으로 보이나 원인은 **미확인**.
- B1(신자의 침례)·F1(Hiscox 집사)의 A 이점은 C에서도 회복되지 않는다. 이 두 질의는 구절이 아니라 질의에 **병기된 영어**(believer's baptism, deacon)와 원문 한국어를 함께 검색하는 A의 “추가” 방식이 유리했던 경우로 보인다(추정, 미검증).
- G1~G3(없는 주제)는 C도 B와 같이 5건을 반환한다 — 6절 1번 위험은 그대로다.

### 8.4 권고 갱신 (결정은 사용자)

**OBSERVED**: C는 대리 지표 최고(60/120), 구절 장 표기 적중은 A와 비슷하고(15 vs 17) B보다 크게 높으며(3), 유일하게 전체 회귀가 무결하다.
**EVIDENCE**: 8.2 표, B와 번역문 24/24 동일(변수 통제), 신규 테스트 6건.
**IMPACT**: A·B 중 하나만 택할 때 생기던 질의 유형별 손실 대부분이 사라진다. 남는 손실은 A3·B1·F1 3건(원인 일부 미확인)과 지연(+약 250ms, LLM 호출)이다.
**RECOMMENDATION**: 번역 방식은 **C 채택을 권고**한다. 채택 전·후 남은 확인:
1. 사람 채점(P0-5 방식) 또는 생성 단계까지 포함한 24건 재실행 — 특히 G1~G3가 생성 단계에서 유보되는지.
2. 캐시 키에 LLM 번역 모드·모델을 넣을지(6절 2번). C에서도 미해결.
3. `RetrievalEngine` 경로(`USE_INVERTED_INDEX=false`)는 여전히 사전 번역만 쓴다(기본값 true라 영향 제한).
4. C는 검색 코어(Retrieval Engine 소관) 변경이다. 실제 통합 라인 반영은 CUE Operating Policy상 **별도 승인 대상**이며, 반영 시 C1 Review 요청 시점에 해당하는지 판단이 필요하다.
