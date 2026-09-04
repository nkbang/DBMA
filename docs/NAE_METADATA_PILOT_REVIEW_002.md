# NAE Metadata Pilot Review — 002

**Review ID:** NAE-METADATA-PILOT-REVIEW-002
**Date:** 2026-08-02
**Reviewer:** C1 (Read-Only Architecture Verification)
**Status:** COMPLETE
**Scope:** `resources/theological_sources/authority/pilot/` Pilot Registry + `docs/NAE_METADATA_PILOT_REPORT_001.md`
**근거 문서:** `docs/NAE_METADATA_GOVERNANCE_v1.md`, `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`, `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md`, `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md`

---

## 1. Executive Summary

Pilot Registry(5개 YAML 파일)와 Pilot Report는 Governance v1, ADR-014, ADR-015와 **전반적으로 일관**합니다. 다만 **3건의 WARNING**(source_type enum gap, Edition 확장성, 제목 3원 불일치)이 확인되었으며, **Commit은 조건부 승인**을 권고합니다.

**최종 판정: APPROVED WITH CONDITIONS**

---

## 2. Pilot Architecture Review (Phase 1)

### 2.1 Entity 분리 적합성

| Entity | 파일 | ID 예시 | Governance v1 §5.1 | 충돌 |
|--------|------|---------|---------------------|------|
| Author | `authors.yaml` | `dagg_john_l` | §5.1 Author | **PASS** |
| Work | `works.yaml` | `WORK-DAGG-CHURCH-ORDER-001` | §5.1 Work | **PASS** |
| Edition | `editions.yaml` | `WORK-DAGG-CHURCH-ORDER-001-1871` | §5.1 Edition (신규 승격) | **PASS** |
| Source File | `sources.yaml` | `BAP-CHURCH-DAGG-001` | §5.1 Source File | **PASS** |

4단계 Entity 모델(Author→Work→Edition→Source File)이 **역사 자료에 적용 가능**함을 pilot 2건으로 확인했습니다.

### 2.2 Registry 구조 확장성

| 항목 | 평가 | 설명 |
|------|------|------|
| 파일 분리(변경 빈도 기반) | **PASS** | `authors.yaml`(저자 등록 시만 변경) / `works.yaml`(edition 추가 시 변경) / `sources.yaml`(파일 유입 시 변경) — 분리 적절 |
| 중첩 구조 vs 별도 파일 | **WARNING** | Governance v1 §5.3은 `works.yaml`에 Edition+Source를 중첩 구조로 제안했으나, Pilot은 `editions.yaml`/`sources.yaml`을 별도 파일로 분리 — **구조적 차이**. 중첩 구조가 아니어도 기능적으로 문제 없으나, Governance v1과 구조가 다름을 기록 |
| git 추적성 | **PASS** | 모든 파일이 YAML 텍스트이므로 git blame/diff 적합 |

### 2.3 Reference 방향성 안전성

| 참조 방향 | 구현 | 안전성 | 평가 |
|-----------|------|--------|------|
| `works.yaml.author_id` → `authors.yaml` | 단방향 (Work → Author) | **안전** | Registry → Registry 단방향 참조 — Governance v1 §Registry Design과 일치 |
| `editions.yaml.work_id` → `works.yaml` | 단방향 (Edition → Work) | **안전** | 동일 |
| `sources.yaml.edition_id` → `editions.yaml` | 단방향 (Source → Edition) | **안전** | 동일 |
| `manifest_pilot.yaml` → Registry 전체 | 단방향 (Manifest → Registry) | **안전** | Manifest가 Registry를 참조 — 이중 관리 방지 원칙 준수 |

---

## 3. Schema v2.0.0 Review (Phase 2)

### 3.1 manifest_pilot.yaml 필드 완성도

| 필드 | 필수 | 값 | Governance v1 §6 | 충돌 |
|------|------|----|-------------------|------|
| `source_id` | 예 | `BAP-CHURCH-DAGG-001` | §6 | **PASS** |
| `author_id` | 예 | `dagg_john_l` | §6 | **PASS** |
| `work_id` | 예 | `WORK-DAGG-CHURCH-ORDER-001` | §6 | **PASS** |
| `edition_id` | 예 | `WORK-DAGG-CHURCH-ORDER-001-1871` | §5.1 (신규) | **PASS** (TSU 외부 필드) |
| `title` | 예 | `"Church Order"` | §3.4 (Modern schema) | **PASS** |
| `category` | 예 | `church_order` | §3.4 | **PASS** |
| `publication_year` | 예 | `1871` | §6 | **PASS** |
| `source_type` | 예 | `reference` | §6 enum: `licensed\|purchased\|personal\|reference` | **WARNING** (§3.2) |
| `copyright_status` | 예 | `public_domain` | §4.1 enum: `public_domain\|copyrighted\|licensed\|unknown` | **PASS** |
| `citation_policy` | 예 | citation string | §6 | **PASS** |
| `usage_permission` | 예 | `research` | §4.2 enum: `research\|citation_only\|internal_use\|no_redistribution` | **PASS** |
| `tsu_access` | 예 | `full` | §6: `full\|restricted\|citation_only` | **PASS** |
| `status` | 예 | `ACQUIRED` | 기존 v1.2 재사용 | **PASS** |

### 3.2 source_type enum gap (F-P1) — WARNING

**문제:** `manifest_pilot.yaml`에서 두 entry 모두 `source_type: reference`를 사용했으나, Governance v1 §6의 enum(`licensed\|purchased\|personal\|reference`) 중 "공개 archive.org PD 스캔본"에 정확히 맞는 값이 없습니다.

- `reference`: "인용만 허용"을 뜻함 — 전문이 이미 공개된 자료에 부적절
- `licensed`: 라이선스 계약 필요 — archive.org PD는 라이선스 아님
- `purchased`: 구매 영수증 필요 — PD 자료는 해당 없음
- `personal`: 개인 자료 — archive.org에서 가져온 자료 아님

**권고:** `public_archive` 또는 `public_domain` 5번째 값 추가 (Governance v1 §4.1 소급 정정 필요).

### 3.3 copyright_status 매핑 정확성

| source_id | license.source_value (원본) | copyright_status | Governance v1 §4.1 매핑표 | 평가 |
|-----------|---------------------------|------------------|--------------------------|------|
| BAP-CHURCH-DAGG-001 | "public domain" (archive.org 추정) | `public_domain` | `public_domain` → `public_domain` | **PASS** |
| BAP-CHURCH-HISCOX | "public domain" (archive.org 추정) | `public_domain` | 동일 | **PASS** |

### 3.4 usage_permission × copyright_status 조합

| source_id | copyright_status | usage_permission | tsu_access | Governance v1 §6 조합표 | 평가 |
|-----------|------------------|------------------|------------|------------------------|------|
| BAP-CHURCH-DAGG-001 | `public_domain` | `research` | `full` | `public_domain` → Full TSU | **PASS** |
| BAP-CHURCH-HISCOX | `public_domain` | `research` | `full` | 동일 | **PASS** |

---

## 4. Reference Integrity Review (Phase 3) — 재검증

### 4.1 Author Reference

```
works.yaml[0].author_id = "dagg_john_l"
    ↓ 조회
authors.yaml.authors[0].author_id = "dagg_john_l"  ✓

works.yaml[1].author_id = "hiscox_edward_t"
    ↓ 조회
authors.yaml.authors[1].author_id = "hiscox_edward_t"  ✓
```

**재검증 결과: PASS (2/2)** — CUE 결과와 일치.

### 4.2 Work Reference

```
editions.yaml[0].work_id = "WORK-DAGG-CHURCH-ORDER-001"
    ↓ 조회
works.yaml.works[0].work_id = "WORK-DAGG-CHURCH-ORDER-001"  ✓

editions.yaml[1].work_id = "WORK-HISCOX-STANDARD-MANUAL-001"
    ↓ 조회
works.yaml.works[1].work_id = "WORK-HISCOX-STANDARD-MANUAL-001"  ✓
```

**재검증 결과: PASS (2/2)** — CUE 결과와 일치.

### 4.3 Edition Reference

```
sources.yaml[0].edition_id = "WORK-DAGG-CHURCH-ORDER-001-1871"
    ↓ 조회
editions.yaml.editions[0].edition_id = "WORK-DAGG-CHURCH-ORDER-001-1871"  ✓

sources.yaml[1].edition_id = "WORK-HISCOX-STANDARD-MANUAL-001-1890"
    ↓ 조회
editions.yaml.editions[1].edition_id = "WORK-HISCOX-STANDARD-MANUAL-001-1890"  ✓
```

**재검증 결과: PASS (2/2)** — CUE 결과와 일치.

### 4.4 Manifest ↔ Registry 일관성

```
manifest_pilot.yaml[0]:
  source_id = "BAP-CHURCH-DAGG-001" → sources.yaml 존재 ✓
  author_id = "dagg_john_l" → authors.yaml 존재 ✓
  work_id = "WORK-DAGG-CHURCH-ORDER-001" → works.yaml 존재 ✓
  edition_id = "WORK-DAGG-CHURCH-ORDER-001-1871" → editions.yaml 존재 ✓

manifest_pilot.yaml[1]:
  source_id = "BAP-CHURCH-HISCOX" → sources.yaml 존재 ✓
  author_id = "hiscox_edward_t" → authors.yaml 존재 ✓
  work_id = "WORK-HISCOX-STANDARD-MANUAL-001" → works.yaml 존재 ✓
  edition_id = "WORK-HISCOX-STANDARD-MANUAL-001-1890" → editions.yaml 존재 ✓
```

**재검증 결과: PASS (4 entry × 4 참조 = 16개 참조 전부 일치)** — CUE 결과(4/4 PASS)와 일치.

---

## 5. Edition Authority Review (Phase 4)

### 5.1 Pilot Edition 규모

| Work | Edition 수 | 다판본 사례 |
|------|-----------|-------------|
| Dagg - Church Order | 1 | 없음 |
| Hiscox - Standard Manual | 1 | 없음 |

### 5.2 Edition 모델 확장성 평가

| 시나리오 | Pilot로 검증 가능 여부 | 설명 |
|----------|----------------------|------|
| 동일 저작, 다른 판본 (예: Fuller Complete Works 8권) | **NO** — Pilot에 다판본 사례 없음 | `edition_id` 생성 로직(연도/판본 표기 기반)이 실제로 어떻게 동작하는지 검증 불가 |
| 동일 판본, 다른 스캔본 (Duplicate Policy) | **NO** — Pilot에 재스캔 사례 없음 | "Different Scan Same Edition" 로직 검증 불가 |
| Edition 간 Work 공유 (예: Spurgeon MTP 여러 판본이 동일 Work) | **NO** — Pilot에 Work 공유 사례 없음 | `work_id`가 Edition 간 공유되는 구조 검증 불가 |

### 5.3 실제 다권본 자료 적용 위험

| 자료 | 예상 Edition 수 | Pilot로 검증되지 않는 로직 |
|------|----------------|---------------------------|
| Fuller Complete Works | 8권 (8 Edition) | Edition 생성/Work-Edition 매핑 |
| Spurgeon MTP | 여러 판본 | Edition 간 Work 공유 |
| Gill Annotated Lecturees | 여러 판본 | 판본 구분 로직 |

**판정: WARNING** — Pilot은 Edition Authority/Duplicate Policy 로직을 **검증하지 못함**. 이전 Plan Review-001 §7이 이미 예견한 한계와 정확히 일치.

---

## 6. hOCR Audit Correction Review (Phase 5)

### 6.1 불일치 사항

| 보고서 | church_order hOCR 기록 | Pilot 실측 |
|--------|----------------------|------------|
| `NAE_BAPTIST_CORPUS_AUDIT_ADDENDUM_001.md` §4 | "hOCR 파일 미검출" | `hocr.html` 존재 (Dagg/Hiscox 둘 다) |

### 6.2 정정 방식 평가

Pilot Report §6는 "이전 보고서는 이번 pilot 범위가 아니므로 소급 수정하지 않고 여기서만 정정 기록" — **적절한 방식**.

- RAW immutable 원칙(NAE_DATA_ARCHITECTURE.md)에 따라 기존 Audit 보고서 수정 금지
- 정정 기록만 남김으로써 향후 혼동 방지
- `sources.yaml`의 Dagg notes 필드에서도 "hocr.html 존재(Audit-002 보고서는 'hOCR 미검출'로 기록했으나 실측 결과 존재함)"라고 명시 — **이중 정정 기록**으로 안전성 확보

**판정: PASS** — 정정 방식 적절.

---

## 7. Title Authority Review (Phase 6)

### 7.1 Dagg 제목 3원 불일치

| 출처 | 제목 |
|------|------|
| RAW title page (ocr.txt 실측) | `"CHURCH ORDER."` |
| Pilot 작업 명령서 | `"A Treatise on Church Order"` |
| 기존 CSV (NAE_SOURCE_MANIFEST_v1.csv) | `"Manual of Church Order"` |

### 7.2 Pilot Report 대응 평가

`works.yaml`은 `title_variants` 필드로 3개 표기를 모두 보존하고, RAW 실측 `"Church Order"`을 canonical로 채택 — **적절한 방식**.

### 7.3 추가 권고: 제목 필드 구조

현재 `works.yaml`의 제목 필드:
```yaml
title: "Church Order"              # canonical (RAW 실측)
title_variants:                    # 다른 모든 표기
  - "A Treatise on Church Order"
  - "Manual of Church Order"
```

**권고:** 향후 Title Authority 관리 명확화를 위해 명시적 필드 분리 고려:

```yaml
title_canonical: "Church Order"    # RAW title page 실측 (최우선)
title_original: "CHURCH ORDER."    # RAW 원문 표기 (대소문자/구두점 포함)
title_archive: "A Treatise on Church Order"  # archive.org 메타데이터 표기
title_manifest: "Manual of Church Order"      # 기존 manifest 표기
```

다만 이는 **전체 Corpus 확대 시** 고려할 사항이며, Pilot 규모에서는 현재 구조로 충분.

**판정: PASS (권고사항 있음)**

---

## 8. Risk Assessment (Phase 7)

### 8.1 Risk Summary Table

| # | 항목 | 심각도 | 설명 | 권고 |
|---|------|--------|------|------|
| R1 | source_type enum gap | **WARNING** | "공개 archive.org PD 스캔본"에 맞는 값 없음 | Governance v1 §4.1에 `public_archive` 추가 검토 |
| R2 | Edition/Duplicate 로직 미검증 | **WARNING** | Pilot에 다판본/재스캔 사례 없음 | Fuller Complete Works 등 2단계 파일럿 필수 |
| R3 | Registry 구조 불일치 | **LOW** | Pilot(별도 파일) vs Governance v1(중첩 구조) | Governance v1 §5.3 구조로 통일하거나 Pilot 구조를 Governance에 반영 |

### 8.2 BLOCKER 평가

**BLOCKER 없음.** R1(enum gap)은 `reference` 잠정치로 우회 가능. R2( Edition 로직)는 2단계 파일럿으로 해결 가능. R3(구조 불일치)는 기능적 문제 없음.

---

## 9. Commit Decision (Phase 8)

### 판정: **APPROVED WITH CONDITIONS**

### 승인 조건

| # | 조건 | 상태 |
|---|------|------|
| 1 | R1(enum gap)을 Governance v1에 반영할 값 결정 | 미결정 — 결정 필요 |
| 2 | 2단계 파일럿(다권본) 계획 수립 | 미수행 — 필수 |
| 3 | Registry 구조(Governance v1 중첩 vs Pilot 별도 파일) 통일 | 선택적 — 기능적 문제 없음 |

### Commit 권고

**조건부 승인.** R1(enum gap)의 값 결정 전이라도 Pilot Registry 파일 자체는 수정/추가/삭제가 필요 없는 상태이므로 **Commit은 가능**. 다만 다음 사항을コミット 메시지에 명시 권고:

```
feat: add pilot authority registry (church_order category, 2 works)

- authors.yaml, works.yaml, editions.yaml, sources.yaml, manifest_pilot.yaml
- Pilot scope: Dagg Church Order, Hiscox Standard Manual
- Reference Integrity: 4/4 PASS
- Known issues: source_type enum gap (F-P1), Edition logic untested
- Next: multi-volume pilot (Fuller Complete Works) for Edition/Duplicate validation
```

---

## 10. Next Action Recommendation (Phase 9)

### 우선순위 1 (필수): 2단계 파일럿 — 다권본 자료

```
Fuller Complete Works (8권) 또는 Spurgeon MTP (여러 판본)
```

**이유:** Edition Authority/Duplicate Policy 로직을 검증하지 않고 전체 소급 매핑 진행 시, 동일 Work의 여러 Edition을 잘못 분리하거나 동일 Edition의 여러 Source File을 잘못 분리할 위험이 있음.

### 우선순위 2 (권고): source_type enum gap 정정

Governance v1 §4.1에 `public_archive` 또는 유사 값 추가 여부 결정.

### 우선순위 3 (선택): Registry 구조 통일

Governance v1 §5.3의 "중첩 구조"와 Pilot의 "별도 파일" 중 하나로 통일. 기능적 차이 없음으나 문서화 일관성 필요.

---

## Appendix A: Reviewed File Inventory

| 파일 | 경로 | 상태 |
|------|------|------|
| authors.yaml | `resources/theological_sources/authority/pilot/authors.yaml` | 검토 완료 |
| works.yaml | `resources/theological_sources/authority/pilot/works.yaml` | 검토 완료 |
| editions.yaml | `resources/theological_sources/authority/pilot/editions.yaml` | 검토 완료 |
| sources.yaml | `resources/theological_sources/authority/pilot/sources.yaml` | 검토 완료 |
| manifest_pilot.yaml | `resources/theological_sources/authority/pilot/manifest_pilot.yaml` | 검토 완료 |
| Pilot Report | `docs/NAE_METADATA_PILOT_REPORT_001.md` | 검토 완료 |
| Governance v1 | `docs/NAE_METADATA_GOVERNANCE_v1.md` | 근거 문서 |
| ADR-014 | `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md` | 근거 문서 |
| ADR-015 | `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md` | 근거 문서 |

---

**Review Complete. 2026-08-02.**

```
STATUS: APPROVED WITH CONDITIONS
COMMIT: CONDITIONAL (R1 enum gap 결정 전이라도 가능 — 메시지 명시 권고)
NEXT STEP: 우선순위 1 — Fuller Complete Works 등 다권본 2단계 파일럿으로 Edition/Duplicate 로직 검증