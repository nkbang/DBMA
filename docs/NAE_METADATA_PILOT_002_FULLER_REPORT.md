# NAE Metadata Pilot 002 — Fuller Multi-Volume Report

**Project:** NAE-METADATA-PILOT-002
**Date:** 2026-08-02
**Scope:** `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01`~`Vol08` (Andrew Fuller, 8 volumes)
**Nature:** Pilot Implementation — Fuller 자료 등록이 목적이 아니라 **Authority Model이 대규모 다권본을 감당할 수 있는지 검증**하는 것이 목적
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

8개 volume 전부의 RAW `ocr.txt` 제목면을 직접 실측한 결과, 기존 가정과
달리 **이 "Eight Volumes" 세트는 실제로는 서로 다른 두 인쇄본(Edition)의
혼합**이었다 — Vol01은 1820년 Charlestown, MA에서, Vol02~08은 1824~1825년
New Haven(S. Converse)에서 각각 별도로 인쇄되었다. 또한 기존
`NAE_SOURCE_MANIFEST_v1.csv`는 8개 volume 전체를 **단일 source_id
(`BAP-MISS-FULLER`)** 로만 등록하고 있어 volume 단위 구분이 전혀 없다는
사실도 확인했다.

Author→Work→Edition→Volume→Source 5단 모델을 실제로 구축해 Reference
Integrity를 프로그램적으로 검증한 결과 **4개 방향 전부 PASS**했다(1 author,
1 work, 2 edition, 8 volume, 8 source, 8 manifest entry — 총 참조 관계
전수 검사). 모델은 이 규모(다권본, Edition 혼재)를 감당할 수 있다고
판단되나, Volume을 Edition 산하 고정 하위로 두는 원안(Phase 2 옵션 A)은
**Edition을 Work당 1개로 가정하면 깨진다** — 이번 실측으로 이 가정이
틀렸음이 확인되어, 모델 자체는 유지하되 "Work 1개 : Edition N개(N≥1)"
관계로 명확히 재정의할 것을 권고한다.

**STATUS: PASS WITH CONDITIONS**

---

## 2. Fuller Corpus Inventory (Phase 1)

| Volume | 파일 구성(실측) | 크기 | hOCR | Title Page 실측(발행처/연도) |
|---|---|---|---|---|
| Vol01 | pdf, txt | 30MB | **없음** | Anderson & Meehan for Wm. Collins, Charlestown, MA, **1820** |
| Vol02 | pdf, txt | 26MB | 없음 | S. Converse, New Haven, **1824** |
| Vol03 | pdf, txt | 25MB | 없음 | S. Converse, New Haven, **1824** |
| Vol04 | pdf, txt | 31MB | 없음 | S. Converse, New Haven, **1824** |
| Vol05 | pdf, txt | 26MB | 없음 | S. Converse, New Haven, **1825** |
| Vol06 | pdf, txt | 23MB | 없음 | S. Converse, New Haven, **1825** |
| Vol07 | pdf, txt | 30MB | 없음 | S. Converse, New Haven, **1824**(OCR 잘림, 잠정) |
| Vol08 | pdf, txt | 35MB | 없음 | S. Converse, New Haven, **1825** |

- **PDF/TXT는 8개 volume 전부 존재.**
- **hOCR은 8개 volume 전부 없음** — Pilot-001(church_order)과 대조적
  (그쪽은 2개 work 모두 hOCR 존재). missions 카테고리 특성인지 개별
  work 특성인지는 이번 pilot 범위에서 판단 불가(표본 부족).
- 소장처 단서: Vol01/03/04/05/08은 NYPL Research Libraries 바코드,
  Vol06은 Princeton Theological Seminary 기증 장서인 — 서로 다른
  물리적 소장처의 스캔본이 하나의 archive.org work로 묶여 있음(§6
  Duplicate Analysis와 연결).

---

## 3. Authority Model Evaluation (Phase 2)

### 검토한 두 모델

```
옵션 A: Author → Work → Edition → Volume → Source
옵션 B: Author → Work → Volume Work(volume을 work처럼 취급) → Source
```

### 판정: **옵션 A 채택, 단 "Work:Edition = 1:N" 관계로 수정**

원안(옵션 A)은 암묵적으로 Edition이 Work당 1개라고 가정하는 것처럼 보였으나
(Pilot-001에서는 실제로 Work:Edition이 1:1이었음), 이번 실측이 그 가정을
반증했다 — 동일 Work("Eight Volumes" 세트) 안에 **서로 다른 인쇄 캠페인
2개**가 섞여 있다. 옵션 A의 계층 구조 자체(Work→Edition→Volume→Source)는
이 상황을 정확히 표현할 수 있다(Edition을 2개 만들고 각각에 해당 volume을
연결하면 됨) — **모델을 바꿀 필요는 없고, "Work 1개당 Edition은 1개 이상일
수 있다"는 서술을 Authority Model 문서에 명시적으로 추가하면 된다.**

옵션 B(Volume을 독립 Work처럼 취급)는 기각한다 — 8개 volume이 하나의
저작으로 기획·판매된 단일 "Works" 세트라는 서지학적 사실을 Work
엔티티가 표현하지 못하게 되어, 검색 시 "Fuller Complete Works" 전체를
하나로 묶어 보여주는 기능을 잃는다.

---

## 4. Volume Model Evaluation (Phase 4)

파일: [`authority/pilot/fuller/volumes.yaml`](../resources/theological_sources/authority/pilot/fuller/volumes.yaml)

| volume_id | volume_number | edition_id | publication_year |
|---|---|---|---|
| `FULLER-COMPLETE-WORKS-VOL01` | 1 | `...-ED-CHARLESTOWN-1820` | 1820 |
| `FULLER-COMPLETE-WORKS-VOL02`~`VOL08` | 2~8 | `...-ED-NEWHAVEN-CONVERSE` | 1824 또는 1825 |

- Volume 번호: RAW title page의 로마숫자(예: "VOL. VIII")는 OCR 노이즈로
  일부 오인식되었으나(예: Vol01은 "VOL. L"로 스캔됨 — I가 L로 오인식),
  **디렉토리명(`Fuller_Complete_Works_Vol01`~`08`)이 명확한 canonical
  volume_number 출처**이므로 이를 기준으로 삼았다 — OCR 텍스트만으로
  volume 번호를 자동 파싱하면 오류 가능성이 있다는 실증 사례(§8 Schema
  Feedback에서 자동화 관련 시사점으로 재확인).
- Work 연결: 8개 volume 전부 `work_id: FULLER-COMPLETE-WORKS-001`로 통일
  — 프로그램적 검증(Python 스크립트, §7)으로 확인.

**판정: VOLUME MODEL — APPROVED**

---

## 5. Edition Analysis (Phase 2/4 상세)

| edition_id | publisher | year | volume 수 |
|---|---|---|---|
| `FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820` | Anderson & Meehan for W. Collins | 1820 | 1 (Vol01) |
| `FULLER-COMPLETE-WORKS-001-ED-NEWHAVEN-CONVERSE` | S. Converse | 1824–1825 | 7 (Vol02~08) |

두 번째 Edition 내부에서도 volume별 연도가 1824/1825로 갈리는데, 이를
Edition을 더 쪼개는 근거로 삼지 않고 **Edition의 `publication_year`를
범위("1824-1825")로, 개별 volume의 `publication_year`는 정확한 연도로**
이중 기록했다 — 다권본이 여러 해에 걸쳐 순차 출판되는 것은 정상적인
출판 관행이므로 이를 "다른 Edition"으로 과분류하지 않기 위함(신뢰도
판단: Vol01만 발행처/도시/연도 3가지가 모두 다르므로 확실한 별도
Edition, 나머지는 발행처/도시는 같고 연도만 1년 차이이므로 같은 Edition
내 순차 출판으로 판단).

---

## 6. Duplicate Analysis (Phase 5)

| 구분 | 발견 | Evidence | Recommendation |
|---|---|---|---|
| **Exact Duplicate** | 없음 | 8개 volume 모두 서로 다른 PDF/TXT 파일(경로·크기 상이) | 조치 불요 |
| **Same Edition, Different Scan** | 없음 | 각 volume당 스캔본 1개씩만 확인 | 조치 불요 |
| **Different Edition** | **있음** | Vol01(Charlestown, 1820) vs Vol02~08(New Haven, S. Converse, 1824~1825) — title page 발행처/도시/연도 3요소가 전부 다름 | 두 개의 `edition_id`로 분리 등록(이미 registry에 반영). Vol01이 실제로 "Eight Volumes" 세트에 원래부터 속했는지, 아니면 후대에 함께 묶인 것인지는 서지학적 추가 조사 필요(사람 확인 권고, BLOCKER 아님) |
| **Volume Conflict(권수 표기 오류)** | 경미 | OCR이 로마숫자를 오인식(Vol01 "VOL. L", Vol03 "VOL. 111") — 그러나 디렉토리명은 일관되게 Vol01~08 | 디렉토리명을 canonical volume_number 출처로 채택(반영 완료). OCR 기반 자동 파싱은 검증 없이 신뢰 금지 |
| **OCR Variant(동일 PDF 다른 OCR)** | 판단 불가 | hOCR이 8개 volume 전부 없어 OCR(txt) vs hOCR 비교 자체가 불가능 | Pilot-001과 달리 이번 표본은 OCR variant 비교 사례가 아예 없음 — 향후 hOCR이 있는 다권본이 나오면 재검증 필요 |

**BLOCKER 없음.**

---

## 7. Metadata Validation (Phase 6)

파일: [`authority/pilot/fuller/manifest_pilot.yaml`](../resources/theological_sources/authority/pilot/fuller/manifest_pilot.yaml)

12개 필수 필드(source_id/author_id/work_id/edition_id/volume_id/category/
publication_year/source_type/copyright_status/usage_permission/
citation_policy/tsu_access) 전부를 8개 volume 각각에 채웠다 — 결측 없음.

`source_type`은 Pilot-001에서 이미 지적된 gap(F-P1)이 여기서도 동일하게
재현됨 — `reference`를 잠정 사용했으나 "공개 archive.org PD 스캔본"에
정확히 맞는 값이 여전히 없다(§9에서 재확인, 2회 연속 발견이므로 우선순위
상향 권고).

---

## 8. Reference Integrity Result (Phase 7)

프로그램적 검증 수행(`python3 -c` 스크립트로 5개 YAML 파일의 모든
참조 필드를 전수 대조, 읽기 전용 — 파일 생성/수정 아님, 검증 로직만 실행):

| 방향 | 검사 | 결과 |
|---|---|---|
| Author | `work.author_id` → `authors.yaml` | **PASS** (1/1) |
| Work | `edition.work_id` → `works.yaml` | **PASS** (2/2) |
| Volume | `volume.work_id` → `works.yaml` | **PASS** (8/8) |
| Volume→Edition(추가 검사) | `volume.edition_id` → `editions.yaml` | **PASS** (8/8) |
| Source | `source.volume_id` → `volumes.yaml` | **PASS** (8/8) |
| Manifest 전체 대조 | manifest_pilot.yaml의 author_id/work_id/edition_id/volume_id/source_id 전부 | **PASS** (8/8 entry, 필드당 전수 일치) |

**전체 판정: PASS** — 5단 계층, 총 27개 entity(1+1+2+8+8+8-오타정정:
1 author + 1 work + 2 edition + 8 volume + 8 source + manifest 8건)에
걸친 참조가 전부 무결.

---

## 9. Schema Improvement Suggestions (Phase 8, 제안만 — Schema 수정 안 함)

현재 Schema v2.0.0(수정하지 않음, 관찰만)이 아래를 지원하는지 평가:

| 기능 | 지원 여부 | 근거 |
|---|---|---|
| Multi-volume | **부분 지원** | `edition`(문자열) 필드는 있으나 `volume_id`/`volume_number` 필드가 없음 — 이번 pilot이 `manifest_pilot.yaml`에서 `volume_id`를 확장 필드로 임시 사용해 검증했으나, 정식 스키마에는 없음 |
| Series(연작, 예: 정기간행물 volume+issue) | **미지원** | Baptist Missionary Magazine처럼 volume+issue 조합이 필요한 자료(Audit-002에서 이미 실측된 사례)는 이번 volume_id 하나로는 부족 — `issue_number` 또는 `series_id` 별도 검토 필요 |
| Collection(다권 세트를 하나로 묶는 상위 단위) | **Work가 이미 이 역할** | 이번 pilot에서 Work 엔티티가 "Eight Volumes" 세트 전체를 성공적으로 대표함 — 추가 엔티티 불필요, PASS |
| Archive Collection(예: early_baptist_collection, 1,416파일) | **미지원(규모 불충분)** | Work→Edition→Volume→Source 4단으로는 1,416개 개별 파일을 감당하기 어려움 — Volume 하나가 다시 "batch/folder" 단위로 나뉠 필요가 있어 보이나, 이는 Pilot-001/002 어느 쪽 표본과도 규모가 다름(이번 pilot 범위 밖, [Pilot-001 Report](NAE_METADATA_PILOT_REPORT_001.md) §8 기존 결론 재확인) |

**제안 필드(스키마 수정은 하지 않음, 제안만)**:

```yaml
volume_id: string       # optional, multi-volume 자료에서 필수
volume_number: integer  # optional
issue_number: string    # optional, 정기간행물용(향후 검토)
```

`NAE_METADATA_GOVERNANCE_v1.md` §6 TSU 필수 필드 목록에 `edition_id`가
권장(선택)으로만 되어 있던 것도, 이번 pilot에서 `edition_id`가 Duplicate
Edition 구분에 실제로 핵심 역할을 했으므로 **필수 격상을 재권고**한다
(Plan Review-001 F2와 동일 결론, 재확인 사례 추가).

---

## 10. Recommendation

1. **Authority Model 문서에 "Work 1개 : Edition N개(N≥1)" 관계를 명문화**
   — `NAE_METADATA_GOVERNANCE_v1.md` §5.1 Entity 계층 설명에 이번 실증
   사례(Fuller)를 근거로 추가 권고.
2. **`volume_id`/`volume_number`를 Schema v2.0.0 정식 필드로 추가 검토**
   — 이번 pilot이 확장 필드로 이미 검증했으므로 기술적 리스크는 낮음.
3. **`source_type` enum gap 우선순위 상향** — Pilot-001, Pilot-002 두
   차례 연속 발견. 다음 GOVERNANCE 개정 시 반드시 처리 권고.
4. **`edition_id`를 TSU 필수 필드로 격상** — 이번 pilot이 Edition 구분의
   실질적 중요성을 입증.
5. **정기간행물(volume+issue) 대상 3차 pilot 고려** — Baptist Missionary
   Magazine처럼 이번 모델로 완전히 커버되지 않는 유형이 다음으로 남음.
6. **early_baptist_collection은 계속 별도 sub-plan으로 분리 유지** —
   이번 pilot도 그 판단이 옳았음을 재확인(규모 차이가 명확).

---

## 완료 판정

```
STATUS: PASS WITH CONDITIONS

REFERENCE INTEGRITY: PASS

EDITION MODEL: APPROVED
  (단, "Work:Edition = 1:N" 관계 명문화 조건부 — 문서상 이 관계가
   묵시적으로만 존재했고 이번 pilot으로 실증됨)

VOLUME MODEL: APPROVED

NEXT RECOMMENDATION:
  1) volume_id/volume_number를 Schema v2.0.0 정식 필드로 반영할지 결정
  2) source_type enum gap 해결(Pilot-001/002 2회 연속 발견)
  3) edition_id를 TSU 필수 필드로 격상할지 결정
  4) 정기간행물(volume+issue) 대상 3차 pilot 여부 결정
  5) 위 결정 후에도 전체 Corpus Migration은 별도 승인 필요(이번 pilot의
     목적은 모델 검증이며, Fuller 자료를 실제로 등록하는 것이 아님)
```

---

*RAW 파일 수정/이동, OCR 변경, 전체 Corpus Migration, 기존 Manifest 변경,
TSU/Embedding 생성, Retrieval 변경, Git Commit 전부 수행하지 않음. Fuller
자료를 실제로 등록하지 않았음 — 이번 산출물은 전부 `authority/pilot/fuller/`
검증용 registry이며 실제 파이프라인에서 참조되지 않는다.*
