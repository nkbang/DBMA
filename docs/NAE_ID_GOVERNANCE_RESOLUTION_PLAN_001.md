# NAE ID Governance Resolution Plan 001

작성일: 2026-08-03
Project: NAE-ID-GOVERNANCE-RESOLUTION-001
성격: **정책 설계 및 영향 분석 — Registry/Manifest/RAW/TSU/Embedding/Retrieval 변경 없음**
근거: [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md),
[ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md),
`scripts/authority_validator.py` 실행 결과(74 PASS/26 WARNING/0 FAIL)

---

## 1. Warning 26건 목록 (실측, `authority_validator.py` 실행 결과 그대로)

| Entity | ID |
|---|---|
| Author | `FULLER-ANDREW-001` |
| Work | `WORK-DAGG-CHURCH-ORDER-001`, `WORK-HISCOX-STANDARD-MANUAL-001`, `FULLER-COMPLETE-WORKS-001` |
| Edition | `WORK-DAGG-CHURCH-ORDER-001-1871`, `WORK-HISCOX-STANDARD-MANUAL-001-1890`, `FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820`, `FULLER-COMPLETE-WORKS-001-ED-NEWHAVEN-CONVERSE` |
| Volume | `FULLER-COMPLETE-WORKS-VOL01`~`VOL08`(8건) |
| Source | `BAP-CHURCH-DAGG-001`, `BAP-CHURCH-HISCOX`, `BAP-MISS-FULLER-VOL01`~`VOL08`(8건) |

합계: 1(Author) + 3(Work) + 4(Edition) + 8(Volume) + 10(Source) = **26건**
(`authority_validator.py` 실행 결과와 정확히 일치, 신규 계산 아님).

---

## 2. 분류 결과

**26건 전부 Type A(Canonical ID 불일치)** — Type B/Type C 해당 사례
없음. 근거:

| 분류 | 판정 기준 | 이번 26건 해당 여부 |
|---|---|---|
| **Type A**(Canonical 불일치) | ADR-017 표기(lowercase snake_case)와 다르지만 canonical 값으로 전환 가능 | **26/26 해당** |
| **Type B**(Legacy 유지 필요) | 외부 시스템/문서가 이 정확한 문자열로 이미 참조하고 있어 canonical_id+legacy_alias 병기가 필요 | 0건 — 아래 §2.1 참고 |
| **Type C**(Migration 불필요) | 이미 v1.2 레거시 네임스페이스(`SLBC1689`류)이거나 외부 Archive ID | 0건 — 이 26건은 v1.2 레거시가 아니라 Pilot-001/002(v2.x 트랙) 등록 시 만들어진 **비표준 표기**일 뿐(ID Governance v1 §1 실측 재확인) |

### 2.1 "이미 참조 중"이 Type C를 성립시키지 않는 이유

실측(`grep -rl`) 결과 이 26개 ID는 **3개 계층·18개 데이터 파일**에서
참조되고 있다:

```
Production Registry(authority/*.yaml)              5 파일
Pilot Registry(authority/pilot/*, pilot/fuller/*)   10 파일(corpus manifest 포함)
Manifest Layer(manifest/pilot/*/manifest.yaml)       3 파일
```

"이미 참조 중"이라는 사실 자체는 Type C(Migration 불필요) 조건이
아니다 — Type C는 "외부 시스템이 이 정확한 문자열을 알고 있어 바꾸면
안 되는 경우"를 뜻하는데, 이 26건은 **내부 데이터 계층끼리만** 참조하고
있어 외부 종속성이 없다. 오히려 이 다층 참조는 **Migration Strategy의
blast radius(영향 범위)**로 다뤄야 할 사실이다(§3).

---

## 3. Migration Strategy

### Option A — 즉시 Rename

| | |
|---|---|
| 장점 | ADR-017 규칙 완전 준수, 이후 신규 데이터와 완전히 균일한 표기 |
| 위험 | 18개 파일(3개 계층)의 FK를 **한 트랜잭션으로** 동시에 바꿔야 함 — 하나라도 누락되면 `authority_validator.py`/`manifest_validator.py`가 즉시 Broken Reference로 잡아내긴 하지만, 그 사이 순간에도 데이터 일관성이 깨진 상태가 존재. 대상 규모(18파일)가 작지 않아 수작업 오류 가능성 존재 |

### Option B — Canonical + Legacy Alias 유지(권장)

| | |
|---|---|
| 장점 | 무중단 — 기존 FK 문자열을 그대로 두고 각 entity에 `canonical_id`(신규 필드) + `legacy_id`(현재 ID 보존)를 병기. 참조하는 쪽(다른 YAML)의 FK 값을 당장 바꾸지 않아도 무결성이 깨지지 않음 |
| 단점 | 과도기 동안 두 ID 체계가 공존 — Validator가 `legacy_id`/`canonical_id` 양쪽을 다 알아야 함(현재 세 Validator 어느 것도 이 필드를 인식하지 못함, §6 실행 순서에서 처리) |

### 결정: **Option B 채택**

ID Governance v1(§4)이 이미 동일한 결론("변경 필요 + `legacy_id` alias
보존")을 내려두었다 — 이번 Resolution Plan은 그 결정을 뒤집지 않고,
**3개 계층·18개 파일이라는 구체적 blast radius를 실측으로 추가
확인**해 Option B가 여전히(오히려 더) 타당함을 재확인했다.

---

## 4. ID Migration Map(정책 문서, 실행 아님)

**이미 `NAE_ID_GOVERNANCE_v1.md` §6.2에 26건 전부 존재** — 이번
Resolution Plan은 그 표를 재도출하지 않고 그대로 정본으로 채택한다
(재작성 시 두 문서가 어긋날 위험만 커짐). 요약:

```yaml
# Author(1건)
legacy_id: FULLER-ANDREW-001
canonical_id: fuller_andrew

# Work(3건)
WORK-DAGG-CHURCH-ORDER-001            -> dagg_john_l_church_order
WORK-HISCOX-STANDARD-MANUAL-001       -> hiscox_edward_t_standard_manual
FULLER-COMPLETE-WORKS-001             -> fuller_andrew_complete_works

# Edition(4건)
WORK-DAGG-CHURCH-ORDER-001-1871                -> dagg_john_l_church_order_1871
WORK-HISCOX-STANDARD-MANUAL-001-1890           -> hiscox_edward_t_standard_manual_1890
FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820  -> fuller_andrew_complete_works_1820_charlestown
FULLER-COMPLETE-WORKS-001-ED-NEWHAVEN-CONVERSE -> fuller_andrew_complete_works_1824_newhaven

# Volume(8건) — fuller_andrew_complete_works_1820_charlestown_v01,
#              fuller_andrew_complete_works_1824_newhaven_v02~v08

# Source(10건) — dagg_john_l_church_order_1871_s01,
#               hiscox_edward_t_standard_manual_1890_s01,
#               fuller_andrew_complete_works_{...}_v01~v08_s01
```

전체 26건 상세 매핑은 [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §6.2 참고.
**실제 rename은 이번 계획에서도 실행하지 않는다.**

---

## 5. ADR 영향 분석

### 판정: **ADR-017 유지**(수정 불필요), `NAE_ID_GOVERNANCE_v1.md`는 **문서 보완**

- ADR-017의 canonical ID 규칙(surname 우선 snake_case 등) 자체는
  이번 26건 실측으로 전혀 흔들리지 않았다 — 규칙은 옳고, 26건은 그
  규칙이 아직 **적용되지 않은** 기존 데이터일 뿐이다. 규칙을 바꿀
  이유가 없으므로 ADR-017 본문 수정은 불필요.
- `NAE_ID_GOVERNANCE_v1.md`는 이미 §6.2에 정확한 매핑표를 갖고
  있으나, **3계층 18파일 blast radius**(§2.1)와 **Option B 재확인
  근거**(§3)는 이번 문서(Resolution Plan)에만 있다 — 향후 혼동
  방지를 위해 `NAE_ID_GOVERNANCE_v1.md`에 이 Resolution Plan을
  가리키는 pointer 한 줄만 추가하는 것을 권고(이번 작업에서는
  실행하지 않음, §6에 후속 작업으로 기록).

---

## 6. Migration Readiness 영향 및 향후 실행 순서

### 답변

```
Metadata Migration 가능?  NO
TSU Pipeline 영향?        YES
```

- **Metadata Migration = NO**: WARNING 26건 자체는 참조 무결성 오류가
  아니지만(FAIL 0건), 사용자가 이미 확립한 로드맵상 "ID Governance
  Migration"이 "Corpus-wide Metadata Migration"보다 선행되어야
  한다는 순서 결정을 이번 계획이 뒤집을 근거가 없다 — 오히려 §2.1의
  18파일 blast radius가 그 순서가 안전한 이유를 뒷받침한다(대량
  자료 유입 전에 ID 체계부터 안정화하는 편이 이후 재작업을 줄임).
- **TSU Pipeline 영향 = YES**: 지금 비표준 ID로 TSU를 생성하면, 이후
  canonical_id로 전환할 때 이미 생성된 TSU 레코드 안의 참조까지
  함께 갱신해야 한다(재생성 비용 발생) — ID 정리를 TSU 생성보다
  먼저 하는 편이 안전하다.

### 향후 실행 순서(계획만, 이번 작업 범위 밖)

```
1. 이번 Resolution Plan(정책) 승인
        ↓
2. C1 ID Governance Review-002(독립 검증)
        ↓
3. canonical_id/legacy_id 필드를 Registry Schema에 추가하는 설계
   (Option B 실행 설계 — 아직 없음, 별도 CUE 작업 필요)
        ↓
4. 3개 Validator(source/manifest/authority)가 canonical_id/legacy_id
   양쪽을 인식하도록 확장(코드 변경, 별도 승인)
        ↓
5. Registry 18개 파일에 실제 canonical_id 필드 추가(RAW/FK 문자열
   자체는 변경 안 함 — Option B 원칙)
        ↓
6. 이후에만 Corpus-wide Metadata Migration 재검토
```

---

## 완료 보고

```
STATUS: COMPLETE (policy design only, no data changes)
FILES CREATED: docs/NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md

WARNING COUNT: 26
TYPE A: 26
TYPE B: 0
TYPE C: 0

MIGRATION STRATEGY: Option B (Canonical + Legacy Alias 유지) — 즉시 Rename(Option A) 기각

ADR-017 IMPACT: 유지(수정 불필요) — NAE_ID_GOVERNANCE_v1.md는 문서 보완(pointer 추가) 권고, 이번엔 미실행

METADATA MIGRATION READY: NO
```

---

*RAW Corpus, Manifest, TSU Dataset, Embedding, RetrievalEngine, Registry
YAML — 전부 수행하지 않음(read-only inspection + validator 실행만).
Git Commit은 사용자 승인 후에만 수행한다.*
