# ADR-030 Amendment D — Authority Tier (T1-T4) Doctrinal Orthodoxy Axis

| | |
|---|---|
| **Status** | **APPROVED** — 4조건(A1-A3 설계 승인, B1 구현, B2 회귀 통과, B3 구현 코드 C1 Review GREEN, B4 HQ 최종 승인) 전부 충족(2026-09-17) |
| **Amends** | `ADR-030-NAE-Sermon-Corpus-Governance.md` (IMPLEMENTED, 2026-08-28) — §7 Metadata Authority, §8.4 M2 Schema 보강, §12 M-2 |
| **Trigger** | 목회자 개인 RAG(DBMA/NAE) 제안서 §11/§13 — `NAE/citation_disclosure.py::get_tier_disclosure()`(커밋 `d7228074`, 2026-09-16)가 이미 T1-T4 라벨 조회 함수를 구현했으나, 이를 호출할 `authority_tier` 필드가 M2 어디에도 없음. 태깅 파이프라인 설계는 `docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md`(2026-09-16)로 선행 작성됨 |
| **Deciders** | Rev. Bang / HQ = Final Authority (설계 승인 2026-09-17, 최종 승인 2026-09-17) · CUE = Architecture + Implementation · C1 = Independent Review (설계 GREEN `_RESULT_002`, 구현 GREEN `_RESULT_003`) |
| **Approved** | 2026-09-17 (설계 A3 + 구현 B4, 채팅 승인, 이 세션) |
| **Approver** | David / HQ |
| **Adoption mutation** | 이 Amendment **채택**(문서 승인) 자체 = Code 0 / M2 신규 필드 0 / Qdrant 0 / TSU 0 — 승인 후 별도 구현 커밋에서 §2.1~§2.2를 실행한다. 이 문서는 설계 승인만 다룬다(Amendment A/B와 동일 관례 — 승인과 구현을 분리) |
| **Protected baseline (변경 금지)** | M2 원본 15개 레코드(원 14개 + Amendment B의 Spurgeon 1건)의 기존 필드 값 — 1글자도 변경하지 않는다. `authority_class` 4-enum(§7.2), `category`/`authority_class` 관계 선언(§7.3) 무변경 |

---

## 1. 배경 — 왜 새 축이 필요한가

ADR-030 §7.3은 이미 한 번 이 문제를 풀었다: `category`(TSU record, 주제/장르)와 `authority_class`
(M2, 교리적 무게)가 서로 다른 개념·다른 계층임을 선언하고, "중복 필드를 새로 만들지 않는다"는
원칙 아래 두 필드를 독립적으로 유지했다. 이번에 발생한 것은 **세 번째 개념**이다.

- `category` — "무엇에 관한 것인가" (주제/장르)
- `authority_class` — "근거로서 얼마나 무겁게 다룰 것인가" (출처 장르·제작 신뢰도: `primary_doctrinal`/
  `historical_witness`/`reference`/`application`)
- **`authority_tier` (신규 제안)** — "이 사용자 자신의 신앙고백에 비추어, 이 자료를 정통 교리로
  제시해도 되는가" (신학적 정통성)

세 번째 축이 필요한 이유는 `authority_class`만으로는 표현할 수 없는 경우가 실제로 존재하기
때문이다: 어떤 자료는 `primary_doctrinal`(해당 공동체 자신에게는 1차 교리 문헌)이면서 동시에
사용자 자신의 전통에서는 이단·타종교 자료일 수 있다(예: 말일성도 「교리와 성약」— LDS 공동체
안에서는 `primary_doctrinal`이지만, 이 시스템 사용자에게는 비교·변증 목적으로만 인용되어야
한다). `authority_class` 하나로 이 두 판단을 동시에 담으려 하면 §7.3이 이미 경고한 "중복 필드"
문제가 재발한다 — 그래서 §7.3과 동일한 해법(독립된 축 신설, 관계 명시적 선언)을 적용한다.

## 2. 이 Amendment가 하는 일

### 2.1 관계 선언 (§7.3 패턴 적용)

> **`authority_class`와 `authority_tier`는 서로 다른 개념이며 서로 다른 판단 기준을 쓴다.**
>
> | | `authority_class` (기존, §7.2) | `authority_tier` (신규 제안) |
> |---|---|---|
> | 계층 | source / manifest M2 (per-source) | source / manifest M2 (per-source) — **같은 계층, 다른 축** |
> | 축 | 출처 장르·제작 신뢰도 ("이 자료는 어떤 종류이고 추출 품질은 어떤가") | 신학적 정통성 ("사용자 자신의 전통에 비추어 정통 교리로 제시 가능한가") |
> | 값 | `primary_doctrinal` / `historical_witness` / `reference` / `application` | `T1`(정경/신조) / `T2`(검증된 신학) / `T3`(비교·변증 참고) / `T4`(미검증) |
> | 판단 주체 | 자료 자체의 성격(장르·제작 경위) | **사용자(HQ)의 신앙고백을 기준점으로 한 상대적 판단** — 같은 자료도 사용자가 바뀌면 tier가 달라질 수 있음 |
> | 독립성 | 한 레코드가 `primary_doctrinal` + `T3`, 또는 `historical_witness` + `T2` 등 임의 조합 가능 | 동상 |
>
> **중복 필드를 새로 만들지 않는다.** `authority_tier`는 `authority_class`를 대체하지 않고,
> `authority_class`도 정통성 판정에 쓰이지 않는다. 두 필드는 독립적으로 채워진다 (§7.3의
> "두 필드는 독립적으로 채워진다" 원칙을 그대로 계승).

**C1 Review 반영 (`NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_001.md`, 질문 7, YELLOW
finding):** 위 표는 §7.3과 구조적으로 유사하지만, "판단 주체" 행이 보여주듯 §7.3에는 없던
차원을 추가한다 — `category`/`authority_class`는 둘 다 **자료 자체의 성격**만으로 값이
정해지는 반면, `authority_tier`는 **사용자(HQ)의 신앙고백을 기준점으로 삼는 상대적 판단**이다.
같은 자료(예: 어떤 교단의 신앙고백서)라도 이 시스템을 사용하는 목회자가 바뀌면 `T2`(own)일
수도, `T3`(other_christian)일 수도 있다 — `authority_class`나 `category`에는 이런 사용자
상대성이 존재하지 않는다. 따라서 이 관계 선언은 §7.3 패턴의 단순 재사용이 아니라, 그 패턴을
**사용자 상대적 축에까지 확장**하는 것임을 명시적으로 인정한다.

### 2.2 신규 필드 (M2, `required: false` — §7.5 원칙 계승)

```
authority_tier     : enum { T1, T2, T3, T4 }              — optional
tradition_relation : enum { own, allied, other_christian,
                             non_christian, heterodox }    — authority_tier 있으면 required
counter_refs       : list[source_id]                       — authority_tier=T3 이면 non-empty required
```

미지정 source는 §7.5와 동일하게 **FAIL이 아니라 WARNING** → Admission Decision 대기로 취급한다.
소비자(예: 미래의 retrieval scope filter)는 필드 부재를 `T4`(미검증)와 동일하게 취급해야 한다 —
fail-closed 기본값. 이 fail-closed 규칙은 이 Amendment가 명문화하는 계약이며, 구현 시
`get_tier_disclosure()`가 아닌 별도 소비자 코드(아직 존재하지 않음, §13.2 ①-⑤에 해당)가 지켜야
할 의무다.

### 2.3 코드 변경 (설계만 — 구현은 이 문서 승인 이후 별도 커밋)

`docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md` §4-§6에 상세 설계 완료:

- `NAE/pipeline/registration/pipeline.py::RegistrationRequest`에 3개 optional 필드 추가,
  manifest_entry 조립 블록에 조건부 포함 — Amendment B가 `content_genre`/`authority_class`/
  `tradition`/`theological_category`에 쓴 것과 **동일한 코드 패턴**(§2.1 Amendment B 참고).
- `manifest_writer.write_entry()` 무변경 — 이미 임의 키를 쓰는 append-only 계약(Amendment B §2.1
  수정 이후).
- `scripts/m2_source_registry_validator.py`에 V9(tier vocab)/V10(T3 counter_refs 필수)/V11(counter_ref
  참조 무결성) 3개 신규 검사 추가.

### 2.4 예시 (신규 레코드, illustrative — 실제 등록 아님)

```yaml
# Amendment D 승인 이후에만 유효 — 예시일 뿐, 이 Amendment 자체는 M2를 쓰지 않는다
authority_tier: T2
tradition_relation: own
```

```json
// NAE/governance/corpus_admissions.jsonl — 승인 이후 실제 태깅 시 이 형태로 append
{"source_id": "BAP-CHURCH-DAGG-001", "decided_by": "David / HQ", "date": "2026-XX-XX", "authority_tier": "T2", "tradition_relation": "own", "rationale": "...", "evidence_refs": ["docs/architecture/ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md"]}
```

## 3. 변경하지 않는 것 (Freeze 유지)

- M2 기존 15개 레코드(원 14 + Amendment B의 Spurgeon)의 **모든 필드 값** — 1바이트도 재기록하지
  않는다.
- `authority_class` 4-enum, §7.3의 `category`/`authority_class` 관계 선언 — 무변경. 이 Amendment는
  그 옆에 **세 번째, 독립된** 축을 추가할 뿐이다.
- `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) — Qdrant 무접촉.
- Retrieval Engine — `core/retrieval.py::RetrievalEngine`은 이 Amendment로 변경되지 않는다.
  `authority_tier`를 실제 검색 스코프 필터링에 사용하는 것(제안서 §13.2 ①-⑤)은 **별도의, 더 큰
  변경**이며 이 Amendment의 범위 밖이다 — 승인되더라도 Retrieval Engine 변경 권한을 주지 않는다
  (CLAUDE.md "반드시 지켜야 하는 사항": Retrieval Engine은 명령 없이는 절대 변경 금지).

  > **명시적 게이트 (C1 Review 반영, 질문 9, YELLOW finding):** 이 산문 선언만으로는 향후 이
  > Amendment를 근거로 retrieval scope filter 구현을 시도하는 것을 기술적으로 막지 못한다는
  > 지적에 따라, 다음을 이 Amendment의 **승인 범위에 대한 명시적 제약**으로 못박는다 — **본
  > Amendment의 승인은 `core/retrieval.py` 또는 그 어떤 검색 경로 코드의 변경에도 권한을
  > 부여하지 않는다. `authority_tier`를 실제 검색 스코프 필터링·랭킹·컨텍스트 조립에 사용하는
  > 구현은, CUE 자신이 제안하는 경우를 포함해, 별도의 ADR Amendment 또는 신규 ADR의 C1
  > Review + HQ 승인을 다시 거쳐야만 착수할 수 있다.** 이 Amendment의 승인을 그 별도 승인의
  > 대체·선행 근거로 인용하는 것은 금지된다.
- ADR-030 §4 TSU Track, §11 human-review 요구, §13 Migration, §14 Production Safety, §16 Scale
  Protection — 전부 그대로.
- `NAE/citation_disclosure.py::get_tier_disclosure()`(커밋 `d7228074`) — 이미 구현·병합된 상태
  그대로. 이 Amendment는 그 함수가 호출할 데이터(§2.2 필드)를 만드는 절차만 정의한다.

## 4. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule)

이 Amendment는 Plan 001 §11이 정의한 대로 **2단계 게이트**를 거친다 — (A) 설계 자체의 승인
게이트(구현 착수 여부를 결정), (B) 구현 이후의 표준 4조건 승격 게이트(Amendment B가 거친 것과
동일한 절차). A가 끝나야 B가 시작된다.

### 4-A. 설계 승인 게이트 (Plan 001 §11, 구현 착수 전)

| # | 조건 | 상태 |
|---|---|---|
| A1 | ADR-030 Amendment 초안 작성 | ✅ 완료 (본 문서, 2026-09-16) |
| A2 | C1 독립 검토 GREEN (설계 문서 대상, 코드 없음) | ✅ **완료** — 1차 YELLOW(`_RESULT_001.md`, 2026-09-17) → 3개 finding 해소 → 재검토 GREEN(`_RESULT_002.md`, 2026-09-17). CUE 사후 검증에서 git HEAD 메타데이터 1건 불일치 발견·기록했으나 내용 검증에는 영향 없음(해당 문서 §CUE 사후 검증 참고) |
| A3 | HQ 승인 (설계 자체에 대한) | ✅ **완료** (2026-09-17, David/HQ, 채팅 승인 — "승인" 및 이후 구현 브랜치 생성 지시로 재확인) |

**A1·A2·A3 전부 완료 — §4-B 구현 게이트 진행 가능.**

### 4-B. 구현 승격 게이트 (A3 완료 후 시작)

| # | 조건 | 상태 |
|---|---|---|
| B1 | 구현 완료 (§2.3 코드 변경 + §2.2 validator 신규 검사) | ✅ **완료** (2026-09-17, CUE, 브랜치 `claude/authority-tier-m2-implementation`) — `NAE_AUTHORITY_TIER_M2_TAGGING_BUILD_REPORT_001.md` 참고 |
| B2 | 회귀 테스트 통과 (`tests/test_m2_source_registry_governance.py` 신규 pos/neg 케이스 포함, 전체 스위트 무회귀) | ✅ **완료** — 신규 6종(pos_08/09, neg_09~12) 전부 PASS, 전체 스위트 3076 passed/17 skipped, 사전 존재 실패 2건(TSU baseline 드리프트, 본 구현과 무관)은 Build Report §3에 별도 기록 |
| B3 | C1 독립 검토 GREEN (이번엔 실제 구현 코드 대상 — A2의 설계 검토와는 별개, Amendment B 선례와 동일한 사후검증형) | ✅ **완료** (2026-09-17, `NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_003.md` — GREEN, CUE가 5개 핵심 주장 독립 재검증 완료. CONCERN 1건(V9 tradition_relation 누락 negative 테스트)은 즉시 반영: `test_neg_09b_tier_without_tradition_relation_fails` 추가, 34 passed) |
| B4 | HQ 승인 (구현에 대한, 최종) | ✅ **완료** (2026-09-17, David/HQ, 채팅 승인 — "승인") |

**Architecture Freeze Rule에 따라, A3(설계 HQ 승인) 완료 이전에는 어떤 코드 구현도
진행되지 않았다(git 히스토리 확인: 본 구현 커밋은 A3 완료 이후).** A1-A3·B1-B4 전부 충족 —
**본 Amendment는 APPROVED로 승격되었다.**

## 5. 관련 문서

- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §7 (Metadata Authority), §8.4 (M2 Schema
  보강), §12 M-2
- `docs/architecture/ADR-030-AMENDMENT-B-Reference-Track-Post-Freeze-Registration.md` (형식·코드 패턴
  선례 — `RegistrationRequest` optional 필드 추가 방식을 그대로 계승)
- `docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md` (전체 태깅 파이프라인 설계, §3-§9)
- `NAE/citation_disclosure.py` 커밋 `d7228074` (T1-T4 라벨 조회 함수 — 이 Amendment가 채워줄 데이터의
  소비자)
- 목회자 개인 RAG(DBMA/NAE) 제안서 §11 (등급 태깅 스키마), §13 (경고 라벨 삽입 로직)

---

**완료 (2026-09-17)**: A1-A3(설계 승인) → B1(구현, `NAE_AUTHORITY_TIER_M2_TAGGING_BUILD_REPORT_001.md`)
→ B2(회귀 통과) → B3(구현 코드 C1 Review GREEN, `_RESULT_003.md`) → B4(HQ 최종 승인) 전부 완료.
**본 Amendment는 APPROVED로 승격되었다.** 이후 단계는 Plan 001 §6-§8(실제 M2 backfill,
`corpus_admissions.jsonl` 태깅)이며, 이는 이번 구현 범위 밖의 별도 HQ 결정·별도 작업이다.
