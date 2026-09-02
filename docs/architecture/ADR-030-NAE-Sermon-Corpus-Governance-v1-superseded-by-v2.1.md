# ADR-030: NAE Sermon Corpus Governance & Pipeline Foundation

| | |
|---|---|
| **Status** | **ACCEPTED** |
| **Date** | 2026-08-27 |
| **Approved** | 2026-08-27 |
| **Approver** | Rev. Bang / HQ |
| **Deciders** | 사용자 (HQ) |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Purpose

NAE의 설교 연구 Corpus가 향후 50권, 500권, 5,000권 이상으로 확대되더라도 무질서하게 증가하지 않도록 다음 원칙을 NAE의 **구조적·파이프라인 수준의 제약조건**으로 확립한다.

> **"무엇을 임베딩할 것인가"를 먼저 결정하고, "어떻게 임베딩할 것인가"를 그 다음 결정한다.**

Corpus의 양보다 **Source Authority, Research Purpose, Classification, Validation, Scope Control**을 우선한다.

---

## 2. Scope

이 ADR은 다음 영역을 다룬다:

- Corpus Category 체계
- Source Lifecycle (6단계 상태 구분)
- Embedding Eligibility Gate
- Research Scope Control
- Provenance 및 Edition Control
- Scale Protection

이 ADR은 **architecture/pipeline foundation**이다. 대량 임베딩, 기존 vectors 삭제, TSU 재생성, Retrieval Engine 변경을 포함하지 않는다.

---

## 3. Corpus Categories (Canonical)

NAE의 설교 연구용 canonical corpus category는 다음 9개 Tier로 정의된다.

| Tier | Category | Description |
|------|----------|-------------|
| T1 | Scripture | Bible text, textual/linguistic resources directly supporting Scripture study |
| T2 | Biblical Interpretation | major commentaries, exegetical works, biblical theology, hermeneutics |
| T3 | Baptist / Evangelical Theology | Baptist theology, systematic theology, confessions, ecclesiology, soteriology |
| T4 | Sermonology | biblical preaching, expository preaching, sermon construction, methodology |
| T5 | Biblical Background | biblical history, ancient Near East, Second Temple Judaism, Greco-Roman background |
| T6 | Language / Reference | Hebrew, Greek, Aramaic, lexicons, grammars, linguistic reference works |
| T7 | Pastoral Theology | pastoral theology, discipleship, spiritual formation, practical ministry |
| T8 | Church History | Baptist history, Reformation history, church history, historical theological witnesses |
| T9 | Auxiliary / Research Materials | 기타 자료 — 자동으로 Production Corpus에 포함하지 않음. 필요성과 authority를 별도로 평가 |

**모든 신규 source는 등록 시 최소한 하나의 Tier를 할당받아야 한다.** T9는 별도 승인이 필요한 영역이다.

---

## 4. Source Lifecycle — Acquired ≠ Validated ≠ Eligible ≠ Embedded ≠ Active

```
ACQUIRED → VALIDATED → ELIGIBLE → INGESTED → EMBEDDED → ACTIVE
```

각 상태의 정의:

| 상태 | 정의 | 책임 |
|------|------|------|
| **ACQUIRED** | 원본 파일이 확보됨 (raw disk에 존재) | Acquisition layer |
| **VALIDATED** | metadata, provenance, integrity 검사 통과 | Registration pipeline (ADR-021) |
| **ELIGIBLE** | corpus category + authority class 할당 완료, human review 통과 | Human Review (ADR-027) |
| **INGESTED** | TSU conversion 완료, TSU validation 통과 | TSU Builder (ADR-015) |
| **EMBEDDED** | vector store에 embedding됨 | Embedding pipeline (ADR-020) |
| **ACTIVE** | Research Scope에 포함되어 retrieval 대상이 됨 | Retrieval Engine / Research Scope config |

**핵심 규칙:**

> 어떤 자료도 위 단계를 우회하여 Production Retrieval Corpus에 직접 들어갈 수 없다.
> "Acquired" 상태의 자료가 자동으로 다음 단계로 진행되지 않는다.
> 각 단계는 명시적 게이트를 통과해야 한다.

---

## 5. Embedding Eligibility Gate

Embedding은 acquisition의 자동적인 다음 단계가 아니다. 다음 조건을 **모두** 만족하는 source만 embedding candidate가 된다:

```
Source Exists (ACQUIRED)
      ↓
Metadata Complete (VALIDATED)
      ↓
Source Validated (VALIDATED)
      ↓
Classification Assigned (ELIGIBLE — category + authority)
      ↓
Authority Assigned (ELIGIBLE)
      ↓
TSU Validated (INGESTED)
      ↓
Embedding Eligible (EMBEDDED)
      ↓
Embed
```

**검증되지 않은 자료의 대량 embedding을 수행하지 않는다.**

---

## 6. Research Scope Control

전체 corpus가 존재하더라도 모든 자료를 모든 설교 연구에 자동으로 사용하지 않는다.

```
NAE Sermon Research
│
├── Scripture (T1)
├── Selected Commentaries (T2)
├── Baptist Theology (T3)
├── Biblical Background (T5)
└── Selected Historical Sources (T8)
```

**구조적 요구사항:**

- Global Corpus, Corpus Category, Source, Work, Edition, Research Scope, Active/Inactive source를 구분할 수 있는 구조 설계
- **임베딩되어 있다는 이유만으로 Active Retrieval Source가 되는 구조를 금지**
- Research Scope는 source의 embedding 상태와 독립적으로 관리

---

## 7. Source Authority Model

현재 NAE의 기존 Authority Model:

> **Author → Work → Edition → Source File**

을 유지하고 확장한다. 각 자료는 최소한 다음 provenance를 유지해야 한다:

```
Author
Work
Edition
Source File
Source Category (corpus Tier)
Authority Class
Validation Status
Embedding Status
Research Scope Eligibility
```

**역사적 Baptist source에 대한 특별 규칙:**

> Dagg, Fuller 및 기타 역사적 침례교 자료는 별도의 theological witness로 분류할 수 있다.
> 역사적 Baptist source를 NAE의 절대적 doctrinal authority로 취급하지 않는다.
> 그 자료가 제공하는 것은 역사적·신학적 증언이며, 현재 Baptist doctrinal control과 동일한 authority level로 자동 승격되어서는 안 된다.

---

## 8. Duplicate / Edition Control

ADR-015 §3.4의 중복 정책을 계승한다:

- **Exact duplicate**: 해시 비교
- **Same Work Different Edition**: work_id + edition_id 대조
- **Different Scan**: 동일 work, 다른 source_file
- **Derivative OCR**: derived_from 참조 필드
- **Supplement**: related_work_id 참조 필드

**어떤 경우에도 파일을 삭제하지 않는다.** 관계는 Authority Layer의 참조 필드로만 표현.

---

## 9. Scale Protection

NAE Corpus가 50 → 500 → 5,000 works로 증가하더라도 다음 문제가 발생하지 않도록 설계:

| 위험 | 방지 조치 |
|------|----------|
| 동일 자료의 중복 embedding | edition_id + source_file 해시 고유성 |
| 잘못된 edition 혼입 | authority registry 대조 |
| 출처 불명 자료 | provenance 필수 게이트 |
| 검증되지 않은 자료의 Production Retrieval 유입 | lifecycle state 게이트 |
| 모든 source를 무조건 retrieval하는 구조 | research scope config |
| corpus category 붕괴 | 9-tier canonical 체계 강제 |
| source authority 상실 | author→work→edition→source_file 추적 |
| provenance 상실 | manifest layer (ADR-019) |
| obsolete embedding의 잔존 | lifecycle state + manifest 대조 |
| manifest와 실제 embedding state 불일치 | periodic reconciliation (ADR-020) |

---

## 10. Production vs Research Corpus

| 구분 | Production Corpus | Research Corpus |
|------|-------------------|-----------------|
| 목적 | 실제 retrieval에 사용 | 실험/평가용 |
| 상태 요구 | ACTIVE만 포함 | 모든 상태 포함 가능 |
| scope | research_scope config로 제어 | 별도 config |
| validation | full pipeline 통과 | relaxed 가능 |

---

## 11. Future Scale Policy

- Corpus가 100 works를 초과하면 periodic reconciliation 필수
- Corpus가 500 works를 초과하면 automated duplicate detection 필수
- Corpus가 1,000 works를 초과하면 tier별 retrieval separate indexing 검토
- 이 숫자는 guidelines이며, corpus governance 원칙(상태 게이트, provenance)은 항상 적용

---

## 12. Relationship to Existing ADRs

| ADR | 관계 |
|-----|------|
| ADR-014 (Modern Corpus Layer) | 설계 단계. 이 ADR과 충돌 없음. PD/Modern 분리 원칙 계승 |
| ADR-015 (Corpus Ingestion Standard) | 설계 단계. 10단계 lifecycle 정의. 이 ADR의 lifecycle과 정합 |
| ADR-016 (Metadata Authority Model) | Author→Work→Edition→Volume→Source 모델 계승 |
| ADR-017 (ID Governance) | source_id 유일성 규칙 계승 |
| ADR-019 (Corpus Manifest Layer) | Manifest Entry = Source 1:1, processing_status 추적. 이 ADR의 lifecycle state와 정합 |
| ADR-020 (Incremental Ingestion) | downstream 절반(Hash→State→Embed→Index). 이 ADR과 충돌 없음 |
| ADR-021 (Source Registration) | upstream 절반(Registration→Validation→Extraction→Quality Gate). 이 ADR의 VALIDATED 게이트와 정합 |
| ADR-027 (Human Review Disposition) | ELIGIBLE 상태의 human review 게이트와 정합 |
| ADR-028 (Smith Reference Layer) | reference tier 분류와 정합 |
| ADR-029 (Research Corpus Expansion Pipeline Lock) | phase lock과 정합. 이 ADR은 expansion의 governance 기반 |

---

## 13. Migration / Compatibility Considerations

- 기존 Production TSU(3,319 verified)에 필드 추가 없음 — 별도 state store 사용
- 기존 Qdrant nae_tsu_v1(3,319 points) 변경 없음
- 기존 manifest(NAE_SOURCE_MANIFEST_v1.csv) 재작성 없음 — 병행 유지
- ADR-014/015의 설계 단계 결정과 충돌 없음
- 신규 corpus category 필드는 manifest schema 2.0.0+에서만 적용 (ADR-014)

---

## 14. Verification Evidence

### VERIFIED — 실제 파일 시스템 확인 결과

#### Corpus Inventory (실측)

| 항목 | 경로 | 상태 | 근거 |
|------|------|------|------|
| Raw Sources | `NAE/corpus/raw/archive_org/` | 7 category, 18 work dirs | `find` 결과 |
| Manifest | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | 26 entries, all ACQUIRED | `head` + `wc -l` |
| Canonical Corpus | `NAE/corpus/canonical/` | 17 works processed | `find` 결과 |
| TSU (Production) | `NAE/corpus/tsu/Dagg_Church_Order/` | tsu.json 6MB, index_report.json | `wc -c` |
| TSU (Production) | `NAE/corpus/tsu/Hiscox_Standard_Manual/` | tsu.json 1.3MB | `wc -c` |
| TSU (Production) | `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/` | tsu.json 3.9MB | `wc -c` |
| Embedding Cache | `NAE/corpus/embeddings/cache/` | 47,578 files | `find | wc -l` |
| Authority Registry | `resources/theological_sources/authority/` | authors.yaml, works.yaml, editions.yaml 등 | `find` 결과 |
| Pilot Manifests | `resources/theological_sources/manifest/pilot/{dagg,fuller,hiscox}/` | 3 pilot manifests | `cat` 결과 |
| Registration Pipeline | `NAE/pipeline/registration/` | 10 modules (ADR-021) | `find` 결과 |
| Incremental Ingest | `NAE/pipeline/ingest/` | 8 modules (ADR-020) | `find` 결과 |
| Human Review | `NAE/review/human/` | 7 modules + checkpoints | `find` 결과 |

#### Current Corpus → Proposed Tier Mapping (실측 기반)

| Source | Category | Proposed Tier | Authority Class | Validation Status |
|--------|----------|---------------|-----------------|-------------------|
| SLBC1689 (1689 Confession) | Confession | T3 (Baptist Theology) | Primary Doctrinal | ACQUIRED |
| PBC1742 (Philadelphia Confession) | Confession | T3 (Baptist Theology) | Primary Doctrinal | ACQUIRED |
| PBC1765 (Baptist Catechism) | Catechism | T3 (Baptist Theology) | Primary Doctrinal | ACQUIRED |
| Dagg_Church_Order | Church Order | T8 (Church History) / T3 | Historical Witness | VALIDATED+EMBEDDED |
| Hiscox_Standard_Manual | Church Administration | T7 (Pastoral Theology) | Historical Witness | VALIDATED+EMBEDDED |
| Fuller_Complete_Works (Vol01-08) | Mission Theology | T3 (Baptist Theology) / T8 | Historical Witness | ACQUIRED (manifest only) |
| Smith_Bible_Dictionary (Vol1-4) | Bible Reference | T6 (Language/Reference) | Reference | ACQUIRED |
| AF1815, PBC1742, TH1612 | Various | 미분류 | 미정 | ACQUIRED |

#### Pipeline Gap Analysis (실측 기반)

| 단계 | 현재 상태 | 목표 상태 | Gap |
|------|----------|----------|-----|
| Source Classification | **미구현** — manifest에 category 필드 있으나 tier 체계 없음 | 9-tier canonical 체계 강제 | 신규 schema/validator 필요 |
| Source Authority | **부분 구현** — authority registry 존재, pilot manifest 존재 | tier별 authority class 자동 할당 | authority class 매핑 로직 필요 |
| Validation Gate | **구현됨** — ADR-021 registration pipeline (QUALITY_PASSED) | VALIDATED 상태 게이트 | 정합성 확인 필요 |
| TSU Generation | **부분 구현** — TSU Builder 존재, 3 works TSU화됨 | ELIGIBLE → INGESTED 게이트 | TSU Builder에 ELIGIBLE 체크 추가 필요 |
| Embedding Eligibility | **미구현** — embedding cache 47,578 files 있으나 state 게이트 없음 | EMBEDDED 상태 게이트 | embedding pipeline에 state 체크 추가 필요 |
| Research Scope | **미구현** — retrieval scope config 없음 | ACTIVE 상태 게이트 | research_scope config 구조 설계 필요 |
| Provenance Tracking | **부분 구현** — manifest layer (ADR-019) | lifecycle state 추적 | manifest ↔ state 정합성 검증 필요 |

#### Dagg / Fuller Classification Status (실측 기반)

| Source | Files Present | Manifest | Canonical | TSU | Embedding | Tier | Authority Class |
|--------|--------------|----------|-----------|-----|-----------|------|-----------------|
| Dagg_Church_Order | PDF + hOCR + OCR | Pilot manifest | canonical.json/txt | tsu.json (6MB) | embedded | T8/T3 | Historical Witness |
| Hiscox_Standard_Manual | PDF + hOCR + OCR | Pilot manifest | canonical.json/txt | tsu.json (1.3MB) | embedded | T7 | Historical Witness |
| Fuller_Complete_Works Vol01-08 | PDF + OCR (8 vols) | Pilot manifest + source_manifest.yaml | canonical Vol01-08 | tsu.json (Vol01 only, 3.9MB) | not embedded | T3/T8 | Historical Witness |
| Smith_Bible_Dictionary Vol1-4 | PDF + DJVU XML (Vol1-4) | Pilot manifest | canonical Vol1-4 | not generated | not embedded | T6 | Reference |

---

## 15. Recommendations

### RECOMMENDED — 즉시 필요한 변경

1. **Corpus Category Schema Extension**
   - `source_manifest.schema.yaml`에 `corpus_tier` 필드 추가 (T1-T9)
   - `authority_class` 필드 추가 (Primary Doctrinal / Historical Witness / Reference / Application Resource)
   - ADR-014 schema 2.0.0와 정합성 확인

2. **Lifecycle State Integration**
   - `NAE/pipeline/registration/state.py::RegistrationState` → `NAE/pipeline/ingest/state.py::ProcessingState` 간 매핑 정의
   - ACQUIRED → VALIDATED → ELIGIBLE → INGESTED → EMBEDDED → ACTIVE 전이 규칙 코드화

3. **Research Scope Config Structure**
   - YAML 또는 JSON으로 research scope 정의 (어떤 tier/source를 어떤 research session에 포함할지)
   - retrieval engine가 이 config를 읽도록 설계 (ADR-001/013 변경 필요)

4. **Duplicate Detection Enhancement**
   - edition_id + source_file 해시 기반 중복 감지
   - ADR-015 §3.4 정책 구현

### RECOMMENDED — 다음 단계

5. **Existing Corpus Tier Mapping Script**
   - 현재 26개 manifest entries를 9-tier 체계에 매핑하는 스크립트
   - 수동 검토가 필요한 entries 식별

6. **Periodic Reconciliation Tool**
   - manifest ↔ embedding cache ↔ Qdrant state 정합성 검증
   - ADR-020의 reconciliation 용도 확장

7. **Scale Threshold Monitoring**
   - corpus size에 따른 automated alerts
   - 100/500/1000 works threshold

### NOT VERIFIED — 추가 검증 필요

8. **ADR-014/015 구현 상태** — 두 ADR 모두 Proposed(승격 보류). 실제 구현 여부 재확인 필요
9. **Qdrant nae_tsu_v1의 actual point count** — 문서상 3,319 points이나 직접 확인 필요
10. **TSU Builder의 ELIGIBLE 게이트 연동** — ADR-019 Future Expansion에서 "미구현"으로 명시

---

## 16. Final Principle

> NAE는 자료를 많이 임베딩하는 시스템이 아니라, 목회자가 신뢰할 수 있는 자료를 선택하고 검증하여 목적에 맞는 연구 범위 안에서 사용하는 시스템이다.

이 원칙은 Corpus lifecycle, embedding eligibility, research scope, provenance 및 retrieval governance에 반영되어야 한다.

---

## 17. Test Requirements

다음 테스트를 검증할 수 있는 테스트 추가 권장:

| Test | 설명 |
|------|------|
| A | Acquired source가 자동으로 Active가 되지 않는가? |
| B | Validated 되지 않은 source가 embedding candidate가 되지 않는가? |
| C | 동일 Work/Edition이 중복 등록되지 않는가? |
| D | Research Scope 밖의 source가 해당 research session에서 retrieval되지 않는가? |
| E | Source provenance가 TSU까지 보존되는가? |
| F | Embedding 상태와 manifest 상태가 불일치할 경우 감지되는가? |
| G | 기존 Production Corpus 및 Retrieval behavior가 의도하지 않게 변경되지 않는가? |

---

## 18. Deliverables Summary

1. **NAE Sermon Corpus Governance Specification** — 이 ADR 본문
2. **현재 Corpus Inventory와 새로운 분류체계의 mapping** — §14 Verification Evidence
3. **현재 pipeline과 목표 pipeline의 차이** — §14 Pipeline Gap Analysis
4. **필요한 코드 변경 목록** — §15 RECOMMENDED 즉시 필요한 변경 1-4
5. **필요한 schema / manifest 변경** — §15-1 (corpus_tier, authority_class)
6. **필요한 테스트** — §17 Test Requirements
7. **ADR 영향 분석** — §12 Relationship to Existing ADRs
8. **Dagg / Fuller 및 기타 Baptist source의 현재 classification 상태** — §14 Dagg/Fuller Classification Status
9. **아직 검증되지 않은 사항** — §15 NOT VERIFIED
10. **다음 단계 제안** — §15 RECOMMENDED 다음 단계

---

## 19. Decision History

| Date | Event | Result |
|------|-------|--------|
| 2026-08-27 | ADR-030 최초 작성 | ACCEPTED |
| 2026-08-27 | Corpus inventory 실측 확인 | VERIFIED — §14 |
| 2026-08-27 | Pipeline gap analysis | RECOMMENDED — §15 |

---

**FINAL STATUS: ACCEPTED. Corpus Governance framework 확립. 실제 corpus inventory, pipeline gap, source classification status 실측 기반 기록.**
