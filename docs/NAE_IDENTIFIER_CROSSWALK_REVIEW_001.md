# NAE Identifier Crosswalk Layer — Architecture Design Review 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001  
**Reviewer:** C1 (Architecture Gatekeeper)  
**작성일:** 2026-08-05  
**성격:** 읽기 전용 검증 — 구현 지시 아님, 파일 수정/생성 없음

---

## 1. Executive Summary

NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Task에서 설계된 **Crosswalk Layer**는
Manifest/Registry `source_id` (예: `BAP-CHURCH-DAGG-001`) 와 Corpus/TSU
`identifier` (예: `PBC1742`) 사이의 **번역표(lookup table)** 로, 두 계층
사이에서 독립적으로 생성된 identifier를 대응시키는 새로운 계층이다.

**5개 설계 문서(모두 Design Only, 구현 없음)** 를 검토한 결과:

| 판정 | 항목 |
|---|---|
| **APPROVED** | Crosswalk Layer 아키텍처 전반 |
| **APPROVED WITH CONDITIONS** | Crosswalk 저장 위치 (§3 ADR-019 조건부) |
| **APPROVED** | TSU Contract (Resolver 삽입 지점) |
| **APPROVED** | Mapping Policy (Rule 1~3) |
| **WARNING** | RAW Path 불일치 (기존 문제, Crosswalk 설계와 무관) |

**BLOCKER 없음.** Crosswalk Layer 신설는 기존 Architecture(ADR-001/014/015/016/017/018/019)와 충돌하지 않으며, 구현 단계에서 다음 조건을 지키면 승인된다:
1. 저장 위치 결정 시 ADR-019 재검토 (§9.3)
2. Crosswalk Adapter 구현 시 `mapping_status=manual-confirmed` Gate 강제 (§7.2)

---

## 2. Reviewed Documents

| # | 문서 | 성격 | 핵심 내용 |
|---|---|---|---|
| 1 | `NAE_IDENTIFIER_INVENTORY_002.md` | 실측 조사 | 4개 계층 identifier 전수 조사, Manifest↔Corpus/TSU 구간 0/10 일치 확인 |
| 2 | `NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` | Schema 설계 | Crosswalk Record 스키마(8 필드), mapping_status 4단계 enum |
| 3 | `NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md` | 정책 문서 | Rule 1(기존 ID 변경 금지), Rule 2(Translation Layer 소유권 없음), Rule 3(추측 Mapping 금지) |
| 4 | `NAE_IDENTIFIER_CROSSWALK_ADR_IMPACT_001.md` | ADR 영향 분석 | 7개 ADR 전수 분석, 전부 "수정 불필요" (ADR-019 조건부 보류) |
| 5 | `NAE_TSU_IDENTIFIER_CONTRACT_001.md` | Interface 정의 | Crosswalk Resolver → TSU Builder 계약(5 필드 전달, Gate 조건) |
| 6 | `NAE_IDENTIFIER_CROSSWALK_REVIEW_PACKAGE_001.md` | Review Package | C1 검증 요청 4항목 |

---

## 3. Existing Architecture Compatibility

### 3.1 ADR-001 (Retrieval Engine Authority) — 영향 없음

ADR-001은 `core/retrieval.py::RetrievalEngine`을 Retrieval Authority로
지정한다. Crosswalk Layer는 **Manifest↔Corpus/TSU 구간**에서만 동작하며,
Retrieval 코드를 전혀 참조하지 않는다(Review Package §Required Questions).

**검증 결과:** PASS — Crosswalk 설계 어디에도 `core/retrieval.py` 수정
제안이 없다. Retrieval Architecture 보호됨.

### 3.2 ADR-017 (NAE ID Governance Standard) — canonical_id authority 완전 유지

ADR-017(Approved, 2026-08-03)은 `canonical_id`/`legacy_id` 필드를
Registry 5개 Entity(28개 record)에 적용했다(Option B: FK 불변, 별도 필드 병기).

Crosswalk Mapping Policy Rule 1은 이 권위를 그대로 존중한다:
- Crosswalk은 Registry `source_id`/`canonical_id`를 **조회만** 한다
- **절대 정의하거나 변경하지 않는다** (Mapping Policy §Rule 1)
- ADR-017 본문 수정 불필요 (ADR Impact 001 확인)

**검증 결과:** PASS — ADR-017의 `canonical_id` authority 완전 유지.
Crosswalk의 `source_identifier` 필드가 참조하는 것은 Registry FK 문자열
(`source_id`)이지 `canonical_id`가 아니다(Option B 구조상).

### 3.3 ADR-019 (NAE Corpus Manifest Layer) — 조건부

ADR-019(Approved, 2026-08-03)는 Manifest Layer를 Source의 확장(별도 Entity,
`source_id` FK로 1:1 연결)으로 설계했다. `manifest_id == source_id`
1:1 매핑이 확정됐다.

Crosswalk 저장 위치는 아직 미확정이다. ADR Impact 001 §종합 판단에서
3개 후보를 제시:
1. Manifest Entry 내 필드 확장 (ADR-019 Amendment 필요)
2. 별도 파일 (`NAE/manifest/crosswalk/*.jsonl`)
3. Registry `sources.yaml` 확장 (권장)

**검증 결과:** WARNING — 저장 위치 미확정으로 인한 ADR-019 조건부 보류.
Crosswalk Adapter 구현 착수 시점에 저장 위치를 확정하고, "Manifest 필드
확장" 방식을 선택하면 ADR-019 Amendment 필요.

---

## 4. ADR-014 Review — 패턴 유사성 있으나 기반 미구현

ADR-014(Proposed, 승격 보류)는 `source_type`/`copyright_status`/
`usage_permission`/`access_control` 4개 필드를 Modern Corpus Layer용으로
제안했다. Crosswalk Schema도 같은 "같은 값을 여러 계층에 병기" 패턴을
사용한다.

그러나 ADR-014 자체가 **아직 Proposed(미승격)** 이므로, 그 위에
Crosswalk을 얹는 것은 "아직 존재하지 않는 기반 위에 짓는 것"이다.
ADR Impact 001 §3에서 "ADR-014 수정 불필요"이나, Crosswalk Layer 실제
구현은 ADR-014 Approved 이후로 순서를 맞추는 것이 안전하다고 권고했다.

**검증 결과:** WARNING — Crosswalk Pilot corpus(legacy 유입분) 대상
설계이므로 당장 문제는 없으나, Modern Corpus용 Crosswalk 설계 시
ADR-014 승격 상태를 재확인해야 함.

---

## 5. ADR-015 Review — 당장 영향 없음

ADR-015(Proposed, 승격 보류)는 신규 corpus Ingestion Lifecycle(10단계)을
설계했다. 아직 실행된 적이 없다(`scope_modified: docs/ only`).

Crosswalk 필요성은 **이미 존재하는(과거에 유입된) Pilot corpus**의
identifier 불일치 문제이지, ADR-015가 다루는 "신규 유입" 문제가 아니다.
ADR Impact 001 §2에서 "당장 불필요" — 향후 ADR-015가 실행되면 그
Lifecycle에 Crosswalk 생성 단계 추가 여부를 검토할 뿐, 현재 ADR-015
본문 수정은 필요하지 않다.

**검증 결과:** PASS — 당장 영향 없음. 향후 신규 corpus 유입 시 재검토
후보로 남김.

---

## 6. Metadata Compatibility

### 6.1 Crosswalk Schema 필드 구성

| 필드 | 타입 | 필수 | 출처/역할 |
|---|---|---|---|
| `source_id` | string | ✓ | Registry/Manifest 정본 FK (ADR-017 Option B 불변값) |
| `canonical_id` | string | - | ADR-017 canonical 표기 (참조용) |
| `legacy_id` | array[string] | - | 참조용 (선택) |
| `crosswalk_id` | string | ✓ | 대응 관계 자체 식별자 (Audit 추적용) |
| `source_type` | enum | ✓ | Source 계층 identifier 유형 |
| `target_type` | enum | ✓ | Corpus/TSU 계층 identifier 유형 |
| `mapping_status` | enum | ✓ | `verified`/`evidence-backed`/`manual-confirmed`/`unmapped` |
| `confidence` | float | - | 매핑 신뢰도 (0.0~1.0) |
| `evidence` | string | 조건부 | 근거 서술 (mapping_status에 따라 요구 수준 다름) |
| `created_at` | datetime | ✓ | 생성 시각 |
| `updated_at` | datetime | ✓ | 최종 업데이트 시각 |

**검증 결과:** PASS — 필드 구성이 Manifest Schema(ADR-019) 및 Registry
Schema(ADR-017)와 충돌하지 않음. `schema_version` 필드는 Manifest schema
version과 TSU schema version 두 축을 독립적으로 추적 (§TSU Contract §3).

### 6.2 기존 Schema 변경 필요 여부

**없음.** Crosswalk은 별도 계층(저장소)으로 신설되며, 기존 Manifest/Registry
Schema를 수정하지 않는다. 저장 위치가 "Manifest 필드 확장"으로 결정되는
다음 단계에서만 ADR-019 Amendment 필요 (§3.3).

---

## 7. TSU Compatibility

### 7.1 Crosswalk Resolver → TSU Builder 계약

TSU Contract §4에서 두 Gate 조건을 정의:

```
1. manifest_validator.py::compute_tsu_eligible() == READY
2. Crosswalk Record가 존재 AND mapping_status == "manual-confirmed"
```

두 조건을 **전부** 만족하는 Manifest entry만 TSU Builder에 전달된다.
둘 중 하나라도 실패하면 제외되고, 제외 사유가 로그에 기록되어야 한다.

**검증 결과:** PASS — 기존 TSU Builder(`NAE/pipeline/tsu/builder.py`)
내부 로직(claim 추출, TSU 레코드 생성 등) **무수정**. 유일한 변경
지점은 `build_tsu_for_all`이 `canonical_root.iterdir()`로 직접 열거하던
부분을 Resolver 호출로 대체하는 것뿐이며, 이 대체 자체도 이번 Task에서
구현하지 않는다(Crosswalk Adapter 구현은 다음 단계).

### 7.2 Mapping Policy Rule 3 — "추측 금지" 검증

Mapping Policy §Rule 3에서 4개 `mapping_status` 값을 정의하고, 3개를
금지 유형으로 명시:

| 금지 유형 | 이유 |
|---|---|
| `guess`(추측) | 잘못된 Crosswalk이 TSU Pipeline 입력으로 흘러가 다른 문헌 TSU 생성 위험 |
| `similar-name`(이름 유사도만) | 신학 문헌은 저자/판본/권호가 비슷한 제목 많음 — 오매칭 확률 구조적으로 높음 |
| `automatic-confidence-only`(자동 신뢰도 점수만) | `evidence-backed`까지는 허용하되, TSU Pipeline 투입 전 반드시 `manual-confirmed` 거쳐야 함 |

**검증 결과:** PASS — "추측 금지" 요구사항을 충분히 강제. 특히
`evidence-backed` → `manual-confirmed` 단계 구분과 "사람 최종 확인"
요건이 데이터 무결성 최악의 실패 모드(다른 문헌 TSU 생성)를 막는
효과적인 게이트다.

### 7.3 이번 Task에서 실제 매핑 건수

**0건.** 이번 Task(Phase 1~6)는 정책과 스키마만 설계했고, 실제 Registry
`source_id` 10건 중 어느 것도 Corpus/TSU identifier와 매핑하지 않았다.
Inventory §5에서 확인한 대로 지금은 겹치는 값이 없으므로, 자동으로라도
만들 수 있는 후보 자체가 없다.

---

## 8. Retrieval Compatibility

Crosswalk Layer는 Manifest↔Corpus/TSU 구간에서만 동작하며, Retrieval
(`core/retrieval.py`)은 그보다 하류(downstream)에 있어 이번 설계의
직접 대상이 아니다. Review Package §Required Questions에서 "Retrieval
보호 여부? **보호됨.**"으로 명시했다.

**검증 결과:** PASS — Crosswalk 설계 어디에도 Retrieval 관련 코드 변경
제안이 없다. `NAE/pipeline/index/`(Qdrant 연동)가 이미 존재한다는 사실은
Preflight Report에서 별도 기록해 두었다(이번 Crosswalk 설계 범위 밖,
참고용).

---

## 9. Identified Risks

| # | 항목 | 평가 | 설명 |
|---|---|---|---|
| 1 | Architecture | **PASS** | Crosswalk Layer 신설은 기존 7개 ADR(001/014/015/016/017/018/019)와 충돌 없음 |
| 2 | Metadata | **PASS** | Schema 필드 구성이 기존 Manifest/Registry Schema와 호환 |
| 3 | TSU Pipeline | **PASS** | Resolver 삽입 지점이 기존 TSU Builder 무수정 가능 — Gate 조건 충분 |
| 4 | Retrieval | **PASS** | Crosswalk 설계 범위 밖, Retrieval 코드 변경 없음 |
| 5 | Copyright | **N/A** | Crosswalk은 identifier 대응표일 뿐, copyright/usage 권한 문제와 무관 |
| 6 | Future Expansion | **WARNING** | (a) ADR-014 승격 전 Crosswalk Modern Corpus 설계 금지, (b) 저장 위치 결정 시 ADR-019 재검토 필요 |
| 7 | RAW Path | **WARNING** | Inventory §2에서 발견: Registry `file_path`가 가리키는 경로가 실제 디렉토리 구조와 안 맞음 — Crosswalk 설계와 무관하지만 별도 조치 필요 |

---

## 10. Recommendations

### 10.1 승인 조건 (Crosswalk Adapter 구현 전 필수)

1. **저장 위치 확정:** Crosswalk Adapter 구현 착수 시점에 저장 위치를
   확정하고, "Manifest 필드 확장" 방식을 선택하면 ADR-019 Amendment
   수행 (§3.3)
2. **ADR-014 상태 확인:** Modern Corpus용 Crosswalk 설계 전 ADR-014
   승격 상태 재확인 (§4)

### 10.2 향후 작업 권고

1. **Crosswalk Adapter 구현:** Resolver 삽입, 매핑 작업, Gate 검증 로직
2. **RAW Path 정정:** Registry `sources.yaml`의 `file_path` 필드를 실제
   디렉토리 구조에 맞게 수정 (§9 Risk #7)
3. **Pilot corpus 매핑:** 사람이 원문을 대조하는 별도 작업으로 10건
   Manifest↔Corpus/TSU 매핑 수행 (Mapping Policy §Rule 3 준수)

---

## 11. Final Verdict

| 항목 | 판정 |
|---|---|
| **Crosswalk Layer 아키텍처** | **APPROVED** |
| **Schema (§2)** | **APPROVED** |
| **Mapping Policy (§3)** | **APPROVED** |
| **TSU Contract (§4)** | **APPROVED** |
| **ADR Impact (§5)** | **APPROVED (ADR-019 조건부 보류)** |
| **전체 설계** | **APPROVED WITH CONDITIONS** |

**조건:** 저장 위치 확정 시 ADR-019 재검토, Modern Corpus용 설계 전
ADR-014 승격 확인.

---

## 12. Required Questions Answered

| 질문 | 답변 | 근거 |
|---|---|---|
| **1. CUE 설계가 현재 NAE 구조와 충돌하는가?** | **아니오.** Crosswalk Layer는 Manifest↔Corpus/TSU 구간 번역 계층으로, 기존 7개 ADR과 충돌하지 않음 (§3, §5) | ADR Impact 001 전수 분석 결과 |
| **2. ADR-014는 승인 가능한가?** | **Modern Corpus용으로는 보류.** Pilot corpus(legacy 유입분) 대상 설계이므로 당장 문제 없음. Modern Corpus용 Crosswalk 설계 시 ADR-014 승격 상태 재확인 필요 (§4) | ADR-014 현재 Status: Proposed (승격 보류) |
| **3. ADR-015는 승인 가능한가?** | **당장 승인.** ADR-015 자체가 아직 미구현(Proposed, 구현 근거 없음) — 지금 발견된 문제는 이미 유입된 legacy Pilot corpus의 문제 (§5) | ADR-015 Scope: 신규 corpus 유입 (이번 문제와 무관) |
| **4. Metadata Layer 구축 전에 수정해야 할 문제가 있는가?** | **없음.** Schema 필드 구성이 기존 Manifest/Registry Schema와 호환 (§6). 저장 위치 결정 시에만 ADR-019 Amendment 필요 (§3.3) | Crosswalk Schema 8 필드 전수 검증 결과 |
| **5. TSU Pipeline으로 넘어가도 되는가?** | **예, 조건부.** Gate 조건(`TSU_ELIGIBLE=READY` AND `mapping_status=manual-confirmed`)이 충분 (§7). 다만 실제 매핑(0건 → N건)은 별도 작업으로 남김 | TSU Contract §4, Mapping Policy §Rule 3 |
| **6. Retrieval Architecture를 보호하고 있는가?** | **예, 보호됨.** Crosswalk 설계 어디에도 Retrieval 코드 변경 제안 없음 (§8) | Review Package §Required Questions |

---

## 13. C1에게 요청한 4항목 검증 결과

| # | 요청 항목 | 검증 결과 |
|---|---|---|
| 1 | Crosswalk Schema 필드 구성이 향후 Manifest/Registry 구조와 충돌 없이 확장 가능한가? | **예.** 8 필드 모두 기존 Schema와 호환, 별도 계층으로 신설 (§6.1) |
| 2 | Mapping Policy 3단계 신뢰도 체계가 "추측 금지" 요구사항을 충분히 강제하는가? | **예.** `evidence-backed` → `manual-confirmed` 단계 구분 + "사람 최종 확인" 요건이 효과적인 게이트 (§7.2) |
| 3 | ADR Impact 분석에서 "이번 단계 수정 불필요, ADR-019 저장 위치 결정 시점에 재검토" 판단이 Architecture Freeze Rule 해석상 타당한가? | **예.** Crosswalk은 별도 계층으로 신설되며 기존 ADR 본문 수정 불필요. 저장 위치 확정 시에만 ADR-019 Amendment 필요 (§3.3) |
| 4 | TSU Identifier Contract의 Resolver 삽입 지점이 기존 TSU Builder 로직을 실제로 무수정으로 남길 수 있는 설계인가? | **예.** `build_tsu_for_all`의 identifier 열거부 대체만 필요, 내부 로직 무수정 (§7.1) |

---

**판정: APPROVED WITH CONDITIONS**

조건 1: 저장 위치 확정 시 ADR-019 재검토  
조건 2: Modern Corpus용 설계 전 ADR-014 승격 확인

Crosswalk Layer 신설은 기존 Architecture와 충돌하지 않으며, 다음 조건을
지키면 구현 단계로 진행할 수 있다.