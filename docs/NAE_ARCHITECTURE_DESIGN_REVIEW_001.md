# NAE Architecture Design Review — 001

**Review ID:** NAE-ARCHITECTURE-DESIGN-REVIEW-001
**Date:** 2026-08-02
**Reviewer:** C1 (Read-Only Architecture Verification)
**Status:** COMPLETE
**Scope:** 설계 문서(NAE_MODERN_CORPUS_ARCHITECTURE_v1.md, ADR-014, NAE_CORPUS_INGESTION_STANDARD_v1.md, ADR-015)와 현재 Repository 구조의 충돌 검증

---

## 1. Executive Summary

CUE가 작성한 4개 설계 문서(NAE_MODERN_CORPUS_ARCHITECTURE_v1.md, docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md, NAE_CORPUS_INGESTION_STANDARD_v1.md, docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md)가 **현재 NAE Repository Architecture와 전반적으로 호환**됩니다. 다만 **Metadata Layer 구축 전 해결해야 할 3건의 WARNING**과 **TSU Pipeline 직전 확인해야 할 1건의 BLOCKER**이 확인되었습니다.

**최종 판정: APPROVED WITH CONDITIONS**

---

## 2. Reviewed Documents

| # | 문서 | 위치 | 용도 |
|---|------|------|------|
| 1 | NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | 현대 코퍼스 아키텍처 설계 |
| 2 | ADR-014-NAE-Modern-Corpus-Layer.md | docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md | 현대 코퍼스 레이어 결정 |
| 3 | NAE_CORPUS_INGESTION_STANDARD_v1.md | docs/NAE_CORPUS_INGESTION_STANDARD_v1.md | 코퍼스 ingestion 표준 |
| 4 | ADR-015-NAE-Corpus-Ingestion-Standard.md | docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md | Ingestion Standard 결정 |

---

## 3. Existing Architecture Compatibility

### 3.1 RAW 원칙 검증 (NAE DATA ARCHITECTURE 기반)

**확인 결과:**

| 원칙 | 현재 구조 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| RAW immutable | `data/RAW/` + `data/nae/sources/` — `copy_source_file()` 불변 보장 | NAE_MODERN_CORPUS_ARCHITECTURE_v1 §RAW | **PASS** |
| public_domain / modern 분리 | `NAE/corpus/raw/archive_org/` 하위 디렉토리 이미 존재(confession, theology, commentary 등) | ADR-014 §Domain Separation | **PASS** |
| TSU 단일 경로 | `output/bench/tsu_dataset.jsonl` — `--dataset-path` 확장 완료(STEP4) | ADR-015 §Lifecycle | **PASS** (조건부) |

**핵심 발견:** `NAE_DATA_ARCHITECTURE.md` §3에서 확인된 TSU 경로 충돌 문제(`--output-dir`로 NAE registry 읽어도 TSU 산출물은 항상 `output/bench/tsu_dataset.jsonl`에 쓰임)는 **STEP4-D에서 `--dataset-path` CLI 인자 추가로 해결됨**. 다만 이 해결이 설계 문서(ADR-015)에 명시적으로 반영되지 않았음.

### 3.2 Retrieval Authority 검증 (ADR-001 기반)

**확인 결과:**

| 항목 | 현재 구조 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| `core/retrieval.py::RetrievalEngine` 권한 | 단일 Vector DB(`chroma_db/`) — NAE 데이터도 최종 합류 원칙 | ADR-014 §Storage Architecture | **PASS** |
| Source weighting | `core/retrieval.py` 내부 로직 — domain filter 미구현 | ADR-014 §Metadata Impact | **WARNING** (§6 참조) |

---

## 4. ADR-014 Review

### 4.1 Domain Separation

**설계 제안:**
```
NAE-PD    (public_domain)
NAE-MODERN (modern)
DBMA
```

**현재 구조 대조:**
```
NAE/corpus/raw/archive_org/
├── confession/
├── theology/
├── commentary/
├── history/
├── systematic_theology/
├── missions/
└── sermons/
```

**판정: PASS**

현재 `NAE/corpus/raw/archive_org/` 구조는 domain separation 원칙과 충돌하지 않음. 다만 설계 문서가 제안하는 `NAE-PD / NAE-MODERN` 최상위 구분보다 **세분화된 장르별 디렉토리**를 사용하고 있음 — 이는 현재 RAW 데이터 수집 현황(archive.org 중심)을 반영한 것으로, ADR-014의 domain separation과 충돌하지 않음(하위 호환).

### 4.2 Storage Architecture

**설계 제안:**
```
NAE/corpus/raw/
public_domain/
modern/
```

**현재 구조:**
```
NAE/corpus/raw/.DS_Store
NAE/corpus/raw/archive_org/    ← 이미 존재
├── books/
├── church_order/
├── commentary/
├── confession/
├── history/
├── missions/
├── sermons/
└── systematic_theology/
```

**판정: PASS (조건부)**

현재 구조가 설계 제안과 완전히 일치하지는 않으나(**장르별 디렉토리**가 최상위 구분), 이는 **하위 호환**임. `archive_org/` 하위에 모든 RAW 원문이 수집되어 있으며, `public_domain / modern` 구분은 향후 `NAE/corpus/raw/` 최상위에서 추가 가능. 현재 구조에 충돌 없음.

### 4.3 Metadata Impact

**확인 사항:**

| 항목 | 현재 상태 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| `source_manifest.schema.yaml` schema_version | `1.2` | `2.0-modern` 제안 | **WARNING** (§6.3 참조) |
| `content_genre` 필드 | confession/theology/history/commentary/sermon/mission/church_practice/pastoral | 동일 값 재사용 | **PASS** |
| `tradition` 필드 | Particular Baptist/American Baptist/Baptist Evangelical (자유 텍스트) | 동일 체계 | **PASS** |
| `theological_category` 필드 | confession/ecclesiology/soteriology/missions | 동일 체계 | **PASS** |
| `copyright_status` | `license` 필드로 대체(public_domain/copyright_restricted/unknown) | `copyright_status` 제안 | **WARNING** (§6.2 참조) |
| `usage_permission` | 미구현 | 설계 문서 제안 | **WARNING** (§6.2 참조) |
| `access_control` | 미구현 | 설계 문서 제안 | **WARNING** (§6.2 참조) |

### 4.4 Copyright Governance

**설계 제안 필드:**
- `source_type` — 현재 `content_genre`로 대체 가능
- `copyright_status` — 현재 `license` 필드 존재하지만 값 체계 다름
- `usage_permission` — **미구현**
- `access_control` — **미구현**

**판정: WARNING**

현재 `source_manifest.schema.yaml`의 `license` 필드(값: `public_domain`, `public_domain_original`, `public_domain_possible`, `copyright_restricted`, `unknown`)는 설계 문서가 제안하는 `copyright_status`와 **반드시 `usage_permission`과 `access_control`이 신규 추가**되어야 함. 현재 스키마에 이 두 필드가 없으며, ADR-014/ADR-015에 이 gap 해결 방안이 명시되지 않음.

---

## 5. ADR-015 Review

### 5.1 Lifecycle Compatibility

**설계 제안 Lifecycle:**
```
Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index
```

**현재 Pipeline 대조:**

| 단계 | 현재 구현 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| Registration | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` + `resources/theological_sources/*/source_manifest.yaml` | 동일 | **PASS** |
| Validation | `scripts/source_validator.py` (schema_version 1.2 기반) | 동일 | **WARNING** (§6.3 참조) |
| Classification | `core/noise_classifier.py` (DBMA noise 분류) + NAE `content_genre` | 부분적 | **PASS** |
| Metadata | `pipeline/canonical/annotate.py` + `pipeline/tsu/builder.py` | 동일 | **PASS** |
| Quality Gate | `pipeline/verify/` 모듈군(consistency, contradiction, duplicate, evidence, score) | 동일 | **PASS** |
| TSU | `pipeline/tsu/builder.py` + `scripts/build_tsu_dataset.py` | 동일 | **PASS** (조건부) |
| Embedding | `pipeline/embed/` 모듈군 | 동일 | **PASS** |
| Index | `pipeline/index/` (qdrant_store, indexer) | 동일 | **PASS** |

**핵심 발견:** ADR-015의 Lifecycle이 현재 NAE Pipeline 구조와 **전반적으로 호환**됨. 다만 `Validation` 단계에서 `source_validator.py`가 schema_version 1.2를 기준으로 검증하는데, 설계 문서가 제안하는 schema_version 2.0-modern과의 **버전 간격**이 명시되지 않음.

### 5.2 Authority Model

**설계 제안:**
```
author_id
work_id
source_id
```

**현재 구조 대조:**

| 항목 | 현재 구현 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| `source_id` | `NAE_SOURCE_MANIFEST_v1.csv::source_id` + `source_manifest.yaml::sources[].source_id` | 동일 | **PASS** |
| `author_id` | `NAE_SOURCE_MANIFEST_v1.csv::author` (문자열, 구조화 아님) | `author_id` (구조화 ID) 제안 | **WARNING** (§6.4 참조) |
| `work_id` | 미구현 | 설계 문서 제안 | **WARNING** (§6.5 참조) |

### 5.2.1 동일 저자 처리

현재 `NAE_SOURCE_MANIFEST_v1.csv`의 `author` 필드는 문자열(예: `"John Spurstow et al. (Baptist Assembly)"`). 설계 문서가 제안하는 `author_id` 구조화 ID로 변경 시 **동일 저자 통합**이 가능해짐. 다만 현재 구조에서 이 변경은 **Metadata Schema Version Upgrade** 필요.

### 5.2.2 동명이인 처리

현재 `author` 문자열 기반에서는 동명이인 구분이 불가능(예: `"Thomas Helwys"`와 `"T. Helwys"`가 동일 인물인지 판단 불가). `author_id` 도입 시 해결 가능.

### 5.2.3 Edition 관리

`work_id` 미구현으로 **Edition 관리가 현재 불가능**. 설계 문서가 제안하는 `work_id`는 동일 저작의 다른 Edition(예: SLBC1689 원본, SLBC1689 abridgment)을 구분하는 데 필수.

### 5.3 Duplicate Policy

**설계 제안:** 삭제 금지 원칙

**현재 구조 대조:** `pipeline/verify/duplicate.py` 존재 — 중복 감지 로직 구현됨. 삭제 금지 원칙은 `core/processing.py::copy_source_file()`의 불변 정책과 호환.

**판정: PASS**

---

## 6. Metadata Compatibility Audit

### 6.1 기존 Schema 변경 없이 가능한가?

**답: 부분적 YES, 완전한 YES NO**

| 항목 | 가능 여부 | 설명 |
|------|-----------|------|
| Domain Separation (NAE-PD / NAE-MODERN) | **YES** | 현재 `NAE/corpus/raw/archive_org/` 구조와 하위 호환 |
| Storage Architecture (raw/ 하위 디렉토리) | **YES** | 이미 존재하는 구조 |
| content_genre / tradition / theological_category | **YES** | `source_manifest.schema.yaml`에 이미 정의됨(schema_version 1.2) |
| copyright_status 값 체계 | **NO** | 현재 `license` 필드와 값이 다름 — schema_version upgrade 필요 |
| usage_permission 신규 필드 | **NO** | 현재 스키마에 없음 — schema_version upgrade 필요 |
| access_control 신규 필드 | **NO** | 현재 스키마에 없음 — schema_version upgrade 필요 |
| author_id 구조화 | **NO** | 현재 `author` 문자열 — schema_version upgrade 필요 |
| work_id 신규 필드 | **NO** | 현재 스키마에 없음 — schema_version upgrade 필요 |

### 6.2 Migration 필요한가?

**답: YES**

`copyright_status`, `usage_permission`, `access_control`, `author_id`, `work_id` 등 **5개 필드/값 체계 변경**이 schema_version 2.0-modern으로의 마이그레이션 필요.

### 6.3 Versioning 방식 적절한가?

**설계 문서 제안:** `schema_version: 2.0-modern`
**현재 상태:** `schema_version: 1.2`

**판정: WARNING**

`2.0-modern`이라는 버전 표기는 **SemVer와 충돌**(pre-release 태그 `-modern`이 SemVer에서 허용되나, DBMA의 기존 버전 관리 정책과 명확히 구분 필요). 권장: `2.0.0` (major version upgrade로 명시적).

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조

| 항목 | 현재 구현 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| 입력 데이터 형식 | `core/tsu_builder.py` — metadata JSONL | 동일 | **PASS** |
| metadata 전달 | `pipeline/tsu/builder.py` → `build_tsu_dataset.py` | 동일 | **PASS** |
| citation 정보 유지 | `pipeline/tsu/citation.py` | 동일 | **PASS** |

### 7.2 TSU 모델별 충돌 분석

| TSU 유형 | 현재 구조 | 설계 문서 | 충돌 |
|----------|-----------|-----------|------|
| Full TSU | `core/tsu_builder.py` — 전체 metadata 포함 | 동일 | **PASS** |
| Restricted TSU | `pipeline/tsu/config.py`에서 접근 제어 | 설계 문서와 호환 | **PASS** (조건부) |
| Citation Only TSU | `pipeline/tsu/citation.py` | 동일 | **PASS** |

### 7.3 TSU Pipeline 직전 확인 사항

**BLOCKER:** `NAE_DATA_ARCHITECTURE.md` §3에서 확인된 TSU 경로 충돌(`--output-dir data/nae/processed` 사용 시 `output/bench/tsu_dataset.jsonl` 덮어쓰기 위험)은 **STEP4-D에서 `--dataset-path` 추가로 해결됨**. 다만 이 해결이 ADR-015에 명시되지 않았음.

**권고:** TSU Pipeline 진행 전 ADR-015에 `--dataset-path` 해결 방안 명시 반영 필요.

---

## 8. Retrieval Compatibility

### 8.1 현재 Retrieval 구조

| 항목 | 현재 구현 | 설계 문서 | 충돌 |
|------|-----------|-----------|------|
| `RetrievalEngine` | `core/retrieval.py` — 단일 인스턴스 | 동일 | **PASS** |
| Source weighting | 미구현 (향후 계획) | ADR-014 §Metadata Impact | **WARNING** |
| Domain filter | 미구현 | ADR-014 §Storage Architecture | **WARNING** |
| Authority ranking | 미구현 | ADR-015 §Authority Model | **WARNING** |

### 8.2 코드 변경 없이 가능한가?

**답: NO**

설계 문서가 제안하는 Source weighting, Domain filter, Authority ranking은 **현재 RetrievalEngine에 구현되지 않음**. 코드 변경 필요. 다만 이는 **새로운 기능 추가**이지 기존 구조와의 충돌이 아님.

**판정: WARNING (non-blocking)**

---

## 9. Identified Risks

### Risk Summary Table

| # | 영역 | 심각도 | 설명 | 권고 |
|---|------|--------|------|------|
| R1 | Metadata Schema | **WARNING** | `license` 값 체계와 `copyright_status` 간 불일치 | schema_version 2.0.0 마이그레이션 시 `license` → `copyright_status` 이름 변경 또는 양립 방안 |
| R2 | Metadata Schema | **WARNING** | `usage_permission`, `access_control` 필드 미구현 | schema_version 2.0.0에 신규 필드 추가 |
| R3 | Metadata Versioning | **WARNING** | `2.0-modern` 버전 표기 — SemVer와 충돌 가능 | `2.0.0`으로 변경 권장 |
| R4 | Authority Model | **WARNING** | `author_id` 구조화 미비 — 동명이인 문제 | schema_version 2.0.0에 `author_id` 추가 |
| R5 | Work Edition | **WARNING** | `work_id` 미구현 — Edition 관리 불가 | schema_version 2.0.0에 `work_id` 추가 |
| R6 | TSU Pipeline | **BLOCKER** | ADR-015에 `--dataset-path` 해결 방안 미명시 | ADR-015 수정 반영 |
| R7 | Retrieval | **WARNING** | Source weighting/Domain filter/Authority ranking 미구현 | 코드 변경 필요 (non-blocking) |

### Risk Assessment by Category

| 카테고리 | 평가 |
|----------|------|
| Architecture | **PASS** — 설계 문서가 현재 아키텍처와 충돌하지 않음 |
| Metadata | **WARNING** — schema_version upgrade 필요, 5개 필드/값 체계 변경 |
| TSU | **WARNING (BLOCKER)** — ADR-015 문서 수정 필요 (`--dataset-path` 명시) |
| Retrieval | **WARNING** — 코드 변경 필요 (non-blocking) |
| Copyright | **WARNING** — `usage_permission`, `access_control` 신규 필드 필요 |
| Future Expansion | **PASS** — 현재 구조가 확장 가능함 |

---

## 10. Recommendations

### Priority 1 (ADR-015 수정 필수)

1. **ADR-015에 `--dataset-path` 해결 방안 명시** — TSU 경로 충돌의 STEP4-D 해결 사항을 설계 문서에 반영

### Priority 2 (Metadata Schema Upgrade 필수)

2. **schema_version 1.2 → 2.0.0 마이그레이션** — `2.0-modern`이 아닌 `2.0.0` 권장
3. **`license` → `copyright_status` 이름 변경 또는 양립** — 값 체계도 함께 조정
4. **`usage_permission` 신규 필드 추가** — copyright governance 필수
5. **`access_control` 신규 필드 추가** — copyright governance 필수
6. **`author_id` 구조화 필드 추가** — 동명이인 문제 해결
7. **`work_id` 신규 필드 추가** — Edition 관리 필수

### Priority 3 (Retrieval Enhancement)

8. **Source weighting 구현** — ADR-014 §Metadata Impact
9. **Domain filter 구현** — ADR-014 §Storage Architecture
10. **Authority ranking 구현** — ADR-015 §Authority Model

---

## 11. Final Verdict

### 판정: **APPROVED WITH CONDITIONS**

### 조건부 승인 기준

| 조건 | 상태 |
|------|------|
| Architecture 충돌 | **없음** — 설계 문서가 현재 아키텍처와 호환 |
| Metadata Schema Upgrade | **필수** — Priority 2 항목 6건 완료 전 TSU Pipeline 진행 금지 |
| ADR-015 문서 수정 | **필수** — Priority 1 항목 1건 완료 전 TSU Pipeline 진행 금지 |
| Retrieval Enhancement | **권고** — Priority 3 항목 3건은 TSU Pipeline 후 진행 가능 |

---

## 12. Final Answers to Required Questions

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: NO (전반적 호환, 일부 WARNING)**

설계 문서(ADR-014, ADR-015)가 제안하는 아키텍처는 현재 NAE Repository 구조와 **충돌하지 않음**. 다만 Metadata Schema(5개 필드/값 체계 변경)와 TSU 경로 명시 부족(**WARNING 2건**)이 확인됨.

### Q2: ADR-014는 승인 가능한가?

**답: CONDITIONAL APPROVAL**

Domain Separation, Storage Architecture, Copyright Governance 원칙은 승인 가능. 다만 Metadata Impact (§4.3에서 확인된 `copyright_status`, `usage_permission`, `access_control` 필드_gap_)가 schema_version 2.0.0 마이그레이션으로 해결된 후 **최종 승인** 필요.

### Q3: ADR-015는 승인 가능한가?

**답: CONDITIONAL APPROVAL (BLOCKER 있음)**

Lifecycle, Authority Model, Duplicate Policy 원칙은 승인 가능. 다만 **BLOCKER R6**(ADR-015에 `--dataset-path` 해결 방안 미명시)이 우선 해결되어야 **최종 승인** 가능.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: YES (6건)**

| # | 문제 | 심각도 |
|---|------|--------|
| 1 | `license` → `copyright_status` 값 체계 불일치 | WARNING |
| 2 | `usage_permission` 필드 미구현 | WARNING |
| 3 | `access_control` 필드 미구현 | WARNING |
| 4 | `author_id` 구조화 미비 | WARNING |
| 5 | `work_id` 미구현 | WARNING |
| 6 | schema_version 표기 (`2.0-modern` → `2.0.0`) | WARNING |

**이 6건이 모두 해결되기 전까지 Metadata Layer 구축을 보류** 권장.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: NO (조건부)**

**필수 조건:**
1. ADR-015에 `--dataset-path` 해결 방안 명시 반영 (Priority 1)
2. Metadata Schema 2.0.0 마이그레이션 완료 (Priority 2)

이 두 조건이 충족된 후 TSU Pipeline 진행 권장.

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: YES**

설계 문서가 제안하는 Source weighting, Domain filter, Authority ranking은 **새로운 기능 추가**이지 기존 RetrievalEngine을 변경하거나 손상시키는 것이 아님. 현재 `core/retrieval.py::RetrievalEngine`의 단일 인스턴스 원칙과 `chroma_db/` 단일 Vector DB 원칙이 유지됨.

---

## Appendix A: Reviewed File Inventory

| 파일 | 경로 | git 추적 | 상태 |
|------|------|----------|------|
| NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | 예 | 설계 문서 |
| ADR-014 | docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md | 예 | 결정 문서 |
| NAE_CORPUS_INGESTION_STANDARD_v1.md | docs/NAE_CORPUS_INGESTION_STANDARD_v1.md | 예 | 설계 문서 |
| ADR-015 | docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md | 예 | 결정 문서 |
| NAE_DATA_ARCHITECTURE.md | docs/NAE_DATA_ARCHITECTURE.md | 예 | 아키텍처 문서 |
| ADR-001 | docs/architecture/ADR-001-* | 예 | 아키텍처 결정 |
| source_manifest.schema.yaml | resources/theological_sources/source_manifest.schema.yaml | 예 | 스키마 정의 |
| NAE_SOURCE_MANIFEST_v1.csv | NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv | 예 | 매니페스트 |
| source_candidates.csv | resources/theological_sources/baptist/source_candidates.csv | 예 | 후보 목록 |

## Appendix B: Repository Structure Reference

```
NAE/
├── benchmark/                    ← benchmark_v1.jsonl, gold_benchmark_v1.jsonl
├── collectors/archive_org/       ← 수집 모듈
├── corpus/
│   ├── canonical/                ← canonical.json, canonical.txt
│   ├── embeddings/               ← 임베딩 캐시 (미구현)
│   ├── manifests/                ← manifest 저장
│   ├── metadata/                 ← metadata 저장
│   ├── quarantine/               ← quarantine 데이터
│   ├── raw/archive_org/          ← RAW 원문 (이미 수집됨)
│   ├── reports/                  ← 리포트
│   └── tsu/                      ← TSU 데이터셋
├── manifest/
│   └── NAE_SOURCE_MANIFEST_v1.csv
└── pipeline/
    ├── canonical/                ← canonicalize
    ├── embed/                    ← embedding
    ├── index/                    ← vector index
    ├── tsu/                      ← TSU builder
    └── verify/                   ← quality gate
```

---

**Review Complete. 2026-08-02.**