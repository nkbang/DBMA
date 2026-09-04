# NAE Metadata Schema 2.0.0 Design Review 001

**Project:** NAE-METADATA-SCHEMA-2.0.0-DESIGN-001
**작성일:** 2026-08-08
**성격:** DESIGN + READ-ONLY AUDIT ONLY. Production 데이터/코드 무수정, Migration 미실행.
**Git Commit/Push:** 미수행.

---

## 0. Authority 확인

1. `docs/NAE_TSU_BUILDER_EXECUTION_RECOVERY_REVIEW_001.md`(C1, §6.2/§9/§10/§Q4/§Q5) — BLOCKER의 근거
2. `docs/NAE_C1_REVIEW_CONDITION_FOLLOWUP_002.md`(CUE, 이전 작업) — BLOCKER 재확인
3. `docs/NAE_METADATA_GOVERNANCE_v1.md` — 값 체계/Authority Model의 유일한 정본(§4/§5/§6)
4. `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`, `ADR-015-NAE-Corpus-Ingestion-Standard.md`, `ADR-016-NAE-Metadata-Authority-Model-Revision.md`, `ADR-019-NAE-Corpus-Manifest-Layer.md`
5. 실제 파일: `resources/theological_sources/authority/*.yaml`, `resources/theological_sources/manifest/pilot/*/manifest.yaml`, `resources/theological_sources/modern/source_manifest.schema.yaml`, `NAE/corpus/tsu/*/tsu.json`

---

## 1. 핵심 발견 — "Schema 2.0.0"은 하나가 아니라 3개의 병렬 스키마 계층이다

실제 저장소를 조사한 결과, 현재 저장소에는 서로 다른 3개의 독립 스키마
체계가 공존한다. 이 구분을 하지 않으면 Migration 대상을 잘못 잡는다.

| 계층 | 정의 파일 | schema_version | 실제 데이터 존재 여부 |
|---|---|---|---|
| A. NAE-PD (Legacy) | `resources/theological_sources/source_manifest.schema.yaml` | `1.2` | 있음(기존 baptist/ 등) |
| B. NAE-MODERN(설계) | `resources/theological_sources/modern/source_manifest.schema.yaml` | `2.1.0`(스키마 파일 자체에 명시, `version_history`에 `2.0.0`→`2.1.0` 기록) | **없음** — `resources/theological_sources/modern/`에는 스키마 정의 파일 1개만 있고 실제 source 데이터는 0건(`find` 확인) |
| C. Authority Registry + Manifest Pilot(실사용, Production) | `authority/*.yaml`(schema_version `1.0`) + `manifest/pilot/*/manifest.yaml`(schema_version `1.0.0`, ADR-019) | `1.0` / `1.0.0` | **있음** — Dagg/Hiscox/Fuller 8권, 이번 작업의 실제 대상 |

**결론**: C1이 지목한 "Metadata Schema 2.0.0 Migration"의 실제 Migration
대상은 계층 B(파일만 있고 데이터가 0건인 미사용 설계)가 아니라 **계층
C(Authority Registry + Manifest Pilot, 실제 운영 중인 Production 데이터)이다.**
계층 C는 라벨상 schema_version `1.0`/`1.0.0`이지만, `NAE_METADATA_GOVERNANCE_v1.md`
§4(copyright_status/usage_permission/access_control/source_type)와 §5
(Author/Work/Edition/Volume) 값 체계를 **이미 실질적으로 구현**하고 있다
(아래 §4 필드 표에서 실측 확인). 즉 "Schema 2.0.0 Migration"의 진짜
의미는 (a) NAE TSU v3에 Governance §6이 요구하는 9개 필드를 채워 넣는
것과, (b) 계층 C의 `schema_version` 라벨을 Governance 값 체계와 정합하게
정리하는 것 2가지로 좁혀진다 — 계층 B 파일을 실제 데이터로 채우는 작업이
아니다.

---

## 2. Governance §6 필수 9개 필드 — Authoritative Source에서 추출

`docs/NAE_METADATA_GOVERNANCE_v1.md` §6 원문 그대로:

```yaml
source_id: string
author_id: string
work_id: string
edition_id: string          # 필수(2026-08-02 승격)
volume_id: string           # 조건부 필수(다권본만)
category: string
publication_year: integer
source_type: licensed | purchased | personal | reference | public_archive
copyright_status: public_domain | copyrighted | licensed | unknown
citation_policy: string
tsu_access: full | restricted | citation_only   # copyright_status×usage_permission 조합의 산출값(§6 표)
```

`usage_permission`/`access_control`은 §4.2/§4.3에 별도 정의되며, §6
TSU 필수 필드 목록에는 직접 나열되지 않지만 `tsu_access` 산출과
Index 단계 필터링에 필수로 사용된다(§6 원문: "access_control=private인
자료는 tsu_access 값과 무관하게 검색 결과에 노출하지 않는다").

---

## 3. 필드별 실측 대조표

FIELD | REQUIRED | CURRENT LOCATION | CURRENT VALUE(Dagg 예시) | SOURCE OF TRUTH | MIGRATION REQUIRED | CAN BE DERIVED SAFELY

| FIELD | REQUIRED | CURRENT LOCATION | CURRENT VALUE(Dagg) | SOURCE OF TRUTH | MIGRATION REQUIRED | CAN BE DERIVED SAFELY |
|---|---|---|---|---|---|---|
| `source_id` | Yes | Registry(`authority/sources.yaml`), Manifest | `BAP-CHURCH-DAGG-001` | Registry(Source File entity, §5.1) | TSU v3에 없음 → 추가 필요 | **YES** — Crosswalk(`manual-confirmed`)로 TSU `identifier`(`Dagg_Church_Order`) ↔ Registry `source_id` 매핑 이미 존재(2건, Dagg/Hiscox) |
| `author_id` | Yes | `authority/authors.yaml`(Authority 원본), Manifest(중복 보유) | `dagg_john_l` | **`authority/authors.yaml`가 authoritative**(Author entity, §5.1) — `authority/sources.yaml`은 Source File entity라 author_id를 갖지 않는 것이 §5.1 설계상 정상(아래 §4 참고) | TSU v3에 없음 → 추가 필요 | **YES**(Dagg/Hiscox만) — `source_id → works.yaml.author_id`(via `edition_id→work_id` 체인) 또는 Manifest의 직접 보유값으로 확인 가능 |
| `work_id` | Yes | `authority/works.yaml`(원본), Manifest(중복 보유) | `WORK-DAGG-CHURCH-ORDER-001` | `authority/works.yaml` | TSU v3에 없음 → 추가 필요 | **YES**(Dagg/Hiscox만) — Manifest 직접 보유 |
| `edition_id` | Yes | Registry, `authority/editions.yaml`, Manifest | `WORK-DAGG-CHURCH-ORDER-001-1871` | `authority/editions.yaml` | TSU v3에 없음 → 추가 필요 | **YES** — Registry/Manifest 양쪽 다 보유, 일치 확인됨 |
| `volume_id` | 조건부(다권본만) | Registry, Manifest | `null`(Dagg/Hiscox는 단권 — 정상) | `authority/volumes.yaml`(다권본만 존재, Fuller 8권 확인됨) | Dagg/Hiscox는 불필요(정상 null), Fuller류는 TSU 생성 시점에 필요 | **YES**(단권은 null 자체가 정답, 다권본은 `volumes.yaml` 보유) |
| `category` | Yes | **어디에도 Production 값 없음** — `authority/pilot/source_manifest.yaml`(구버전, 승격 시 제외됨)에만 `category: church_order` 존재 | 없음(Registry에 의도적 제외, `authority/sources.yaml` 헤더 주석: "citation_policy/tsu_access/... 는 이 Registry의 책임이 아니라 corpus manifest의 책임") | **모호함** — Registry 주석은 "Manifest 책임"이라 하나, 실제 ADR-019 Manifest Schema v1.0.0(`manifest/pilot/*/manifest.yaml`)에도 `category` 필드가 없음(§4 실측) | 필요 | **NO(단, 예외적으로 낮은 리스크)** — Pilot 구버전 파일에 값이 남아있으나 "승격 시 의도적으로 제외된 필드"이므로 그 값을 그대로 재사용해도 되는지는 사람 확인 필요(설계 결정 재확인 필요, 추측 금지 원칙 적용) |
| `publication_year` | Yes | `authority/editions.yaml` | `1871` | `authority/editions.yaml` | TSU v3에 없음 → 추가 필요 | **YES** — Edition 단위로 확정값 보유, 다권본은 Volume별 값도 별도 존재(§5.2) |
| `source_type` | Yes | Registry | `reference` | Registry | TSU v3에 없음 → 추가 필요 | **YES**(값은 있으나 §4.4 아래 WARNING 참고) |
| `copyright_status` | Yes | Registry | `public_domain` | Registry | TSU v3에 없음 → 추가 필요 | **YES** |
| `citation_policy` | Yes | **어디에도 Production 값 없음** — `category`와 동일하게 Pilot 구버전에만 존재 | 없음 | 모호함(§`category`와 동일 문제) | 필요 | **NO** — 동일 사유, 사람 확인 필요 |
| `tsu_access` | Yes(산출값) | **어디에도 저장되지 않음** — Governance §6 표(`copyright_status`×`usage_permission` 조합)로 매 순간 계산해야 하는 derived 값 | 미저장 | Governance §6 조합표(코드 규칙) | 저장 여부 자체가 설계 결정 필요(저장 vs 매번 계산) | **YES(규칙 기반 계산)** — `copyright_status=public_domain`이면 조합표상 Full TSU → `tsu_access=full`. 규칙이 명시적이므로 "추측"이 아니라 "결정론적 산출" |
| `usage_permission` | (§4.2, TSU 필수 목록 외) | Registry | `research` | Registry | TSU v3에 없음 → 추가 필요 | **YES** |
| `access_control` | (§4.3, TSU 필수 목록 외) | Registry | `public` | Registry | TSU v3에 없음 → 추가 필요 | **YES** |
| `schema_version` | (문서 자체) | Registry(`1.0`), Manifest(`1.0.0`), NAE TSU v3(`tsu_schema_version="1"`, 별개 개념) | 계층별 상이 | §7 참고 — 규명 결과 아래 §7 | 라벨 정리 필요(값 재계산 아님) | 해당 없음(버전 정책 문제) |

### 3.1 `category`/`citation_policy` — WARNING(추측 금지 대상)

이 두 필드는 **현재 어떤 Production Authoritative 파일에도 존재하지
않는다.** Registry 주석은 "corpus manifest의 책임"이라 명시하지만, 실제
ADR-019 기준 Manifest Schema v1.0.0(`manifest/pilot/*/manifest.yaml`)에는
정의되어 있지 않다 — Registry의 "책임 위임" 주석과 실제 Manifest 스키마
사이에 불일치가 있다. Pilot 구버전 파일(`authority/pilot/source_manifest.yaml`)에
남아있는 `category: church_order`/`citation_policy: "Dagg, John L. ..."`
값을 그대로 재사용할 수 있어 보이지만, 이 값이 **의도적으로 승격 대상에서
제외된 값인지 단순 누락인지가 문서상 불명확**하므로 추측으로 채우지
않는다. **사람의 확인이 필요한 항목으로 분류한다.**

### 3.2 `source_type=reference` — WARNING(값 정확성 의심)

Governance §4.4는 `public_archive`(archive.org 등 공개 아카이브에서 확보한
PD 스캔본, 전문 저장 가능)와 `reference`(발췌만 허용, 전문 저장 불가)를
명확히 구분한다. 그러나 Dagg/Hiscox의 실제 획득 경로는 이번 작업 계열의
Corpus Recovery(`NAE-CORPUS-RECOVERY-EXECUTION-001`)에서 확인된 대로
**archive.org 백업에서 복구**된 것이며, 실제로 전문(全文) 스캔 PDF+OCR가
저장되어 있다(발췌가 아님). Governance §4.4 정의에 따르면 이는
`public_archive`에 해당할 가능성이 높으나, 현재 Registry 값은
`reference`로 되어 있다. **이 값을 이번 작업에서 변경하지 않았다** —
Migration 설계 단계에서 재확인이 필요한 별도 WARNING으로만 보고한다
(Registry 수정은 이번 작업의 절대 금지 사항).

---

## 4. Registry ↔ Manifest 비대칭 조사

**초기 관찰(이전 FOLLOWUP-002 보고)**: Registry(`authority/sources.yaml`)에는
`author_id`/`work_id`가 없고 Manifest에는 있다 — 이번 작업에서 더 깊이
조사한 결과, 이것은 **버그가 아니라 §5.1 Entity 설계의 정상 결과**임을
확인했다:

```
Author(authority/authors.yaml, author_id 원본)
  ↓
Work(authority/works.yaml, work_id 원본, author_id를 FK로 보유)
  ↓
Edition(authority/editions.yaml, edition_id 원본, work_id를 FK로 보유)
  ↓
Volume(authority/volumes.yaml, 다권본만)
  ↓
Source File(authority/sources.yaml, source_id 원본, edition_id/volume_id를 FK로 보유 — author_id/work_id는 FK 체인을 타야 얻어짐)
```

즉 `authority/sources.yaml`은 원래 `author_id`/`work_id`를 **직접
보유하지 않는 것이 설계대로**다(Source File entity는 Edition까지만
FK를 가짐). Manifest(`manifest/pilot/*/manifest.yaml`)가 `author_id`/
`work_id`를 **중복 보유**하는 것은 편의상 denormalization이며, 이 값이
Registry의 FK 체인(`sources.edition_id → editions.work_id →
works.author_id`)과 실제로 일치하는지 Dagg/Hiscox 양쪽에서 실측
확인했다:

```
Dagg:   Manifest.author_id="dagg_john_l" == editions[edition_id].work_id → works[work_id].author_id="dagg_john_l"  (일치)
Hiscox: Manifest.author_id="hiscox_edward_t" == 동일 체인 결과           (일치)
```

**결론: 비대칭이 아니라 정상적인 정규화 구조이며, 현재 실제 값도
일치한다.** Migration 설계에서 author_id/work_id를 TSU v3에 채울 때는
Registry FK 체인을 authoritative source로 삼고(Manifest 값은 교차검증
용도로만 사용), 두 값이 불일치하는 사례가 향후 발견되면 Registry
체인을 우선한다(Registry가 §5.1 원본이므로).

---

## 5. NAE TSU v3(4,117건) 실제 메타데이터 현황

```
현재 TSU 필드(19개): id, tsu_schema_version, book, author, identifier,
source_identifier, collector_version, canonical_version, page, paragraph,
sentence, source_text, claim, doctrine, scriptures, citations, confidence,
extraction_method, review_status, model

Governance §6 요구 필드(9개) 중 TSU에 존재하는 것: 0개
누락 필드 수: 4,117건 × 9개 필드 = 37,053개 필드값 누락(레코드당 9개 전부)
```

### 5.1 안전하게 보완 가능한 필드(Registry/Manifest/Crosswalk로 derive)

Dagg_Church_Order(3,377건)와 Hiscox_Standard_Manual(740건) 전부
기존 **manual-confirmed Crosswalk 레코드 2건**(`NAE/metadata/crosswalk/crosswalk.yaml`)으로
100% 커버된다(TSU `identifier` 값이 이 2개뿐임을 실측 확인). 이 Crosswalk를
경유하면 아래 7개 필드는 **사람의 판단 없이 결정론적으로 도출 가능**하다:

```
source_id           (Crosswalk.target_identifier → source_identifier)
author_id            (Registry FK 체인 또는 Manifest 직접값, §4에서 일치 확인)
work_id               (동일)
edition_id            (Registry/Manifest 직접값)
volume_id             (Dagg/Hiscox는 null이 정답 — 다권본 아님)
publication_year      (editions.yaml)
source_type/copyright_status/usage_permission/access_control  (Registry 직접값)
tsu_access            (Governance §6 조합표로 계산 — public_domain → full)
```

### 5.2 사람의 확인이 필요한 필드(추측 금지)

```
category         — 어떤 Production 파일에도 authoritative 값 없음
citation_policy  — 동일
source_type의 정확성  — reference vs public_archive 재확인 필요(§3.2)
```

이 3개는 이번 작업에서 값을 만들어내지 않았다(지시 원칙 준수).

---

## 6. `schema_version` 정책 규명

`docs/NAE_METADATA_GOVERNANCE_v1.md` §2.2가 유일한 SemVer 정책
authority다:

```
Major: 구조 변경(필드 제거/의미 변경/entity 계층 변경)
Minor: 필드 추가(하위 호환, 기존 데이터 무효화 없음)
Patch: 오류 수정(구조 변경 없음)

원칙: 설계 단계 정정은 버전을 올리지 않되, 승인·데이터 생성 이후의
구조 변경은 반드시 Major bump로 기록한다.
```

**현재 Production 계층(C, §1)은 schema_version `1.0`/`1.0.0`이고,
Governance 문서가 정의하는 값 체계 버전은 `2.1.0`(계층 B, 실사용 데이터
0건)이다.** 이 둘은 **서로 다른 파일의 서로 다른 버전 번호이지 같은
스키마의 이력이 아니다** — 계층 C가 "1.0.0에서 2.1.0으로 올라가야 한다"는
전제 자체가 문서상 명시적으로 확인되지 않는다(Governance §2.1은 "Modern
manifest schema: 2.1.0"이라고만 말하며, 이것이 곧 `authority/*.yaml`+
`manifest/pilot/*`의 차기 버전이라고 선언한 문장은 어디에도 없다).

**이번 작업에서 버전 번호를 임의로 결정하지 않는다.** 대신 아래 2가지
옵션만 제시하고, 실제 채택은 별도 승인 대상으로 남긴다:

- **옵션 1**: 계층 C(Registry+Manifest Pilot)를 계층 B(Modern v2.1.0)로
  **통합**한다 — 이 경우 `resources/theological_sources/modern/`이 원래
  의도한 실제 사용처가 되고, `authority/*`+`manifest/pilot/*`는 이관
  대상이 된다. Major 구조 변경(entity 계층 이동)이므로 SemVer 원칙상
  최소 `3.0.0`(계층 C 기준) 또는 별도 협의 필요.
- **옵션 2**: 계층 C를 **독립 계보로 유지**하고, TSU v3에 필드를 추가하는
  작업은 계층 C의 `schema_version`을 `1.0`/`1.0.0` → `1.1.0`(Minor,
  필드 추가만이므로)으로 올린다 — 계층 B(Modern)는 그대로 미사용 설계로
  남긴다.

두 옵션 중 **어느 쪽이 Architecture 의도와 맞는지는 문서만으로 확정할
수 없다** — Governance 문서 자체가 "이 문서 발행 이후 이 문서의 값으로
대체된다(해당 원문은 소급 수정하지 않음)"고만 말할 뿐, 계층 C와 계층
B의 파일 단위 통합/분리 여부는 다루지 않는다. **이 결정은 사람의
승인이 필요한 항목으로 보고한다(추측하지 않음).**

---

## 7. Migration 방법 비교

### A. Additive Migration Script (기존 TSU metadata에 필드 추가)

```
NAE/corpus/tsu/{identifier}/tsu.json의 각 레코드에 §5.1의 7개 안전 필드를
Crosswalk 경유로 조회해 추가하는 별도 스크립트 실행
(builder.py 실행 없음 — LLM 재호출 없음)
```

| 항목 | 평가 |
|---|---|
| 소요 시간 | 매우 짧음(파일 I/O + YAML/JSON lookup, LLM 호출 없음 — 분 단위) |
| Architecture 영향 | `NAE/pipeline/tsu/builder.py`(claim/doctrine 추출 로직) 무관, 신규 별도 스크립트로 격리 가능 |
| Review Gate 영향 | 없음 — `review_status` 필드는 건드리지 않음 |
| Rollback 난이도 | 낮음 — 이번 Recovery 작업에서 이미 만든 백업(`NAE/corpus/tsu/_backup_20260807T015632/`)과 동일한 방식으로 migration 직전 재백업 후 실행하면 원상복구 trivial |
| 리스크 | 낮음 — 기존 필드(`claim`/`doctrine`/`review_status` 등) 손상 없이 순수 추가만 하면 안전 |

### B. TSU Regeneration(재생성)

```
builder.py를 다시 실행해 처음부터 9개 필드를 포함한 스키마로 4,117건을
재생성
```

| 항목 | 평가 |
|---|---|
| 소요 시간 | 매우 김 — 이전 Recovery 작업 실측 기준 Dagg+Hiscox 합계 약 12~13시간(LLM 재호출 필요) |
| Architecture 영향 | `builder.py` 자체를 수정해야 함(신규 필드를 레코드에 반영하는 로직 추가) — "builder.py 기능 변경 금지" 원칙과 충돌 가능성 |
| Review Gate 영향 | 없음(review_status는 여전히 generated로 재생성됨) |
| Rollback 난이도 | 낮음(백업 존재) 이지만 재실행 자체의 실패 리스크(이전 Execution Recovery에서 실제로 중단 사고 발생 이력)가 있음 |
| 리스크 | **높음** — (1) LLM 재호출로 claim/doctrine 판정이 이전 실행과 달라질 수 있어 이미 확보한 4,117건의 review 대상 콘텐츠 자체가 바뀜(불필요한 재작업), (2) 12시간대 장시간 실행 리스크 재발 가능성, (3) 이번 작업의 절대 금지 사항("TSU 생성/재생성 금지")에 정면으로 저촉 |

### 8. 권장 전략

**A안(Additive Migration Script) 채택을 권장한다.** 근거:

1. Governance §7.1 원칙("기존 데이터 보존 — RAW 변경 금지, 점진적
   Migration")과 정확히 부합 — claim/doctrine 등 이미 생성된 LLM 판정을
   그대로 보존하면서 메타데이터만 추가
2. LLM 재호출이 없어 리스크·소요시간이 극히 낮음
3. `builder.py`(추출 로직) 자체를 변경할 필요가 없어 "기능 변경 금지"
   원칙과 충돌하지 않음(별도 신규 스크립트로 구현 가능)
4. §5.2에서 확인한 "사람 확인 필요 필드"(category/citation_policy)는
   Migration Script가 우선 `null`/`pending_human_review` 같은 명시적
   placeholder로 남기고, 사람이 확정한 뒤 별도 patch를 적용하는 2단계
   구조로 설계하면 "추측 금지" 원칙을 그대로 지킬 수 있음

**이번 작업에서는 이 스크립트를 실제로 작성/실행하지 않는다** — 설계
방향 제안에 그친다.

---

## 9. Migration 후 필요한 검증 Gate(설계만)

```
1. Schema Validation:
   - 9개 필드 존재 여부(category/citation_policy는 명시적 placeholder 허용)
   - 필드 타입(publication_year=integer, volume_id는 다권본만 필수 등)

2. Metadata Authority Validation:
   - TSU.source_id가 Crosswalk를 통해 실제 Registry source_id와 일치하는지
   - author_id/work_id/edition_id가 §4 FK 체인과 일치하는지(Registry 우선)

3. Crosswalk Consistency:
   - Migration 대상 TSU의 identifier가 전부 manual-confirmed(또는 동급) Crosswalk를 가지는지
   - evidence-backed 아닌 매핑으로 필드를 채우지 않았는지

4. Review Gate:
   - review_status/review_metadata 필드가 Migration 전후로 완전히 동일한지(byte-diff)
   - Migration이 review_status를 절대 변경하지 않았는지

5. Regression:
   - 기존 tests/test_nae_tsu_builder.py, test_tsu_review_gate.py,
     test_indexer_review_gate_wiring.py, test_crosswalk*.py 전체 통과

6. Drift:
   - source_validator/manifest_validator/authority_validator 3종 PASS/WARNING/FAIL 수치 baseline과 동일(89/0/0, 138/0/0, 128/26/0)

7. Architecture Boundary:
   - core/retrieval.py, core/tsu_builder.py, Registry/Manifest 원본 파일 무수정
   - builder.py(claim/doctrine 추출 로직) 무수정

8. Production TSU Integrity:
   - claim/doctrine/scriptures/citations/confidence/extraction_method/model 등 기존 19개 필드 값이 Migration 전후 완전히 동일(추가만, 변경 없음)
   - 레코드 수(4,117건) 불변
```

---

## 10. E2E Readiness 판정

**Metadata Migration 완료만으로는 READY가 되지 않는다.** 이유:

1. §6에서 확인했듯, `schema_version` 정책 자체가 옵션 1/2 중 결정되지
   않은 상태 — Migration을 시작하기 전에 이 결정이 선행되어야 함(사람
   승인 필요)
2. §5.2의 `category`/`citation_policy` 2개 필드는 Migration Script만으로
   자동 완성될 수 없음 — 사람이 값을 확정해야 완전한 Schema 2.0.0
   준수가 됨
3. `NAE_C1_REVIEW_CONDITION_FOLLOWUP_002.md`의 WARNING 2건(Verified 개념
   전용 문서화, TSU Pipeline 분리 ADR)은 이번 작업 범위 밖으로
   Metadata Migration과 무관하게 별도로 남아있음
4. Metadata Migration이 완료되더라도 Review Gate(사람 검토 후 verified
   승급) 자체가 아직 실행된 적이 없음 — Embedding/Qdrant/Retrieval
   Benchmark로 가는 경로는 Metadata Migration 완료 이후에도 별도 단계로
   남음(원래 End-to-End Readiness 로드맵상 순서)

**판정: NOT READY.**

---

## 완료 보고

```
STATUS: BLOCKED

BLOCKER:
1. Metadata Schema 2.0.0 Migration 자체가 아직 미실행(이번 작업은 설계만 완료)
2. schema_version 정책(옵션 1/2) 미확정 — 사람 승인 필요
3. category/citation_policy 2개 필드는 어떤 Production 파일에도 authoritative 값이 없음 — 사람 확인 필요

WARNING:
1. Registry의 source_type=reference 값이 실제 획득 경로(archive.org 백업)와 맞지 않을 가능성(§3.2) — Registry 수정은 이번 작업 범위 밖, 별도 확인 필요
2. Registry 헤더 주석("citation_policy/tsu_access는 Manifest 책임")과 실제 ADR-019 Manifest Schema v1.0.0 사이 불일치 — 문서 정합성 확인 필요
3. (이월) NAE_C1_REVIEW_CONDITION_FOLLOWUP_002.md의 WARNING 2건(Verified 개념 문서화, TSU Pipeline 분리 ADR) 미해소

CURRENT SCHEMA:
Registry(authority/*.yaml) schema_version=1.0, Manifest(manifest/pilot/*, ADR-019) schema_version=1.0.0 — 이 둘이 실제 Production 데이터의 스키마. NAE TSU v3(tsu_schema_version="1")는 Governance §6 필드를 0/9 보유.

TARGET SCHEMA:
Governance §6의 9개 필드(source_id/author_id/work_id/edition_id/volume_id/category/publication_year/source_type/copyright_status/citation_policy/tsu_access) — 단, 이 필드들의 "정본 스키마 파일"이 계층 B(modern, 미사용)인지 계층 C(Registry+Manifest, 실사용)의 새 버전인지는 미확정(§6 옵션 1/2).

MIGRATION SCOPE:
NAE TSU v3 레코드 4,117건(Dagg 3,377 + Hiscox 740)에 최대 7개 필드 additive 추가(Crosswalk 경유 derive 가능) + 2개 필드(category/citation_policy)는 사람 확인 후 별도 patch. Registry/Manifest 자체는 수정 대상 아님(이미 값 보유, source_type 재확인 WARNING만 별도).

RECOMMENDED STRATEGY:
Additive Migration Script(방법 A) — TSU regeneration(방법 B) 대비 리스크·소요시간 압도적으로 낮고 "TSU 생성/재생성 금지" 원칙과도 충돌하지 않음. 실행은 별도 승인 대상.

PRODUCTION DATA CHANGE: NONE
CODE CHANGE: NONE

E2E READINESS: NOT READY

NEXT STEP:
1. (사람 승인 필요) schema_version 정책 옵션 1/2 결정
2. (사람 확인 필요) category/citation_policy 값 확정 방법 결정(Pilot 구버전 재사용 여부)
3. (사람 확인 필요) Registry source_type=reference → public_archive 재검토
4. 위 3건 결정 후 별도 Implementation Task(NAE-METADATA-SCHEMA-2.0.0-MIGRATION-001)로 Additive Migration Script 구현 발주
```
