# NAE Schema v2.2.0 Version Decision 001

작성일: 2026-08-02
Project: NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 Phase 1-2
성격: **결정 문서 — schema 파일 실제 수정 없음**
근거: [ADR-018](architecture/ADR-018-NAE-Periodical-Authority-Extension.md),
[ADR-019](architecture/ADR-019-NAE-Corpus-Manifest-Layer.md),
[`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §2.2

---

## Phase 1. v2.1.0 → v2.2.0 변경 분석

대상: `resources/theological_sources/modern/source_manifest.schema.yaml`
(corpus manifest 스키마, Registry/Manifest와는 별도 트랙 — 아래 §Manifest
Schema 관계 참고).

| 필드 | 소속 Entity | Category | 근거 |
|---|---|---|---|
| `author_type` | Author | **Optional**(기본값 `person`) | ADR-018 — 기존 Author entry는 전부 사람이었으므로, 값이 없으면 `person`으로 간주해도 데이터 훼손 없음. 신규 등록 시 조직이면 명시적으로 `organization` 지정 |
| `editor_id` | Work | **Optional** | ADR-018 — 정기간행물 중 편집자가 별도로 확인된 경우만 사용, 대부분 자료(monograph 전체, 편집자 미상 periodical)는 비워둠 |
| `issue_id` | Source(또는 Manifest, §Phase3 참고) | **Conditional** | ADR-018/019 — monograph에서는 forbidden, periodical에서는 required(아래 표) |
| `title_history` | Work | **Optional** | ADR-018 — periodical에서만 유의미(monograph는 기존 `aliases` 계속 사용), 필드 자체는 모든 Work에 열어두되 값 없으면 무시 |
| `continues_work_id` | Work | **Optional** | ADR-018 — 계승 관계가 서지적으로 확인된 극소수 자료만(현재 0건, Title History Validation-001의 향후 적용안만 존재) |
| `continued_by_work_id` | Work | **Optional** | 동일 |
| `manifest_id` | **신규 계층(ADR-019, Manifest Entry)** | Required(그 계층 내에서) | corpus manifest 스키마 자체의 필드가 아님 — 별도 Manifest Schema에 속함(§Phase3) |
| `processing_status` | **신규 계층(ADR-019, Manifest Entry)** | Required(그 계층 내에서) | 동일 |

**핵심 구분**: `manifest_id`/`processing_status`는 corpus manifest
(`modern/source_manifest.schema.yaml`, v2.x)의 필드가 아니라 ADR-019가
정의한 **별도 Manifest Schema**(자체 버전 트랙)에 속한다 — 이 둘을
같은 스키마 파일에 섞지 않는다(§Phase3에서 상세, Manifest Schema는
corpus manifest와 독립적으로 버전 관리).

---

## Phase 2. Schema Version 판정

### 판정: **Minor 증가(v2.1.0 → v2.2.0) 적절**

| 검토 항목 | 결과 |
|---|---|
| Required field 증가 여부(corpus manifest 자체) | **없음** — `author_type`/`editor_id`/`issue_id`/`title_history`/`continues_work_id`/`continued_by_work_id` 전부 Optional 또는 Conditional(자료 유형에 따라서만 required) |
| 기존 데이터 무효화 여부 | **없음** — v2.1.0으로 이미 등록된 Pilot-001/002 manifest entry(Dagg/Hiscox/Fuller)는 신규 필드가 전부 비어 있어도 그대로 유효 |
| Backward Compatibility | **완전 호환** — v2.1.0 검증 로직(source_validator.py의 v2 분기)이 신규 optional 필드를 인식하지 못해도 기존 required 필드 검사에는 영향 없음(신규 필드는 검증 대상에 추가되지 않는 한 존재 여부와 무관하게 통과) |

GOVERNANCE §2.2 SemVer 원칙(필드 추가 = Minor)과 완전히 일치 — Major
bump(구조 변경/필드 제거/의미 변경)에 해당하는 변경이 없다.

**결론**: `schema_version: "2.2.0"`. **이번 문서에서 실제 스키마 파일은
수정하지 않았다.**
