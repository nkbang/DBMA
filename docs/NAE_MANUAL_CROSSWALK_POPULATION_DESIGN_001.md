# NAE Manual Crosswalk Population Design 001

**Project:** NAE-MANUAL-CROSSWALK-POPULATION-DESIGN-001
**작성일:** 2026-08-05
**성격:** Design Only — `crosswalk.yaml`/`index.json` 수정, Manual
Mapping 생성, Production Identifier 추가, TSU 생성/Activation,
Manifest/Registry/RAW/canonical 변경, Migration 실행 전부 미수행.

---

## Phase 1 — Identifier Inventory(재조사, 2026-08-05 기준)

### Registry Identifier(Source, 10건)

```
BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX,
BAP-MISS-FULLER-VOL01 ~ BAP-MISS-FULLER-VOL08
```

전부 `canonical_id`/`legacy_id` 완비(ADR-017 Option B, NAE-ID-
GOVERNANCE-IMPLEMENTATION-001 기완료).

### Manifest Identifier(10건)

`resources/theological_sources/manifest/pilot/*/manifest.yaml`의
`source_id` — Registry Source 10건과 **정확히 1:1 일치**(ADR-019
"manifest_id = source_id" 원칙, 재확인).

### Canonical Identifier(3건, 이전 조사 대비 갱신됨)

| identifier | canonical.json | 비고 |
|---|---|---|
| `PBC1742` | **없음**(`normalize_report.json`만) | 처리 불가 상태 유지 |
| `PBC1765` | **있음**(`source: hocr`, 114 페이지) | 이전 조사(§NAE_TSU_PIPELINE_PREFLIGHT_REPORT_001.md) 시점엔 "미확인"이었으나 이번에 실제 콘텐츠 확인됨 |
| `SLBC1689` | **있음**(`source: hocr`, 157 페이지) | 위와 동일 — 이번에 처음 확인 |

`canonical.json`에는 `identifier`/`pipeline_version`/`source`/
`page_count`/`paragraphs`/`footnotes`/`scripture_references`만 있고
**제목·저자 필드가 없다** — title/author는 `NAE/corpus/raw/archive_org/
{identifier}/metadata.json`에서 가져오도록 설계되어 있으나(`parser.
_find_raw_metadata`), 실측 결과 그 경로들이 비어있다(§아래).

### RAW Identifier(3건, canonical과 다른 집합)

```
NAE/corpus/raw/archive_org/{AF1815, PBC1742, TH1612}
```

**canonical(3건)과 raw(3건)의 identifier가 겹치는 것은 `PBC1742`
하나뿐**이다(`PBC1765`/`SLBC1689`는 canonical에 있지만 raw
디렉토리는 없고, `AF1815`/`TH1612`는 raw에 있지만 canonical
디렉토리는 없다). 게다가 `AF1815`/`PBC1742`/`TH1612` 디렉토리 자체가
비어있어(`metadata.json` 없음) title/creator 정보를 조회할 수
없었다 — 즉 **canonical 3건 중 어느 것도 raw 메타데이터로 제목/저자를
확인할 근거가 지금 당장은 없다.**

### 연결 상태 요약

```
Registry(10) ──1:1──> Manifest(10)     [완전 연결, 재확인 완료]
Manifest(10) ──0:0──> Canonical(3)     [연결 없음 — 겹치는 identifier 없음]
Canonical(3) ··2:1··  RAW(3)            [부분 우연 일치(PBC1742) 1건뿐, 근거 자료 없음]
```

### Crosswalk 필요 구간

**Manifest(Registry Source 10건) → Canonical/TSU(현재 3건) 구간
전체**가 Crosswalk 대상이다. 단, Phase 2에서 확인하듯 지금 이
10×3(=최대 30가지 조합) 어느 쌍도 "동일 작품/동일 저자"임을 뒷받침할
**근거 자료(제목/저자 메타데이터)가 확보되어 있지 않다** — 이것이
Phase 2 Candidate Selection Policy가 반드시 "근거 부족 시 후보에서
제외"를 원칙으로 삼아야 하는 이유다.

---

## Phase 2 — Candidate Selection Policy

### 원칙: 5가지 근거 중 최소 2가지 이상 **독립적으로** 일치해야 후보

| 근거 | 확인 방법(설계만, 실제 조회는 구현 단계) |
|---|---|
| 동일 작품명 | Registry `works.yaml::canonical_title`/`aliases` vs canonical/raw 메타데이터의 제목(있다면) |
| 동일 저자 | Registry `authors.yaml::canonical_name`/`aliases` vs canonical/raw 메타데이터의 creator(있다면) |
| 동일 Edition | Registry `editions.yaml::publication_year`/`publisher`/`publication_place` vs 원문 실측(title page 등) |
| 동일 Source Evidence | Registry `sources.yaml::file_path`가 가리키는 실제 파일 경로/구조와 canonical/raw 실측 경로 일치 |
| 동일 File Evidence | 체크섬(sha256) 또는 페이지 수·파일 크기 등 물리적 특징 일치(§Phase3에서 Evidence 필드로 구체화) |

**"근거 1가지만 일치"는 후보로 인정하지 않는다** — 예: identifier
문자열이 우연히 비슷해 보이는 것(`AF1815`가 "Andrew Fuller"+"1815"를
연상시킴 — Registry의 `FULLER-ANDREW-001`/`fuller_andrew`, death_year
1815와 절묘하게 겹친다는 것을 이번 조사에서 발견했다)은 **그 자체로는
후보 사유가 될 수 없다** — 이는 Mapping Policy Rule 3가 명시적으로
금지하는 `similar-name`(이름 유사도만) 패턴의 실제 사례이며, 이번
설계에서는 이 우연의 일치를 "그럴듯해 보이지만 검증되지 않은
추측"의 교육적 예시로만 기록한다 — **실제 매핑 후보로 채택하지
않는다**(File/Source Evidence 없이는 §Phase3 기준 미달).

### 추측 금지의 구체적 의미

- identifier 이름의 문자·숫자 유사성만으로 후보를 만들지 않는다
- "아마 같은 책일 것"이라는 정황 추론만으로 후보를 만들지 않는다
- 자동 스크립트가 계산한 유사도 점수(예: 문자열 편집 거리)만으로
  후보를 만들지 않는다 — 그런 도구는 **후보를 더 빨리 찾도록 돕는
  것까지만** 허용되고, 후보 확정에는 반드시 사람이 원문을 대조해야
  한다(§Phase4 Review Workflow)

---

## Phase 3 — Evidence Requirement

`mapping_status = manual-confirmed`가 되기 위한 최소 필드(Crosswalk
Schema `evidence: string` 필드에 아래 항목을 구조화된 서술로 담는다 —
스키마 자체는 변경하지 않음, `evidence` 필드의 **내용 작성 규칙**만
이번에 정의):

| 항목 | 정의 |
|---|---|
| Source Evidence | Registry `sources.yaml::file_path` 및 그 상위 Work/Edition 서지 정보와 대상 identifier의 원문(제목/저자/발행 정보)이 일치한다는 서술 |
| File Evidence | 물리적 대조 근거 — 페이지 수, 체크섬, 파일 크기, 또는 canonical.json의 `page_count` 등과 실제 원문(RAW/archive.org 메타데이터) 간 일치 확인 |
| Reviewer | 검토를 수행한 사람의 식별자(이름 또는 계정) |
| Review Date | 검토 수행 일자(ISO 8601) — Crosswalk Schema의 `verified_at` 필드에 대응 |
| Confidence | Schema의 기존 `confidence` enum(`high`/`medium`/`low`) — TSU Gate 통과에는 `high`만 허용됨(기존 구현, `CONFIDENCE_SCORE` 재확인) |
| Decision Reason | 왜 이 매핑을 확정했는지에 대한 사람의 최종 판단 서술(단순 "일치함"이 아니라 "무엇을 근거로" 일치한다고 봤는지) |

**최소 기준**: Source Evidence + File Evidence **둘 다** 있어야 하며
(Phase2의 "최소 2가지 독립 근거" 원칙과 일치), 저자/작품명만 일치하고
물리적 대조(File Evidence)가 없는 경우는 `manual-confirmed`가 아니라
`evidence-backed`(기존 enum, "확정 전 단계")에 머무른다.

---

## Phase 4 — Review Workflow

```
Candidate(Phase2 기준 2가지 이상 근거로 압축된 (source_identifier, target_identifier) 쌍)
        │
        ▼
Evidence 수집(Phase3 6개 항목 — Source/File Evidence 최소 필수)
        │
        ▼
Reviewer 검토(사람이 원문 대조 — 자동 승인 경로 없음)
        │
   ┌────┴────┐
   ▼         ▼
승인       거부(Phase5 Failure Policy로 이동)
   │
   ▼
mapping_status = manual-confirmed(Crosswalk Record 확정, 이번 Task 범위 밖 — 실제 등록은 별도 구현 단계)
   │
   ▼
Crosswalk 등록(YamlCrosswalkRepository.add(), 이번 Task에서 실행하지 않음)
   │
   ▼
TSU Eligible 재확인(manifest_validator TSU_ELIGIBLE=READY와 AND 결합 — 기존 Gate 로직 그대로 재사용, §Phase6)
```

**Reviewer는 최소 1인 이상**이어야 하며, Candidate를 제안한 사람과
Reviewer가 동일인이어도 되는지(자기 검토 허용 여부)는 이번 설계에서
확정하지 않는다 — Pilot 규모(10건)에서는 실용적으로 동일인이 될 수
있으나, Corpus-wide 확장 시 별도 정책이 필요할 수 있다는 점만
기록한다(향후 검토 후보).

---

## Phase 5 — Failure Policy

| 상황 | 처리 |
|---|---|
| Candidate Rejected(Reviewer가 원문 대조 후 불일치로 판단) | Crosswalk Record 생성하지 않음. 거부 사유를 별도 로그(이번 Task 범위 밖, 구현 단계에서 형식 결정)에 남길 것을 권고 — 같은 잘못된 후보가 반복 제안되는 것을 막기 위함 |
| Evidence 부족(Source/File Evidence 중 하나라도 없음) | `manual-confirmed` 승격 불가 — `evidence-backed`(있는 근거만) 또는 `unmapped`(근거 자체가 없음)로 유지. 추가 조사 없이 임의로 `manual-confirmed`로 승격하지 않는다(Mapping Policy Rule 3 절대 원칙) |
| Duplicate Identifier(동일 `source_identifier`에 대해 서로 다른 `target_identifier` 후보 2개 이상) | 자동 선택 금지 — 두 후보 전부 사람에게 제시하고, 더 강한 Evidence를 가진 쪽을 사람이 선택. 애매하면 `unmapped` 유지(§Ambiguous Mapping과 동일 처리) |
| Multiple Candidate(동일 `target_identifier`에 여러 `source_identifier`가 매칭되려는 경우) | 이론상 발생 가능(예: 여러 volume이 물리적으로 한 파일에 합본된 경우) — 이 경우 Crosswalk Schema가 이미 N:1 매핑을 구조적으로 허용하므로(레코드 하나당 source→target 1쌍, 여러 레코드가 같은 target을 가리키는 것 자체는 스키마 위반 아님), Validator Check 2(Duplicate source-target pair, 기존 구현)가 정확히 동일한 쌍의 중복만 막고 서로 다른 source가 같은 target을 가리키는 것은 막지 않는다 — 이것이 의도된 것인지는 실제 사례 발생 시 재검토 |
| Ambiguous Mapping(근거가 상충하거나 근거 강도가 비슷한 후보가 여럿) | `unmapped` 유지, 강제로 확정하지 않는다 — 애매함 자체가 "아직 결정할 수 없다"는 정보이므로, 이를 무리하게 해소하려 하지 않는다 |

**공통 원칙**: 모든 실패 상황에서 **기본값은 `unmapped`(또는 근거
있는 만큼만 `evidence-backed`) 유지**이지, 어느 것도 "일단
`manual-confirmed`로 넣고 나중에 고친다"는 방향으로 처리하지 않는다
— TSU Gate가 `manual-confirmed`만 신뢰하도록 이미 구현되어 있으므로
(`scripts/crosswalk/schema.py::GATE_ELIGIBLE_STATUSES`), 이 원칙이
깨지면 Gate 전체의 신뢰성이 무너진다.

---

## Phase 6 — Activation Requirement

```
TSU Activation 허용 조건(전부 AND):

records >= 1
AND
해당 record의 mapping_status == "manual-confirmed"
AND
해당 record의 confidence == "high"(schema.py CONFIDENCE_SCORE, 기존 구현 — Gate가 이미 강제 중)
AND
대응하는 Manifest entry의 TSU_ELIGIBLE == "READY"(manifest_validator.py, 기존 구현)
```

이 조건은 **이미 코드로 구현되어 있다** — `scripts/crosswalk/
tsu_gate.py::check_tsu_gate()`와 `CrosswalkRecord.is_gate_eligible()`
가 정확히 이 4개 조건을 검사한다(NAE-TSU-GATE-RELIABILITY-
IMPLEMENTATION-001, NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001에서
실측 검증 완료). 이번 설계가 새로 추가하는 것은 **이 조건을 만족하는
"최초의 1건"을 어떻게 사람이 확정하는가**(Phase1~5)이지, Gate
판정 로직 자체가 아니다.

**Pilot 규모 실제 적용 시 최소 요구**: `records >= 1`이라고 했지만,
Registry Source 10건 전부가 TSU_ELIGIBLE=READY 상태(기존 확인)이므로,
Activation "가능"과 "의미 있는 규모"는 다르다 — 최소 1건이라도
`manual-confirmed`가 생기면 Gate는 통과시키지만, 그것이 곧 "TSU
Pipeline이 실용적으로 가동됐다"는 뜻은 아니다. 이 구분은 Phase E
(Activation) 단계의 판단 사항으로 남긴다.

---

## Phase 7 — Architecture Audit

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    scripts/crosswalk/ resources/theological_sources/ NAE/corpus/raw \
    NAE/corpus/canonical NAE/corpus/tsu docs/architecture/
?? scripts/crosswalk/
```

`scripts/crosswalk/`의 `??` 표시는 이전 작업(NAE-CROSSWALK-*
시리즈)에서 이미 만들어진 뒤 아직 git commit되지 않은 기존 파일 —
이번 Task가 그 안의 어떤 파일도 수정(`M`)하지 않았다. 나머지 8개
경로(`core/`, `scripts/adapters/`, `scripts/migration_engine.py`,
`resources/theological_sources/`, `NAE/corpus/{raw,canonical,tsu}`,
`docs/architecture/`)는 전부 아무 표시 없음(완전 무변경).

```
$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**Production 데이터 변경 0건 재확인.**

---

## Required Questions

| 질문 | 답변 |
|---|---|
| Q1. Manual Mapping 후보는 어떻게 선정하는가? | Phase2 5가지 근거(작품명/저자/Edition/Source Evidence/File Evidence) 중 **최소 2가지가 독립적으로 일치**해야 후보 — identifier 이름의 우연한 유사성(`AF1815` 사례, §Phase2)만으로는 후보가 될 수 없다. |
| Q2. Evidence가 충분하다는 기준은 무엇인가? | Phase3의 6개 필드 중 **Source Evidence + File Evidence 둘 다** 확보돼야 `manual-confirmed` 가능 — 하나만 있으면 `evidence-backed`(확정 전 단계)에 머무른다. |
| Q3. manual-confirmed 승인은 누가 할 수 있는가? | 사람(Reviewer) — 자동 승인 경로는 설계에 존재하지 않는다(Phase4, "Reviewer 검토" 단계가 필수 게이트). Candidate 제안자와 Reviewer가 동일인이어도 되는지는 이번 설계에서 미확정(Pilot 규모에서는 실용적으로 허용 가능, Corpus-wide 확장 시 재검토 필요 — §Phase4). |
| Q4. Duplicate Mapping은 어떻게 처리하는가? | 동일 source에 대한 복수 target 후보는 자동 선택 없이 사람에게 제시, 더 강한 Evidence 쪽을 채택하거나 애매하면 `unmapped` 유지(§Phase5). |
| Q5. TSU Activation 최소 조건은 무엇인가? | `records>=1 AND mapping_status=manual-confirmed AND confidence=high AND TSU_ELIGIBLE=READY` — 이 조건은 이미 코드로 구현·검증되어 있음(§Phase6). |
| Q6. Retrieval Architecture에 영향이 있는가? | **없음.** 이번 설계 전체가 Crosswalk Record 확정 절차(사람의 검토 워크플로우)만 다루며, `core/retrieval.py`나 TSU 생성 이후 단계를 전혀 언급하지 않는다 — git status로 무변경 재확인(§Phase7). |

---

## 종합 — 이번 설계가 다음에 남기는 것

1. Phase1~6에서 정의한 절차는 **문서일 뿐, 아직 어느 코드에도
   구현되지 않았다** — Reviewer가 실제로 이 절차를 따라 첫 매핑을
   확정하려면, 이 워크플로우를 보조하는 도구(예: Evidence 입력 폼,
   Reviewer 승인 CLI)가 필요할 수 있으나 이는 별도 구현 단계의
   판단 사항이다.
2. Phase1 실측에서 canonical 3건 중 2건(`PBC1765`/`SLBC1689`)이
   이전 조사 시점보다 콘텐츠가 채워져 있음을 새로 확인했다 — 그러나
   RAW 메타데이터 부재로 제목/저자 등 1차 근거 자료가 없어, 지금
   당장 이 3건에 대해 Evidence를 갖춘 후보를 만들 수 있는 상태는
   아니다(§Phase1 "연결 상태 요약"). 실제 Candidate 발굴은 이
   설계와 별개로, 원문 접근 경로 확보가 선행되어야 할 수 있다.
