---
title: "ADR-014: NAE Modern Corpus Layer (Design Only)"
category: architecture
based_on:
  - docs/NAE_DATA_ARCHITECTURE.md
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md
  - docs/architecture/ADR-013-NAE-Vector-Store.md
created: 2026-08-02
scope_modified: docs/ only — 디렉토리 생성, 데이터 확보, TSU/Embedding/Retrieval 코드 변경 없음
partially_extended_by: docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md (2026-08-02 — Volume entity, source_type 값 추가 등. 본문은 소급 수정하지 않음, GOVERNANCE §7.5 원칙)
---

# ADR-014: NAE Modern Corpus Layer (Design Only)

| | |
|---|---|
| Status | Proposed |
| Date | 2026-08-02 |
| Deciders | 사용자 승인 대기 (설계 문서 단계) |
| Supersedes | — |
| Superseded by | — |

---

## 1. Context

NAE Public Domain Corpus(`NAE/corpus/raw/archive_org/`, `resources/theological_sources/baptist/`)는
구축이 완료되어 있다 — John Gill, Boyce, Dagg, Carroll, Strong, Mullins, Broadus,
Robertson, Spurgeon 등 저작권 만료 자료 중심.

설교 준비·신학 연구에는 현대(저작권 유효) 신학·목회 자료가 추가로 필요하지만,
NAE-PD는 저작권 만료 자료만을 전제로 설계되어 있어(`source_manifest.schema.yaml`의
`license` 필드가 `public_domain*` 값 체계 중심) 저작권 제한 자료를 그대로
얹으면 다음 위험이 발생한다.

- 저작권 상태가 다른 자료가 동일 authority/weight로 검색되어 인용 오남용 위험
- DBMA(개인 목회 자료)·NAE-PD(공개 원전)·현대 자료가 한 트리에 섞여
  출처 추적성이 무너짐 (CLAUDE.md "작업은 반드시 추적 가능해야 한다" 원칙 위반)
- `resources/theological_sources/`의 기존 manifest 스키마(schema_version 1.2)가
  저작권 거버넌스 필드를 갖고 있지 않음

## 2. Problem

현대 신학·목회 자료를 NAE-PD 구조를 깨지 않고, DBMA 개인 자료와도 섞이지 않게,
저작권 상태를 추적 가능한 형태로 추가하려면 어떤 구조가 필요한가?

## 3. Decision

### 3.1 세 영역 분리 유지

```
NAE-PD (Public Domain Corpus)      — 변경 없음
NAE-MODERN (Modern Research Layer) — 신설, 별도 Architecture Track
DBMA (Personal Ministry Archive)   — 변경 없음
```

### 3.2 디렉토리 (제안, 미생성)

```
NAE/corpus/raw/
├── public_domain/   (기존 archive_org/ 의미상 재분류 — 실제 rename은 별도 승인 필요)
└── modern/
    ├── theology/ commentary/ sermons/ missions/ ministry/ apologetics/ reference/
```

### 3.3 Source Governance

4개 신규 필드(`source_type`, `copyright_status`, `usage_permission`, `access_control`)를
기존 `source_manifest.schema.yaml`에 **추가** 필드로 병행 도입한다(기존 필드 재작성 없음).
`access_control=no_redistribution` 자료는 기본적으로 `metadata_only`로만 관리한다.

### 3.4 Metadata Schema

기존 스키마(schema_version 1.2)를 계승하는 `schema_version: "2.0.0"`을
modern 전용 manifest에 적용한다 — `author_id`/`work_id`/`edition`/`publisher`/
`language`/`theological_position`/`denomination`/`scripture_reference` 등 신규
필드 추가, `status` enum과 `source_id` 유일성 규칙은 그대로 재사용.

전체 필드 정의는 [`docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`](../NAE_MODERN_CORPUS_ARCHITECTURE_v1.md) Task 3 참고.

### 3.5 Retrieval / TSU 영향 (설계만, 미구현)

- Retrieval: NAE-PD를 1차 사료로 최우선 authority 유지, NAE-MODERN은 별도
  가중치의 보조 트랙 — `core/retrieval.py::RetrievalEngine` 코드 변경 없음
  (ADR-001/ADR-013 범위 유지).
- TSU: 동일 `TSU_SCHEMA_VERSION` 체계 재사용 가능. 단 TSU payload에 저작권
  거버넌스 필드 전파 필요 및 `metadata_only`/`citation_only` 자료를 위한
  "citation-only TSU" 서브타입 필요 — 둘 다 요구사항 식별만, 구현은 후속 ADR.
- 경로 충돌 주의: `docs/NAE_DATA_ARCHITECTURE.md` §3의 `DEFAULT_TSU_DATASET_PATH`
  하드코딩 이슈(해결됨, `--dataset-path` 옵션)와 동일 패턴이 modern TSU 산출
  시 재발하지 않도록 명시적 `--dataset-path` 사용을 후속 구현 시 강제한다.

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| NAE-PD 트리에 저작권 필드만 추가하고 디렉토리는 통합 | 폴더 레벨에서 PD/저작권 자료가 섞여, 실수로 `access_control` 필터를 거치지 않고 원문이 노출될 위험이 구조적으로 남음 |
| DBMA 개인 자료 트리에 현대 신학 자료 편입 | CLAUDE.md의 DBMA=개인 목회 자료 정의와 충돌, [[project_brand_freeze_nae]] 원칙(NAE/DBMA 역할 분리 동결)과도 배치 |
| 저작권 자료 전체를 metadata_only로 강제(원문 저장 자체 금지) | 정당하게 라이선스 확보한(`licensed`/`purchased`) 자료까지 과잉 제한 — governance 필드로 세분화하는 편이 유연 |

## 5. Consequences

- NAE-PD 기존 구조(스키마·경로·검증 스크립트)는 변경되지 않는다.
- `resources/theological_sources/`는 NAE-PD(schema 1.2)와 NAE-MODERN(schema
  2.0.0) manifest가 별도 스키마 버전으로 공존한다 — `scripts/source_validator.py`가
  두 버전을 모두 검증하도록 확장하는 작업이 후속 필요(미구현).
- Retrieval 통합(세 영역을 단일 질의로 검색)은 이번 ADR 범위 밖이며, 착수 시
  ADR-001/ADR-013을 개정하는 별도 ADR이 필요하다.
- 기존 NAE-PD 로드맵(Corpus Collection → Audit → Metadata → TSU → Embedding →
  Benchmark)은 그대로 진행하며, 이 ADR로 인해 지연되지 않는다.
- ADR 번호 충돌 확인: 작성 시점 기준 `docs/architecture/`에 001–013 존재, 014는
  미사용 번호로 충돌 없음.

## 6. Future Expansion

- `scripts/source_validator.py`의 modern manifest(schema 2.0) 검증 지원
- TSU payload 저작권 필드 확장 + citation-only TSU 서브타입 구현
- 저자 신뢰도/`theological_position` 기반 가변 가중치 스코어 체계 설계
- NAE-PD/NAE-MODERN/DBMA 통합 검색이 필요해질 경우 별도 ADR로 RetrievalEngine 확장 검토
- `NAE/corpus/raw/archive_org/` → `public_domain/` 실제 rename은 별도 승인 건으로 분리 처리

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-014" docs/  # 상호 참조 확인
```
