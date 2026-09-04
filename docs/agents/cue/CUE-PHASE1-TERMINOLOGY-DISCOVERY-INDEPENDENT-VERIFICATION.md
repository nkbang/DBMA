# CUE Independent Verification — PHASE 1: Terminology Discovery

**검증 대상**: C1 `PHASE 1 — TERMINOLOGY DISCOVERY: Independent Forensic Audit Report`
**검증자**: CUE (Independent Verification, read-only)
**검증일**: 2026-08-25
**Governing Authority**: `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`
**Mode**: DISCOVER — 이 문서는 구현을 수행하지 않는다.

---

## 0. 사전 확인 — 문서 소재 및 전제 불일치

C1의 `PHASE 1 — TERMINOLOGY DISCOVERY: Independent Forensic Audit Report` 원문 파일을
저장소 전체(`docs/`, `output/`, `.automation/`, `NAE/`)에서 검색했으나 **발견하지 못했다**
(`output/c1_forensic_audit_report.md`, `output/c1_pilot_001_forensic_audit.md`는 존재하나
둘 다 `Dagg_Church_Order` corpus의 별개 Phase 2 forensic audit이며 terminology와 무관).
C1 보고서가 파일로 커밋되지 않고 채팅으로만 전달되었을 가능성이 높다. 따라서 이 검증은
verification 지시문 자체에 명시된 C1 claim(§3.1~§7)을 기준으로 코드·데이터를 독립
재확인하는 방식으로 진행했다.

**전제 불일치 발견**: 지시문 §1은 "ADR-029 Status: `ACCEPTED`"라고 명시하나, 실제
`docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`의 Status는
`DRAFT — 사용자 승인 필요`이다 (git 상 `??` untracked, 2026-08-25 생성). §11 Next Steps도
"이 ADR을 사용자(HQ)가 검토·승인"을 미완료 항목으로 남겨두고 있다. 이 문서 전체가
근거로 삼는 governing document가 아직 사용자 승인을 받지 않은 상태다 — Gate Judgment에
반영한다.

---

## 1. Verdict

# **C. CONDITIONAL**

C1이 제시한 개별 사실관계(코드 구조 존재 여부, TSU 필드 미사용, 한국어 테마 탐지 실패)는
전부 코드·실행·프로덕션 데이터로 강하게 확인된다. 그러나 (a) governing ADR이 아직
DRAFT 상태이고, (b) "BGE-M3 benchmark" gate 권고가 ADR-029 자신이 정의한 Phase 구조와
맞지 않게 PHASE 1과 PHASE 4를 혼동하고 있으며, (c) `crosswalk.yaml`을 terminology 구조로
분류한 것은 오분류이고, (d) 현재 corpus가 실제로는 cross-lingual embedding을 쓰고 있지
않다는(§7 아래 참고) 사실이 benchmark 시급성 판단에 누락되어 있다. 이 네 가지를
보완해야 Gate를 깨끗하게 닫을 수 있다.

---

## 2. C1 Claim-by-Claim Verification

| # | C1 Claim | 검증 결과 | 근거 |
|---|---|---|---|
| 1 | `BOOK_ID_TO_NAMES` 등 7개 구조가 실존한다 | **CONFIRMED** | §3 |
| 2 | TSU JSONL에 `themes`/`doctrine_category`/`baptist_theme` 필드가 존재하나 비어있다 | **CONFIRMED** | §4.1 |
| 3 | Qdrant production payload에 이 필드들이 없거나 유효하게 쓰이지 않는다 | **CONFIRMED (더 강하게)** — payload에 아예 존재하지 않음 | §4.2 |
| 4 | `THEME_KEYWORDS`가 English-only이며 한국어 query에서 theme detection이 실패한다 | **CONFIRMED — 실행으로 재현** | §5 |
| 5 | Terminology layer가 "현재는 필요 없음(conditional)" | **PLAUSIBLE, 단 근거 보강 필요** | §9 |
| 6 | PHASE 1 Gate: BGE-M3 benchmark 대기 | **CONFIRMED되지 않음 — scope 오류 발견** | §7, §9 |

---

## 3. Current-State Findings — 7개 구조

| 구조 | 실존 | 위치 | 책임 | EN/KO | Terminology 관련성 |
|---|---|---|---|---|---|
| `BOOK_ID_TO_NAMES` | ✅ | `core/retrieval.py:202` | 성경 66권 book_id ↔ 이름 alias 매핑 (`QueryParser`, `BibleIndex`, `query_enhancements.py`) | **완전 이중언어** (66권 전부 EN+KO 별칭 보유) | Alias mapping — proper-noun 수준, 신학 개념 아님 |
| `THEME_KEYWORDS` | ✅ | `core/retrieval.py:288` | 14개 신학 테마 키워드 매칭 (`_extract_themes`, `_thematic_relevance_score`, `_summarize_theology`) | **English-only, 한국어 0건** | 정확히 C1 claim의 핵심 대상 |
| `DOCTRINE_CATEGORY` | ✅ | `core/sermon/doctrine_vocabulary.py:14` | 설교 초안 교리 검토 LLM 프롬프트(`doctrine_filter.py`)의 고정 어휘, ADR-009로 잠긴 값 | English 라벨만(Trinity, Christology 등), 사용자 승인 없이 CUE/C1이 수정 금지 | RAG retrieval과 무관한 별도 기능(SIL 설교 검토) |
| `BAPTIST_THEME` | ✅ | `core/sermon/doctrine_vocabulary.py:27` | 상동 (개혁파 침례교 강조점 10개) | English 라벨만 | 상동 |
| `_THEOLOGICAL_CONCEPTS` | ✅ | `NAE/smith_activation.py:64` | Smith Bible Dictionary 활성화 여부 판단(boolean gate)의 매칭 패턴 | **이중언어** (은혜/grace, 언약/covenant, 구원/salvation 등) | Smith 책임 영역(§6) — terminology 매핑이 아니라 activation trigger |
| `_BIBLICAL_PROPER_NOUN_PATTERNS` | ✅ | `NAE/smith_activation.py:30` | 상동, 고유명사(인명/지명) 매칭 | **이중언어** (모세/Moses, 다윗/David 등) | 상동 |
| `crosswalk.yaml` | ✅ | `NAE/metadata/crosswalk/crosswalk.yaml` | **Registry `source_id` ↔ corpus `canonical_id` 식별자 매핑** (예: `BAP-CHURCH-DAGG-001` → `Dagg_Church_Order`). 레코드 2건만 존재 | 언어 무관 — 문서 식별자 매핑이지 용어 번역이 아님 | **오분류 위험**: terminology-like로 나열됐지만 실제로는 한국어/영어 신학 용어와 전혀 무관한 문서 identity crosswalk. C1 목록에 포함됐다면 이 항목은 제외해야 함 |

**핵심 발견**: 이중언어(EN+KO) proper-noun/개념 매칭은 이미 두 곳(`BOOK_ID_TO_NAMES`,
Smith의 `_THEOLOGICAL_CONCEPTS`/`_BIBLICAL_PROPER_NOUN_PATTERNS`)에서 검증된 패턴으로
존재한다. 반면 **테마 기반 검색 스코어링(`THEME_KEYWORDS`)만 English-only로 남아있다** —
즉 "한국어를 전혀 다루지 못하는 시스템"이 아니라 "한 개의 특정 하위 스코어링 컴포넌트만
한국어를 다루지 못하는" 훨씬 좁은 문제다.

---

## 4. TSU Metadata Verification

### 4.1 TSU JSONL — 필드 존재 여부

`core/tsu_builder.py:367,436-437`:
```python
"themes": [],                    # (레코드 생성 시점, line 367)
...
record["theological_claim"] = None
record["doctrine_category"] = []  # line 436
record["baptist_theme"] = []      # line 437
```
소스 주석(431행)이 명시적으로 확인: *"[ADR-009] Additive-only ... including the
pre-existing unused "themes" field, which this intentionally does not reinterpret ...
no tagging logic populates these yet, because the doctrine vocabulary is a separate,
not-yet-approved decision"*. → **필드는 존재하나 어떤 코드 경로도 값을 채우지 않는다.
이는 우연한 누락이 아니라 의도적으로 문서화된 미구현 상태다.**

### 4.2 Qdrant Production Payload — 실측

로컬 Qdrant(`http://localhost:7333`, read-only GET/scroll만 수행)를 직접 조회했다:
```
GET /collections/nae_tsu_v1 → points_count: 3319, status: green
POST /collections/nae_tsu_v1/points/scroll (limit=2, with_payload=true)
```
실제 payload 키 전체: `tsu_id, book, author, identifier, source_identifier, doctrine,
page, paragraph, sentence, claim, source_text, scriptures, citations, review_status,
llm_score, parser_score, evidence_score, citation_score, overall_score, duplicate_of,
tsu_schema_version, collector_version, canonical_version, source_id, author_id,
work_id, edition_id, volume_id, publication_year, source_type, copyright_status,
usage_permission, access_control, tsu_access, metadata_schema_version, category,
category_status, citation_policy, citation_policy_status, metadata_provenance`

`themes`, `doctrine_category`, `baptist_theme` — **셋 다 payload에 존재하지 않는다.**

원인도 코드에서 확인됨: `NAE/pipeline/index/qdrant_store.py:40-87`의 `build_point()`가
Qdrant에 올릴 payload 키를 **명시적 화이트리스트**로 하드코딩한다 — TSU record dict를
그대로 pass-through하지 않는다. 이 화이트리스트에 애초에 `themes`/`doctrine_category`/
`baptist_theme`가 없다. 즉 TSU JSONL에 값이 채워지더라도(현재는 항상 `[]`) 이 화이트리스트가
수정되지 않는 한 Qdrant에는 절대 반영되지 않는다.

**주의 — `doctrine`(단수) 필드는 실제로 존재하고 채워져 있다** (예: `"doctrine": "Ecclesiology"`).
이는 `DOCTRINE_CATEGORY`(core/sermon 쪽 복수형 리스트 필드명)와는 다른, NAE TSU 파이프라인
자체의 별도 분류 필드다. C1 보고서가 `doctrine_category`(TSU 스키마의 dead field)와
`doctrine`(실제 채워지는 payload 필드)을 혼동하지 않았는지 원문 확인이 필요하다 —
현재 확보한 지시문 텍스트만으로는 이 구분이 명시돼 있는지 알 수 없다.

### 4.3 세 영역 구분 (지시문 3.2 요구사항)

```
TSU JSONL 존재?        themes=[] 존재(dead) / doctrine_category=[] 존재(dead) / baptist_theme=[] 존재(dead)
Qdrant payload 존재?    셋 다 부재 (build_point() 화이트리스트에 없음) — 실측 확인
Retrieval 실사용?       불사용. 단, core/retrieval.py의 _thematic_relevance_score()는
                        TSU.themes를 읽는 게 아니라 tsu["content"] 원문 텍스트를
                        THEME_KEYWORDS로 직접 재스캔한다(§5.3) — 별도의 라이브 스코어링
                        경로이지 메타데이터 필드 소비가 아니다.
```
**C1의 3단 구분은 정확하다.** 오히려 실측 결과 "존재하지 않거나 유효하게 사용되지
않는다"는 C1의 완곡한 표현보다 더 확정적으로 말할 수 있다 — Qdrant payload에는
**존재 자체가 아예 없다.**

---

## 5. Korean Theme Detection — 실행 검증

`core.retrieval.QueryParser().parse(query)`를 직접 호출해 실측했다(코드 inspection이
아니라 실제 파서 실행):

```
'은혜'                              -> themes=[]
'언약'                              -> themes=[]
'구원'                              -> themes=[]
'믿음'                              -> themes=[]
'로마서와 은혜에 대해 알려줘'          -> themes=[]
'grace'                            -> themes=['mercy']
'romans and grace'                 -> themes=['mercy']
'What does Romans say about grace?' -> themes=['mercy']

# 대조군 — 책 이름 인식은 정상 작동(BOOK_ID_TO_NAMES가 이중언어이므로)
'로마서 8:28'         -> refs=[('ROM', 8, 28)]  (theme은 여전히 [])
'romans 8:28'        -> refs=[('ROM', 8, 28)]
'로마서 8:28 은혜'     -> refs=[('ROM', 8, 28)]  (theme은 여전히 [])
```

**C1의 claim은 코드 inspection이 아니라 실행 결과로 재확인됐다.** 모든 한국어 입력에서
theme=[]이고, 대응하는 영어 입력에서는 정상적으로 테마가 검출된다. 반면 책 이름(로마서)
인식은 한국어에서도 정상 작동 — 이는 `BOOK_ID_TO_NAMES`가 이중언어이기 때문이며,
theme 탐지 실패가 QueryParser 전체의 한국어 무능력이 아니라 `THEME_KEYWORDS` 딱 한
컴포넌트에 국한된 문제임을 정확히 특정한다.

---

## 6. Theme Detection vs Cross-Lingual Retrieval — 분리 검증

`core/retrieval.py`의 실제 파이프라인 순서(RetrievalEngine.retrieve, 약 1500~1600행)를
추적한 결과, A와 B는 **아키텍처적으로 분리된 별개 스테이지**임을 확인했다:

- **STEP 3 (line ~1524)**: `semantic_embedder.encode(...)` — BGE-M3(추정) 임베딩 기반
  cosine similarity. Query embedding vs `tsu["content"]` embedding. **THEME_KEYWORDS와
  무관하게 독립 작동**. 이 단계가 실제 "Korean query → English/한국어 corpus retrieval"의
  recall을 좌우한다.
- **STEP 4 (line ~1560, `compute_theological_score`)**: `final_score = 0.45·SSA +
  0.35·TRS + 0.20·SUS` — STEP 3에서 이미 뽑힌 후보군(`capped_pool`)에 대한 **재랭킹
  전용 스코어**. TRS(`_thematic_relevance_score`, THEME_KEYWORDS 기반)가 이 중 35%
  가중치를 차지한다.
- `_thematic_relevance_score()`(line 1116)는 `tsu["themes"]` 메타데이터가 아니라
  `tsu["content"]` 원문과 query 원문을 **둘 다 직접 재스캔**한다. `hits_query`(한국어
  query에서는 항상 False) 또는 `hits_content`만 맞아도 0.5점을 주므로, 한국어 query라도
  후보 content가 영어 신학 어휘를 포함하면 TRS가 완전히 0이 되지는 않는다 — 다만
  query·content 모두 일치할 때 받는 만점(1.0)은 구조적으로 받을 수 없다.

**결론**: C1이 A(query-side theme extraction)의 실패를 B(cross-lingual semantic
retrieval)의 실패로 혼동했다면 그것은 오류이나, 확보한 지시문 텍스트 자체(§3.4)는
이미 이 둘을 정확히 분리해서 검증하라고 요구하고 있다 — 즉 **분리 자체는 지시문
수준에서 이미 올바르게 설계돼 있고, 코드 추적 결과도 이 분리가 실제로 타당함을
확인한다.** A의 실패는 재랭킹 단계의 35% 가중치 컴포넌트 하나에 국한되며, 후보군
자체(recall)는 STEP 3 임베딩 유사도가 담당하므로 A 실패가 B 실패를 의미하지 않는다.

---

## 7. BGE-M3 Cross-Lingual Benchmark Necessity

### 7.1 기존 문서화된 인식

`NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md`(§1, 이번 검증 이전부터 존재하던 문서)에
이미 다음 문장이 있다: *"현재 BGE-M3 임베딩은 다국어 지원이지만 완벽한 교차언어 검색
성능은 검증되지 않았다 — 이것도 벤치마크가 측정해야 할 대상 중 하나다."* — 이는 C1의
claim이 새로운 발견이 아니라 프로젝트에 이미 기록된 인식과 일치함을 보여준다.

### 7.2 결정적 발견 — 현재 corpus는 실제로 cross-lingual embedding을 쓰지 않는다

`NAE/pipeline/index/indexer.py:115-124`:
```python
claim_text = record.get("claim")
...
vector = embed_client.embed_text(claim_text, content_hash=content_hash)
```
임베딩 대상은 `source_text`(영어 원문)가 아니라 **`claim`(한국어로 이미 paraphrase된
필드)**다. 실제 Qdrant payload 샘플에서도 `claim`은 한국어("교회에서 부족한 것을
정돈하고...")이고 `source_text`만 영어 원문("Se a That thou shouldst set in order...")
이다. 즉 **현재 프로덕션은 한국어 query ↔ 한국어 claim embedding 매칭**이며, 진짜
"한국어 query → 영어 corpus 직접 cross-lingual 매칭"을 실행하고 있지 않다.
`pilot_001_gold_v1_results.jsonl`(10문항, 전부 한국어, recall@5=1.0, MRR=1.0)의 완벽한
성능도 이 구조 때문일 가능성이 높다 — cross-lingual 능력이 아니라 TSU 생성 시점의
한국어 claim 추출 품질을 측정한 결과에 더 가깝다.

이 사실은 benchmark 시급성 판단에 직접 영향을 준다: **기존 corpus(Dagg/Hiscox/Smith)는
cross-lingual 검색에 의존하지 않으므로, 이 corpus만 놓고 보면 BGE-M3 cross-lingual
성능은 지금 당장 검증하지 않아도 실사용에 지장이 없다.** 반면 ADR-029 PHASE 3(NAC)가
같은 "한국어 claim 추출" 패턴을 재사용할지, 아니면 규모상 영어 원문을 직접 임베딩하는
방식으로 바뀔지는 **아직 결정되지 않은 PHASE 3 설계 문제**다 — 후자라면 benchmark가
반드시 필요해진다.

### 7.3 ADR-029 자체의 Phase 배치 확인

ADR-029 §3(Fixed Pipeline)을 직접 재확인:
```
PHASE 1: Korean Theological Terminology Corpus  → Gate: canonical term validation PASS
PHASE 2: Terminology retrieval / Korean↔English mapping validation → Gate: cross-lingual mapping accuracy PASS
PHASE 3: NAC Pilot (1 volume)                    → Gate: file/metadata/TSU quality audit PASS
PHASE 4: Cross-lingual Korean→English retrieval benchmark → Gate: Korean query → English NAC Top-5/Top-10 PASS
```
**"BGE-M3 cross-lingual retrieval benchmark"는 ADR-029 자신이 PHASE 4(NAC 대상)의
고유 Gate로 명시적으로 배치해뒀다 — PHASE 1의 Gate가 아니다.** PHASE 1의 정의된 Gate는
"canonical term validation PASS"(권위 있는 용어 출처 확인)이며 검색/임베딩 성능과
무관하다.

### 7.4 판정

# **USEFUL BUT NOT GATING** (PHASE 1에 대해서는)

근거:
1. ADR-029 §3이 이 benchmark를 PHASE 4 고유 Gate로 이미 배치해뒀다 — PHASE 1 Gate
   ("canonical term validation")는 검색 성능과 무관한 출처/권위 검증이다.
2. 현재 corpus는 §7.2에서 확인했듯 실제로 cross-lingual embedding을 쓰고 있지 않다 —
   따라서 "BGE-M3가 가능하다는 사실만으로 production readiness를 가정하지 말라"(ADR-029
   §5.2)는 원칙은 **PHASE 3 NAC**에는 직접 적용되지만, PHASE 1(terminology corpus 구축
   자체, 순수 데이터 큐레이션 작업)에는 애초에 해당하지 않는다.
3. Production mutation 없이 수행 가능한가 — 가능하다: 기존 read-only Qdrant + 기존
   `NAE/benchmark/datasets/gold_benchmark_v1.jsonl`(5문항, 이미 한국어/영어 혼합으로
   설계돼 있으나 `"evaluation": {"status": "pending"}`으로 미실행 상태)로 재임베딩·
   재색인 없이 측정 가능하다. 다만 이 benchmark는 PHASE 4(NAC) 설계에 유용한 것이지
   PHASE 1을 여는 데 필수 전제조건은 아니다.

**따라서 C1의 "PHASE 1 Gate: WAIT FOR BGE-M3 BENCHMARK" 권고를 문자 그대로 채택하면
ADR-029 자신의 Phase 구조와 어긋난다.** 다만 "terminology layer 구현에 실제로
착수하기 전에, 이미 존재하는 것과 다른 방식의 검증이 먼저 필요하다"는 취지(DISCOVER
≠ IMPLEMENT)는 타당하다 — 정확한 근거는 benchmark가 아니라 §4(TSU 필드 dead)와
§5(THEME_KEYWORDS 영어전용)이지, cross-lingual retrieval 자체가 아니다.

---

## 8. Smith Boundary Verification

`NAE/smith_activation.py` 코드로 직접 확인:

| 질문 | 답 | 근거 |
|---|---|---|
| Proper noun activation은 Smith 책임인가? | **예** | `_BIBLICAL_PROPER_NOUN_PATTERNS`(30행)가 `should_activate_smith()`의 boolean gate로만 쓰임 — 이중언어(모세/Moses 등) |
| Theological concept activation은 Smith 책임인가? | **예** | `_THEOLOGICAL_CONCEPTS`(64행), 상동, 이중언어(은혜/grace 등) |
| Cross-lingual terminology alignment는 Smith와 별개 문제인가? | **예, 별개다** | Smith는 "이 query가 사전을 필요로 하는가"(boolean)만 판단하고, "어떤 한국어 용어가 어떤 authoritative 영어 용어와 대응하는가"는 전혀 하지 않는다. `should_activate_smith()`는 term_id/definition/provenance 같은 구조를 전혀 반환하지 않는다 |
| 새 terminology layer가 Smith 기능을 중복 구현할 위험 | **낮음, 단 alias 데이터 불일치 위험은 있음** | Smith의 정규식 목록과 향후 terminology dictionary가 서로 다른 한국어 표기(예: "예수"/"예수님")를 쓰면 두 시스템의 판단이 어긋날 수 있음 — 기능 중복이 아니라 데이터 동기화 문제 |

PHASE 0 Smith가 `VERIFIED / LOCKED` 상태이므로 이번 검증에서 `NAE/smith_activation.py`에
대한 수정을 제안하지 않았다 — 읽기만 수행.

---

## 9. Taxonomy Assessment

세 개념 구분:
```
Taxonomy(계층적 카테고리 체계)     — DOCTRINE_CATEGORY(7개)/THEME_KEYWORDS(14개)가
                                    가장 가까우나 둘 다 flat list이며 계층 없음.
                                    각각 별도 기능(설교검토/재랭킹)에 국한된 지역적
                                    vocabulary — 범용 taxonomy가 아님.
Terminology dictionary(정의+출처) — 코드베이스 전체에서 term_id/korean_term/
                                    english_term/definition/source/provenance/
                                    confidence 구조를 가진 것은 전혀 없음. ADR-029
                                    PHASE 1이 겨냥하는 게 바로 이 공백.
Alias mapping(동의어/이명 묶음)   — BOOK_ID_TO_NAMES(완전 이중언어, 66권)와 Smith의
                                    proper-noun 패턴(이중언어)이 이미 이 패턴으로
                                    검증된 상태로 존재.
```

**판단**: 현재 필요한 최소 abstraction은 이미 "alias mapping" 형태로 두 곳에서 검증됐다.
`THEME_KEYWORDS`가 겪는 문제(§5)는 **ADR-029급 authoritative terminology dictionary가
아니라, 이미 검증된 alias-mapping 패턴을 하나 더 복제하는 것으로 해결 가능한 좁은 문제**
— 단, 이는 "지금 구현하라"는 뜻이 아니라 "PHASE 1의 요구 스펙(출처·provenance 포함
authoritative dictionary)과 THEME_KEYWORDS 버그 수정에 필요한 스펙(단순 alias list)이
서로 다른 스케일의 문제"라는 관찰이다. Taxonomy는 **NOT REQUIRED** — 현재 어떤 기능도
계층적 분류를 요구하지 않는다. 이 판단은 C1의 "Taxonomy NOT REQUIRED"와 일치한다.

---

## 10. Governance Boundary Check

이번 검증에서 다음을 수행하지 않았음을 확인한다:
- taxonomy/terminology dictionary 구현: **미수행**
- Smith 수정: **미수행** (읽기만)
- retrieval engine 수정: **미수행** (읽기만)
- TSU/corpus 수정: **미수행**
- embedding/재임베딩/cache rebuild: **미수행**
- Qdrant mutation: **미수행** — `points/scroll`(POST이나 read-only 조회 엔드포인트)과
  collection info GET만 수행, upsert/delete 없음
- production configuration 변경: **미수행**
- ADR-029 변경: **미수행** — 단, ADR-029 Status가 실제로는 DRAFT임을 §0/§1에 기록함(변경이 아니라 기존 상태 확인)

파일 시스템에는 이 보고서 1개 파일만 신규 생성했다(`docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md`). 기존 파일은 어느 것도 수정하지 않았다.

---

## 11. Findings / Discrepancies

1. **[중요] ADR-029 Status 불일치** — 지시문은 ACCEPTED를 전제하나 실제로는 DRAFT.
   사용자 승인 여부를 먼저 확인해야 이 Gate Judgment가 공식적으로 유효해진다.
2. **[중요] Gate 권고의 Phase 범위 오류** — "BGE-M3 benchmark"는 ADR-029 §3에서 PHASE 4
   Gate로 이미 정의돼 있다. PHASE 1 Gate("canonical term validation")에 이를 요구하는
   것은 ADR 자신의 구조와 불일치한다.
3. **[경미] `crosswalk.yaml` 오분류 가능성** — 이 파일은 문서 식별자(source_id ↔
   canonical_id) 매핑이며 한국어/영어 신학 용어 매핑과 무관하다. terminology-like
   구조 목록에서 제외하거나 별도로 명시해야 한다.
4. **[정보] `doctrine`(단수, 실제 채워짐) vs `doctrine_category`(복수, dead field) 혼동
   가능성** — C1 원문을 확보하지 못해 이 혼동이 실제로 있었는지 확인 불가. 후속 보고서
   작성 시 명확히 구분 필요.
5. **[정보] 현재 corpus는 cross-lingual embedding을 쓰지 않음** — `claim`(한국어)을
   임베딩하지 `source_text`(영어)를 임베딩하지 않는다. Benchmark 시급성 판단과 PHASE 3
   NAC 설계 결정에 직접 영향을 주는 사실이며, 확보한 지시문 텍스트에는 이 구조가
   언급돼 있지 않았다.
6. **[정보] C1 원본 보고서 파일 미발견** — 저장소 전체 검색으로 위치를 찾지 못했다.
   향후 재검증을 위해 C1 보고서를 파일로 커밋해두는 것을 권고한다(경미, 이 검증
   자체를 막지는 않음).

---

## 12. PHASE 1 Gate Judgment

# **C. CONDITIONAL**

핵심 사실관계(§3~§6)는 코드 실행·프로덕션 Qdrant 실측으로 강하게 확인되어 C1 discovery의
기술적 정확도는 높다. 그러나 Gate를 공식적으로 닫기 전에 §11의 1~3번(ADR 승인 상태,
Gate의 Phase 범위, crosswalk.yaml 재분류)을 보완해야 한다. 이들은 "C1의 핵심 결론이
틀렸다"(FAIL)는 수준은 아니며, "재검증 없이 다음 phase로 넘어가면 안 되는 미확정
항목"(CONDITIONAL) 수준이다.

---

## 13. Required Next Action

1. **사용자(HQ)에게 ADR-029 승인 여부를 확인**한다 — DRAFT 상태로 이 Gate Judgment를
   공식화할 수 없다.
2. C1/기록 문서에서 "BGE-M3 benchmark" gate를 **PHASE 1이 아니라 PHASE 4 소관으로
   재기재**한다. PHASE 1은 canonical term validation(권위 있는 출처 확인)만으로
   Gate를 정의할 수 있다.
3. `crosswalk.yaml`을 terminology-like 구조 목록에서 제외하거나 "문서 식별자 crosswalk
   — 용어 매핑 아님"으로 명확히 주석한다.
4. PHASE 3(NAC) 설계 착수 시, TSU 임베딩 대상을 기존처럼 한국어 `claim`으로 할지 영어
   `source_text`로 바꿀지를 **먼저 결정**한다 — 이 결정에 따라 PHASE 4 benchmark의
   필요성과 설계가 달라진다(backlog 기록, 현재 phase 변경 아님, ADR-029 §9 원칙 준수).
5. `THEME_KEYWORDS`의 한국어 미지원은 authoritative terminology dictionary(PHASE 1
   scope)가 아니라 `BOOK_ID_TO_NAMES`와 동일한 패턴의 alias-list 확장으로 해결
   가능하다는 관찰을 backlog에 기록한다 — **지금 구현하지 않는다** (DISCOVER ≠
   IMPLEMENT).
6. 이상 보완 후 CUE 또는 C1 Forensic Auditor가 재검증하여 PASS 여부를 재판정한다.

**본 검증은 여기서 종료한다. 구현은 수행하지 않았다.**
