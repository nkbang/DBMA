# 기본 코퍼스 적재 Build Report 001

**작성일:** 2026-09-15
**작업:** 퍼블릭 도메인 기본 코퍼스 적재 (2026-09-15 리셋 이후 첫 적재)
**결과:** STATUS = 성공

---

## 1. 적재 결과

| 출처 | TSU | 성격 |
|---|---:|---|
| Spurgeon Metropolitan Tabernacle Pulpit Vol02 | 2,637 | 설교 원문 |
| Spurgeon Metropolitan Tabernacle Pulpit Vol01 | 2,601 | 설교 원문 |
| Spurgeon, *Till He Come* | 609 | 성찬 설교·묵상 |
| Spurgeon, *Lectures to My Students* | 533 | 설교학 강의 |
| **합계** | **6,380** | 출처 4건 |

`source_document_count: 4` · `dataset_records: 6380` · 청킹 1200/120

---

## 2. 자료 출처와 저작권

**출처:** `~/NAE_CORPUS_RAW/raw/archive_org/sermons/` (Archive.org 수집분, 기존 보유)
**신규 다운로드 없음** — 로컬에 이미 확보된 자료만 사용.

C. H. Spurgeon(1834–1892) 저작으로 **퍼블릭 도메인**이다. 원 스캔본에 Google
디지털화 고지가 포함된 판본이 있으나, 이는 스캔 이미지에 대한 것이며 본문
텍스트의 퍼블릭 도메인 지위에는 영향을 주지 않는다.

`docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` §2.2 판정과 일치 — **무료 배포 시 동봉 가능**.

같은 경로에 즉시 추가 가능한 퍼블릭 도메인 자료가 63건 더 있다
(Spurgeon MTP 총 40여 권, NPSP 6권, Maclaren *Expositions* 17권,
Whitefield *Works* 4권, Broadus, Dargan, Keach).

---

## 3. 처리 경로

UI(`ui/pages/processing.py`)와 **동일한 호출 경로**를 헤드리스로 재현했다 —
`build_converter` → `build_splitter` → `process_batch` → `reconcile_pending()`.
새 경로를 만들지 않았으므로 ADR-001(One Pipeline / One Retrieval Engine) 무위반.

```
[extract]  텍스트 추출          → 4건 성공
[noise]    노이즈 점검          → score 12.5~14.0
[chunk]    청킹                 → 6,380 chunks
[validate] 청크 검증            → valid=True, filtered 0, encoding_err 0
[reconcile] registry → TSU → 색인 → reconciled 4, failed 0
```

색인 재생성 확인: `tantivy_index/`, `bible_index.sqlite3` 모두 재작성됨.

---

## 4. 검증

**검색 스모크 (PASS)**

| 질의 | 결과 |
|---|---|
| `prayer of the pastor` | 3건 반환, 본문 적합 |
| `the Lord's supper communion` | 3건 반환, 마태복음 26:30 성찬 본문 포함 |
| `설교자의 기도` (한국어) | 3건 반환 — **한국어 질의 → 영어 코퍼스 교차 검색 동작 확인** (bge-m3 다국어) |

---

## 5. 발견된 문제 (후속 조치 필요)

### 5.1 인용 메타데이터가 여전히 비어 있음 — B-3 재확인

신규 적재분 6,380건 전수 검사 결과 `title`·`author`·`themes`·`verse_mapping`이
**모두 비어 있다.**

이것이 중요한 이유: 종전에는 이 결함을 "옛 코퍼스의 데이터 오염"으로 볼 여지가
있었으나, **깨끗한 상태에서 새로 적재해도 동일하게 재현되었다.** 따라서
**데이터 문제가 아니라 파이프라인 결함이 확정**되었다.

`INSTALL.md` §7의 "각 답변에는 author, source_title, evidence_confidence가
포함되어 출처를 확인할 수 있습니다"는 현재 사실과 다르다.

### 5.2 문서 유형 분류 실패

4건 모두 `doc_type = "기타"`로 분류되었다. 스펄전 설교집이 "설교"로 인식되지
않는다. `설교 리뷰` 페이지의 후보 목록 로직이 `doc_type`에 의존하므로 영향이 있다.

### 5.3 영어 코퍼스 / 한국어 사용자

기본 코퍼스가 전량 영어다. 교차 언어 검색은 동작하나, 한국어 설교문 생성 시
영어 자료를 인용하게 된다. 한국어 퍼블릭 도메인 신학 자료 확보는 별도 과제다.

---

## 6. 배포 영향

`docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` §6 차단 항목 변화:

| # | 항목 | 변화 |
|---|---|---|
| B-1 | 빈 코퍼스에서 근거 없는 설교 생성 | **위험 완화** — 코퍼스가 비어 있지 않게 됨. 다만 자료 0건 시 생성 차단 로직 자체는 여전히 필요 |
| B-3 | 인용 메타데이터 null | **원인 확정** — 파이프라인 결함으로 재분류 (§5.1) |

---

## 7. 다음 조치

- [ ] §5.1 메타데이터 추출 결함 수정 (배포 차단 항목)
- [ ] §5.2 `doc_type` 분류에 설교 유형 인식 추가
- [ ] 기본 코퍼스 범위 확정 — 현 4건 유지 / Maclaren·Whitefield 등 확장 여부
- [ ] 자료 0건일 때 설교 생성 차단 (B-1)

---

## 8. 기록

```
STATUS:      성공
Changed:     data/RAW/ (+4), data/제련완성본/ (신규 산출물), output/bench/ (TSU·색인 재생성)
             ※ 전부 .gitignore 범위 — 추적 변경 없음
Tests:       검색 스모크 3건 PASS
Regression:  미실행 (데이터 적재, 코드 무변경)
Git:         본 문서만 커밋
Next:        §7
```
