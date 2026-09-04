# NAE ID Governance v1

작성일: 2026-08-02
Project: NAE-ID-GOVERNANCE-001
성격: **ID 정책 설계 — 실제 rename 없음.** 이 문서가 확정하는 규칙은
"Migration Policy"(§6)이며, 실행은 별도 승인 대상이다.
근거: [`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md`](NAE_AUTHORITY_REGISTRY_DESIGN_v1.md),
[`NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md`](NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md) Remaining Risk #1,
[`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §5,
[ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md)

이 문서는 Author/Work/Edition/Volume/Source ID의 **유일한 정본**이다.
`NAE_CORPUS_INGESTION_STANDARD_v1.md`의 기존 "ID 생성 규칙" 절은 이
문서 발행 이후 이 문서를 참조하도록 갱신 대상이며(코드/데이터 변경은
아님), 원문은 소급 수정하지 않는다(ADR 불변 원칙과 동일 관례, GOVERNANCE §7.5).

---

## 1. Existing ID Audit (Phase 1)

실측(`resources/theological_sources/authority/*.yaml`, 2026-08-02
Authority Registry Build-001 산출물 기준):

| Entity | ID | 대소문자 | Separator | Suffix | 비고 |
|---|---|---|---|---|---|
| Author | `dagg_john_l` | 소문자 | `_` | 없음 | surname_given_middleinitial 패턴 |
| Author | `hiscox_edward_t` | 소문자 | `_` | 없음 | 동일 패턴 |
| Author | `FULLER-ANDREW-001` | **대문자** | `-` | **`-001`(순번)** | 완전히 다른 패턴 |
| Work | `WORK-DAGG-CHURCH-ORDER-001` | 대문자 | `-` | `-001` | prefix `WORK-` + author surname + title 일부 + 순번 |
| Work | `WORK-HISCOX-STANDARD-MANUAL-001` | 대문자 | `-` | `-001` | 동일 패턴 |
| Work | `FULLER-COMPLETE-WORKS-001` | 대문자 | `-` | `-001` | author surname + title + 순번(Work prefix 없음 — Work/Work 계열 표기 자체도 불일치) |
| Edition | `WORK-DAGG-CHURCH-ORDER-001-1871` | 대문자 | `-` | year 접미 | `{work_id}-{year}` |
| Edition | `FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820` | 대문자 | `-` | `-ED-{place}-{year}` | `{work_id}-ED-{place}-{year}` — Dagg/Hiscox와 다른 하위 패턴 |
| Volume | `FULLER-COMPLETE-WORKS-VOL01` | 대문자 | `-` | `VOL{NN}` | edition_id 접두 아니라 work_id 접두 + `VOL{NN}` |
| Source | `BAP-CHURCH-DAGG-001` | 대문자 | `-` | `-001` | `BAP-{category}-{author}-{seq}` — v1.2 레거시(`SLBC1689` 등)와도 다른 제3의 패턴 |
| Source | `BAP-MISS-FULLER-VOL01` | 대문자 | `-` | `-VOL{NN}` | `BAP-{category}-{author}-VOL{NN}` |

**동명이인 처리**: 현재 Registry에 실제 동명이인 사례 없음(3명 전원
고유). 처리 규칙은 §3(Collision Policy)에서 사전 정의.

**Work ID 판단**: 현재 3개 Work 모두 "저자 prefix + 제목 slug + 순번"
패턴이나 표기 스타일이 서로 다름(Work- 접두 유무, 순번 자릿수 등).
Collection 성격 Work(`fuller_complete_works`류)는 이번 감사 대상에
1건(Fuller) 존재 — `work_type: multi_volume`로 이미 구분됨(Registry
Build-001 §Phase2).

**Edition ID 판단**: `publication_year` 포함(전원), `publisher` 포함은
Fuller만(`CHARLESTOWN`/`NEWHAVEN-CONVERSE`) — Dagg/Hiscox는 연도만
사용. 충돌 가능성: 동일 Work가 같은 해에 두 출판사에서 나온 경우
연도만으로는 구분 불가(현재 실제 사례 없음, 잠재 위험으로 §3에서 규칙화).

**Volume ID 판단**: `volume_number`는 2자리 zero-pad(`VOL01`~`VOL08`)로
일관 — 이 부분은 8개 전부 일치. Edition 종속성은 `edition_id` 필드로
표현되나(FK), ID 문자열 자체는 edition_id를 포함하지 않고 work_id를
직접 이어붙임 — Edition이 여러 개인 Work(Fuller)에서도 volume_id
문자열만 보면 어느 Edition 소속인지 알 수 없음(FK 필드를 봐야만 알 수
있음 — ID 자체의 자기서술성이 약함, §2.4에서 개선).

**Source ID 판단**: 파일(스캔본) 단위(volume_id/edition_id당 여러
source_id 가능한 구조는 설계되어 있으나 현재 실제로는 1:1). archive
source 식별자(예: archive.org identifier)는 포함되지 않음 — 별도 필드
(`archive_source`, corpus manifest 쪽)로 관리(Registry Source에는
없음, Registry Build-001 §2.5 의도적 축소).

---

## 2. Entity별 Canonical ID Rule (Phase 2)

### 공통 원칙

- **lowercase, snake_case, ASCII only** — 대문자/하이픈 혼용 금지.
- **Deterministic** — 같은 입력이면 항상 같은 ID가 나와야 함(등록
  순서·시점에 의존하는 값 금지, 예: 단순 증가 순번은 정렬 순서가
  달라지면 값이 바뀔 수 있어 deterministic하지 않음 — 순번이 필요하면
  사람이 명시적으로 확정한 값만 사용).
- **자기서술적(self-descriptive)** — ID만 보고도 어느 Author/Work/
  Edition에 속하는지 유추 가능해야 함(Volume ID 개선, 아래 §2.4).

### 2.1 Author ID

```
author_id = "{surname}_{given_name}[_{middle_initial}]"
```

예: `dagg_john_l`, `hiscox_edward_t`, `fuller_andrew`

**표기 순서 결정: surname 우선(given-name 우선 아님)** — 이번
명령서의 예시(`john_l_dagg`, `andrew_fuller`)는 given-name 우선이었으나,
아래 근거로 **surname 우선을 canonical로 채택**한다:

1. 기존 실 데이터 3건 중 2건(`dagg_john_l`, `hiscox_edward_t`)이 이미
   surname 우선 — 이 규칙을 채택하면 마이그레이션 대상이 1건(Fuller)뿐.
   given-name 우선을 채택하면 3건 전부 변경 필요.
2. `NAE_CORPUS_INGESTION_STANDARD_v1.md` "ID 생성 규칙"이 이미
   `author_id = "{surname}_{givenname}"`로 문서화되어 있음(기존 정본).
3. 신학 서지학 관례상 저자를 성(姓) 기준으로 알파벳 정렬·색인하는
   것이 표준적(Author Authority 조회 시 surname으로 찾는 경우가 많음).

### 2.2 Work ID

```
work_id = "{author_id}_{title_slug}"
```

예: `dagg_john_l_church_order`, `fuller_andrew_complete_works`

- `title_slug`는 `canonical_title`(RAW 실측 제목, GOVERNANCE 제목 우선
  원칙)에서 파생 — 소문자, 공백→`_`, 구두점 제거.
- Collection형 Work(다권본 전집)는 `title_slug`에 "complete_works"처럼
  집합명을 그대로 사용 — 별도 접미사 불필요(work_type 필드가 이미
  구분자 역할).

### 2.3 Edition ID

```
edition_id = "{work_id}_{publication_year}[_{place_slug}]"
```

예: `dagg_john_l_church_order_1871`,
`fuller_andrew_complete_works_1820_charlestown`,
`fuller_andrew_complete_works_1824_newhaven`

- `place_slug`는 **동일 Work에 Edition이 2개 이상**이거나, 연도가
  범위(예: "1824-1825")인 경우 **필수**로 포함 — 그 외(Work당 Edition
  1개뿐)에는 생략 가능(Dagg/Hiscox처럼 연도만으로 충분히 유일).
- 연도가 범위인 경우 ID에는 **시작 연도**만 사용(범위 전체는
  `publication_year` 필드에 문자열로 유지, ID는 짧게).
- **충돌 시(동일 Work, 동일 연도, 다른 출판사)**: `place_slug`를
  필수로 강제(§3 Collision Policy와 연동).

### 2.4 Volume ID (조건부 Entity)

```
volume_id = "{edition_id}_v{NN}"
```

예: `dagg_...`(해당 없음, 단권), `fuller_andrew_complete_works_1820_charlestown_v01`,
`fuller_andrew_complete_works_1824_newhaven_v02`

- **개선 사항**: 기존(`FULLER-COMPLETE-WORKS-VOL01`)은 work_id
  기반이라 Edition이 여러 개인 Work에서 어느 Edition 소속인지 ID만으로
  알 수 없었다 — canonical rule은 **edition_id를 접두**로 사용해
  자기서술성을 개선한다.
- `volume_number` 필수(§Phase1에서 이미 확인된 실무 요구, Registry
  Design 문서 Remaining Risk #2 반영), 2자리 zero-pad(`v01`~`v99`,
  100권 이상 시 확장은 후속 검토).

### 2.5 Source ID

```
source_id = "{volume_id}_{scan_suffix}"          # 다권본(volume 있음)
source_id = "{edition_id}_{scan_suffix}"          # 단권(volume 없음)
```

예: `dagg_john_l_church_order_1871_s01`,
`fuller_andrew_complete_works_1820_charlestown_v01_s01`

- `scan_suffix`는 `s01`부터 시작, 동일 Volume/Edition의 재스캔본이
  추가되면 `s02`, `s03`… (Different Scan Same Edition 유형,
  `NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 6과 연동).
- **archive source 식별자는 ID에 포함하지 않는다** — Registry Build-001
  §2.5의 "의도적 축소" 원칙 재확인(Source ID는 구조적 위치만 표현,
  출처 상세는 별도 필드).
- **v1.2 레거시 source_id**(`SLBC1689`, `AF1815` 등, 접두어 없는 영숫자
  코드)는 이 규칙 대상이 아니다 — v1.2 네임스페이스는 그대로 유지하고
  건드리지 않는다(스키마 병행 원칙, GOVERNANCE §1 Philosophy #2와 동일
  적용). 두 패턴은 형태가 완전히 달라(영숫자 코드 vs snake_case) 우연히
  충돌할 가능성이 사실상 없다.

---

## 3. Collision Policy (Phase 3)

### 3.1 동일 이름 저자(진짜 동명이인)

```
1차: author_id에 출생연도 포함 — "{surname}_{given}_{birth_year}"
     예: john_smith_1660, john_smith_1810
2차(출생연도도 모르거나 같을 때): 숫자 suffix — "_2", "_3"...
     반드시 notes 필드에 구분 근거(활동 시기/저작/교단 등) 기록
```

**출생연도를 1차로 선택한 이유**: 임의 순번(등록 순서)은 나중에 셋째
인물이 추가되면 재정렬 압박이 생기고 deterministic하지 않음(§2 공통
원칙) — 출생연도는 사실에 근거한 값이라 안정적. 단, 출생연도 자체가
불확실한 역사 인물이 많으므로 2차 수단(숫자 suffix)을 반드시 남겨둔다.

**자동 처리 금지**: GOVERNANCE §1 Philosophy #3(자동 병합 금지)과
동일하게, 두 저자가 진짜 동일 인물인지 다른 인물인지는 항상 사람이
먼저 판단한다 — ID 규칙은 "다른 인물로 확정된 후"의 표기법만 다룬다.

### 3.2 동일 Work 제목(같은 저자, 제목만 같음)

```
같은 저자가 "Sermons"라는 제목을 여러 번 썼거나, 다른 저작을
등록자가 실수로 같은 제목으로 입력한 경우:

1. 먼저 사람이 확인: 진짜 다른 저작인가, 중복 등록 실수인가?
2. 다른 저작으로 확정되면: 부제/연도/장르를 title_slug에 포함해 구분
   예: "sermons" 충돌 시 "sermons_1850", "sermons_collection" 등
   RAW 근거가 있는 구분자를 우선 사용(임의 순번 지양, §2 공통 원칙)
3. 중복 등록 실수로 확정되면: 하나를 삭제하지 않고 aliases로 병합
   (Duplicate Policy, NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 6과 동일 원칙)
```

### 3.3 동일 Edition (같은 publisher+year+title)

```
같은 publisher/year/title 조합이 재등장하면:

기본 가정: Duplicate(같은 Edition의 재확인 시도) — 새 edition_id를
발급하지 않고 기존 edition_id에 Source만 추가(§2.5 scan_suffix 증가).

새 Edition으로 인정하는 경우(예외): RAW 실물 대조로 실제 인쇄판
차이가 확인될 때만(예: 오탈자 수정판, 재판(reprint) 표시가 title
page에 명시) — 이 경우 publisher/year가 같아도 edition_id에 구분자
(`_rev2` 등) 추가.

판단 주체: 항상 사람. Edition 여부는 서지학적 판단이라 자동 규칙으로
확정하지 않는다.
```

---

## 4. Pilot ID 호환성 평가 (Phase 4)

| ID | 평가 | 사유 |
|---|---|---|
| `dagg_john_l` | **유지 가능** | §2.1 canonical rule과 이미 일치 |
| `hiscox_edward_t` | **유지 가능** | 동일 |
| `FULLER-ANDREW-001` | **변경 필요** | 대문자/하이픈/순번 접미 — canonical과 불일치 |
| `WORK-DAGG-CHURCH-ORDER-001` | **변경 필요** | 대문자/하이픈, author_id 기반이 아님(문자열상 author_id 재사용 안 됨) |
| `WORK-HISCOX-STANDARD-MANUAL-001` | **변경 필요** | 동일 |
| `FULLER-COMPLETE-WORKS-001` | **변경 필요** | 동일 |
| Edition 4건 전부 | **변경 필요** | 대문자/하이픈, Dagg/Hiscox와 Fuller가 서로 다른 하위 패턴 |
| Volume 8건 전부 | **변경 필요** | 대문자/하이픈, edition_id 비포함(자기서술성 부족) |
| Source 10건 전부(v2.1.0 Registry 분) | **변경 필요** | 대문자/하이픈, `BAP-` 접두(v1.2 관례를 어설프게 흉내낸 표기) |

**원칙 확인**: 기존 Registry(`authority/*.yaml`, `authority/pilot/*`)는
**삭제하지 않는다**(명령서 금지 사항 준수, 이번 문서 발행만으로는
어떤 YAML 파일도 수정하지 않았음 — §7 Remaining Risks에서 재확인).

**결정: "변경 필요 + legacy_id alias 보존"** — 단순 "변경"이 아니라,
실제 Migration 시 각 entity에 `legacy_id`(구 ID) 필드를 추가해 구
ID로도 역참조 가능하게 한다(Phase4가 제시한 3개 선택지 중 2번+3번의
혼합 — 완전 교체이지만 완전 삭제는 아님).

---

## 5. ADR 결정 (Phase 5)

**Option B 채택 — 신규 ADR-017 작성.**

이유: ADR-016(Metadata Authority Model Revision)은 Entity **모델**
(Author→Work→Edition→Volume→Source 계층 자체)에 대한 결정이고, 이번
결정은 그 모델의 **ID 표기 규칙**(문자열 포맷)에 대한 것 — 층위가
다르다. 또한 이미 확립된 관례(GOVERNANCE 개정 시 ADR-014를 소급
수정하지 않고 ADR-016을 신설했던 선례)를 일관되게 적용 — ADR은 결정
시점의 기록이므로 매번 새 결정은 새 ADR로 남긴다. 상세는
[ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md).

---

## 6. Migration Policy (Phase 6) — 정책만, 미실행

### 6.1 원칙

- **RAW/기존 Registry 미변경** — 이 문서는 정책만 정의, 실제 rename은
  하지 않는다.
- **legacy_id 보존** — 실제 Migration 시 구 ID를 삭제하지 않고
  `legacy_id` 필드로 각 entity에 보존한다.
- **원자적 rename** — 실행 시 ID 변경은 해당 entity의 ID 필드와, 그
  ID를 참조하는 **모든 FK 필드**를 같은 커밋에서 함께 바꾼다(부분
  변경 시 참조 무결성이 깨짐 — Registry Build-001 §Phase4 검증
  스크립트로 실행 전/후 반드시 재확인).

### 6.2 변환 매핑 (Old → New, 실행 전 검토용)

```yaml
# Author
FULLER-ANDREW-001              -> fuller_andrew

# Work
WORK-DAGG-CHURCH-ORDER-001            -> dagg_john_l_church_order
WORK-HISCOX-STANDARD-MANUAL-001       -> hiscox_edward_t_standard_manual
FULLER-COMPLETE-WORKS-001             -> fuller_andrew_complete_works

# Edition
WORK-DAGG-CHURCH-ORDER-001-1871                     -> dagg_john_l_church_order_1871
WORK-HISCOX-STANDARD-MANUAL-001-1890                -> hiscox_edward_t_standard_manual_1890
FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820        -> fuller_andrew_complete_works_1820_charlestown
FULLER-COMPLETE-WORKS-001-ED-NEWHAVEN-CONVERSE       -> fuller_andrew_complete_works_1824_newhaven

# Volume
FULLER-COMPLETE-WORKS-VOL01 -> fuller_andrew_complete_works_1820_charlestown_v01
FULLER-COMPLETE-WORKS-VOL02 -> fuller_andrew_complete_works_1824_newhaven_v02
FULLER-COMPLETE-WORKS-VOL03 -> fuller_andrew_complete_works_1824_newhaven_v03
FULLER-COMPLETE-WORKS-VOL04 -> fuller_andrew_complete_works_1824_newhaven_v04
FULLER-COMPLETE-WORKS-VOL05 -> fuller_andrew_complete_works_1824_newhaven_v05
FULLER-COMPLETE-WORKS-VOL06 -> fuller_andrew_complete_works_1824_newhaven_v06
FULLER-COMPLETE-WORKS-VOL07 -> fuller_andrew_complete_works_1824_newhaven_v07
FULLER-COMPLETE-WORKS-VOL08 -> fuller_andrew_complete_works_1824_newhaven_v08

# Source
BAP-CHURCH-DAGG-001    -> dagg_john_l_church_order_1871_s01
BAP-CHURCH-HISCOX      -> hiscox_edward_t_standard_manual_1890_s01
BAP-MISS-FULLER-VOL01  -> fuller_andrew_complete_works_1820_charlestown_v01_s01
BAP-MISS-FULLER-VOL02  -> fuller_andrew_complete_works_1824_newhaven_v02_s01
BAP-MISS-FULLER-VOL03  -> fuller_andrew_complete_works_1824_newhaven_v03_s01
BAP-MISS-FULLER-VOL04  -> fuller_andrew_complete_works_1824_newhaven_v04_s01
BAP-MISS-FULLER-VOL05  -> fuller_andrew_complete_works_1824_newhaven_v05_s01
BAP-MISS-FULLER-VOL06  -> fuller_andrew_complete_works_1824_newhaven_v06_s01
BAP-MISS-FULLER-VOL07  -> fuller_andrew_complete_works_1824_newhaven_v07_s01
BAP-MISS-FULLER-VOL08  -> fuller_andrew_complete_works_1824_newhaven_v08_s01

# 변경 없음(이미 canonical)
dagg_john_l      -> dagg_john_l (unchanged)
hiscox_edward_t  -> hiscox_edward_t (unchanged)
```

**주의**: 위 표는 검토용 계획이며 **이번 작업에서 실행하지 않았다**
(어떤 YAML 파일도 수정하지 않음). 실제 rename은 별도 승인된
Migration 작업에서, `legacy_id` 보존 + 원자적 FK 갱신 + 실행 전/후
Reference Integrity 재검증(Registry Build-001 §Phase4 스크립트 재사용)
절차로 진행한다.

### 6.3 신규 자료(예: Baptist Missionary Magazine)에 대한 적용

다음 Pilot부터는 **처음부터 이 문서의 canonical rule로 ID를 생성**한다
— 구 관례(Fuller 스타일)로 만들었다가 나중에 다시 변환하는 이중 작업을
피한다. 정기간행물(volume+issue)의 ID 확장 규칙(예: `_i{NN}` issue
접미)은 이번 문서 범위 밖 — Baptist Missionary Magazine Pilot에서
실제 사례로 확정 필요(§7 Remaining Risks).
