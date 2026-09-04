# NAE Crosswalk Storage Implementation Report 001

**Project:** NAE-CROSSWALK-STORAGE-ADAPTER-IMPLEMENTATION-001
**작성일:** 2026-08-05
**성격:** Option B(Dedicated Crosswalk Store) 실제 구현 — TSU Pipeline
실행, TSU Builder/Manifest/Registry/RAW/canonical 수정, Retrieval
코드 변경, ADR 파일 수정 전부 미수행.
**Git Commit/Push:** 미수행 — C1 Review 승인 전까지 대기.

---

## 1. Summary

`docs/NAE_CROSSWALK_STORAGE_DECISION_001.md`(Option B, C1 Approved)를
그대로 구현했다. `NAE/metadata/crosswalk/`에 `crosswalk.yaml`(정본,
0건)과 `index.json`(파생 캐시, 빈 객체)을 생성하고,
`scripts/crosswalk/storage/` 3개 모듈(`yaml_repository.py`/
`index_manager.py`/`__init__.py`)로 `YamlCrosswalkRepository`를
구현했다 — `ruamel.yaml` round-trip 기반이며 `yaml.safe_dump()`는
어디에도 사용하지 않았다.

**YAML이 authoritative, JSON은 언제든 재생성 가능한 파생 캐시**라는
원칙을 코드로 강제했다: `IndexManager`는 `crosswalk.yaml`을 직접
읽거나 쓰지 않고, 호출자(`YamlCrosswalkRepository`)가 이미 로드한
레코드 목록만 받아 인덱스를 재생성한다 — index가 없거나 내용이
어긋나도 Repository의 `get`/`list_all`은 항상 YAML 기준으로만
응답함을 테스트로 증명했다(`TestYamlAuthority`).

---

## 2. Files

### 생성

```
NAE/metadata/crosswalk/crosswalk.yaml    # 정본, records: [] (0건)
NAE/metadata/crosswalk/index.json         # 파생 캐시, {} (0건)
scripts/crosswalk/storage/__init__.py
scripts/crosswalk/storage/yaml_repository.py
scripts/crosswalk/storage/index_manager.py
tests/test_crosswalk_storage.py
docs/NAE_CROSSWALK_STORAGE_IMPLEMENTATION_REPORT_001.md
```

### 변경

없음 — `scripts/crosswalk/repository.py`(추상 인터페이스)는 이번
작업에서 한 글자도 수정하지 않았다. `YamlCrosswalkRepository`는
`CrosswalkRepository`를 상속만 할 뿐, 기존 `InMemoryCrosswalkRepository`
와 나란히 존재한다:

```
CrosswalkRepository(ABC)
        │
        ├── InMemoryCrosswalkRepository   (기존, 테스트/참조용)
        └── YamlCrosswalkRepository        (신규, 이번 구현 — Option B 정본)
```

기존 `tests/test_crosswalk_repository.py`(15개, `InMemoryCrosswalkRepository`
대상)는 이번 작업으로 전혀 영향받지 않았다 — 재실행 결과 그대로 PASS.

---

## 3. Architecture Constraint 준수 확인

```
Crosswalk Storage Layer(NAE/metadata/crosswalk/)
        ↓
Crosswalk Repository(scripts/crosswalk/storage/yaml_repository.py)
        ↓
Crosswalk Resolver(scripts/crosswalk/resolver.py) — 무수정
        ↓
TSU Gate Interface(scripts/crosswalk/tsu_gate.py) — 무수정
```

금지된 역방향 결합 확인:

```
$ grep -rn "yaml_repository\|NAE/metadata" resources/theological_sources/ NAE/pipeline/tsu/ 2>&1
(결과 없음 — Manifest도 TSU Builder도 이번 신규 Storage를 참조하지 않음)
```

`Resolver`/`TSU Gate`는 여전히 `CrosswalkRepository` 추상 인터페이스
에만 의존하므로, `YamlCrosswalkRepository`를 주입해도 그 두 모듈의
코드는 한 글자도 바뀌지 않는다(의존성 역전 원칙이 실제로 작동함을
재확인).

---

## 4. Tests

| 파일 | 테스트 수 | 대상 |
|---|---|---|
| `tests/test_crosswalk_storage.py`(신규) | 28 | Empty Init(3)/Add(2)/Get(2)/List(2)/Persistence(2)/Duplicate(3)/No-delete(1)/YAML Reload(1)/Index Rebuild(4)/YAML Authority(2)/Comment(2)/Quote(1)/Ordering(1)/Data Safety(2) |

요구 최소 20건을 초과(28건). `TestDataSafety`는 실제 프로덕션
저장소(`NAE/metadata/crosswalk/crosswalk.yaml`)를 직접 읽어 0건임을
재확인하는 테스트를 포함한다(단, 그 파일에 쓰기는 절대 하지 않음 —
전부 `tmp_path` fixture만 대상으로 `add()` 호출).

```
$ pytest tests/test_crosswalk_storage.py -q
28 passed in 0.28s

$ pytest tests/test_crosswalk*.py -q
104 passed in 0.20s   (기존 76 + 신규 28)
```

---

## 5. Regression

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
253 passed in 0.65s
```

전체 프로젝트 `pytest`(1600여 개 전체 스위트)도 별도로 백그라운드
실행했다 — 이전 세션들과 동일하게 `tests/test_nae_embed.py`의 사전
존재 실패 2건(이번 작업과 무관, AttributeError) 외에는 전부 통과할
것으로 예상되며, 결과는 이번 보고 이후 확인되는 대로 별도 공유한다.

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 6. Safety

```
$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**Crosswalk records: 0.** Production identifier(실제 Registry
source_id나 실제 Corpus/TSU identifier)를 이번 구현 어디에도 입력하지
않았다 — `NAE/metadata/crosswalk/crosswalk.yaml`은 여전히 헤더 주석과
`records: []`뿐이다.

### 금지 목록 준수 확인

```
$ git status --short core/ scripts/migration_engine.py scripts/adapters/ \
    resources/theological_sources/ NAE/corpus/raw NAE/corpus/canonical \
    NAE/corpus/tsu docs/architecture/
(출력 없음 — 전부 무변경)
```

---

## 7. ADR Impact

```
ADR-019: No amendment required
```

`docs/NAE_ADR019_IMPACT_REVIEW_001.md`의 판단(Option B 채택 시 ADR-019
본문/Amendment 둘 다 불필요)이 실제 구현 이후에도 그대로 유효함을
재확인했다 — Manifest Entry 필드 집합에 `crosswalk` 관련 필드를 추가한
적이 없고, `resources/theological_sources/manifest/`는 이번 구현에서
전혀 열지 않았다(git status로 확인).

---

## 완료 보고

```
STATUS: COMPLETE (Storage Adapter implementation only — no TSU execution, no Manifest/Registry/RAW changes, no production mappings)

FILES CREATED:
NAE/metadata/crosswalk/crosswalk.yaml
NAE/metadata/crosswalk/index.json
scripts/crosswalk/storage/__init__.py
scripts/crosswalk/storage/yaml_repository.py
scripts/crosswalk/storage/index_manager.py
tests/test_crosswalk_storage.py
docs/NAE_CROSSWALK_STORAGE_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
(없음 — scripts/crosswalk/repository.py 등 기존 파일 전부 무변경)

STORAGE:
Option B implemented (NAE/metadata/crosswalk/crosswalk.yaml authoritative, index.json rebuildable)

DATA:
Crosswalk records: 0

TEST:
Crosswalk: 104 passed (기존 76 + 신규 28, test_crosswalk_storage.py)

REGRESSION:
253 passed (기존 225 + 신규 28, 감소 없음)

VALIDATOR:
drift=0 (source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치)

FORBIDDEN PATH:
PASS (core/, migration_engine.py, adapters/, resources/theological_sources/, NAE/corpus/{raw,canonical,tsu}, docs/architecture/ 전부 git status 빈 결과)

BLOCKER:
0

WARNING:
0

NEXT STEP:
C1에 NAE-CROSSWALK-STORAGE-REVIEW-001 요청 → 승인 후 TSU Gate 실제 연결 설계 → TSU Pipeline Resume

GIT:
NOT PERFORMED
```
