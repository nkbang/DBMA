# NAE Authority Registry Design v1

작성일: 2026-08-02
Project: NAE-AUTHORITY-REGISTRY-BUILD-001
성격: Registry 구조 확립 — **전체 Corpus Metadata Migration 아님**
근거: [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §5,
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[`NAE_METADATA_PILOT_REPORT_001.md`](NAE_METADATA_PILOT_REPORT_001.md),
[`NAE_METADATA_PILOT_002_FULLER_REPORT.md`](NAE_METADATA_PILOT_002_FULLER_REPORT.md)

---

## Phase 1. Authority Registry 위치 결정

### 후보

1. **Pilot 데이터를 운영 registry로 승격(이동)** — `authority/pilot/*`를
   삭제하고 그 내용을 `authority/*.yaml`로 옮긴다.
2. **Pilot archive 유지 + Production registry 신규 생성(복사 승격)** —
   `authority/pilot/`은 검증 이력 그대로 보존하고, `authority/*.yaml`
   (이미 Schema Migration에서 빈 템플릿으로 생성됨)에 Pilot에서
   **검증된 값만 복사**해 운영 데이터로 채운다.

### 결정: **2안(복사 승격) 채택**

**근거**:
- `NAE_PILOT_MANIFEST_FIX_REPORT_001.md` 이후 이미 확립된 원칙 — Pilot
  기록 보존과 운영 위치는 구분한다(사용자 지시 재확인).
- `authority/pilot/`, `authority/pilot/fuller/`는 C1의
  [Review-002](NAE_METADATA_PILOT_REVIEW_002.md)가 이미 "검토 완료"로
  참조하고 있는 **검증 이력 문서**다 — 이동(삭제)하면 그 리뷰가 가리키는
  대상이 사라져 감사 추적성(traceability)이 끊긴다.
- RAW immutable 원칙(`NAE_DATA_ARCHITECTURE.md`)과 동일한 논리를
  metadata 검증 이력에도 적용하는 것이 일관적이다 — 한번 검증을 통과한
  기록은 보존하고, 운영 데이터는 그 기록에서 파생시킨다.
- 이동이 아니라 복사이므로 **손실 위험이 없다**(원본 유지) — 잘못
  승격해도 Pilot 원본에서 재작업 가능.

### 결과 구조

```
resources/theological_sources/authority/
├── authors.yaml     ← Production(이번 작업으로 Pilot 데이터 복사 승격)
├── works.yaml       ← Production
├── editions.yaml    ← Production
├── volumes.yaml      ← Production
├── sources.yaml      ← Production
├── manifest.yaml     ← Production(신규 — Registry 자체의 색인/메타, §Phase2.6 참고)
└── pilot/            ← 검증 이력 archive(변경 없음, 그대로 보존)
    ├── authors.yaml, works.yaml, editions.yaml, sources.yaml, source_manifest.yaml
    └── fuller/
        └── authors.yaml, works.yaml, editions.yaml, volumes.yaml, sources.yaml, source_manifest.yaml
```

---

## Phase 2. Registry Entity Schema 확정

아래 필드 정의가 **Production Registry(`authority/*.yaml`)의 정본**이다.
Pilot 단계(`authority/pilot/`)의 필드 구성과 이름이 다른 경우가 있는데
(예: Source의 `path` → `file_path`), 이는 Pilot이 탐색적으로 사용한
표기이고 이 문서가 확정하는 쪽이 우선한다 — Pilot 데이터 승격 시 이
문서 기준으로 필드명을 정규화한다(§Phase 3 매핑표 참고).

### 2.1 Author

```yaml
author_id: string        # required, canonical ID
canonical_name: string    # required
aliases: array[string]    # required(값이 없으면 빈 배열)
birth_year: integer|null  # required(값 모르면 null 명시 — 필드 자체는 존재)
death_year: integer|null  # required
tradition: string|null    # required
notes: string|null        # required
```

### 2.2 Work

```yaml
work_id: string            # required
author_id: string          # required, authors.yaml FK
canonical_title: string    # required — RAW title page 실측 우선(NAE_CORPUS_INGESTION_STANDARD_v1.md 제목 우선 원칙)
aliases: array[string]     # required(구 title_variants와 동일 개념, 필드명 통일)
work_type: string          # required — 예: monograph(단행본) | multi_volume(다권본) | periodical(정기간행물)
original_language: string  # required — 예: en
```

**변경 사항**: Pilot의 `title`/`title_variants`를 각각 `canonical_title`/
`aliases`로 필드명 통일(Author의 `aliases`와 명명 일관성), `work_type`/
`original_language` 신규 추가(Pilot에는 없던 필드 — Registry 승격 시
Fuller/Dagg/Hiscox 실제 값으로 채움, §Phase 3).

### 2.3 Edition

```yaml
edition_id: string           # required
work_id: string               # required, works.yaml FK
publication_year: integer|string  # required(다권본 범위 표기 가능, 예: "1824-1825")
publisher: string             # required
publication_place: string     # required — Pilot의 `place`에서 필드명 통일
edition_notes: string|null    # required
```

### 2.4 Volume (조건부 Entity — 다권본만 사용)

```yaml
volume_id: string        # required
edition_id: string        # required, editions.yaml FK
volume_number: integer    # required
volume_title: string      # required
```

단권 자료(Dagg, Hiscox)는 Volume entity를 생성하지 않는다 — Source가
Edition에 직접 연결된다(GOVERNANCE §5.1 "단권 자료는 이 계층을 생략").

### 2.5 Source

```yaml
source_id: string           # required
volume_id: string|null       # required(다권본만 값 존재, 단권은 null)
edition_id: string           # required — volume_id가 없어도 이 필드로 항상 Edition에 연결(단권/다권 공통 경로)
file_path: string            # required — Pilot의 `path`에서 필드명 통일
source_type: string          # required, 값 체계: NAE_METADATA_GOVERNANCE_v1.md §4.4
copyright_status: string     # required, §4.1
usage_permission: string     # required, §4.2
access_control: string       # required, §4.3
```

**의도적 축소**: 이 Registry Source entity는 corpus manifest
(`source_manifest.yaml`)의 `citation_policy`/`tsu_access`/`archive_source`
등을 포함하지 않는다 — 그 필드들은 manifest(TSU/검색 파이프라인이 직접
소비하는 레이어)의 책임이고, Registry Source는 **Authority 계층 간 연결
정보(FK)와 governance 4필드만**을 다룬다(역할 분리, §Phase 6 참고). 두
데이터가 같은 `source_id`로 연결되므로 중복이 아니라 관점이 다른
투영(projection)이다.

### 2.6 manifest.yaml (Registry 색인, 신규)

corpus manifest(`source_manifest.yaml`)와 이름이 비슷해 혼동 우려가
있어 명확히 구분: 이 파일은 **Registry 자체의 메타데이터**(버전, 최종
갱신일, entity 개수 요약)만 담는다 — 개별 저작 데이터는 담지 않는다.

```yaml
registry_version: string     # 이 registry 구조 자체의 버전(entity schema 버전, §Phase2 changelog)
last_updated: string          # ISO 날짜
promoted_from: array[string]  # 이번 승격에 사용된 pilot 소스 경로
entity_counts:
  authors: integer
  works: integer
  editions: integer
  volumes: integer
  sources: integer
```

---

## Phase 3. Pilot Data 승격 매핑

| Pilot 필드 | Production 필드 | 변환 |
|---|---|---|
| `works.yaml.title` | `works.yaml.canonical_title` | 이름만 변경, 값 동일 |
| `works.yaml.title_variants` | `works.yaml.aliases` | 이름만 변경, 값 동일 |
| `editions.yaml.place` | `editions.yaml.publication_place` | 이름만 변경, 값 동일 |
| `sources.yaml.path` | `sources.yaml.file_path` | 이름만 변경, 값 동일 |
| (신규) `works.yaml.work_type` | — | Dagg/Hiscox: `monograph`, Fuller: `multi_volume` — RAW 실측(각 1개 work, 8권 vs 1권)에 근거해 채움 |
| (신규) `works.yaml.original_language` | — | 전부 `en`(RAW 원문이 영어) |
| `authors.yaml.domain` | (삭제) | Pilot에서 시험적으로 추가했던 필드 — Production 스키마(§2.1)에 없어 승격 시 제외(정보 손실 없음, `tradition`으로 충분히 구분 가능) |

승격 대상: Pilot-001(Dagg, Hiscox) + Pilot-002(Fuller, 8 source, 2
edition, 1 work, 1 author) — **총 3 author, 3 work, 4 edition, 8
volume, 10 source**. 실제 파일은
[`NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md`](NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md) §3에 검증 결과와 함께 기록.

---

## Phase 5(설계). Registry Validation Tool 요구사항

코드 구현 없이 요구사항만 정의(향후 별도 승인 후 구현).

### 검증 범주

| 범주 | 항목 |
|---|---|
| Reference | `works[].author_id` → `authors` 존재 / `editions[].work_id` → `works` 존재 / `volumes[].edition_id` → `editions` 존재 / `sources[].edition_id` → `editions` 존재 / `sources[].volume_id`(값 있을 때만) → `volumes` 존재 |
| Duplicate | 동일 `*_id` 중복(각 entity 파일 내 유일성) / 동일 `canonical_title`+`author_id` 조합 중복(같은 저작 이중 등록 의심) / 동일 `edition_id`가 서로 다른 `work_id`에 걸쳐 나타남(모델 위반) |
| Schema | 각 entity의 §Phase 2 필수 필드 존재 / `source_type`/`copyright_status`/`usage_permission`/`access_control` enum 값 유효성(GOVERNANCE §4 재사용) / `registry_version`이 인식 가능한 값인지 |

### 출력

기존 `source_validator.py`와 동일한 3단계 텍스트 출력 관례를 따른다
(`PASS`/`WARNING`/`FAIL` + 요약 카운트) — 도구 간 사용자 경험 일관성.

### 구현 방식(제안, 미구현)

`scripts/authority_validator.py`(가칭)로 `source_validator.py`와
**별도 파일**로 구현할 것을 권고 — 두 도구는 검증 대상(manifest vs
registry)이 다르므로 하나로 합치면 책임이 섞인다(§Phase 6).

---

## Phase 4(설계). ID Governance 규칙 재확인

Pilot 단계에서 이미 확립된 규칙을 Production Registry에도 그대로
적용(변경 없음, 재확인만):

- **author_id 동명이인**: 정규화 비교(소문자, 공백/구두점 제거) 후
  불일치 시 사람이 확인 — 예로 든 `john_dagg`/`john_a_dagg`처럼 slug가
  다르면 애초에 자동 병합 대상이 아니고, 사람이 "동일 인물인지"를 먼저
  판단해야 함(자동 병합 금지 원칙, GOVERNANCE §1 Philosophy #3).
- **work_id 동일 제목 충돌**: `canonical_title`이 같아도 `author_id`가
  다르면 별도 work — 충돌은 `author_id`+`canonical_title` 조합이 완전히
  같을 때만 성립(§Phase 5 Duplicate 검사 대상).
- **edition_id 다중 지원**: 이미 Fuller 사례로 실증됨(Work:Edition=1:N).
- **volume_id 번호 중복**: 동일 `edition_id` 내에서 `volume_number`
  유일성 검사 필요(Registry Validation Tool 검사 항목에 추가 권고 —
  §Phase5 표에는 명시적으로 없었으나 실무상 필요, Remaining Risk로 기록).

이번 승격 대상(3 author, 3 work, 4 edition, 8 volume, 10 source)에는
실제 충돌 사례가 없음 — 확인 결과는 Build Report §4 참고.
