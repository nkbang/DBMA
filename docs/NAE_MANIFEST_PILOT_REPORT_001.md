# NAE Manifest Pilot Report 001

**Project:** NAE-MANIFEST-PILOT-IMPLEMENTATION-001
**Date:** 2026-08-03
**Nature:** Manifest Layer 실제 Pilot 데이터 — 전체 Corpus Migration 아님
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

Manifest Schema v1.0.0(`NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md`)을
Primary Pilot(Fuller, 8 volume·2 edition)과 Secondary Pilot(Dagg/
Hiscox, monograph 2건)에 실제 적용해 총 10개 Manifest Entry를
생성했다. Production Authority Registry(`authority/*.yaml`)를 참조한
Reference Integrity 검증 10/10 PASS(Python 스크립트 실행, 추론 아님).
Lifecycle은 지시된 초기값(acquired/complete/validated/pending/pending)
그대로 적용했고 TSU/Embedding 완료 처리는 하지 않았다. **Optional
Third(Baptist Missionary Magazine)는 지시대로 이번 단계에서 생략**했다.

Phase 5(Validator v2.2 실행)에서 **구조적 발견**이 있었다 — Manifest
Layer 파일(Phase 1이 지시한 별도 `manifest.yaml`, `manifests:` 키
구조)은 `source_validator.py`가 애초에 탐색하지 않는 파일명·구조라
"Pilot Manifest: PASS"를 이 도구로 직접 재현할 수 없었다. 이는 버그가
아니라 Registry/Manifest/Corpus-manifest 3계층 분리 설계(ADR-019,
Validator Boundary Design-001)의 **의도된 결과**이지만, 이번 명령서의
Phase5 기대치와는 어긋난다 — §7 Risk #1에서 상세.

---

## 2. Pilot Dataset

| Type | Count(Work) | Count(Manifest Entry) |
|---|---|---|
| Monograph | 2(Dagg, Hiscox) | 2 |
| Multi-volume | 1(Fuller — 2 edition, 8 volume) | 8 |
| Periodical(optional) | 0(생략) | 0 |
| **합계** | **3** | **10** |

생성 위치: `resources/theological_sources/manifest/pilot/{dagg,hiscox,fuller}/manifest.yaml`
(Pilot namespace, Phase 1 지시대로 실제 운영 구조 확정 아님).

---

## 3. Schema Validation

각 Manifest Entry는 Manifest Schema v1.0.0의 Identity(`manifest_id`/
`source_id`/`schema_version`) + Authority Reference(`author_id`/
`work_id`/`edition_id`/`volume_id`/`issue_id`) + Lifecycle(5개 필드) +
Audit(`created_at`/`updated_at`/`verified_by`) 전체 필드를 채웠다.

**monograph 조건 적용**(Dagg/Hiscox): `edition_id` 필수 존재,
`volume_id`/`issue_id` = null(Phase 2 조건과 일치 — "edition_id
required, volume_id optional, issue_id forbidden"에서 volume_id는
값 없이도 조건 위반 아님).

**multi_volume 조건 적용**(Fuller 8건): `edition_id`/`volume_id`
전부 존재, `issue_id` = null(forbidden 규칙 준수).

---

## 4. Reference Integrity

실제 Python 스크립트 실행 결과(Production
`authority/{authors,works,editions,volumes,sources}.yaml` 대조,
10개 Manifest Entry × 참조 필드):

```
REFERENCE: PASS
total manifests checked: 10
```

세부: `author_id→authors.yaml` 10/10, `work_id→works.yaml` 10/10,
`edition_id→editions.yaml` 10/10, `volume_id→volumes.yaml`(값이 있는
8건만 해당) 8/8, `source_id→sources.yaml` 10/10 — **전부 PASS,
FAIL 없음**.

---

## 5. Validator Result

### 회귀 확인(기존 corpus manifest, 영향 없음 확인)

```
--root resources/theological_sources                 : 89 PASS / 0 WARNING / 0 FAIL (불변)
--root resources/theological_sources/baptist           : 21 PASS / 0 WARNING / 0 FAIL (불변, v1.2 격리)
```

### Pilot Manifest 직접 검증 시도(구조적 한계 확인)

```
--root resources/theological_sources/manifest         : 0 PASS / 1 WARNING / 0 FAIL
  → "source_manifest.yaml 없음 — 검사할 대상 없음"
```

**원인**: `source_validator.py`(`MANIFEST_FILENAME =
"source_manifest.yaml"`, `find_manifests()`가 이 파일명만 `rglob`)는
Manifest Layer 전용 파일(`manifest.yaml`, 최상위 키 `manifests:`)을
설계상 대상으로 삼지 않는다 — Manifest 필드 검증(Phase 7, opt-in)은
"corpus manifest entry 안에 `manifest_id`가 있을 때"만 작동하도록
구현되어 있다(NAE-VALIDATOR-V2.2-IMPLEMENTATION-001). 즉 지금 구조로는
Manifest Layer 데이터를 **corpus manifest entry에 병합해야만**
Validator가 검사할 수 있다. 이번 Pilot은 (a) Registry/Manifest/
Corpus-manifest 3계층 분리를 유지하는 것과 (b) `source_validator.py`를
추가 수정하지 않는 것(금지 사항) 둘 다를 지키기 위해, **병합하지
않고 이 한계를 그대로 기록**하는 쪽을 택했다.

**판정**: Validator v2.2 자체는 기존 회귀 기준 그대로 PASS(89/21
불변). Manifest Pilot 데이터에 대한 "Validator PASS"는 이 도구로
직접 재현되지 않았다 — Reference Integrity(§4)가 사실상 그 역할을
대신했다.

---

## 6. Lifecycle Evaluation

10개 Manifest Entry 전부 아래 초기값으로 생성(지시된 값 그대로):

```
acquisition_status: acquired
ocr_status: complete
metadata_status: validated
tsu_status: pending
embedding_status: pending
```

Phase6 지시대로 `acquired → ocr_complete → metadata_complete →
tsu_ready`까지의 진행은 **개념적으로 표현 가능함을 확인**했다(5개
필드 조합이 이 4단계 요약과 매핑됨, 실제로는 `metadata_status:
validated`까지 도달한 상태를 요약 `processing_status: metadata_complete`
값으로 파생 기록 — Manifest Schema Design v1 §Phase6 매핑 원리 재사용).
**embedding 완료 처리·TSU 완료 처리는 지시대로 수행하지 않았다**
(`tsu_status`/`embedding_status` 둘 다 `pending` 유지).

`manifest_id` 명명 규칙: 이번 명령서 예시
(`dagg_standard_manual_1890_manifest`류 서술형 슬러그)를 따르지 않고
**ADR-019가 이미 확정한 `manifest_id = source_id` 규칙을 그대로
유지**했다 — 서술형 슬러그로 바꾸면 이미 검증된 설계 결정을 이번
Pilot에서 조용히 뒤집는 셈이 되어, 명시적 재검토 없이는 변경하지
않는 편을 택했다(§7 Risk #1).

---

## 7. Remaining Risks

| # | 리스크 | 설명 |
|---|---|---|
| 1 | **Manifest ID 규칙과 파일 구조의 불일치** | (a) 이번 명령서 예시(서술형 슬러그)와 ADR-019 결정(`=source_id`) 중 ADR-019를 따름 — 재확인 필요. (b) Manifest Layer 파일 구조(`manifest.yaml`/`manifests:`)가 `source_validator.py`의 탐색 대상이 아니라서 Validator 통합 경로가 아직 없음(§5) |
| 2 | Source↔Manifest 1:1 적합성 | 10건 전부 1:1로 정상 구현됨 — 위반 사례 없음. 단, 재스캔(Different Scan) 시나리오는 이번 Pilot 표본에 없어 1:1 원칙이 그 상황에서도 유지되는지 미검증 |
| 3 | Multi-volume 처리 문제 | Fuller의 두 Edition(Charlestown/New Haven) 각각에 속한 volume들이 Manifest에서도 정확히 구분됨(edition_id 값이 volume별로 다름, §3) — 문제 없음 확인 |
| 4 | **Periodical 확장 필요 여부** | 이번 Pilot은 Baptist Missionary Magazine을 생략했으므로 `issue_id`가 실제 값으로 채워진 Manifest Entry가 하나도 없다 — periodical 조건부 규칙(§Phase2)이 코드 레벨(Validator v2.2)에서는 이미 테스트됐지만, Manifest Layer 데이터로는 이번 단계에서 검증되지 않음(별도 승인 필요, 명령서 지시와 일치) |
| 5 | Lifecycle 역행 검사 미구현 | 의도된 범위 제한(Phase 6 지시) — 실제 lifecycle enforcement는 여전히 미구현 |
| 6 | `manifest/schema/` 디렉토리에 실제 schema.yaml 미생성 | Phase 1 구조 예시에 `schema/` 폴더가 있었으나, 기존 설계 문서(Manifest Schema Design v1/v2.2)와의 정본 중복을 피하기 위해 README만 두고 실제 스키마 파일은 만들지 않음(판단 근거는 해당 README에 기록) |

---

## 8. Migration Readiness

**BLOCKED.** Manifest Pilot 성공이 Corpus-wide Migration 승인을
의미하지 않는다(명령서 "최종 판정 기준" 재확인). Risk #1(Validator
통합 경로 부재)이 특히 Migration 전 해결이 필요한 항목이다 —
Manifest Layer 데이터가 실제로 자동 검증되지 않는 상태로는 규모를
키울 수 없다.

---

## 완료 조건 답변

1. **Manifest Schema v1.0.0 적용 성공 여부?** — 성공(10개 Entry, 전체 필드 채움).
2. **Dagg/Hiscox Manifest 생성 여부?** — 생성됨(2건).
3. **Fuller 8 Volume Manifest 생성 여부?** — 생성됨(8건, 2 Edition 정확히 구분).
4. **Authority Registry Reference PASS 여부?** — **PASS**(10/10, §4).
5. **Validator v2.2 PASS 여부?** — 회귀 기준(89/21)은 PASS. Manifest 데이터 직접 검증은 구조적으로 불가(§5, Risk #1).
6. **Lifecycle 모델 검증 여부?** — 검증됨(5필드 초기값 적용, 요약 파생값 매핑 확인, embedding/TSU 완료 처리 안 함).
7. **Periodical 적용 필요사항 발견 여부?** — 예 — Issue 실데이터 검증이 여전히 없음(Risk #4), 별도 승인 필요.
8. **Metadata Migration 가능 여부?** — 아니오, BLOCKED.
9. **TSU Pipeline 진입 가능 여부?** — 아니오 — `tsu_status: pending` 그대로, TSU_ELIGIBLE 판정 메커니즘 자체가 여전히 없음.

---

```
STATUS: COMPLETE (pilot data created, no migration performed)
FILES CREATED:
  resources/theological_sources/manifest/pilot/dagg/manifest.yaml
  resources/theological_sources/manifest/pilot/hiscox/manifest.yaml
  resources/theological_sources/manifest/pilot/fuller/manifest.yaml
  resources/theological_sources/manifest/schema/README.md
  docs/NAE_MANIFEST_PILOT_REPORT_001.md
VALIDATION:
  Reference Integrity: PASS (10/10)
  Validator v2.2 regression: PASS (89/0/0 full-tree, 21/0/0 baptist-isolated, unchanged)
  Validator v2.2 direct Manifest check: NOT APPLICABLE (structural — see Risk #1)
RISKS: 6 items recorded, none BLOCKER-severity for this Pilot's own scope,
  but Risk #1/#4 block Corpus-wide Migration
MIGRATION READINESS: BLOCKED
COMMIT WAITING FOR APPROVAL
```

---

## 로드맵 갱신

```
Manifest Pilot Implementation   ✅ (이번 작업)

C1 Manifest Pilot Review          NEXT
Schema v2.2 Final Lock              FUTURE
Metadata Migration Approval          FUTURE
TSU Eligibility Check                  FUTURE
TSU Pipeline                             FUTURE
```

---

*전체 Corpus Metadata Migration, RAW 수정, OCR 수정, TSU/Embedding
생성, Retrieval 변경, `source_validator.py` 추가 수정, Authority
Registry 확대, Git Commit — 전부 수행하지 않음.*
