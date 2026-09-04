# NAE Periodical Authority Review 001 (C1 독립 검증)

**Project:** NAE-PERIODICAL-AUTHORITY-PILOT-001
**Reviewer:** C1 (Independent Verification)
**Date:** 2026-08-02
**Nature:** 설계/Pilot 문서 독립 검토 — **실행 아님, 검토만**
**검토 대상 문서:**
- [`NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md`](NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md) (Design)
- [`NAE_PERIODICAL_PILOT_REPORT_001.md`](NAE_PERIODICAL_PILOT_REPORT_001.md) (Pilot Report)
- [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) (Governance 정본)
- [`ADR-016-NAE-Metadata-Authority-Model-Revision.md`](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md) (ADR)
- [`ADR-017-NAE-ID-Governance-Standard.md`](architecture/ADR-017-NAE-ID-Governance-Standard.md) (ADR)

---

## 1. Executive Summary

Baptist Missionary Magazine(1803~1907, archive.org 스캔 10개 issue)를 대상으로
현재 NAE Authority Model이 정기간행물을 표현할 수 있는지 검증했다. C1은 CUE가
작성한 Design/Pilot/Governance/ADR 문서를 독립적으로 검토하고, 기존 Architecture와
충돌 여부를 분석했다.

**판정: APPROVED WITH CONDITIONS** (조건부 승인)

---

## 2. Reviewed Documents

| # | 문서 | 성격 | C1 검증 결과 |
|---|---|---|---|
| 1 | `NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md` | Entity Model 분석, ID Governance 영향 | ✅ 일관성 있음 (§3과 §4 호환) |
| 2 | `NAE_PERIODICAL_PILOT_REPORT_001.md` | Pilot 검증 결과 (Reference Integrity 10/10 PASS) | ✅ 실측 기반, 과장 없음 |
| 3 | `NAE_METADATA_GOVERNANCE_v1.md` | Metadata Governance 정본 (schema 2.1.0) | ✅ §4 값 체계 명확 (§3/§4/§4.3 네 필드 독립성 확립) |
| 4 | `ADR-016` | Metadata Authority Model Revision (Entity 모델) | ✅ §5.1 Volume Entity 신설과 §5.2 Work:Edition 1:N 호환 |
| 5 | `ADR-017` | ID Governance Standard (canonical snake_case) | ✅ §3.4 "정기간행물 ID 확장 규칙은 이번 ADR 범위 밖" — Design 문서에서 처리한 것과 일관 |

---

## 3. Existing Architecture Compatibility

### 3.1 RAW 원칙 (NAE_DATA_ARCHITECTURE.md)

**검증 결과: 호환**

- Design §0의 실측(1803 "Massachusetts Baptist Missionary Magazine" → 1817 "New Series" → 이후 "Missionary Magazine")은 RAW immutable 원칙과 충돌하지 않음.
- Pilot Report §4에서 `resources/theological_sources/authority/pilot_periodical/`에 Registry 파일 생성했으나 **기존 Registry(`authority/*.yaml`, `authority/pilot/`)는 변경하지 않음**, RAW 파일도 이동하지 않음 — RAW 원칙 준수.

### 3.2 Retrieval Authority (ADR-001)

**검증 결과: 권한 침해 없음**

- Design/Pilot 모두 Retrieval Engine(`core/retrieval.py::RetrievalEngine`)을 변경하지 않음.
- Periodical Entity Model은 Metadata/Registry 레벨의 결정일 뿐, Retrieval Pipeline에 직접 영향을 주지 않음.
- TSU 신규 필드(`periodical_id`, `volume_id`, `issue_id` 등)는 기존 `TSU_SCHEMA_VERSION`과 독립적 — ADR-016과 동일 패턴.

### 3.3 Metadata Schema 호환성 (schema_version 2.1.0)

**검증 결과: 하위 호환**

- Governance §2.2에서 `2.0.0 → 2.1.0` Minor bump로 정정 — 기존 데이터 무효화 없음.
- 신규 필드(`volume_id`, `issue_id`, `author_type` 제안 등)는 optional 추가.
- `source_type`에 `public_archive` 값 추가 (§4.4) — 기존 4개 값 의미 변경 없음.

---

## 4. ADR-016 Review (Metadata Authority Model Revision)

### 4.1 Entity Model (Option A 채택)

**검토 결과: 적절**

- Work의 `work_type: periodical` 값 추가 — 기존 `work_type` enum(`monograph`, `multi_volume`)에 `periodical`만 추가하는 Minor 확장.
- Edition 계층 선택적 생략 — Registry Design v1이 이미 "Volume은 단권 자료에서 생략 가능한 선택 계층" 패턴을 확립했으므로, 그 패턴을 일반화한 것(정기간행물은 Edition 선택적 생략).
- Article을 Registry Entity로 만들지 않음 — RAW가 article 단위 물리 파일을 제공하지 않으므로 원칙(Registry Design v1 §2.5 "실제 파일 단위")과 일치.

### 4.2 Work:Edition = 1:N 관계 (Pilot-002 실증 대응)

**검토 결과: 적절**

- Andrew Fuller "Works in Eight Volumes" 사례에서 동일 Work 안에 서로 다른 인쇄 캠페인 2개 실측 확인 — 1:N 관계 정의 필요.
- 기존 Pilot-001(church_order, Work:Edition=1:1) 결과 무효화 없음 — 1:1은 N=1인 특수한 경우.

### 4.3 Volume Entity 신설

**검토 결과: 적절**

- 다권본(예: Fuller 8권, Baptist Encyclopedia 2권)에서 "권" 단위 표현을 위한 canonical key 필요.
- 단권 자료는 이 계층 생략 — 기존 Pilot-001 church_order 데이터 하위 호환.

---

## 5. ADR-017 Review (ID Governance Standard)

### 5.1 Canonical ID Rule

**검토 결과: 적절**

- `author_id = "{surname}_{given_name}[_{middle_initial}]"` — lowercase snake_case, ASCII, deterministic.
- 기존 Pilot-001(`dagg_john_l`, `hiscox_edward_t`)과 일치 — 마이그레이션 대상 최소화.

### 5.2 Collision Policy

**검토 결과: 적절**

- 동명이인 Author: 출생연도 1차 구분 → 숫자 suffix 2차 — Deterministic.
- 자동 병합 금지 원칙 재확인 — §1 Philosophy #3(Authority는 사람이 최종 승인)와 일관.

### 5.3 정기간행물 ID 확장 (Volume ID 3자리)

**검토 결과: 적절하게 분리 처리**

- ADR-017 §3.4에서 "정기간행물(volume+issue)의 ID 확장 규칙은 이번 ADR 범위 밖" — Design 문서(NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md §3.2)에서 처리.
- 정기간행물 한정 `v{NNN}`(3자리) 확장 — monograph용 2자리(`v{NN}`)는 ADR-017에서 유지.
- "ADR 소급 수정 금지" 관례 일관된 적용.

### 5.4 Organization Author 문제

**검토 결과: 우회적 해결, 근본 해결 필요**

- Design §3.4에서 `author_type: person | organization` 필드 신설 권고 — 이번 Pilot에서는 미신설.
- 현재 Author 필수 필드(`birth_year`/`death_year`)가 조직에는 무의미 — `null`로 두면 스키마 위반 없음으나 의미상 어색함.
- **권고**: 다음 단계에서 `author_type` 필드를 추가하거나, Organization을 위한 별도 Entity(예: `CorporateAuthor`)를 고려할 것.

---

## 6. Metadata Compatibility

### 6.1 기존 Schema 변경 없이 가능한가?

**답: 부분적으로 가능**

- `work_type: periodical` 추가 — Minor 확장, 기존 데이터 무효화 없음.
- `source_type: public_archive` 추가 — §4.4에서 이미 처리됨.
- `volume_id`/`issue_id` 추가 — optional 필드, 기존 단권 자료 영향 없음.
- **단**, `author_type` 필드는 Author 스키마 변경이 필요 — Minor bump 대상.

### 6.2 Migration 필요한가?

**답: NOT READY (§8 참고)**

- Pilot Report §8에서 명시: "NOT READY — 전체 Periodical Migration도, 전체 Corpus Migration도 착수 조건이 갖춰지지 않았다."
- 필요 선행 작업: (1) 제호 계승 관계 서지 검증(Risk #1), (2) Author `author_type` 필드 추가 결정(Risk #4), (3) Design 문서의 Option A 결정을 프로덕션 스키마에 반영.

### 6.3 Versioning 방식 적절한가?

**답: 적절**

- Governance §2.2에서 Semantic Versioning 채택 — Major/Minor/Patch 구분 명확.
- 이번 개정(필드 추가, 값 체계 정정)은 Minor bump(`2.0.0 → 2.1.0`)로 적절.

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조와 충돌 여부

**검토 결과: 충돌 없음**

- Design §6에서 제안한 신규 필드(`periodical_id`, `volume_id`, `issue_id`, `article_title`, `author_or_editor`, `publication_date`, `citation_policy`, `tsu_access`)는 기존 `TSU_SCHEMA_VERSION`과 독립적.
- `article_title`/`author_or_editor`는 신규 optional 필드 — 기존 TSU 레코드를 무효화하지 않음.

### 7.2 TSU Pipeline으로 넘어가도 되는가?

**답: NOT YET (조건부)**

- Pilot Report §8: "NOT READY" — 선행 작업 필요.
- TSU 생성은 해당 자료가 필요 필드(`edition_id` 필수, `volume_id` 조건부 필수)를 모두 갖춘 이후에만 허용(Governance §6).

---

## 8. Retrieval Compatibility

### 8.1 Source weighting / Domain filter / Authority ranking

**검토 결과: 코드 변경 없이 가능**

- Periodical Entity Model은 Metadata/Registry 레벨의 결정일 뿐, Retrieval Engine(`core/retrieval.py`)에 직접 영향을 주지 않음.
- `work_type: periodical` 값이 추가되어도 기존 Source weighting 로직은 `source_type`/`copyright_status` 등을 기준으로 하므로 충돌 없음.
- Domain filter(NAE-PD / NAE-MODERN)는 Corpus Layer 구분일 뿐, Periodical Entity Model과 직접 관련 없음.

### 8.2 Retrieval Architecture 보호

**검토 결과: 보호됨**

- Design/Pilot 모두 Retrieval Pipeline을 변경하지 않음.
- Periodical Authority Model은 Metadata/Registry 레벨에서 TSU 생성 시점의 영향만 있음.

---

## 9. Identified Risks

| # | 리스크 | 평가 | 설명 |
|---|---|---|---|
| 1 | 제호 계승 관계 미확정 | WARNING | "Massachusetts Baptist Missionary Magazine"(1803)과 "American Baptist Magazine...New Series"(1817)를 별도 periodical로 분리한 것은 volume 번호 불연속에 근거했으나, 서지학 전수 조사 결과가 아님 — 사서/전문가 검증 권고 |
| 2 | 동일 volume 내 복수 issue 미검증 | WARNING | RAW 표본이 volume당 issue 1개씩만 제공 — "같은 volume, 여러 issue" 시나리오 미검증 |
| 3 | Organization Author 스키마 미지원 | WARNING | `author_type` 필드가 아직 존재하지 않아 조직을 Author로 등록할 때 `birth_year`/`death_year`를 억지로 `null` 처리 |
| 4 | Article 단위 검증 불가 | LOW | RAW가 article 단위 파일을 제공하지 않음 — TSU 필드로만 다루는 결정이 실제 TSU 생성 시점에도 유효할지 미검증 |
| 5 | 발행 조직 계보 단순화 | LOW | 실제로는 수십 년간 조직명이 변화했을 가능성 — 이번 Pilot은 대표 조직 하나로 단순화 |
| 6 | Migration 준비도 부족 | BLOCKER | Pilot Report §8에서 명시: "NOT READY" — 선행 작업 필요 |

---

## 10. Recommendations

1. **제호 계승 관계 서지 검증 수행** (Risk #1, 중간 우선순위)
   - 사서/신학 전문가 검토를 통해 1803년 자료와 1817년 "New Series"의 계승 관계 확인.
   - 만약 계승 관계가 확인되면 2개 periodical을 1개로 병합 필요.

2. **Author `author_type` 필드 추가** (Risk #3, 중간 우선순위)
   - `author_type: person | organization` 필드를 Author 스키마에 추가.
   - 또는 Organization을 위한 별도 Entity(`CorporateAuthor`) 고려.

3. **Pilot 확장** (중간 우선순위)
   - "같은 volume, 여러 issue" 시나리오를 검증할 추가 issue 확보.
   - `issue_number` 충돌/정렬 로직 실제 검증.

4. **Design → Production 반영** (조건부)
   - Option A 결정(`work_type: periodical`, Edition 선택적 생략, Volume Entity 신설)을 `authority/works.yaml` 프로덕션 스키마에 반영.
   - 이는 별도 승인 작업이며, 이번 검토에서 자동 승인되지 않음.

5. **Migration은 선행 조건 충족 후** (BLOCKER)
   - TSU 생성은 필요 필드(`edition_id` 필수, `volume_id` 조건부 필수) 모두 갖춘 이후에만 허용.
   - 전체 Corpus Migration은 별도 Pilot과 검증 필요.

---

## 11. Final Verdict

### 판정: **APPROVED WITH CONDITIONS** (조건부 승인)

### 조건:

| # | 조건 | 우선순위 |
|---|---|---|
| 1 | 제호 계승 관계 서지 검증 | 중간 |
| 2 | Author `author_type` 필드 추가 결정 | 중간 |
| 3 | 동일 volume 내 복수 issue 시나리오 검증 | 중간 |
| 4 | Design → Production 반영 (별도 승인) | 조건부 |
| 5 | Migration 착수 전 TSU 필요 필드 모두 갖춘 자료 확인 | BLOCKER |

---

## 12. 최종 답변 (명령서 요구 6문항)

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: 충돌 없음.** Periodical Entity Model(Option A)은 기존 Authority Model(Work/Edition/Volume/Source)을 Minor 확장하는 형태이며, RAW immutable 원칙, Retrieval Authority, Metadata Schema 하위 호환성 모두 준수. Pilot Report §4에서 기존 Registry/RAW 파일 변경하지 않음 확인됨.

### Q2: ADR-016은 승인 가능한가?

**답: 승인 가능 (APPROVED).** Entity Model(Work→Edition 건너뛰기→Volume→Issue→Source), Work:Edition 1:N 관계, Volume Entity 신설 모두 기존 Architecture와 호환. Governance §5.1/§5.2/§6과 일관.

### Q3: ADR-017은 승인 가능한가?

**답: 승인 가능 (APPROVED).** Canonical ID Rule(lowercase snake_case), Collision Policy, 기존 Pilot ID 처리 모두 적절. 정기간행물 ID 확장(`v{NNN}`, `_i{NNN}`)은 Design 문서에서 별도 처리한 것과 일관.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: BLOCKER 1건, WARNING 3건.**
- **BLOCKER**: Migration 착수 전 TSU 필요 필드(`edition_id` 필수, `volume_id` 조건부 필수) 모두 갖춘 자료 확인 필요.
- **WARNING**: (1) 제호 계승 관계 서지 검증, (2) Author `author_type` 필드 추가, (3) 동일 volume 내 복수 issue 시나리오 검증.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: NOT YET (조건부).** Periodical Authority Pilot은 모델 검증까지 완료(Reference Integrity 10/10 PASS)했으나, 실제 TSU 생성은 선행 조건(제호 계승 검증, `author_type` 필드 추가, Design → Production 반영) 충족 후. TSU 생성은 해당 자료가 필요 필드를 모두 갖춘 이후에만 허용(Governance §6).

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: 보호됨.** Periodical Authority Model은 Metadata/Registry 레벨의 결정일 뿐, Retrieval Engine(`core/retrieval.py`)에 직접 영향을 주지 않음. Design/Pilot 모두 Retrieval Pipeline을 변경하지 않음. `work_type: periodical` 추가도 기존 Source weighting 로직과 충돌 없음.

---

*이 보고서는 설계/Pilot 문서 검토만 수행했으며, 파일 수정, 코드 변경, TSU 생성, Embedding 생성, Git Commit, Git Push — 전부 수행하지 않음.*