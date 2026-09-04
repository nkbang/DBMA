# NAE TSU Pipeline Contract Design 001

**Project:** NAE-TSU-PIPELINE-PREFLIGHT-001 Phase 2
**작성일:** 2026-08-05
**성격:** Design Only — `NAE/pipeline/tsu/`, `core/*`, Migration Engine,
ADR 전부 무수정. `NAE/corpus/{canonical,raw,tsu}/` 데이터 변경 없음.

---

## 1. Phase 1 감사 결과 요약(설계의 전제)

### Input Source

```
CURRENT INPUT:
  NAE/corpus/canonical/{identifier}/canonical.json   (주 입력)
  NAE/corpus/raw/archive_org/{category}/{identifier}/metadata.json  (보조 조회)
  식별자 목록 산출 방식: canonical_root.iterdir()로 하위 디렉토리를 그대로 나열
                          (NAE/pipeline/tsu/builder.py::build_tsu_for_all)

EXPECTED INPUT:
  Manifest Layer controlled source
  (manifest_validator.py가 계산하는 TSU_ELIGIBLE=READY 판정을 통과한
   Manifest entry만)
```

### Gate Bypass 확인(grep 결과)

```
$ grep -R "TSU_ELIGIBLE" NAE/pipeline    → 결과 없음
$ grep -R "canonical_id" NAE/pipeline    → 결과 없음
$ grep -Ri "manifest" NAE/pipeline --include="*.py"  → 결과 없음
$ grep -R "schema_version|authority_id|legacy_id|manifest_id" NAE/pipeline --include="*.py"
  → "schema_version" 매칭은 전부 `tsu_schema_version`(TSU 레코드 자체
    shape 버전, NAE/pipeline/embed/hashing.py 등) — Registry/Manifest
    schema_version과 무관. authority_id/legacy_id/manifest_id 매칭 0건.
```

**결론: TSU Pipeline은 Manifest/Registry Gate를 "우회"하는 게 아니라,
애초에 그 존재 자체를 모른다** — 코드에 그것을 읽는 지점이 전혀 없다.

### 결정적 추가 발견 — Identifier 공간이 서로 겹치지 않는다

```
NAE/corpus/canonical/ 실제 디렉토리: PBC1742, PBC1765, SLBC1689
Registry/Manifest 실제 source_id:    BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX,
                                      BAP-MISS-FULLER-VOL01~08

$ grep -rn "PBC1742|PBC1765|SLBC1689" resources/theological_sources/authority/ resources/theological_sources/manifest/
  → 결과 없음(Registry/Manifest 어디에도 이 3개 ID가 존재하지 않음)

$ ls NAE/corpus/canonical/PBC1742/
  → normalize_report.json만 존재, canonical.json 없음
    (즉 TSU Pipeline이 지금 당장 실행돼도 처리할 실제 콘텐츠가 없다)
```

이는 단순한 "필터 하나 추가하면 되는" 문제가 아니다 — **Manifest/
Registry가 관리하는 source_id 공간과 TSU Pipeline이 순회하는
canonical identifier 공간이 지금 시점에 완전히 분리된 두 세계**다.
Contract를 정의하려면 이 둘을 잇는 **crosswalk(대응 관계)** 자체를
먼저 설계해야 한다 — 이것이 Phase 4에서 "Option A(설계만, ADR 필요)"
를 선택한 핵심 근거다.

---

## 2. Contract 정의

### TSU Pipeline Input(목표 상태, 아직 미구현)

```yaml
manifest_id: <Manifest entry의 manifest_id>
source_id: <Registry Source entity ID — 기존 FK 문자열, Option B 원칙상 불변>
authority_id: <상위 Author/Work/Edition 참조 체인 — Registry FK 그대로>
canonical_id: <ADR-017 canonical 표기 — Author/Work/Edition/Volume/Source 각 계층>
schema_version: <Manifest schema version — 현재 v2.2.x>
processing_status: <5개 lifecycle 필드로부터 파생 — 현재 manifest_validator.py가 계산하는 TSU_ELIGIBLE과 동일 판정 로직>
```

### Gate

```
processing_status == TSU_ELIGIBLE(READY)  # manifest_validator.py::compute_tsu_eligible()의 판정 결과
```

만 TSU Builder 입력으로 허용한다. `BLOCKED` 판정인 Manifest entry는
TSU Pipeline에 전달되지 않는다.

### 아직 정의되지 않은 것(이번 설계에서 미해결로 남기는 부분)

- **identifier crosswalk**: Manifest `source_id`(예: `BAP-CHURCH-DAGG-001`)
  → TSU Pipeline `identifier`(예: `PBC1742`류 archive.org 스타일 slug)
  간의 변환 규칙이 아직 없다. 두 후보:
  1. Registry `sources.yaml`의 `file_path` 필드(`NAE/corpus/raw/
     archive_org/church_order/Dagg_Church_Order/`)에서 identifier를
     역산 — 그러나 현재 `file_path` 값과 실제 `NAE/corpus/raw/
     archive_org/`의 디렉토리 구조가 정확히 일치하는지 미검증
  2. `source_id`를 canonical identifier로 그대로 승격(예:
     `BAP-CHURCH-DAGG-001` = TSU Pipeline `identifier`) — 그러나 이는
     canonical/raw 디렉토리 구조 자체를 바꿔야 할 수 있어 RAW/canonical
     경로 변경(이번 Task 금지 목록) 소지가 있음
  - 이 결정은 ADR-019(Manifest Layer) 또는 신규 ADR 범위의 사안 —
    이번 설계 문서는 문제를 정의만 하고 확정하지 않는다(§Phase4).

---

## 3. TSU 생성 Flow

### 현재

```
NAE/corpus/raw/archive_org/{category}/{identifier}/
        │
        ▼ (identifier로 디렉토리 직접 순회)
NAE/corpus/canonical/{identifier}/canonical.json
        │
        ▼ (Gate 없음)
NAE/pipeline/tsu/builder.py::build_tsu_for_all()
        │
        ▼
NAE/corpus/tsu/{identifier}/tsu.json
```

### 변경 목표(향후, 이번 Task 범위 밖)

```
RAW(NAE/corpus/raw/)
        │
Manifest Layer(resources/theological_sources/manifest/**, ADR-019)
        │
Validator(manifest_validator.py — Authority Reference FK + Processing Lifecycle)
        │
TSU_ELIGIBLE 판정(compute_tsu_eligible, READY만 통과)
        │
        ▼ (identifier crosswalk 필요 — §2 미해결 항목)
TSU Builder(NAE/pipeline/tsu/, 기존 로직 재사용)
        │
        ▼
TSU
```

**핵심**: 기존 TSU Builder(`parser.py`/`claim.py`/`doctrine.py` 등 claim
추출 로직)는 그대로 재사용 가능하다 — 바뀌어야 하는 것은 "어떤
identifier를 처리 대상으로 삼을지 결정하는 단 하나의 지점"
(`build_tsu_for_all`의 `canonical_root.iterdir()` 호출부)뿐이다. 이
지점만 Manifest 기반 필터로 교체하면 나머지 파이프라인은 변경 불필요
— 단, §2에서 확인했듯 그 필터가 의존할 identifier crosswalk이 아직
정의되지 않았다는 것이 남은 선행 과제다.
