# NAE Manifest Validator Architecture Design 001

작성일: 2026-08-03
Project: NAE-MANIFEST-VALIDATOR-ARCHITECTURE-001
성격: **설계 문서 — 코드 수정 없음**
근거: [`NAE_MANIFEST_PILOT_REPORT_001.md`](NAE_MANIFEST_PILOT_REPORT_001.md) §5/§7 Risk #1(BLOCKER 원인),
[`NAE_VALIDATOR_BOUNDARY_DESIGN_001.md`](NAE_VALIDATOR_BOUNDARY_DESIGN_001.md),
[`NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md`](NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md),
[ADR-019](architecture/ADR-019-NAE-Corpus-Manifest-Layer.md)

---

## 0. BLOCKER 재확인

Manifest Pilot Report-001이 실측으로 확인한 문제: Manifest Layer
데이터(`resources/theological_sources/manifest/pilot/*/manifest.yaml`,
최상위 키 `manifests:`)는 `source_validator.py`가 탐색하는 파일명
(`source_manifest.yaml`)·구조(`sources:`)와 다르다 — **Manifest Layer
전용 파일은 어떤 도구로도 자동 검증되지 않는 상태**다. 이 설계는 이
gap을 메운다.

---

## 1. source_validator.py / manifest_validator.py 책임 분리

### 결정: **2개 도구로 분리 유지, 단 각자의 스캔 대상을 명확히 재정의**

```
source_validator.py       — corpus manifest(source_manifest.yaml, sources:) 전담
                             (v1.2/v2.1.x/v2.2.x 3-트랙, 기존 구현 그대로)

manifest_validator.py      — Manifest Layer(manifest.yaml, manifests:) 전담 [신규 설계]
                             Identity/Authority Reference/Lifecycle/Audit 검증
```

`authority_validator.py`(Registry 전담, Registry Design v1 §Phase5,
여전히 설계만)까지 포함하면 최종적으로 3개 도구 체제
(Validator Boundary Design-001의 원안)가 유지된다 — 다만 이번
BLOCKER를 겪으며 **"3개 도구"가 이론이 아니라 실제로 필요하다는 것이
Pilot 데이터로 증명됐다**는 점이 이전 설계 문서와의 차이다.

### 책임 경계표

| 검증 항목 | 담당 |
|---|---|
| corpus manifest 필수 필드/enum(title/category/source_type 등) | `source_validator.py`(변경 없음) |
| corpus manifest entry에 `manifest_id`가 얹혀 있을 때의 opt-in 검사(기존 구현, NAE-VALIDATOR-V2.2-IMPLEMENTATION-001 Phase 7) | `source_validator.py`(**유지, 제거하지 않음** — 하위 호환) |
| Registry 내부 FK(Work→Author, Edition→Work 등, Registry 파일들 사이) | `authority_validator.py`(설계만, 변경 없음) |
| **Manifest Layer 파일(`manifest.yaml`) 탐색·존재 검증** | **`manifest_validator.py`(신규)** |
| **Manifest→Registry FK**(author_id/work_id/edition_id/volume_id/issue_id/source_id) | **`manifest_validator.py`(신규, 아래 §3)** |
| **Manifest Lifecycle 필드 검증**(5개 상태 + 파생 요약) | **`manifest_validator.py`(신규)** |
| **TSU_ELIGIBLE Gate 계산**(아래 §4) | **`manifest_validator.py`(신규)** |

**중복 금지 원칙 재확인**: `manifest_validator.py`는 corpus manifest의
필수 필드(title/category 등)를 재검사하지 않는다 — 그건
`source_validator.py`의 책임이다. 반대로 `source_validator.py`의
기존 opt-in Manifest 필드 검사(entry 내 `manifest_id`)는 **제거하지
않는다** — 이미 배포된 기능이고 회귀를 만들 이유가 없다. 두 경로가
공존하되(entry-embedded 방식 vs 별도 파일 방식), 새로 생성되는
Manifest 데이터는 별도 파일 방식(`manifest_validator.py` 대상)을
정본으로 삼는다(§5).

---

## 2. Manifest Schema v1.0.0 검증 범위

`manifest_validator.py`가 검증할 항목(Manifest Schema Design v1의
필드 정의 그대로, 코드는 미작성):

```
Identity:
  manifest_id, source_id, schema_version  — 존재 확인

Authority Reference:
  author_id, work_id, edition_id(조건부), volume_id(조건부),
  issue_id(조건부)  — §3에서 FK 검증

Processing Lifecycle:
  acquisition_status / ocr_status / metadata_status / tsu_status /
  embedding_status  — 각 enum 값 유효성
  processing_status(파생 요약)가 5개 필드와 일치하는지 sync 검사
  (Manifest Pilot에서 실제로 이 파생값을 수동 계산해 넣었음 —
  Pilot Report-001 §6 — 자동 재계산 검증 필요성이 실증됨)

Quality Gate:
  ocr_quality / metadata_verified / authority_verified / tsu_eligible
  — §4에서 상세

Audit:
  created_at / updated_at / verified_by  — 존재 확인(형식 검증까지는
  이번 설계 범위, `verified_by` 없으면 WARNING — source_validator.py의
  기존 opt-in 검사와 동일한 관용 수준 유지)
```

**work_type 조건부 규칙 재사용**: `edition_id`/`volume_id`/
`issue_id`의 필수 여부는 `source_validator.py`가 이미 구현한
`_WORK_TYPE_FIELD_RULES`(NAE-VALIDATOR-V2.2-IMPLEMENTATION-001)를
**그대로 재사용**한다 — Manifest Entry에는 `work_type` 필드가 직접
없으므로, `work_id`로 Registry를 조회해 해당 Work의 `work_type`을
가져온 뒤 같은 규칙표를 적용한다(중복 규칙 정의 금지).

---

## 3. Authority Registry FK 검증 위치

### 결정: **`manifest_validator.py`에서 필수(mandatory) 수행** —
`source_validator.py`의 기존 `--registry-path`(선택)와는 별도 정책

| 도구 | FK 검증 방식 |
|---|---|
| `source_validator.py` | `--registry-path` **선택** 플래그(기존 그대로 유지) — corpus manifest 자체는 Registry 없이도 스키마 검증만으로 의미가 있으므로 |
| `manifest_validator.py`(신규) | **필수** — Manifest Entry의 존재 이유 자체가 "Registry와 Source를 이어주는 것"이므로, Registry 경로 없이 실행하는 것 자체를 오류로 처리(`--registry-path` 인자를 optional이 아니라 required로 설계) |

Manifest Pilot Report-001의 Reference Integrity 검증(Python 스크립트,
10/10 PASS)이 이번 설계의 **레퍼런스 구현**이다 — `manifest_validator.py`는
그 스크립트의 검사 로직(author_id/work_id/edition_id/volume_id/
source_id 존재 확인)을 정식 도구로 승격한 것.

---

## 4. TSU_ELIGIBLE Gate 요구사항

### 계산식(Manifest Schema Design v1 §Phase2 계산식 재확인·구체화)

```
tsu_eligible =
    ocr_status == "complete"
    AND metadata_status IN ("validated",)
    AND authority_verified == true   (§3 FK 검증 전부 PASS일 때 true)
    AND ocr_quality IN ("PASS", "WARNING", null)   # FAIL이면 불가, 미측정(null)은 잠정 허용
    AND copyright_status != "unknown"
```

### `copyright_status` 교차 조회 문제(신규 발견)

`copyright_status`는 Manifest Entry 필드가 아니라 **corpus manifest**
(source_manifest.yaml)에 있는 필드다(GOVERNANCE §4.1) — TSU_ELIGIBLE을
계산하려면 `manifest_validator.py`가 `source_id`로 corpus manifest
entry를 교차 조회해야 한다.

**결정: 교차 조회 방식 채택(값 복제 아님)** — `copyright_status`를
Manifest Entry에 비정규화 복사해 두는 대안도 검토했으나, 저작권처럼
민감하고 자주 바뀔 수 있는 governance 필드는 **단일 정본(corpus
manifest)만 유지**하는 편이 안전하다(Registry Design v1 §2.5 "governance
4필드는 corpus manifest 책임"과 일관). `manifest_validator.py`는
`--corpus-manifest-root` 인자(별도, `source_validator.py`의 `--root`와
동일 개념)로 corpus manifest 트리도 함께 읽어 `source_id` 기준
교차 조회한다.

### TSU_ELIGIBLE 필수 필드 목록(최종)

```
Manifest Entry에서: ocr_status, metadata_status, ocr_quality(선택,
  null 허용), authority_verified(FK 검증 결과로 계산)
corpus manifest에서(교차 조회): copyright_status
```

---

## 5. Migration 전제조건 업데이트

`NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md` Phase 3(Validator
Integration)과 `NAE_MANIFEST_PILOT_REPORT_001.md` §8(BLOCKED 사유)을
아래와 같이 구체화한다:

```
기존(모호): "Validator Integration" 단계에서 검증 도구 구현
        ↓
갱신(이번 설계로 구체화):
  1. manifest_validator.py 구현(이번 문서 §1~4 사양대로, 별도 승인)
  2. Manifest Pilot(10건, 이미 생성됨)에 대해 manifest_validator.py 실행
     → Reference Integrity 10/10 PASS 유지 확인(회귀)
     → TSU_ELIGIBLE 계산 결과가 사람이 수동 검토한 값과 일치하는지 확인
  3. 위 2가 성공해야 Corpus-wide Migration 검토 착수 가능
```

이 순서가 충족되기 전까지 Migration은 계속 **BLOCKED**다.

---

## 최종 답변

### Validator 통합 방식

**통합하지 않는다 — `source_validator.py`(corpus manifest 전담)와
`manifest_validator.py`(Manifest Layer 전담, 신규 설계)로 분리
유지**, `authority_validator.py`(Registry 전담, 여전히 설계만)까지
3개 도구 체제. `source_validator.py`의 기존 opt-in Manifest 필드
검사는 하위 호환을 위해 그대로 둔다.

### TSU Gate 필요 필드

Manifest Entry: `ocr_status`, `metadata_status`, `ocr_quality`(선택),
`authority_verified`(FK 검증 결과). corpus manifest 교차 조회:
`copyright_status`. 다섯 조건 전부 AND로 결합(§4 계산식).

### Migration 가능 여부

**아니오, 여전히 BLOCKED.** 이번 문서는 설계만 완료했다 —
`manifest_validator.py` 코드가 없고, 따라서 §5의 갱신된 전제조건
1~2단계가 아직 수행되지 않았다.

### 다음 구현 단계

1. `manifest_validator.py` 코드 구현(별도 승인 필요, 이번 설계 범위 밖).
2. Manifest Pilot(기존 10건)에 대해 실제 실행 및 회귀 확인.
3. TSU_ELIGIBLE 계산 결과의 사람 검토(수동 대조).
4. 위 3건 통과 후에만 Corpus-wide Migration 재검토.
