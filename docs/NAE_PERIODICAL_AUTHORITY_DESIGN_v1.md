# NAE Periodical Authority Design v1

작성일: 2026-08-02
Project: NAE-PERIODICAL-AUTHORITY-PILOT-001
성격: Entity Model 분석 및 결정 — **전체 Migration 아님**
근거: [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md),
[`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md),
[ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md),
[`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md`](NAE_AUTHORITY_REGISTRY_DESIGN_v1.md)

---

## 0. RAW 실측 배경 (Phase 1 겸 근거)

`NAE/corpus/raw/archive_org/missions/`의 Baptist Missionary Magazine
계열 10개 issue를 전수 확인(title page/masthead OCR 실측):

| 실측 issue | 제호(masthead) | Volume | Issue | 발행 조직(표기) |
|---|---|---|---|---|
| 1803_v1i1 | "Massachusetts Baptist Missionary Magazine" | I | 1(Sept) | Massachusetts Baptist Missionary Society |
| 1817_v1i1 | "The American Baptist Magazine, and Missionary Intelligencer. New Series" | I | 1 | (trustees, Baptist Missionary Society of Massachusetts 표기) |
| 1837~1907(8건) | "Missionary Magazine"(masthead 축약형) | XVII~LXXXVII | 다양 | American Baptist Missionary Union |

**핵심 발견**: 이 "한 시리즈처럼 보이는" 자료가 실제로는 **제호가 최소
2회 이상 바뀌었다**(1803 단독 제호 → 1817 "New Series" 재시작 → 이후
"Missionary Magazine"으로 축약). 이는 도서/설교집과 달리 정기간행물
고유의 문제 — **시리즈가 시간이 지나며 이름이 바뀌고, volume 번호가
리셋될 수 있다.** 이번 Design/Pilot의 모든 결정은 이 실측 사실에
근거한다.

---

## 1. 검토 질문에 대한 답변 (명령서 제시 5문항)

| # | 질문 | 답 |
|---|---|---|
| 1 | Periodical을 Work로 처리 가능한가? | **가능** — §2 Option A 채택 근거 참고 |
| 2 | Editor/Organization을 Author Layer에 포함 가능한가? | **가능, 단 확장 필요** — Author의 `birth_year`/`death_year`가 조직에는 무의미(둘 다 `null`로 두면 스키마 위반 없이 수용 가능하나, 의미상 어색함이 남음). §3.4에서 상세 |
| 3 | Issue Entity가 필요한가? | **필요** — Volume만으로는 "Vol.37의 어느 호(1857년 10월 vs 다른 달)"를 구분 불가 |
| 4 | Article Entity가 필요한가? | **Registry 레벨에서는 불필요** — RAW가 issue 단위 스캔(PDF/OCR 1개)만 제공, article별 물리 파일이 없음. TSU 생성 단계의 metadata 필드로는 필요(§6) |
| 5 | 기존 TSU 구조와 충돌하는가? | **충돌 없음** — TSU는 아직 어떤 자료에 대해서도 생성되지 않았고(전체 파이프라인이 설계 단계), 신규 필드 추가는 기존 TSU_SCHEMA_VERSION과 독립적으로 가능(ADR-016/GOVERNANCE §6과 동일 패턴) |

---

## 2. Entity Model 분석 (Phase 2)

### Option A — 현재 모델 확장(Work→Edition→Volume→Issue→Source)

**장점**:
- 이미 구축된 Author/Work 인프라(Registry Build-001, ID Governance
  ADR-017)를 100% 재사용 — 새 최상위 Entity 없음.
- Work의 `aliases` 필드가 이미 "제목 다원 표기 보존" 용도로 설계되어
  있어(Registry Design v1 §2.2), 정기간행물의 제호 변경도 **동일
  메커니즘으로 흡수 가능**(신규 구조 불필요) — 실제로 이번 Pilot에서
  검증함(§0의 "Missionary Magazine" 표기 변화를 aliases로 처리).
- `work_type` 필드(이미 존재: `monograph`/`multi_volume`)에
  `periodical` 값만 추가하면 됨 — Minor 확장.

**단점**:
- Edition 계층이 정기간행물에는 개념적으로 어색함(§2.4 참고) — "판본"
  개념이 성립하지 않는 자료 유형에 빈 계층을 강제하는 형태가 됨.
- Volume:Issue 관계가 Work:Edition 관계와 개념적으로 유사해 계층이
  5단으로 늘어나면 전체 모델이 무거워짐.

### Option B — Periodical 별도 최상위 Entity(Periodical→Volume→Issue→Article→Source)

**장점**:
- 개념적으로 가장 명료 — 도서 계열과 정기간행물 계열을 완전히 분리.
- Article까지 1급 Entity로 만들면 향후 article 단위 정밀 검색에
  유리(단, 현재 RAW가 article 단위 파일을 제공하지 않아 당장은
  실익 없음).

**단점**:
- Author→Work 관계, ID 생성 규칙(ADR-017), Registry Validation Tool
  설계(Registry Design v1 §Phase5)를 **전부 병행 구축**해야 함 —
  중복 인프라.
- CLAUDE.md "불필요하게 넓은 리팩터링 금지"/"관련 없는 파일은 건드리지
  않는다" 원칙과 충돌 — 지금 자료 규모(10 issue, 2 periodical)에서는
  과설계.

### Option C — Work subtype(work_type: periodical만 추가, 계층 변경 없음)

**장점**: 가장 단순한 변경.

**단점**: Issue 단위 자체를 표현할 계층이 없어 §1 질문3(Issue Entity
필요)에 답하지 못함 — 이번 실측(volume당 issue가 명확히 구분되는
자료)에는 부적합.

### 결정: **Option A 채택(Edition 계층은 정기간행물에서 "건너뛰기")**

```
Author(조직/개인 포함, §3.4)
  └── Work(work_type: periodical)
        └── Edition  ← 정기간행물에서는 건너뜀(아래 근거)
              └── Volume
                    └── Issue(신규)
                          └── Source
```

**Edition을 건너뛰는 이유**: Registry Design v1이 이미 "Volume은
단권 자료에서 생략 가능한 선택 계층"이라는 패턴을 확립했다(Author→
Work→Edition→**Volume(선택)**→Source). 이번 결정은 그 패턴을
일반화한 것 — **정기간행물은 Edition을 선택적으로 생략**한다(판본
개념이 성립하지 않으므로). 새 규칙을 만드는 대신 이미 있는 "선택
계층" 메커니즘을 재사용 — 최소 확장 원칙에 부합.

**Article을 Registry Entity로 만들지 않는 이유**: RAW는 issue 전체가
PDF/OCR 1개 파일이며 article별 파일 분리가 없다(실측). Registry
Source entity는 "실제 파일 단위"를 표현하는 것이 원칙(Registry Design
v1 §2.5) — 물리적으로 존재하지 않는 단위를 Entity로 만들면 참조할
File이 없어 원칙에 어긋난다. Article 정보(제목/저자)는 TSU 생성
시점의 **메타데이터 필드**로만 다룬다(§6).

---

## 3. ID Governance 검토 (Phase 3)

### 3.1 신규 ID 필요 여부

| ID | 필요 여부 | 형식 |
|---|---|---|
| `periodical_id` | 불필요(개념적으로는 `work_id`) — 단, 이번 Pilot 파일 격리 목적으로 `periodical_id`라는 필드명을 그대로 사용(§4에서 파일 분리 이유 설명) | `{author_id}_{title_slug}`(work_id와 동일 규칙, ADR-017 §2.2 그대로 재사용) |
| `issue_id` | **필요**(신규) | `{volume_id}_i{NNN}` |
| `article_id` | 불필요(§2 Option A 결정, Registry Entity 아님) | — |

### 3.2 Volume ID 폭 확장(2자리 → 3자리)

ADR-017 §2.4는 단행본 다권본 기준 `v{NN}`(2자리, ~99권까지)을
정의했다. 이번 실측에서 Volume 번호가 87까지 나타나 2자리로도 아직은
충분하나, 정기간행물은 100년 이상 이어지며 수백 volume에 이를 수
있어(예: 어떤 신학 저널이 200년째 발행 중이면 Vol 200+) **정기간행물
한정으로 `v{NNN}`(3자리)을 채택**한다. ADR-017 본문은 소급 수정하지
않고(기존 관례), 이 확장을 §5(완료 조건 Q4)에서 "ADR-017 개정 불필요,
Design 문서로 명시적 확장"으로 처리한다 — 상세 근거는 완료 조건 답변
참고.

### 3.3 Issue ID 및 Source ID

```
issue_id  = "{volume_id}_i{NNN}"
source_id = "{issue_id}_{scan_suffix}"     # ADR-017 §2.5의 scan_suffix 패턴 재사용
```

### 3.4 Organization을 Author로 취급하는 문제

현재 Author 필수 필드(`birth_year`/`death_year`)는 개인을 전제로
설계됐다. 조직(예: American Baptist Missionary Union)은 이 두 필드가
구조적으로 무의미하다. 이번 Pilot에서는 실용적으로 두 필드를 비워
(`null`) 두는 방식으로 우회했으나(스키마 위반 없음), **근본적으로는
Author 스키마에 `author_type: person | organization` 필드를 추가하는
것을 권고**한다(이번 Pilot에서는 실제로 필드를 추가하지 않음 — Design
결정만, §7 Remaining Risk에 기록).

---

## 4. Registry 구조 (Phase 4 요약)

```
resources/theological_sources/authority/pilot_periodical/
├── periodicals.yaml   (Work 동등물, work_type=periodical)
├── volumes.yaml
├── issues.yaml         (신규 Entity)
├── sources.yaml
└── manifest.yaml       (Registry 색인)
```

명령서가 지정한 파일명을 그대로 사용했으나(`periodicals.yaml`), §2
결정에 따르면 **Production 반영 시에는 이 내용을
`authority/works.yaml`(work_type=periodical)에 병합**하는 것을
권고한다 — 별도 최상위 파일로 영구 유지하지 않는다(Option B를
채택하지 않았으므로).

---

## 5. TSU 영향 분석 (Phase 6, 설계만 — TSU 생성 안 함)

정기간행물 TSU에 필요한 필드(제안):

```yaml
periodical_id: string     # = work_id
volume_id: string
issue_id: string           # 신규
article_title: string|null # article 단위 청킹 시에만 채움, Registry에는 없음(§2)
author_or_editor: string|null  # article 저자(있으면) — periodical 전체 author_id와 별개일 수 있음
publication_date: string   # issue_id로부터 상속(issues.yaml)
citation_policy: string    # 기존 corpus manifest 필드 재사용
tsu_access: full | restricted | citation_only   # 기존 필드 재사용
```

**TSU 스키마 충돌 없음**(§1 질문5 답 재확인) — `TSU_SCHEMA_VERSION`은
metadata schema_version과 독립적(ADR-016에서 이미 확인된 원칙,
`NAE/pipeline/tsu/config.py` 실측). `article_title`/`author_or_editor`는
신규 optional 필드로 추가하면 되고 기존 TSU 레코드를 무효화하지 않는다.
