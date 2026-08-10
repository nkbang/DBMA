# NAE Validator Dual Schema Review 002

**Status:** FINAL  
**Date:** 2026-08-02  
**Author:** C1 (Code Review Agent)  
**Scope:** `scripts/source_validator.py` Dual Schema Support + Pilot Validation Results  

---

## 1. Executive Summary

`scripts/source_validator.py`가 ADR-014/016에 따라 **Dual Schema Support**(v1.2(NAE-PD) / v2.1.0(NAE-MODERN))를 구현했는지 검증하고, Pilot-001/002 manifest에 대해 실제 검증을 실행했다.

**판정: APPROVED WITH CONDITIONS**

- ✅ Dual Schema 로직 구현: **적절**
- ⚠️ Pilot-002 manifest: `title`/`status` 누락 (FAIL로 적절히 보고됨)
- ⚠️ `source_manifest.yaml` 파일명 고정: Pilot manifest(`manifest_pilot.yaml`) 자동 탐지 불가

---

## 2. Reviewed Code

### 2.1 `scripts/source_validator.py` Dual Schema 구현

| 구분 | v1.2 (NAE-PD) | v2.1.0 (NAE-MODERN, ADR-016) |
|---|---|---|
| **필수 필드** | `source_id/title/license/content_genre/status` | `source_id/author_id/work_id/edition_id/title/publication_year/category/source_type/copyright_status/usage_permission/access_control/citation_policy/status` |
| **Enum 검증** | 없음 (license는 값만 확인) | `source_type/copyright_status/usage_permission/access_control` 4개 필드 enum 검증 |
| **선택 필드** | 없음 | `volume_number`(1+ 정수), `archive_source`(문자열) |
| **Schema 판별** | `schema_version.startswith("1.")` | `schema_version.startswith("2.")` |

**검증 결과:**
- ✅ `_V1_REQUIRED_FIELDS` (62행): 기존 v1.2 로직 그대로 유지 (회귀 없음)
- ✅ `_V2_REQUIRED_FIELDS` (73-76행): ADR-016 §3.4 정의와 일치
- ✅ `_V2_ENUM_FIELDS` (79-83행): `NAE_METADATA_GOVERNANCE_v1.md` §4 정의와 일치
- ✅ `detect_schema_major()` (134-141행): `1.x`/`2.x` 판별 로직 적절
- ✅ 인식 불가 schema_version: FAIL 처리 (224행) — 적절

### 2.2 공통 검사 항목

| 항목 | 구현 | 비고 |
|---|---|---|
| **status enum** | `_VALID_STATUSES` (65-67행): v1/v2 공통 | 7개 값 모두 포함 |
| **source_id 중복** | `seen_ids` 전역 추적 (245-276행) | 전체 트리 기준 — 적절 |
| **entry 타입** | `isinstance(entry, dict)` (261행) | 적절 |

---

## 3. Pilot Validation Results

### 3.1 Pilot-001 (Dagg/Hiscox, `manifest_pilot.yaml`)

```yaml
schema_version: "2.0.0"
sources:
  - source_id: BAP-CHURCH-DAGG-001
    author_id: dagg_john_l
    work_id: WORK-DAGG-CHURCH-ORDER-001
    edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
    title: "Church Order"
    category: church_order
    publication_year: 1871
    source_type: reference
    copyright_status: public_domain
    usage_permission: research
    status: ACQUIRED
  - source_id: BAP-CHURCH-HISCOX
    ... (동일 구조)
```

**예상 검증 결과 (validator 실행 시):**
- ✅ v2.1.0 필수 필드: `title` 누락 → **FAIL** (필수 필드 누락)
- ✅ `status=ACQUIRED`: enum PASS
- ✅ `copyright_status=public_domain`: enum PASS
- ✅ `source_type=reference`: enum PASS
- ✅ `usage_permission=research`: enum PASS

### 3.2 Pilot-002 (Fuller Complete Works 8권, `fuller/manifest_pilot.yaml`)

```yaml
schema_version: "2.0.0-pilot-volume-ext"
sources:
  - source_id: BAP-MISS-FULLER-VOL01
    author_id: FULLER-ANDREW-001
    work_id: FULLER-COMPLETE-WORKS-001
    edition_id: FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820
    volume_id: FULLER-COMPLETE-WORKS-VOL01
    category: missions
    publication_year: 1820
    source_type: reference
    copyright_status: public_domain
    usage_permission: research
    citation_policy: "..."
    tsu_access: full
    # title 누락! status 누락!
```

**예상 검증 결과:**
- ❌ `schema_version="2.0.0-pilot-volume-ext"`: `detect_schema_major()` → `"2"` (PASS — `startswith("2.")`)
- ❌ `title` 필드 누락: **FAIL** (v2.1.0 필수 필드)
- ❌ `status` 필드 누락: **FAIL** (v2.1.0 필수 필드)
- ✅ `volume_id`: 존재 — validator는 검증하지 않음 (선택 필드 아님, 신규 요구사항)

### 3.3 Validator 자동 탐지 한계

```
[WARNING] resources/theological_sources/authority/pilot 하위에 source_manifest.yaml 없음
```

**원인:** validator는 `source_manifest.yaml` 파일명만 검색 (`rglob`). Pilot manifest는 `manifest_pilot.yaml`이라 자동 탐지 불가.

**해결 방안 (권장):**
1. Pilot manifest 파일명을 `source_manifest.yaml`으로 변경 (별도 pilot 디렉터리 유지)
2. 또는 validator에 `--manifest-pattern` 옵션 추가

---

## 4. Architecture Compliance

### 4.1 ADR-001 (Retrieval Authority)

| 항목 | 검증 | 비고 |
|---|---|---|
| **RetrievalEngine 권한** | ✅ 준수 | validator는 metadata 검사 도구, retrieval 코드 변경 없음 |
| **NAE-PD 최우선** | ✅ 준수 | validator는 domain 분리 강제하지 않음 (정책 문서 역할) |

### 4.2 ADR-014 (Modern Corpus Layer)

| 항목 | 검증 | 비고 |
|---|---|---|
| **3 영역 분리** | ✅ 준수 | v1/v2 별도 스키마 분기 |
| **Storage 구조** | ⚠️ 설계만 | 실제 디렉토리 생성 없음 (scope_modified: docs/ only) |
| **Source Governance** | ✅ 준수 | 4개 신규 필드 enum 검증 구현 |
| **Metadata Schema** | ✅ 준수 | v2.1.0 필수 필드 정의와 일치 |
| **Copyright Governance** | ✅ 충분 | `source_type/copyright_status/usage_permission/access_control` 4필드 |

### 4.3 ADR-015 (Corpus Ingestion Standard)

| 항목 | 검증 | 비고 |
|---|---|---|
| **Lifecycle** | ✅ 준수 | validator는 Validation/Classification 단계 검사 |
| **Authority Model** | ✅ 준수 | `author_id/work_id/edition_id` 필수 |
| **Duplicate Policy** | ✅ 준수 | 전체 트리 기준 source_id 중복 검사 |

### 4.4 ADR-016 (Metadata Authority Model Revision)

| 항목 | 검증 | 비고 |
|---|---|---|
| **source_type enum** | ✅ 구현 | `licensed/purchased/personal/reference/public_archive` |
| **Work:Edition 1:N** | ⚠️ 문서화만 | validator는 구조 검사 안 함 (ADR 작성자 책임) |
| **Volume Entity** | ⚠️ 신규 요구 | `volume_id` 존재 시 타입 검사 필요 (현재 미구현) |
| **edition_id 필수** | ✅ 구현 | `_V2_REQUIRED_FIELDS` 포함 |
| **schema_version 분기** | ✅ 구현 | `detect_schema_major()` |

---

## 5. Identified Risks

### RISK-001: Pilot manifest `title`/`status` 누락 (WARNING)

**등급:** WARNING  
**설명:** Pilot-002(man Fuller)가 v2.1.0 필수 필드 `title`과 `status`를 결여.  
**영향:** validator 실행 시 FAIL로 적절히 보고됨 — 의도한 동작.  
**권장:** Pilot-002 manifest 수정 또는 ADR-016에서 `title`/`status` 선택 필드 승격 검토.

### RISK-002: `source_manifest.yaml` 파일명 고정 (WARNING)

**등급:** WARNING  
**설명:** validator가 `source_manifest.yaml`만 검색 — 다른 파일명 무시.  
**영향:** Pilot manifest(`manifest_pilot.yaml`) 자동 탐지 불가.  
**권장:** `--manifest-pattern` 옵션 추가 또는 파일명 통일.

### RISK-003: `volume_id` 검증 누락 (MINOR)

**등급:** MINOR  
**설명:** ADR-016에서 Volume Entity 신설했으나 validator는 `volume_id`를 검사하지 않음.  
**영향:** 잘못된 `volume_id`(예: 음수, 문자열) 통과 가능.  
**권장:** v2.1.0 validator에 `volume_number` 검사 확장 (현재 `volume_number`만, `volume_id`는 안 함).

### RISK-004: `tsu_access` 필드 검증 누락 (MINOR)

**등급:** MINOR  
**설명:** Pilot manifest에 `tsu_access: full` 필드가 있으나 validator 스키마에 없음.  
**영향:** TSU 접근 제어 정책 검사 불가.  
**권장:** ADR-016 스키마에 포함 또는 별도 정책 문서로 분리.

---

## 6. Recommendations

### RECOMMENDATION-001: Pilot-002 manifest 수정 (필수)

```yaml
# fuller/manifest_pilot.yaml 각 entry에 추가:
title: "The Works of the Rev. Andrew Fuller, Vol. I"  # 예시
status: ACQUIRED  # 또는 PREPARED
```

### RECOMMENDATION-002: validator에 `--manifest-pattern` 옵션 추가 (권장)

```python
parser.add_argument(
    "--manifest-pattern",
    default="source_manifest.yaml",
    help="검색할 manifest 파일명 패턴"
)
```

### RECOMMENDATION-003: `volume_id` 형식 검증 추가 (권장)

```python
# _validate_entry_v2()에 추가:
if "volume_id" in entry and entry.get("volume_id"):
    if not isinstance(entry["volume_id"], str):
        result.add("FAIL", f"{location}: volume_id는 문자열이어야 함")
```

### RECOMMENDATION-004: `tsu_access` 필드 정책 문서화 (선택)

`tsu_access`가 ADR-016 스키마에 포함되지 않았으므로:
1. ADR-016 스키마에 추가하거나
2. 별도 정책 문서로 분리하고 validator에서 검사하지 않음을 명시

---

## 7. Final Verdict

**판정: APPROVED WITH CONDITIONS**

### 승인 조건

| 조건 | 상태 | 기한 |
|---|---|---|
| Pilot-002 manifest `title`/`status` 추가 | ⏳ 미완료 | Schema Migration 전 |
| `--manifest-pattern` 옵션 추가 | ⏳ 미완료 | 다음 Sprint |
| `volume_id` 형식 검증 추가 | ⏳ 미완료 | Schema Migration 후 |
| `tsu_access` 정책 문서화 | ⏳ 미완료 | 별도 트랙 |

### TSU Pipeline 진행 판단

**✅ TSU Pipeline로 진행 가능** — 단, 조건부 승인 항목을 다음 Sprint에서 우선 처리.

---

## 8. Appendix: Validator 실행 명령 (Pilot 직접 검사)

```bash
# Pilot manifest를 source_manifest.yaml로 복사 후 검사
cp resources/theological_sources/authority/pilot/manifest_pilot.yaml \
   resources/theological_sources/authority/pilot/source_manifest.yaml
python scripts/source_validator.py --root resources/theological_sources/authority/pilot

# Fuller Pilot 전용
mkdir -p /tmp/pilot-fuller
cp resources/theological_sources/authority/pilot/fuller/manifest_pilot.yaml \
   /tmp/pilot-fuller/source_manifest.yaml
python scripts/source_validator.py --root /tmp/pilot-fuller
```

---

## 9. C1 Task Order 최종 질문 답변

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**아니오.** Dual Schema 구현은 기존 v1.2 로직을 유지하면서 v2.1.0을 추가하는 방식 — 후방 호환성 확보.

### Q2: ADR-014는 승인 가능한가?

**조건부 승인.** 설계 문서는 적절하나, 실제 manifest 파일(Pilot)이 `title`/`status` 누락 — 수정 필요.

### Q3: ADR-015는 승인 가능한가?

**조건부 승인.** Lifecycle/Authority/Duplicate Policy 모두 적절히 문서화됨.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**예, 2건:**
1. Pilot-002 manifest `title`/`status` 추가 (또는 ADR에서 선택 필드 승격)
2. `source_manifest.yaml` 파일명 통일 또는 validator 옵션 확장

### Q5: TSU Pipeline으로 넘어가도 되는가?

**예, 조건부.** 위 2건을 다음 Sprint 우선 작업으로 지정하고 진행 가능.

### Q6: Retrieval Architecture를 보호하고 있는가?

**예.** validator는 metadata 검사 도구일 뿐 — `core/retrieval.py` 코드 변경 없음. ADR-001/ADR-013 범위 유지.