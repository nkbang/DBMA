# ADR-030 POST-FORENSIC REASSESSMENT

**작성자**: CUE (Independent Post-Forensic Reassessment)
**작성일**: 2026-08-27
**Mode**: READ-ONLY · RECOMMENDATION ONLY · 독립 재평가
**Baseline**: `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md` (2026-08-27)
**Mutation Budget**: Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Config 0 / ADR 0 / Migration 0 / Cleanup 0 / Git commit 0
**산출물**: 본 보고서 1건

---

## 1. FINAL VERDICT

### **YELLOW**

ADR-030의 **핵심 원칙**("무엇을 임베딩할지 먼저 결정한다", "Acquired ≠ Validated ≠ Embedded ≠ Active", CLEAN
영역 재처리 금지, provenance 우선)은 forensic 결과를 반영해도 **옳고 유지 가능하다**. Forensic 자체가 이
원칙의 필요성을 실증했다 — C1이 "backlog"를 "defect"로, stale `index_report.json`을 "현재 상태"로 오인한
사건이 곧 "상태 구분이 architecture 수준에서 강제되지 않으면 문서가 production을 잘못 대표한다"는 증거다.

그러나 ADR-030의 **본문 구현 요구사항**은 검증된 architecture와 4곳에서 충돌한다:

1. **Terminology** — "EMBEDDED"를 단일 상태로 써서 TSU embedding(`nae_tsu_v1`)과 reference indexing
   (`nae_ref_v1`)을 뭉갠다. 둘은 별도 pipeline·schema·retrieval 경로다(§5).
2. **Lifecycle 순서** — §4의 `... → ELIGIBLE(human review) → INGESTED(TSU 생성) → ...`은 실제 pipeline과
   역순이다. TSU는 human review보다 **먼저** 생성된다. "ELIGIBLE"이 서로 다른 두 게이트를 하나로 합쳤다(§6).
3. **Research Scope / "ACTIVE"** — 존재하지 않으며, "즉시 필요한 변경"으로 구현하면 ADR-029 PHASE 6 lock과
   ADR-024/ADR-001 retrieval authority를 정면으로 위반한다(§7).
4. **State machine** — 이미 3개의 상태 권위(RegistrationState / ProcessingState / TSU record `review_status`)가
   공존한다. 4번째 독립 lifecycle enum을 추가하면 conflicting authority가 된다(§6).

**결론**: ADR-030을 재작성할 필요는 없다(RED 아님). 그러나 §4 lifecycle·§5 embedding-eligibility 순서·§6
research scope·§15 "즉시 필요한 변경 1–3"을 **현재 architecture 용어로 교정**하고, 구현 범위를 §11 MUST HAVE로
축소한 뒤에만 implementation specification으로 진행할 수 있다.

---

## 2. FORENSIC BASELINE

직전 3-Way Forensic Reconciliation 결과를 baseline으로 채택한다. 본 재평가에서 **독립 재확인**한 값
(2026-08-27, READ-ONLY GET only):

| 항목 | Baseline 값 | CUE 독립 재확인 | 판정 |
|---|---|---|---|
| Qdrant collections | `nae_ref_v1`, `nae_tsu_v1` | 동일 | MATCH |
| `nae_tsu_v1` points | 3,319 (Dagg 2,958 + Hiscox 361) | **3,319** | MATCH |
| `nae_tsu_v1` vector | 1024 / Cosine | **1024 / Cosine** | MATCH |
| `nae_ref_v1` points | 34,948 (Smith Vol1–4) | **34,948** | MATCH |
| Qdrant 컨테이너 포트 | `nae_qdrant` 7333→6333, up 47h | 동일 | MATCH |
| `incremental_state.json` | 3,319 all INDEXED | **3,319 all `INDEXED`** | MATCH |
| `registration_state.json` | 10 sources QUALITY_PASSED | **10 sources all `QUALITY_PASSED`** | MATCH |
| review_status ≠ verified in Qdrant | 0 | (baseline 채택) | — |
| Production mutation | 0 | 0 | MATCH |
| Fuller leakage | 0 | (baseline 채택) | — |

**Discrepancy: 없음.** Baseline은 그대로 authoritative하다. 아래 모든 판단은 이 baseline 위에서 이루어진다.

**Baseline이 확정한 3분리 (혼합 금지)**:
- **A. Production Data Integrity — CLEAN**: 인덱싱된 3,319 point는 5중 정합, 재처리·재임베딩 불필요.
- **B. Corpus Governance Readiness — 부분적**: manifest 3원화, M1 `raw_path` 부재, SLBC1689/PBC1742
  provenance BROKEN, M3 19건 CLAIM-ONLY.
- **C. Future Processing Backlog — 실재**: Fuller Vol02–08 TSU 미생성, Fuller Vol01 review 미착수,
  M3 CLAIM-ONLY raw 미확보.

ADR-030은 B와 C를 다루는 문서이며, A를 건드려서는 안 된다.

---

## 3. VERIFIED ARCHITECTURE

Forensic + 본 재평가에서 코드·파일로 확인한 실제 NAE architecture:

### 3.1 두 개의 상태 머신 (둘 다 live, 물리적으로 분리)

| 상태 머신 | 정의 위치 | 범위 | 상태 값 | 저장소 | 현재 내용 |
|---|---|---|---|---|---|
| `RegistrationState` (ADR-021) | `NAE/pipeline/registration/state.py` | source 단위 (upstream) | DISCOVERED → REGISTERED → RAW_PRESERVED → VALIDATED → EXTRACTED → QUALITY_PASSED (+4 실패) | `registration_state.json` | 10 source 전부 `QUALITY_PASSED` |
| `ProcessingState` (ADR-020) | `NAE/pipeline/ingest/state.py` | TSU 단위 (downstream) | DISCOVERED → IDENTIFIED → INGESTED → TSU_GENERATED → VALIDATED → HUMAN_REVIEW → PROMOTED → EMBEDDED → INDEXED (+4 실패) | `incremental_state.json` | 3,319 전부 `INDEXED` |

두 store 모두 **Production TSU 레코드에 필드를 추가하지 않는다** — 별도 JSON. 이것이 ADR-030 §13
"별도 state store 사용"이 이미 지켜지고 있다는 뜻이다.

### 3.2 실제 human review 권위 (v1)

- 3,319건의 verified/generated/rejected 판정은 **`NAE/corpus/tsu/*/tsu.json` 각 레코드의 `review_status`
  필드** + `NAE/review/human/decisions/` 40개 decision 파일이 authoritative.
- ADR-027(`ReviewStateV2`/`DispositionV2`)는 **DRAFT**, 776건 pilot 미실행. Production 3,319는 v1 경로로 처리됨.

### 3.3 세 개의 독립 retrieval 경로

| 경로 | 코드 | 대상 | 게이트 | 기본값 | 결과 표시 |
|---|---|---|---|---|---|
| DBMA 정본 | `core/retrieval.py::RetrievalEngine` | DBMA TSU dataset (in-memory) | ADR-001 authority | ON | 정본 |
| NAE TSU bridge | `NAE/retrieval_adapter.py::bridge_query()` | `nae_tsu_v1` (3,319) | `config.yaml modules.nae_pd.enabled` | **false (OFF)** | 별도 섹션, vector-only |
| NAE reference | `NAE/reference_retrieval_adapter.py::search_reference()` | `nae_ref_v1` (34,948) | ADR-028 conditional heuristic (`ui/pages/chat.py`) | DRAFT | silent background, citation UI 없음 |

ADR-013:88은 "NAE corpus를 RetrievalEngine production 경로에 통합하려면 신규 ADR 필요"라고 명시했고,
**그 신규 ADR이 ADR-024다** — ADR-024는 retrieval engine에 scope config를 읽히는 대신 **module-gate +
별도 섹션**을 선택했다(§B "결과 병합 금지", §F "스위치 하나").

### 3.4 두 개의 임베딩 pipeline

- TSU: `NAE/pipeline/ingest/` + `NAE/pipeline/embed/` + `NAE/pipeline/index/` → `nae_tsu_v1` (claim 기반)
- Reference: `NAE/pipeline/reference/` (chunker.py, ingest.py) → `nae_ref_v1` (chunk 기반, `content_type:
  reference_dictionary`, TSU claim 아님)

### 3.5 두 개의 authority registry (하나는 비어 있음)

| registry | 경로 | 모델 | 상태 |
|---|---|---|---|
| ADR-021 Option C | `NAE/authority/{authors,works}.yaml` | Author→Work→Edition→Source | **비어 있음** (`authors: []`, `works: []`) |
| ADR-016/017/018 | `resources/theological_sources/authority/{authors,works,editions,volumes,sources}.yaml` | Author→Work→Edition→Volume→Issue→Source | Fuller pilot 데이터 존재 (`pilot/fuller/`) |

### 3.6 설계만 되고 구현되지 않은 계층

- **ADR-019 Manifest Layer** (`processing_status`, `tsu_access`, `manifest_id`): 어떤 live manifest도 이
  필드를 담고 있지 않다. `processing_status` 문자열은 migration 코드와 TSU backup에만 잔존. ADR-019 §6
  "TSU 빌더에 `processing_status=TSU_ELIGIBLE` 게이트" = **미구현**(Promotion Evidence에도 명시).
- **ADR-014/015** (Modern Corpus Layer, 10단계 Ingestion Lifecycle): 둘 다 설계 단계, 승인 대기.
- **ADR-030의 `corpus_tier` / `authority_class` / `research_scope`**: 코드·schema·manifest 어디에도 없음
  (grep 결과 0건).

---

## 4. ADR-030 FINDINGS

각 핵심 조항을 verified architecture와 대조한 결과:

| ADR-030 조항 | 주장 | 실제 | 판정 |
|---|---|---|---|
| §3 T1–T9 9-tier | "canonical corpus category" | 어떤 코드도 이 vocabulary를 모름. 기존 `content_genre`(8값)/`theological_category`(4값)/`tradition`(3값)/ADR-015 "Authority Weight 4단계"가 이미 존재하며 T1–T9와 축이 겹치되 불일치 | **REWORK** — 신규 vocabulary 발명 대신 기존 축에 매핑 |
| §4 lifecycle 순서 | ACQUIRED→VALIDATED→**ELIGIBLE(review)→INGESTED(TSU)**→EMBEDDED→ACTIVE | 실제: QUALITY_PASSED → TSU_GENERATED → HUMAN_REVIEW → PROMOTED(verified) → EMBEDDED → INDEXED. TSU가 review보다 먼저 | **REWORK** — 순서 역전, "ELIGIBLE" 재정의 |
| §4 "ELIGIBLE" = category+authority+review | 단일 상태 | 두 개의 별개 게이트: (a) ADR-019 pre-TSU `TSU_ELIGIBLE`(미구현), (b) ADR-027 post-TSU disposition(DRAFT) | **REWORK** — 분리 |
| §4 "EMBEDDED" 책임 = ADR-020 | 단일 상태 | TSU embedding(ADR-020, `nae_tsu_v1`) ↔ reference indexing(ADR-028, `nae_ref_v1`) 별개 pipeline | **REWORK** — 용어 분리 |
| §4 "ACTIVE" = Research Scope config | Retrieval engine가 읽음 | 존재하지 않음. ADR-024는 의도적으로 module-gate 채택. ADR-029 PHASE 6 lock | **NOT YET** — §7 참조 |
| §5 Embedding Eligibility Gate | 순서: ... → Classification → Authority → TSU Validated → Embed | 실무: `review_status=verified` 없이는 아무것도 임베딩되지 않음 (`review_gate.filter_embedding_eligible`). Classification/authority 게이트는 없음 | **PARTIALLY EXISTS** — verified 게이트는 이미 강제됨; classification 게이트만 신규 |
| §7 Authority Model "유지·확장" | Author→Work→Edition→Source File | NAE-track registry(`NAE/authority/`)는 **비어 있음**. populated된 것은 `resources/theological_sources/authority/` (다른 경로) | **INCOMPLETE** — 분리 미인지 |
| §7 역사적 Baptist = Historical Witness (Primary Doctrinal 아님) | — | 옳음. Dagg/Hiscox/Fuller에 정확히 적용 가능 | **KEEP** |
| §8 Duplicate Control (ADR-015 §3.4 계승) | 해시/edition_id 대조 | ADR-021 §9 Level 1/2로 이미 구현(Phase B/C, commit `b1ebc3a`) | **ALREADY EXISTS** |
| §9 Scale Protection 위험표 | "manifest ↔ embedding state 불일치 → periodic reconciliation" | 정확히 이 실패가 발생했다(stale `index_report.json`). 그러나 doc-vs-production governance 규칙이 없음 | **KEEP + 강화** |
| §11 Future Scale (100/500/1000 threshold) | guideline | 현재 indexed works = 2개. Threshold monitoring은 시기상조 | **KEEP as guideline, NOT YET as 구현** |
| §13 Migration | "3,319 TSU/Qdrant 변경 없음, 별도 state store" | 정확. ADR-020/021 패턴과 정합 | **KEEP** |
| §14 "Smith … not embedded" | Dagg/Fuller Classification Status 표 | Forensic: Smith = `nae_ref_v1` 34,948 chunk 적재됨 | **CORRECT ERROR** — §14 표 갱신 필요 |
| §14 "Authority Registry … editions.yaml 등" | populated | `resources/theological_sources/authority/`엔 있음, `NAE/authority/`엔 없음 | **AMBIGUOUS** — 어느 registry인지 명시 필요 |
| §15 NOT VERIFIED #9 "Qdrant 3,319 직접 확인 필요" | 미검증 | Forensic + 본 재평가로 **검증 완료**: 3,319 | **RESOLVED** |

---

## 5. TSU vs REFERENCE CORPUS

**핵심: ADR-030은 두 corpus를 하나의 "Embedded" 상태로 표현하고 있고, 이것을 반드시 분리해야 한다.**

| 축 | TSU Track | Reference Track |
|---|---|---|
| Qdrant collection | `nae_tsu_v1` (3,319) | `nae_ref_v1` (34,948) |
| 단위 | TSU claim (review 대상) | chunk (`chunk_index`/`text`/`page_start·end`) |
| payload | `tsu_id`, `review_status`, `work_id`, `edition_id`, `verse_mapping` | `source_id`, `content_type: reference_dictionary`, `volume` |
| 생성 pipeline | `NAE/pipeline/{ingest,embed,index}/` (ADR-020) | `NAE/pipeline/reference/` (ADR-028) |
| human review | v1 40 decision 파일, `review_status=verified` 강제 | **없음 — 설계상 TSU review 대상 아님** |
| retrieval 경로 | `retrieval_adapter.bridge_query()` — module-gate `nae_pd` (OFF) | `reference_retrieval_adapter.search_reference()` — conditional heuristic |
| 결과 노출 | 별도 "NAE Public Theology" 섹션, citation 있음 | silent background, `<reference>` 태그, **citation UI 없음** (ADR-028 §10) |
| authority 순위 | 2순위 (TSU theological corpus) | 3순위 (background knowledge) — ADR-029 §2.3 |
| governing ADR | ADR-020/024 (Approved) | ADR-028 (DRAFT) |

**권고 (terminology)**:
- ADR-030 §4의 "EMBEDDED"를 두 상태로 분리: **`TSU_EMBEDDED`**(claim → `nae_tsu_v1`) 와 **`REFERENCE_INDEXED`**
  (chunk → `nae_ref_v1`).
- ADR-030 §4의 "INGESTED"(TSU conversion)는 reference track에 **적용되지 않음**을 명시. Reference track의
  lifecycle은 `RAW_PRESERVED → QUALITY_PASSED → CHUNKED → REFERENCE_INDEXED` (TSU/review 단계 없음).
- 정확한 architecture 트리:

```
Source Acquisition (RAW_PRESERVED, checksum ledger)
        │
Canonical Source (canonical/, normalize_report status=ok)
        │
        ├── TSU Track ──────────────────────────────┐
        │     TSU_GENERATED → HUMAN_REVIEW(v1)      │
        │     → verified subset → TSU_EMBEDDED      │→ nae_tsu_v1  (retrieval: nae_pd gate, OFF)
        │     → INDEXED                             │
        │                                          │
        └── Reference Track ───────────────────────┘
              CHUNKED → REFERENCE_INDEXED           → nae_ref_v1  (retrieval: search_reference heuristic)
```

- "Embedded"라는 단어 하나로 두 track을 표현하는 것은 **불가**하다는 task의 가설은 **확인됨(CONFIRMED)**.

---

## 6. LIFECYCLE / STATE ANALYSIS

### 6.1 ADR-030 6-state를 실제 state/metadata에 매핑

| ADR-030 상태 | 실제 대응 | authoritative store | 존재 여부 |
|---|---|---|---|
| ACQUIRED | `RegistrationState.RAW_PRESERVED` + `raw_checksum_ledger.jsonl` | `registration_state.json` | ✅ live |
| VALIDATED | `RegistrationState.VALIDATED` / `QUALITY_PASSED` | `registration_state.json` | ✅ live (10 sources) |
| ELIGIBLE (ADR-030: category+authority+review) | **분해됨**: (a) ADR-019 `TSU_ELIGIBLE` pre-TSU 게이트 = ❌ 미구현; (b) category/authority 할당 = ❌ 없음; (c) ADR-027 human review = v1은 `review_status` 필드, v2는 DRAFT | 없음 / `tsu.json` `review_status` | ⚠️ 부분 |
| INGESTED (TSU 생성) | `ProcessingState.TSU_GENERATED` / `VALIDATED` | `incremental_state.json` | ✅ live |
| EMBEDDED | `ProcessingState.EMBEDDED` / `INDEXED` + Qdrant point | `incremental_state.json` + `nae_tsu_v1` | ✅ live (3,319 INDEXED) |
| ACTIVE (Research Scope) | — | — | ❌ **존재하지 않음** |

### 6.2 순서 문제

ADR-030 §4는 `ELIGIBLE(human review) → INGESTED(TSU conversion)`. 실제 pipeline:
`TSU_GENERATED → HUMAN_REVIEW → PROMOTED`. **TSU가 human review보다 먼저 존재**한다 — 존재하지 않는 claim을
검수할 수 없다. `review_date` 분포(Forensic §4)가 이를 실측으로 뒷받침한다(TSU 2026-08-08 생성 → review
2026-08-09~11).

ADR-030의 "ELIGIBLE"이 실제로 가리키는 것은 **두 개의 서로 다른 게이트**:
- **pre-TSU eligibility**: "이 source를 TSU로 변환해도 되는가" — ADR-019 §6 `TSU_ELIGIBLE`, 미구현.
- **post-TSU disposition**: "이 TSU claim을 production에 승격해도 되는가" — `review_status=verified`, live.

### 6.3 State machine 판정 (task §4)

```
A. Existing state model is sufficient        — 아니오 (ELIGIBLE 게이트 부재, ACTIVE 부재)
B. Existing state model needs metadata ext.   — 예 (classification/authority_class를 source_id 키로 부착)
C. New state is genuinely required            — 부분 (pre-TSU TSU_ELIGIBLE 게이트 하나만 — 그러나 ADR-019가 이미 정의함, 신규 아님)
D. Architecture has conflicting authorities   — 예 (아래)
```

**판정: D (+ B).**

**근거 (D)**: 상태 권위가 최소 4곳에 분산 — `RegistrationState`(source), `ProcessingState`(TSU),
`tsu.json::review_status`(review v1), ADR-027 `ReviewStateV2`(review v2, DRAFT). 이들은 대부분 *계층적*
(source→TSU→review)이라 정면 모순은 아니지만, **단일 문서로 정리된 적이 없고**, ADR-027 v2가 production에
들어오면 v1 `review_status`와 두 개의 review 권위가 동시 존재하게 된다.

**근거 (B, 아님 C)**: ADR-030이 요구하는 것 중 진짜 신규 상태는 없다. "ELIGIBLE"의 pre-TSU 부분은
ADR-019가 이미 정의(미구현)했고, classification/authority는 *상태*가 아니라 *메타데이터*다 — 상태 머신이
아니라 source_id 키의 registry 필드로 충분하다.

**권고**: 새 독립 lifecycle enum을 만들지 말 것. 대신 —
1. §3.1의 상태 권위 지도를 ADR-030 본문(또는 부속 문서)에 **명시적으로 기록**한다.
2. ADR-019 `TSU_ELIGIBLE` 게이트를 `ProcessingState`에 상태 하나로 추가할지 여부만 별도 검토(현재 backlog).
3. classification/authority_class는 manifest schema 확장(§14)으로 처리.

---

## 7. CORPUS TIER / AUTHORITY ANALYSIS

### 7.1 T1–T9 재평가

| 질문 | 답 |
|---|---|
| 실제 NAE에 필요한가 | **분류 개념은 필요, 이 특정 9-tier 형태는 불필요.** 기존 schema에 `content_genre`(confession/theology/history/commentary/sermon/mission/church_practice/pastoral), `theological_category`(confession/ecclesiology/soteriology/missions), `tradition`(Particular/American/Evangelical Baptist)이 이미 존재 |
| tier 간 중복 | 있음. T3(Baptist/Evangelical Theology) ↔ T8(Church History) ↔ T7(Pastoral)은 Dagg 하나에 동시 적용 가능(ADR-030 §14 자체가 "T8/T3", "T7"로 흔들림) |
| authority와 category 혼동 가능성 | **있음.** T1–T9 목록이 축을 섞음 — 주제(T1 Scripture, T2 Interpretation), 장르(T4 Sermonology), 시대(T8 Church History), 언어역할(T6 Reference)이 한 리스트에. ADR-030이 `authority_class`를 별도로 두면서도 tier 목록은 여전히 혼합 |
| future scale 유지 가능 | 낮음. 5,000 works에서 "이 책은 T3인가 T8인가" 판정이 주관적 → tier 붕괴. 다축 태그(genre[] + category[] + tradition)가 더 견고 |
| retrieval scope에 의미 | 현재 없음. retrieval은 collection(`nae_tsu_v1`/`nae_ref_v1`) + `nae_pd` gate로만 갈림. tier는 어디에도 안 쓰임 |

### 7.2 `corpus_tier` vs `authority_class` — 별개 개념인가

**예, 별개다** — 그리고 ADR-030이 이 둘을 분리한 것은 옳다:
- **corpus classification** = "이 자료는 무엇에 관한 것인가" (주제/장르/전통). → 기존 `content_genre` +
  `theological_category` + `tradition`로 표현 가능.
- **authority_class** = "이 자료의 교리적 무게는 어느 정도인가" (Primary Doctrinal / Historical Witness /
  Reference / Application). → **기존 필드에 없음.** `tradition`은 계보이지 무게가 아니다. ADR-015가 설계한
  "Authority Weight 4단계"가 가장 가깝다(설계만).

**권고**:
- `corpus_tier`(T1–T9 단일 필드)는 **보류/폐기**. 대신 기존 `content_genre[]` + `theological_category[]` +
  `tradition`을 NAE M2 manifest에 적용.
- `authority_class`(enum: `primary_doctrinal` / `historical_witness` / `reference` / `application`)는 **채택**
  — 신규 개념이고 기존 중복 없음. ADR-015 "Authority Weight"와 정합 확인 필요.
- 두 축의 경계를 ADR 본문에 1문장으로 고정: *"classification은 검색 필터·범위용, authority_class는 생성
  프롬프트의 근거 우선순위용. 하나가 다른 하나를 결정하지 않는다."*

### 7.3 자료별 authority_class (task §10, §11)

| Source | classification (genre / category) | authority_class | 근거 |
|---|---|---|---|
| Dagg — Church Order (1871) | church_practice / ecclesiology | `historical_witness` | ADR-030 §7 규칙, 19c Baptist 저술 |
| Hiscox — Standard Manual (1890) | church_practice, pastoral / ecclesiology | `historical_witness` | 동 |
| Fuller — Works Vol01–08 (1820–24) | theology, sermon / soteriology, missions | `historical_witness` | 동 |
| Smith — Dictionary of the Bible Vol1–4 (1868) | commentary(reference) / — | `reference` | ADR-028 §3 3순위, background knowledge |
| SLBC1689 / PBC1742 (M3) | confession / confession | `primary_doctrinal` (자격상) — 단 provenance BROKEN → **INELIGIBLE** | Forensic B / FINAL-GOVERNANCE-RECONCILIATION |

---

## 8. MANIFEST GOVERNANCE

### 8.1 실측된 manifest/registry 목록

| # | 파일 | schema | 레코드 | 역할 (실제) | source_id 규약 |
|---|---|---|---|---|---|
| M1 | `NAE/authority/source_manifest.yaml` | 1.2 (lean) | 10 (Dagg, Hiscox, Fuller01–08) | — | `BAP-CHURCH-DAGG-001` |
| M2 | `NAE/pipeline/registration/state/source_manifest.yaml` | 1.2 (lean) | 14 (M1의 10 + Smith01–04) | ADR-021 registration pipeline 산출물 | `BAP-CHURCH-DAGG-001` |
| M3 | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | CSV | 25 | "NAE-BAPTIST-CORPUS-001" acquisition wishlist (2026-08-01, "25 planned") | `BAP-CONF-1689`, `BAP-SYS-GILL-001` |
| — | `resources/theological_sources/source_manifest.schema.yaml` | 1.2 (rich) | (스키마) | `scripts/source_validator.py`가 쓰는 스키마 — `content_genre`/`tradition`/`theological_category`/`status` enum 보유 | — |
| — | `resources/theological_sources/authority/*.yaml` | — | Fuller pilot | ADR-016/017/018 authority registry (populated for pilot) | — |

### 8.2 task §8 6개 질문에 대한 답

1. **의도된 architectural separation인가?** — 부분적으로만.
   - M2 ↔ M3: **예** — 서로 다른 lifecycle 단계. M3 = acquisition/wishlist(대부분 `sha256` 공란,
     `source_url` 공란, 계획 항목). M2 = registration 완료(`QUALITY_PASSED`, checksum 확정).
   - M1 ↔ M2: **아니오** — M1의 10개 레코드는 M2 앞 10개와 **바이트 단위로 동일**. M1은 M2의 부분 복사본
     (2026-08-18 commit `b111293`으로 `NAE/authority/`에 별도 커밋). 의도된 분리가 아니라 **중복**.

2. **중복 registry인가?** — M1 = M2의 중복. M3 = 다른 목적(중복 아님).

3. **서로 다른 lifecycle을 표현하는가?** — M3(acquisition intent) vs M2(registered/QUALITY_PASSED). 그러나
   실제 "동적 처리 상태"를 담는 layer(ADR-019 `processing_status`)는 **어느 manifest에도 구현되어 있지 않다**.
   현재 처리 진행은 manifest가 아니라 `registration_state.json` + `incremental_state.json` + `tsu.json`이 안다.

4. **source identity가 일관되게 유지되는가?** — **아니오.**
   - `BAP-CHURCH-DAGG-001`: M3에서 "Manual of Church Order" / M1·M2에서 "Church Order"
     (`edition_id: dagg_john_l-church_order-1871`).
   - `BAP-MISS-FULLER`: M3 = 1개 레코드 ("Complete Works of Andrew Fuller"). M1·M2 = 8개
     (`BAP-MISS-FULLER-VOL01..08`).
   - `BAP-CHURCH-HISCOX`: M3 "Edward Hiscox" / M1·M2 "Edward T. Hiscox".
   - Smith: M2에만, M1·M3엔 없음. PBC1765: 세 곳 모두 없음(quarantine).

5. **M1 `raw_path` 추가가 필요한가?** — 필요하다(Forensic §20 fix #4). 단, **M1이 아니라 SSOT로 지정될
   manifest(M2)에**. Dagg/Hiscox는 canonical이 `hocr.html`에서 생성됨 → `raw_checksum`이 `original.pdf`가
   아닌 `hocr.html`의 해시. `raw_path`/`checksum_target` 필드가 없어 감사 시 모호(C1의 "checksum mismatch"
   오판의 원인).

6. **통합이 필요한가, 역할 분리가 필요한가?** — **역할 분리 + 단일 SSOT 지정** (단순 병합 아님).
   - **M2 = source registry의 SSOT**로 선언 (registration pipeline이 이미 쓰고 있음).
   - **M3 = "acquisition backlog tracker"로 명시적 재분류** — source registry 아님. 헤더 주석 추가.
     19건 CLAIM-ONLY는 여기 남되 "미확보" 표시.
   - **M1 = M2에서 파생하거나 폐기** — 별도 수기 편집 금지 (byte-identical 유지 불가능).
   - **`resources/theological_sources/authority/` ↔ `NAE/authority/`** 관계를 1개 문서로 고정 — 어느 것이
     NAE production authority인지 (현재 `NAE/authority/`는 비어 있음).

### 8.3 ADR-030에 대한 권고

ADR-030 §9는 "manifest layer (ADR-019)"를 provenance 근거로 인용하지만 그 layer는 **런타임에 존재하지
않는다**. ADR-030은 "ADR-019 manifest layer가 존재한다"는 가정을 버리고, 위 §8.2-6의 **SSOT 지정 + 역할
명세**를 명시적으로 담아야 한다.

---

## 9. STALE ARTIFACT GOVERNANCE

### 9.1 확인된 stale artifact

| artifact | 값 | 실제 | 원인 |
|---|---|---|---|
| `NAE/corpus/tsu/Dagg_Church_Order/index_report.json` | `indexed: 5`, `gate_block: 3372`, `generated_at: 2026-08-09T18:32` | Qdrant Dagg = 2,958 | 2026-08-09 pilot smoke test 후 동결. 검수 후 인덱싱은 `embed_batch24_36.py`/`nae_incremental_ingest.py`가 수행하며 이 파일을 갱신 안 함 |
| `NAE/corpus/tsu/Hiscox_Standard_Manual/index_report.json` | `indexed: 5` | Qdrant Hiscox = 361 | 동 |
| `NAE/corpus/tsu/_*backup*/index_report.json` ×4 | `indexed: 0` | (backup 디렉터리) | pilot 시각 일괄 생성 |
| `config.yaml:52` `qdrant.url` | `http://localhost:6333` | `nae_qdrant`는 7333 | DBMA legacy config. NAE pipeline은 `NAE/pipeline/index/config.py` 사용 → 실害 제한적이나 혼동 유발 |
| memory "Smith 임베딩 보류" | (2026-08-25) | `nae_ref_v1` 34,948 | 이후 적재로 stale |

### 9.2 4-way 구분 (task §9)

```
Current Production State   = Qdrant live count + incremental_state.json + tsu.json::review_status
                             (권위: 실측)
Historical Report          = index_report.json, promotion_batch*_evidence.json
                             (특정 시점 스냅샷 — generated_at 필수, 현재 상태 아님)
Pilot Artifact             = _*backup*/, _remediation_backup_*, 2026-08-09 pilot smoke outputs
                             (일회성 실험 — production SSOT로 읽으면 안 됨)
Production State (문서)      = ADR-030 §14, STATE.md
                             (반드시 Current Production State와 일치해야 함, 아니면 supersede 표기)
```

### 9.3 ADR-030이 제공해야 하는 최소 governance mechanism

ADR-030 §9는 "obsolete embedding 잔존"과 "manifest ↔ state 불일치"를 위험으로 나열하지만 **doc-vs-report
staleness 규칙이 없다**. 다음을 ADR-030에 추가 권고 (cleanup은 수행 안 함):

1. **모든 상태 report(*.json/*.md)는 `generated_at`(UTC ISO) + `pipeline_stage`를 포함**한다. 없으면
   downstream(Ops Dashboard 등)이 SSOT로 소비 금지.
2. **`superseded_by` / `authoritative: false` 마커** — stale로 판명된 report에 파일을 삭제하지 않고 마커만
   추가(예: `index_report.json`에 `"superseded_by": "incremental_state.json + Qdrant live count"`).
3. **pilot artifact 명명 규칙** — pilot/smoke/backup 산출물은 `*_pilot_*` / `_*backup*` 접두사를 강제하고,
   어떤 production 판정도 이 경로를 읽지 않는다(코드 리뷰 체크 항목).
4. **단일 reconciliation 명령** — manifest(M2) ↔ `incremental_state.json` ↔ `tsu.json::review_status` ↔
   Qdrant point count를 대조해 drift를 출력(read-only). ADR-020의 `index_all()` reconciliation 역할을 확장.
   자동 수정 없음.
5. **인덱싱 경로 배선 통일** — 검수 후 인덱싱을 하는 스크립트가 `index_report.json`을 갱신하도록(재발 방지,
   Forensic §20 fix #2). ADR-030 범위 밖이면 backlog로 이관.

---

## 10. C1 RECOMMENDATIONS REASSESSMENT

ADR-030 §15의 C1 제안 7건을 Forensic baseline(Production CLEAN) 위에서 재판정:

| # | C1 제안 | 판정 | 근거 |
|---|---|---|---|
| 1 | Corpus Category Schema Extension (`corpus_tier` T1–T9, `authority_class`) | **REQUIRED LATER (수정 조건부)** | classification은 필요하나 T1–T9 대신 기존 `content_genre`/`theological_category`/`tradition` 재사용. `authority_class`만 신규 채택. §7 |
| 2 | Lifecycle State Integration (RegistrationState → ProcessingState 매핑 코드화) | **USEFUL (문서화) / NOT REQUIRED (코드)** | 매핑은 ADR-020/021에 암묵적으로 이미 존재. §3.1 상태 지도를 *문서로* 고정하는 것은 USEFUL. 신규 전이 layer 코드는 불필요 — conflicting authority 위험 |
| 3 | Research Scope Config Structure (retrieval engine가 config 읽도록, "ADR-001/013 변경 필요") | **NOT YET / ARCHITECTURALLY UNSAFE (as drafted)** | ADR-029 rule #4("retrieval authority 우회 금지") + PHASE 6("지금 구현 안 함") 정면 위반. ADR-024가 이미 module-gate로 해결. §7 |
| 4 | Duplicate Detection Enhancement (edition_id + hash) | **ALREADY EXISTS** | ADR-021 §9 Level 1/2 구현 완료(Phase B/C, commit `b1ebc3a`), `raw_checksum_ledger.jsonl` 운영 중 |
| 5 | Existing Corpus Tier Mapping Script (26 entries → 9-tier) | **REQUIRED LATER** | #1의 vocabulary 확정 후. 실제 registered source는 14개(M2), 그중 real acquisition 확정은 Dagg/Hiscox/Fuller/Smith — 스크립트보다 수기 표가 빠름 |
| 6 | Periodic Reconciliation Tool (manifest ↔ cache ↔ Qdrant) | **USEFUL / SHOULD HAVE** | §9.3-4와 동일. stale-artifact 실패를 직접 방지. ADR-020 reconciliation 확장으로 구현 |
| 7 | Scale Threshold Monitoring (100/500/1000 alerts) | **NOT YET** | 현재 indexed works = 2. 시기상조. ADR-030 §11에 guideline으로만 유지 |

**추가**: ADR-030 §15 "NOT VERIFIED #9(Qdrant 3,319 직접 확인)"은 Forensic + 본 재평가로 **RESOLVED**.
"#10(TSU Builder ELIGIBLE 게이트)"는 ADR-019 §6 미구현 상태 그대로 — backlog.

---

## 11. MUST HAVE

> *"NAE가 50 → 500 → 5,000 works로 확장될 때 corpus가 무질서해지는 것을 막는 최소 governance"*

| # | 항목 | 이유 (scale 붕괴 시나리오) | 비용 |
|---|---|---|---|
| M-1 | **단일 source registry SSOT 지정** — M2를 SSOT로 선언, M3를 "acquisition backlog tracker"로 재분류, M1은 파생/폐기, `resources/.../authority/` ↔ `NAE/authority/` 관계 1문서 고정 | 지금도 `BAP-CHURCH-DAGG-001`이 manifest마다 다른 저작을 가리킴. 500 works면 어느 ID가 canonical인지 판정 불가 → 중복 임베딩·엉뚱한 edition 혼입 | governance 문서 + manifest 헤더 주석. 코드 0 |
| M-2 | **classification + authority_class 메타데이터 (source_id 키)** — 기존 `content_genre[]` / `theological_category[]` / `tradition` + 신규 `authority_class` enum을 M2 schema에 추가 | tier 없이 5,000 works면 "이번 연구에 어떤 자료가 근거로 적합한가" 판정 불가. authority_class 없으면 Historical Witness(Dagg)가 Confession과 동일 무게로 프롬프트에 유입 | schema 4필드 추가 + 14개 레코드 backfill. 기존 vocabulary 재사용 |
| M-3 | **Embedding Eligibility = 명시적 사람 결정, 문서화** — "verified 없이는 임베딩 없음"(이미 강제됨)을 규칙으로 명문화 + reference track은 별도 eligibility 노트(TSU review 우회하므로) + 대량 임베딩 전 체크리스트(ADR-029 rule #7 계승) | ADR-029 위반(pilot 없는 일괄 임베딩)이 가장 흔한 사고 유형. 명문 규칙이 없으면 "canonical 됐으니 임베딩"으로 미끄러짐 | ADR 본문 1개 절 |
| M-4 | **Doc-vs-Production staleness governance** — 모든 상태 report에 `generated_at`+`pipeline_stage` 강제, stale엔 `superseded_by` 마커, pilot artifact 명명 규칙, read-only reconciliation 명령 1개 | 이미 발생했다: stale `index_report.json` → Ops Dashboard → C1 오판. 자료가 늘수록 stale report 수도 늘어남 | §9.3. reconciliation은 ADR-020 확장 |
| M-5 | **TSU Track ↔ Reference Track 용어 분리** — ADR-030 §4의 "EMBEDDED"를 `TSU_EMBEDDED` / `REFERENCE_INDEXED`로, "INGESTED"는 reference track 비적용 명시 | 한 단어로 두 track을 표현하면 "Smith가 임베딩됐다 = TSU corpus에 있다"는 오해 (ADR-030 §14가 실제로 반대 방향으로 틀림). track 수가 늘면 혼동 가중 | ADR 본문 용어 교정 |

---

## 12. SHOULD HAVE

| # | 항목 | 근거 |
|---|---|---|
| S-1 | T1–T9 아이디어를 기존 `content_genre`/`theological_category`/`tradition` 축으로 흡수하는 매핑 설계 문서 | §7. tier를 버리되 그 취지(주제 구분)는 유지 |
| S-2 | `NAE/authority/{authors,works}.yaml`(비어 있음)을 채우거나 공식 폐기 | ADR-021 Option C 이후 방치. 어느 registry가 authority인지 모호 |
| S-3 | M2에 `raw_path` / `checksum_target` 필드 추가 | Forensic §20 fix #4. C1 checksum 오판 재발 방지 |
| S-4 | ADR-019 `TSU_ELIGIBLE` 게이트를 `ProcessingState`에 추가할지 결정 | §6.3. pre-TSU eligibility의 유일한 진짜 gap |
| S-5 | Periodic reconciliation tool (C1 rec #6) | §9.3-4. 지금은 works 2개라 수기로 충분하지만 ~50 works 시점에 필요 |
| S-6 | ADR-030 §14 표를 Forensic 실측으로 갱신 (Smith `nae_ref_v1` 34,948, Fuller Vol01 TSU 3,643 all generated, 등) | 문서가 production을 잘못 대표 중 |
| S-7 | ADR-015 "Authority Weight 4단계" ↔ ADR-030 `authority_class` 정합 확인 | 중복 개념 방지 |

---

## 13. NOT YET

| # | 항목 | 차단 근거 |
|---|---|---|
| N-1 | **Research Scope config / "ACTIVE" 상태 / retrieval engine가 scope 읽기** | ADR-029 PHASE 6 ("Smith → 실제 앱 → 실제 질문 → workflow 관찰 후 설계"), ADR-029 rule #4, ADR-024 module-gate 설계. "즉시 필요"로 올리면 3개 ADR 위반 |
| N-2 | **신규 독립 lifecycle state machine** (ADR-030 6-state를 별도 enum으로) | §6. 기존 3 권위로 충분. 4번째는 conflicting authority. 필요성 미입증 |
| N-3 | **`corpus_tier` T1–T9 단일 필드 schema 추가** | §7. 축 혼합, 유지 불가. 다축 태그로 대체 |
| N-4 | **Tier별 separate retrieval indexing** (ADR-030 §11, 1,000+ works) | 현재 indexed works 2개. far off |
| N-5 | **Scale Threshold Monitoring 자동화** (C1 rec #7) | 시기상조. guideline으로만 |
| N-6 | **ADR-027 v2 776 pilot 실행** | 별도 HQ 승인 대기 (memory: NAE 776 Human Review Pause). ADR-030과 독립 |
| N-7 | **SLBC1689 / PBC1742 provenance 재구성** | BROKEN 확정, HQ decision 대기 (FINAL-GOVERNANCE-RECONCILIATION §17) |
| N-8 | **Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition** | Backlog(C). ADR-030 governance 대상이지 이번 재평가의 구현 대상 아님. ADR-029 PHASE 순서 준수 |

---

## 14. IMPLEMENTATION SPECIFICATION

**이번 재평가에서 구현 승인 대상: 없음.** 아래는 §11 MUST HAVE 중 **schema/code 변경을 수반하는 항목**
(M-2, M-4 일부)에 대한 다음 단계 명세다. 각 항목은 별도 HQ 승인 후에만 착수.

### 14.1 M-2 — classification + authority_class 메타데이터

| 항목 | 내용 |
|---|---|
| 변경 대상 파일 | (1) `resources/theological_sources/source_manifest.schema.yaml` — 이미 `content_genre`/`tradition`/`theological_category` 정의됨, 여기에 `authority_class` 필드 정의 추가. (2) `NAE/pipeline/registration/state/source_manifest.yaml` (M2) — 14개 레코드에 4필드 backfill. (3) `NAE/pipeline/registration/manifest_writer.py` — 신규 등록 시 4필드 요구 |
| 변경 이유 | ADR-030 §3/§7의 정당한 핵심(분류·authority 구분)을 기존 vocabulary로 구현. tier 붕괴 방지 |
| 기존 authority | schema = `resources/theological_sources/source_manifest.schema.yaml` (scripts/source_validator.py가 소비). ID 규약 = ADR-017. authority weight 개념 = ADR-015 §3.5 |
| backward compatibility | 4필드 전부 `required: false`로 시작(ADR-021 Quality Gate WARNING-first 패턴). 기존 `source_validator.py`는 미지 필드 무시. Production TSU/Qdrant 무접촉. M2 backfill은 append-only diff |
| migration risk | 낮음. 데이터 mutation은 M2 YAML 14줄 그룹. `registration_state.json`/`incremental_state.json`/Qdrant 불변. rollback = git revert 1파일 |
| test requirement | (a) schema에 `authority_class` enum 4값만 허용; (b) 14개 레코드 전부 4필드 채워짐 + enum 준수; (c) `source_validator.py` PASS 유지; (d) 미지정 시 WARNING(FAIL 아님); (e) Dagg/Hiscox/Fuller = `historical_witness`, Smith = `reference` assert; (f) baseline protection — 실행 전후 `nae_tsu_v1` count / `incremental_state.json` 해시 불변 |

### 14.2 M-4 — reconciliation 명령 (read-only)

| 항목 | 내용 |
|---|---|
| 변경 대상 파일 | 신규 `scripts/nae_corpus_reconcile.py` (read-only). ADR-020 `NAE/pipeline/index/indexer.py::index_all()`의 reconciliation 역할 참조, 코드 재사용 |
| 변경 이유 | §9. stale-artifact 실패 재발 방지. manifest ↔ state ↔ Qdrant drift를 사람이 볼 수 있게 |
| 기존 authority | Current Production State 정의(§9.2) = Qdrant live count + `incremental_state.json` + `tsu.json::review_status` |
| backward compatibility | 신규 파일, 기존 코드 import만. 쓰기 0 (GET/count/scroll + json.load만). `--apply` 플래그 없음 |
| migration risk | 없음 (read-only). |
| test requirement | (a) Qdrant 정지 상태에서 예외 전파 없이 "unreachable" 보고; (b) 정상 상태에서 `nae_tsu_v1=3,319`, `incremental_state INDEXED=3,319`, drift=0 출력; (c) 인위적 mismatch fixture에서 정확히 flag; (d) mutation 0 검증 |

### 14.3 M-1 / M-3 / M-5 (문서 전용, 코드 변경 없음)

- M-1: `docs/agents/cue/` 또는 `docs/architecture/`에 "NAE Manifest & Authority SSOT" 1페이지. M2 헤더에
  `# SSOT: source registry`, M3 헤더에 `# acquisition backlog tracker — NOT a source registry` 주석.
- M-5: ADR-030 §4/§5/§14 용어 교정 (ADR modification이므로 HQ가 ADR-030 개정으로 처리).

---

## 15. RISKS

| # | 위험 | 심각도 | 완화 |
|---|---|---|---|
| R-1 | ADR-030 §15 "즉시 필요한 변경 3"(Research Scope)을 그대로 구현 착수 | **높음** | ADR-029 PHASE 6 lock 명시. N-1로 고정. retrieval 경로(`core/retrieval.py`, `nae_pd` gate)는 이번 범위에서 완전 동결 |
| R-2 | 새 `corpus_tier` 필드 + 새 lifecycle enum 추가 → 4번째 상태 권위 | 중 | §6 판정 D. metadata 확장(B)만 승인, state machine 신규 금지 |
| R-3 | manifest "3개니까 하나로 합친다"식 병합 → M3의 acquisition intent 소실 또는 M2 SSOT 오염 | 중 | §8.2-6. 병합 아님, 역할 분리 + SSOT 지정 |
| R-4 | M2 backfill 중 다른 세션이 registration pipeline 실행 → 경합 쓰기 | 중 | backfill은 단일 세션, 실행 전 `git status NAE/pipeline/registration/state/` 확인 (memory: Concurrent C1 File Edits, Test Fixture Path Overrides) |
| R-5 | ADR-030 문서(§14)가 stale인 채로 "ACCEPTED" 유지 → 후속 작업이 잘못된 상태표 인용 | 중 | S-6로 §14 갱신. 그 전까지 §14를 근거로 한 판단 금지 |
| R-6 | reference track(`nae_ref_v1`)을 TSU governance 규칙에 억지로 끼워맞춤 (review 요구 등) | 낮음 | §5. reference track 별도 lifecycle 명시. ADR-028(DRAFT) 정합 |
| R-7 | `config.yaml:52` 6333 stale을 "고친다"며 DBMA legacy config 건드림 | 낮음 | NAE pipeline은 `NAE/pipeline/index/config.py` 사용. DBMA legacy와 분리 (ADR-013). 이번 범위 밖 |
| R-8 | 재평가 산출물(본 문서)이 ADR-030을 대체하는 것으로 오인 | 낮음 | 본 문서는 RECOMMENDATION. ADR-030 개정은 HQ가 수행 |

---

## 16. FINAL RECOMMENDATION

**ADR-030 = YELLOW.** 원칙은 유지, 구현 요구사항은 교정 후 진행.

**HQ 결정이 필요한 사항**:

1. **ADR-030 개정 승인** — §5(TSU/Reference 용어 분리), §6(lifecycle 순서 교정, "ELIGIBLE" 2게이트 분리),
   §7(T1–T9 → 기존 축 + `authority_class`), §15("즉시 필요한 변경 3" Research Scope → NOT YET로 강등).
   상태를 `ACCEPTED`에서 `ACCEPTED (Amendment A pending)` 등으로 표기.

2. **MUST HAVE 5건 중 문서 전용 3건(M-1, M-3, M-5)** 즉시 착수 승인 가능 — 코드·데이터 mutation 0.

3. **schema/code 수반 2건(M-2, M-4)** — §14 명세대로 별도 작업 명령. 각각 backward-compatible,
   Production CLEAN 영역 무접촉.

4. **동결 확인** — 이번 및 후속 작업에서 `core/retrieval.py`, `nae_pd` gate, `nae_tsu_v1`/`nae_ref_v1`
   데이터, `incremental_state.json`, 3,319 verified TSU는 건드리지 않는다. ADR-029 PHASE 순서 준수.

5. **Backlog로 이관** (ADR-030 governance 대상이나 이번 구현 아님): Fuller Vol01 review, Fuller Vol02–08
   TSU, M3 CLAIM-ONLY 19건, SLBC1689/PBC1742 provenance decision, ADR-027 v2 776 pilot, ADR-019
   `TSU_ELIGIBLE` 게이트.

---

**최종 기준 재확인**:

> NAE는 자료를 많이 임베딩하는 시스템이 아니라, 목회자가 신뢰할 수 있는 자료를 선택·검증하여 목적에 맞는
> 연구 범위 안에서 사용하는 시스템이다. 무엇을 임베딩할지 먼저 결정하고, 어떻게 임베딩할지는 그 다음이다.
> 이미 CLEAN으로 검증된 영역(3,319 verified TSU / `nae_tsu_v1` 3,319 point)에는 재처리·migration을 하지
> 않는다.

ADR-030은 이 기준에 부합하는 방향이다. 다만 "선택·검증·범위"를 **현재 architecture의 용어와 상태 권위로**
표현해야 하며(§5, §6), "범위(Research Scope)"의 실제 구현은 실사용 관찰 이후다(ADR-029 PHASE 6).

---

**Reassessment Mode**: READ-ONLY · INDEPENDENT · RECOMMENDATION ONLY
**Mutations**: 0 (Code / Corpus / TSU / Embedding / Qdrant / Manifest / Registry / Config / ADR / Git commit)
**Baseline discrepancy**: 없음 (Qdrant 3,319 / 34,948, state stores 독립 재확인)
**Report generated**: 2026-08-27
