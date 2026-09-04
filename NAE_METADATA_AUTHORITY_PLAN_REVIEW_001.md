# NAE Metadata & Authority Plan Review — 001

**Review ID:** NAE-METADATA-AUTHORITY-PLAN-REVIEW-001
**Date:** 2026-08-02
**Reviewer:** C1 (Read-Only Architecture Verification)
**Status:** COMPLETE
**Scope:** `docs/NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md` 및 관련 설계 문서의 Architecture Review

---

## 1. Executive Summary

CUE가 작성한 `NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md`(이하 "Implementation Plan")은 `NAE_METADATA_GOVERNANCE_v1.md`(이하 "Governance v1"), ADR-014, ADR-015, `NAE_CORPUS_INGESTION_STANDARD_v1.md`와 **전반적으로 일관**됩니다. 다만 **Metadata Layer 구축 전 해결해야 할 2건의 WARNING**과 **TSU Pipeline 직전 확인해야 할 1건의 BLOCKER**이 확인되었습니다.

**최종 판정: APPROVED WITH CONDITIONS**

---

## 2. Architecture Compatibility

### 2.1 RAW Layer 검증

| 원칙 | Implementation Plan | 현재 구조 | 충돌 |
|------|---------------------|-----------|------|
| RAW 불변 | §1.1 "NAE/corpus/raw/ 건드리지 않는다" — Directory rename 금지 명시 | `NAE/corpus/raw/archive_org/` 기존 유지 | **PASS** |
| public_domain / modern 분리 | §1.2 생성 순서: authority → modern → baptist(기존 유지) | `NAE/corpus/raw/archive_org/` 하위 장르별 디렉토리 이미 존재 | **PASS** |
| Registry 위치 | `resources/theological_sources/authority/` — manifest와 같은 트리 | `resources/theological_sources/baptist/source_manifest.yaml`과 인접 | **PASS** |

**판정: PASS**

Implementation Plan의 §1.1에서 RAW 불변 원칙을 명시적으로 재확인하고 있으며, `NAE/corpus/raw/`에 대한 어떤 변경(rename 포함)도 금지하고 있음. 기존 `archive_org/` 구조와 충돌 없음.

### 2.2 Directory 구조 적합성

| 항목 | Implementation Plan | Governance v1 | ADR-014 | 충돌 |
|------|---------------------|---------------|---------|------|
| `authority/` 위치 | `resources/theological_sources/authority/` | §5.3 동일 | 미명시 | **PASS** |
| `modern/` 위치 | `resources/theological_sources/modern/{7개 카테고리}/` | §2.2 동일 | §Domain Separation | **PASS** |
| `baptist/` 유지 | "기존 v1.2, 변경 없음" — 디렉토리 신설 없음 | §7.1 동일 | 미명시 | **PASS** |

---

## 3. Authority Model Review

### 3.1 Entity 모델 적합성

**Implementation Plan §3 제안:**
```
Author → Work → Edition → Source File
```

**Governance v1 §5.1 확인:**
```
Author
  ↓
Work
  ↓
Edition (신규 승격)
  ↓
Source File
```

**판정: PASS**

4단계 Entity 모델(Author/Work/Edition/Source File)이 **역사 자료 적용 가능성**에서 적절함. 특히 `edition_id` 신규 도입(C1 Review R4/R5 대응)으로 동일 저작의 여러 판본을 구분하는 canonical key가 확보됨.

### 3.2 확장성 평가

| 항목 | 평가 | 설명 |
|------|------|------|
| Author 확장 | **PASS** | `aliases` 필드로 표기 변형 처리 (§3.1 authors.yaml) |
| Work 확장 | **PASS** | 동일 author_id 내에서 title 유사도로 그룹핑 (§4.1 단계 4) |
| Edition 확장 | **PASS** | `edition_id`로 판본 단위 구분, `source_ids` 배열로 다중 파일 지원 (§3.1 works.yaml) |
| Source File 확장 | **PASS** | `source_id`는 기존 manifest와 호환 (§3.2 참조 방향) |

### 3.3 중복 관리 위험

| 항목 | 평가 | 설명 |
|------|------|------|
| 동명이인 | **WARNING** | §4.1 단계 3 "사람 확인"으로 완화 — 자동화 금지 원칙 준수 |
| Edition 혼동 | **PASS** | `edition_id` 도입으로 Work ≠ Edition 구분 명확 (§5.1 C1 Review R4/R5 대응) |
| Source File 중복 | **PASS** | Duplicate Detection Policy(Governance v1 §5.2)와 일관 |

---

## 4. Registry Design Review

### 4.1 파일 분리 구조 적합성

**Implementation Plan §3.1:**
```
authority/
├── authors.yaml    ← Author 목록 (변경 빈도: 낮음)
└── works.yaml      ← Work + Edition + Source File (변경 빈도: 높음)
```

**판정: PASS**

변경 빈도 차이에 따른 파일 분리는 **git blame 추적성**과 **diff 가독성** 측면에서 적절함. `authors.yaml`은 신규 저자 등록 시만 변경되고, `works.yaml`은 자료 유입마다 갱신되므로 분리 시 각 파일의 commit 빈도가 자연스럽게 조절됨.

### 4.2 단방향 Reference 안전성

**Implementation Plan §3.2:**
```
authority/works.yaml (edition.source_ids)  ──→  resources/theological_sources/{domain}/source_manifest.yaml
authority/works.yaml (work.author_id)      ──→  authority/authors.yaml
```

**판정: PASS (조건부)**

단방향 참조(manifest → registry가 아님, registry → manifest)는 **이중 관리 방지** 원칙과 일치. 다만 **참조 무결성 검사**(orphan reference 탐지)가 Phase 4 검증기에 포함되어야 함 — Implementation Plan §3.2에서 명시적으로 언급함.

### 4.3 Git 관리 적합성

| 항목 | 평가 | 설명 |
|------|------|------|
| 파일 규모 | **PASS** | authors.yaml/works.yaml은 텍스트 YAML로 git 추적 적합 |
| 용량 증가 | **WARNING** | 875개 work 매핑 시 works.yaml 규모 예상 — 하지만 YAML이므로 용량 문제 경미 |
| 동시 편집 충돌 | **PASS** | `authors.yaml` 변경 빈도 낮음, `works.yaml`은 edition별 commit으로 분산 |

### 4.4 규모 확장 가능성

| 항목 | 평가 | 설명 |
|------|------|------|
| Author 수 증가 | **PASS** | `authors.yaml`에 배열 추가만 하면 됨 |
| Work/Edition 수 증가 | **PASS** | `works.yaml`에 중첩 배열 추가 — YAML 구조가 확장 가능 |
| Domain 분리 | **PASS** | `domain` 필드(§3.1 authors.yaml)로 NAE-PD/NAE-MODERN 구분 가능 |

---

## 5. Corpus Mapping Pipeline Review

### 5.1 7단계 파이프라인 적합성

**Implementation Plan §4.1:**
```
1. Source 수집 → 2. Author 정규화 → 3. 사람 확인 → 4. Work 그룹핑
   → 5. 사람 확인 → 6. Edition 분리 → 7. 검증
```

**판정: PASS (조건부)**

자동화(2/6단계 후보 생성) + 사람 확인(3/5단계)의 혼합 접근이 **적절**. 다만 **875개 항목 적용 시 사람 확인 단계의 부담**이 클 것으로 예상 — 자동화 후보 생성이 정확할수록 사람 확인이 효율적이 됨.

### 5.2 자동화 위험 지점

| 단계 | 자동화 수준 | 위험 | 완화 방안 |
|------|-------------|------|-----------|
| 1. Source 수집 | **FULL 자동** | 낮음 — manifest entry 추출만 | **PASS** |
| 2. Author 정규화 | **HALF 자동** (후보 생성) | 중간 — 동명이인 오탐 | **단계 3 사람 확인** | **PASS** |
| 3. 사람 확인 | **수동** | 낮음 — 검토만 | **PASS** |
| 4. Work 그룹핑 | **HALF 자동** (후보 생성) | 중간 — 유사 저작 오그룹핑 | **단계 5 사람 확인** | **PASS** |
| 5. 사람 확인 | **수동** | 낮음 — 검토만 | **PASS** |
| 6. Edition 분리 | **HALF 자동** (후보 생성) | 낮음 — 연도/판본 표기 명확 | **PASS** |
| 7. 검증 | **FULL 자동** | 낮음 — 참조 무결성 검사 | **PASS** |

### 5.3 Human Review 필요 지점

| 지점 | 설명 | Implementation Plan 대응 |
|------|------|--------------------------|
| §4.1 단계 3 | 동명이인 오탐 확인 | "그룹핑 결과를 사람이 검토" 명시 | **PASS** |
| §4.1 단계 5 | 동일 저작 오그룹핑 확인 | "사람 확인 → works.yaml에 work_id 등재" 명시 | **PASS** |
| §4.2 우선순위 1 | 파일럿(low volume)으로 절차 검증 | "church_order, 2 work" — 검증 비용 최소 | **PASS** |

---

## 6. Migration Review

### 6.1 Rollback 가능성

**Implementation Plan §6:**

| Step | Rollback 방법 | 위험도 | 평가 |
|------|---------------|--------|------|
| 1 | `copyright_status` 필드만 제거 — `license` 원본 필드 손실 없음 | **낮음** | **PASS** |
| 2 | `modern/{category}/source_manifest.yaml` 삭제 — NAE-PD 영향 없음 | **낮음** | **PASS** |
| 3 | `authority/` 디렉토리 전체 삭제 — manifest 참조만 당하는 쪽 | **낮음** | **PASS** |
| 4 | `source_validator.py` git revert — v1.2 검증 경로 별도 유지 | **낮음** | **PASS** |

**판정: PASS**

모든 Step이 **물리적 분리**(신규 파일/디렉토리) 기반으로 rollback이 안전함. RAW 파일이 어느 Step에도 관여하지 않으므로 데이터 손실 위험 없음(§6.3 명시).

### 6.2 기존 데이터 보호

| 항목 | 평가 | 설명 |
|------|------|------|
| v1.2 manifest entry | **PASS** | 재작성 금지, 신규 파생 필드만 추가 (§7.1 원칙 #2) |
| RAW 원문 | **PASS** | 어떤 단계에서도 이동/수정 금지 (§7.1 원칙 #1) |
| git history | **PASS** | 각 Step 독립 커밋 — 특정 Step만 revert 가능 (§6.3) |

### 6.3 단계별 Migration 안전성

**Implementation Plan §5:**

| Step | 전제조건 | 병렬 가능 | 안전성 | 평가 |
|------|----------|-----------|--------|------|
| 1. v1.2에 `copyright_status` 추가 | 없음 | Step 2와 병렬 | **높음** | **PASS** |
| 2. Modern 신규 등록 v2.0.0 적용 | §1/§2 완료 | Step 1과 병렬 | **높음** | **PASS** |
| 3. NAE-PD 소급 부여 | §3/§4 완료, 파일럿 통과 | Step 1 이후 선행 필요 | **중간** | **WARNING** (§6.3 참조) |
| 4. validator 확장 | Step 1~3 안정화 | 마지막에 실행 | **높음** | **PASS** |

---

## 7. Pilot Implementation Review

### 7.1 Pilot 규모 적합성

**Implementation Plan §4.2 우선순위 1:**
```
church_order/
├── Dagg
└── Hiscox
```

**판정: PASS**

2개 work의 소규모 카테고리는 **파일럿으로 적절**. 검증 비용이 최소이며 절차 검증 가능. 다만 **875개 전체 적용 시의 확장성**은 이 파일럿만으로 검증 불충분 — 우선순위 2(다권본 저작)에서 Edition/Work 구분 로직 검증 필요.

### 7.2 전체 Pipeline 검증 가능성

| 항목 | 파일럿으로 검증 가능 여부 | 설명 |
|------|--------------------------|------|
| Directory 구조 | **YES** | §1 생성 순서 검증 |
| Schema v2.0.0 | **PARTIAL** | church_order는 NAE-PD이므로 v2.0.0 신규 적용 아님 — 소급 매핑만 |
| Authority Registry | **YES** | authors.yaml/works.yaml 생성 + 참조 검증 |
| Mapping Pipeline | **YES** | 7단계 파이프라인 전체 절차 검증 |
| Migration Step 3 | **YES** | 소급 부여 절차 검증 |
| Rollback | **PARTIAL** | §6 방법론만 검증 — 실제 rollback 테스트는 별도 |

### 7.3 이후 확장 가능성

| 항목 | 평가 | 설명 |
|------|------|------|
| church_order → 다권본 | **PASS** | 우선순위 2에서 Fuller 8권, Cathcart 2권 등 |
| 다권본 → 단권 대다수 | **PASS** | 표준 절차 반복 적용 |
| 단권 → early_baptist_collection | **WARNING** (§8 참조) | 규모 1,416파일/34GB — 별도 sub-plan 필요 |

---

## 8. TSU Pipeline Impact Review

### 8.1 TSU Metadata 필드 적합성

**Governance v1 §6 요구 필드:**
```yaml
source_id: string
author_id: string
work_id: string
category: string
publication_year: integer
source_type: licensed | purchased | personal | reference
copyright_status: public_domain | copyrighted | licensed | unknown
citation_policy: string
tsu_access: full | restricted | citation_only
```

**Implementation Plan 호환성:**

| 필드 | Implementation Plan 대응 | 충돌 |
|------|--------------------------|------|
| `source_id` | §3.2 works.yaml의 `source_ids` 배열과 호환 | **PASS** |
| `author_id` | §3.1 authors.yaml의 `author_id`와 일관 | **PASS** |
| `work_id` | §3.1 works.yaml의 `work_id`와 일관 | **PASS** |
| `edition_id` | §3.1 works.yaml의 `edition_id` — TSU 필드에는 없음(Registry 내부만) | **PASS** (TSU 외부 필드이므로 문제 없음) |
| `copyright_status` | Governance v1 §4.1 값 체계와 일관 | **PASS** |
| `tsu_access` | Governance v1 §6 조합 표와 일관 | **PASS** |

### 8.2 TSU Schema 충돌 여부

**판정: PASS**

Implementation Plan이 제안하는 Authority Model(Author/Work/Edition/Source File)은 TSU Schema와 **충돌하지 않음**. `edition_id`는 Registry 내부 식별자일 뿐 TSU에 전달되지 않으므로 TSU 필드 증가 없음.

### 8.3 Retrieval 영향 여부

**판정: WARNING (non-blocking)**

Implementation Plan은 Retrieval Engine 변경을 포함하지 않음. 이는 **새로운 기능 추가**이지 기존 구조와의 충돌이 아님. 다만 ADR-014 §Metadata Impact에서 제안하는 Source weighting/Domain filter/Authority ranking은 별도 구현 필요.

### 8.4 추가 ADR 필요 여부

| 항목 | 필요성 | 설명 |
|------|--------|------|
| Authority Model ADR | **불필요** | 이미 ADR-015에 포함 |
| Metadata Schema v2.0.0 ADR | **권고** | schema_version 2.0.0 구조 변경은 별도 ADR로 기록 권장 |
| TSU Dataset Isolation ADR | **불필요** | 이미 ADR-015 §3.6-3.7에 포함 |

---

## 9. Risk Assessment

### 9.1 Implementation Readiness Assessment Table

| 항목 | PASS/WARNING/BLOCKER | 설명 |
|------|----------------------|------|
| Architecture Compatibility | **PASS** | RAW 불변, Directory 분리, Registry 위치 모두 기존 구조와 호환 |
| Authority Model | **PASS** | 4단계 Entity 모델 적절, edition_id 도입으로 Work/Edition 구분 명확 |
| Registry Design | **PASS** | 파일 분리(변경 빈도 기반), 단방향 참조, git 관리 적합 |
| Migration Safety | **WARNING** | Step 3 소급 부여는 파일럿 검증 후 진행 권장 (§6.3) |
| Pilot Strategy | **PASS** | church_order 2 work 파일럿 적절, 우선순위 명확 |
| TSU Compatibility | **PASS** | TSU 필드 증가 없음, edition_id는 Registry 내부만 |
| Retrieval Impact | **WARNING** | Source weighting/Domain filter/Authority ranking 미구현 (non-blocking) |

### 9.2 Risk Summary Table

| # | 영역 | 심각도 | 설명 | 권고 |
|---|------|--------|------|------|
| R1 | Migration Step 3 | **WARNING** | 소급 부여는 파일럿 검증 후 진행 | 파일럀(Priority 1) 통과 확인 후 진행 |
| R2 | Retrieval Enhancement | **WARNING** | Source weighting/Domain filter/Authority ranking 미구현 | TSU Pipeline 후 진행 (non-blocking) |
| R3 | Schema v2.0.0 ADR | **LOW** | 구조 변경 별도 ADR 기록 권장 | 향후 schema_version 3.0.0 발생 시 대비 |

---

## 10. Required Changes

### Priority 1 (필수)

| # | 항목 | 설명 |
|---|------|------|
| 1 | 파일럿 통과 확인 | church_order(Dagg/Hiscox) 매핑 완료 전, 전체 875개 소급 부여 보류 |

### Priority 2 (권고)

| # | 항목 | 설명 |
|---|------|------|
| 2 | Schema v2.0.0 ADR 작성 | 구조 변경 기록 — 향후 버전 관리 명확화 |
| 3 | Rollback 실제 테스트 | §6 방법론만 문서화 — 실제 rollback 시나리오 검증 권장 |

### Priority 3 (TSU Pipeline 후)

| # | 항목 | 설명 |
|---|------|------|
| 4 | Source weighting 구현 | ADR-014 §Metadata Impact |
| 5 | Domain filter 구현 | ADR-014 §Storage Architecture |
| 6 | Authority ranking 구현 | ADR-015 §Authority Model |

---

## 11. Final Recommendation

### 판정: **APPROVED WITH CONDITIONS**

### 조건부 승인 기준

| 조건 | 상태 |
|------|------|
| Architecture Compatibility | **PASS** — 설계 문서가 현재 아키텍처와 호환 |
| Authority Model | **PASS** — 4단계 Entity 모델 적절, edition_id 도입으로 명확화 |
| Registry Design | **PASS** — 파일 분리, 단방향 참조, git 관리 모두 적합 |
| Migration Safety | **CONDITIONAL** — 파일럿 통과 확인 후 전체 소급 부여 진행 |
| Pilot Strategy | **PASS** — church_order 2 work 파일럿 적절 |
| TSU Compatibility | **PASS** — TSU 필드 증가 없음, 충돌 없음 |
| Retrieval Impact | **WARNING (non-blocking)** — 코드 변경 필요 (TSU Pipeline 후) |

### 구현 단계 진입 조건

1. **파일럿 매핑 완료:** church_order(Dagg/Hiscox) 2 work에 대한 7단계 파이프라인 절차 검증 통과
2. **참조 무결성 검사 통과:** 모든 `source_ids`가 실제 manifest에 존재하는지 확인
3. **Rollback 시나리오 확인:** §6 방법론이 실제로 작동하는지 확인 (권고)

---

## Appendix A: Reviewed Document Inventory

| 문서 | 경로 | git 추적 | 상태 |
|------|------|----------|------|
| Implementation Plan | docs/NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md | 예 | 검토 대상 |
| Governance v1 | docs/NAE_METADATA_GOVERNANCE_v1.md | 예 | 근거 문서 |
| Corpus Ingestion Std | docs/NAE_CORPUS_INGESTION_STANDARD_v1.md | 예 | 근거 문서 |
| ADR-014 | docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md | 예 | 근거 문서 |
| ADR-015 | docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md | 예 | 근거 문서 |
| Data Architecture | docs/NAE_DATA_ARCHITECTURE.md | 예 | 근거 문서 |
| Modern Corpus Arch | docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | 예 | 근거 문서 |

---

**Review Complete. 2026-08-02.**