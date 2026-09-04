# NAE Crosswalk Storage Option Analysis 001

**Project:** NAE-CROSSWALK-STORAGE-LOCATION-DESIGN-001
**작성일:** 2026-08-05
**성격:** Architecture Decision 설계 문서 — 코드 변경, 데이터 생성,
Migration 실행 전부 미수행.

---

## 0. 검토 전제

`scripts/crosswalk/repository.py`의 `CrosswalkRepository`(ABC)는 이미
저장 위치를 추상화해 두었다(`NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001`)
— 이번 분석은 그 인터페이스 뒤에 실제로 무엇을 둘지 결정하는 것이며,
결정 이후에도 `CrosswalkResolver`/`CrosswalkValidator` 코드는 전혀
바뀌지 않는다(인터페이스만 만족하는 새 구현체 하나 추가로 끝남).

---

## 1. Option A — Manifest Extension

```yaml
# resources/theological_sources/manifest/pilot/dagg/manifest.yaml (예시)
manifests:
  - manifest_id: BAP-CHURCH-DAGG-001
    source_id: BAP-CHURCH-DAGG-001
    # ... 기존 필드 그대로 ...
    crosswalk:
      target_identifier: <corpus/TSU identifier>
      mapping_status: manual-confirmed
      confidence: high
```

### 장점
- Manifest가 이미 Source 1:1 Entity이므로, 조회 시 추가 파일을 열
  필요 없이 한 번에 확인 가능(접근성)
- TSU Gate 판정 시 Manifest 하나만 읽으면 됨(단순화)

### 위험
- **ADR-019 §3.3(Schema)이 명시한 필수 필드 집합에 없는 새 필드
  (`crosswalk`)를 Manifest Entry에 추가**하는 것이므로, ADR-019
  Schema 정의 확장이 필요 — Amendment 대상이 된다(§ADR019 Impact
  Review에서 상세 분석).
- Manifest의 책임(ADR-019 §2: "이 자료가 지금 파이프라인의 어느
  단계에 있는가" 추적)에 "다른 계층의 identifier로 어떻게
  번역되는가"라는 **다른 종류의 책임**이 섞인다 — 단일 책임 원칙
  위반 소지(Crosswalk Schema Design 001 §1에서 이미 "Authority↔Manifest
  는 잘 연결되어 있으니 건드리지 않는다"고 명시적으로 정한 것과
  방향이 어긋남).
- `mapping_status`가 아직 `unmapped`인 Source가 있으면, Manifest
  Entry 자체가 불완전한 채로 존재해야 함(Manifest는 "생성됨=구조가
  갖춰짐"을 전제하는 ADR-019 Lifecycle과 마찰 가능).

### Audit Requirement 충족 여부
가능(YAML 필드 추가로 8개 속성 전부 표현 가능) — 단 Manifest 파일이
이미 갖고 있는 Audit 필드(`created_at`/`updated_at`/`verified_by`)와
Crosswalk 고유 Audit 필드(`created_at`/`verified_at`)가 이름은 같고
의미는 다른 두 세트로 한 파일 안에 공존하게 되어 혼동 위험.

### Backup/Versioning
Git 관리 가능(기존 Manifest와 동일 커밋 이력 공유) — 그러나 Crosswalk
갱신(예: `unmapped`→`manual-confirmed`)이 Manifest 파일 전체의 diff로
잡혀, "이 커밋이 Source 상태 변경인지 Crosswalk 매핑 확정인지"가
diff만 봐서는 구분되지 않음(NAE-ADAPTER-REFACTOR-001에서 그렇게
공들여 살려낸 comment-preserving diff의 가독성이 다시 희석될 위험).

---

## 2. Option B — Dedicated Crosswalk Store(권장 후보)

```
NAE/
 └── metadata/
      └── crosswalk/
           ├── crosswalk.yaml
           └── index.json
```

### 장점
- **Metadata Layer 독립** — Manifest/Registry 어느 파일도 열지 않고
  Crosswalk만 별도로 읽고 쓸 수 있다. `CrosswalkRepository`가 이미
  이 형태를 전제로 설계됨(`add`/`get`/`get_by_source`/`list_all`이
  Manifest 구조를 전혀 몰라도 동작).
- **Manifest 불변** — ADR-019가 정의한 Manifest Entry 필드 집합에
  손대지 않으므로, ADR-019 Amendment가 필요 없다(§ADR019 Impact
  Review 결론).
- **Retrieval 영향 없음** — `NAE/metadata/`는 `core/retrieval.py`가
  참조하는 어떤 경로도 아니다(grep 확인, §3 Architecture Boundary).
- Crosswalk 갱신이 Manifest/Registry와 완전히 분리된 git diff로
  나타나 변경 추적이 명확함(Option A의 diff 혼동 문제 없음).

### 위험
- **신규 Metadata namespace 필요** — `NAE/metadata/`라는 디렉토리가
  지금까지 존재하지 않았다(`find NAE -maxdepth 1 -type d` 확인 결과
  `NAE/`의 실제 하위 디렉토리는 `benchmark/`, `collectors/`,
  `corpus/`, `manifest/`, `pipeline/`). **주의**: `NAE/manifest/`가
  이미 존재하지만, 그 안에는 레거시 CSV(`NAE_SOURCE_MANIFEST_v1.csv`)
  하나뿐이고 현재 Manifest Layer(ADR-019, `resources/theological_
  sources/manifest/`)와는 무관한 과거 산출물이다 — 이름이 비슷해
  혼동하기 쉬우므로 Crosswalk을 여기 두지 않는다(신규 `NAE/metadata/
  crosswalk/`가 필요한 이유이기도 함, §Decision에서 명명 근거 재확인).
  새 namespace 도입 자체가 작은 구조 변경이므로, "ADR-019를 안
  건드린다"는 것이 "Architecture 문서화가 전혀 필요 없다"는 뜻은
  아니다 — 최소한 이 새 디렉토리의 존재와 소유권을 어딘가에는
  기록해야 한다(§Decision에서 처리 방식 제시).
- `crosswalk.yaml` 1개 파일에 전부 넣을지, Source별로 나눌지
  세부 설계가 남아있음(이번 문서는 최상위 위치만 결정, 파일 분할
  전략은 구현 단계로 이관).

### Audit Requirement 충족 여부
가능 — 8개 필드 전부 독립 스키마로 자유롭게 표현, Manifest의 Audit
필드와 이름 충돌 없음.

### Backup/Versioning
Git 관리 가능(신규 경로, 기존 파일과 독립적으로 diff 추적). Crosswalk
Record는 `frozen=True`(불변)로 설계되어 있으므로(schema.py), "수정"이
아니라 "새 레코드 추가"가 기본 갱신 방식이 되도록 유도하기 쉬움 —
append-only에 가까운 git 이력을 자연스럽게 얻을 수 있다(Migration
Engine Audit Log와 동일 정신).

---

## 3. Option C — Database Backend(SQLite/PostgreSQL)

### 장점
- Query 효율(대량 매핑 시 인덱스 기반 조회)
- 대규모 확장(수천~수만 건 Crosswalk Record) 시 파일 기반보다 유리

### 위험
- **현재 NAE Architecture 과잉** — Registry/Manifest 전부 YAML 파일
  기반이고(schema_version 필드까지 YAML 관례를 따름), DB 백엔드를
  도입하면 이 프로젝트에서 처음으로 "파일이 아닌 정본"이 생긴다 —
  기존 3-Validator(source/manifest/authority)가 전부 파일 시스템을
  직접 읽는 방식과 근본적으로 다른 운영 모델이 필요해짐(백업 절차,
  스키마 마이그레이션 도구, 동시성 제어 등 새 운영 부담).
- 현재 Crosswalk 대상 규모(Pilot 10건, 향후 Corpus-wide로 확장해도
  수백~수천 단위로 예상)에서 DB가 주는 이점(Query 효율)을 체감하기
  어려움 — Registry/Manifest도 지금 규모에서 파일 기반으로 충분히
  동작 중(source_validator 89 PASS 등, 밀리초 단위 실행).
- 운영 복잡성 증가(백업/버전 관리를 위한 별도 도구 필요 — Git이
  자연스럽게 제공하는 이력 추적을 잃음).

### Audit Requirement 충족 여부
가능(스키마 테이블 설계로 8개 필드 표현) — 그러나 "가능"과 "이
프로젝트 규모에 적절"은 별개 문제(§결론).

### Backup/Versioning
- Git 관리: **부분적으로만 가능**(SQLite 파일 자체는 git-track 가능하나
  binary diff라 사람이 읽을 수 있는 변경 이력을 못 얻음, PostgreSQL은
  git 관리 불가 — 별도 dump/backup 절차 필요)
- Immutable history: DB 트랜잭션 로그로 가능하나 별도 구현 필요
- Rollback: DB 자체 기능으로 가능하나, Migration Engine의 git-tag
  기반 Checkpoint(NAE-GIT-HISTORY-CLEANUP-001에서 검증된 패턴)와
  다른 별도의 Rollback 메커니즘을 새로 갖추어야 함

---

## 4. 비교 요약

| 기준 | Option A(Manifest Extension) | Option B(Dedicated Store) | Option C(DB Backend) |
|---|---|---|---|
| ADR-019 영향 | Amendment 필요 가능성 높음 | **불필요**(필드 집합 무변경) | 불필요(관련 없음) |
| Architecture Boundary(Retrieval/TSU Builder/Migration Engine/RAW 비접촉) | 충족(단, Manifest 책임 확대) | **충족(가장 깔끔)** | 충족 |
| Audit Requirement(8개 필드) | 충족(단 필드명 충돌 위험) | **충족(충돌 없음)** | 충족 |
| Git 관리 가능 여부 | 가능(단 diff 혼동) | **가능(diff 명확)** | 제한적(SQLite) / 불가(PostgreSQL) |
| Immutable history | Manifest git 이력에 편승 | **git 이력 + frozen record로 자연스럽게 확보** | 별도 구현 필요 |
| Rollback 가능 여부 | git revert(Manifest 전체 단위) | **git revert(Crosswalk 전용 단위, 더 세밀)** | DB 별도 메커니즘 필요 |
| 신규 구조 도입 부담 | 없음(기존 파일에 필드 추가) | 낮음(신규 디렉토리 1개) | 높음(신규 운영 체계) |
| 현재 규모 적합성 | 적합 | **적합** | 과잉 |

**결론은 §Decision 001 문서에서 확정한다.**
