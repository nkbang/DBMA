# NAE Metadata Governance v1 (Design Only)

작성일: 2026-08-02
상태: 설계 단계 — 미구현 (Corpus/RAW 변경, Directory rename, Metadata 실제 생성,
Authority 파일 생성, TSU/Embedding 생성, Retrieval/Pipeline 코드 변경 없음)
근거: C1 [`NAE_ARCHITECTURE_DESIGN_REVIEW_001.md`](NAE_ARCHITECTURE_DESIGN_REVIEW_001.md),
[`NAE_CORPUS_INGESTION_STANDARD_v1.md`](NAE_CORPUS_INGESTION_STANDARD_v1.md),
[ADR-015](architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md),
[`NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`](NAE_MODERN_CORPUS_ARCHITECTURE_v1.md),
[ADR-014](architecture/ADR-014-NAE-Modern-Corpus-Layer.md)

이 문서는 NAE Metadata 관련 **License/Copyright/Usage Permission/Access
Control/Source Type 값 체계와 Authority Model의 유일한 정본(single source of
truth)**이다. ADR-014/`NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`에 있던 초기 값
목록은 이 문서 발행 이후 이 문서의 값으로 대체된다(해당 원문은 소급 수정하지
않음 — §7 참고).

**개정 이력**: 2026-08-02 NAE-METADATA-ARCHITECTURE-REVISION-001 — Pilot-001/
Pilot-002 실증 결과 반영(`schema_version` 2.0.0 → 2.1.0, Minor). 상세는
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md) 및
[`NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md`](NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md) 참고.

---

## 1. Metadata Philosophy

1. **원본 표기는 보존, 정규화는 파생값으로** — 자료가 어디서 왔든(Archive.org,
   출판사, 개인 스캔) 원본이 제공한 표기(`license`의 source_value 등)는 그대로
   보존하고, DBMA/NAE 내부에서 사용할 정규화된 값(`copyright_status` 등)은
   그로부터 파생시킨 **별도 필드**로 둔다. 원본 재작성 금지 원칙(RAW immutable,
   `NAE_DATA_ARCHITECTURE.md`)을 메타데이터 레벨로 확장한 것이다.
2. **스키마는 추가만, 재작성은 하지 않는다** — 기존 `source_manifest.schema.yaml`
   v1.2 필드는 유지하고, 새 필드는 병행 도입한다(§7 Migration Policy).
3. **Authority는 사람이 최종 승인** — 저자/저작/판본 통합은 자동 병합하지 않는다.
   동명이인·오귀속 오류가 검색 신뢰도를 직접 훼손하기 때문이다.
4. **저작권 정보 없이는 TSU 없다** — `copyright_status`가 확정되지 않은
   (`unknown`) 자료는 Full TSU로 진행하지 않는다(§6).
5. **한 파이프라인으로 반복 처리 가능해야 한다** — 신규 자료마다 이 문서를
   다시 쓰지 않고, 값 체계·Authority 모델·TSU 요건이 고정된 규칙으로 적용된다
   (NAE-CORPUS-INGESTION-STANDARD-DESIGN-001의 원래 목적 계승).

---

## 2. Schema Version Policy

### 2.1 현재 버전

```
source_manifest.schema.yaml: 1.2   (NAE-PD, 변경 없음)
Modern manifest schema:      2.1.0 (NAE-MODERN, 이 문서가 값 정본 — 2026-08-02 개정)
```

### 2.2 Semantic Versioning 채택 사유

C1 Review R3(WARNING) — `2.0-modern`이라는 표기가 SemVer(`MAJOR.MINOR.PATCH`)와
충돌 가능하다는 지적에 따라 `2.0.0`으로 정정(이미 ADR-014/ADR-015/
NAE_MODERN_CORPUS_ARCHITECTURE_v1.md/NAE_CORPUS_INGESTION_STANDARD_v1.md
4개 문서에 반영됨). 이후 버전 증가 규칙:

| 구분 | 조건 | 예 |
|---|---|---|
| **Major** | 구조 변경 — 필드 제거, 필드 의미 변경, entity 계층 변경(예: Edition을 신규 entity로 승격) | `2.0.0` → `3.0.0` |
| **Minor** | 필드 추가(하위 호환, 기존 데이터 무효화 없음) | `2.0.0` → `2.1.0` |
| **Patch** | 오류 수정(값 enum의 오탈자 수정, 문서 정정 등 — 데이터 구조 변경 없음) | `2.0.0` → `2.0.1` |

이번 개정(NAE-METADATA-GOVERNANCE-REVISION-001)에서 `copyright_status`/
`usage_permission`/`access_control`의 **값 목록 자체가 바뀌었다**(§4). 이는
아직 실제 데이터가 없는 설계 단계의 정정이므로 `2.0.0` 유지 — 만약 이 스키마로
실제 데이터가 이미 생성된 뒤 값 체계를 바꿨다면 Major bump(`3.0.0`) 대상이었을
것이다. **원칙**: 설계 단계 정정은 버전을 올리지 않되, 승인·데이터 생성 이후의
구조 변경은 반드시 Major bump로 기록한다.

**2026-08-02 개정(NAE-METADATA-ARCHITECTURE-REVISION-001, `2.0.0`→`2.1.0`)**:
Pilot-001/002에서 실증된 두 변경을 반영 — (1) `source_type` enum에
`public_archive` 값 추가(§4.4, 기존 값 무효화 없음), (2) `volume_id`/
`volume_number` 선택 필드 추가(§5.1, 기존 단권 자료의 필드 구성은 변경 없이
그대로 유효). 둘 다 **기존 데이터를 무효화하지 않는 추가 변경**이므로 Minor
bump(`2.1.0`)로 기록 — 이 스키마는 아직 실제 데이터가 없는 설계 단계이므로
Major bump 없이도 정정 가능하다는 원칙(위 문단)과 일관된 적용이다. 이번
개정으로도 여전히 실제 데이터는 생성되지 않은 상태이므로, 다음 개정도 계속
Minor/Patch 범위 안에서 이뤄질 수 있다 — 실제 Migration(Corpus-wide Metadata
Build)이 시작된 이후에는 이 완화된 기준이 더 이상 적용되지 않는다.

---

## 3. License Policy

### License Rule: source_value / normalized_value 분리

```yaml
license:
  source_value: string        # 원본 출처가 제공한 원문 표기 그대로 보존
  normalized_value: string    # §4 copyright_status 값 체계로 정규화된 값
```

매핑 흐름:

```
Archive.org metadata (licenseurl, rights 등 원문 필드)
        ↓  (source_value로 그대로 저장)
license.source_value
        ↓  (정규화 규칙 적용)
license.normalized_value  ==  copyright_status (§4)
```

- NAE-PD 기존 `source_manifest.schema.yaml`의 `license` 필드(`public_domain`,
  `public_domain_original`, `public_domain_possible`, `copyright_restricted`,
  `unknown`)는 **source_value 그대로 유지** — 이 필드를 재작성하지 않는다.
- `license.normalized_value`는 신규 파생 필드이며, 아래 §4 매핑표로 산출한다.
- Modern 자료는 원본이 다양(출판사 카탈로그, 개인 구매 영수증, 계약서 등)하므로
  `license.source_value`에 원문 표기를 자유 텍스트로 기록하고, 등록자가
  `license.normalized_value`(=`copyright_status`)를 §4 표에 따라 수동 지정한다.

---

## 4. Copyright Policy

### 4.1 Copyright Status Rule (정정된 값 체계)

```yaml
copyright_status: public_domain | copyrighted | licensed | unknown
```

| 값 | 의미 |
|---|---|
| `public_domain` | 저작권 만료 또는 원저작자가 공개 선언 |
| `copyrighted` | 저작권 유효, 별도 이용 허락 없음(구매/라이선스 전 상태 포함) |
| `licensed` | 저작권 유효하나 이용권을 명시적으로 확보(구매·계약·라이선스) |
| `unknown` | 저작권 상태 미확인 — Full TSU 진입 불가(§6) |

**C1 Review R1(WARNING) 대응**: 기존 ADR-014 초안의
`copyright_status: public_domain \| copyright_restricted \| fair_use_reference \| unknown`은
이 표로 대체된다. `license.source_value → license.normalized_value` 매핑 예:

| `license.source_value`(예시) | `license.normalized_value`(=`copyright_status`) |
|---|---|
| `public_domain`, `public_domain_original`, `public_domain_possible` | `public_domain` |
| `copyright_restricted` | `copyrighted` |
| 출판사 라이선스 계약/구매 영수증 존재 | `licensed` |
| 미확인 | `unknown` |

### 4.2 Usage Permission Rule (정정된 값 체계)

```yaml
usage_permission: research | citation_only | internal_use | no_redistribution
```

| 값 | 의미 |
|---|---|
| `research` | 연구/설교 준비 목적 전문 활용 가능(원문 청크 저장 가능) |
| `citation_only` | 서지정보+발췌 인용만 가능, 원문 전체 저장 불가 |
| `internal_use` | 사용자 개인/내부 용도로만 사용, 외부 공유 불가 |
| `no_redistribution` | 재배포 절대 금지 — 메타데이터만 관리, 원문 저장 자체를 하지 않는 것을 기본값으로 함 |

**C1 Review R2(WARNING) 대응**: 기존 ADR-014 초안의
`usage_permission: full_text_storage \| excerpt_only \| metadata_only \| citation_only`는
이 표로 대체된다. `no_redistribution`이 이전 `access_control=no_redistribution`
값과 이름이 겹쳤던 문제(§4.3에서 `access_control`을 별도 축으로 재정의해 해소)도
함께 정리한다.

### 4.3 Access Control Rule (정정된 값 체계)

```yaml
access_control: public | restricted | private
```

| 값 | 의미 |
|---|---|
| `public` | NAE 검색 결과에 제한 없이 노출 |
| `restricted` | 인증된 사용자(등록자 본인)에게만 노출 |
| `private` | 노출하지 않음 — 등록 기록만 유지(예: 아직 저작권 검토 중인 자료) |

**C1 Review R3(access_control 미구현, WARNING) 대응**: `access_control`은
`usage_permission`과 **다른 축**이다 — `usage_permission`은 "이 자료를 어떻게
쓸 수 있는가"(용도 제한), `access_control`은 "누구에게 보이는가"(노출 범위).
예: `usage_permission=citation_only` + `access_control=public`(발췌만 공개
검색에 노출) 조합이 유효하다.

### 4.4 Source Type Rule (2026-08-02 개정 — `public_archive` 값 추가)

```yaml
source_type: licensed | purchased | personal | reference | public_archive
```

| 값 | 의미 |
|---|---|
| `licensed` | 출판사/저작권자로부터 이용권을 별도 취득 |
| `purchased` | 개인/기관이 정가 구매(전자책, 실물 스캔 등) |
| `personal` | 개인 소장 자료(설교노트, 강의안 등 제3자 저작권 없음) |
| `reference` | 인용/참조만 허용되는 자료(전문 저장 불가, 서지사항+발췌만) |
| `public_archive` (신규) | archive.org 등 공개 아카이브에서 무상 확보한 PD 스캔본 — 전문 저장 가능하나 "발췌만 허용"을 뜻하는 `reference`와는 의미가 다름 |

**Pilot-001 F-P1 / Pilot-002 §9 대응(2회 연속 발견)**: 기존 4개 값 중
"공개 아카이브에서 확보한 PD 자료"에 정확히 맞는 값이 없어 두 pilot 모두
`reference`를 부정확한 잠정치로 사용했다. `public_archive` 신설로 해소 —
기존 4개 값의 의미는 변경되지 않았으므로 Minor bump(§2.2) 대상.

### 4.5 네 필드의 관계 요약

```
copyright_status  — 법적 상태 (사실)
usage_permission  — 허용된 활용 방식 (권한)
access_control    — 검색/노출 범위 (가시성)
source_type       — 확보 경로/방식 (출처)
```

네 필드는 서로 독립이며 어느 하나도 다른 것에서 자동 유도되지 않는다 — 등록
시점에 각각 명시적으로 지정한다(자동 추론 시 오분류 위험, §1 Philosophy #1).
예: `source_type=public_archive` + `copyright_status=public_domain` +
`usage_permission=research` + `access_control=public` 조합이 Pilot-001/002
전체 자료의 전형적 값 조합이었다(실증 확인).

---

## 5. Authority Model

### 5.1 Entity 및 관계 (개정: Edition 승격, 2026-08-02 Volume 추가)

```
Author
  ↓
Work
  ↓
Edition          (1개 Work가 Edition을 1개 이상 가질 수 있음 — 아래 참고)
  ↓
Volume (선택)     (다권본에서만 사용, 단권 자료는 이 계층을 생략)
  ↓
Source File
```

| Entity | ID | 의미 |
|---|---|---|
| Author | `author_id` | 저자 canonical 식별자, 표기 변형(aliases) 통합 — Person 또는 Organization(아래 참고) |
| Work | `work_id` | 저작 단위(개정판·역서를 아우르는 상위 개념) |
| Edition | `edition_id` | 판본 단위 — 동일 Work의 여러 출판연도/개정 |
| Volume | `volume_id` (2026-08-02 신규, 선택) | 다권본에서 권(volume) 단위 — 동일 Edition 산하 여러 volume |
| Source File | `source_id` | 실제 파일 단위 — 동일 Edition/Volume의 여러 스캔본 가능 |

**Author: Person / Organization 구분(`author_type`, ADR-018, ID Governance Review Phase 2 반영 — 설계 확정, 스키마 파일 미반영)**:

```yaml
author_id: string
author_type: person | organization   # 신규(설계만, source_manifest.schema.yaml 미반영)
canonical_name: string
aliases: array[string]
birth_year: integer|null   # organization이면 항상 null(설립연도로 재해석하지 않음 — 아래 근거)
death_year: integer|null   # organization이면 항상 null(대부분 후신 조직으로 활동 지속 — 해산연도가 모호)
tradition: string|null
notes: string|null
```

정기간행물(Baptist Missionary Society, American Baptist Missionary
Union 등)처럼 발행 주체가 개인이 아닌 경우를 위해 별도 `CorporateAuthor`
Entity를 신설하지 않고 기존 Author entity를 확장하는 방식을 채택했다
(ADR-018 §3.2) — `author_id` FK가 Person/Organization 어느 쪽이든
동일하게 동작해야 Registry Validation Tool의 Reference 검사 로직이
이원화되지 않는다.

**Editor 관계**: 발행 조직(Publisher)과 편집자(Editor, 개인)를 구분해야
하는 경우 — `Work.author_id`는 발행 조직(`author_type=organization`)을
가리키고, 신규 선택 필드 `Work.editor_id`(Author FK,
`author_type=person`)로 편집자를 별도 연결한다. 예: Baptist Missionary
Magazine의 `author_id`는 `american_baptist_missionary_union`(조직),
편집자가 RAW에서 확인되면 `editor_id`로 별도 개인 Author를 연결한다
(Periodical Pilot 실제 데이터에는 RAW에서 명시적 개인 편집자 표기가
확인되지 않아 `editor_id`가 비어 있음 — ADR-018 §Risk 6).

**주의**: 위 `author_type`/`editor_id` 설계는 2026-08-02
NAE-PERIODICAL-CONDITION-RESOLUTION-001에서 문서화만 완료됐다 —
`resources/theological_sources/modern/source_manifest.schema.yaml`
(schema_version 2.1.0)에는 아직 반영되지 않았다(실제 반영은 Schema
v2.2.0 적용 시점, 별도 승인 필요).

**C1 Review R4/R5(WARNING) 대응**: 기존 설계는 Author/Work까지만 구조화하고
Edition은 `source_manifest.yaml`의 문자열 필드로만 존재해 "같은 판본의 다른
스캔본"을 묶을 canonical key가 없었다. `edition_id` 도입으로 Work(저작) ≠
Edition(판본) ≠ Source File(파일) 3단 구분이 명확해진다.

**Work:Edition = 1:N 관계 명문화(2026-08-02, Pilot-002 실증 대응)**: 1개
Work는 Edition을 정확히 1개만 갖는다고 암묵 가정되어 있었으나, Andrew Fuller
"Works in Eight Volumes" 사례에서 동일 Work 안에 서로 다른 인쇄 캠페인
2개(Vol01: 1820 Charlestown / Vol02-08: 1824-1825 New Haven)가 실측
확인되었다 — Work:Edition은 **1:N(N≥1)** 관계로 정의한다. 이 관계 변경은
기존 Pilot-001(church_order, Work:Edition=1:1)의 결과를 무효화하지 않는다
— 1:1은 N=1인 특수한 경우로 그대로 포함된다.

**Volume Entity 신설(2026-08-02, Pilot-002 실증 대응)**: 다권본(예: Fuller
8권, Baptist Encyclopedia 2권)에서 "권" 단위를 표현할 canonical key가 없어
Edition과 Source File 사이에 `volume_id`를 신설한다. 단권 자료는 이 계층을
생략하고 Edition→Source File로 직접 연결한다(하위 호환 — 기존 Pilot-001
church_order 데이터는 volume 없이도 유효).

### 5.2 병합 규칙 (변경 없음, 재확인)

- Author: 표기 변형을 정규화 비교(소문자, 공백/구두점 제거) 후 기존 `author_id`와
  일치하면 재사용, 불일치 시 사람이 동명이인 여부 확인 — **자동 병합 금지**.
- Work: 동일 Work의 여러 Edition은 같은 `work_id`, 다른 `edition_id`.
- Edition: 동일 Edition의 여러 Source File(재스캔 등)은 같은 `edition_id`, 다른
  `source_id` — Duplicate Detection Policy(`NAE_CORPUS_INGESTION_STANDARD_v1.md`
  Phase 6)의 "Different Scan Same Edition" 유형과 정확히 대응.
- **Volume(신규)**: 다권본에서 동일 Work의 서로 다른 인쇄 캠페인은 별도
  `edition_id`로 분리하고, 그 Edition 산하 volume들을 `volume_id`로 나열한다.
  같은 Edition 내에서도 volume별 `publication_year`가 1년 안팎 다를 수 있다
  (다권본이 여러 해에 걸쳐 순차 출판되는 정상적 관행) — 이 경우 Edition을
  추가로 쪼개지 않고 Edition의 `publication_year`는 범위로, 각 Volume의
  `publication_year`는 정확한 연도로 이중 기록한다(Pilot-002 §5 근거).
  Volume 번호는 OCR 텍스트가 아니라 RAW 디렉토리명을 canonical 출처로
  삼는다(OCR의 로마숫자 오인식 사례 확인, Pilot-002 §6).

### 5.3 레지스트리 (설계만, 미생성)

```
authority/authors.yaml   — Author 목록
authority/works.yaml     — Work + Edition + Volume + Source File 목록(중첩 구조)
```

(Pilot-002는 검증 목적상 `works.yaml`/`editions.yaml`/`volumes.yaml`/
`sources.yaml`을 별도 파일로 분리해 사용했다 — 실제 프로덕션 레지스트리를
파일 몇 개로 분리할지는 이 Governance 문서가 강제하지 않으며, 구현 단계에서
결정할 사항이다.)

이번 작업에서 실제 파일을 생성하지 않는다(명령서 금지 사항).

---

## 6. TSU Metadata Requirement

TSU 생성 호출 전 아래 필드가 존재해야 한다(**2026-08-02 개정: `edition_id`
필수 승격, `volume_id` 조건부 필수 추가** — Plan Review-001 F2, Pilot-002 §9
대응. 다권본 자료에서 Edition 구분이 인용 정확도에 직결됨을 실증):

```yaml
source_id: string
author_id: string
work_id: string
edition_id: string          # 필수로 승격(기존: 선택) — 2026-08-02
volume_id: string           # 조건부 필수: 해당 Work가 다권본(N volume ≥ 2)일 때만 필수, 단권 자료는 생략 가능 — 2026-08-02 신규
category: string
publication_year: integer
source_type: licensed | purchased | personal | reference | public_archive   # §4.4
copyright_status: public_domain | copyrighted | licensed | unknown   # §4.1
citation_policy: string
tsu_access: full | restricted | citation_only
```

| `copyright_status` × `usage_permission` 조합 | TSU 방식 |
|---|---|
| `public_domain` | Full TSU |
| `licensed` + `usage_permission=research` | Full TSU (라이선스 범위 내) |
| `licensed`/`copyrighted` + `usage_permission=citation_only` | Citation Only TSU |
| `usage_permission=no_redistribution` | TSU 생성 보류, 메타데이터만 등록 |
| `unknown` | TSU 생성 차단(§1 Philosophy #4) |

`tsu_access`는 위 조합의 최종 산출값이며, `access_control`(§4.3)과는 함께
평가된다 — `access_control=private`인 자료는 `tsu_access` 값과 무관하게 검색
결과에 노출하지 않는다(Index Update 단계 이전 필터).

**Dataset Isolation**: TSU 생성은 항상 명시적 `--dataset-path`를 사용하며
NAE/DBMA 파이프라인 경계를 넘지 않는다 — 정본은
[ADR-015 §3.6–3.7](architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md).

---

## 7. Migration Policy

### 7.1 원칙

- **RAW 변경 금지** — 원문 파일은 어떤 단계에서도 이동/수정하지 않는다.
- **기존 데이터 보존** — v1.2로 이미 등록된 NAE-PD manifest entry는 재작성하지
  않는다. `copyright_status`는 새 파생 필드로 v1.2 entry에 **추가**된다(기존
  `license` 필드는 그대로 둠).
- **점진적 Migration** — 전체 일괄 변환이 아니라 카테고리/자료 단위로 순차
  적용 가능해야 한다.

### 7.2 단계 (설계만, 미실행)

```
Step 1. v1.2 manifest entry에 copyright_status(파생) 필드 추가
        — license.source_value → license.normalized_value 매핑(§3) 적용,
          기존 license 필드는 변경 없음

Step 2. Modern 자료 신규 등록분부터 schema_version 2.0.0 전체 필드 적용
        — author_id/work_id/edition_id/usage_permission/access_control 등

Step 3. NAE-PD 기존 entry에 author_id/work_id/edition_id 점진적 소급 부여
        — Phase 4/5 Authority 병합 규칙에 따라 사람이 확인하며 진행(자동화 아님)

Step 4. source_validator.py 확장
        — v1.2/v2.0.0 양쪽 스키마 + 이번 문서의 값 체계(§3/§4) 검증 지원
          (`scripts/source_validator.py`, 미구현 — Future Expansion)
```

각 Step은 독립적으로 진행 가능 — Step 2가 끝나야 Step 3을 시작할 수 있는
구조가 아니다(병렬 가능). 단, TSU 생성(§6)은 해당 자료가 필요 필드를 모두
갖춘 이후에만 허용된다.

### 7.3 Validator 확장 요구사항 (2026-08-02 추가, Plan Review-001 F1 대응)

`scripts/source_validator.py`(코드 미수정, 요구사항 문서화만)의
`_REQUIRED_FIELDS`가 `content_genre`를 하드코딩 요구하는데, v2.0.0+ 스키마는
`content_genre` 대신 `category`를 사용한다 — 확장 없이 Step 2(Modern 신규
등록)를 실행하면 modern manifest가 전량 FAIL 처리된다(실측 확인됨). 향후
구현 시 요구사항: **`schema_version` 값에 따라 필수 필드 집합을 분기**한다
(`1.2` → `content_genre` 요구, `2.0.0` 이상 → `category` 요구). 이 요구사항은
문서화만 하며 실제 코드 변경은 별도 승인 대상이다.

### 7.4 ID(slug) 충돌 처리 규칙 (2026-08-02 추가, Plan Review-001 F3 대응)

`author_id`/`work_id`/`edition_id`/`volume_id` 생성 규칙(slug 연결 방식,
`NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 3 "ID 생성 규칙")이 동일 slug를
산출할 경우: 새 ID에 숫자 suffix(`-2`, `-3`, …)를 순차 부여하고, 충돌 발생
사실을 사람이 확인하도록 로그/notes에 남긴다 — 자동으로 조용히 override하지
않는다(§1 Philosophy #3 자동 병합 금지 원칙과 동일 취지).

### 7.5 ADR-014 원문과의 관계

ADR-014 §3.3/§3.4에 남아있는 초기 값 목록(`copyright_status: public_domain |
copyright_restricted | fair_use_reference | unknown` 등)은 **소급 수정하지
않는다** — ADR은 결정 시점의 기록이므로, 이 문서(§4)가 최신 정본이라는 사실을
ADR-014 자체에는 남기지 않고, 이 문서와 `NAE_CORPUS_INGESTION_STANDARD_v1.md`
쪽에서 명시적으로 참조·대체를 선언하는 방식을 택한다(NAE-METADATA-GOVERNANCE-
REVISION-001 명령서가 ADR-014 수정을 허용 범위에 포함하지 않았기 때문이기도 함).

**2026-08-02 개정 추가**: 이번 Architecture Revision(Volume Entity 신설,
Work:Edition 1:N, source_type `public_archive` 추가, edition_id TSU 필수
승격)은 ADR-014/ADR-015 어느 쪽도 직접 수정하지 않고 **신규
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md)**으로
기록한다 — 동일한 "ADR은 소급 수정하지 않는다" 원칙의 일관된 적용. ADR-014에는
ADR-016을 가리키는 최소한의 pointer 주석만 추가했다(본문 내용은 변경 없음).

---

## 완료 조건 체크

1. **ADR-015 BLOCKER 제거**: §3.6(--dataset-path 필수) + §3.7(Dataset Isolation Rule) — 제거됨.
2. **Metadata Schema v2.0.0 준비**: 값 체계 정정(§3/§4) + Semantic Versioning 원칙(§2) — 준비됨(실제 스키마 파일 생성은 범위 밖).
3. **Author/Work/Edition/Source 모델 정의**: §5 — 정의됨(레지스트리 파일 생성은 범위 밖).
4. **TSU Pipeline 필요 Metadata 확정**: §6 — 9개 필드 확정(2026-08-02: `edition_id` 필수 승격 + `volume_id` 조건부 필수 추가로 개정).
5. **추가 자료 동일 Pipeline 처리 가능 여부**: 가능 — Lifecycle(`NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 2)은 변경 없이 유지되고, 이번 개정은 값 체계/Entity 모델만 정정했으므로 파이프라인 구조 자체의 재작성 없이 신규 자료에 그대로 적용된다.

---

## 2026-08-02 개정 요약 (NAE-METADATA-ARCHITECTURE-REVISION-001)

Pilot-001/Pilot-002 실증 결과를 반영한 개정. `schema_version 2.0.0 → 2.1.0`
(Minor — 기존 데이터/필드 무효화 없음).

| 변경 | 위치 |
|---|---|
| `source_type`에 `public_archive` 값 추가 | §4.4 |
| Work:Edition = 1:N 관계 명문화 | §5.1 |
| Volume Entity 신설(`volume_id`, 선택) | §5.1, §5.2, §5.3 |
| `edition_id` TSU 필수 승격, `volume_id` 조건부 필수 추가 | §6 |
| Validator `schema_version`별 필수 필드 분기 요구사항 | §7.3 |
| ID(slug) 충돌 처리 규칙(suffix 부여) | §7.4 |
| ADR 처리: 신규 ADR-016 채택(ADR-014/015 미수정) | §7.5 |

상세 근거·대응표는 [`NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md`](NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md) 참고.
