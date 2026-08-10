# NAE Identifier Crosswalk Mapping Policy 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 3
**작성일:** 2026-08-05
**성격:** 정책 문서 — 실제 Mapping 레코드는 이번 문서에서 생성하지
않는다(Rule 3 참고 — 근거 없이 만들면 그 자체가 Rule 3 위반).

---

## Rule 1 — 기존 ID 변경 금지

Crosswalk Layer는 `source_id`/`canonical_id`/`legacy_id`(Registry,
ADR-017 Option B) 어느 것도 변경하지 않는다 — 이 필드들은 여전히
불변이며, Crosswalk은 그 위에 **추가되는 새로운 대응표**일 뿐이다.
Migration Engine이 canonical_id를 추가할 때 기존 FK 필드를 전혀
건드리지 않은 것(Resolution Plan-001 §0)과 동일한 원칙을 Corpus/TSU
방향으로 확장한 것이다.

**검증 방법(향후 구현 시)**: Crosswalk Adapter가 Registry/Manifest
파일을 쓰기 모드로 여는 코드 경로를 가지면 안 된다 — Crosswalk은
읽기 전용으로 두 계층을 조회하고, 그 대응 관계만 별도 저장소(§Schema
§3 후보)에 기록한다.

---

## Rule 2 — Crosswalk는 Translation Layer(단방향 변환, 소유권 없음)

Crosswalk Layer는 **어떤 identifier의 "정본"도 새로 만들지 않는다** —
Registry `source_id`가 여전히 정본이고, Corpus/TSU `identifier`도
그 자체로 자기 계층의 정본이다. Crosswalk은 두 정본 사이를 오갈 수
있게 해주는 **번역표(lookup table)**일 뿐, 제3의 권위를 갖지 않는다.

```
source_identifier(Registry/Manifest 정본)
        │
        │  Crosswalk Record(번역만, 소유권 없음)
        ▼
target_identifier(Corpus/TSU 정본)
```

(구체적인 예시 매핑은 이 정책 문서에 싣지 않는다 — Rule 3에 따라
아직 evidence-backed로 확정된 실제 매핑이 하나도 없으므로, 추측성
예시조차 여기 적으면 나중에 "문서에 있던 예시"가 사실로 오인될 위험이
있다.)

### 이 Rule이 막는 것

- Crosswalk 테이블을 Registry나 Manifest의 대체 정본으로 취급하는 것
- Crosswalk 값을 역으로 Registry `source_id`에 되먹임(back-write)하는 것
- Corpus/TSU `identifier`를 Crosswalk 존재 이유로 rename하는 것(각
  계층의 identifier는 자기 계층 안에서 계속 독립적으로 진화 가능)

---

## Rule 3 — 추측 Mapping 금지

### 허용되는 `mapping_status`

| 값 | 의미 | 요구 조건 |
|---|---|---|
| `verified` | 사람이 원문(archive.org 메타데이터, RAW 파일 실물, OCR 텍스트 등)을 직접 대조해 확인 | `evidence` 필드에 대조 방법과 근거 서술 필수 |
| `evidence-backed` | 자동/반자동 도구가 만든 후보이나, 명확한 근거(파일명 일치, 메타데이터 필드 일치 등)가 있어 신뢰도가 높음 | `evidence` 필드에 어떤 신호를 근거로 삼았는지 명시 필수 |
| `manual-confirmed` | `evidence-backed` 후보를 사람이 최종 검토해 확정 | `verified_at` 채워짐 필수 |
| `unmapped` | 아직 대응 관계를 모름(명시적 플레이스홀더) | `confidence`/`evidence` 비워둠 — "모른다"는 사실 자체를 기록 |

### 금지되는 근거

| 금지 유형 | 이유 |
|---|---|
| `guess`(추측) | 근거 없이 "아마 이거일 것"으로 채우면, 잘못된 Crosswalk이 TSU Pipeline 입력으로 흘러 들어가 완전히 다른 문헌의 TSU가 생성될 위험(데이터 무결성 최악의 실패 모드) |
| `similar-name`(이름 유사도만) | 신학 문헌은 저자/판본/권호가 비슷한 제목을 가진 경우가 매우 흔함(예: Fuller Complete Works 8권류) — 이름만으로 매칭하면 오매칭 확률이 구조적으로 높음 |
| `automatic-confidence-only`(자동 신뢰도 점수만, 사람 검토 없음) | `evidence-backed`까지는 허용하되, 그 상태에서 곧바로 TSU Pipeline에 투입하는 것은 금지 — 반드시 `manual-confirmed`(사람 확인)를 거쳐야 Gate를 통과할 수 있다(§Phase5 TSU Contract에서 이 요건을 다시 명시) |

### 이번 Task에서 실제로 몇 건이 매핑됐는가

**0건.** 이번 Task(Phase 1~6)는 정책과 스키마만 설계했고, 실제
Registry `source_id` 10건 중 어느 것도 Corpus/TSU identifier와
매핑하지 않았다 — Inventory §5에서 확인한 대로 지금은 겹치는 값이
없으므로, 자동으로라도 만들 수 있는 후보 자체가 없다(이름 유사도로
추측하는 것은 Rule 3 위반이므로 시도하지 않았다). 실제 매핑 작업은
사람이 원문을 대조하는 별도 작업(Crosswalk Adapter 구현 이후 단계)
으로 남긴다.
