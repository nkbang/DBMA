# NAE Identifier Crosswalk Schema 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 2
**작성일:** 2026-08-05
**성격:** Design Only — 신규 Layer 스키마 설계, 코드 작성 없음.

---

## 1. 설계 전제

`NAE_IDENTIFIER_INVENTORY_002.md` §5의 실측 결과: Authority↔Manifest는
이미 1:1로 연결되어 있고, **Manifest↔Corpus/TSU 구간만 끊어져 있다.**
따라서 Crosswalk Layer는 정확히 이 구간, 즉 **Manifest `source_id`
(=Registry Source의 기존 FK 문자열) → Corpus/TSU `identifier`** 방향
1개만 담당하면 된다 — Authority↔Manifest 사이에 별도 Crosswalk을
추가하지 않는다(이미 잘 연결된 것을 건드리지 않는다, Architecture
Freeze Rule과 같은 정신).

---

## 2. Crosswalk Record 스키마

```yaml
crosswalk_id: string        # 필수. 결정적 생성 권장(예: sha256(source_identifier+target_identifier)[:16])
source_identifier: string   # 필수. Manifest/Registry의 source_id(예: BAP-CHURCH-DAGG-001)
source_type: string         # 필수. enum: "registry_source_id"(현재 유일한 값 — 향후 확장 가능)
target_identifier: string   # 필수. Corpus/TSU identifier(예: PBC1742)
target_type: string         # 필수. enum: "corpus_canonical_id" | "corpus_raw_id"
mapping_status: string      # 필수. enum: "verified" | "evidence-backed" | "manual-confirmed" | "unmapped"
confidence: string          # 필수. enum: "high" | "medium" | "low" — mapping_status="unmapped"면 값 없음(null)
evidence: string            # 필수(unmapped 제외). 근거 서술 — 예: "archive.org item page 제목/저자 대조", "RAW PDF 파일명·페이지수 일치 확인"
created_at: string          # 필수. ISO 8601
verified_at: string | null  # 선택. 사람 검증 완료 시각(자동 생성 시점과 구분)
```

### 필드별 설계 근거

- **`crosswalk_id`**: Migration Engine의 `compute_migration_unit_id`와
  동일한 결정적 해시 원칙을 재사용(우연/타임스탬프 기반 ID 금지) —
  이 Crosswalk이 향후 Migration Engine 스타일의 Adapter로 소비될
  가능성을 열어둔다(구현은 이번 범위 밖).
- **`source_type`/`target_type`을 분리한 이유**: 지금은
  `registry_source_id` → `corpus_canonical_id` 방향 하나뿐이지만,
  Inventory §2에서 확인했듯 `NAE/corpus/raw/archive_org/`(raw id)와
  `NAE/corpus/canonical/`(canonical id)가 이미 다른 값 체계일 수
  있음이 드러났다(현재는 우연히 `PBC1742`가 raw/canonical 양쪽에
  같은 이름으로 존재하지만, 이것이 규칙이라는 보장이 없다) — 향후
  `corpus_raw_id`도 별도로 다뤄야 할 가능성에 대비해 type을 명시적
  필드로 분리했다.
- **`mapping_status`/`confidence`/`evidence`를 3중으로 둔 이유**:
  Phase 3 Rule 3(추측 Mapping 금지)을 스키마 레벨에서 강제하기
  위함 — `evidence` 필드가 비어 있으면 그 자체로 이 Crosswalk이
  아직 신뢰할 수 없는 상태임을 기계적으로 판별 가능하게 한다.
- **`verified_at`을 `created_at`과 분리한 이유**: 자동/반자동으로
  Crosswalk 후보가 먼저 생성되고, 사람이 나중에 검증하는 2단계
  워크플로우를 지원하기 위함(Rule 3의 "manual-confirmed" 상태와
  대응).

---

## 3. 저장 위치(제안, 미확정)

이번 설계는 저장 위치를 **확정하지 않는다** — Phase 4에서 ADR-019
범위 해당 여부를 먼저 검토해야 하기 때문이다. 후보만 기록:

| 후보 | 장점 | 단점 |
|---|---|---|
| Manifest entry에 필드 추가(`crosswalk_id`, `target_identifier` 등) | Manifest가 이미 Source 1:1 단위이므로 자연스러움 | ADR-019가 정의한 Manifest 필드 집합을 확장해야 함(ADR 영향, §Phase4) |
| 별도 파일(`resources/theological_sources/crosswalk/*.yaml`) | Manifest 스키마를 안 건드림 | 새로운 파일 종류 도입 — 이것도 광의로는 ADR-019 범위 확장(신규 파일 유형) |
| Registry Source entity에 필드 추가 | Registry가 이미 `canonical_id`/`legacy_id` 확장 전례가 있음(ADR-017 Option B) | Registry는 Corpus/TSU를 몰라야 한다는 기존 계층 분리 원칙(Migration Engine이 Adapter로 도메인을 분리한 것과 동일 정신)과 충돌 소지 |

**권고(비확정)**: 별도 파일 방식이 기존 두 계층(Registry/Manifest)의
책임 경계를 가장 덜 건드린다 — 그러나 이는 권고일 뿐, Phase 4 ADR
영향 분석 결과에 따라 최종 결정한다.
