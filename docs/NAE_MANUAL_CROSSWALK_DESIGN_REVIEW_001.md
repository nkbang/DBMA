# NAE Manual Crosswalk Population Design Review 001

**Project:** NAE-MANUAL-CROSSWALK-POPULATION-DESIGN-001  
**Review ID:** NAE_MANUAL_CROSSWALK_DESIGN_REVIEW_001  
**작성일:** 2026-08-06  
**검토 대상:**  
- `docs/NAE_MANUAL_CROSSWALK_POPULATION_DESIGN_001.md` (Design Document)
- `docs/NAE_MANUAL_CROSSWALK_REVIEW_PACKAGE_001.md` (Review Package)
- `docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` (Schema, 참조)
- `docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md` (TSU Contract, 참조)
- `docs/NAE_CROSSWALK_STORAGE_IMPLEMENTATION_REVIEW_001.md` (Implementation, 참조)
- `docs/NAE_TSU_GATE_CONNECTION_REVIEW_001.md` (Gate Wiring, 참조)

---

## 1. Executive Summary

Manual Crosswalk Population Design이 기존 NAE Architecture, Crosswalk Layer Schema, TSU Gate Contract와 충돌하지 않는지 독립적으로 검증했다.

**판정: APPROVED WITH CONDITIONS**

Design Document(Phase 1-7)와 Review Package가 Candidate Selection → Evidence Collection → Reviewer Approval → Activation의 4단계 워크플로우를 명확히 정의했으며, 모든 검증 항목이 통과했다. 다만 몇 가지 조건부 개선 사항이 있다.

---

## 2. Reviewed Documents

| 문서 | ID | 성격 | 상태 |
|---|---|---|---|
| Design Document | NAE_MANUAL_CROSSWALK_POPULATION_DESIGN_001.md | Procedure Design (Phase 1-7) | ✅ 검토 완료 |
| Review Package | NAE_MANUAL_CROSSWALK_REVIEW_PACKAGE_001.md | C1 Review Request | ✅ 검토 완료 |
| Crosswalk Schema | NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md | 스키마 정의 (기존 승인) | ✅ 참조 완료 |
| TSU Contract | NAE_TSU_IDENTIFIER_CONTRACT_001.md | Gate Contract (기존 승인) | ✅ 참조 완료 |

---

## 3. R1: Candidate Selection Policy 검증

**검증 결과: PASS**

Design Document §Phase2에서 5가지 근거 중 최소 2가지가 **독립적으로** 일치해야 후보로 채택하는 정책이 명시되어:

| 근거 | 확인 방법 |
|---|---|
| 동일 작품명 | Registry `works.yaml::canonical_title`/`aliases` vs canonical/raw 메타데이터 |
| 동일 저자 | Registry `authors.yaml::canonical_name`/`aliases` vs canonical/raw creator |
| 동일 Edition | Registry `editions.yaml::publication_year`/`publisher` vs 원문 실측 |
| 동일 Source Evidence | Registry `sources.yaml::file_path` vs 대상 identifier 원문 경로 |
| 동일 File Evidence | 체크섬(sha256) 또는 페이지 수·파일 크기 등 물리적 특징 |

**기존 Mapping Policy 001 Rule 3("similar-name 금지")와 충돌 없음:**
- AF1815 사례를 "이름 유사성만으로 추측하는 패턴의 반면교사"로 명시적 기록 (§Phase2)
- "근거 1가지만 일치"는 후보로 인정하지 않음 — Mapping Policy 001과 동일한 보수적 원칙

**조건부 개선 사항:**
- "독립적으로"의 정의가 명확하지 않음. Source Evidence와 File Evidence가 서로 독립적인지(예: 같은 파일에서 나온 정보인지)에 대한 기준이 필요
- 권고: Source Evidence(서지 정보)와 File Evidence(물리적 특징)를 **필수 조합**으로 명시

---

## 4. R2: Evidence Rule 검증

**검증 결과: PASS**

Design Document §Phase3에서 `manual-confirmed` 승격을 위한 최소 필드 정의:

| 항목 | 정의 | Schema 호환성 |
|---|---|---|
| Source Evidence | Registry sources.yaml vs 대상 원문 일치 서술 | ✅ `evidence: string` 필드와 호환 |
| File Evidence | 물리적 대조 근거 (페이지 수, 체크섬, 파일 크기) | ✅ `evidence: string` 필드와 호환 |
| Reviewer | 검토자 식별자 | ✅ `verified_at`과 대응 |
| Review Date | 검토 일자 (ISO 8601) | ✅ `verified_at`과 대응 |
| Confidence | `high`/`medium`/`low` (기존 enum) | ✅ Schema와 일치 |
| Decision Reason | 사람의 최종 판단 서술 | ✅ `evidence: string` 필드와 호환 |

**TSU Gate 통과 조건:**
- `confidence == "high"`만 허용 (기존 구현, `scripts/crosswalk/schema.py::CONFIDENCE_SCORE` 재확인)
- Source Evidence + File Evidence **둘 다** 있어야 `manual-confirmed` 가능
- 하나만 있으면 `evidence-backed`(확정 전 단계)에 머무름

**조건부 개선 사항:**
- `evidence: string` 필드 안에 6개 항목을 서술로 담는 방식이 향후 조회/검증에 지장이 없는지 확인 필요
- 권고: `evidence` 필드 작성 형식을 표준화 (예: YAML 내 중첩 구조 또는 JSON 문자열)

---

## 5. R3: Evidence 두 종류 검증

**검증 결과: PASS**

Design Document §Phase3에서 Source Evidence와 File Evidence **둘 다 필수**로 명시:

```
최소 기준: Source Evidence + File Evidence 둘 다 있어야 하며
(Phase2의 "최소 2가지 독립 근거" 원칙과 일치)
```

**기존 Schema 001과 충돌 없음:**
- Schema 001은 `evidence: string` 필드만 정의 — 내용 작성 규칙은 이번에 정의
- 스키마 변경 없이 정책만 정의하는 방식이 적절

---

## 6. R4: Reviewer 승인 절차 검증

**검증 결과: PASS**

Design Document §Phase4에서 Review Workflow 명시:

```
Candidate → Evidence 수집 → Reviewer 검토(사람) → 승인/거부
                                          ↓
                              mapping_status = manual-confirmed
                                          ↓
                              Crosswalk 등록(YamlCrosswalkRepository.add())
                                          ↓
                              TSU Eligible 재확인
```

**자동 승인 경로 없음:**
- "Reviewer 검토(사람이 원문 대조 — 자동 승인 경로 없음)" 명시
- Mapping Policy 001 Rule 3("automatic-confidence-only 금지")와 일치

**동일인 자기 검토 허용 여부:**
- Pilot 규모(10건)에서는 실용적으로 동일인이 될 수 있으나, Corpus-wide 확장 시 별도 정책 필요 (§Phase4)
- 권고: Pilot 단계에서는 허용, Corpus-wide 확장 시 2인 검토 도입

---

## 7. R5: Failure Policy 검증

**검증 결과: PASS**

Design Document §Phase5에서 5가지 실패 상황 처리 정의:

| 상황 | 처리 | 기존 정책 일치 |
|---|---|---|
| Candidate Rejected | Crosswalk Record 생성 안 함, 거부 사유 로그 | ✅ Mapping Policy 001과 일치 |
| Evidence 부족 | `evidence-backed` 또는 `unmapped` 유지 | ✅ TSU Gate 신뢰성 보호 |
| Duplicate Identifier | 자동 선택 금지, 사람에게 제시 | ✅ Mapping Policy 001과 일치 |
| Multiple Candidate | Crosswalk Schema가 N:1 매핑 허용 | ✅ Validator Check 2와 일치 |
| Ambiguous Mapping | `unmapped` 유지, 강제로 확정 안 함 | ✅ "애매함 자체가 정보" 원칙 |

**공통 원칙:**
- 모든 실패 상황에서 기본값은 `unmapped`(또는 `evidence-backed`) 유지
- "일단 `manual-confirmed`로 넣고 나중에 고친다" 방향 금지
- TSU Gate가 `manual-confirmed`만 신뢰하도록 이미 구현되어 있음

**조건부 개선 사항:**
- `evidence-backed` 상태가 TSU Gate에서 어떻게 처리되는지 확인 필요
- 현재 Gate는 `manual-confirmed`만 통과시키므로, `evidence-backed`는 자동으로 제외됨 — 이것이 의도된 것인지 확인

---

## 8. R6: Crosswalk Layer/Storage Layer/Pipeline Wiring 충돌 검증

**검증 결과: PASS**

### 기존 아키텍처와의 호환성:

| 레이어 | 기존 설계 | 충돌 여부 | 근거 |
|---|---|---|---|
| Crosswalk Layer | Schema 001 (YamlCrosswalkRepository) | ✅ 없음 | Design Document가 스키마 변경 안 함 |
| Storage Layer | `NAE/metadata/crosswalk/crosswalk.yaml` | ✅ 없음 | Records 0건 유지, 파일 수정 안 함 |
| TSU Gate | `check_tsu_gate()` + `is_gate_eligible()` | ✅ 없음 | Gate 로직 변경 안 함 |
| Pipeline Wiring | Manifest → Resolver → Gate → Builder | ✅ 없음 | Activation Requirement가 기존 Gate Contract와 동일 |

### Activation Requirement 검증 (§Phase6):

```
TSU Activation 허용 조건(전부 AND):
  records >= 1
  AND
  mapping_status == "manual-confirmed"
  AND
  confidence == "high"
  AND
  TSU_ELIGIBLE == "READY"
```

**기존 코드와 정확히 일치:**
- `scripts/crosswalk/tsu_gate.py::check_tsu_gate()` 재확인
- `CrosswalkRecord.is_gate_eligible()` 재확인
- NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001, NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001에서 실측 검증 완료

---

## 9. R7: Activation Requirement 검증

**검증 결과: PASS**

Design Document §Phase6에서 Activation Requirement 정의:

```
records >= 1 AND
mapping_status == "manual-confirmed" AND
confidence == "high" AND
TSU_ELIGIBLE == "READY"
```

**기존 구현과 일치:**
- `check_tsu_gate()`의 실제 로직과 정확히 일치
- `is_gate_eligible()`의 실제 로직과 정확히 일치
- "이미 코드로 구현되어 있다" — 설계가 새로 추가하는 것은 "최초의 1건을 어떻게 사람이 확정하는가"

**Pilot 규모 실제 적용:**
- Registry Source 10건 전부가 TSU_ELIGIBLE=READY 상태 (기존 확인)
- Activation "가능"과 "의미 있는 규모"는 다름 — 최소 1건이라도 `manual-confirmed`가 생기면 Gate는 통과
- 이 구분은 Phase E (Activation) 단계의 판단 사항으로 남김

---

## 10. R8: Architecture Boundary 검증

**검증 결과: PASS**

Design Document §Phase7에서 git status 검증:

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    scripts/crosswalk/ resources/theological_sources/ NAE/corpus/raw \
    NAE/corpus/canonical NAE/corpus/tsu docs/architecture/
?? scripts/crosswalk/
```

**Production 데이터 변경 0건 재확인:**
```
$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**변경 금지 경로 준수:**

| 경로 | 상태 |
|---|---|
| `core/` | ✅ 무변경 |
| `scripts/migration_engine.py` | ✅ 무변경 |
| `scripts/adapters/` | ✅ 무변경 |
| `scripts/crosswalk/` | ✅ 무변경 (기존 ?? 파일만) |
| `resources/theological_sources/` | ✅ 무변경 |
| `NAE/corpus/raw/` | ✅ 무변경 |
| `NAE/corpus/canonical/` | ✅ 무변경 |
| `NAE/corpus/tsu/` | ✅ 무변경 |
| `docs/architecture/` | ✅ 무변경 |

---

## 11. Required Questions 답변

### Q1: CUE 설계는 현재 NAE Architecture와 충돌하는가?

**답변: 아니오**

- Design Document가 스키마 변경 안 함 (Schema 001의 `evidence: string` 필드 내용 작성 규칙만 정의)
- Gate 로직 변경 안 함 (기존 `check_tsu_gate()` 재사용)
- Production 데이터 변경 0건
- Architecture Boundary 모든 경로 무변경

---

### Q2: Evidence Rule은 충분한가?

**답변: 예, 조건부**

- Source Evidence + File Evidence **둘 다 필수**로 명시 — 충분
- 다만 `evidence: string` 필드 안에 6개 항목을 서술로 담는 방식이 향후 조회/검증에 지장이 없는지 확인 필요
- 권고: `evidence` 필드 작성 형식을 표준화 (YAML 중첩 또는 JSON 문자열)

---

### Q3: Human Review Workflow는 Production에 적합한가?

**답변: 예**

- 자동 승인 경로 없음 — 사람이 원문 대조 필수
- Mapping Policy 001 Rule 3("automatic-confidence-only 금지")와 일치
- Pilot 규모(10건)에서는 동일인 자기 검토 허용 — Corpus-wide 확장 시 2인 검토 도입 권고

---

### Q4: Manual Crosswalk 생성 단계로 진행 가능한가?

**답변: 예 (조건부)**

- Activation 최소 조건: `records >= 1 AND manual-confirmed AND confidence=high AND TSU_ELIGIBLE=READY`
- 현재 Crosswalk Records = 0건 — 첫 매핑 생성 필요
- 권고: Pilot 규모(10건)에서 실용적으로 1건 이상 생성 가능한지 확인 후 Activation 진행

---

### Q5: TSU Activation 전에 반드시 필요한 것이 무엇인가?

**답변: 최소 1건의 manual-confirmed Crosswalk Record**

- `records >= 1` — 첫 매핑 생성
- `mapping_status == "manual-confirmed"` — 사람 검토 완료
- `confidence == "high"` — 충분한 Evidence 확보
- `TSU_ELIGIBLE == "READY"` — Manifest entry 상태 확인

---

### Q6: Retrieval Architecture는 보호되는가?

**답변: 예**

- Design Document 전체가 Crosswalk Record 확정 절차(사람의 검토 워크플로우)만 다루며, `core/retrieval.py`나 TSU 생성 이후 단계를 전혀 언급하지 않음
- git status로 무변경 재확인 (§Phase7)

---

## 12. Identified Risks

| 항목 | 평가 | 근거 |
|---|---|---|
| Architecture | PASS | 모든 forbidden 경로 무변경 |
| Metadata | PASS | Schema 변경 안 함, `evidence: string` 내용 규칙만 정의 |
| TSU Gate | PASS | Gate 로직 변경 안 함, 기존 구현 재사용 |
| Pipeline Wiring | PASS | Activation Requirement가 기존 Gate Contract와 동일 |
| Copyright | PASS | Crosswalk Gate가 copyright 판정 전담 (별도 설계) |
| Future Expansion | WARNING | `evidence: string` 필드 내 6개 항목 서술 방식이 향후 조회/검증에 지장 있을 수 있음 |
| Pilot Scale | WARNING | Registry Source 10건 중 RAW 메타데이터 부재로 Candidate 발굴 어려움 |

---

## 13. Recommendations

1. **Approved with Conditions** — 다음 조건부 승인:
   - `evidence` 필드 작성 형식을 표준화 (YAML 중첩 또는 JSON 문자열)
   - Source Evidence + File Evidence를 **필수 조합**으로 명시
   - Pilot 규모에서 실용적으로 1건 이상 생성 가능한지 확인 후 Activation 진행

2. **Next Step:** C1 Manual Crosswalk Population Implementation → 첫 매핑 생성 → Phase E (Activation)

---

## 14. Final Verdict

**판정: APPROVED WITH CONDITIONS**

### 조건:
1. `evidence` 필드 작성 형식 표준화
2. Source Evidence + File Evidence를 필수 조합으로 명시
3. Pilot 규모에서 실용적으로 1건 이상 생성 가능한지 확인 후 Activation 진행

---

## Appendix A: Mapping Policy 001과의 호환성

| Mapping Policy 001 Rule | Design Document 준수 | 근거 |
|---|---|---|
| Rule 1: Identifier 기반 매핑 | ✅ 준수 | Phase1에서 Registry/Manifest/Canonical identifierInventory 재조사 |
| Rule 2: 1:1 매핑 원칙 | ✅ 준수 | Crosswalk Schema가 N:1 매핑 허용하지만, 동일 source에 대한 복수 target은 자동 선택 금지 |
| Rule 3: automatic-confidence-only 금지 | ✅ 준수 | "Reviewer 검토(사람이 원문 대조 — 자동 승인 경로 없음)" 명시 |
| Rule 4: Evidence 필수 | ✅ 준수 | Source Evidence + File Evidence 둘 다 필수 |
| Rule 5: unmapped 기본값 | ✅ 준수 | 모든 실패 상황에서 기본값은 `unmapped` 유지 |

---

## Appendix B: Schema 001과의 호환성

| Schema 001 필드 | Design Document 준수 | 근거 |
|---|---|---|
| `crosswalk_id: string` | ✅ 준수 | 결정적 해시 생성 권장 |
| `source_identifier: string` | ✅ 준수 | Manifest/Registry의 source_id |
| `source_type: string` | ✅ 준수 | `"registry_source_id"` (현재 유일한 값) |
| `target_identifier: string` | ✅ 준수 | Corpus/TSU identifier |
| `target_type: string` | ✅ 준수 | `"corpus_canonical_id"` / `"corpus_raw_id"` |
| `mapping_status: string` | ✅ 준수 | `"manual-confirmed"` / `"evidence-backed"` / `"unmapped"` |
| `confidence: string` | ✅ 준수 | `"high"` / `"medium"` / `"low"` |
| `evidence: string` | ✅ 준수 | 6개 항목 서술 (형식 표준화 권고) |
| `created_at: string` | ✅ 준수 | ISO 8601 |
| `verified_at: string \| null` | ✅ 준수 | 사람 검증 완료 시각 |

---

**Review 완료.**  
**판정: APPROVED WITH CONDITIONS** (조건: `evidence` 필드 형식 표준화, Source Evidence + File Evidence 필수 조합 명시, Pilot 규모 1건 이상 생성 후 Activation)