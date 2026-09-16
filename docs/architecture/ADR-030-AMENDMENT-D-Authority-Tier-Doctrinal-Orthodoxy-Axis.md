# ADR-030 Amendment D — Authority Tier (T1-T4) Doctrinal Orthodoxy Axis

| | |
|---|---|
| **Status** | **PROPOSED (DRAFT)** — Evidence Before Promotion Rule 4조건 중 0개 충족. 구현 착수 전, C1 Review 요청 대기 |
| **Amends** | `ADR-030-NAE-Sermon-Corpus-Governance.md` (IMPLEMENTED, 2026-08-28) — §7 Metadata Authority, §8.4 M2 Schema 보강, §12 M-2 |
| **Trigger** | 목회자 개인 RAG(DBMA/NAE) 제안서 §11/§13 — `NAE/citation_disclosure.py::get_tier_disclosure()`(커밋 `d7228074`, 2026-09-16)가 이미 T1-T4 라벨 조회 함수를 구현했으나, 이를 호출할 `authority_tier` 필드가 M2 어디에도 없음. 태깅 파이프라인 설계는 `docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md`(2026-09-16)로 선행 작성됨 |
| **Deciders** | Rev. Bang / HQ = Final Authority · CUE = Architecture (초안 작성) · C1 = Independent Review (미착수) |
| **Approved** | — (PROPOSED) |
| **Approver** | — |
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
- ADR-030 §4 TSU Track, §11 human-review 요구, §13 Migration, §14 Production Safety, §16 Scale
  Protection — 전부 그대로.
- `NAE/citation_disclosure.py::get_tier_disclosure()`(커밋 `d7228074`) — 이미 구현·병합된 상태
  그대로. 이 Amendment는 그 함수가 호출할 데이터(§2.2 필드)를 만드는 절차만 정의한다.

## 4. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule)

| # | 조건 | 상태 |
|---|---|---|
| 1 | 구현 완료 (§2.3 코드 변경 + §2.2 validator 신규 검사) | ⬜ 미착수 — 이 Amendment 승인 후 별도 구현 커밋 필요 |
| 2 | 회귀 테스트 통과 (`tests/test_m2_source_registry_governance.py` 신규 pos/neg 케이스 포함, 전체 스위트 무회귀) | ⬜ 미착수 |
| 3 | C1 독립 검토 GREEN | ⬜ 요청 대기 — 트리거 조건 충족(신규 Metadata Model 변경, CLAUDE.md 명시 항목) |
| 4 | HQ 승인 | ⬜ 대기 |

**4조건 중 0개 충족 — 이 문서는 PROPOSED 상태를 유지한다.** Architecture Freeze Rule에 따라, 이
Amendment가 APPROVED로 승격되기 전까지 `authority_tier`/`tradition_relation`/`counter_refs`는
어떤 M2 레코드에도 쓰여서는 안 되며, 이 필드들을 전제로 한 어떤 구현도 진행되어서는 안 된다.

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

**다음 단계**: C1 Review 요청 (`docs/agents/c1/` 관례에 따라 C1 Review Request 문서 작성 후 제출).
C1 GREEN 이후 §4 조건 1-2(구현·회귀) 진행, 마지막으로 HQ 승인.
