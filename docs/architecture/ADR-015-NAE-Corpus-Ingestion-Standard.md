---
title: "ADR-015: NAE Corpus Ingestion Standard (Design Only)"
category: architecture
based_on:
  - docs/NAE_DATA_ARCHITECTURE.md
  - docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md
  - docs/NAE_METADATA_GOVERNANCE_v1.md (2026-08-02 revision)
created: 2026-08-02
revised: 2026-08-02 (NAE-METADATA-GOVERNANCE-REVISION-001 — §3.7 Dataset Isolation Rule 추가, C1 Review-001 R6 대응)
scope_modified: docs/ only — 파일 이동/삭제/다운로드/OCR/TSU/Embedding/Retrieval 코드 변경 없음
---

# ADR-015: NAE Corpus Ingestion Standard (Design Only)

| | |
|---|---|
| Status | Proposed(승격 보류, 2026-08-03 NAE-ADR-PROMOTION-001 검토) |
| Date | 2026-08-02 |
| Deciders | 사용자 승인 대기 (설계 문서 단계) |
| Supersedes | — |
| Superseded by | — |

---

## 1. Context

NAE Baptist Corpus(Public Domain)는 43GB+ 확보되어 있고, ADR-014로 Modern Corpus
Layer가 설계되었다. 그러나 신규 자료(신학서/현대 자료/주석/설교집/선교/교회행정/연구
자료)가 계속 추가될 때, 매번 Architecture Review 전체를 반복하는 것은 비효율적이며
등록 기준이 문서마다 흩어져 일관성이 떨어질 위험이 있다.

## 2. Problem

신규 자료를 동일 기준으로, 반복 가능한 절차로, 안전하게(원본 불변·저작권 보호·
중복 비파괴) 등록하려면 어떤 표준 파이프라인이 필요한가?

## 3. Decision

### 3.1 Ingestion Lifecycle (10단계 고정 순서)

```
New Source → Registration → Validation → Classification → Metadata Creation
→ Quality Check → Clean Processing → TSU → Embedding → Index Update
```

각 단계의 책임/입출력/실패 처리는 [`NAE_CORPUS_INGESTION_STANDARD_v1.md`](../NAE_CORPUS_INGESTION_STANDARD_v1.md)
Phase 2에 정의. 신규 자료는 예외 없이 이 순서를 따른다 — 순서 생략(예: Quality Gate
건너뛰고 TSU 진행)을 금지한다.

### 3.2 Registration Schema

요청된 12개 필수 필드(`source_id`~`usage_permission`)를 채택하고, 기존
`source_manifest.schema.yaml`을 **재작성하지 않고** 그 위에 병행 절차로 얹는다 —
PD(v1.2)는 `license` 필드를 canonical로 유지하며 `copyright_status`는 파생값,
Modern(ADR-014 v2.0.0)은 신규 필드를 그대로 사용.

### 3.3 Authority Layer 신설 (설계, 미생성)

`author_id`/`work_id`를 등록 표준의 1급 필드로 채택하고, 표기 변형 통합(Author
Authority)과 판본 관리(Edition Authority)를 manifest와 분리된 authority 레지스트리
(`authority/authors.yaml`, `authority/works.yaml`, 설계 제안, 미생성)로 관리한다.
자동 병합은 하지 않는다 — 동명이인 오탐 위험 때문에 최종 확인은 항상 사람이 한다.

### 3.4 Duplicate Policy: 비파괴 원칙

5가지 중복 유형(Exact/Same Work Different Edition/Different Scan/Derivative
OCR/Supplement)을 정의하고, **어떤 경우에도 파일을 삭제하지 않는다** — 관계는
Authority Layer의 참조 필드(`aliases`/`related_work_id`/`derived_from`)로만 표현.
RAW immutable 원칙(`NAE_DATA_ARCHITECTURE.md`)과 정합.

### 3.5 Quality Gate: 3단계 판정

File/OCR/Metadata 3범주 검사 → PASS/WARNING/FAIL 판정. FAIL은 Registration으로
반려, WARNING은 사람 확인 후 진행. 구체적 임계값은 이번 ADR 범위 밖(후속 보정 필요).

### 3.6 TSU/Retrieval 정책은 ADR-014를 계승·구체화

Full/Restricted/Citation Only TSU 3단계와 Authority Weight 4단계 랭킹
(Primary Baptist > Historical > Modern Interpretation > Application Resource)은
ADR-014에서 이미 확정된 원칙을 이번 표준의 운영 규칙으로 구체화한 것이며, 새로운
결정이 아니다. `RetrievalEngine`(ADR-001) 코드는 변경하지 않는다.

**TSU 경로 충돌 방지(필수 조건)**: `NAE_DATA_ARCHITECTURE.md` §3에서 확인된
`DEFAULT_TSU_DATASET_PATH` 하드코딩 문제는 STEP4-D에서 `--dataset-path` CLI
인자 추가로 이미 해결되었다. Modern Corpus를 TSU화할 때 이 해결책이 재적용되지
않으면 `--output-dir`로 NAE registry를 가리켜도 TSU 산출물이 여전히 고정 경로
`output/bench/tsu_dataset.jsonl`에 쓰여 운영 TSU를 덮어쓸 위험이 있다. 따라서
Phase 8(TSU Integration Policy)의 모든 TSU 생성 호출은 **명시적 `--dataset-path`
지정을 필수 조건으로 한다** — 이 조건 없이는 TSU Pipeline 진행을 승인하지 않는다.

### 3.7 Dataset Isolation Rule (신규, NAE-METADATA-GOVERNANCE-REVISION-001 반영)

`--dataset-path` 필수 지정(§3.6)을 일반 원칙으로 확장한다.

1. **명시적 dataset path 사용** — NAE와 DBMA의 TSU Dataset은 항상 명시적 경로로
   지정한다. 어느 파이프라인도 기본값(implicit) 경로에 의존해 다른 파이프라인의
   산출물 위치를 추정하지 않는다.
2. **Implicit path inference 금지** — `--output-dir`이 가리키는 registry로부터
   TSU 산출 경로를 자동 추론하는 로직(§3.6에서 확인된 `DEFAULT_TSU_DATASET_PATH`
   하드코딩과 동일 부류의 위험)을 금지한다. 경로는 항상 호출 시점에 명시적으로
   전달되어야 한다.
3. **Pipeline별 dataset boundary 유지** — DBMA(`output/bench/tsu_dataset.jsonl`,
   `DEFAULT_TSU_DATASET_PATH`)와 NAE(`NAE/corpus/tsu/`, `nae_qdrant`/ADR-013)는
   서로 다른 dataset boundary를 가지며, 한쪽 파이프라인의 실행이 다른 쪽 경로에
   쓰기 작업을 일으켜서는 안 된다. NAE-MODERN이 추가되어도 이 경계는 그대로
   유지되며, modern 전용 TSU는 PD/DBMA와 별도 경로를 갖는다(예:
   `output/nae/bench/tsu_dataset_modern.jsonl` — 예시, 확정 경로는 구현 단계에서 결정).

목적: DBMA/NAE TSU 데이터셋 간 충돌 방지, dataset 오염(한 파이프라인의 산출물이
다른 파이프라인의 운영 데이터를 덮어쓰는 사고) 방지. 이 규칙은 §3.6 BLOCKER의
근본 원인(암묵적 경로 추론)에 대한 일반화된 예방 조치이며, §3.6의 예외가 아니다.

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| 자료 추가마다 개별 ADR 작성 | 목적(반복 Review 제거)과 정면 배치 — 이번 표준이 그 대안 자체 |
| Author/Work Authority를 별도 레지스트리 없이 manifest 필드만으로 관리 | 표기 변형 통합·판본 그룹핑을 조회할 canonical 소스가 없어, 매 등록 시 전체 manifest를 스캔해야 함 — 레지스트리 분리가 조회 비용을 낮춤 |
| 중복 자료를 발견 즉시 정리(구버전 스캔본 삭제 등) | RAW immutable 원칙 위반, 추후 더 나은 스캔본으로 대체 판단을 위한 근거 자료 유실 위험 |
| Quality Gate를 PASS/FAIL 2단계로 단순화 | WARNING 없이는 hOCR 누락 같은 경미한 결함도 전면 반려되어 등록 마찰이 커짐 — 3단계가 실무 유연성 확보 |

## 5. Consequences

- 신규 자료 등록은 이제 10단계 고정 Lifecycle을 따르며, 매번 Architecture Review를
  반복하지 않는다.
- `source_manifest.schema.yaml`은 v1.2/v2.0.0 두 버전이 계속 병행되고, 이번
  ADR로 3번째 스키마 버전이 생기지 않는다(Registration은 절차이지 스키마 교체가 아님).
- Authority 레지스트리(`authority/*.yaml`)는 설계만 되었고 실제 생성/구현은 후속
  작업 필요 — 그 전까지는 Author/Work 통합을 사람이 수동으로 확인해야 한다.
- Quality Gate 임계값(OCR 품질 점수 등)이 미정이므로, 실제 운영 착수 전 샘플
  데이터로 보정하는 후속 단계가 필요하다.
- ADR 번호 충돌 확인: 작성 시점 기준 001–014 존재, 015는 미사용 번호로 충돌 없음.
- **C1 Architecture Design Review-001 R6(BLOCKER) 대응 완료**: §3.6에 `--dataset-path`
  필수 조건 명시, §3.7에 Dataset Isolation Rule 일반화 — TSU Pipeline 진행을 막던
  BLOCKER는 문서 레벨에서 해소됨(실제 CLI 호출 시 조건 준수 여부는 구현 단계에서
  별도 검증 필요, 이번 ADR은 규칙만 확정).

## 6. Future Expansion

- `authority/authors.yaml`, `authority/works.yaml` 실제 생성 및 `scripts/source_validator.py`
  확장(Registration Schema 검증 포함)
- Duplicate Detection 자동화(해시 비교, 제목/저자 유사도) — Phase 10 후보
- Quality Gate 임계값 보정(실제 OCR 샘플 기반)
- TSU payload 저작권 필드(`tsu_access`/`citation_policy`/`source_restriction`) 구현 — ADR-014 Future Expansion과 동일 항목
- Retrieval Index 실제 통합 시 ADR-001/013 개정 ADR 별도 작성

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-015" docs/
```

## Promotion Review (NAE-ADR-PROMOTION-001, 2026-08-03) — 승격 보류

Evidence Before Promotion Rule(CLAUDE.md) 4조건 검토 결과 **1번 조건
미충족으로 Approved 승격 보류**:

1. **구현 완료** — **미충족**: Modern Corpus 실제 수집/ingestion
   파이프라인 코드가 아직 존재하지 않음(ADR-014 승격 보류와 동일 원인
   — ADR-015는 ADR-014 위에 세워진 표준이므로 선행 조건이 먼저 풀려야
   함)
2. 회귀/C1/사용자 승인 — 1번이 충족되지 않아 검토 보류

Status는 `Proposed`로 유지한다. ADR-014 구현·승격 이후 함께 재검토한다.
