# NAE Metadata Pilot Report 001

**Project:** NAE-METADATA-PILOT-001
**Date:** 2026-08-02
**Scope:** `NAE/corpus/raw/archive_org/church_order/` — Dagg, Hiscox (2 works)
**Nature:** Pilot Implementation (전체 Corpus Migration 아님)
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

church_order 카테고리 2개 작품(Dagg, Hiscox)에 Metadata Schema v2.0.0과
Author→Work→Edition→Source 4단 Authority 모델을 실제 적용했다. Reference
Integrity는 4개 방향 전부 PASS. RAW 원문(OCR 텍스트)에서 발행연도·발행처를
직접 실측 확인했고, 이 과정에서 **문서 불일치 2건**(제목 표기 3원 불일치,
이전 Audit 보고서의 hOCR "미검출" 기록이 실측과 다름)과 **스키마 gap 1건**
(`source_type` enum에 "공개 아카이브 PD 자료"에 정확히 맞는 값이 없음)을
발견했다.

**STATUS: PASS WITH CONDITIONS**

---

## 2. Pilot Scope

| 항목 | 값 |
|---|---|
| 대상 디렉토리 | `NAE/corpus/raw/archive_org/church_order/` |
| 대상 작품 | Dagg_Church_Order/, Hiscox_Standard_Manual/ |
| 파일 구성(실측) | 각 work: `original.pdf`, `ocr.txt`, `hocr.html` |
| 용량(실측) | Dagg 33MB, Hiscox 16MB |
| Archive metadata JSON | **없음** — RAW 디렉토리에 archive.org 사이드카 메타데이터 파일 미존재(실측) |

---

## 3. Author Registry Result

파일: [`resources/theological_sources/authority/pilot/authors.yaml`](../resources/theological_sources/authority/pilot/authors.yaml)

| author_id | canonical_name | 근거 |
|---|---|---|
| `dagg_john_l` | John L. Dagg | RAW title page 실측(`ocr.txt`: "BY J. L. DAGG, D.D.") |
| `hiscox_edward_t` | Edward T. Hiscox | RAW title page 실측(`ocr.txt`: "BY EDWARD T. HISCOX, D.D.") |

`birth_year`/`death_year`/`tradition`은 RAW 파일에 없어 일반 전기 정보로
채움 — **이번 pilot에서 원문 검증 안 됨**(§9 Issues 참고).

---

## 4. Work Registry Result

파일: [`resources/theological_sources/authority/pilot/works.yaml`](../resources/theological_sources/authority/pilot/works.yaml)

| work_id | canonical title(RAW 실측) | title_variants |
|---|---|---|
| `WORK-DAGG-CHURCH-ORDER-001` | "Church Order" | "A Treatise on Church Order"(명령서), "Manual of Church Order"(기존 CSV) |
| `WORK-HISCOX-STANDARD-MANUAL-001` | "The Standard Manual for Baptist Churches" | 없음(3곳 일치) |

**발견**: Dagg 작품 제목이 RAW 원문/작업 명령서/기존
`NAE_SOURCE_MANIFEST_v1.csv`(BAP-CHURCH-DAGG-001, "Manual of Church Order")
3곳에서 전부 다르게 표기되어 있다. `title_variants` 필드로 3개 표기를
모두 보존하고 RAW 실측을 canonical로 채택했다(§1 Metadata Philosophy —
원본 표기 보존 원칙 적용).

---

## 5. Edition Registry Result

파일: [`resources/theological_sources/authority/pilot/editions.yaml`](../resources/theological_sources/authority/pilot/editions.yaml)

| edition_id | publication_year | publisher | 근거 |
|---|---|---|---|
| `WORK-DAGG-CHURCH-ORDER-001-1871` | 1871 | Bible and Publication Society (Philadelphia) | `ocr.txt` 실측: "Entered according to Act of Congress, in the year 1871" |
| `WORK-HISCOX-STANDARD-MANUAL-001-1890` | 1890 | American Baptist Publication Society (Philadelphia) | `ocr.txt` 실측: "Entered...in the year 1890...American Baptist Publication Society" |

두 작품 모두 RAW에 판본 1개씩만 확인 — 이번 pilot 대상에는 Edition
Authority가 실제로 여러 판본을 구분해야 하는 사례가 없다(§8 Migration
Findings에서 "자동화 가능 영역"으로 재확인).

---

## 6. Source Mapping Result

파일: [`resources/theological_sources/authority/pilot/sources.yaml`](../resources/theological_sources/authority/pilot/sources.yaml)

| source_id | edition_id | file_type | ocr_available | quality_status |
|---|---|---|---|---|
| `BAP-CHURCH-DAGG-001` | `WORK-DAGG-CHURCH-ORDER-001-1871` | pdf, txt, hocr | true | **WARNING** |
| `BAP-CHURCH-HISCOX` | `WORK-HISCOX-STANDARD-MANUAL-001-1890` | pdf, txt, hocr | true | PASS |

- `source_id`는 기존 `NAE_SOURCE_MANIFEST_v1.csv`의 값을 그대로 재사용
  (신규 발급하지 않음 — 기존 manifest 덮어쓰기 금지 원칙과는 별개로,
  ID 재사용 자체는 "기존 manifest를 참조만 하고 값을 복제하지 않는다"는
  Registry 설계 원칙과 일치).
- Dagg는 `ocr.txt` 초반부에 스캔 노이즈가 많아(예: "Tee ae H", "rk") 품질
  WARNING 판정.
- **hOCR 발견 정정**: 이전 [`NAE_BAPTIST_CORPUS_AUDIT_ADDENDUM_001.md`](NAE_BAPTIST_CORPUS_AUDIT_ADDENDUM_001.md)
  §4는 church_order 카테고리를 "hOCR 파일 미검출"로 기록했으나, 이번 pilot
  실측 결과 두 작품 모두 `hocr.html`이 실제로 존재한다. 해당 보고서는
  이번 작업 범위(Pilot)가 아니므로 소급 수정하지 않고 여기서만 정정 기록.

---

## 7. Integrity Validation (Phase 4)

| 방향 | 검사 | 결과 |
|---|---|---|
| Author Reference | `work.author_id` → `authors.yaml` 존재 | **PASS** (2/2: `dagg_john_l`, `hiscox_edward_t` 모두 존재) |
| Work Reference | `edition.work_id` → `works.yaml` 존재 | **PASS** (2/2) |
| Source Reference | `source.edition_id` → `editions.yaml` 존재 | **PASS** (2/2) |
| (추가) Manifest↔Registry | `manifest_pilot.yaml`의 author_id/work_id/edition_id/source_id가 각 registry와 전부 일치 | **PASS** (수동 대조, 4개 ID × 2 entry = 8개 참조 전부 일치) |

**전체 판정: PASS** — 4방향 참조 무결성 전부 통과.

---

## 8. Migration Findings (Phase 5, 시뮬레이션만)

| 구분 | 항목 |
|---|---|
| **정보 부족** | archive_source(원본 archive.org URL/식별자) — RAW에 사이드카 메타데이터가 없어 확인 불가. author의 birth_year/death_year — RAW 원문에 없음, 외부 소스 필요 |
| **Human Verification 필요** | (1) Dagg 제목 3원 불일치 해소(canonical 확정), (2) `source_type` enum 값 결정(§9 F-P1), (3) BAP-CHURCH-DAGG-002 "consolidated with -001" 경위 확인(원본 CSV 기록만 있고 근거 파일 불명) |
| **자동화 가능 영역** | publication_year/publisher 추출 — "Entered according to Act of Congress, in the year {YYYY}" 패턴이 두 작품 모두에서 동일하게 나타남, OCR 텍스트에 대한 정규식 매칭으로 자동 추출 가능성 높음(단, OCR 노이즈가 심한 자료는 실패율 있을 것으로 예상, Dagg 사례 참고) |

church_order → Metadata Layer 연결 자체는 **가능**하다고 확인됨(4개 entity
전부 실제 자료로 채울 수 있었음). 단, 이 2건은 저자당 작품 1개·판본 1개뿐이라
**Edition Authority의 "동일 work, 다른 edition" 로직과 Duplicate Policy의
"Different Scan Same Edition" 로직은 이번 pilot으로 검증되지 않았다** — 이전
[`NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md`](NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md)
§7이 이미 예견한 한계와 정확히 일치(그 리뷰가 권고한 "2단계 파일럿" 필요성 재확인).

---

## 9. Issues Found

| # | 항목 | 심각도 | 설명 |
|---|---|---|---|
| F-P1 | `source_type` enum gap | WARNING | 4개 값(`licensed\|purchased\|personal\|reference`) 중 "공개 archive.org PD 스캔본"에 정확히 맞는 값이 없음 — 이번 pilot은 잠정적으로 `reference`를 사용했으나 의미상 부정확(전문 저장이 이미 이루어지는 자료를 "인용만 허용"을 뜻하는 `reference`로 분류하는 것은 어색). `public_archive` 같은 5번째 값 추가를 권고 |
| F-P2 | 제목 3원 불일치 | WARNING | Dagg 작품명이 RAW/명령서/기존 CSV 3곳에서 전부 다름 — canonical 확정을 위한 사람 확인 필요(§4) |
| F-P3 | Audit-002 hOCR 기록 오류 | INFO | 이전 감사 보고서가 "hOCR 미검출"로 기록했으나 실측 결과 존재 — 이번 pilot 범위 밖이라 원본 미수정, 기록만 남김 |
| F-P4 | archive_source 정보 없음 | WARNING | RAW에 archive.org 사이드카 메타데이터가 전혀 없어 `archive_source` 필드를 추정치로만 채움 — 전체 확대 시 이 필드가 필수라면 별도 조사 필요 |
| F-P5 | BAP-CHURCH-DAGG-002 통합 경위 불명 | INFO | 기존 CSV에 "ACQUIRED_CONSOLIDATED_WITH_DAGG-001"로만 기록, RAW에는 통합 근거 파일이 없음 — 데이터 손실은 아니나(원본 CSV 기록 보존됨) 경위를 아는 사람 확인 권고 |

BLOCKER는 없음.

---

## 10. Recommendation

1. **F-P1(source_type gap)을 `NAE_METADATA_GOVERNANCE_v1.md` §4에 반영** —
   전체 확대 전 5번째 값(`public_archive` 또는 유사) 추가 여부 결정 필요.
2. **2단계 파일럿 진행** — [Plan Review-001](NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md)
   §7 권고대로, 다권본(Fuller Complete Works 등)으로 Edition Authority/
   Duplicate Policy 로직을 검증하는 2차 pilot을 Step 3(전체 소급 매핑) 전에
   수행할 것.
3. **archive_source 필드 정책 결정** — 이 필드를 필수로 유지할지, RAW에
   실제로 없는 정보이니 optional로 낮출지 결정 필요.
4. **제목 canonical 확정 절차 문서화** — 이번처럼 3원 불일치가 나올 때
   RAW 원문을 최우선으로 하는 규칙을 `NAE_CORPUS_INGESTION_STANDARD_v1.md`에
   명문화 권고(현재는 암묵적으로만 적용됨).

---

## 완료 판단 기준 답변

1. **Metadata Schema v2.0.0 적용 가능한가?** — 예. 2개 작품 모두 11개 필수 필드를 채울 수 있었다(단, `source_type`은 F-P1로 잠정치).
2. **Author/Work/Edition/Source 모델이 실제 자료에 적용 가능한가?** — 예, 4방향 Reference Integrity 전부 PASS. 단 Edition/Duplicate 로직은 이번 표본(판본 1개씩)으로는 미검증(§8).
3. **Reference Integrity 검증 통과했는가?** — 예, 4/4 PASS(§7).
4. **전체 Corpus 확대 전에 수정해야 할 문제가 있는가?** — 예, 4건(F-P1/F-P2/F-P4 WARNING, F-P5 INFO) — BLOCKER는 없으나 F-P1(enum gap)은 전체 확대 전 결정 필요.
5. **TSU Pipeline 연결 준비가 되었는가?** — 조건부 예. `manifest_pilot.yaml`이 TSU 필수 필드(`tsu_access`, `citation_policy`, `copyright_status` 등)를 전부 채웠으나, 이번 pilot에서 TSU를 실제로 생성하지 않았으므로(금지 사항) 실제 TSU 빌더와의 연동은 미검증.

---

```
STATUS: PASS WITH CONDITIONS
FILES CREATED:
  resources/theological_sources/authority/pilot/authors.yaml
  resources/theological_sources/authority/pilot/works.yaml
  resources/theological_sources/authority/pilot/editions.yaml
  resources/theological_sources/authority/pilot/sources.yaml
  resources/theological_sources/authority/pilot/manifest_pilot.yaml
  docs/NAE_METADATA_PILOT_REPORT_001.md
VALIDATION RESULT: Reference Integrity 4/4 PASS (Author/Work/Source 참조 + Manifest-Registry 대조)
RISKS: F-P1(source_type enum gap, WARNING) / F-P2(제목 3원 불일치, WARNING) /
  F-P4(archive_source 정보 없음, WARNING) / F-P3·F-P5(INFO, 비차단)
NEXT RECOMMENDATION: 다권본(Fuller Complete Works 등) 2단계 파일럿으로 Edition/
  Duplicate 로직 검증 후 Step 3(전체 소급 매핑) 착수. F-P1 enum gap은 그 전에
  GOVERNANCE 문서에 반영 권고.
```

---

*RAW 파일 수정/이동, OCR 변경, TSU/Embedding 생성, Retrieval 변경, 기존
Manifest 덮어쓰기, Git Commit 전부 수행하지 않음. early_baptist_collection 및
전체 Corpus Mapping은 이번 pilot 범위 밖.*
