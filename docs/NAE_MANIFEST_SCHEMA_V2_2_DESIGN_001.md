# NAE Manifest Schema v2.2 Design 001

작성일: 2026-08-02
Project: NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 Phase 3-4
성격: **설계 문서 — Manifest 실제 생성 없음, 스키마 파일 미작성**
근거: [ADR-019](architecture/ADR-019-NAE-Corpus-Manifest-Layer.md),
[`NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md`](NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md)

---

## Phase 3. Manifest Schema 설계

### 버전 관계(중요)

Manifest Schema는 corpus manifest(`modern/source_manifest.schema.yaml`,
v2.x)와 **독립된 버전 트랙**을 갖는다 — `TSU_SCHEMA_VERSION`이
metadata `schema_version`과 독립적인 것과 동일한 원칙(ADR-016에서
이미 확립). 이번 설계로 **Manifest Schema 버전을 `1.0.0`으로 시작**
한다고 확정한다(Manifest Architecture Review-001의 Remaining Risk #2
"Manifest 자체 schema_version 값 미확정"을 이번 문서에서 해소).

### Manifest Identity

```yaml
manifest_id: string     # = source_id 그대로(ADR-019, 별도 ID 체계 없음)
source_id: string        # Registry sources.yaml FK, 1:1
schema_version: "1.0.0"  # Manifest Schema 자체의 버전(corpus manifest v2.x와 별개)
```

### Processing State

```yaml
processing_status: enum
values:
  - RAW_ACQUIRED
  - REGISTERED
  - VALIDATED
  - TSU_ELIGIBLE
  - TSU_GENERATED
  - INDEXED
```

**변경 사항(ADR-019 대비 정리)**: ADR-019 초안의 7단계
(`RAW Acquired → Registered → Manifest Created → Validated → TSU
Eligible → TSU Generated → Indexed`)에서 `MANIFEST_CREATED`를
제거했다 — Manifest Entry 자체가 존재해야 `processing_status`
필드를 가질 수 있으므로, "Manifest Entry가 생성됨"은 상태 값이
아니라 **Manifest Entry가 존재하기 시작하는 시점**(레코드 생성
자체)이다. 즉 `processing_status`의 최초값은 `RAW_ACQUIRED`이고,
Manifest Entry 레코드 존재 여부 자체가 "Manifest Created"를
암묵적으로 표현한다(중복 상태 제거, 6단계로 단순화).

### Authority Reference

```yaml
author_id: string
work_id: string
edition_id: string|null
volume_id: string|null
issue_id: string|null
```

### 조건 정의(Monograph / Periodical)

| 필드 | Monograph | Periodical |
|---|---|---|
| `edition_id` | **required** | conditional(계승 관계가 있는 경우만 참고용, 기본은 생략 — ADR-018 "Edition 계층 생략") |
| `volume_id` | optional(다권본만) | **required** |
| `issue_id` | **forbidden**(monograph에는 issue 개념 자체가 없음) | **required** |

이 표는 ADR-018의 TSU 필수 필드 예외 규칙(work_type 분기)을 Manifest
Authority Reference 필드에도 동일하게 적용한 것이다 — 새 규칙을
만들지 않고 기존 결정을 재사용(GOVERNANCE §6/ADR-018 §3.4와 일관).

**`issue_id` forbidden의 의미**: 다른 필드(`volume_id` 등)는 "값이
없으면 null"이지만, monograph의 `issue_id`는 **값이 있으면 오류**로
취급한다 — monograph가 issue를 가지면 데이터 모델링 오류(Work
분류가 잘못됐거나 `work_type`이 잘못 지정된 경우)이기 때문. 이는
Manifest Validator(§Phase5)의 검증 규칙 후보가 된다.

---

## Phase 4. Lifecycle 정합성 해결

### 결정: **B — ADR-015(Ingestion Lifecycle)과 ADR-019(Manifest
Lifecycle)는 별개 층위, 명시적 대응 관계로 연결**

**A(ADR-019 ⊂ ADR-015) 기각 사유**: ADR-015의 10단계(Registration→
Validation→Classification→Metadata Creation→Quality Check→Clean
Processing→TSU→Embedding→Index Update, `NAE_CORPUS_INGESTION_STANDARD_v1.md`
Phase 2)는 **한 자료가 처음 시스템에 들어올 때 사람/파이프라인이
수행하는 절차(procedure)**다. ADR-019의 6단계(§Phase3)는 **한 자료의
현재 상태를 나타내는 상태값(state)**이다 — 절차와 상태는 같은
계층에 속하지 않으므로 "부분집합" 관계로 표현하면 오히려 왜곡된다
(절차의 각 단계가 상태값 하나에 깔끔하게 대응하지 않을 수 있음 —
예: "Quality Check"는 절차상 한 단계이지만 상태값으로는 여러 번
반복될 수 있는 활동).

**C(완전 통합) 기각 사유**: 두 문서(ADR-015/ADR-019)를 병합하면
"어떻게 하는가"(절차)와 "지금 어디인가"(상태)라는 서로 다른 질문에
답하는 도구를 하나로 합치게 되어, Manifest의 목적(빠른 상태 조회)이
절차 문서의 서술적 성격에 묻힌다.

### 대응 관계(신규 정리, C1 WARNING 직접 해소)

| ADR-015 Ingestion Lifecycle(절차) | ADR-019 Manifest processing_status(상태) |
|---|---|
| Registration | `RAW_ACQUIRED`(진입) → Manifest Entry 생성 시점의 초기값 |
| Validation, Classification, Metadata Creation | `REGISTERED`(Registry 등록 완료 후 이 상태로 전이) |
| Quality Check | `VALIDATED`(통과 시) — FAIL 시 상태 전이 없이 Registration으로 반려(ADR-015 원칙 그대로) |
| Clean Processing | `VALIDATED` 상태 내부 활동(별도 상태값 없음 — Manifest는 "정제까지 끝났다"를 `VALIDATED`로 뭉뚱그림, 정제 자체의 세부 진행은 Manifest 책임 밖) |
| TSU | `TSU_ELIGIBLE`(필드 조건 충족 판정) → `TSU_GENERATED`(실제 생성 후) |
| Embedding | `TSU_GENERATED`와 `INDEXED` 사이의 암묵적 단계(별도 상태값 부여하지 않음 — Embedding 실패 시나리오는 이번 설계 범위 밖, Remaining Risk) |
| Index Update | `INDEXED` |

이 표가 C1 WARNING("ADR-015 Lifecycle과 ADR-019 Lifecycle 관계
미정리")을 해소하는 결과물이다 — 둘은 여전히 별개 문서·별개 개념으로
유지되지만, 이제 상호 참조 가능한 명시적 대응표가 생겼다.
