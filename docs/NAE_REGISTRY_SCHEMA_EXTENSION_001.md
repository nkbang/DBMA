# NAE Registry Schema Extension 001

작성일: 2026-08-03
Project: NAE-REGISTRY-SCHEMA-EXTENSION-001
성격: **Schema 설계만 — Registry/YAML/Pilot/Manifest/RAW/Validator 코드 변경 없음**
근거: [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md),
[`NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md`](NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md)(Option B 채택 근거),
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md)

---

## 0. 설계 전제 — Option B의 정확한 의미 재확인

Resolution Plan-001이 채택한 Option B("Canonical + Legacy Alias 유지")는
**기존 FK 문자열을 바꾸지 않는다**는 것이 핵심이다. 이번 확장은 그
원칙을 스키마 레벨로 구체화한다:

- 각 entity의 **기존 ID 필드**(`author_id`/`work_id`/`edition_id`/
  `volume_id`/`source_id`)는 **그대로 유지**되고, 계속 다른 entity의
  FK 대상으로 쓰인다 — 이번 확장으로 **바뀌지 않는다.**
- `canonical_id`/`legacy_id`는 그 기존 ID 필드에 **추가되는 신규
  속성**이지, 새로운 FK 대상이 아니다. 즉 `work.author_id`가
  `canonical_id`를 가리키도록 바뀌는 일은 없다.
- 이렇게 설계해야 "기존 Registry 데이터를 건드리지 않고 신규 필드만
  추가"가 실제로 가능해진다(§3 Q1 답변의 근거).

---

## 1. 필드 정의

```yaml
canonical_id:
  type: string
  required: true
  description: >
    ADR-017 canonical 표기(lowercase snake_case, surname 우선 등)로
    변환된 값. 이미 canonical인 entity는 자기 자신의 ID와 동일한 값을
    채운다(예: author_id=dagg_john_l → canonical_id=dagg_john_l).
    ID Governance v1 §6.2 매핑표가 이 필드의 값 출처다.

legacy_id:
  type: array[string]
  required: false
  description: >
    과거에 사용됐거나 현재 사용 중인 비-canonical 표기를 보존한다.
    이번 확장 시점에는 "현재 ID 필드 값이 canonical_id와 다른 경우"
    그 값을 legacy_id에 그대로 기록한다(예: author_id=FULLER-ANDREW-001
    → legacy_id: [FULLER-ANDREW-001]). 향후 실제 ID rename이 실행되면
    이 배열에 항목이 늘어날 수 있다(다회 rename 이력 보존).
```

### 왜 `canonical_id`는 필수이고 `legacy_id`는 선택인가

모든 entity는 "ADR-017 기준 정식 표기가 무엇인가"에 답할 수 있어야
하므로(설계 문서 §Executive Summary의 "Architecture 완성" 취지와
일치) `canonical_id`는 예외 없이 채워야 한다. 반면 `legacy_id`는
"과거 표기가 실제로 존재하는 경우"에만 의미가 있다 — 처음부터
canonical하게 등록된 entity(`dagg_john_l`, `hiscox_edward_t`)는
legacy_id가 빈 배열이어도 정상이다.

---

## 2. Entity별 영향 분석

| Entity | 파일 | 영향 받는 개수 | canonical_id ≠ 기존 ID인 개수(legacy_id 필요) |
|---|---|---|---|
| Author | `authors.yaml` | 3 | 1(`FULLER-ANDREW-001`) |
| Work | `works.yaml` | 3 | 3(전부) |
| Edition | `editions.yaml` | 4 | 4(전부) |
| Volume | `volumes.yaml` | 8 | 8(전부) |
| Source | `sources.yaml` | 10 | 10(전부) |
| **합계** | 5개 파일 | **28** | **26**(Resolution Plan-001의 WARNING 26건과 정확히 일치) |

값 출처는 전부 `NAE_ID_GOVERNANCE_v1.md` §6.2 매핑표 — 이번 확장에서
새로 계산하지 않는다(재도출 시 두 문서가 어긋날 위험 회피, Resolution
Plan-001과 동일 원칙).

---

## 3. 검토

### Q1. 기존 Registry 수정 없이 적용 가능한가?

**예.** `canonical_id`/`legacy_id`는 **추가 필드**이지 기존 필드의
값·의미를 바꾸지 않는다 — 스키마 정의(이 문서)와 실제 YAML 파일에
필드를 채워 넣는 작업(향후 별도 승인)은 분리된 단계이며, 이번
문서는 전자만 다룬다. 기존 FK 필드(§0)가 안 바뀌므로 이 필드를
추가해도 다른 entity와의 참조 관계는 전혀 영향받지 않는다.

### Q2. FK 무결성 유지 가능한가?

**예, 영향 없음.** `canonical_id`/`legacy_id`는 FK 대상이 아니므로
(§0), `authority_validator.py`의 기존 FK Integrity 검사(5개 엣지)는
전혀 수정할 필요가 없다 — 새 필드는 그 검사 로직과 완전히 독립적이다.

### Q3. Authority Validator 수정 범위

**수정 필요 — 단, 신규 항목 추가일 뿐 기존 로직 변경 아님:**

1. `canonical_id` 필드 존재 확인(신규 required 필드) — 없으면 FAIL.
2. `canonical_id` 값 자체가 ADR-017 정규식(lowercase snake_case)을
   만족하는지 검사 — **여기서는 WARNING이 아니라 FAIL**이어야 한다.
   기존 Canonical ID Format 검사(§4, `_CANONICAL_ID_RE`)는 entity의
   **기존 ID 필드**가 비표준이어도 WARNING만 주도록 설계됐지만(ID
   Governance v1이 즉시 rename을 보류했으므로), `canonical_id`
   필드는 애초에 "이것이 canonical 표기다"라고 선언하는 필드이므로
   그 값 자체가 규칙을 어기면 데이터 오류(FAIL)로 봐야 한다.
3. `legacy_id`가 있으면 배열 타입인지 확인(형식 검증만, 값의 사실
   여부는 판단하지 않음 — 기존 `archive_source` 필드 검사와 동일
   관용 수준).

**변경하지 않는 것**: 기존 FK Integrity(#1)/Duplicate IDs(#2)/Legacy
Alias(#3)/Orphan Entity(#6)/Circular Reference(#7)/Duplicate
Canonical Name(#8) 6개 검사는 전부 무변경 — canonical_id 도입과
무관한 별개 관심사.

### Q4. Migration 순서

```
1. 이번 설계 문서 승인
        ↓
2. C1 독립 Architecture Review(요청하신 대로 이번 단계는 미투입,
   설계 완료 후 검토)
        ↓
3. Authority Validator 코드 구현(Q3의 3개 항목, 별도 CUE 작업 승인)
        ↓
4. Registry 5개 파일에 canonical_id/legacy_id 실제 데이터 추가
   (28개 entity, 값은 ID Governance v1 §6.2 그대로 — 이 단계도
   기존 FK 필드는 절대 건드리지 않음)
        ↓
5. authority_validator.py 재실행 회귀 확인(74 PASS 기준 유지 + 신규
   canonical_id 검사 항목 추가 확인)
        ↓
6. (선택, 장기 과제) 실제 FK 문자열을 canonical_id로 전환하는 완전한
   Migration — 이 단계는 Option A에 준하는 위험을 가지므로 별도의
   전용 논의와 승인이 필요, 이번 로드맵 범위 밖
```

---

## 완료 시 답변

1. **canonical_id 필수 여부** — **예, required**(모든 entity, §1).
2. **legacy_id 자료형** — **array[string], optional**(§1).
3. **FK 영향** — **없음**(§0, §Q2) — 기존 FK 필드는 전혀 바뀌지 않음.
4. **Authority Validator 수정 필요 여부** — **예**(§Q3, 3개 항목 추가 — 기존 6개 검사는 무변경).
5. **Migration 가능 여부** — **아니오** — 이번 문서는 스키마 설계만, 실제 필드 추가/데이터 변경 없음.
6. **ADR-016 수정 여부** — **불필요** — Entity 계층 모델(Author→Work→Edition→Volume→Source) 자체는 변경 없음, `canonical_id`/`legacy_id`는 각 Entity의 속성 추가일 뿐.
7. **ADR-017 수정 여부** — **불필요** — canonical ID 생성 규칙 자체는 그대로, 이번 확장은 그 규칙을 Registry 데이터에 반영하는 실행 메커니즘(스키마 필드) 설계일 뿐.

---

*Registry 수정, YAML 수정, Pilot 수정, Manifest 수정, RAW 수정,
Validator 코드 수정, Migration, Git Commit/Push — 전부 수행하지 않음.*
