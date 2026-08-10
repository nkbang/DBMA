# NAE Crosswalk Storage Decision 001

**Project:** NAE-CROSSWALK-STORAGE-LOCATION-DESIGN-001
**작성일:** 2026-08-05
**성격:** Architecture Decision — 코드 변경, 데이터 생성, Migration
실행 전부 미수행. 이 문서가 확정하는 것은 "어디에 저장할 것인가"
뿐이다.

---

## 결정

```
CHOSEN: Option B — Dedicated Crosswalk Store
LOCATION: NAE/metadata/crosswalk/
```

`docs/NAE_CROSSWALK_STORAGE_OPTION_ANALYSIS_001.md` §4 비교표 기준,
Option B가 8개 평가 기준 중 7개에서 최선이거나 A/C와 동률 이상이며,
유일한 약점("신규 namespace 필요")은 위험이 아니라 단순 작업량이다
— ADR-019 Amendment처럼 기존 Approved Architecture를 다시 여는 것과는
무게가 다르다.

---

## 근거

### 1. ADR Impact

`docs/NAE_ADR019_IMPACT_REVIEW_001.md` 결론: **본문 수정 불필요,
Amendment 불필요.** ADR-019가 정의한 Manifest Entry 필드 집합(9개)에
Crosswalk의 8개 필드가 전혀 포함되지 않으므로, Option B는 Approved
ADR을 조금도 열지 않고 구현 가능하다 — Architecture Freeze Rule을
가장 적게 건드리는 선택.

### 2. Architecture Boundary

```
$ grep -n "^from|^import" core/retrieval.py | grep -i "nae|metadata"
(결과 없음)
```

`core/retrieval.py`는 `NAE/` 하위 어떤 경로도 import하지 않는다 —
`NAE/metadata/crosswalk/`를 새로 만들어도 Retrieval이 그 존재를
알 방법이 없다(코드 레벨로 재확인). TSU Builder(`NAE/pipeline/tsu/`)/
Migration Engine(`scripts/migration_engine.py`)/RAW(`NAE/corpus/
raw/`) 중 어느 것도 이번 Task에서 수정하지 않았고, Option B 채택이
그 무엇도 건드리도록 요구하지 않는다(전부 이번 Task의 절대 변경
금지 목록과 일치, git status로 재확인 — §Regression).

### 3. Audit Requirement

8개 필드(`crosswalk_id`/`source_identifier`/`source_type`/
`target_identifier`/`target_type`/`mapping_status`/`confidence`/
`evidence`/`created_at`/`verified_at`) 전부 독립 저장소이므로 필드명
충돌 없이 그대로 보존 가능 — Manifest의 기존 Audit 필드(`created_at`/
`updated_at`/`verified_by`)와 이름이 겹치는 위험(Option A의 단점)이
원천적으로 없다.

### 4. Backup / Versioning

- **Git 관리 가능**: `NAE/metadata/crosswalk/`는 일반 텍스트(YAML/
  JSON) 경로이므로 기존 Registry/Manifest와 동일한 방식으로 git
  추적·diff·revert 가능.
- **Immutable history 가능**: `CrosswalkRecord`가 이미
  `frozen=True`(NAE-CROSSWALK-TEST-EVIDENCE-FIX-001)이므로, 값을
  바꾸려면 코드 레벨에서부터 "새 레코드 추가"만 가능하다 — 이 특성이
  저장 파일에도 자연스럽게 반영되어, 매핑 갱신이 기존 레코드 삭제/
  수정이 아니라 append로 나타나는 git 이력을 얻기 쉽다(Migration
  Engine Audit Log와 동일 정신, NAE-GIT-HISTORY-CLEANUP-001 이후
  이 프로젝트가 일관되게 지켜온 "이력은 지우지 않는다" 원칙과 부합).
- **Rollback 가능**: 일반 git revert/checkout으로 가능 — Migration
  Engine이 이미 검증한 Checkpoint 패턴(브랜치/태그 기반)을 그대로
  재사용할 수 있다.

---

## 저장 구조 초안(제안, 이번 Task에서 생성하지 않음)

```
NAE/metadata/crosswalk/
├── crosswalk.yaml     # CrosswalkRecord 목록(schema.py CrosswalkRecord.to_dict() 직렬화)
└── index.json         # source_identifier -> crosswalk_id 역인덱스(조회 최적화, 선택)
```

**주의**: `NAE/manifest/`(레거시 CSV 산출물, ADR-019 Manifest Layer와
무관)와 이름이 유사해 혼동 가능 — `NAE/metadata/crosswalk/`라는
새 이름을 명확히 써서 그 레거시 디렉토리와 섞이지 않게 한다
(Option Analysis 001 §2 발견 사항 재확인).

파일 분할 전략(Source당 1개 파일 vs 전체 1개 파일), `index.json`의
실제 필요 여부, `CrosswalkRepository`의 구체 구현체(예:
`YamlFileCrosswalkRepository`) 이름과 세부 API는 **이번 결정 문서의
범위 밖** — 다음 단계(Crosswalk Production 적용 준비)에서 별도
설계·구현 승인을 받는다.

---

## 이번 결정이 하지 않는 것(명시적 범위 제한)

- `NAE/metadata/crosswalk/` 디렉토리를 실제로 생성하지 않는다
- `crosswalk.yaml`/`index.json` 파일을 만들지 않는다
- `CrosswalkRepository`의 구체 구현체(YAML 기반)를 코드로 작성하지
  않는다
- 실제 Crosswalk 매핑을 0건에서 1건이라도 늘리지 않는다

이 문서는 **"어디에 저장할지"만 확정**한다 — "실제로 저장소를 만들고
채우는 것"은 승인 이후 별도 작업이다.
