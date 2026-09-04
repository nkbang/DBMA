# NAE Metadata & Authority Implementation Plan 001

작성일: 2026-08-02
Project: NAE-METADATA-AUTHORITY-IMPLEMENTATION-PLAN-001
담당: CUE
성격: **설계 → 구현 계획 변환** — 실행 계획서이며 실행 그 자체가 아니다.
근거: [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md),
[`NAE_CORPUS_INGESTION_STANDARD_v1.md`](NAE_CORPUS_INGESTION_STANDARD_v1.md),
[ADR-014](architecture/ADR-014-NAE-Modern-Corpus-Layer.md),
[ADR-015](architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md)

**이번 문서에서 하지 않는 것** (명령서 명시): 실제 metadata 생성, 기존 자료
(약 875개) 변환, TSU 생성. 아래는 전부 "어떻게 할 것인가"의 설계이며,
"지금 실행한다"가 아니다.

---

## 0. 전제 확인

기존 corpus 규모(참고용 실측치, 이번 계획의 대상 모수):

| 위치 | 항목 수 | 근거 |
|---|---|---|
| `NAE/corpus/raw/archive_org/` 하위 work 디렉토리 | 194개 | `find -mindepth 2 -maxdepth 2 -type d` |
| `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | 25 row(헤더 제외) | 현재 CSV 등록분 |
| `resources/theological_sources/baptist/source_manifest.yaml` | 1개 파일(다건 포함) | v1.2 canonical manifest |

명령서가 언급한 "875개 자료"는 work 단위가 아닌 파일 단위(PDF+TXT+…) 집계로
추정된다(C1 Audit-002 기준 history/missions/church_order만으로 이미 ~1,534개
파일). 이 계획은 work/edition/source 3단 중 **어느 단위를 변환 대상으로 셀지도
Phase 1에서 먼저 확정**해야 함을 전제로 한다 — 정확한 모수 확정은 구현 착수
직전 재실측 필요.

---

## 1. Directory 구조

### 1.1 신규 디렉토리 (실행 시점에 생성 — 이번 계획 문서는 생성하지 않음)

```
resources/theological_sources/
├── baptist/                      ← 기존 v1.2, 변경 없음
│   ├── source_manifest.yaml
│   └── source_candidates.csv
├── modern/                       ← 신규 (ADR-014 Task 1)
│   ├── theology/source_manifest.yaml
│   ├── commentary/source_manifest.yaml
│   ├── sermons/source_manifest.yaml
│   ├── missions/source_manifest.yaml
│   ├── ministry/source_manifest.yaml
│   ├── apologetics/source_manifest.yaml
│   └── reference/source_manifest.yaml
└── authority/                    ← 신규 (Authority Registry, §3)
    ├── authors.yaml
    └── works.yaml                ← Edition/Source File 중첩 포함
```

- `NAE/corpus/raw/`(실물 RAW)는 이번 계획에서 **건드리지 않는다** — Directory
  rename도 금지 사항이므로 `archive_org/` → `public_domain/` 재명명은 별도
  승인 건으로 계속 분리 유지(ADR-014 Future Expansion과 동일 결정 재확인).
- `authority/`는 `resources/theological_sources/` 바로 하위에 둔다 — manifest와
  같은 트리에 있어야 상대경로 참조(`work_id`/`edition_id` 룩업)가 스크립트에서
  간단해진다. `NAE/` 하위가 아니라 `resources/` 하위인 이유: git 추적 대상이
  전자(`resources/`)이고, `NAE/`는 대용량 RAW/산출물 중심으로 이미 관례가
  다르다(`docs/NAE_DATA_ARCHITECTURE.md` §"핵심 구분" 원칙 계승).

### 1.2 생성 순서 (실행 시)

1. `resources/theological_sources/authority/` (빈 registry, §3 형식)
2. `resources/theological_sources/modern/{7개 카테고리}/` (빈 manifest, §2 스키마 골격만)
3. 기존 `baptist/`는 그대로 — 디렉토리 신설 없음, 파일 내용만 점진적으로 보강(§5)

---

## 2. Schema 파일 위치

| 스키마 | 위치 | 상태 |
|---|---|---|
| v1.2 (NAE-PD) | `resources/theological_sources/source_manifest.schema.yaml` | 기존, 변경 없음 |
| v2.0.0 (NAE-MODERN) | `resources/theological_sources/modern/source_manifest.schema.yaml` (신규 파일) | 이번 계획에서 **작성 계획만**, 실제 파일 생성은 실행 단계 |
| 값 체계 정본 | `docs/NAE_METADATA_GOVERNANCE_v1.md` §3/§4 | 이미 존재(전 단계 완료) — 스키마 파일은 이 문서의 값을 YAML enum으로 옮기기만 함 |

v2.0.0 스키마 파일은 v1.2 파일(`source_manifest.schema.yaml`)과 **같은
포맷**(fields/required/description 구조)을 따르되, 다음을 추가한다:

```yaml
# resources/theological_sources/modern/source_manifest.schema.yaml (실행 시 작성 예정, 골격만 여기 제시)
schema_version: "2.0.0"
extends: "../source_manifest.schema.yaml"   # v1.2 필드 상속 표시(문서 관례, 검증기가 실제로 두 파일을 병합하지는 않음 — Phase 4 검증기 확장 시 결정)
fields:
  # v1.2 공통 필드(source_id, title, status 등)는 표기만 하고 재정의하지 않음
  author_id: {type: string, required: true}
  work_id: {type: string, required: true}
  edition_id: {type: string, required: false}   # NAE_METADATA_GOVERNANCE_v1.md §5.1
  copyright_status: {type: enum, values: [public_domain, copyrighted, licensed, unknown]}   # §4.1
  usage_permission: {type: enum, values: [research, citation_only, internal_use, no_redistribution]}  # §4.2
  access_control: {type: enum, values: [public, restricted, private]}   # §4.3
  license:
    type: object
    fields: {source_value: string, normalized_value: string}   # §3
  # ... (나머지 필드는 NAE_MODERN_CORPUS_ARCHITECTURE_v1.md Task 3 전체 목록 참고)
```

`extends` 키는 이번 계획에서 **표기 관례로만 제안**하며, `source_validator.py`가
이를 실제로 해석하도록 구현할지는 Phase 4(검증기 확장)에서 별도 결정한다 —
스키마 문서 자체는 이번 계획 산출물이 아니라 실행 단계 첫 산출물이다.

---

## 3. Authority Registry 형식

### 3.1 파일 분리 이유

`authors.yaml`과 `works.yaml`(Edition/Source File 포함)을 분리한다 — Author는
Work보다 변경 빈도가 낮고(신규 저자 등록은 드묾), Work/Edition은 자료 유입마다
빈번히 갱신되므로 diff 가독성과 git blame 추적성을 위해 분리.

```yaml
# resources/theological_sources/authority/authors.yaml (실행 시 생성 예정)
schema_version: "1.0"
authors:
  - author_id: gill_john
    canonical_name: "John Gill"
    aliases: ["John_Gill", "Gill, John", "J. Gill"]
    domain: baptist   # NAE-PD/NAE-MODERN 구분(선택 필드, 검색 필터용)
```

```yaml
# resources/theological_sources/authority/works.yaml (실행 시 생성 예정)
schema_version: "1.0"
works:
  - work_id: gill_john-body_of_doctrinal_divinity
    author_id: gill_john              # authors.yaml 참조 키
    canonical_title: "A Body of Doctrinal Divinity"
    editions:
      - edition_id: gill_john-body_of_doctrinal_divinity-1810
        edition: "1810"
        preferred: false
        source_ids: [baptist-theology-014]   # source_manifest.yaml의 source_id 참조
      - edition_id: gill_john-body_of_doctrinal_divinity-1839
        edition: "1839"
        preferred: true
        source_ids: [baptist-theology-015]
```

### 3.2 참조 방향

```
authority/works.yaml (edition.source_ids)  ──→  resources/theological_sources/{domain}/source_manifest.yaml (source_id)
authority/works.yaml (work.author_id)      ──→  authority/authors.yaml (author_id)
```

Registry는 manifest를 **참조만** 하고 manifest 내용을 복제하지 않는다 — 이중
관리(entry가 두 곳에서 어긋나는 사고) 방지. `source_id`가 manifest에서
삭제/변경되면 registry의 참조가 끊어지므로, Phase 4 검증기에 **참조 무결성
검사**(orphan reference 탐지)를 추가 항목으로 포함한다(§4).

### 3.3 신규 필드 요건 재확인

`author_id`/`work_id`/`edition_id` 생성 규칙은 `NAE_CORPUS_INGESTION_STANDARD_v1.md`
Phase 3 "ID 생성 규칙"을 그대로 사용 — 이번 계획에서 규칙을 새로 만들지 않는다.

---

## 4. Existing Corpus Mapping 방법

기존 NAE-PD 자료(194개 work, `NAE_SOURCE_MANIFEST_v1.csv` 25행 + 각
`source_manifest.yaml` entry)를 신규 Authority Layer로 **소급 매핑**하는 절차.

### 4.1 매핑 파이프라인 (설계, 미실행)

```
1. Source 수집   — 기존 source_manifest.yaml의 모든 entry(author 문자열, title, source_id) 추출
2. Author 정규화 — author 문자열을 정규화(소문자, 공백/구두점 제거)하여 그룹핑
                   → 그룹별로 author_id 후보 생성(예: "Gill, John"/"John Gill" → gill_john)
3. 사람 확인     — 그룹핑 결과를 사람이 검토(동명이인 오탐 여부, §5 Authority Model 원칙)
                   → 확정된 그룹만 authors.yaml에 등재
4. Work 그룹핑   — 동일 author_id 내에서 title 유사도(정확 일치 우선, 유사도 매칭은 후보 제시만)로
                   Work 후보 그룹핑 → 사람 확인 → works.yaml에 work_id 등재
5. Edition 분리  — Work 그룹 내에서 연도/판본 표기(파일명의 연도, source_manifest의 year)로
                   edition 후보 분리 → edition_id 부여
6. Source 연결   — 각 source_id를 해당 edition_id의 source_ids 배열에 연결
7. 검증          — Phase 4 검증기로 참조 무결성 확인(모든 source_id가 실제 manifest에 존재하는지)
```

3, 4단계는 **자동 병합 금지 원칙**(NAE_METADATA_GOVERNANCE_v1.md §5.2) 때문에
반드시 사람 확인을 거친다 — 2/5단계는 후보 생성까지만 자동화 가능.

### 4.2 매핑 우선순위 (Migration §7.2 Step 3과 연결)

| 순서 | 대상 | 사유 |
|---|---|---|
| 1 | 저자가 이미 명확히 식별된 소규모 카테고리(church_order, 2 work) | 검증 비용 최소, 파일럿으로 절차 검증 가능 |
| 2 | 다권본 저작(Fuller 8권, Cathcart 2권 등) | Edition/Work 구분 로직을 가장 잘 검증할 수 있는 케이스(C1 Audit-002에서 이미 식별됨) |
| 3 | 단권 저작 대다수 | 표준 절차 반복 적용 |
| 4 | `early_baptist_collection`(1,416파일, 34GB) | 규모가 커 별도 sub-plan 필요 — 이번 계획에서는 "나중에" 표시만, 세부 설계는 범위 밖 |

### 4.3 Modern 자료 매핑

Modern 자료는 신규 등록이므로 소급 매핑이 아니라 Registration 시점(Phase 2
Corpus Ingestion Lifecycle)에 바로 author_id/work_id/edition_id를 부여한다 —
기존 corpus 매핑과 다른 절차임을 명확히 구분.

---

## 5. Migration 순서

`NAE_METADATA_GOVERNANCE_v1.md` §7.2의 4-Step을 이번 문서의 §1~§4와 연결해
구체화한다(순서 자체는 변경하지 않음, 각 Step에 산출물/전제조건 추가):

| Step | 내용 | 전제조건 | 산출물 | 검증 |
|---|---|---|---|---|
| 1 | v1.2 entry에 `copyright_status`(파생) 필드 추가 | 없음(즉시 시작 가능) | `license.source_value/normalized_value` 매핑표 적용된 v1.2 entry | 매핑표(§4.1 GOVERNANCE) 커버리지 100% 확인 |
| 2 | Modern 신규 등록분에 schema v2.0.0 전체 필드 적용 | §1(Directory), §2(Schema 파일) 완료 | `modern/{category}/source_manifest.yaml` 신규 entry | Phase 4 검증기 PASS |
| 3 | NAE-PD 기존 entry에 author_id/work_id/edition_id 소급 부여 | §3(Registry), §4(Mapping) 완료, 파일럿(§4.2 순서 1) 검증 통과 | `authority/authors.yaml`, `authority/works.yaml` | 참조 무결성 검사(모든 source_ids가 실재 source_id와 일치) |
| 4 | `source_validator.py` 확장 | Step 1~3 스키마/값 체계가 안정화된 후 | 확장된 validator 코드 + 회귀 테스트 | 기존 v1.2 검증 통과 유지 + 신규 필드 검증 통과 |

Step 1, 2는 서로 독립(병렬 가능). Step 3은 Step 1의 `copyright_status`
매핑이 선행되어야 저작권 확인 없이 Authority만 먼저 만드는 상황을 피할 수
있다(§1 Philosophy #4 — 저작권 미확정 자료는 진행 보류 원칙과 일관).
Step 4는 Step 1~3에서 실제 사용해본 필드/값만 검증 대상으로 확정하는 것이
안전하므로 마지막에 둔다.

---

## 6. Rollback 방법

### 6.1 원칙

모든 신규 파일(스키마/Registry)은 **기존 v1.2 파일과 물리적으로 분리**되어
있으므로(§1 Directory 구조), rollback은 신규 파일 삭제만으로 충분하고 v1.2
데이터에 영향이 없다 — RAW immutable 원칙과 동일한 논리를 metadata 레벨에
적용.

### 6.2 Step별 Rollback

| Step | Rollback 방법 |
|---|---|
| 1 | v1.2 manifest entry에서 `copyright_status` 필드(파생값)만 제거 — `license` 원본 필드는 애초에 손대지 않았으므로 원상복구 즉시 완료 |
| 2 | `modern/{category}/source_manifest.yaml` 삭제 — NAE-PD(v1.2)에는 영향 없음(별도 디렉토리) |
| 3 | `authority/authors.yaml`, `authority/works.yaml` 삭제 — manifest는 참조만 당하는 쪽이므로 registry 삭제가 manifest entry를 손상시키지 않음(§3.2 참조 방향이 단방향이기 때문) |
| 4 | `source_validator.py` 확장분을 git revert — 기존 v1.2 검증 로직은 별도 함수/분기로 추가하는 것을 권장(기존 로직 수정이 아니라 병렬 추가)하여 revert 시 v1.2 검증 경로가 그대로 남도록 함 |

### 6.3 Git 기준 Rollback

각 Step은 독립 커밋 단위로 진행할 것을 권장(Step 1 커밋 → Step 2 커밋 → …) —
특정 Step에서 문제가 발견되면 해당 커밋만 `git revert`하고 이후 Step은
재작업. RAW 파일이 어느 Step에도 관여하지 않으므로 데이터 손실 위험이 있는
rollback은 이 계획에 존재하지 않는다(구조적으로 metadata-only 변경이기 때문).

---

## 완료 조건 자가 점검

이번 계획이 다음 실행 질문에 답할 수 있는가:

1. **파일을 어디에 만드는가** → §1 Directory 구조로 확정.
2. **스키마는 어떤 형식인가** → §2, v1.2 포맷 계승 + 값 체계는 GOVERNANCE 문서 참조.
3. **Authority는 어떤 형식이고 어떻게 참조되는가** → §3, authors.yaml/works.yaml 분리 + 단방향 참조.
4. **기존 875개(추정) 자료를 어떤 순서로, 누가 확인하며 매핑하는가** → §4, 7단계 파이프라인 + 우선순위 4단계.
5. **Migration은 어떤 순서로 진행되고 각 Step의 전제조건은 무엇인가** → §5, Step 1~4 표.
6. **문제가 생기면 어떻게 되돌리는가** → §6, Step별 rollback + 물리적 분리 원칙에 근거한 낮은 위험도.

**실행 여부는 이 문서로 결정되지 않는다** — 실제 metadata 생성/875개 자료
변환/TSU 생성은 이번 계획의 승인과 별개로 추가 승인이 필요하다.
