# ADR-030: NAE Sermon Corpus Governance & Pipeline Foundation

> **이 본문은 forensic reconciliation + post-forensic reassessment + C1 Implementation-Readiness
> Review를 거쳐 v1(2026-08-27) → v2 → v2.1로 개정된 최종본이다. 이 ADR의 채택 자체는 코드·데이터·
> Qdrant·manifest mutation을 수행하지 않는다 — 구현 항목은 §12 MUST로 분리된다.**

---

## 1. Status

| | |
|---|---|
| **Status** | **IMPLEMENTED / §12 MUST COMPLETE (2026-08-28)** — 채택: ACCEPTED 2026-08-27 (v2.1 consolidated). §12 MUST M-1~M-5 전량 완료, 각 단계 CUE 독립검증 GREEN (§12 표 · Appendix C) |
| **Date** | 2026-08-27 |
| **Approved** | 2026-08-27 — Rev. Bang / HQ ("ADR-030 v1을 v2.1 내용으로 교체" 지시) |
| **Supersedes** | ADR-030 v1 (2026-08-27). 개정 경로: v1 → v2 REV-DRAFT → v2.1 → 본 최종본 |
| **Superseded by** | — |
| **Deciders** | Rev. Bang / HQ = Final Authority. CUE = Governance/Architecture, C1 = Independent Verification |
| **Baseline** | `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md` (2026-08-27) |
| **Reviews** | `docs/agents/cue/CUE-ADR-030-POST-FORENSIC-REASSESSMENT.md` (YELLOW) · C1 Implementation-Readiness Review (YELLOW — READY WITH FINDINGS, Production Contact NO, Migration NO) |
| **CLEAN baseline (변경 금지)** | `nae_tsu_v1` = 3,319 · `nae_ref_v1` = 34,948 |
| **Adoption mutation** | 이 ADR 채택 = Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Config 0 / Migration 0. 구현은 §12. |

중간 draft(`ADR-030-...-REV-DRAFT.md`, `ADR-030-...-REV-DRAFT-v2.1.md`)는 본 최종본으로 통합되어
삭제되었다. 개정 근거는 위 Baseline / Reviews 문서에 보존된다.

---

## 2. Change Log & Decision History

### 2.1 v1 → v2 (요약)

C-1 `corpus_tier` T1–T9 단일 필드 폐기 → 기존 다축 + `authority_class` · C-2 lifecycle을 TSU/Reference
2 track 분리, 순서 교정 · C-3 Research Scope 구현 제외(ADR-029 PHASE 6) · C-4 §15 "즉시 필요한 변경"
재분류 · C-5 "ADR-019 manifest layer" 인용 제거 · C-6 Manifest SSOT §신설 · C-7 Stale Artifact
Governance §신설 · C-8 §14 forensic 실측 갱신.

### 2.2 v2 → v2.1 (C1 5개 FINDING 교정)

| FINDING | 심각도 | v2의 미흡점 | v2.1 교정 | 문서 위치 |
|---|---|---|---|---|
| **F-1** | MEDIUM | TSU record에 이미 `category` 필드 존재(현재 대부분 `None`). `authority_class`와의 관계 불명확 | `category`(TSU-record layer, 주제/장르 분류, `category_status=AUTHORITATIVE_SOURCE_MISSING`)와 `authority_class`(source/manifest layer, 교리적 무게)는 **서로 다른 개념·다른 계층**임을 선언. `authority_class`는 **TSU record에 쓰지 않는다**. 중복 필드 신설 금지 원칙 명시. 3,319 production TSU migration 없음 | §7 |
| **F-2** | MEDIUM | "ELIGIBLE"이 실제 code state와 매핑 안 됨. 독립 `ELIGIBLE` state value 없음 | "ELIGIBLE" 용어 **폐기**. 3개 실제 개념으로 분리: **Admission Decision**(HQ governance 결정, state 아님) / **Review Disposition**(`tsu.json::review_status`, 기존) / **Retrieval Eligibility**(런타임 게이트, 기존). 새 state enum 없음 | §6 |
| **F-3** | LOW | M1 폐기 대상 파일·절차 불명확 | M1 = **`NAE/authority/source_manifest.yaml`** (schema 1.2, 10 records) — M2의 **byte-identical prefix**. 역할 = **`derived` (non-authoritative mirror)**. 즉시 삭제 안 함. runtime consumer 0 확인됨(별도 migration task에서 재확인 후 archival) | §8 |
| **F-4** | LOW | `tsu.json::review_status` ↔ `HUMAN_REVIEW`가 중복 추적처럼 보임 | 3개 층으로 분리 정의: `review_status`(TSU record — disposition **결과**, SSOT) / `ProcessingState.HUMAN_REVIEW`(`incremental_state.json` — pipeline **단계 위치**) / `NAE/review/human/decisions/`(governance **증거·audit trail**). 동일 authority 아님. 새 state machine 없음 | §10 |
| **F-5** | MEDIUM (CRITICAL GOVERNANCE) | Human Embedding Eligibility Gate가 실제 workflow에 명시적으로 없음 | `ACQUIRED ≠ EMBEDDING ELIGIBLE ≠ EMBEDDED ≠ RETRIEVAL-ELIGIBLE` 4구분을 명문화. **Admission Decision**을 append-only governance 기록(`NAE/governance/corpus_admissions.jsonl`, 신규 MUST task)으로 정의 — state machine 아님. 3,319 production TSU는 기존 human review 증거로 **소급 충족**, 재처리·재승인 없음 | §11 |

### 2.3 Decision History

| Date | Event | Result |
|---|---|---|
| 2026-08-27 | ADR-030 v1 작성 | ACCEPTED (evidence base에 C1 보고 포함) |
| 2026-08-27 | 3-Way Forensic Reconciliation | Production CLEAN, C1 보고 일부 CONTRADICTED, manifest 3원화 / stale artifact 발견 |
| 2026-08-27 | CUE Post-Forensic Reassessment | **YELLOW** — 원칙 유지, terminology/schema/governance 교정 |
| 2026-08-27 | v2 REV-DRAFT | 8개 교정 (C-1 … C-8) |
| 2026-08-27 | C1 Implementation-Readiness Review | **YELLOW — READY WITH FINDINGS** (5 findings, Production Contact NO, Migration NO) |
| 2026-08-27 | v2.1 REV-DRAFT | C1 5개 finding 교정 (F-1 … F-5) |
| 2026-08-27 | HQ 지시 "v1을 v2.1 내용으로 교체" | **ACCEPTED (v2.1 consolidated)** — v1 superseded, 중간 draft 통합·삭제 |

---

## 3. Corpus Governance Principles

1. **선택이 먼저다.** "무엇을 임베딩할 것인가"를 먼저 결정하고, "어떻게 임베딩할 것인가"를 그 다음 결정한다.
2. **자동 진행 금지.** ACQUIRED 상태의 자료가 자동으로 다음 단계로 가지 않는다. 각 게이트는 명시적으로
   통과되어야 한다.
3. **CLEAN 영역 동결.** 이미 forensic으로 CLEAN 검증된 3,319 verified TSU / `nae_tsu_v1` 3,319 point /
   `nae_ref_v1` 34,948 chunk는 이 ADR을 이유로 재처리·재승인·migration하지 않는다.
4. **기존 authority 유지.** 새로운 pipeline / config / retrieval authority / state machine / vector DB /
   embedding pipeline을 만들지 않는다. 이 ADR은 governance 계층이지 실행 계층이 아니다.
5. **Track 분리.** TSU Track과 Reference Track은 별도 pipeline·schema·retrieval 경로다. 하나의 "embedded"
   용어로 뭉뚱그리지 않는다.
6. **문서는 production을 정확히 대표한다.** stale 상태 파일이 SSOT로 소비되지 않도록 governance mechanism을
   둔다(§9).
7. **Research Scope는 이 ADR 밖.** 세션별 자료 ON/OFF는 ADR-029 PHASE 6(실사용 관찰 후 설계).

---

## 4. TSU Track

**대상**: 검증 가능한 신학적 claim으로 분해되는 자료 (Dagg, Hiscox, Fuller …).

```
[upstream — ADR-021]
DISCOVERED → REGISTERED → RAW_PRESERVED → VALIDATED → QUALITY_PASSED
        저장소: NAE/pipeline/registration/state/registration_state.json  (source 단위, RegistrationState)
        현재: 10 source 전부 QUALITY_PASSED

        │  ← Admission Decision (§6.1, §11) — HQ governance 결정, state 아님
        ▼
[downstream — ADR-020]
TSU_GENERATED → VALIDATED → HUMAN_REVIEW → PROMOTED → EMBEDDED → INDEXED
        저장소: NAE/pipeline/ingest/state/incremental_state.json  (TSU 단위, ProcessingState)
        현재: 3,319 전부 INDEXED

        Review Disposition (§6.2): tsu.json::review_status ∈ {generated, reviewed, verified, rejected}
        Embedding gate: review_gate.filter_embedding_eligible() — EMBEDDING_ELIGIBLE_STATUSES = {verified}
        현재: Dagg 2,958 verified / Hiscox 361 verified → nae_tsu_v1

        │  ← Retrieval Eligibility (§6.3)
        ▼
RETRIEVAL-ELIGIBLE  ⟺  config.yaml modules.nae_pd.enabled == true   (ADR-024, 기본 false)
```

**순서 주의**: TSU는 human review보다 **먼저** 생성된다. 존재하지 않는 claim을 검수할 수 없다
(`review_date` 분포가 TSU 생성 후 검수를 실측으로 뒷받침 — forensic §4).

**review v2**: ADR-027 `ReviewStateV2` / `DispositionV2`는 DRAFT(776 pilot 미실행). 도입 시 v1
`review_status`와의 authority 관계를 그 시점에 명시한다(§10). 지금은 v1 `review_status`가 3,319에 대한
유일 disposition 권위.

---

## 5. Reference Track

**대상**: 검증 가능한 claim이 아닌 background knowledge (Smith Bible Dictionary …).

```
[upstream — ADR-021]
DISCOVERED → … → QUALITY_PASSED
        저장소: registration_state.json  (Smith는 M2 등록, registration_state.json에는 미기재 — §10 참조)

        │  ← Admission Decision (§6.1, §11) + Reference Quality Confirmation
        ▼
[reference pipeline — ADR-028, NAE/pipeline/reference/]
CHUNKED → REFERENCE_INDEXED
        단위: chunk (chunk_index / text / page_start·end), content_type = reference_dictionary
        human review 단계 없음 (claim 아님)
        현재: Smith Vol1–4 = 34,948 chunk → nae_ref_v1

        │  ← Retrieval Eligibility (§6.3)
        ▼
RETRIEVAL-ELIGIBLE  ⟺  ADR-028 conditional heuristic (ui/pages/chat.py, DRAFT)
        노출 방식: silent background, <reference> 태그, citation UI 없음 (ADR-028 §10, ADR-029 §2.3 3순위)
```

**v1 §4 "INGESTED (TSU conversion)"는 이 track에 적용되지 않는다.** Reference track에는 TSU 생성도,
`review_status`도, HUMAN_REVIEW 단계도 없다.

---

## 6. Admission / Review / Retrieval Eligibility — Terminology (F-2)

v1/v2의 "ELIGIBLE"이라는 단일 단어를 **폐기**한다. 그 단어가 실제 runtime state처럼 오해되기 때문이다.
실제로는 성격이 다른 3개 개념이다.

### 6.1 Admission Decision — HQ governance 결정 (state machine 아님)

| 항목 | 내용 |
|---|---|
| 정의 | "이 source를 NAE corpus로 받아들일 것인가, 어느 track으로 보낼 것인가, authority_class와 classification은 무엇인가"에 대한 **사람의 결정** |
| 시점 | `QUALITY_PASSED` 이후, TSU 생성 / reference chunking **이전** |
| 기록 위치 | `NAE/governance/corpus_admissions.jsonl` (append-only, 신규 — §12 MUST M-3). 항목: `{source_id, decided_by, date, track: "tsu"\|"reference", authority_class, content_genre[], theological_category[], tradition, reference_quality_confirmed?, rationale, evidence_refs[]}` |
| state와의 관계 | **state가 아니다.** `RegistrationState` / `ProcessingState` 어느 enum에도 값을 추가하지 않는다. ADR-019 §6이 설계한 `processing_status=TSU_ELIGIBLE` 게이트의 governance 대체물이며, 그 게이트가 코드로 구현되면 이 기록이 그 입력이 된다 |
| 대응 코드 | 현재 없음 (수기 governance 기록). ADR-019 `TSU_ELIGIBLE` = 미구현 |

### 6.2 Review Disposition — 기존, per-TSU

| 항목 | 내용 |
|---|---|
| 정의 | 개별 TSU claim의 검수 결과 |
| 저장 | `tsu.json` 각 레코드의 `review_status` ∈ {`generated`, `reviewed`, `verified`, `rejected`} (`NAE/pipeline/tsu/review_gate.py` `VALID_REVIEW_STATUSES`) |
| Embedding 게이트 | `review_gate.py` `EMBEDDING_ELIGIBLE_STATUSES = {verified}` — `verified`가 아니면 BLOCK |
| 현재 | Dagg 2,958 / Hiscox 361 `verified`; Fuller Vol01 3,643 전부 `generated` |
| Reference track | **해당 없음** (claim 검수 대상 아님) |

### 6.3 Retrieval Eligibility — 기존, 런타임 게이트 (corpus state 아님)

| Track | 게이트 | 소유 ADR | 기본값 |
|---|---|---|---|
| TSU | `config.yaml modules.nae_pd.enabled` | ADR-024 | **false** |
| Reference | `search_reference()` conditional heuristic (`ui/pages/chat.py`) | ADR-028 (DRAFT) | 조건부 |

임베딩되어 있다는 사실만으로 retrieval 대상이 되지 않는다 — 이 게이트가 별도로 통제한다. 세션별
자료 선택(Research Scope)은 ADR-029 PHASE 6.

### 6.4 용어 매핑 (구 → 신)

| v1/v2 "ELIGIBLE" 용법 | 최종 용어 | 성격 |
|---|---|---|
| "category + authority + human review 통과" | **Admission Decision** (앞부분) + **Review Disposition** (뒷부분) | governance 결정 + per-TSU 결과 |
| "Research Scope에 포함되어 retrieval 대상 (ACTIVE)" | **Retrieval Eligibility** | 런타임 config 게이트 |

---

## 7. Metadata Authority (F-1)

### 7.1 기존 `category` 필드 — 실측 정의

| 항목 | 실측 |
|---|---|
| 위치 | **TSU record** (`NAE/corpus/tsu/*/tsu.json` 각 레코드), Metadata Schema 2.0.0 additive 필드 |
| 값 세팅 | `NAE/pipeline/tsu/metadata_migration.py:161` → `metadata["category"] = None`; `metadata["category_status"] = "AUTHORITATIVE_SOURCE_MISSING"` |
| 현재 값 | 3,319 production TSU **전부 `None`** (`category_status = AUTHORITATIVE_SOURCE_MISSING`) |
| 의도된 의미 | 문서의 **주제/장르 분류** (단일 문자열, 예: 구버전 pilot의 `category: church_order`). `NAE_METADATA_SCHEMA_2_DESIGN_REVIEW_001.md` §3.1: "어디에도 Production 값 없음", "추측 금지 대상", 사람 확인 필요 |
| 짝 필드 | `citation_policy` / `citation_policy_status` (동일하게 `None` / `AUTHORITATIVE_SOURCE_MISSING`) |

### 7.2 `authority_class` (v2 신규) — 정의

| 항목 | 내용 |
|---|---|
| 위치 | **source / manifest 계층 (M2 = `NAE/pipeline/registration/state/source_manifest.yaml`)**, `source_id` 키 |
| 값 | enum: `primary_doctrinal` / `historical_witness` / `reference` / `application` |
| 의미 | 자료의 **교리적 무게** — 생성 프롬프트에서 근거 우선순위 결정용 (ADR-015 §3.5 "Authority Weight 4단계"와 정합 확인) |
| TSU record 기재 | **하지 않는다** |

### 7.3 관계 선언 (F-1 핵심)

> **`category`와 `authority_class`는 서로 다른 개념이며 서로 다른 계층에 있다.**
>
> | | `category` (기존) | `authority_class` (신규) |
> |---|---|---|
> | 계층 | TSU record (per-claim) | source / manifest M2 (per-source) |
> | 축 | 주제/장르 ("무엇에 관한 것인가") | 교리적 무게 ("근거로서 얼마나 무겁게 다룰 것인가") |
> | 값 예 | `church_order`, `theology` | `historical_witness`, `primary_doctrinal` |
> | 현재 상태 | `None` / `AUTHORITATIVE_SOURCE_MISSING` (3,319 전부) | 미존재 (M2 backfill 예정, §12 M-2) |
>
> **중복 필드를 새로 만들지 않는다.** `authority_class`는 `category`를 대체하지 않고, `category`도
> 교리적 무게 판정에 쓰이지 않는다. 두 필드는 독립적으로 채워진다.

### 7.4 적용 계층 지정

| 개념 | SSOT 계층 | 파생 여부 |
|---|---|---|
| source-level 장르 | M2 `content_genre[]` | SSOT |
| source-level 신학 주제 | M2 `theological_category[]` | SSOT |
| source-level 전통 | M2 `tradition` | SSOT |
| source-level 교리적 무게 | M2 `authority_class` | SSOT (신규) |
| TSU-level 주제/장르 (`category`) | — | **M2 `content_genre` 대표값에서 파생 가능** (TSU 빌드 시, **신규 source에 한함**). 기존 3,319는 `None` 유지 |

### 7.5 Backward Compatibility

- 3,319 production TSU record: **필드 추가/변경 없음**. `category`는 계속 `None` /
  `category_status=AUTHORITATIVE_SOURCE_MISSING`. migration 없음.
- `authority_class` / classification 필드는 M2에만, `required: false`로 시작 (ADR-021 WARNING-first).
  미지정 source는 FAIL이 아니라 WARNING → Admission Decision 대기.
- 기존 `metadata_migration.py`, `review_gate.py`, `builder.py`, indexer, embed client — **무수정**.

---

## 8. M2 SSOT / M3 Backlog / M1 Disposition (F-3)

### 8.1 실측된 3개 파일

| 라벨 | 정확한 경로 | schema / 형식 | 레코드 | forensic finding |
|---|---|---|---|---|
| **M1** | `NAE/authority/source_manifest.yaml` | YAML, `schema_version: '1.2'` | 10 (`BAP-CHURCH-DAGG-001`, `BAP-CHURCH-HISCOX`, `BAP-MISS-FULLER-VOL01`…`VOL08`) | **M2의 byte-identical prefix** (앞 10 레코드 완전 동일) |
| **M2** | `NAE/pipeline/registration/state/source_manifest.yaml` | YAML, `schema_version: '1.2'` | 14 (M1의 10 + `BAP-REF-SMITH-VOL01`…`VOL04`) | ADR-021 registration pipeline이 write |
| **M3** | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | CSV | 25 data rows | 2026-08-01 acquisition wishlist ("25 planned"), source_id 규약 상이 (`BAP-CONF-1689` 등), Dagg/Fuller identity가 M1/M2와 불일치 |

### 8.2 역할 선언

| 파일 | 역할 | 조치 (이 ADR = 문서만) |
|---|---|---|
| **M2** | **Source Registry SSOT** — NAE에 등록된 source의 정본 목록. registration pipeline이 유일 writer | 파일 헤더에 `# ROLE: Source Registry SSOT (ADR-030 §8)` 주석 추가 (별도 문서 task) |
| **M3** | **Acquisition Backlog Tracker** — 확보 예정/확보 시도 목록. source registry가 **아니다** | 헤더에 `# ROLE: Acquisition Backlog Tracker — NOT a source registry`. 19건 CLAIM-ONLY 행은 유지하되 `status`를 `PLANNED` / `UNACQUIRED`로 표기 |
| **M1** | **`derived` (non-authoritative mirror)** — M2 앞부분의 복사본. 독립 authority 없음 | 아래 §8.3 |

### 8.3 M1 disposition — 구체 절차

1. **즉시 삭제하지 않는다.**
2. **역할 = `derived`.** M1 파일 헤더에 주석 추가(문서 task): `# DERIVED from
   NAE/pipeline/registration/state/source_manifest.yaml (M2). Non-authoritative mirror. Do NOT hand-edit.
   See ADR-030 §8.3.`
3. **runtime consumer 확인** — 재평가에서 repo grep(`*.py`) 결과 `NAE/authority/source_manifest.yaml`을
   로드하는 코드 **0건**. (`NAE/pipeline/registration/authority.py`와
   `scripts/generate_legacy_authority_snapshot.py`는 `NAE/authority/{authors,works}.yaml` 및
   `legacy_snapshot/`만 참조하며 `source_manifest.yaml`은 참조하지 않음.)
4. **별도 migration task** (이 ADR 아님): (a) yaml/json/test/config 포함 repo 전수 grep으로 consumer 0
   재확인 → (b) consumer가 없으면 M1을 `archive/`로 이동하거나 M2를 가리키는 pointer 파일로 대체 →
   (c) consumer가 있으면 그 consumer를 M2로 재배선한 뒤 이동. 삭제는 이동 후 별도 결정.
5. 그 전까지 M1은 **읽기 전용 파생물**로 취급 — 어떤 작업도 M1을 수정하지 않는다.

### 8.4 Schema 보강 (M2, backward-compatible — §12 M-2와 함께)

- `raw_path` : canonical 생성에 실제 사용된 파일 (Dagg/Hiscox = `hocr.html`, Fuller/Smith = `original.pdf`).
  부재가 C1 "checksum mismatch" 오판 원인 (forensic §3.2 — 결함 아님, hygiene).
- `checksum_target` : `raw_checksum`이 가리키는 파일.
- `content_genre[]` / `theological_category[]` / `tradition` / `authority_class` (§7.4), `required: false`.

### 8.5 ADR-019 manifest layer

`processing_status` / `tsu_access` / `manifest_id` 기반 "Manifest Layer"는 **런타임에 존재하지 않는다**
(grep 0건, ADR-019 Promotion Evidence "TSU 빌더 게이트 미구현"). 처리 상태 권위는 §10의 state store다.

---

## 9. Stale Artifact Governance

### 9.1 확인된 실패 (forensic §12)

`NAE/corpus/tsu/{Dagg,Hiscox}/index_report.json` (`indexed: 5`, `generated_at: 2026-08-09T18:32`) —
2026-08-09 pilot smoke test 후 동결. 검수 후 실제 인덱싱은 `embed_batch24_36.py` /
`nae_incremental_ingest.py`가 수행하며 이 파일을 갱신하지 않음 → Ops Dashboard가 stale 값을 SSOT로
소비 → C1 audit "5 indexed / NOT PRODUCTION READY" 오판. 실제 Qdrant = 2,958 / 361.

### 9.2 4-way 구분 (혼동 금지)

```
Current Production State  = Qdrant live count + incremental_state.json + tsu.json::review_status   (권위)
Historical Report         = index_report.json, promotion_batch*_evidence.json                      (시점 스냅샷)
Pilot Artifact            = _*backup*/, _remediation_backup_*, pilot smoke outputs                  (일회성)
Production State (문서)     = ADR-030 §14, STATE.md    (Current Production State와 일치 필수)
```

### 9.3 최소 mechanism

1. 모든 상태 report(`*.json` / `*.md`)에 `generated_at`(UTC ISO) + `pipeline_stage` 포함. 없으면
   downstream이 SSOT로 소비 금지.
2. stale로 판명된 report에는 삭제 없이 `superseded_by` 마커 추가
   (예: `index_report.json` → `"superseded_by": "incremental_state.json + nae_tsu_v1 live count"`).
3. pilot/smoke/backup 산출물은 `*_pilot_*` / `_*backup*` 접두사 강제, production 판정이 이 경로를 읽지
   않음 (코드 리뷰 체크 항목).
4. **read-only reconciliation 명령 1개** (§12 M-4): M2 ↔ `incremental_state.json` ↔
   `tsu.json::review_status` ↔ Qdrant count 대조, drift 출력, 자동 수정 없음. ADR-020 `index_all()`
   reconciliation 역할 확장.
5. 검수 후 인덱싱 스크립트가 `index_report.json`을 갱신하도록 배선 통일 — 또는 `index_report.json`을
   authority에서 공식 제외 (backlog).

**cleanup은 이 ADR에서 수행하지 않는다.**

---

## 10. State Authority Map (F-4)

**판정: 새 state machine 없음.** 현재 권위를 문서로 고정한다. 아래는 층위가 다른 것들이며 서로 경쟁하는
authority가 아니다.

| 관심사 | 권위 저장소 | 성격 | 현재 |
|---|---|---|---|
| Source registration | `RegistrationState` → `NAE/pipeline/registration/state/registration_state.json` | source 단위 **stage** | 10 source 전부 `QUALITY_PASSED` (Smith 미기재 — M2에만 등록) |
| Source identity | **M2** `source_manifest.yaml` | 정본 목록 (SSOT) | 14 레코드 |
| Admission Decision | `NAE/governance/corpus_admissions.jsonl` (신규, §11) | **governance 결정 기록** (state 아님) | 미생성 (MUST M-3) |
| TSU processing | `ProcessingState` → `NAE/pipeline/ingest/state/incremental_state.json` | TSU 단위 **stage 위치** | 3,319 전부 `INDEXED` |
| **Review Disposition (결과)** | `tsu.json` 각 레코드 `review_status` | per-TSU **결과값 — SSOT** ("이 claim이 verified인가") | 3,319 verified |
| **Review stage (위치)** | `ProcessingState.HUMAN_REVIEW` / `HUMAN_REVIEW_REQUIRED` | "이 TSU가 지금 검수 단계에 있는가" (컨베이어 위치) | 해당 없음 — 3,319 전부 `INDEXED`로 통과 완료 |
| **Review evidence (audit)** | `NAE/review/human/decisions/` 40파일 | "누가·언제·무엇을 결정했나" (audit trail) | reviewer `David`, 2026-08-09~11, APPROVED 3,319 |
| Review v2 (미래) | ADR-027 `ReviewStateV2` / `DispositionV2` | disposition 생성 **프로세스** (결과는 여전히 `review_status`로 표현) | DRAFT, 776 pilot 미실행 |
| 물리 벡터 (TSU) | Qdrant `nae_tsu_v1` payload | 저장 실체 | 3,319 (전부 verified) |
| 물리 벡터 (Reference) | Qdrant `nae_ref_v1` payload | 저장 실체 | 34,948 chunk |
| Retrieval 노출 (TSU) | `config.yaml modules.nae_pd.enabled` | 런타임 게이트 | **false** |
| Retrieval 노출 (Reference) | ADR-028 heuristic | 런타임 게이트 | DRAFT |
| Research Scope (세션별) | — | 부재 | ADR-029 PHASE 6 |

### 10.1 `review_status` vs `HUMAN_REVIEW` — 명시적 구분 (F-4)

| | `tsu.json::review_status` | `ProcessingState.HUMAN_REVIEW` |
|---|---|---|
| 무엇 | 검수 **결과** (generated/reviewed/verified/rejected) | 증분 pipeline의 **단계 위치** (DISCOVERED..INDEXED 중 하나) |
| 어디 | TSU record 안 (`NAE/corpus/tsu/*/tsu.json`) | `incremental_state.json` (`tsu_id → {state, content_hash}`) |
| 쓰는 주체 | `builder.py` / 검수 프로세스 | 증분 ingest 실행기 |
| 읽는 주체 | `review_gate.py` (embedding 게이트) | 증분 ingest 실행기 (다음 단계 판단) |
| authority | **verified-ness의 SSOT** | 파이프라인 진행 위치. `review_status`를 대체하지 않음 |
| 현재 | 3,319 verified | 3,319 전부 `INDEXED` (HUMAN_REVIEW 단계는 이미 지남) |

두 값은 **동일 authority가 아니다**: `review_status`는 "결과", `HUMAN_REVIEW`는 "그 결과를 만드는 단계에
지금 있는가"이다. `NAE/review/human/decisions/`는 그 결정의 **증거**다. 셋 다 계층이 다르므로 중복
추적이 아니다.

---

## 11. Human Eligibility Governance (F-5)

### 11.1 4단계 구분 — 명문화

> **ACQUIRED ≠ EMBEDDING ELIGIBLE ≠ EMBEDDED ≠ RETRIEVAL-ELIGIBLE**

| 단계 | 정의 | 어디에 기록되나 | 사람/기계 |
|---|---|---|---|
| **ACQUIRED** | raw 파일 확보 + 무결성 검증 | `RegistrationState.RAW_PRESERVED` + `raw_checksum_ledger.jsonl` | 기계 |
| **ADMISSION DECISION** | "이 source를 corpus로 받아들이고 어느 track으로 보낼지" + `authority_class` / classification 부여 | `NAE/governance/corpus_admissions.jsonl` (append-only, 신규) | **사람 (HQ)** |
| **EMBEDDING ELIGIBLE** | — TSU track: `review_status == "verified"` (`review_gate.py`)  — Reference track: Admission Decision + `reference_quality_confirmed == true` (예: PBC1765는 HQ HOLD) | TSU: `tsu.json::review_status`  · Reference: admissions 기록의 `reference_quality_confirmed` | TSU: 사람 검수 결과  · Reference: 사람 |
| **EMBEDDED** | 물리 벡터가 collection에 존재 | `ProcessingState.EMBEDDED`/`INDEXED` + `nae_tsu_v1` / `nae_ref_v1` | 기계 |
| **RETRIEVAL-ELIGIBLE** | 런타임에 검색 대상 | `config.yaml modules.nae_pd.enabled` (TSU) / ADR-028 heuristic (Reference) | 설정 |

**자료를 확보했다고 자동으로 embedding 대상이 되지 않는다.** ACQUIRED → EMBEDDING ELIGIBLE 사이에
**Admission Decision(사람)**이 반드시 있다.

### 11.2 신규 자료 flow (명확한 순서)

```
source acquisition (collector / 수동)
   → registration (ADR-021: RAW_PRESERVED → VALIDATED → QUALITY_PASSED)
   → ADMISSION DECISION (사람, corpus_admissions.jsonl):
        track = tsu | reference
        authority_class, content_genre[], theological_category[], tradition
        (reference인 경우) reference_quality_confirmed
   → track 배정
        ├─ TSU Track: TSU_GENERATED → HUMAN_REVIEW → review_status=verified → EMBEDDED → INDEXED
        └─ Reference Track: (quality 확인) → CHUNKED → REFERENCE_INDEXED
   → Retrieval Eligibility 게이트 (nae_pd / ADR-028 heuristic)
```

### 11.3 `corpus_admissions.jsonl` — governance 기록 (state machine 아님)

| 항목 | 내용 |
|---|---|
| 경로 | `NAE/governance/corpus_admissions.jsonl` (신규 — §12 MUST M-3에서 생성) |
| 형식 | append-only JSONL. 한 줄 = 한 source의 admission 결정 |
| 필드 | `source_id`, `decided_by`, `date`, `track` (`"tsu"`\|`"reference"`), `authority_class`, `content_genre[]`, `theological_category[]`, `tradition`, `reference_quality_confirmed` (reference track만), `rationale`, `evidence_refs[]` |
| 성격 | **거버넌스 결정 기록** — `NAE/review/human/decisions/`와 같은 패턴이되 source-admission 단위. `RegistrationState` / `ProcessingState`에 값을 추가하지 않으며 새 enum도 아니다 |
| 게이트 역할 | 이 기록이 없는 source는 TSU 생성 / reference chunking을 시작하지 않는다 (수기 확인; ADR-019 `TSU_ELIGIBLE` 코드 게이트가 구현되면 이 기록이 그 입력) |

### 11.4 기존 3,319 production TSU + Smith — 소급 처리 (재처리·재승인 없음)

- **Dagg / Hiscox (3,319 verified TSU)**: 기존 human review 증거(`NAE/review/human/decisions/` 40파일,
  APPROVED 3,319, reviewer David, 2026-08-09~11)가 Admission + Review를 **이미 충족**한다.
  → `corpus_admissions.jsonl`에 Dagg·Hiscox 각 1건의 **back-fill 항목**을 그 증거를 `evidence_refs`로
  인용해 기록한다. **개별 TSU 재검수·재승인·재임베딩 없음.**
- **Smith Vol1–4 (`nae_ref_v1` 34,948 chunk)**: `docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md`
  + ADR-028 + M2 등록이 Admission을 충족한다. → `corpus_admissions.jsonl`에 track=`reference`,
  `authority_class=reference`, `reference_quality_confirmed=true`인 back-fill 항목 1건(또는 vol별 4건).
  **재chunk·재인덱싱 없음.**
- back-fill은 **문서 기록 행위**이며 corpus / Qdrant / state store를 건드리지 않는다.

---

## 12. MUST / SHOULD / NOT YET

### MUST HAVE

| # | 항목 | 산출물 | mutation | 종결 (2026-08-28) |
|---|---|---|---|---|
| M-1 | M2 = Source Registry SSOT, M3 = Acquisition Backlog Tracker, M1 = `derived` mirror — 각 파일 헤더 주석 + 1페이지 "NAE Manifest & Authority SSOT" 문서 | 문서 + 주석 | 코드 0 | ✅ `470a1b5` (헤더 주석) + `NAE-Manifest-Authority-SSOT.md` (`fcaa380`~`0931e0c`) · CUE 검증 |
| M-2 | M2 schema에 `content_genre[]` / `theological_category[]` / `tradition` / `authority_class` / `raw_path` / `checksum_target` 추가 (`required: false`), 14 레코드 backfill | schema + M2 YAML | manifest만 | ✅ `5f4e300` (A-2a) → `1fa6fce` (A-2b-1) → `0931e0c` (A-2b-2) · CUE 독립검증 ×3 · 분류 권위 `CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` RATIFIED v1.1 |
| M-3 | `NAE/governance/corpus_admissions.jsonl` 신설 + Dagg / Hiscox / Smith back-fill 항목(기존 증거 인용) + admission flow 문서화 | 신규 governance 파일 (append-only) | governance 기록만 | ✅ `ad1464d` · HQ CLOSED |
| M-4 | read-only reconciliation 명령 (`scripts/nae_corpus_reconcile.py`) — M2 ↔ `incremental_state.json` ↔ `tsu.json::review_status` ↔ Qdrant count drift 출력, `--apply` 없음 | 신규 script (read-only) | 0 | ✅ `5b0a867` · HQ GREEN/CLOSED (F-1/F-2/F-3 correction 포함) |
| M-5 | ADR-030 status 갱신 (본 문서 = 완료) | ADR 상태 변경 | — | ✅ 본 커밋 · CUE |

### SHOULD HAVE

| # | 항목 |
|---|---|
| S-1 | T1–T9 → §7.4 축 매핑 참고표 (부록) |
| S-2 | `NAE/authority/{authors,works}.yaml` (비어 있음) 채우거나 공식 폐기 결정 |
| S-3 | M1 archival migration task (§8.3-4) — consumer 0 전수 재확인 후 |
| S-4 | ADR-019 `TSU_ELIGIBLE` 코드 게이트를 `ProcessingState`에 추가할지 결정 (추가 시 `corpus_admissions.jsonl`이 입력) |
| S-5 | periodic reconciliation (M-4의 스케줄 확장) — ~50 works 시점 |
| S-6 | §14 표를 forensic 실측과 상시 동기화 |
| S-7 | `authority_class` ↔ ADR-015 "Authority Weight 4단계" 정합 확인 |
| S-8 | 기존 TSU `category` / `citation_policy` (`AUTHORITATIVE_SOURCE_MISSING`)의 authoritative source 확정 — 사람 확인 (신규 source는 M2 `content_genre`에서 파생) |

### NOT YET

| # | 항목 | 차단 근거 |
|---|---|---|
| N-1 | Research Scope 구현 / "ACTIVE" 상태 / retrieval engine의 scope 인식 | ADR-029 PHASE 6, rule #4; ADR-024 module-gate |
| N-2 | 새 독립 lifecycle state machine | §10 — 기존 권위로 충분 |
| N-3 | `corpus_tier` T1–T9 단일 schema 필드 | §7.4 — 축 혼합 |
| N-4 | tier별 separate retrieval indexing | indexed works 2개 |
| N-5 | scale threshold 자동 alert 구현 | 시기상조 |
| N-6 | automatic corpus classification / automatic embedding approval | Admission Decision은 사람 몫 (§11) |
| N-7 | ADR-027 v2 776 pilot | 별도 HQ 승인 |
| N-8 | SLBC1689 / PBC1742 provenance 재구성 | BROKEN, HQ decision 대기 |
| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | admission-in-principle 승인 (HQ, 2026-09-02) — TSU generation / TSU verification / human review / embedding / production ingestion 전부 HOLD 유지. corpus_admissions.jsonl ledger 기입 + 수기 게이트 활성화는 M3 모델 확장(별도 CUE 단계) 후. provenance: `docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md`. backlog, ADR-029 PHASE 순서 |
| N-10 | corpus-wide reprocessing / Qdrant migration | Production Freeze (§14) |

---

## 13. Migration Policy

- **기존 3,319 production TSU record: 필드 추가·변경·재생성 없음.** `category` 계속 `None` /
  `AUTHORITATIVE_SOURCE_MISSING`. `authority_class`는 TSU record에 쓰지 않음.
- **신규 메타데이터(`authority_class` / classification / `raw_path` / `checksum_target`)는 M2에만**,
  `source_id` 키, `required: false`.
- **M1 / M3: 재작성 없음** — 헤더 주석만. M1 archival은 별도 task(§8.3-4).
- **`corpus_admissions.jsonl`**: 신규 파일. 기존 3,319 + Smith는 back-fill **기록**만(재처리 아님, §11.4).
- **Qdrant / `incremental_state.json` / `registration_state.json` / embedding cache: 무접촉.**
- **`config.yaml` / `nae_pd` gate: 무변경.**
- Migration Required = **NO** (C1 verdict와 일치).

---

## 14. Production Safety

| 대상 | 상태 | 이 ADR의 접촉 |
|---|---|---|
| `nae_tsu_v1` (3,319) | CLEAN (5-way reconciled, forensic §8) | 없음 |
| `nae_ref_v1` (34,948) | 적재 완료 | 없음 |
| `incremental_state.json` (3,319 INDEXED) | live | 없음 |
| `registration_state.json` (10 QUALITY_PASSED) | live | 없음 |
| `core/retrieval.py::RetrievalEngine` | ADR-001 authority | 없음 |
| `config.yaml modules.nae_pd` | `enabled: false` | 없음 |
| 기존 pipeline / test / manifest / authority registry code | — | 없음 |

**Production Contact = NO. 채택 시점 Mutation = 0.** 이 문서는 governance 텍스트만 생성한다.

One Pipeline / One Config / One Retrieval Authority / Existing State Authority / Production Freeze /
No unnecessary migration — 전부 보존.

---

## 15. Test Requirements

ADR-030 v1 §17 A–G 유지 + v2 H–K + v2.1 L–N:

| Test | 설명 |
|------|------|
| A | Acquired source가 자동으로 retrieval-eligible이 되지 않는가 (`nae_pd` OFF) |
| B | `review_status != verified` TSU가 embedding candidate가 되지 않는가 (`review_gate.py`) |
| C | 동일 Work/Edition 중복 등록 차단 (ADR-021 §9) |
| D | Retrieval Eligibility 게이트(`nae_pd` / ADR-028 heuristic) 밖의 source가 노출되지 않는가 |
| E | Source provenance가 TSU / reference chunk까지 보존되는가 |
| F | M2 ↔ embedding state 불일치가 §9.4 reconciliation으로 감지되는가 |
| G | 기존 Production Corpus / Retrieval behavior 무변경 (baseline hash) |
| H | TSU Track과 Reference Track이 하나의 "embedded" 판정으로 뭉뚱그려지지 않는가 (collection·pipeline 분리 assert) |
| I | `authority_class` 미지정 source가 bulk embedding candidate가 되지 않는가 (WARNING → Admission Decision 요구) |
| J | `generated_at` 없는 / `superseded_by` 있는 report가 production SSOT로 소비되지 않는가 |
| K | §9.4 reconciliation 명령이 drift를 정확히 flag하고 mutation 0인가 |
| L | **(F-1)** `authority_class`가 TSU record에 기재되지 않는가; 기존 `category` 필드가 `authority_class` 값으로 덮어써지지 않는가 |
| M | **(F-4)** `review_status`(결과)와 `ProcessingState.HUMAN_REVIEW`(단계)가 서로를 대체하지 않는가 — 3,319가 `INDEXED`이면서 `review_status=verified`임을 동시 확인 |
| N | **(F-5)** `corpus_admissions.jsonl` 항목 없는 신규 source가 TSU 생성 / reference chunking 단계로 진입하지 않는가 (수기 게이트 확인); 기존 3,319 / Smith는 back-fill 항목으로 충족되며 재처리 트리거가 없는가 |

---

## 16. Scale Protection

| 위험 (50 → 500 → 5,000 works) | 방지 조치 |
|---|---|
| source identity가 manifest / TSU / reference / embedding 사이에서 갈라짐 | **M2 SSOT** (§8). M1 = derived, M3 = backlog. `BAP-CHURCH-DAGG-001` 같은 id가 파일마다 다른 저작을 가리키는 현상 차단 |
| human eligibility 판단이 자료마다 즉흥적 | **Admission Decision** 을 `corpus_admissions.jsonl`에 명시 기록 (§11) — 누가·언제·왜 받아들였는지 추적 |
| 동일 자료 중복 embedding | `edition_id` + `raw_checksum` 고유성 (ADR-021 §9, 구현됨) |
| 검증 안 된 자료의 Production 유입 | §4/§5 게이트 + `review_gate.py` (`verified`만) |
| classification 붕괴 | §7 다축 (`content_genre` / `theological_category` / `tradition` / `authority_class`), T1–T9 단일 필드 폐기 |
| doctrinal authority 상실 | `authority_class` (source 계층), Author→Work→Edition→Source File 추적 |
| stale 상태 파일이 현재를 잘못 대표 | §9 (`generated_at` 강제, `superseded_by`, reconciliation) |
| 모든 source 무조건 retrieval | `nae_pd` gate (기본 false) + Research Scope는 PHASE 6 |

threshold(100 / 500 / 1,000): guideline. 현재 indexed works = **2** (Dagg, Hiscox). 자동화 시기상조.

---

## 17. Final Principle

> NAE는 자료를 많이 임베딩하는 시스템이 아니라, 목회자가 신뢰할 수 있는 자료를 선택하고 검증하여 목적에
> 맞는 연구 범위 안에서 사용하는 시스템이다.

> 무엇을 임베딩할 것인가를 먼저 결정하고 — 그 결정은 **Admission Decision**으로 사람이 기록한다 —
> 어떻게 임베딩할 것인가는 그 다음이다. 이미 CLEAN으로 검증된 영역(3,319 verified TSU / `nae_tsu_v1`
> 3,319 / `nae_ref_v1` 34,948)에는 재처리·재승인·migration을 하지 않는다.

이 ADR은 governance·foundation이다. 대량 임베딩·기존 vector 삭제·TSU 재생성·Qdrant migration·Retrieval
Engine 변경·Research Scope 구현은 이 ADR의 채택 범위에 포함되지 않으며, 각각 별도 작업 명령과 (해당 시)
HQ 승인을 요구한다.

---

## Appendix A — T1–T9 → 다축 매핑 (참고, 비공식 — schema 필드 아님)

| v1 Tier | content_genre (대략) | authority_class 힌트 |
|---|---|---|
| T1 Scripture | — (성경 본문은 별도, 1순위) | — |
| T2 Biblical Interpretation | commentary | historical_witness / reference |
| T3 Baptist / Evangelical Theology | theology, confession | primary_doctrinal(confession) / historical_witness |
| T4 Sermonology | sermon | historical_witness |
| T5 Biblical Background | history | reference |
| T6 Language / Reference | commentary(reference) | reference |
| T7 Pastoral Theology | pastoral | application / historical_witness |
| T8 Church History | history | historical_witness |
| T9 Auxiliary | — | Admission Decision 개별 판정 |

Tier는 등록 의무가 아니다. 등록 시 §7.4의 M2 필드 할당이 의무.

---

## Appendix B — C1 Findings Resolution Record

- [x] FINDING 1 해결 — §7 (`category` vs `authority_class` 계층·개념 분리, 중복 필드 금지, TSU 무기재, migration 없음)
- [x] FINDING 2 해결 — §6 ("ELIGIBLE" 폐기 → Admission Decision / Review Disposition / Retrieval Eligibility)
- [x] FINDING 3 해결 — §8.3 (M1 = `NAE/authority/source_manifest.yaml`, byte-identical prefix, `derived`, consumer 0, 별도 archival task)
- [x] FINDING 4 해결 — §10.1 (`review_status` 결과 / `HUMAN_REVIEW` 단계 / decisions 증거 — 3층 분리)
- [x] FINDING 5 해결 — §11 (`ACQUIRED ≠ EMBEDDING ELIGIBLE ≠ EMBEDDED ≠ RETRIEVAL-ELIGIBLE`, `corpus_admissions.jsonl`, 3,319 소급 충족·재처리 없음)
- [x] 새로운 state machine 없음 (§6.1, §10, §11.3 명시)
- [x] Production mutation 없음 · 3,319 TSU 무변경 · Qdrant 무변경 (§13, §14)
- [x] Research Scope 구현 없음 (§12 N-1, ADR-029 PHASE 6)
- [x] TSU / Reference Track 분리 유지 (§4, §5)
- [x] M2 SSOT / M3 backlog / M1 대상 명확 (§8)
- [x] Human Eligibility decision 위치 명확 — `NAE/governance/corpus_admissions.jsonl` (§11.3)
- [x] `category` / `authority_class` 책임 명확 (§7.3)
- [x] `review_status` / `HUMAN_REVIEW` 책임 명확 (§10.1)
- [x] ADR-001/013/019/020/021/024/027/028/029 충돌 없음 (§4, §5, §6.3, §8.5, §10, §12 N-1)

---

## Appendix C — §12 MUST 종결 기록 (2026-08-28)

ADR-030 v2.1 §12 MUST 5개 항목 전량 완료. 각 항목 CUE 독립검증 → 단일 커밋 landing. Production mutation 0.

| 항목 | 종결 커밋 | 검증 | 핵심 산출물 |
|---|---|---|---|
| M-1 | `470a1b5` + `fcaa380`~`0931e0c` (SSOT 문서) | CUE | M1/M2/M3 역할 주석 + `docs/architecture/NAE-Manifest-Authority-SSOT.md` |
| M-2 | `5f4e300` (A-2a) → `1fa6fce` (A-2b-1) → `0931e0c` (A-2b-2) | CUE 독립검증 ×3 | M2 additive 6필드 (`required: false`): authority_class·raw_path·checksum_target·content_genre 14/14, theological_category 5/14, tradition 10/14 (RATIFIED v1.1). validator 16/0, governance test 29 passed |
| M-3 | `ad1464d` | HQ CLOSED | `NAE/governance/corpus_admissions.jsonl` (append-only) + Dagg/Hiscox/Smith 소급 + flow 문서 |
| M-4 | `5b0a867` | HQ GREEN/CLOSED | `scripts/nae_corpus_reconcile.py` (read-only, `--apply` 없음). test 20 passed · 인접 regression 49 passed · 실데이터 smoke "No drift detected" exit 0. F-1/F-2/F-3 bounded correction 포함 |
| M-5 | 본 커밋 | CUE | 본 문서 status = IMPLEMENTED / §12 MUST COMPLETE |

- 분류 권위: `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` (RATIFIED v1.1, HQ 2026-08-28).
- M-4 설계 권위: `docs/agents/cue/CUE-ADR-030-M4-RECONCILE.md` (RATIFIED v1.1).
- M-1/M-2 종결 감사: CUE read-only audit 2026-08-28 = GREEN.
- SHOULD (S-1~S-9) / NOT-YET (N-1~N-10)는 자동 착수 안 함 — 별도 HQ 우선순위 결정 대상.

---

**STATUS: IMPLEMENTED / §12 MUST COMPLETE (2026-08-28). 채택 ACCEPTED 2026-08-27 (v2.1 consolidated),
supersedes ADR-030 v1. §12 MUST M-1~M-5 전량 완료 — 각 단계 CUE 독립검증 GREEN, production mutation 0
(TSU 3,319 / nae_tsu_v1 3,319 / nae_ref_v1 34,948 / Qdrant / incremental_state / config 무변경).
SHOULD (S-1~S-9) / NOT-YET (N-1~N-10)는 별도 HQ 우선순위 대상. Production Contact NO. Migration NO.**
