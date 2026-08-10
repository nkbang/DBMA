# NAE Crosswalk Storage Decision Review 001

**Project:** NAE-CROSSWALK-STORAGE-DECISION-REVIEW-001  
**작성일:** 2026-08-05  
**검토 성격:** Read-Only Architecture Compatibility Verification  
**판정:** APPROVED WITH CONDITIONS

---

## 1. Executive Summary

CUE가 작성한 Storage Decision 문서(`docs/NAE_CROSSWALK_STORAGE_DECISION_001.md`)에서
Option B(`NAE/metadata/crosswalk/`)를 선택한 것은 **기존 NAE Architecture와 충돌하지 않음**.

**주요 발견:**
- `NAE/corpus/metadata/`가 이미 존재하므로 `NAE/metadata/` 경로와의 계층 구분 필요
- ADR-019 Manifest Layer 책임과 Crosswalk Layer 책임 분리 명확
- ADR Amendment 불필요 — Crosswalk 필드가 Manifest Entry 필드와 겹치지 않음
- Retrieval Architecture 보호 — `core/retrieval.py`는 `NAE/` 하위 경로를 import하지 않음

---

## 2. Reviewed Documents

### 2.1 대상 문서

| 문서 | 성격 |
|---|---|
| `docs/NAE_CROSSWALK_STORAGE_DECISION_001.md` | Architecture Decision — Option B 선택 |
| `docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` | CrosswalkRecord 10개 필드 스키마 |
| `docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md` | Rule 1-3 (추측 매핑 금지, Confidence Gate, Evidence 필수) |
| `docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md` | TSU Gate 정의 |
| `docs/NAE_CROSSWALK_ADAPTER_REVIEW_001.md` | Review 001 — APPROVED WITH CONDITIONS → R7 RESOLVED |

### 2.2 ADR 참조

| ADR | 제목 | 관련성 |
|---|---|---|
| ADR-001 | Retrieval Engine Authority | Retrieval 보호 |
| ADR-014 | NAE Modern Corpus Layer | 계층 구조 분리 |
| ADR-015 | NAE Corpus Ingestion Standard | Pipeline 호환성 |
| ADR-016 | Metadata Authority Model Revision | Metadata 책임 |
| ADR-017 | ID Governance Standard | Identifier 관리 |
| ADR-018 | Periodical Authority Extension | Authority 확장 |
| ADR-019 | Corpus Manifest Layer | **가장 직접적 관련** |

---

## 3. R1. Storage Architecture Compatibility

### 검토: Option B — `NAE/metadata/crosswalk/`

**제안 구조:**
```
NAE/metadata/crosswalk/
├── crosswalk.yaml     # CrosswalkRecord 목록
└── index.json         # source_identifier -> crosswalk_id 역인덱스
```

### 기존 구조와 충돌 분석

| 항목 | 확인 결과 | 충돌 여부 |
|---|---|---|
| `NAE/corpus/metadata/` | **이미 존재** (현재 corpus manifest Pilot 산출물 위치) | ⚠️ WARNING |
| `NAE/manifest/` | **존재하지 않음** (레거시 CSV는 `NAE/corpus/manifests/`) | ✅ 없음 |
| `NAE/metadata/` | **존재하지 않음** (신규 생성 경로) | ✅ 가능 |

### 발견: `NAE/corpus/metadata/` 존재

```
NAE/corpus/metadata/   # 현재 corpus manifest Pilot 산출물 위치
```

**의미:** 
- `NAE/metadata/crosswalk/`는 `NAE/corpus/metadata/`와 **다른 계층**
- `NAE/corpus/` = Corpus (수집·정제·생성물)
- `NAE/metadata/` = Metadata Layer (메타데이터 관리·거버넌스)

**판정:** ✅ **PASS** — 계층이 다르므로 충돌 없음. 다만 문서에 이 구분 명시 권고.

---

## 4. R2. ADR-019 Compatibility

### ADR-019 Manifest Layer 책임

| 책임 영역 | 내용 |
|---|---|
| Lifecycle | `RAW Acquired → Registered → Manifest Created → Validated → TSU Eligible → TSU Generated → Indexed` |
| Authority Metadata | `manifest_id`, `source_id`, `work_id`, `edition_id`, `volume_id`, `issue_id`, `processing_status`, `tsu_access`, `schema_version` (9개 필드) |
| Source Governance | Manifest Entry = Source와 1:1, `manifest_id = source_id` |

### Crosswalk Layer 책임

| 책임 영역 | 내용 |
|---|---|
| Identifier Translation | `source_identifier → target_identifier` 매핑 |
| Mapping Evidence | 매핑 근거 기록 (`evidence` 필드) |
| Confidence | 매핑 신뢰도 (`confidence` 필드) |

### 책임 분리 평가

| 기준 | Manifest Layer | Crosswalk Layer | 분리 유지 |
|---|---|---|---|
| 데이터 성격 | 정적 서지 + 동적 처리 상태 | identifier 간 번역 | ✅ 유지 |
| Entity 관계 | Source 1:1 | Source → Corpus canonical/raw | ✅ 유지 |
| 필드 겹침 | `created_at`, `updated_at`, `verified_by` | `crosswalk_id`, `source_identifier`, `target_identifier` 등 | ✅ 없음 (별도 필드) |
| Lifecycle 영향 | Processing status 전진 | Mapping status 전진 | ✅ 독립 |

**판정:** ✅ **PASS** — 두 계층의 책임 분리가 명확히 유지됨.

---

## 5. R3. ADR Amendment Requirement

### 판정: B — 본문 수정 불필요 + Reference 추가 권고

### 근거

1. **ADR-019 본문 영향 없음:**
   - ADR-019 §3.3 Schema 필수 필드(9개): `manifest_id`, `source_id`, `work_id`, `edition_id`, `volume_id`, `issue_id`, `processing_status`, `tsu_access`, `schema_version`
   - Crosswalk 10개 필드: `crosswalk_id`, `source_identifier`, `source_type`, `target_identifier`, `target_type`, `mapping_status`, `confidence`, `evidence`, `created_at`, `verified_at`
   - **필드 겹침 없음** — Manifest Entry에 Crosswalk 필드가 포함되지 않음

2. **ADR-019 §5 Consequences와 일치:**
   > "Schema/Registry/Validator/Pilot/RAW는 이 ADR로 변경되지 않는다 — 정책·설계만 확정."
   
   Crosswalk Layer도 동일하게 "정책·설계만 확정" — 실행 단계 별도 승인 필요

3. **권고: ADR-019 References에 Crosswalk 문서 추가:**
   - `docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md`
   - `docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md`
   - `docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md`

---

## 6. R4. Manifest Extension Option 검토

### Option A: Manifest field extension

#### 검토 항목

| 항목 | 평가 |
|---|---|
| lifecycle field 침범 가능성 | ⚠️ **높음** — Manifest Entry의 `processing_status`와 Crosswalk의 `mapping_status`가 혼동 가능 |
| schema coupling 증가 | ⚠️ **높음** — Manifest Schema가 Crosswalk 의존성 추가로 복잡해짐 |
| migration complexity | ⚠️ **높음** — 기존 Manifest Pilot(10 source) 재작성 필요 |

#### Option B 대비 적합성

| 기준 | Option A | Option B | 우세 |
|---|---|---|---|
| 책임 분리 | ❌ 혼합 | ✅ 독립 | **B** |
| Schema 안정성 | ❌ 취약 | ✅ 독립 | **B** |
| Migration 비용 | ❌ 높음 | ✅ 낮음 | **B** |
| ADR 영향 | ❌ Amendment 필요 | ✅ 불필요 | **B** |

**판정:** Option B가 **명확히 우세** — Option A 비권고.

---

## 7. R5. Database Backend Option 검토

### Option C: Database Backend

#### 검토 항목

| 항목 | 평가 |
|---|---|
| 현재 NAE 규모 적합성 | ⚠️ **과잉** — Crosswalk 매핑은 현재 수천 건 수준 — YAML/JSON으로 충분 |
| 운영 복잡도 | ❌ **높음** — DB backup/recovery/migration 추가 운영 부담 |
| backup/recovery 영향 | ❌ **복합** — git 관리에서 DB 관리로 전환 일관성 손실 |

#### Option B 대비 적합성

| 기준 | Option C | Option B | 우세 |
|---|---|---|---|
| 규모 적합성 | ⚠️ 과잉 | ✅ 적정 | **B** |
| 운영 복잡도 | ❌ 높음 | ✅ 낮음 | **B** |
| git 일관성 | ❌ 손실 | ✅ 유지 | **B** |

**판정:** Option B가 **명확히 우세** — Option C는 규모 증가 시 재검토 권고.

---

## 8. R6. Legacy Path Collision 검토

### `NAE/manifest/` 레거시 directory 존재 여부

```
grep -r "NAE/manifest/" .  # 결과: 없음 (레거시 CSV는 NAE/corpus/manifests/)
```

**발견:**
- `NAE/manifest/` 디렉토리는 **존재하지 않음**
- Manifest 관련 파일은 `NAE/corpus/manifests/.gitkeep` (비어 있음)
- 실제 Manifest Pilot 산출물은 `NAE/corpus/metadata/`에 위치

### `NAE/metadata/crosswalk/` 명칭 충돌 위험

| 경로 | 존재 여부 | 충돌 |
|---|---|---|
| `NAE/metadata/` | 없음 (신규 생성) | ✅ 없음 |
| `NAE/metadata/crosswalk/` | 없음 (신규 생성) | ✅ 없음 |
| `NAE/corpus/metadata/` | **존재** | ⚠️ 문서상 구분 필요 |

**판정:** ✅ **PASS** — 실제 충돌 없음. 다만 문서에 `NAE/corpus/metadata/`와의 구분 명시 권고.

---

## 9. R7. TSU Contract Compatibility

### 현재 흐름

```
Manifest (processing_status=TSU_ELIGIBLE)
 ↓
Crosswalk Resolver (source_identifier → target_identifier)
 ↓
TSU Gate (tsu_eligible AND manual-confirmed)
 ↓
TSU Builder
```

### Storage 위치 변경이 TSU Contract에 미치는 영향

| 항목 | 평가 |
|---|---|
| Crosswalk Resolver | `scripts/crosswalk/resolver.py` — InMemory 또는 YAML 파일 읽음 |
| TSU Gate | `scripts/crosswalk/tsu_gate.py` — Interface만 제공, 호출 쪽 배선 |
| TSU Builder | `NAE/pipeline/tsu/builder.py` — **수정 없음** |

### 영향 분석

1. **Crosswalk Storage가 YAML인 경우:**
   - Resolver가 `crosswalk.yaml` 읽음 → TSU Gate에 record 전달
   - TSU Gate는 `crosswalk_record.mapping_status == MANUAL_CONFIRMED` 확인
   - **TSU Pipeline 코드 변경 없음** — Interface만 사용

2. **Crosswalk Storage가 DB인 경우 (Option C, 향후):**
   - Resolver가 DB 쿼리 → 동일 Interface 통해 record 전달
   - **동일하게 TSU Pipeline 코드 변경 없음**

**판정:** ✅ **PASS** — Storage 위치 변경이 TSU Contract를 깨뜨리지 않음.

---

## 10. R8. Retrieval Architecture Protection

### `core/retrieval.py` 의존성 확인

```bash
grep -n "^from\|^import" core/retrieval.py | grep -i "nae\|metadata\|crosswalk"
# 결과: 없음 (Storage Decision 문서 §2 근거와 일치)
```

### Retrieval Engine 보호 평가

| 항목 | 평가 |
|---|---|
| `NAE/metadata/crosswalk/` import | ❌ Retrieval이 import하지 않음 |
| `core/retrieval.py` 수정 필요 | ❌ 불필요 |
| NAE metadata layer dependency 추가 | ❌ 요구되지 않음 |

**판정:** ✅ **PASS** — Retrieval Architecture가 보호됨.

---

## 11. Required Questions Answered

### Q1. CUE Storage Decision 설계가 현재 NAE 구조와 충돌하는가?

**아니요.** Option B(`NAE/metadata/crosswalk/`)는 기존 구조와 충돌하지 않음.
- `NAE/corpus/metadata/`와 다른 계층 (corpus vs metadata layer)
- ADR-019 Manifest Entry 필드와 겹치지 않음
- Retrieval Engine 의존성 없음

### Q2. ADR-019 수정이 필요한가?

**아니요.** 본문 수정 불필요. 다만 References에 Crosswalk 문서 추가 권고.

### Q3. Option B 선택이 장기적으로 적절한가?

**예.** Option B는 8개 평가 기준 중 7개에서 최선 또는 A/C와 동률 이상.
- 유일한 약점("신규 namespace 필요")은 위험이 아닌 작업량
- ADR Amendment처럼 기존 Approved Architecture를 다시 열지 않음

### Q4. Manifest Extension 방식이 더 나은 선택인가?

**아니요.** Option A(Manifest extension)는 Option B 대비 모든 기준에서 열세.
- 책임 분리, Schema 안정성, Migration 비용, ADR 영향 모두 B가 우세

### Q5. Crosswalk Storage 구현으로 넘어가도 되는가?

**조건부: 예.** 다음 조건 충족 시:
1. `NAE/metadata/crosswalk/` 디렉토리 생성 승인
2. `crosswalk.yaml`/`index.json` 파일 생성 승인
3. `CrosswalkRepository` 구체 구현체(YAML 기반) 설계 승인

### Q6. Retrieval Architecture가 보호되는가?

**예.** Crosswalk Layer는 `scripts/crosswalk/` 패키지로 분리되어 있으며,
`core/retrieval.py`를 수정하지 않음. Storage 위치(`NAE/metadata/crosswalk/`)도
Retrieval이 import하지 않음.

---

## 12. Identified Risks

| # | 항목 | 수준 | 설명 |
|---|---|---|---|
| 1 | `NAE/corpus/metadata/`와의 명칭 혼동 | WARNING | 문서상 구분 명시 필요 |
| 2 | Storage 위치 미확정 (ADR-019) | INFO | 기존 Review 001에서 이미 확인 |
| 3 | 향후 DB 확장 시 재검토 필요 | INFO | 규모 증가 시 Option C 재평가 |

---

## 13. Recommendations

### 승인 조건

1. **`NAE/metadata/crosswalk/` 디렉토리 생성 승인** — 기존 `NAE/corpus/metadata/`와 구분
2. **`crosswalk.yaml`/`index.json` 파일 생성 승인** — YAML 직렬화 + 선택적 인덱스
3. **ADR-019 References에 Crosswalk 문서 추가 권고** — 본문 수정 불필요

### 향후 작업

4. **Storage Adapter 구현:** `YamlFileCrosswalkRepository` 설계·구현 승인 필요
5. **TSU Gate 배선:** TSU Pipeline이 `tsu_gate.py` Interface 호출하도록 배선
6. **Production 사용 전 Backup Strategy:** YAML/JSON 파일 git 관리 외 backup 전략

---

## 14. Final Verdict

```
APPROVED WITH CONDITIONS
```

### 조건

| 조건 | 수준 | 조치 |
|---|---|---|
| R1. Storage Architecture | ✅ PASS | `NAE/corpus/metadata/`와의 구분 명시 |
| R2. ADR-019 Compatibility | ✅ PASS | 책임 분리 명확 |
| R3. ADR Amendment | ✅ B (불필요) | References 추가 권고 |
| R4. Manifest Extension | ⚠️ 비권고 | Option B 우세 |
| R5. Database Backend | ⚠️ 향후 재검토 | 규모 증가 시 평가 |
| R6. Legacy Path Collision | ✅ PASS | 충돌 없음 |
| R7. TSU Contract | ✅ PASS | 영향 없음 |
| R8. Retrieval Protection | ✅ PASS | 보호됨 |

---

## 15. Reviewer Signature

**Reviewer:** Cline (Architecture Verification Agent)  
**Date:** 2026-08-05  
**Basis:** Direct file read of Storage Decision + ADR-019 + NAE directory structure verification  
**Method:** Read-Only Architecture Compatibility Verification