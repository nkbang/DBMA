# NAE Metadata Migration Engine Design 001

**Project:** CUE-TASK-ORDER-041 / NAE-METADATA-MIGRATION-ENGINE-DESIGN-001
**작성일:** 2026-08-03
**성격:** **Design Only** — `resources/`, `scripts/`, `tests/`, Registry
YAML, Manifest YAML, Corpus Manifest, RAW, TSU, Embedding, Retrieval,
Validator 전부 수정하지 않음. 구현/데이터 변경/Migration 실행 없음.
**Architecture Freeze Rule 준수:** ADR-016~019(Approved)는 이 설계
전체의 제약 조건으로만 사용하며, 어떤 항목도 개정하지 않는다. 충돌
발견 시 즉시 중단하고 사용자 확인(§10 참고 — 이번 조사에서는 충돌
발견되지 않음, §최종 답변 Q1).

---

## 0. 조사 요약 (Approved Architecture 재확인)

| 근거 문서 | 이번 설계에 반영한 제약 |
|---|---|
| ADR-016(Approved) | Author→Work→Edition→Volume→Source 5-tier 모델, Work:Edition=1:N, `edition_id` TSU 필수, `volume_id` 조건부 필수 — Migration Unit 계층 설계의 기준(§1) |
| ADR-017(Approved) | canonical_id(필수)/legacy_id(선택 배열), Option B(기존 FK 불변, 원자적 rename 시 legacy_id 보존) — 향후 실제 ID rename Migration의 원자성 요구사항(§4 Rollback, §5 Idempotency) |
| ADR-018(Approved) | Periodical(volume+issue) 확장 — Migration Unit이 periodical 계열도 커버해야 함(§1) |
| ADR-019(Approved) | Manifest Layer 5개 lifecycle 필드(`acquisition_status`/`ocr_status`/`metadata_status`/`tsu_status`/`embedding_status`)와 TSU_ELIGIBLE 판정 — Migration 이후 TSU Gate 재계산 시점의 근거(§14) |
| `NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md` | BLOCKER 2(Idempotency/Rollback 미설계)·BLOCKER 3(sha256 체크섬 필드 부재)가 바로 이 설계 문서가 메워야 할 항목 |
| `NAE_MANIFEST_VALIDATOR_DESIGN_001.md` | Manifest는 저작권 정보를 저장하지 않음(corpus manifest가 Single Source of Truth) — Migration Engine의 Checksum 대상 정의(§7)에서 동일 원칙 적용 |
| ID Governance(`NAE_ID_GOVERNANCE_v1.md` §6.1) | "원자적 rename": ID 필드 + 그 ID를 참조하는 모든 FK 필드를 같은 커밋/같은 트랜잭션에서 함께 변경 — Migration Unit/State Machine 설계의 핵심 제약(§1, §2) |
| Schema v2.2 | Registry `schema_version: "1.0"`, Manifest schema v2.2.x — Migration Version과 별개 축(§11) |

---

## 1. Migration Unit 정의

**Migration Unit = 하나의 원자적 rename 트랜잭션이 커버하는 entity
집합.** ID Governance v1 §6.1의 "원자적 rename" 요구사항(ID 필드 자체
+ 그 ID를 참조하는 모든 FK 필드를 함께 변경) 때문에, Migration Unit은
**단일 entity가 아니라 "entity + 그 entity를 참조하는 모든 자식
entity + 그 entity를 참조하는 모든 Manifest entry"의 폐쇄 집합**으로
정의한다.

```
Migration Unit = {
  target_entity: (entity_type, entity_id),
  fk_dependents: [
    # ADR-016 FK 방향(자식 → 부모)의 역방향 탐색으로 산출
    (entity_type, entity_id), ...
  ],
  manifest_dependents: [
    # target_entity 또는 fk_dependents 중 하나라도 참조하는
    # authority/manifest/*.yaml entry 전부
    (manifest_id), ...
  ],
}
```

예: Author `FULLER-ANDREW-001`을 canonical_id `fuller_andrew`로 실제
rename하는 Migration Unit은 다음을 전부 포함해야 한다(Resolution
Plan-001 §2.1 blast radius 실측 그대로):

```
Author(1) -> Work(1, FULLER-COMPLETE-WORKS-001)
          -> Edition(2) -> Volume(8) -> Source(10)
          -> Manifest entry(해당 source들의 manifest.yaml)
```

**Migration Unit은 절대 부분 집합으로 쪼개 실행하지 않는다** — Author만
바꾸고 Work는 나중에 바꾸는 식의 분할 실행은 FK Broken Reference를
발생시키므로 설계 자체에서 금지한다(§8 Failure Recovery의 "부분 실패"
정의와 직결).

### Migration Unit 종류

| 종류 | 대상 | 비고 |
|---|---|---|
| ID Rename Unit | 하나의 canonical_id 미적용 entity + 그 하위 폐쇄 집합 | ID Governance WARNING 26건 처리(향후, 이번 설계 범위는 엔진 자체) |
| Corpus Ingestion Unit | 신규 Source 1건 + 그 Registry 상위 체인(신규 Author/Work/Edition 포함 가능) + Manifest 1건 | Corpus-wide Migration의 기본 반복 단위 |
| Schema Field Backfill Unit | 특정 필드(예: `canonical_id`)를 아직 갖지 않은 entity 전체 | 이번 ID Governance 구현(커밋 `1042b1f`)이 실제로 수행한 작업의 일반화 형태 |

---

## 2. Migration State Machine

```
PENDING
   │
   ▼
VALIDATING  ──(검증 실패)──▶ FAILED
   │
   ▼ (검증 통과)
MIGRATING  ──(중단/오류)──▶ FAILED
   │
   ▼ (쓰기 완료)
VERIFYING  ──(사후 검증 실패)──▶ FAILED
   │
   ▼ (사후 검증 통과)
COMPLETE

FAILED ──(Rollback 실행)──▶ ROLLED_BACK
FAILED ──(Rollback 불가, §4 사유)──▶ FAILED(최종, 사람 개입 필요)
```

### 상태 정의

| 상태 | 의미 | 진입 조건 |
|---|---|---|
| PENDING | Migration Unit이 큐에 등록됨, 아직 처리 시작 안 함 | Migration Plan 생성 시 |
| VALIDATING | 사전 검증 중(§4 Checkpoint "before" 단계와 동일 시점) | PENDING → 처리 시작 |
| MIGRATING | 실제 쓰기(YAML 갱신) 진행 중 | VALIDATING 전부 PASS |
| VERIFYING | 쓰기 후 3-Validator 재실행 중 | MIGRATING의 쓰기 완료(파일 flush) |
| COMPLETE | 사후 검증 전부 PASS, Checkpoint 기록됨 | VERIFYING 전부 PASS |
| FAILED | 어느 단계에서든 실패 | 각 단계의 실패 조건 |
| ROLLED_BACK | FAILED 상태에서 Rollback 실행 완료 | FAILED + Rollback 대상(§4) |

### 역행 규칙(State Machine이 절대 허용하지 않는 전이)

- **COMPLETE → 임의 상태로의 자동 역행 금지** — COMPLETE는 종단 상태.
  COMPLETE 이후 문제가 발견되면 새로운 Migration Unit(역방향 rename)을
  별도로 발행해야 하며, 기존 COMPLETE 레코드를 지우거나 덮어쓰지 않는다
  (Audit Log 불변성, §6).
- **MIGRATING 중 상태에서 직접 ROLLED_BACK으로 전이 금지** — 반드시
  FAILED를 거친다(Rollback 실행 자체가 실패할 수 있으므로, "시도함"과
  "완료함"을 구분해야 함).
- **FAILED → COMPLETE 금지** — 실패한 Migration Unit은 재시도 시 새
  PENDING을 처음부터 다시 생성한다(같은 FAILED 레코드를 재사용해
  COMPLETE로 승격하지 않음 — Audit 추적성).

---

## 3. Checkpoint

### 어디서 생성하는가

Checkpoint는 State Machine의 **VALIDATING 진입 직전**과 **COMPLETE
진입 직후**, 두 지점에서 생성한다.

```
PENDING → [Checkpoint A: pre-migration snapshot] → VALIDATING
                                                        │
                                                        ▼
                                            MIGRATING → VERIFYING
                                                        │
                                                        ▼
                                    [Checkpoint B: post-migration commit] → COMPLETE
```

- **Checkpoint A(pre-migration)**: Migration Unit이 건드릴 모든 YAML
  파일의 git 커밋 해시 + 각 파일의 sha256(§7)을 기록. Rollback의
  복원 대상이 되는 지점(§4).
- **Checkpoint B(post-migration)**: 쓰기 완료 후 git commit 1개(§Git
  정책과 별개 — 이는 미래 Migration Engine 구현 단계의 실제 실행
  시점 정책이며, 이번 설계 문서 자체의 커밋 여부와는 무관)로 확정,
  그 커밋 해시를 Audit Log에 기록.

### Checkpoint 단위

**Migration Unit 1개 = Checkpoint 1개.** Migration Unit 내부를 더
잘게 쪼개 중간 Checkpoint를 만들지 않는다 — Migration Unit 자체가
이미 "원자적으로 함께 바뀌어야 하는 최소 폐쇄 집합"(§1)이므로, 그보다
작은 단위의 Checkpoint는 오히려 부분 완료 상태를 영속화시켜 FK
무결성을 깨뜨릴 위험이 있다.

---

## 4. Rollback

### Rollback 범위

Rollback은 **Migration Unit 전체 단위**로만 수행한다(§1의 폐쇄 집합
원칙과 동일 이유). Checkpoint A(pre-migration) 시점의 git 커밋으로
관련 YAML 파일 전체를 되돌리고, 3-Validator를 재실행해 FK Integrity가
Checkpoint A 이전 상태와 동일함을 확인한 뒤에만 ROLLED_BACK으로
전이한다.

```
Rollback 절차:
1. Migration Unit이 건드린 파일 목록 조회(Checkpoint A에 기록됨)
2. 해당 파일들을 Checkpoint A 커밋 시점으로 git checkout
3. sha256 재계산 → Checkpoint A 기록값과 일치 확인
4. 3-Validator 재실행 → FAIL 0건 확인
5. Audit Log에 ROLLED_BACK 기록(원본 실패 사유 + Rollback 근거 포함)
```

### Rollback 불가능한 경우

1. **COMPLETE 이후** — §2 역행 규칙에 의해 COMPLETE는 Rollback 대상이
   아니다(새 역방향 Migration Unit 필요).
2. **Migration Unit 완료 후 그 위에 다른 Migration Unit이 이미
   실행된 경우** — 예: Author rename이 COMPLETE된 뒤 같은 Author의
   Work가 별도 Migration Unit으로 이미 변경됐다면, 첫 Migration Unit만
   단독으로 되돌리면 두 번째 Migration Unit이 참조하는 FK가 깨진다.
   이 경우 **의존 순서의 역순으로 연쇄 Rollback**해야 하며, 연쇄
   Rollback이 불가능하다고 판단되면(예: 사람이 그 사이 수작업으로
   추가 변경) **자동 Rollback을 거부하고 사람 개입을 요구**한다.
3. **외부 시스템이 이미 새 ID를 소비한 경우** — 이번 설계 범위(TSU/
   Embedding/Retrieval 미수행, §설계 목표)에서는 해당 없음(Migration
   Engine은 Metadata Layer만 다루므로), 그러나 향후 TSU가 이미 생성된
   뒤라면 Rollback 불가 — 이것이 Readiness Review Q5("TSU_ELIGIBLE
   계산은 Migration 이후"), §14 TSU Gate의 근거.

---

## 5. Idempotency

### 동일 Migration 재실행

Migration Unit은 **입력(target_entity + 목표 canonical_id/필드 값)이
동일하면 몇 번을 재실행해도 최종 상태가 동일**해야 한다. 이를 보장하는
메커니즘:

1. **Migration Unit ID는 결정적으로 생성**한다 —
   `hash(target_entity_type, target_entity_id, migration_version)`
   형태로, 같은 대상·같은 Migration Version에 대해 항상 같은 ID가
   나온다(우연/타임스탬프 기반 ID 금지).
2. **실행 전 현재 상태 확인** — VALIDATING 단계에서 "이미 목표 상태와
   동일한가?"를 먼저 검사한다. 이미 `canonical_id`가 목표 값과
   일치하면 그 Migration Unit은 즉시 COMPLETE(no-op)로 처리하고 쓰기를
   수행하지 않는다.
3. **Migration Lock**(§10)과 결합 — 동시 재실행 시 중복 쓰기를
   원천적으로 차단.

### 중복 생성 방지

- Audit Log(§6)에 Migration Unit ID를 유일 키로 기록 — 같은 Migration
  Unit ID가 이미 COMPLETE 상태로 있으면 재실행 요청은 즉시 no-op
  COMPLETE 반환(§2 "FAILED → COMPLETE 금지"와 별개로, 이건 "이미
  COMPLETE인 것의 재실행"이므로 새 레코드를 만들지 않고 기존 COMPLETE
  레코드를 그대로 반환).
- `legacy_id` 배열에 append할 때도 이미 존재하는 값이면 추가하지
  않음(집합 semantics, ADR-017 Option B와 일치).

---

## 6. Audit Log

### 필수 기록 필드

```yaml
timestamp: "2026-08-03T16:00:00+09:00"   # Checkpoint 생성 시각(ISO 8601)
operator: "cue"                           # 실행 주체(CUE/C1/사람 구분)
dataset: "authority"                      # 대상 Registry/Manifest 구분
source_id: "BAP-MISS-FULLER-VOL01"        # 영향받는 최하위 entity(해당 시)
manifest_id: "..."                        # 영향받는 Manifest entry(해당 시)
migration_version: "1.0.0"                # §11 Version Policy
migration_unit_id: "<결정적 해시>"          # §5
state: "COMPLETE"                         # State Machine 현재 상태
old_checksum: "sha256:..."                # Checkpoint A 시점 파일 체크섬
new_checksum: "sha256:..."                # Checkpoint B 시점 파일 체크섬
result: "PASS"                            # PASS/FAIL/ROLLED_BACK
reason: null                              # FAIL/ROLLED_BACK 시 사유(필수)
```

Audit Log는 **append-only**(기존 레코드 수정/삭제 금지 — COMPLETE
불변성과 동일 원칙, §2). 저장 위치는 Registry/Manifest와 분리된 별도
디렉토리(예: `resources/theological_sources/_migration_audit/`,
실제 경로는 구현 단계에서 확정 — 이번 설계는 개념만 정의).

---

## 7. Checksum

### 무엇을 계산하는가

| 대상 | 체크섬 계산 범위 | 근거 |
|---|---|---|
| Manifest | 각 `manifest.yaml` 파일 전체(YAML 직렬화 전 원본 바이트) | Migration Unit이 건드리는 최소 파일 단위 |
| Metadata(Registry) | 각 `authority/*.yaml` 파일 전체 | 동일 |
| Corpus Manifest(`source_manifest.yaml`) | 파일 전체(Migration Unit이 이 파일을 직접 쓰지는 않지만, TSU_ELIGIBLE 판정의 `copyright_status` 조회 대상이므로 읽기 시점 체크섬을 Audit에 남겨 "이 Migration이 어떤 corpus manifest 상태를 전제로 실행됐는지" 추적) | Manifest Validator Design-001 §4 Single Source of Truth 원칙과 일관 |

**SHA256** 단일 알고리즘 사용(RAW 백업 검증 시 이미 `shasum -a 256`으로
실사용 중인 것과 통일, NAE-GIT-HISTORY-CLEANUP-001에서 검증한 방식
재사용).

파일 단위 체크섬만 계산하고 entity(레코드) 단위 체크섬은 계산하지
않는다 — Migration Unit이 이미 파일 단위보다 세밀한 원자성 경계(§1)를
갖고 있으므로, 체크섬은 "그 파일이 Migration Unit이 의도한 대로
정확히 바뀌었는가"를 확인하는 무결성 게이트로만 쓰인다.

---

## 8. Failure Recovery

| 상황 | 처리 |
|---|---|
| 중단(프로세스 kill, 정전 등) | 재시작 시 Migration Lock(§10) 확인 → 이전 실행이 남긴 Lock이 있으면 그 Migration Unit을 FAILED로 표시(Lock timeout 기준) 후 사람 확인 요청. 자동 재개 금지(Idempotency로 안전하게 재실행 가능하지만, "왜 중단됐는지" 원인 파악 없이 자동 재시도하면 같은 이유로 또 중단될 수 있음) |
| 재시작 | 위 절차로 FAILED 처리된 Migration Unit은 새 PENDING으로 재발행(§2 "FAILED → COMPLETE 금지") — 이번엔 Idempotency(§5)에 의해 이미 완료된 부분은 no-op 처리됨 |
| 부분 실패(Migration Unit 내부 일부 파일만 쓰기 성공) | **설계상 발생해서는 안 되는 상태** — §1에서 Migration Unit을 폐쇄 집합으로 정의한 이유가 바로 이것을 막기 위함. 그럼에도 발생하면 즉시 FAILED, 자동 Rollback 시도(§4), 실패 시 사람 개입(§4 불가능 사유 3) |
| 전체 실패(Migration Plan 전체 중단) | 이미 COMPLETE인 Migration Unit들은 그대로 유지(각 Unit이 독립 원자 단위이므로 서로 영향 없음). 미완료 PENDING/FAILED Unit들만 재시도 대상 |

---

## 9. Dry Run

### Dry Run 출력

- 각 Migration Unit이 **VALIDATING까지만 실행**되고 MIGRATING(실제
  쓰기)은 건너뛴다.
- 출력: Migration Unit 목록(target_entity + fk_dependents +
  manifest_dependents), 예상 변경 필드 diff(old value → new value),
  VALIDATING 단계에서 발견된 문제(FK 불일치, canonical_id 형식 위반
  등 — authority_validator.py 스타일의 PASS/WARNING/FAIL 형식 재사용).
- Dry Run 자체도 Audit Log에 기록하되 `result: "DRY_RUN"`으로
  구분(실제 COMPLETE와 혼동 방지).

### Dry Run 한계

- 실제 쓰기를 하지 않으므로 **동시성 문제(Migration Lock 경합, §10)는
  재현하지 못한다** — Dry Run이 PASS해도 실제 실행 시점에 다른
  프로세스와 경합해 FAILED가 날 수 있음.
- 파일 시스템 권한 오류, 디스크 공간 부족 등 "쓰기 시도 자체에서만
  드러나는 오류"는 Dry Run으로 사전에 잡을 수 없다.
- Dry Run 시점과 실제 실행 시점 사이에 Registry/Manifest가 바뀌면
  (예: 다른 작업자가 그 사이 수정) Dry Run 결과가 무효화될 수 있음 —
  실제 실행 직전에 VALIDATING을 다시 수행하는 것은 생략 불가(Dry Run이
  VALIDATING을 대체하지 않음).

---

## 10. Migration Lock

### 동시 실행 방지

- 하나의 Migration Unit이 건드리는 파일 집합(§1의 fk_dependents +
  manifest_dependents가 걸치는 모든 YAML 파일)에 대해 **파일 단위
  Lock**을 건다 — 두 Migration Unit이 같은 파일을 동시에 쓰려고 하면
  나중 요청은 대기하거나 즉시 실패(정책은 구현 단계에서 선택, 이번
  설계는 "Lock이 존재해야 한다"는 요구사항만 확정).
- Lock은 Migration Unit이 VALIDATING에 진입하는 시점에 획득하고,
  COMPLETE 또는 FAILED(Rollback 완료 포함)에 도달하면 해제한다.
- Lock에는 **timeout**을 둔다(§8 "중단" 상황에서 좀비 Lock이 영구히
  남는 것을 방지) — 구체 시간값은 구현 단계에서 결정.
- 이번 설계는 단일 Migration Engine 프로세스를 전제(분산 실행/여러
  프로세스 동시 구동은 범위 밖) — 향후 필요 시 별도 설계 확장.

---

## 11. Version Policy

| 버전 축 | 정의 | 현재 값 |
|---|---|---|
| Migration Version | Migration Engine 자체의 로직 버전(어떤 규칙으로 Migration Unit을 만들고 실행했는지) | 이번 설계 문서 기준 `1.0.0`(아직 구현 없음, 설계 버전) |
| Schema Version | Registry YAML의 `schema_version`(현재 `"1.0"`) / Manifest의 schema v2.2.x | 독립적으로 진화 — Migration Engine은 특정 Schema Version을 대상으로 동작하도록 명시해야 함 |
| Manifest Version | 개별 `manifest.yaml`의 스키마 버전(v2.2.x) | 동일 |

### 관계

Migration Version은 Schema Version/Manifest Version과 **N:1 관계**다
— 하나의 Migration Version은 특정 범위의 Schema/Manifest Version을
대상으로 명시하고, 그 범위 밖의 데이터에는 실행을 거부한다(예:
Migration Engine v1.0.0은 Registry schema_version="1.0" AND Manifest
schema v2.2.x만 대상 — 이번 ID Governance 구현이 정확히 이 조합이었음).
Schema/Manifest Version이 올라가면(예: v2.3.0) 대응하는 새 Migration
Version을 발행해야 하며, 기존 Migration Version을 소급 확장하지
않는다(ADR "소급 수정 금지" 관례, GOVERNANCE §7.5와 동일 원칙 적용).

---

## 12. Performance

| 항목 | 정책 |
|---|---|
| Batch Size | Migration Unit 단위가 이미 자연스러운 배치 경계(§1) — Migration Plan은 여러 Migration Unit을 배치로 묶어 순차/병렬 실행할 수 있으나, **서로 fk_dependents/manifest_dependents가 겹치는 Migration Unit은 같은 배치에서 병렬 실행 금지**(Migration Lock 경합, §10) |
| Memory | 현재 Registry(28 entity)·Manifest Pilot(10 source) 규모에서는 전체를 메모리에 올려도 무리 없음(source_validator.py/manifest_validator.py가 이미 이 방식으로 동작). Corpus-wide 확장(수백~수천 entity) 시에도 entity 단위 스트리밍 없이 충분할 것으로 예상 — 실측 재확인은 Corpus-wide Migration 착수 직전에 필요 |
| Resume | §8 Failure Recovery와 동일 메커니즘(FAILED Unit 재발행) — 별도 Resume 전용 로직 불필요, Idempotency(§5)가 Resume을 대체 |

---

## 13. Production Safety

### 작업 전 검사(pre-flight)

1. 대상 Migration Plan에 포함된 모든 Migration Unit에 대해 Dry
   Run(§9) PASS 확인
2. 3-Validator(source/manifest/authority) 전체 실행 → FAIL 0건 확인
   (Migration 시작 전 기준선 확보)
3. `backup/pre-git-cleanup` 스타일의 사전 브랜치/태그 생성(git
   checkpoint) — NAE-GIT-HISTORY-CLEANUP-001에서 검증된 패턴 재사용
4. Migration Lock(§10) 전역 상태 확인 — 이미 실행 중인 Migration이
   없는지

### 작업 후 검사(post-flight)

1. 3-Validator 전체 재실행 → FAIL 0건 확인(Migration 전후 비교,
   WARNING 수는 "Migration이 해결하려던 항목만큼 감소"했는지 확인)
2. 모든 COMPLETE Migration Unit의 Checkpoint B 체크섬 재검증
3. Audit Log 완결성 확인(모든 Migration Unit이 COMPLETE/FAILED/
   ROLLED_BACK 중 하나로 종결됐는지, PENDING/VALIDATING/MIGRATING에
   멈춰있는 Unit이 없는지)

---

## 14. TSU Gate

### Migration 이후

Migration Engine은 **TSU를 생성하지 않는다**(설계 목표). Migration
Unit이 COMPLETE된 이후, 그 영향을 받은 Manifest entry에 대해
`manifest_validator.py`의 TSU_ELIGIBLE 판정(§0 표, ADR-019 기준)을
**다시 계산**해야 한다 — Migration이 Registry의 canonical_id/legacy_id
또는 FK 값을 바꿨다면 Authority Reference FK 검사 결과가 달라질 수
있기 때문(TSU_ELIGIBLE 판정 조건 중 "authority_verified" 항목).

### TSU_ELIGIBLE 계산 시점

```
Migration Unit COMPLETE
        ↓
영향받은 Manifest entry 목록 산출(§1 manifest_dependents)
        ↓
manifest_validator.py 재실행(해당 entry만, 또는 전체)
        ↓
TSU_ELIGIBLE 재계산 결과를 Audit Log에 별도 기록(선택)
        ↓
TSU_ELIGIBLE=READY인 entry만 이후 TSU Pipeline(core/tsu_builder.py,
현재 게이트 미구현 — Readiness Review WARNING 1) 대상
```

**중요**: TSU 생성 자체는 이 Migration Engine의 책임이 아니다 —
TSU_ELIGIBLE 재계산까지만 Migration Engine의 post-flight 절차(§13)에
포함하고, 실제 TSU 생성은 별도 TSU Pipeline(현재 게이트 미구현 상태)의
책임으로 명확히 분리한다(§설계 목표).

---

## 최종 답변

### Q1. Migration Engine이 ADR-016~019와 충돌하는가?

**아니오.** 이번 설계 전 항목(§1~14)은 ADR-016(5-tier 모델, Work:
Edition 1:N)/ADR-017(Option B, 원자적 rename, canonical_id/legacy_id)/
ADR-018(Periodical 확장)/ADR-019(Manifest lifecycle, TSU_ELIGIBLE)의
기존 규칙을 그대로 전제로 설계됐다 — 어떤 필드 의미도, FK 방향도,
enum 값도 바꾸지 않는다. 충돌 후보로 검토했던 지점(ID rename의 원자성
범위, TSU_ELIGIBLE 재계산 시점)도 기존 ADR 문서에 이미 명시된 규칙을
그대로 인용해 설계했다.

### Q2. Migration Engine 구현 전에 추가 ADR이 필요한가?

**조건부로 필요할 수 있음 — 단, 이번 설계 자체는 신규 ADR 없이
가능.** 이 설계 문서(§1~14)는 기존 ADR-016~019의 실행 메커니즘일
뿐 새로운 아키텍처 결정을 내리지 않는다. 다만 구현 단계에서 아래
2가지가 실제로 필요해지면 그 시점에 신규 ADR(또는 기존 ADR의
Amendment) 검토가 필요하다:

1. Migration Audit Log 저장 위치(`_migration_audit/` 등)가 Registry/
   Manifest와 다른 디렉토리 구조를 도입한다면 — ADR-019(Manifest
   Layer 디렉토리 구조)의 범위 확장 여부 판단 필요
2. 분산/다중 프로세스 Migration 실행(§10에서 범위 밖으로 명시한
   부분)을 실제로 필요로 하게 되면 별도 설계·ADR 필요

**Evidence Before Promotion Rule 준수**: 이 설계 문서 자체는 새 ADR을
제안하지 않으며, 위 2가지는 "필요해질 수 있는 후보"로만 기록한다
(신규 ADR 승격 금지 — 이번 작업 범위).

### Q3. Rollback으로 복구 불가능한 경우가 존재하는가?

**예, 존재한다(§4에 3가지 명시)**:
1. COMPLETE 이후(새 역방향 Migration Unit 필요)
2. 연쇄 의존 Migration Unit이 이미 실행된 뒤 첫 Unit만 단독 Rollback
   시도하는 경우(연쇄 Rollback 실패 시 사람 개입 필요)
3. TSU가 이미 생성된 뒤(이번 Migration Engine 범위 밖이지만, Migration
   이 완료된 후 TSU Pipeline이 그 위에서 실행됐다면 Metadata만
   되돌려도 TSU와의 정합성이 깨짐 — §14가 TSU 생성을 이 엔진 밖에
   두면서도 "TSU_ELIGIBLE 재계산까지만" 책임지는 이유)

### Q4. Checkpoint 단위는 무엇이 가장 적절한가?

**Migration Unit(§1) 단위 — Corpus/Author/Work/Edition/Volume/Source/
Manifest 중 어느 단일 계층도 아니다.**

선택 이유:
- **Corpus 단위**는 너무 크다 — 하나라도 실패하면 전체가 FAILED되어
  Idempotency(§5)의 이점을 살릴 수 없고, Rollback 범위(§4)가
  과도하게 넓어진다.
- **Author/Work/Edition/Volume/Source 개별 계층 단위**는 너무 작다 —
  ID Governance v1 §6.1의 "원자적 rename"(ID 필드 + 그 ID를 참조하는
  모든 FK 필드를 함께 변경) 요구사항을 위반한다. 예를 들어 Author만
  Checkpoint를 찍고 Work는 별도 Checkpoint로 처리하면, 그 사이 시점에
  Author는 새 canonical_id인데 Work의 `author_id` FK는 아직 옛
  값인 상태가 영속화될 위험이 있다(실제로는 §1에서 이런 분할 실행
  자체를 금지했으므로, Checkpoint 단위가 이보다 작으면 그 금지를
  강제할 수 없다).
- **Manifest 단위**도 마찬가지로 너무 작다 — Manifest는 Registry FK를
  참조만 할 뿐 소유하지 않으므로, Registry 변경과 Manifest 변경을
  분리된 Checkpoint로 찍으면 그 사이 순간 FK가 깨진 상태가 존재할 수
  있다.

**Migration Unit은 ID Governance v1의 원자성 요구사항과 정확히
일치하는 최소 단위**이므로(§1의 예시: Author 1 + Work 1 + Edition 2 +
Volume 8 + Source 10을 하나의 폐쇄 집합으로), 이 단위를 Checkpoint
경계로 삼는 것이 FK 무결성을 보장하는 가장 작은(=가장 세밀한 재시도가
가능한) 단위다.

### Q5. Migration을 100회 반복해도 결과가 동일한가? (Idempotency)

**설계상 예 — 단, 3가지 전제 하에.**

1. Migration Unit ID가 결정적으로 생성되고(§5-1), VALIDATING 단계에서
   "이미 목표 상태인가"를 확인하는 no-op 경로가 실제로 구현되어야
   한다(설계는 이 요구사항을 명시했으나, 구현 정확성은 §Q2와 별개로
   구현 단계의 검증 대상).
2. Migration Lock(§10)이 실제로 동시 실행을 차단해야 한다 — Lock이
   없거나 오작동하면 두 프로세스가 동시에 같은 파일을 써서
   Idempotency가 깨질 수 있다.
3. legacy_id 배열에 append하는 로직이 집합 semantics를 지켜야
   한다(§5, 중복 값 방지) — 그렇지 않으면 재실행마다 legacy_id
   배열 길이가 늘어나는 non-idempotent 부작용이 생긴다.

이 3가지는 전부 이번 설계에 이미 요구사항으로 포함되어 있다(§5, §10)
— 구현 시 이 요구사항을 정확히 지키면 100회 반복 실행에도 최종 상태는
동일하다.

### Q6. Pilot Migration 전에 반드시 구현되어야 하는 기능은?(우선순위 순)

```
1순위: Migration Unit 계산 로직(§1) — target_entity로부터
       fk_dependents/manifest_dependents 폐쇄 집합을 정확히 산출하는
       기능. 이게 틀리면 이후 모든 것이 무의미(FK 손상 직결).

2순위: Checkpoint A/B(§3) + Rollback(§4) — Pilot 단계부터 실패
       가능성을 전제해야 하므로, 되돌릴 수 없는 상태로 Pilot을
       시작해서는 안 된다.

3순위: Idempotency 보장 로직(§5, no-op 경로) — Pilot 재실행이 반드시
       필요해질 것이므로(중단/재시작 흔함) 이 시점에 없으면 Pilot
       자체가 위험해진다.

4순위: Checksum(§7) 계산 및 Audit Log(§6) 기록 — Pilot 결과를 사람이
       사후 검토할 수 있어야 다음 단계(Corpus-wide) 승인 근거가
       생긴다.

5순위: Dry Run(§9) — Pilot 실행 직전 최종 확인 수단. 1~4가 갖춰진
       뒤에는 Dry Run이 "설계대로 동작하는지"를 값싸게 검증하는
       도구가 된다.

6순위: Migration Lock(§10) — Pilot은 보통 단일 작업자·단일 프로세스로
       실행되므로 동시성 위험이 낮지만, Corpus-wide 단계로 가기 전
       반드시 필요 — Pilot 후반부/Corpus-wide 착수 전에만 구현되어도
       무방.
```

### Q7. Corpus-wide Migration 착수 가능 여부

**NO(이번 설계 완료 시점 기준) — 이 설계 문서 자체가 착수 조건이
아니라 "착수 이전에 반드시 있어야 하는 청사진"이다.**

근거:
- 이번 작업(TASK-ORDER-041)은 **Design Only**이며 코드 한 줄도
  작성하지 않았다 — Migration Engine 자체가 아직 존재하지 않는다
  (Readiness Review §Phase2 "Migration Engine 코드 없음" 확인과
  동일 상태 유지).
- §최종 답변 Q6의 1~4순위(Migration Unit 계산/Checkpoint/Rollback/
  Idempotency/Audit)가 구현되고 Pilot Migration으로 최소 1회 이상
  실증되기 전까지, Corpus-wide 규모(수백~수천 entity)에 이 설계를
  적용하는 것은 위험도가 감당 불가능하다.
- 순서는 사용자가 이미 제시한 로드맵과 동일: **C1 Architecture
  Review(설계 검증) → Migration Engine Implementation → Pilot
  Migration → (재검토) → Corpus-wide Migration.**

---

*Git Commit/Push 미수행 — 워킹트리에만 존재. 설계 문서 3종
(`NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md`,
`NAE_METADATA_MIGRATION_STATE_MACHINE.md`,
`NAE_METADATA_MIGRATION_SEQUENCE.md`) 외 어떤 파일도 생성/수정하지
않음.*
