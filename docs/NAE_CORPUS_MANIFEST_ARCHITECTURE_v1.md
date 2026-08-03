# NAE Corpus Manifest Architecture v1

작성일: 2026-08-02
Project: NAE-CORPUS-MANIFEST-ARCHITECTURE-DESIGN-001
성격: **설계 문서 — 실제 Manifest 생성 없음, Schema/Validator/Registry 변경 없음**
근거: [`NAE_PERIODICAL_CONDITION_RESOLUTION_REPORT_001.md`](NAE_PERIODICAL_CONDITION_RESOLUTION_REPORT_001.md)
(TSU Field Readiness Gap 발견), [`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md`](NAE_AUTHORITY_REGISTRY_DESIGN_v1.md),
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[ADR-018](architecture/ADR-018-NAE-Periodical-Authority-Extension.md)

---

## Phase 1. 현재 Pipeline Boundary 분석

### 실측: 코드에 Manifest 개념이 존재하는가?

`NAE/pipeline/`, `core/`, `scripts/` 전수 검색 결과 `manifest_id`,
`processing_status`, `tsu_eligible` 등의 개념은 **코드 어디에도
존재하지 않는다**(실측, grep 결과 0건) — 이는 추측이 아니라 확인된
사실이다. 즉 지금까지 "corpus manifest"라고 불러온
`source_manifest.yaml`(Pilot-001/002가 실제로 만든 파일)은 **비공식적
관행**이었을 뿐, 정식으로 설계된 계층이 아니었다. 이번 작업은 그
비공식 관행을 정식 Architecture로 승격시키는 것이다.

### 현재 구조와 공백

```
RAW
  │
Authority Registry   (Author→Work→Edition→Volume→Issue→Source, 정체성/서지 구조)
  │
  ?                    ← 이번에 정의하는 Manifest Layer
  │
TSU
  │
Embedding
  │
Retrieval
```

### Manifest Layer의 책임(정의)

| 책임 | 설명 | Registry와의 차이 |
|---|---|---|
| Source Identity | `source_id` 재확인(Registry와 동일 값 공유, FK) | Registry가 "이 Source가 어느 저작·판본·권·호에 속하는가"를 정의한다면, Manifest는 "이 Source가 지금 처리 파이프라인의 어느 단계에 있는가"를 정의 |
| File Location | RAW/처리 결과물의 실제 경로 | Registry의 `file_path`(RAW 원본 위치, 불변)와 달리 Manifest는 **처리된 산출물**(정제 텍스트, TSU 입력 등)의 경로도 함께 추적할 수 있음 |
| Authority Reference | `work_id`/`edition_id`/`volume_id`/`issue_id` (Registry FK 재확인) | Registry가 정본, Manifest는 조회 편의를 위한 비정규화(denormalized) 복사값 — TSU 생성 시 Registry를 매번 조인하지 않아도 되게 함(TSU Field Readiness Report-001에서 확인된 "유도 경로가 깊다"는 문제의 직접적 해법) |
| Access Policy | `source_type`/`copyright_status`/`usage_permission`/`access_control`(GOVERNANCE §4) | Registry Source entity가 이미 갖고 있는 필드 — Manifest는 이를 **TSU 생성 게이트의 판단 근거**로 다시 사용(중복이 아니라 같은 값을 다른 목적으로 조회) |
| Processing Status | 파이프라인 진행 상태(§Phase3 Lifecycle) | Registry에는 없는 개념 — Registry는 "무엇인가"를, Manifest는 "지금 어디까지 처리됐는가"를 답한다 |
| TSU Eligibility | 위 조건이 전부 충족됐는지 파생 판정 | Registry 데이터만으로는 계산되지 않음 — Manifest가 계산해 저장하는 파생 상태 |

**핵심 결론**: Registry는 **정적 서지 구조**(바뀌지 않는 "이 책은
누가 썼고 어느 판본인가"), Manifest는 **동적 처리 상태**("이 파일이
지금 파이프라인의 어디에 있는가")를 담당한다. 이 구분이 지금까지
암묵적으로만 존재했다(Registry Design v1 §2.5 "Registry Source는
TSU 필드를 의도적으로 갖지 않는다"는 결정이 이미 이 경계를 예견했음).

---

## Phase 2. Entity 관계 설계

### 최종 구조

```
Author
  │
Work
  │
Edition (monograph, periodical은 생략 — ADR-018)
  │
Volume (선택)
  │
Issue (periodical 전용, ADR-018)
  │
Source
  │
Manifest Entry   ← 신설
  │
TSU
```

### Q1. Manifest Entry는 Source의 확장인가, 별도 Entity인가?

**결정: 별도 Entity, `source_id` FK로 1:1 연결**(Source의 하위
필드로 확장하지 않음).

**근거**:
- Registry Source(`authority/sources.yaml`)와 Manifest Entry는
  **갱신 빈도가 다르다** — Source는 자료 등록 시 1회 기록되고 거의
  바뀌지 않지만, Manifest의 `processing_status`는 파이프라인이
  진행될 때마다 계속 바뀐다. 하나의 파일/엔티티에 합치면 자주 바뀌는
  값과 거의 안 바뀌는 값이 뒤섞여 git diff 가독성이 떨어진다(Registry
  Design v1 §Phase3에서 이미 "변경 빈도 차이"를 파일 분리 근거로 사용한
  것과 동일 원칙 재적용).
- Registry Build-001부터 유지해 온 원칙 — "Registry Source는 TSU
  필드를 의도적으로 갖지 않는다"(Registry Design v1 §2.5)와 일관되게,
  Manifest도 Source의 확장이 아니라 **독립된 관점(projection)**으로
  둔다.

### Q2. 하나의 Source가 여러 Manifest를 가질 수 있는가?

**결정: 1:1**(`Source → Manifest Entry`). OCR/TSU/Embedding 단계를
별도 Manifest 문서로 나누지 않고, **하나의 Manifest Entry 안에서
`processing_status` 필드 값이 전진(advance)하는 방식**을 채택한다.

**근거**:
- Phase 3의 Lifecycle(RAW Acquired → … → Indexed)은 **선형(linear)
  진행**이지 병렬 분기가 아니다 — 병렬 Manifest(OCR Manifest/TSU
  Manifest/Embedding Manifest)를 만들면 "지금 이 Source가 정확히 어느
  단계인가"를 여러 문서를 대조해야 알 수 있게 되어 Manifest 본연의
  목적(단일 진실 공급원으로 상태 추적)에 반한다.
- 1:1 모델은 Reference Integrity 검사 로직도 단순하다(Registry
  Build-001/Periodical Pilot에서 반복 검증한 패턴 재사용 가능 — FK
  1개만 확인하면 됨).

---

## Phase 3. Manifest Schema 설계 (문서 수준, 스키마 파일 미생성)

### Required Fields

```yaml
manifest_id: string        # = source_id 그대로 재사용(1:1이므로 별도 ID 체계 불필요, ADR-017 미개정)
source_id: string          # Registry sources.yaml FK
work_id: string             # Registry 비정규화 복사(조회 편의)
edition_id: string|null     # monograph 필수, periodical은 null(Edition 생략, ADR-018)
volume_id: string|null      # 다권본/periodical 필수, 단권 monograph는 null
issue_id: string|null       # periodical 필수, monograph는 null
processing_status: RAW_ACQUIRED | REGISTERED | MANIFEST_CREATED | VALIDATED | TSU_ELIGIBLE | TSU_GENERATED | INDEXED
tsu_access: full | restricted | citation_only   # GOVERNANCE §6 기존 값 체계 재사용
schema_version: string      # 이 Manifest 레코드가 따르는 스키마 버전(예: "2.2.0")
```

`edition_id`/`volume_id`/`issue_id`의 조건부 필수 규칙은 **ADR-018이
TSU 필수 필드에 대해 이미 정의한 `work_type` 분기 규칙을 그대로
재사용**한다 — Manifest Layer가 새 규칙을 만들지 않는다(중복 결정
방지).

### Lifecycle

```
RAW Acquired        원본 파일 확보(Registry Source entity 생성 이전 단계)
      ↓
Registered           Registry(Author/Work/Edition/Volume/Issue/Source) 등록 완료
      ↓
Manifest Created      Manifest Entry 생성(이 문서가 정의하는 신규 단계)
      ↓
Validated              Registry Validation Tool(설계만 존재, Registry Design v1 §Phase5) 통과
      ↓
TSU Eligible            Access Policy + Authority Reference 필드 전부 충족(파생 판정)
      ↓
TSU Generated             TSU 빌더 실행 완료
      ↓
Indexed                    Retrieval에 노출 가능
```

각 화살표는 **역행 불가**(단조 증가)를 원칙으로 한다 — 단, 검증
실패 시 이전 단계로 되돌리는 것은 "역행"이 아니라 "반려"로 별도
취급한다(Registry Design v1의 FAIL→Registration 반려 패턴과 동일).

---

## Phase 4. Monograph / Periodical 통합 검토

### 판정: **PASS(공통 모델로 처리 가능, Extension 불필요)**

```
Monograph:   Work → Edition → Source → Manifest → TSU   (volume_id/issue_id = null)
Periodical:  Work(periodical) → Volume → Issue → Source → Manifest → TSU   (edition_id = null)
```

**근거**: Manifest Schema(§Phase3)가 `edition_id`/`volume_id`/
`issue_id` 3개 필드를 전부 갖되 자료 유형에 따라 필요한 것만 채우는
구조이므로, monograph와 periodical이 **동일한 Manifest Entry 스키마를
공유**한다 — ADR-018이 TSU 필수 필드에 대해 이미 적용한 "work_type
분기, 필드는 공유" 원칙과 완전히 같은 패턴이다. 별도
`PeriodicalManifest`/`MonographManifest` 타입 분리는 불필요(과설계
회피, CLAUDE.md 원칙과 일관 — 지금까지 이 Revision 시리즈 전체에서
반복 적용해 온 판단 기준).

---

## 완료 조건 관련 요약(상세 답변은 Review 문서 참고)

이 설계 문서는 Manifest Layer의 **필요성·경계·스키마·통합 가능성**을
정의했다. 실제 구현(스키마 파일, Validator 확장, 실 데이터 생성)은
전부 후속 작업이며, 이번 문서 자체는 어떤 파일도 생성/수정하지
않았다(Registry/RAW/Validator/Pilot 무변경).
