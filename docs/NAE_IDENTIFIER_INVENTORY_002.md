# NAE Identifier Inventory 002

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 1
**작성일:** 2026-08-05
**성격:** 읽기 전용 실측 조사 — 4개 계층에 실제로 존재하는 identifier를
전부 나열한다. 코드/데이터 변경 없음.

---

## 1. Authority Layer

Registry(`resources/theological_sources/authority/`)의 필드별 실제 값.

### Author(3건)

| author_id | canonical_id | legacy_id |
|---|---|---|
| `dagg_john_l` | `dagg_john_l` | (없음 — 이미 canonical) |
| `hiscox_edward_t` | `hiscox_edward_t` | (없음 — 이미 canonical) |
| `FULLER-ANDREW-001` | `fuller_andrew` | `["FULLER-ANDREW-001"]` |

### Work(3건, author_id FK 포함)

| work_id | canonical_id | legacy_id | author_id(FK) |
|---|---|---|---|
| `WORK-DAGG-CHURCH-ORDER-001` | `dagg_john_l_church_order` | `["WORK-DAGG-CHURCH-ORDER-001"]` | `dagg_john_l` |
| `WORK-HISCOX-STANDARD-MANUAL-001` | `hiscox_edward_t_standard_manual` | `["WORK-HISCOX-STANDARD-MANUAL-001"]` | `hiscox_edward_t` |
| `FULLER-COMPLETE-WORKS-001` | `fuller_andrew_complete_works` | `["FULLER-COMPLETE-WORKS-001"]` | `FULLER-ANDREW-001` |

### Edition(4건)/Volume(8건)/Source(10건)

이전 문서(`NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md` §1,
`NAE_REGISTRY_SCHEMA_EXTENSION_001.md` §2)에 이미 전수 기록되어 있음 —
이번 문서에서 재나열하지 않고 참조만 한다(문서 간 불일치 위험 회피,
Resolution Plan-001과 동일 원칙). 핵심: **Source 10건의 `source_id`가
이번 Crosswalk 설계의 실질적 대상**이다:

```
BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX,
BAP-MISS-FULLER-VOL01 ~ BAP-MISS-FULLER-VOL08
```

---

## 2. Corpus Layer

### `NAE/corpus/canonical/`(TSU Pipeline이 직접 순회하는 디렉토리)

```
PBC1742
PBC1765
SLBC1689
```

(`PBC1742/`는 `normalize_report.json`만 존재, `canonical.json` 없음 —
실질적으로 처리 가능한 콘텐츠 없음. `PBC1765`/`SLBC1689`도 미확인,
이번 조사는 존재 여부만 확인.)

### `NAE/corpus/quarantine/`

```
PBC1765
```

(canonical과 quarantine에 동일 ID `PBC1765`가 양쪽에 존재 — 상태
전이 중이거나 재검토 대상으로 추정, 이번 조사 범위 밖.)

### `NAE/corpus/raw/archive_org/`(현재 git 추적 상태, 실제 디렉토리)

```
AF1815
PBC1742
TH1612
```

**중요 발견**: Registry `sources.yaml`의 `file_path` 필드가 가리키는
경로(`NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/`,
`NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/` 등)
는 **현재 실제 디렉토리 구조에 존재하지 않는다**(현재 존재하는 것은
`AF1815`/`PBC1742`/`TH1612` 3개뿐, `church_order`/`missions` 하위
디렉토리 자체가 없음). 이는 NAE-GIT-HISTORY-CLEANUP-001(2026-08-03)
에서 대용량 RAW PDF를 git 밖(`~/NAE_CORPUS_RAW/raw/`)으로 백업한 뒤,
git 추적 대상에서 제거한 영향으로 추정된다 — Registry의 `file_path`
필드는 그 정리 작업 이전 시점의 경로를 여전히 기록하고 있다.
**이번 Crosswalk 설계는 이 사실을 발견만 하고 수정하지 않는다**(RAW
경로 변경은 금지 목록).

---

## 3. Manifest Layer

Pilot Manifest(`resources/theological_sources/manifest/pilot/`)의
실제 `manifest_id`/`source_id`(10건, ADR-019 결정에 따라
`manifest_id == source_id` 1:1):

```
BAP-CHURCH-DAGG-001
BAP-CHURCH-HISCOX
BAP-MISS-FULLER-VOL01
BAP-MISS-FULLER-VOL02
BAP-MISS-FULLER-VOL03
BAP-MISS-FULLER-VOL04
BAP-MISS-FULLER-VOL05
BAP-MISS-FULLER-VOL06
BAP-MISS-FULLER-VOL07
BAP-MISS-FULLER-VOL08
```

별도의 `entry_id` 필드는 존재하지 않는다(Manifest Schema Design v1
기준 — `manifest_id`가 곧 entry 식별자).

---

## 4. TSU Layer

### `NAE/pipeline/tsu/`(NAE 전용 TSU Pipeline) 레코드 필드

```yaml
id: "TSU-0000001"                 # 순번 기반, tsu_id 역할
tsu_schema_version: "1"
identifier: <canonical_root의 디렉토리명, 예: PBC1742>
source_identifier: <identifier와 동일 값>
```

`document_id`/`chunk_id` 필드는 **존재하지 않는다** — NAE 전용
파이프라인은 sentence-level candidate 단위로 처리하며(`parser.py`의
`SentenceCandidate`), 그 상위 문서 단위 식별자를 별도로 두지 않는다.

### `core/tsu_builder.py`(레거시 Index Authority, NAE 비전용) 레코드 필드

```yaml
tsu_id: <ID>
document_id: <레거시 registry(dict, 우리 Authority Registry 아님)의 "documents" 키>
chunk_id: <generate_chunk_id(document_id, idx)로 결정적 생성>
```

이 모듈이 참조하는 `registry: dict`는 **우리 Authority Registry가
아니다** — 파라미터명이 같을 뿐 완전히 다른 자료구조(문서 dict)를
가리킨다(§NAE_TSU_PIPELINE_PREFLIGHT_REPORT_001.md에서 이미 확인된
사실 재확인).

---

## 5. 계층 간 겹침 실측 요약

| 비교 | 결과 |
|---|---|
| Authority `source_id`(10) ∩ Manifest `source_id`(10) | **10/10 일치**(Manifest가 Registry Source를 1:1로 참조하도록 설계됐으므로 당연) |
| Manifest `source_id`(10) ∩ Corpus `canonical/`(3: PBC1742/PBC1765/SLBC1689) | **0/10 일치** |
| Authority `sources.yaml.file_path` 경로 ∩ 실제 `NAE/corpus/raw/archive_org/` 디렉토리 | **0/10 일치**(§2 발견) |
| Corpus `canonical/`(3) ∩ TSU `NAE/pipeline/tsu/` 처리 대상(`identifier`) | 코드상 `canonical_root.iterdir()` 그대로 사용 — **1:1 재사용**(단, 내용물 없음) |

**결론**: Authority↔Manifest는 이미 1:1로 잘 연결되어 있다(Migration
Workstream이 검증한 부분). 끊어져 있는 것은 **Manifest↔Corpus/TSU**
구간 하나뿐 — Crosswalk Layer가 메워야 할 지점이 정확히 여기임을
실측으로 확인했다.
