---
title: "ADR-021: NAE Source Registration → Raw Preservation → Extraction (Upstream Ingestion Layer v1)"
category: architecture
based_on:
  - docs/NAE_CORPUS_INGESTION_STANDARD_v1.md
  - docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
  - docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
  - docs/architecture/ADR-020-NAE-Incremental-Ingestion-Architecture.md
  - docs/NAE_METADATA_GOVERNANCE_v1.md
created: 2026-08-11
scope: 신규 모듈 NAE/pipeline/registration/ (제안). 기존 NAE/pipeline/canonical/*,
  NAE/pipeline/tsu/*, NAE/pipeline/ingest/*, NAE/pipeline/index/*, NAE/pipeline/embed/*,
  NAE/collectors/*, core/dataset_registry.py 무수정 — 전량 재사용만.
---

# ADR-021: NAE Source Registration → Raw Preservation → Extraction (Upstream Ingestion Layer v1)

| | |
|---|---|
| Status | **Proposed** (구현 전 승인 대기) |
| Date | 2026-08-11 |
| Deciders | Rev. Bang, CUE |
| Extends | ADR-020(Incremental Ingestion, downstream 절반 — 이미 Approved/GREEN) |
| Formalizes | `NAE_CORPUS_INGESTION_STANDARD_v1.md`(설계 단계, 2026-08-02)의 Phase 2 "Registration → Validation → Classification → Metadata Creation → Quality Check" 구간을 코드로 승격 |
| Supersedes | — |
| Superseded by | — |

**Evidence Before Promotion Rule 적용**: 본 ADR은 구현 완료·회귀 테스트 통과·
C1 독립 리뷰·사용자 승인 4개 조건을 모두 충족하기 전까지 Proposed 상태를
유지하며, 다른 구현의 근거로 사용하지 않는다.

---

## 1. Context

ADR-020(Approved, GREEN GATE)은 **TSU 레코드가 이미 Production에 존재하는
시점부터** 시작하는 downstream 절반(hash 판정 → state → embedding → Qdrant
append)만 다룬다. ADR-020 §12는 이렇게 명시했다:

> "discovery→registration→OCR→first-TSU 파이프라인은 out of scope"

이 앞단은 `NAE_CORPUS_INGESTION_STANDARD_v1.md`(2026-08-02)가 **절차/스키마
수준으로는 이미 설계**되어 있으나(Phase 2~10, Registration ID 규칙·Authority
Model·Quality Gate·TSU Integration Policy까지 확정), **코드로 구현된 적은
없다** — 문서 자체가 "이번 설계는 각 단계의 정의와 순서만 확립하며, 실제
코드/스크립트 구현은 하지 않는다"고 명시.

본 ADR의 목적은 그 설계 문서의 Phase 2~7(Registration/Identity/Raw
Preservation/Extraction까지)을 **코드로 승격**하는 것이다. Phase 8(TSU
Integration)부터는 이미 존재하는 `NAE/pipeline/tsu/builder.py`(TSU 생성)와
ADR-020의 `NAE/pipeline/ingest/`(hash/state/embedding/index)를 그대로
호출·재사용하며, 이 두 하위 시스템의 코드는 수정하지 않는다.

## 2. Decision

`NAE/pipeline/registration/` 패키지를 신설해 다음 4단계를 담당하게 한다:

```
NEW SOURCE (Public-Domain 원자료)
       ↓
Source Registration      — source_id/author_id/work_id/edition_id 발급,
                            source_manifest.yaml entry 작성 (Phase 3 ID 규칙)
       ↓
Identity Resolution       — Author/Work/Edition Authority 대조·병합
                            (Phase 4, 자동 병합 금지 — 불일치 시 사람 확인)
       ↓
Immutable Raw Preservation — NAE/corpus/raw/ 하위 배치, SHA256 체크섬 기록,
                            원본 파일 쓰기 금지(read-only 권한 부여)
       ↓
Extraction                — 기존 NAE/pipeline/canonical/extract.py 그대로 호출
                            (hOCR 우선 → OCR TXT → PDF fallback)
       ↓
Quality Gate               — Phase 7 PASS/WARNING/FAIL, FAIL 시 Registration으로 반려
       ↓
(TSU Builder / ADR-020 incremental pipeline로 인계 — 본 ADR 범위 밖)
```

기존 `NAE/pipeline/canonical/*`(extract/normalize/structure/reflow/annotate),
`NAE/pipeline/tsu/builder.py`, `NAE/collectors/archive_org/*`,
`core/dataset_registry.py`는 **코드 무수정, 호출만** 한다.

## 3. 재사용 vs 신규 (Discovery 결과 요약)

| 구성요소 | 상태 | 처리 |
|---|---|---|
| ID 생성 규칙(source_id/author_id/work_id/edition_id) | 설계 확정(`NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 3) | 그대로 구현 |
| `source_manifest.schema.yaml` v1.2 | 기존 스키마 존재, 검증 로직 미확장 | 재사용, `source_validator.py` 확장만(Phase 10 후보 → 본 ADR로 승격) |
| Author/Work/Edition Authority(`authority/*.yaml`) | 설계만, 파일 미생성 | 신규 생성 |
| OCR/텍스트 추출 | `NAE/pipeline/canonical/extract.py` 완전 구현·재사용 중 | **무수정 재사용** — 신규 OCR 엔진 붙이지 않음(기존이 업스트림 사전-OCR 결과 소비 방식 유지) |
| Raw 디렉토리 구조 | `NAE/corpus/raw/archive_org/{category}/{work}/` 관례 존재 | 그대로 계승, 체크섬만 추가 |
| Immutability 강제 | 정책만 존재(코드 강제 없음) | **신규** — SHA256 기록 + 파일 권한 read-only(0o444) |
| Duplicate Detection | 규칙 설계만(Phase 6) | Exact Duplicate(해시 비교)만 자동화, 나머지는 사람 판단 유지 |
| Quality Gate | 항목/판정 체계 설계만(Phase 7) | 신규 구현, 임계값은 실측 샘플로 보정(초기값은 보수적으로 WARNING 우선) |
| Dataset Isolation | `core/dataset_registry.py` 기존 구현 | 재사용 — 신규 source 등록 시 Dataset Registry에도 등록 |
| Archive.org 수집 | `NAE/collectors/archive_org/collector.py` 완전 구현 | 재사용(선택적 전단계, 이미 다운로드된 원자료도 직접 등록 가능해야 함) |

## 4. Identity Strategy

ADR-020 §3과 동일 계층을 **역방향으로** 채운다 — ADR-020은 이미 존재하는
TSU에서 identity를 역추출했지만, 본 ADR은 Registration 시점에 identity를
**최초로 발급**한다:

```
Author(author_id) → Work(work_id) → Edition(edition_id) → Source File(source_id)
```

- `author_id`/`work_id`/`edition_id` 포맷: `NAE_CORPUS_INGESTION_STANDARD_v1.md`
  Phase 3 "ID 생성 규칙" 그대로(`{surname}_{givenname}`,
  `{author_id}-{title_slug}`, `{work_id}-{edition_slug}`).
- 충돌 시 숫자 suffix 순차 부여 + notes 기록(자동 침묵 덮어쓰기 금지) — 기존
  규칙 그대로.
- `source_id`는 포맷 강제 없이 유일성만 검사(기존 관례 계승).
- Author/Work Authority 병합은 **항상 사람 확인** — 자동 병합 금지(동명이인
  위험, Phase 4 원칙 그대로 계승).

## 5. Raw Immutability (신규 강제 메커니즘)

기존 갭: "RAW immutable"은 `NAE_DATA_ARCHITECTURE.md`의 **정책**일 뿐, 이를
어기는 것을 막는 코드가 없었다(Discovery 확인 완료). 본 ADR이 추가하는 것:

1. Registration 완료 시 원본 파일에 SHA256 체크섬 계산 → manifest entry에
   `raw_checksum` 필드로 기록.
2. 파일 권한을 read-only(0o444)로 변경 — 실수로 인한 덮어쓰기 방지(강제는
   아니며 사고 방지 수준; `chmod`로 우회 가능함을 문서에 명시).
3. 이후 모든 파이프라인 단계(Extraction 포함)는 원본 파일 경로를 **읽기만**
   하고, 결과물은 별도 경로(`NAE/corpus/canonical/`, 기존 관례)에 쓴다 —
   기존 Extraction 코드가 이미 이 원칙을 따르고 있음을 확인함(수정 불필요).
4. 체크섬 불일치가 감지되면(예: 재실행 시 재확인) FAIL로 처리하고 Quality
   Gate를 통과시키지 않는다 — 자동 복구/재다운로드는 하지 않는다(사람 개입
   필요).

## 6. Idempotency

- 동일 원본 파일(해시 일치)이 재등록 시도되면 Phase 6 "Exact Duplicate"
  규칙에 따라 신규 `source_id`를 발급하지 않고 기존 entry에 `local_path`
  alias만 추가한다.
- Registration이 중간에 실패해도(예: Quality Gate FAIL) 원본 파일은
  Immutable Raw 영역에 남아있고, manifest entry의 `status`만 이전 단계로
  되돌린다 — 파일을 삭제/이동하지 않는다.

## 7. Failure Isolation

ADR-020 §5의 `ProcessingState` 패턴을 그대로 계승 — 신규
`NAE/pipeline/registration/state.py`가 소스 파일 단위 상태를 독립적으로
추적한다:

```
DISCOVERED → REGISTERED → RAW_PRESERVED → EXTRACTED → QUALITY_PASSED
실패: REGISTRATION_FAILED / RAW_CHECKSUM_MISMATCH / EXTRACTION_FAILED / QUALITY_GATE_FAILED
```

한 source의 실패가 다른 source의 등록을 막지 않는다(레코드별 독립 상태,
ADR-020과 동일 원칙).

## 8. Dataset Isolation

신규 source 등록 시 `core/dataset_registry.py`에도 함께 등록한다
(`TrustTier`/`LicensePolicy` 부여) — Public-Domain 원자료는 기본
`TrustTier.T1`(raw/objective) + `LicensePolicy.redistributable`(저작권
만료 확인된 경우만; 불확실하면 `metadata_only`). 기존 3,319 verified TSU가
속한 dataset과는 별도 `dataset_id`로 등록해 명시적으로 분리한다 — 병합은
Human Review 완료 후 별도 절차(Phase F, 현재 보류 중)에서만 수행.

## 9. TSU Builder / ADR-020 인계 지점

Quality Gate PASS(또는 사람이 확인한 WARNING)를 통과한 source만 기존
`NAE/pipeline/tsu/builder.py`에 canonical text를 넘긴다. TSU 생성 이후
`review_status=generated`로 시작하는 것은 기존 동작 그대로이며(776건과
동일 패턴), 곧바로 embedding/index로 넘어가지 않는다 — ADR-020의
incremental pipeline은 `review_status=verified`인 레코드만 처리하므로
자동으로 격리된다(기존 `review_gate.py`가 이미 이 경계를 강제).

## 10. 절대 금지 (본 ADR 구현 범위에서)

- `NAE/pipeline/canonical/*`, `NAE/pipeline/tsu/*`, `NAE/pipeline/ingest/*`,
  `NAE/pipeline/index/*`, `NAE/pipeline/embed/*` 코드 수정
- 기존 3,319 verified TSU / Qdrant 3,319 vector에 대한 어떤 재처리도 수행
- OCR 엔진 자체 구현(기존처럼 사전-OCR 결과를 소비하는 방식 유지)
- Human Review disposition 구조(776건, 현재 보류 중) 설계 — 완전히 별개
  범위, 본 ADR과 무관
- 자동 병합(Author/Work Authority) — 항상 사람 확인

## 11. Compliance

- ADR-001(RetrievalEngine 유일 정본) 미충돌 — 본 계층은 Qdrant/Retrieval에
  직접 쓰지 않고 TSU Builder까지만 인계.
- ADR-013(NAE 독립 Qdrant) 미충돌 — vector 쓰기 없음.
- ADR-015/016(Ingestion Standard/Metadata Authority) 미충돌 — 그 설계를
  코드로 승격할 뿐, 값 체계나 ID 규칙을 변경하지 않음.
- ADR-020(Incremental Ingestion) 미충돌 — downstream(TSU 존재 이후)에는
  일절 손대지 않고, upstream(TSU 존재 이전)만 신설.
- Architecture Freeze Rule: 본 ADR은 Proposed 상태이며, Approved로
  승격되기 전까지 어떤 기존 Approved ADR도 변경/우회하지 않는다.

---

## 12. 미결 사항 (구현 전 확인 필요)

1. Quality Gate의 OCR 품질 임계값 — 실측 샘플 부재로 초기값 미정(설계
   문서도 "후속 정의"로 명시). 초기 구현은 보수적으로 WARNING 우선 처리
   제안, 사람이 실측 후 조정.
2. Author/Work Authority 파일(`authority/authors.yaml`,
   `authority/works.yaml`) 최초 생성 — 기존 3,319 TSU에서 역산해 초기
   시드를 만들지, 빈 상태로 시작할지 결정 필요.
3. `source_validator.py` 확장 범위 — Phase 3 신규 필드까지 검사하도록
   넓힐지, 별도 validator를 신설할지.
