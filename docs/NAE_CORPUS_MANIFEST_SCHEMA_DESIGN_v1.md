# NAE Corpus Manifest Schema Design v1

작성일: 2026-08-02
Project: NAE-MANIFEST-SCHEMA-DESIGN-001
성격: **설계 문서 — Schema 파일/Manifest 데이터 생성 없음**
근거: [`NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md`](NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md),
[ADR-019](architecture/ADR-019-NAE-Corpus-Manifest-Layer.md),
[`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md),
[`NAE_SCHEMA_MIGRATION_GUIDE_v1.md`](NAE_SCHEMA_MIGRATION_GUIDE_v1.md)

**이 문서와 이전 설계의 관계**: `NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md`
(NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001)가 단일 `processing_status`
enum(6단계)을 제안했었다. 이번 명령서는 **5개 세분화된 단계별 상태
필드 + Quality Gate + Audit**을 요구한다 — 이는 단일 enum보다 더
정밀한 모델이므로, **이번 문서를 Manifest Schema v1.0의 정본으로
채택**하고 이전 단일-enum 설계는 "상위 요약값(derived summary)"으로
격하해 흡수한다(모순이 아니라 세분화 — §2.3에서 상세).

---

## Phase 1. 기존 구조 분석

### 확인 결과(실측)

| 항목 | 확인 |
|---|---|
| 기존 `source_id` 체계 | Registry(`authority/sources.yaml`)와 corpus manifest(`source_manifest.yaml`)가 동일 네임스페이스 공유(ADR-017 §2.5, Registry Build-001에서 실측 확인) — Manifest도 이 값을 그대로 재사용(`manifest_id = source_id`, ADR-019 결정 유지) |
| Registry 관계 | Author→Work→Edition→Volume→Issue→Source 6단 구조(ADR-016/018) — Manifest는 이 중 `author_id`/`work_id`/`edition_id`/`volume_id`/`issue_id`를 비정규화 복사(조회 편의, Manifest Architecture v1 §Phase1) |
| Manifest 필요 필드 | Identity/Authority Reference/Processing/Quality Gate/Audit 5개 범주 — 이전 설계(Identity+Processing State+Authority Reference 3범주)보다 Quality Gate와 Audit이 추가됨(§Phase2에서 신규 정의) |
| Lifecycle 충돌 여부 | ADR-015(Ingestion, 절차)와 ADR-019(Manifest, 상태) 사이의 관계가 NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001에서 이미 "B안"(별개 층위 + 대응표)으로 해소됨(`NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md` §Phase4) — 이번 Phase 3에서 이 결정을 유지하며 세분화된 상태 필드에 맞춰 대응표만 갱신 |

---

## Phase 2. Manifest Schema 설계

### 1. Entity 정의

```
Authority Registry
        │
Source Manifest      ← 이번 설계 대상(Manifest Entry)
        │
   ┌────┼────┬─────────┐
  RAW   OCR  TSU   Embedding
```

Registry가 "이 자료는 무엇인가"(정적 서지), Source Manifest가 "이
자료가 RAW→OCR→TSU→Embedding 각 단계를 어디까지 통과했는가"(동적
진행 상태)를 담당한다 — Manifest Architecture v1의 경계 정의를
그대로 유지, RAW/OCR/TSU/Embedding 4개를 **Manifest가 추적하는
하위 단계들**로 명시한 것이 이번 정의의 구체화 지점이다.

### 2. Manifest 필수 필드

#### Identity

```yaml
manifest_id: string    # = source_id (ADR-019 유지, 별도 ID 체계 없음)
source_id: string        # Registry sources.yaml FK
schema_version: string   # 이 Manifest 레코드의 스키마 버전(§Phase4에서 필드명 결정)
```

#### Authority Reference

```yaml
author_id: string
work_id: string
edition_id: string|null    # monograph 필수, periodical은 null(ADR-018)
volume_id: string|null     # 다권본/periodical 필수, 단권은 null
issue_id: string|null      # periodical만(optional로 명시 요청됨 — 아래 근거)
```

**`issue_id`를 "optional"로 표기하는 이유**: 명령서 Phase1 예시가
`issue_id(optional)`로 표기했다 — 이전 설계(Manifest Schema v2.2
Design-001)의 "monograph에서 forbidden"이라는 엄격한 규칙과 표현이
다르다. 이번 문서에서는 **"optional"로 통일**한다 — forbidden(값이
있으면 오류)과 optional(없어도 됨, 있어도 허용)은 검증 강도가 다른데,
Manifest 레벨에서는 optional로 두고 **강한 제약(monograph에 issue_id가
있으면 안 됨)은 Validator 책임으로 이전**한다(§Phase5) — 스키마
자체는 유연하게, 강제는 검증기가 담당하는 책임 분리 원칙.

#### Processing Lifecycle(세분화, 5개 단계별 상태)

```yaml
acquisition_status: pending | acquired | failed
ocr_status: not_started | in_progress | complete | failed
metadata_status: not_started | in_progress | verified | failed
tsu_status: not_ready | ready | complete | failed
embedding_status: not_started | in_progress | complete | failed
```

**단일 `processing_status`(이전 설계) 대비 개선점**: 5개 필드로
나누면 "OCR은 끝났지만 metadata 검증이 아직 안 된 상태"처럼 **동시에
여러 단계가 서로 다른 진행도를 가질 수 있는 실제 상황**을 정확히
표현할 수 있다(이전 단일 enum은 이런 부분 진행 상태를 표현하지
못했음 — 실질적 개선).

#### Quality Gate

```yaml
ocr_quality: PASS | WARNING | FAIL | null        # NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 7 3단계 판정 재사용
metadata_verified: boolean
authority_verified: boolean    # Registry Reference Integrity 통과 여부(authority_validator.py 결과 반영)
tsu_eligible: boolean           # 파생값 — 아래 계산식
```

`tsu_eligible` 계산식(파생, 저장은 하되 항상 아래 조건으로 재계산
가능해야 함):

```
tsu_eligible =
    ocr_status == "complete"
    AND metadata_verified == true
    AND authority_verified == true
    AND ocr_quality IN ("PASS", "WARNING")   # FAIL이면 불가
    AND copyright_status != "unknown"          # GOVERNANCE §1 Philosophy #4
```

#### Audit

```yaml
created_at: datetime(ISO 8601)
updated_at: datetime(ISO 8601)
verified_by: string|null    # 사람 식별자 — 자동 검증(도구)과 사람 검증을 구분하기 위해 null 허용, 사람이 확인한 경우만 채움
```

---

## Phase 3. Lifecycle 정합성(갱신)

### 결정 유지: **B안**(ADR-015=절차, Manifest=상태, 별개 층위)

NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001에서 이미 이 결정을 내렸고
이번 문서에서도 번복하지 않는다 — 단, 상태 필드가 5개로 세분화됨에
따라 대응표를 갱신한다.

```
ADR-015 (운영 Process, 절차)
        ↓
Manifest (현재 상태 기록 — 5개 세분화 필드)
        ↓
TSU Pipeline (처리 실행)
```

| ADR-015 단계 | Manifest 필드 대응 |
|---|---|
| Registration | `acquisition_status: acquired`로 전이 |
| Validation, Classification | `authority_verified` 계산(Registry 검증 결과 반영) |
| Metadata Creation | `metadata_status: in_progress → verified` |
| Quality Check | `ocr_quality` 판정 결과 기록 |
| Clean Processing | `ocr_status: in_progress → complete` |
| TSU | `tsu_status: ready → complete`(`tsu_eligible=true`가 `ready` 전이 조건) |
| Embedding | `embedding_status: in_progress → complete` |
| Index Update | Manifest 범위 밖(Retrieval 책임, ADR-001) — Manifest는 `embedding_status: complete`까지만 추적 |

**Index Update가 Manifest 범위 밖인 이유**: ADR-019 Consequences가
이미 "Manifest는 TSU 생성 시점까지의 영향만 있고 RetrievalEngine에
직접 영향을 주지 않는다"고 명시했다 — Embedding 완료 이후 Retrieval
Index 반영은 별도 파이프라인(ADR-001 소관)이므로 Manifest가 추적할
필요가 없다. 이는 이전 설계(v2.2 Design-001)의 `INDEXED` 상태값을
이번 설계에서 의도적으로 제외한 것과 일관된 결정이다.

---

## Phase 4. schema_version 필드 결정

### 결정: **`schema_version`**(단순 필드명, `manifest_schema_version` 아님)

**근거**: Manifest Entry 안에서 이 필드가 가리키는 대상은 항상
"이 Manifest 레코드 자신의 스키마"이므로 `manifest_` 접두어는
중복 정보다(파일이 이미 Manifest Entry라는 문맥 안에 있음 — corpus
manifest의 `schema_version` 필드나 TSU의 `tsu_schema_version` 필드도
각자의 문맥 안에서 접두어 없이 `schema_version`(corpus manifest) /
`tsu_schema_version`(TSU, 실제로는 접두어 있음 — `NAE.pipeline.tsu.config`
실측)을 쓰는 것과 정합성을 맞추려면, 짧은 쪽(`schema_version`)이
Manifest 파일 자체의 관용구와 더 가깝다). 값은 `"1.0.0"`으로 시작
(v2.2 Design-001의 기존 결정 유지, 번복 없음).

---

## Phase 5. Validator Boundary (재확인)

**Option A 채택**(NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001의
Validator Boundary Design-001과 동일 결정, 번복 없음):

```
source_validator.py     (기존, corpus manifest)
        ↓
authority_validator.py  (설계만, Registry)
        ↓
manifest_validator.py    (신규 설계, Manifest Entry)
```

**Option B(통합 Validator) 기각 근거 재확인**: 세 계층(corpus
manifest/Registry/Manifest)은 각각 다른 파일·다른 갱신 빈도·다른
책임을 가지므로, 하나의 통합 도구로 합치면 책임이 섞이고 회귀 테스트
범위가 불필요하게 커진다(`NAE_VALIDATOR_BOUNDARY_DESIGN_001.md` §2와
동일 논리). `manifest_validator.py`의 신규 책임(이전 설계 대비 추가):

- `tsu_eligible` 파생값이 실제로 위 계산식과 일치하는지 재계산·대조
- `acquisition_status`~`embedding_status` 5개 필드의 개별 전이 규칙
  준수 여부(각 enum 내에서 forward-only)
- `issue_id`가 monograph(Work.work_type≠periodical)에 값이 있으면
  FAIL(스키마는 optional로 열어뒀지만 검증기가 강제, §Phase2 근거)

---

## Phase 6. Processing Status Rule

### 허용 값(요청된 단일 요약 enum, 파생 필드로 채택)

```yaml
processing_status: pending | acquired | ocr_complete | metadata_verified | tsu_ready | tsu_complete | embedded
```

이 필드는 **5개 세분화 필드(§Phase2)의 파생 요약값**이다 — 저장은
하되(빠른 필터링용), 진실의 원천(source of truth)은 항상 5개
세분화 필드다. 매핑 규칙:

| `processing_status`(요약) | 조건(5개 필드 기준) |
|---|---|
| `pending` | `acquisition_status = pending` |
| `acquired` | `acquisition_status = acquired`, 나머지 미시작 |
| `ocr_complete` | `ocr_status = complete` |
| `metadata_verified` | `metadata_status = verified` |
| `tsu_ready` | `tsu_eligible = true`(Quality Gate 계산식 충족) |
| `tsu_complete` | `tsu_status = complete` |
| `embedded` | `embedding_status = complete` |

### 역행 처리 정책

**원칙: 각 세분화 필드는 자신의 enum 안에서 forward-only.** 예:
`embedded`(요약값)에서 `acquired`로 직접 되돌리는 것은 **금지**(명령서
예시 그대로).

**단, "역행"과 "재작업(rework)"을 구분**한다(이전 설계 Manifest
Architecture v1 §Phase3에서 이미 확립한 "반려는 역행이 아니다" 원칙의
구체화):

```
금지: embedded → acquired  (요약값을 강제로 되돌리는 것)

허용: 특정 세분화 필드를 개별적으로 "failed"로 전이 후 재시도
      예: embedding_status: complete → (재작업 필요 발견) → in_progress
      단, 이 경우 반드시 audit(verified_by + updated_at)에 사유 기록
```

즉 "이미 끝난 embedding을 다시 하고 싶다"는 요구는 **요약값을
되돌리는 것이 아니라, `embedding_status`만 명시적으로
`in_progress`로 재설정하고 사유를 audit에 남기는 것**으로 처리한다
— 이렇게 하면 다른 4개 필드(acquisition/ocr/metadata/tsu)의 완료
기록은 그대로 보존되어 "처음부터 다시"가 아니라 "이 단계만 재작업"이
명확히 구분된다.
