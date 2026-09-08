# Fuller Canonical 재검증 + Provenance 한계 확정 (F1) — C1 산출물

- 발급: C1 (독립 검증)
- 일자: 2026-09-08
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine` (worktree 아님)
- venv: `~/envs/dbma311`

---

## git status / HEAD

```
e38a810c6f4c40050656072c12f74cd4a0f54ff5
```

`git status --porcelain` = empty (tracked 파일 수정 없음). Mutation 0 준수.

---

## T1. Canonical 존재·무결성 (8권)

### 결과: ✅ PASS (8/8)

| Vol | canonical.json | canonical.txt | normalize_report.json | JSON parse | status | paragraph_count 일치 |
|-----|---------------|---------------|----------------------|------------|--------|---------------------|
| 01 | ✅ 2,765,539B | ✅ 954,514B | ✅ 596B | OK | ok | 2,250 = 2,250 |
| 02 | ✅ 2,450,617B | ✅ 858,772B | ✅ 597B | OK | ok | 2,040 = 2,040 |
| 03 | ✅ 2,978,041B | ✅ 1,029,275B | ✅ 600B | OK | ok | 2,526 = 2,526 |
| 04 | ✅ 2,760,809B | ✅ 945,300B | ✅ 597B | OK | ok | 2,268 = 2,268 |
| 05 | ✅ 2,317,927B | ✅ 768,064B | ✅ 595B | OK | ok | 1,890 = 1,890 |
| 06 | ✅ 2,606,667B | ✅ 843,002B | ✅ 597B | OK | ok | 2,756 = 2,756 |
| 07 | ✅ 2,779,268B | ✅ 949,732B | ✅ 595B | OK | ok | 2,103 = 2,103 |
| 08 | ✅ 3,239,455B | ✅ 1,085,983B | ✅ 598B | OK | ok | 2,769 = 2,769 |

**판정**: 8권 모두 canonical.json / canonical.txt / normalize_report.json 존재, JSON 파싱 성공, status=ok, paragraph_count 일치.

---

## T2. normalize_report 8권 집계표

### 결과: ✅ 완료 (수치 = 파일 원문)

| Vol | pipeline_version | source | page_count | characters_after | paragraph_count | heading_count | sentence_count | verse_paragraph_count | quote_count | footnotes_extracted | scripture_references_found | headers_footers_removed | page_numbers_removed |
|-----|-----------------|--------|------------|-----------------|-----------------|---------------|----------------|----------------------|-------------|---------------------|---------------------------|------------------------|---------------------|
| 01 | 2.0.0 | ocr | **1** | 953,307 | 2,250 | 137 | 6,304 | 0 | 0 | 0 | **2** | 32 | 2 |
| 02 | 2.0.0 | ocr | **1** | 857,805 | 2,040 | 144 | 5,101 | 0 | 2 | 0 | **3** | 3 | 62 |
| 03 | 2.0.0 | ocr | **1** | 1,028,129 | 2,526 | 184 | 6,527 | 24 | 11 | 0 | **⚠️ 0** | 0 | 31 |
| 04 | 2.0.0 | ocr | **1** | 944,284 | 2,268 | ⚠️ 395 | 6,478 | 2 | 1 | 0 | **3** | 3 | 79 |
| 05 | 2.0.0 | ocr | **1** | 767,156 | 1,890 | ⚠️ 284 | 6,215 | 1 | 0 | 0 | **1** | 1 | 12 |
| 06 | 2.0.0 | ocr | **1** | 841,580 | 2,756 | ⚠️ 359 | 5,949 | 8 | 17 | 0 | **1** | 1 | 82 |
| 07 | 2.0.0 | ocr | **1** | 949,051 | 2,103 | ⚠️ 77 | 7,033 | 1 | 2 | 0 | **⚠️ 0** | 0 | 27 |
| 08 | 2.0.0 | ocr | **1** | 1,084,597 | 2,769 | 163 | 7,996 | 0 | 1 | 0 | **1** | 1 | 31 |

**이상치 표시**:
- ⚠️ `page_count=1` (8/8 전량) — page-level citation 불가
- ⚠️ `scripture_references_found=0` (Vol.03, Vol.07) — T3에서 원인 규명
- ⚠️ `heading_count` 편차: Vol.04=395, Vol.05=284, Vol.06=359 (정상 범위 77~284 초과)

---

## T3. scripture_references_found=0 원인 규명

### 결과: ⚠️ 추출기 누락 (원문 특성 아님)

#### 실측 grep 카운트 (canonical.txt 기준)

| Vol | KR 패턴(한글 성서명) | EN 패턴(영문 로마자 숫자) | 합계 실제 | normalize_report 값 | 불일치 |
|-----|----------------------|--------------------------|-----------|--------------------|--------|
| 01 | 0 | **196** | **196** | 2 | ⚠️ -194 |
| 02 | 22 | 101 | 123 | 3 | ⚠️ -120 |
| 03 | 23 | **56** | **79** | **0** | ⚠️ -79 |
| 04 | 24 | 33 | 57 | 3 | ⚠️ -54 |
| 05 | 30 | 64 | 94 | 1 | ⚠️ -93 |
| 06 | 17 | 44 | 61 | 1 | ⚠️ -60 |
| 07 | 35 | **39** | **74** | **0** | ⚠️ -74 |
| 08 | 48 | 130 | 178 | 1 | ⚠️ -177 |

#### Vol.03/Vol.07 실제 성구 인용 샘플 (canonical.txt에서 grep)

```
# Vol.03 samples:
Rev. xvii. 12
Rom. ii. 12
Rev. xxi. 3
Acts xvi. 30
Dan. viii. 3
Isa. xiii. 2
Jer. iv. 19
Luke xxiii. 8

# Vol.07 samples:
Acts xi. 24
Hag. i. 2
Rev. xiv. 13
Heb. v. 12
Gal. vi. 7
Jer. xxix. 7
Psa. xl. 6
```

#### Vol.01 실제 카운트 대조

```
# canonical.txt grep 결과:
EN 로마자 숫자 패턴: 196개 매칭 (John i. 12, Psa. cxviii. 22, Acts xiii. 46 등)
normalize_report scripture_references_found: 2 (Ephes 1:4, Jer 6:8)
```

#### 근본 원인 (추출기 코드 분석: `NAE/pipeline/canonical/annotate.py`)

**원인 1: 한글 성서 명칭 완전 미지원**
- `_ARABIC_REF` 패턴: `\b(?P<book>(?:[1-3]\s)?[A-Z][a-z]+)\.?\s+(?P<chapter>\d{1,3}):...`
- `_LEGACY_REF` 패턴: `\b(?P<book>(?:[1-3]\s)?[A-Z][a-z]+)\.?\s+(?P<chapter>[ivxlcdm]+)...`
- 둘 다 `[A-Z][a-z]+` (영문 대소문자)만 book 이름으로 허용 → 한글 "롬", "요", "행" 등 **절대 매칭 안 됨**

**원인 2: 로마자 숫자 매핑 불완전**
- `_ROMAN_MAP` 사전이 최대 "xxviii"(28)까지만 매핑
- "cxviii"(118), "xl"(40) 등은 regex는 일치하지만 lookup 실패 → `None` 반환

**원인 3: OCR 노이즈 간섭**
- 실제 텍스트에서 "Rom. ii." 다음에 "+" 등 OCR 노이즈가 와서 verse 숫자가 가려짐
- 예: `* Rom. ii. + 2Kiiig3Xvii.\n\nVol.`

#### 판정

**추출기 누락**. Vol.03/Vol.07의 원문이 성구 인용을 포함하지 않는 것이 아니라, 추출기가 로마자 숫자 + 영문 책 이름 패턴만 지원하여 실제 성구 인용의 대부분을 놓치고 있다. Vol.01도 리포트값 2 vs 실제 ~196개로 **추출기 신뢰도가 심각하게 낮음**.

**재-정제(re-normalize) 필요성**: scripture extraction 정확도 개선을 위해서는 extract.py/annotate.py 수정 후 재-정제가 필요하지만, 이는 본 F1 Task Order 범위 밖 (F0/Amendment 결정 사항).

---

## T4. Citation locator 규칙 제안

### page_count=1 확정

8권 모두 `page_count = 1` (normalize_report.json 실측). page-level citation 불가.

### 기존 TSU 레코드 필드

```
TSU Vol.01 sample:
  page=1, paragraph=19, sentence=0
  heading_path=N/A (누락)
```

### canonical.json 구조

```
Vol.01: total=2,250 paragraphs, headings=137 (real=123), prose=2,113
heading index=0~284 범위, type={heading, prose, quote, verse}
```

### 제안: `work_id + heading_path + paragraph_index`

```
locator = {
  "work_id": "fuller_andrew_works_vol01",
  "heading_path": ["CHAPTER III", "OF THE ATONEMENT"],  # canonical.json heading text 경로
  "paragraph_index": 42  # canonical.json paragraphs[].index
}
```

**매핑**:
- TSU `page` (전부 1) → 사용 불가
- TSU `paragraph` → canonical.json `paragraphs[].index` 와 매핑
- TSU `sentence` → 해당 paragraph 내 `sentences[].sentence_index` 와 매핑
- `heading_path` → paragraph index 이전의 마지막 heading text들을 경로로 구성

**재현성**: 같은 claim → 같은 paragraph_index → 같은 heading_path → 같은 locator. canonical.json은 결정적 출력이므로 재현 보장.

**한계**: heading_count 편차(Vol.04=395 등)로 heading_path가 노이즈 포함 가능. F0 재-정제 시 heading 품질 개선 필요.

---

## T5. Disclosure 문구 초안 (KR + EN)

### 한국어

> **출처 고지**
> 
> 이 claim은 Andrew Fuller, *The Works of the Rev. Andrew Fuller, in Eight Volumes* (archive.org 공개 도메인 OCR 원본)에서 추출되었습니다.
> 
> - **OCR 출처**: page-level provenance 없음 (page_count=1). citation은 heading/paragraph 기반 locator로 대체됩니다.
> - **신뢰도**: 모델 self-report 값이며 교정(uncalibrated)되지 않았습니다.
> - **생성 모델**: `my-theology-bot-v2:latest`
> - **권한 클래스**: `historical_witness` (역사적 증언 — scholarly citation certification이 아님)
> - **성구 인용**: 추출기 한계로 일부 성구 참조가 누락되었을 수 있습니다.

### English

> **Provenance Notice**
> 
> This claim was extracted from Andrew Fuller, *The Works of the Rev. Andrew Fuller, in Eight Volumes* (public-domain OCR original via archive.org).
> 
> - **OCR source**: No page-level provenance available (page_count=1). Citations use heading/paragraph-based locator instead.
> - **Confidence**: Model self-report value; uncalibrated.
> - **Generation model**: `my-theology-bot-v2:latest`
> - **Authority class**: `historical_witness` (historical witness — not a scholarly citation certification)
> - **Scripture references**: Some scripture references may be missed due to extractor limitations.

### 기존 admission record rationale와의 정합

8개 admission record (`BAP-MISS-FULLER-VOL01`–`VOL08`)의 rationale에 이미 다음 사항이 명시됨:
- `source=ocr, page_count=1 (no page-level provenance)`
- `scripture-reference detection limited/volume-dependent`
- `authority_class: historical_witness`

본 disclosure 문구는 기존 rationale의 내용을 UI 노출용으로 구조화한 것일 뿐, 새로운 주장을 포함하지 않음. 정합 ✅.

---

## Next

1. **F0/F2**: scripture extraction 정확도 개선을 위한 re-normalize 필요 여부 결정 (F0/Amendment)
2. **F3**: David의 Vol.01 human review 착수 (본 F1 GREEN 후)
3. **C1 Review**: TSU pipeline 진입 전 C1 Review 요청 (P-4 게이트)
4. **citation locator 구현**: F5 색인 단계에서 `work_id + heading_path + paragraph_index` 반영

---

## Mutation 0 증명

```
git status --porcelain = (empty)
```

신규 문서 1개 (`NAE_FULLER_CANONICAL_VERIFICATION_001.md`) 외 무변경.