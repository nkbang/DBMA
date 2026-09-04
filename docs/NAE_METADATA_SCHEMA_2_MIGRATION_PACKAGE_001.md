# NAE Metadata Schema 2.0.0 Migration — Pre-Implementation Package

**Project:** NAE-METADATA-SCHEMA-2.0.0-MIGRATION-PRE-PACKAGE-001
**작성일:** 2026-08-08
**성격:** C1 Architecture Review 제출용 최종 설계 패키지. **Migration 미실행.**
Production 데이터/코드 무수정, TSU 재생성/Embedding/Qdrant 전부 미실행.
**Authority:** `docs/NAE_METADATA_SCHEMA_2_DESIGN_REVIEW_001.md`(선행 Design Review, 승인 대기 3건 BLOCKER 포함)
**Git Commit/Push:** 미수행.

---

## 1. Field Provenance — 7개 안전 도출 필드

대상: 4,117건 전부(Dagg_Church_Order 3,377건 + Hiscox_Standard_Manual
740건). 두 identifier 모두 **manual-confirmed Crosswalk 레코드**로
100% 커버되므로(Design Review §5.1 실측 확인), 아래 provenance chain은
4,117건 전체에 동일하게 적용된다.

### 1.1 Provenance Chain(공통 구조)

```
TSU.identifier ("Dagg_Church_Order")
        │
        ▼  [1] Crosswalk lookup (NAE/metadata/crosswalk/crosswalk.yaml)
        │     WHERE target_identifier == TSU.identifier
        │       AND mapping_status IN {manual-confirmed, verified}
        │       AND confidence == high
        ▼
Crosswalk.source_identifier ("BAP-CHURCH-DAGG-001")
        │
        ▼  [2] Registry lookup (resources/theological_sources/authority/sources.yaml)
        │     WHERE source_id == Crosswalk.source_identifier
        ▼
Registry record { edition_id, volume_id, source_type, copyright_status,
                  usage_permission, access_control }
        │
        ▼  [3] Edition lookup (authority/editions.yaml)
        │     WHERE edition_id == Registry.edition_id
        ▼
Edition record { work_id, publication_year }
        │
        ▼  [4] Work lookup (authority/works.yaml)
        │     WHERE work_id == Edition.work_id
        ▼
Work record { author_id }
        │
        ▼  [5] tsu_access 산출 (Governance §6 조합표, 코드 규칙 — 조회 아님)
        ▼
tsu_access = f(copyright_status, usage_permission)
```

### 1.2 Dagg_Church_Order — 실측 Provenance(3,377건 전체 동일 적용)

| 필드 | 값 | Provenance(단계) |
|---|---|---|
| `source_id` | `BAP-CHURCH-DAGG-001` | Crosswalk `f914f6c442983e59`.`source_identifier` (mapping_status=`manual-confirmed`, confidence=`high`) — [1] |
| `author_id` | `dagg_john_l` | Registry.edition_id=`WORK-DAGG-CHURCH-ORDER-001-1871` → editions.yaml.work_id=`WORK-DAGG-CHURCH-ORDER-001` → works.yaml.author_id=`dagg_john_l` — [2]→[3]→[4] |
| `work_id` | `WORK-DAGG-CHURCH-ORDER-001` | editions.yaml[edition_id=`WORK-DAGG-CHURCH-ORDER-001-1871`].work_id — [2]→[3] |
| `edition_id` | `WORK-DAGG-CHURCH-ORDER-001-1871` | Registry.edition_id(직접) — [2] |
| `volume_id` | `null` | Registry.volume_id(직접, 단권 자료이므로 null이 정답) — [2] |
| `publication_year` | `1871` | editions.yaml[edition_id=`WORK-DAGG-CHURCH-ORDER-001-1871`].publication_year — [3] |
| `source_type` | `reference` | Registry.source_type(직접) — [2] **(§1.4 WARNING 참고 — 재검토 대상, 이번 패키지에서는 현재 값 그대로 사용)** |
| `copyright_status` | `public_domain` | Registry.copyright_status(직접) — [2] |
| `usage_permission` | `research` | Registry.usage_permission(직접) — [2] |
| `access_control` | `public` | Registry.access_control(직접) — [2] |
| `tsu_access` | `full` | Governance §6 조합표: `copyright_status=public_domain` → Full TSU — [5], 규칙: `if copyright_status=="public_domain": tsu_access="full"` |

### 1.3 Hiscox_Standard_Manual — 실측 Provenance(740건 전체 동일 적용)

| 필드 | 값 | Provenance |
|---|---|---|
| `source_id` | `BAP-CHURCH-HISCOX` | Crosswalk `260d31b2331a3f8b`.`source_identifier`(manual-confirmed, high) |
| `author_id` | `hiscox_edward_t` | Registry→Edition→Work FK 체인 |
| `work_id` | `WORK-HISCOX-STANDARD-MANUAL-001` | 동일 체인 |
| `edition_id` | `WORK-HISCOX-STANDARD-MANUAL-001-1890` | Registry 직접 |
| `volume_id` | `null` | Registry 직접(단권) |
| `publication_year` | `1890` | editions.yaml 직접 |
| `source_type` | `reference` | Registry 직접(§1.4 WARNING 동일 적용) |
| `copyright_status` | `public_domain` | Registry 직접 |
| `usage_permission` | `research` | Registry 직접 |
| `access_control` | `public` | Registry 직접 |
| `tsu_access` | `full` | 조합표 규칙 동일 |

### 1.4 명시적 조회 규칙(코드로 옮길 때의 정확한 로직)

```python
def resolve_metadata(tsu_identifier: str) -> dict | MigrationSkip:
    crosswalk_record = crosswalk_repo.find_by_target(tsu_identifier)
    if crosswalk_record is None:
        return MigrationSkip(reason="no crosswalk record")
    if crosswalk_record.mapping_status not in {"manual-confirmed", "verified"}:
        return MigrationSkip(reason=f"mapping_status={crosswalk_record.mapping_status} not eligible")
    if crosswalk_record.confidence != "high":
        return MigrationSkip(reason=f"confidence={crosswalk_record.confidence} not high")

    registry = registry_repo.find_by_source_id(crosswalk_record.source_identifier)
    if registry is None:
        return MigrationSkip(reason="no registry record")

    edition = edition_repo.find_by_edition_id(registry.edition_id)
    work = work_repo.find_by_work_id(edition.work_id) if edition else None

    return {
        "source_id": crosswalk_record.source_identifier,
        "author_id": work.author_id if work else None,
        "work_id": edition.work_id if edition else None,
        "edition_id": registry.edition_id,
        "volume_id": registry.volume_id,  # null 그대로 허용(단권)
        "publication_year": edition.publication_year if edition else None,
        "source_type": registry.source_type,
        "copyright_status": registry.copyright_status,
        "usage_permission": registry.usage_permission,
        "access_control": registry.access_control,
        "tsu_access": compute_tsu_access(registry.copyright_status, registry.usage_permission),
    }
```

**추측 없음 원칙**: 위 체인 중 어느 한 단계라도 레코드를 찾지 못하면
(`registry is None`, `edition is None` 등) 해당 TSU 레코드는 **전체
Migration에서 skip**되고 `MigrationSkip` 사유가 로그에 남는다 — 부분
필드만 채우거나 기본값으로 대체하지 않는다.

---

## 2. `category` / `citation_policy` — Authoritative Source 부재 명시

Design Review §3.1/§5.2에서 확인한 대로, 이 2개 필드는 **현재 어떤
Production authoritative 파일에도 값이 존재하지 않는다**:

```
authority/sources.yaml       — 헤더 주석으로 명시적 제외("이 Registry의 책임 아님")
manifest/pilot/*/manifest.yaml(ADR-019, schema_version 1.0.0) — 필드 자체가 스키마에 없음
authority/pilot/source_manifest.yaml — 값 존재하나 "승격 시 제외된 구버전 Pilot 산출물"
                                        (제외가 의도적 결정인지 단순 누락인지 문서상 불명확)
```

**Migration Script는 이 2개 필드를 다음과 같이 명시적으로 처리한다
(임의값 생성 금지)**:

```json
{
  "category": null,
  "category_status": "AUTHORITATIVE_SOURCE_MISSING",
  "citation_policy": null,
  "citation_policy_status": "AUTHORITATIVE_SOURCE_MISSING"
}
```

`_status` 보조 필드는 "이 필드가 비어있는 이유가 조회 실패가 아니라
설계상 정본 부재임"을 명시적으로 구분하기 위함이다(§4 불변성 검증에서
`null`과 `AUTHORITATIVE_SOURCE_MISSING`을 혼동하지 않도록). 사람이 값을
확정하면 별도 patch(§5 rollback 대상과 분리된 후속 단계)로 채운다 — 이
패키지가 제안하는 Migration Script 1회 실행 범위에는 포함하지 않는다.

---

## 3. Before / After Schema 예시(실제 레코드 기준)

### 3.1 Before(현재 Production 실측값, `TSU-0000006`)

```json
{
  "id": "TSU-0000006",
  "tsu_schema_version": "1",
  "book": "Church Order",
  "author": "John L. Dagg",
  "identifier": "Dagg_Church_Order",
  "source_identifier": "Dagg_Church_Order",
  "collector_version": "",
  "canonical_version": "2.0.0",
  "page": 8,
  "paragraph": 8,
  "sentence": 0,
  "source_text": "Se a That thou shouldst set in order the things that are wanting, and ordain elders in every city.—Tırus i. 5.",
  "claim": "교회에서 부족한 것을 정돈하고 각 도시마다 장로를 임명해야 한다.",
  "doctrine": "Ecclesiology",
  "scriptures": [],
  "citations": [],
  "confidence": 0.8,
  "extraction_method": "llm",
  "review_status": "generated",
  "model": "my-theology-bot-v2:latest"
}
```

### 3.2 After(Additive Migration 적용 후 — 설계안, 미실행)

```json
{
  "id": "TSU-0000006",
  "tsu_schema_version": "1",
  "book": "Church Order",
  "author": "John L. Dagg",
  "identifier": "Dagg_Church_Order",
  "source_identifier": "Dagg_Church_Order",
  "collector_version": "",
  "canonical_version": "2.0.0",
  "page": 8,
  "paragraph": 8,
  "sentence": 0,
  "source_text": "Se a That thou shouldst set in order the things that are wanting, and ordain elders in every city.—Tırus i. 5.",
  "claim": "교회에서 부족한 것을 정돈하고 각 도시마다 장로를 임명해야 한다.",
  "doctrine": "Ecclesiology",
  "scriptures": [],
  "citations": [],
  "confidence": 0.8,
  "extraction_method": "llm",
  "review_status": "generated",
  "model": "my-theology-bot-v2:latest",

  "metadata_schema_version": "1.1.0",
  "source_id": "BAP-CHURCH-DAGG-001",
  "author_id": "dagg_john_l",
  "work_id": "WORK-DAGG-CHURCH-ORDER-001",
  "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
  "volume_id": null,
  "publication_year": 1871,
  "source_type": "reference",
  "copyright_status": "public_domain",
  "usage_permission": "research",
  "access_control": "public",
  "tsu_access": "full",
  "category": null,
  "category_status": "AUTHORITATIVE_SOURCE_MISSING",
  "citation_policy": null,
  "citation_policy_status": "AUTHORITATIVE_SOURCE_MISSING",
  "metadata_provenance": {
    "crosswalk_id": "f914f6c442983e59",
    "resolved_at": "<migration 실행 시각, ISO8601>",
    "resolver_version": "<migration script version>"
  }
}
```

**변경 요약**: 기존 19개 필드는 **1글자도 변경되지 않는다**(§4에서
검증 규칙 정의). 신규 필드는 12개(`metadata_schema_version` 포함,
`_status` 보조 필드 2개 포함) 추가만 이루어진다. `metadata_schema_version="1.1.0"`은
C1 Final Review(`NAE_METADATA_SCHEMA_2_MIGRATION_FINAL_REVIEW_001.md`
§10 R-A1 권장안 1)에 따라 확정된 값이다 — Design Review §6의 "옵션
2"(계층 C 독립 Minor bump)를 채택, `NAE_METADATA_GOVERNANCE_v1.md`
§2.2 Minor 규칙(필드 추가, 기존 데이터 무효화 없음)을 준수한다. 이
버전이 지칭하는 대상은 계층 B(Modern, `2.1.0`)가 아니라 **계층
C(Authority Registry + Manifest Pilot, 실사용 Production 데이터)의
독자적 버전 축**이다(§6.3 Governance 문서 개정 참고).

---

## 4. 불변성(Invariant) 조건 — 기존 필드 무변경 검증

Migration Script는 아래 조건을 **자체 검증(self-check)** 하고, 하나라도
위반하면 해당 레코드 갱신을 커밋하지 않는다(all-or-nothing per record).

```python
IMMUTABLE_FIELDS = [
    "id", "tsu_schema_version", "book", "author", "identifier",
    "source_identifier", "collector_version", "canonical_version",
    "page", "paragraph", "sentence", "source_text",
    "claim", "doctrine", "scriptures", "citations",
    "confidence", "extraction_method", "review_status", "model",
]

def verify_invariant(before: dict, after: dict) -> None:
    for field in IMMUTABLE_FIELDS:
        assert before.get(field) == after.get(field), (
            f"INVARIANT VIOLATION: {field} changed "
            f"({before.get(field)!r} -> {after.get(field)!r})"
        )
    # 신규 필드는 반드시 추가(add)만 — 기존 키 삭제 금지
    assert set(before.keys()) <= set(after.keys()), "INVARIANT VIOLATION: existing key removed"
```

**특히 `review_status`/`claim`/`doctrine`/`evidence`(스키마상 `citations`/
`scriptures`가 evidence 역할) — 이 4개는 C1 Review와 Review Gate의 핵심
계약이므로 별도로 재확인한다**:

```
review_status: Migration 전후 100% 동일해야 함 — Migration은 review
                lifecycle(generated→reviewed→verified→rejected)에
                절대 관여하지 않는다(review_promotion.py만이 이 필드를
                변경할 권한을 가짐 — 기존 설계 그대로 유지).
claim/doctrine: 원본 LLM 추출 결과, Migration이 재계산하거나
                덮어쓰지 않는다.
scriptures/citations: 원본 evidence 배열, Migration이 건드리지 않는다.
```

Migration Script 실행 후 배치 레벨 검증:

```
$ diff <(jq -S 'map({id,claim,doctrine,scriptures,citations,confidence,
    extraction_method,review_status,model,source_text,page,paragraph,
    sentence,book,author,identifier,source_identifier,collector_version,
    canonical_version,tsu_schema_version})' tsu.json.before) \
       <(jq -S 'map({id,claim,doctrine,scriptures,citations,confidence,
    extraction_method,review_status,model,source_text,page,paragraph,
    sentence,book,author,identifier,source_identifier,collector_version,
    canonical_version,tsu_schema_version})' tsu.json.after)
(빈 출력이어야 함 — 19개 기존 필드 부분집합이 byte-identical)
```

---

## 5. Idempotency 및 Rollback 요구사항

### 5.1 Idempotency

```
요구사항: Migration Script를 동일 입력에 N번 실행해도 결과가 1번 실행한
결과와 동일해야 한다(N-1번의 재실행이 필드를 중복 추가하거나 값을
누적/변형하지 않음).

구현 규칙:
1. 이미 metadata_provenance 필드가 존재하는 레코드는 기본적으로 skip
   (재실행 시 덮어쓰기는 --force 플래그로만 허용, 기본값 아님)
2. --force 재실행 시에도 §4 불변성 검증을 동일하게 통과해야 함
3. Crosswalk/Registry/Edition/Work 조회 결과가 Migration 최초 실행과
   재실행 사이에 바뀌지 않았다면(이번 작업 범위에서는 Registry/Manifest
   자체를 수정하지 않으므로 항상 동일), 산출 필드값도 항상 동일해야 함
   (순수 함수적 조회 — 난수/타임스탬프 등 비결정적 요소는
   metadata_provenance.resolved_at 한 곳으로만 격리)
```

### 5.2 Rollback

```
요구사항: Migration 실행 직전 자동 백업, 실패/이상 발견 시 즉시 원상복구
가능해야 한다(이번 Recovery 작업(NAE-TSU-BUILDER-EXECUTION-RECOVERY-001)
에서 이미 사용한 방식과 동일한 패턴 — NAE/corpus/tsu/_backup_<timestamp>/).

절차:
1. 실행 직전: NAE/corpus/tsu/{identifier}/tsu.json 전체를
   NAE/corpus/tsu/_migration_backup_<timestamp>/{identifier}/tsu.json으로 복사
2. Migration은 원본을 직접 in-place 수정하지 않고, 임시 파일에 먼저
   쓴 뒤(§4 불변성 검증 통과 확인 후) 원자적 rename(os.replace)으로 교체
   (쓰기 중간 상태에서 프로세스가 죽어도 원본이 손상되지 않도록 —
   이전 Execution Recovery 사고(중간 종료)의 교훈을 반영)
3. Rollback 명령: 단순 파일 복사(백업 → 원본 경로) — 코드 로직 불필요,
   Migration Script와 독립적으로 항상 가능
4. Rollback 후 검증: §4 불변성 검증 스크립트를 롤백된 파일에도 실행해
   원본과 100% 일치하는지 재확인
```

---

## 6. 4,117건 전체 적용 시 예상 변경 범위 및 검증 방법

### 6.1 예상 변경 범위

```
대상 레코드: 4,117건(Dagg 3,377 + Hiscox 740)
Crosswalk 커버리지: 100%(4,117/4,117 — 두 identifier 모두 manual-confirmed 존재, 실측 확인)
예상 skip 건수: 0건(모든 레코드가 §1.4 조회 체인을 끝까지 통과할 것으로
                 예상 — Dagg/Hiscox 둘 다 Registry→Edition→Work 체인이
                 이미 실측으로 완전함을 확인함, §1.2/§1.3)
추가 필드 수(레코드당): 10개 값 필드 + 2개 status 보조 필드
                         (category/citation_policy) + 1개 provenance 객체 = 13개 키
전체 추가 필드 개수: 4,117 × 13 ≈ 53,521개 키
기존 필드 변경: 0건(§4 불변성 검증으로 보증)
파일 크기 증가 예상: 레코드당 약 400~600 byte 증가(provenance 객체 포함) ×
                      4,117 ≈ 1.6~2.5MB 증가(Dagg tsu.json 현재 2.9MB → 약 4.5~5.4MB 예상)
```

### 6.2 검증 방법(실행 시점에 반드시 수행)

```
1. 사전: NAE_METADATA_SCHEMA_2_DESIGN_REVIEW_001.md §9 Gate 8종 전체 재확인
2. 레코드 수 불변: len(tsu.json) before == after (4,117 유지)
3. §4 불변성 검증 스크립트: 4,117건 전체 PASS
4. Crosswalk 커버리지 재확인: skip 건수가 사전 예상(0건)과 다르면 즉시
   중단하고 원인 보고(예상 밖 skip은 Registry/Crosswalk 변경 등 외부
   요인을 의심해야 함 — 이번 Recovery 작업 중 실제로 발생했던 "예상치
   못한 외부 파일 변경" 사례(TSU 파일이 알 수 없이 비었던 사고)를
   교훈 삼아, 이상 발견 시 자동 계속 진행하지 않고 즉시 정지)
5. Review Gate 재검증: index_all(dry_run=True) 결과가 Migration 전후
   동일해야 함(indexed=0 유지 — review_status는 여전히 전부 generated)
6. Regression: tests/test_nae_tsu_builder.py, test_tsu_review_gate.py,
   test_indexer_review_gate_wiring.py, test_crosswalk*.py,
   test_manual_crosswalk_pilot.py 전체 재실행, 감소 없음 확인
7. Validator Drift: source/manifest/authority validator 3종 baseline과
   동일(89/0/0, 138/0/0, 128/26/0) — Migration이 Registry/Manifest를
   읽기만 하고 쓰지 않으므로 값 변화가 없어야 정상
```

---

## 7. 절대 금지 사항 재확인(이번 패키지 작성 중 준수)

```
Production 데이터 변경:      수행 안 함(실제 tsu.json 파일 무수정)
TSU 재생성:                   수행 안 함(builder.py 미실행)
Embedding 실행:                수행 안 함
Qdrant 실행:                   수행 안 함
Registry/Manifest/Crosswalk 수정: 수행 안 함(읽기 전용 조회만)
core/retrieval.py, core/tsu_builder.py: 무관/무수정
Git commit/push:               수행 안 함
```

---

## 8. C1 Review를 위한 요약 체크리스트

```
[ ] §1 Provenance Chain의 5단계 조회 로직이 Architecture Boundary(Crosswalk/Registry read-only)와 합치하는가
[ ] §2 category/citation_policy의 "AUTHORITATIVE_SOURCE_MISSING" 처리 방식이 "추측 금지" 원칙에 충분히 부합하는가
[ ] §3 Before/After 예시에서 기존 19개 필드가 정말 1개도 안 바뀌었는지 재검증
[ ] §4 불변성 검증 로직이 review_status/claim/doctrine/evidence 보호에 충분한가
[ ] §5 Idempotency/Rollback 설계가 실제 구현 승인 조건으로 충분한가
[ ] §6 예상 skip 0건 가정이 실제 실행 시에도 유지될지, 아니면 조건부 재검토가 필요한지
[x] metadata_schema_version="1.1.0" 확정(C1 Final Review R-A1 권장안 1 채택, NAE-METADATA-SCHEMA-2.0.0-MIGRATION-IMPLEMENTATION-001에서 해제)
```

---

## 완료 보고

```
STATUS: PASS(패키지 준비 완료, C1 제출 가능) / Migration 자체는 미실행

FILES CREATED:
docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md

FILES MODIFIED:
(없음)

PRODUCTION DATA CHANGE: NONE
TSU REGENERATION: NOT EXECUTED
EMBEDDING: NOT EXECUTED
QDRANT: NOT EXECUTED
REGISTRY/MANIFEST/CROSSWALK MODIFICATION: NONE

PROVENANCE COVERAGE:
4,117/4,117(100%) — Dagg 3,377 + Hiscox 740, 둘 다 manual-confirmed Crosswalk로 커버

UNRESOLVED FIELDS(추측 없이 보류):
category, citation_policy — AUTHORITATIVE_SOURCE_MISSING으로 명시 처리, 사람 확인 후 별도 patch

NEXT STEP:
C1 Architecture Review 제출 → 승인 시 별도 Implementation Task(NAE-METADATA-SCHEMA-2.0.0-MIGRATION-001)로 Migration Script 실제 구현 발주. 승인 전까지 실행하지 않음.

GIT:
NOT PERFORMED
```
