# NAE Schema Migration Guide v2.2 — 001

작성일: 2026-08-02
Project: NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 Phase 6
성격: **로드맵 문서 — 실행 없음**, 각 Phase는 별도 승인 후 착수
근거: [`NAE_SCHEMA_MIGRATION_GUIDE_v1.md`](NAE_SCHEMA_MIGRATION_GUIDE_v1.md)(2.0.0→2.1.0 가이드),
[`NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md`](NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md)

이 문서는 기존 `NAE_SCHEMA_MIGRATION_GUIDE_v1.md`를 대체하지 않는다
(그 문서는 2.0.0→2.1.0 전환을 다룸, 원문 보존) — 이번 문서는 v2.2.0
전환 + Manifest Layer 도입을 함께 다루는 **신규 로드맵**이다.

---

## 로드맵

```
Phase 0   Design                (이번 작업 — Schema v2.2.0 + Manifest Schema 설계)
Phase 1   Schema Apply            (source_manifest.schema.yaml 실제 v2.2.0 반영)
Phase 2   Manifest Pilot          (Monograph 먼저, Periodical 다음 — 기존 Pilot 확대 원칙 재사용)
Phase 3   Validator               (manifest_validator.py 구현)
Phase 4   TSU Connection           (processing_status=TSU_ELIGIBLE 게이트 연결)
```

---

## Phase 0 — Design (완료, 이번 작업)

산출물: `NAE_SCHEMA_V2_2_VERSION_DECISION_001.md`,
`NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md`,
`NAE_VALIDATOR_BOUNDARY_DESIGN_001.md`, 본 문서,
`NAE_SCHEMA_V2_2_IMPLEMENTATION_DESIGN_REPORT_001.md`. **코드/스키마
파일 변경 없음.**

## Phase 1 — Schema Apply (다음 단계, 별도 승인)

- `resources/theological_sources/modern/source_manifest.schema.yaml`에
  `author_type`/`editor_id`/`issue_id`/`title_history`/
  `continues_work_id`/`continued_by_work_id` 6개 필드 실제 추가,
  `schema_version: "2.2.0"`로 갱신.
- Manifest Schema(별도 트랙, `schema_version: "1.0.0"`)를 실제 YAML
  스키마 파일로 작성 — 위치는 이 Phase 착수 시 결정(후보:
  `resources/theological_sources/manifest/manifest.schema.yaml`).
- **회귀 요구사항**: 기존 v2.1.0 Pilot manifest(Dagg/Hiscox/Fuller,
  10건)가 이 변경 후에도 동일하게 검증 통과해야 함(Backward
  Compatibility, Version Decision-001 §Phase2에서 이미 확인된 이론적
  근거의 실증 확인).

## Phase 2 — Manifest Pilot

- **Monograph 먼저**: Pilot-001/002(10건)에 실제 Manifest Entry 생성,
  `processing_status`를 `RAW_ACQUIRED`부터 시작해 `VALIDATED`까지
  진행.
- **Periodical 다음**: Baptist Missionary Magazine Pilot에 Manifest
  Entry 신설(Periodical Condition Resolution Report-001 §4에서 발견된
  "corpus manifest 계층 자체 부재" gap을 여기서 실제로 메움).
- 순서 근거: 이미 검증된 절차(monograph)로 리스크를 먼저 줄인 뒤
  새로운 유형(periodical)에 적용 — Authority Registry Design v1 §4.2
  "소규모 우선" 원칙과 동일.

## Phase 3 — Validator

- `scripts/manifest_validator.py` 구현(Validator Boundary Design-001
  §3 책임 범위 그대로).
- 회귀 테스트: 기존 `source_validator.py`/`authority_validator.py`
  결과에 영향 없어야 함.

## Phase 4 — TSU Connection

- `processing_status=TSU_ELIGIBLE`인 Manifest Entry만 TSU 빌더 입력
  으로 연결.
- **전제조건**: Phase 3 완료, 최소 1건 이상 실제 데이터로 전체
  파이프라인(Manifest Entry 생성 → 상태 전이 → TSU_ELIGIBLE 판정)이
  성공적으로 동작함을 확인.

---

## 이전 로드맵과의 관계

`NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md`(Phase 0~5, Monograph/
Periodical Pilot을 별도 Phase로 나눔)와 이번 문서(Phase 0~4, 두
Pilot을 Phase 2 하나로 통합 서술)는 **내용상 동일한 계획을 다른
세분화 수준으로 표현**한 것이다 — 이번 문서가 상위 로드맵,
`NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md`의 Phase 2/3가 이번 문서
Phase 2의 세부 실행 순서로 대응한다. 두 문서 모두 유지하며 어느
쪽도 소급 수정하지 않는다.
