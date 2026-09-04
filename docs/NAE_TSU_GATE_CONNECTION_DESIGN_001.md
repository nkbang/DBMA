# NAE TSU Gate Connection Design 001

**Project:** NAE-TSU-GATE-CONNECTION-DESIGN-001
**작성일:** 2026-08-05
**성격:** Design Only — `NAE/pipeline/tsu/`, TSU 생성, Corpus/RAW 접근,
Manifest/Registry 변경, Retrieval 변경, ADR 파일 수정 전부 미수행.

---

## 0. 현재 상태 재확인

```
현재:  Manifest Layer ---X(단절)--- TSU Pipeline
목표:  Manifest → Crosswalk Resolver → TSU Gate → TSU Builder
```

이미 존재하는 조각(코드 무수정, 이번 문서에서 그대로 인용):

- `scripts/crosswalk/resolver.py::CrosswalkResolver.resolve()`/
  `resolve_record()` — exact match만, fuzzy 없음
- `scripts/crosswalk/tsu_gate.py::check_tsu_gate()` — `TSU_ELIGIBLE`
  ∧ `mapping_status==manual-confirmed` 판정(현재는 `eligible: bool`
  + `reason: str`의 2필드 결과만 반환 — 아래 §4에서 3-상태 모델로
  확장 설계)
- `docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md` — Contract 필드/Flow 최초
  설계(이번 문서가 그 후속)

**이번 문서가 새로 하는 일**: 위 조각들을 실제로 어떻게 배선할지
(Gate Contract 정식화, Resolver/TSU Builder 책임 경계 명문화, 3-상태
Failure Policy) 확정한다 — 코드는 그대로 두고 계약만 고정한다.

---

## 1. Gate Contract 정의

### TSU Gate 입력

```yaml
source_id: string        # Registry/Manifest 정본 FK(Option B 불변값)
canonical_id: string      # ADR-017 canonical 표기(참조용)
legacy_id: array[string]  # 참조용(선택)
tsu_eligible: bool         # manifest_validator.py::compute_tsu_eligible()의 판정 결과
mapping_status: string     # Crosswalk Record의 mapping_status(schema.py MappingStatus)
confidence: string | null  # Crosswalk Record의 confidence(schema.py Confidence)
```

`canonical_id`/`legacy_id`는 Gate 판정 자체에는 쓰이지 않는다(판정은
`tsu_eligible`/`mapping_status`/`confidence` 3개만으로 충분 —
`NAE_TSU_IDENTIFIER_CONTRACT_001.md` §4와 동일 결론) — 그러나 TSU
레코드에 원본 계보를 남기기 위한 참조값으로 입력 계약에 포함한다.

### Gate 통과 조건

```
TSU_ELIGIBLE == READY
AND
mapping_status == "manual-confirmed"
AND
confidence_score(confidence) >= threshold   # threshold = 1.0(HIGH만), schema.py CONFIDENCE_SCORE 재사용
```

이는 이미 구현된 `scripts/crosswalk/tsu_gate.py::check_tsu_gate()`와
`scripts/crosswalk/schema.py::CrosswalkRecord.is_gate_eligible()`의
로직을 그대로 계약으로 문서화한 것이다(NAE-CROSSWALK-ADAPTER-
IMPLEMENTATION-001에서 이미 구현·61개 테스트로 검증됨) — 이번
설계에서 새 판정 로직을 만들지 않는다.

---

## 2. Resolver 책임 분리

### Crosswalk Resolver 책임(정확히 이것만)

```
identifier translation only
  = source_identifier(Registry/Manifest source_id) -> target_identifier(Corpus/TSU identifier)
```

`scripts/crosswalk/resolver.py`의 현재 구현(`resolve()`/
`resolve_record()`)이 정확히 이 범위 안에 있음을 재확인:

```
$ grep -n "def " scripts/crosswalk/resolver.py
    def resolve(self, source_identifier: str) -> str | None:
    def resolve_record(self, source_identifier: str) -> CrosswalkRecord | None:
```

두 메서드 다 문자열/레코드 하나를 반환할 뿐, 파일을 열거나(content
loading) TSU를 만들거나(TSU generation) 벡터를 계산하거나(embedding)
검색을 수행하지(retrieval) 않는다 — import 구조로도 재확인:

```
$ grep -n "^import\|^from" scripts/crosswalk/resolver.py
from .repository import CrosswalkRepository
from .schema import CrosswalkRecord
```

`NAE/pipeline/tsu/`, `core/retrieval.py`, `NAE/corpus/` 어느 것도
import하지 않는다 — Resolver는 Crosswalk 저장소 인터페이스만 안다.

### Resolver가 하지 않는 것(명시적 금지 확인)

| 금지 항목 | 확인 |
|---|---|
| content loading(RAW/canonical 파일 읽기) | Resolver 코드에 `Path.read_text`/`open` 호출 없음 |
| TSU generation | `NAE/pipeline/tsu/builder.py` import 없음 |
| embedding | `NAE/pipeline/embed/` import 없음 |
| retrieval | `core/retrieval.py` import 없음 |

---

## 3. TSU Builder 보호

### 목표 구조

```
TSU Builder(NAE/pipeline/tsu/, 무수정)
     ↑
     │  identifier 목록만 전달(claim 추출 로직 등 내부 무관여)
     │
TSU Gate Adapter(scripts/crosswalk/tsu_gate.py, 이미 존재 — 순수 판정 함수)
     ↑
     │  (tsu_eligible, crosswalk_record) 조회 결과를 넘겨받음
     │
[미구현 — 다음 단계 설계 대상] Gate Orchestrator
     │  manifest_validator.py::compute_tsu_eligible() 호출
     │  CrosswalkResolver.resolve_record() 호출
     ▼
Manifest 목록
```

### 삽입 지점(재확인, `NAE_TSU_IDENTIFIER_CONTRACT_001.md` §5와 동일)

`NAE/pipeline/tsu/builder.py::build_tsu_for_all()`이 지금
`canonical_root.iterdir()`로 identifier를 직접 열거하는 **딱 그
한 줄**만 교체 대상이다. `build_tsu_for_identifier()`(claim 추출,
TSU 레코드 생성 등 내부 로직)는 이번에도, 다음 구현 단계에서도
**무수정**을 목표로 한다 — 이번 설계 문서는 그 목표를 재확인만 하고,
실제 교체는 이번 Task 범위 밖(TSU Builder 수정 금지).

---

## 4. Failure Policy 정의

기존 `check_tsu_gate()`는 `eligible: bool` 2-상태만 반환한다. 이번
설계는 **3-상태 모델**로 확장할 것을 제안한다(코드 변경은 이번
Task에서 하지 않음 — 다음 구현 단계의 설계 근거로만 기록):

| 상황 | 결과 | 현재 코드와의 대응 |
|---|---|---|
| Mapping 없음(Crosswalk Record 자체가 없음) | `TSU_GATE_BLOCK` | `check_tsu_gate(tsu_eligible=True, crosswalk_record=None)` → `eligible=False` |
| confidence 부족(HIGH 미만) | `TSU_GATE_BLOCK` | `is_gate_eligible()`이 `False` → `eligible=False` |
| mapping_status가 manual-confirmed 아님 | `TSU_GATE_BLOCK` | 동일 |
| `TSU_ELIGIBLE` 자체가 `READY` 아님 | `TSU_GATE_BLOCK` | `tsu_eligible=False` → `eligible=False` |
| **Crosswalk Storage 오류**(`crosswalk.yaml` 파싱 실패, 파일 I/O 오류 등) | `TSU_GATE_ERROR` | **미구현** — 현재 `YamlCrosswalkRepository`는 이런 오류를 그대로 예외로 던진다(`SchemaError`/`ruamel.yaml` 파싱 예외 등), Gate 레벨에서 이를 `BLOCK`과 구분되는 `ERROR`로 잡아 반환하는 wrapper가 없음 |
| 승인 Mapping(모든 조건 충족) | `TSU_GATE_PASS` | `eligible=True` |

**설계 결정**: `BLOCK`(정상적으로 자격 미달 판정)과 `ERROR`(저장소
자체가 고장난 상태)는 반드시 구분되어야 한다 — `BLOCK`은 "아직 사람
확인을 못 받았다"는 정상적인 대기 상태이고, `ERROR`는 "Crosswalk
Layer 자체를 신뢰할 수 없다"는 운영 이상 상태이기 때문이다. 후자를
`BLOCK`과 같이 취급하면, 저장소 손상을 그냥 "아직 매핑 안 됨"으로
착각해 방치할 위험이 있다.

이 3-상태 모델(`TSU_GATE_PASS`/`TSU_GATE_BLOCK`/`TSU_GATE_ERROR`)을
실제로 코드에 반영하는 것은 **다음 구현 단계**의 작업이다 — 이번
Task는 설계만 고정한다.

---

## 5. Data Boundary 검증

```
$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**Crosswalk records = 0.** §1의 Gate 통과 조건 중
`mapping_status == "manual-confirmed"`를 만족하는 레코드가 저장소에
하나도 없으므로, 지금 이 설계를 그대로 코드로 옮기더라도 **모든
Manifest entry가 `TSU_GATE_BLOCK`으로 귀결된다** — 즉:

```
No TSU execution possible(현재 데이터 상태 기준)
```

이는 결함이 아니라 의도된 안전장치다 — Mapping Policy Rule 3(추측
금지)를 지키는 한, 사람이 검증한 매핑이 생기기 전까지 TSU Gate는
구조적으로 전부 막혀 있어야 정상이다.

---

## 6. ADR Impact Analysis

| ADR | 검토 | 결론 |
|---|---|---|
| ADR-016(Metadata Authority Model) | TSU Gate는 Author/Work/Edition/Volume/Source 5-tier 모델을 참조만 하고(canonical_id/legacy_id 필드), 그 모델 자체를 바꾸지 않음 | 영향 없음 |
| ADR-017(ID Governance) | canonical_id authority 완전 유지 — Gate는 canonical_id를 읽기만 함(Crosswalk ADR Impact 001과 동일 결론) | 영향 없음 |
| ADR-018(Periodical Extension) | Gate 입력 계약(`source_id`/`canonical_id`/`tsu_eligible`/`mapping_status`/`confidence`)은 Periodical/Monograph 구분 없이 동일하게 적용 가능(ADR-018이 이미 확립한 "동일 Manifest Entry 구조를 공유" 패턴과 일치) | 영향 없음, 호환 확인 |
| ADR-019(Manifest Lifecycle) | Gate는 `manifest_validator.py::compute_tsu_eligible()`의 **결과값**만 소비하고, Manifest Lifecycle 필드나 전이 규칙 자체를 바꾸지 않음 | 영향 없음 |

```
결론: No amendment required
```

---

## 7. Required Questions

| 질문 | 답변 |
|---|---|
| Q1. TSU Gate 설계가 기존 TSU Builder와 충돌하는가? | **아니오.** §3에서 확인한 대로 유일한 교체 지점은 identifier 열거 한 줄이며, claim 추출 등 TSU Builder 내부 로직은 무수정 목표를 유지한다. 이번 Task에서 실제 교체를 수행하지 않았으므로 충돌 자체가 발생할 여지가 없다(git status로 무변경 재확인, §9). |
| Q2. Crosswalk Resolver 책임 범위가 적절한가? | **예.** §2에서 코드 실측(import 구조, 메서드 목록)으로 "identifier translation only"라는 책임이 정확히 지켜지고 있음을 확인했다 — content loading/TSU generation/embedding/retrieval 중 어느 것도 하지 않는다. |
| Q3. Manifest Layer 책임을 침범하는가? | **아니오.** Gate는 `manifest_validator.py`의 `TSU_ELIGIBLE` 판정 **결과**만 입력으로 받는다 — Manifest 파일을 직접 읽거나 쓰지 않으며(이번 Task에서 `resources/theological_sources/`를 전혀 열지 않음, §9), Manifest Lifecycle 필드의 소유권은 여전히 ADR-019/Manifest Validator에 있다. |
| Q4. ADR-016~019 영향이 있는가? | **없음.** §6 전체 표 참고 — 4개 ADR 전부 "영향 없음", Amendment 불필요. |
| Q5. TSU Pipeline Resume 조건을 만족하는가? | **아니오, 아직.** Gate Contract는 설계됐지만 (1) 3-상태 Failure Policy가 아직 코드로 구현되지 않았고(§4), (2) Crosswalk records가 0건이라 어떤 Manifest entry도 통과할 수 없다(§5) — 두 조건 다 다음 단계 작업 대상. |
| Q6. Retrieval Architecture가 보호되는가? | **예.** 이번 설계 어디에도 `core/retrieval.py`를 참조하거나 수정하는 내용이 없다 — Gate는 TSU Builder 앞단에서 끝나며, Retrieval은 그보다 하류에 있어 이번 설계의 대상이 아니다(git status로 무변경 재확인). |

---

## 8. Regression

```
$ pytest tests/test_source_validator_v2.py tests/test_validator_v22.py \
         tests/test_manifest_validator.py tests/test_authority_validator.py \
         tests/test_authority_validator_canonical.py tests/test_migration_lock.py \
         tests/test_migration_checkpoint.py tests/test_migration_engine.py \
         tests/test_registry_adapter.py tests/test_manifest_adapter.py \
         tests/test_pilot_executor.py tests/test_comment_preservation.py \
         tests/test_crosswalk_schema.py tests/test_crosswalk_repository.py \
         tests/test_crosswalk_validator.py tests/test_crosswalk_resolver.py \
         tests/test_crosswalk_tsu_gate.py tests/test_crosswalk_storage.py -q
253 passed
```

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 9. Forbidden Scope 확인

```
$ git status --short core/ NAE/corpus/raw NAE/corpus/canonical NAE/corpus/tsu \
    resources/theological_sources/ scripts/migration_engine.py NAE/pipeline/tsu
(출력 없음)
```

**NO CHANGE.**

---

## 완료 보고

```
STATUS: COMPLETE (design only)

FILES CREATED:
docs/NAE_TSU_GATE_CONNECTION_DESIGN_001.md

FILES MODIFIED:
(없음)

TSU GATE:
DESIGNED / NOT IMPLEMENTED

CROSSWALK RECORDS:
0

TSU EXECUTION:
NOT RUN

ADR IMPACT:
No amendment required (ADR-016/017/018/019 전부 영향 없음, §6)

VALIDATOR:
DRIFT=0

FORBIDDEN PATH:
PASS

BLOCKER:
0

WARNING:
1 (3-상태 Failure Policy(TSU_GATE_PASS/BLOCK/ERROR)가 아직 코드로 구현되지 않음 — 현재 tsu_gate.py는 PASS/BLOCK만 구분 가능하고 ERROR 상태는 미구현, §4)

NEXT STEP:
C1 TSU Gate Design Review 요청 → 승인 후 (1) 3-상태 Failure Policy 구현 + Gate Orchestrator(§3 미구현 부분) 설계/구현, (2) Crosswalk Record Population Design(실제 매핑 최소 1건 이상 사람 검증) → Manual Mapping Approval → TSU Pipeline Resume

GIT:
NOT PERFORMED
```
