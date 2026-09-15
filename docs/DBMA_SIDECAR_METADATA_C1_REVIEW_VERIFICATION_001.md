# CUE 대조 검증 — C1 Review 결과 (사이드카 메타데이터)

- 작성자: CUE
- 일자: 2026-09-15
- 대상: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md` (C1 제출 원문)
- 근거: CLAUDE.md "Evidence Classification" — VERIFIED / REPORTED / UNKNOWN 구분,
  및 반복 관측된 C1 보고 정확도 문제(엉뚱한 저장소 감사·수치 날조 전례)

---

## 0. 요약

| C1 항목 | CUE 검증 | 조치 |
|---|---|---|
| 조건 **C1** (빈 문자열 간극, 우선순위 "높음") | ❌ **오진 — 코드·실증으로 반박** | **기각** |
| 조건 **C2** (`source` 검증 가능 형식) | ✅ 타당 | **수용** |
| **Q4** (`metadata_source` 필드) | ✅ 타당 (단 C1 자체 서술에 모순 있음) | **수용, 방식 수정** |
| 조건 **C3** / Q6 (`doc_type` 영향 목록) | ✅ 타당 | **수용** |
| **Q1** | ⚠️ **요청한 질문에 답하지 않음** | **재요청 필요** |
| Q3 핵심 판단 (전사 ≠ 추론) | ✅ 유효한 확인 | 수용 |
| Q5, Q7 | ✅ 타당 | 수용 |

**결론: C1의 YELLOW 판정 자체는 유지하되, 최우선 조건으로 제시된 C1은 성립하지 않는다.**
실제 잔여 조건은 3건이 아니라 **2건(C2, C3) + Q4**이며, 여기에 **미답변 Q1**이 추가된다.

---

## 1. 조건 C1 — 기각 (오진)

### C1의 주장

> `core/extractors.py` 638행: `_extract_pdf_title_author()`가 빈 문자열을 반환하면
> `title=""`가 되고, 이는 `None`이 아님. … 사이드카 로직은 "내장이 None 인 필드에
> 한해서만" 채우므로, `""`는 채워지지 않음.
>
> **해소 방안:** `_extract_pdf_title_author()` (및 `_extract_docx_title_author()`,
> `_extract_epub_title_author()`, `_extract_html_title_author()`)가 빈 문자열을
> 반환할 때 `None`으로 강등해야 합니다.

### 반박 — 요구된 강등은 이미 전 경로에 구현돼 있다

C1이 지목한 4개 함수는 **전부 이미 빈 문자열을 `None`으로 강등한다.**
`.strip() or None` 관용구가 7개 지점 모두에 적용돼 있다.

```
core/extractors.py:116    title  = (meta.get("title")  or "").strip() or None   # PDF
core/extractors.py:117    author = (meta.get("author") or "").strip() or None   # PDF
core/extractors.py:129    title  = (props.title  or "").strip() or None         # DOCX
core/extractors.py:130    author = (props.author or "").strip() or None         # DOCX
core/extractors.py:150    return (str(value) or "").strip() or None             # EPUB (_first_dc_value)
core/extractors.py:184    title  = soup.title.string.strip() or None            # HTML
core/extractors.py:189    author = (tag.get("content") or "").strip() or None   # HTML
```

`"" or None` → `None`, `"   ".strip() or None` → `None`. 빈 문자열은 **반환될 수 없다.**

### 실증

```python
# 빈 title + 빈 author meta 를 가진 HTML
open(p,'w').write('<html><head><title>   </title>'
                  '<meta name="author" content=""></head><body>x</body></html>')
_extract_html_title_author(p)
```
```
빈/공백 메타데이터 HTML → (None, None)
```

공백만 있는 `<title>`과 빈 `content` 모두 `None`으로 강등됐다. C1이 상정한
`title=""` 상태는 이 코드에서 **발생하지 않는다.**

### 원인 추정

C1은 **호출부(638행)만 읽고 함수 본문(116-117, 129-130, 150, 184, 189행)을 읽지
않았다.** C1이 인용한 행 번호 자체는 정확하므로(638행, 624행 docstring 모두 실재
확인), 저장소·커밋을 잘못 본 사고는 아니다. 읽기 범위의 문제다.

### 다만 — C1이 스치듯 언급한 진짜 문제는 남는다

C1은 같은 항목에서 *"`title`/`author` 필드도 쓰레기 값(빈 문자열, **인코딩 깨짐 등**)일
수 있습니다"* 라고 썼다. 빈 문자열 부분은 위와 같이 기각되지만, **비어 있지 않은
쓰레기 값**(`Untitled`, `Microsoft Word - doc1.doc`, 제작 도구명, mojibake)은
여전히 `None`이 아니므로 사이드카를 이긴다. 이것은 요청서 Q2가 원래 물었던 바로 그
문제이며, **C1은 이 부분에 답하지 않고 빈 문자열 쪽으로 논점을 옮겼다.**

→ **UNKNOWN으로 남음.** 재요청 대상(§4).

---

## 2. 조건 C2 — 수용 (`source` 검증 가능 형식)

타당하다. 현재 `"source": "archive.org original.pdf docinfo"`는 자유 텍스트라
사후 감사 시 진위를 기계적으로 가릴 수 없다.

다만 C1이 제시한 중첩 JSON 객체는 스키마 v1의 "최소" 원칙 대비 과하다.
**구분자 기반 형식**을 채택한다(C1도 대안으로 허용).

```json
{ "source": "archive.org|lecturestomystud1877spur|pdf_docinfo" }
```

형식: `<제공처>|<식별자>|<필드>`. 3단 구분자를 파서가 검증하고, 위반 시 사이드카
전체를 무시(경고 로그)한다. `lecturestomystud1877spur`는 실제 PDF docinfo의
`keywords`에 들어 있는 archive.org 식별자이므로 전사 가능하다(VERIFIED —
`docs/DBMA_LECTURES_PDF_TEXT_QUALITY_MEASUREMENT_001.md` 측정 시 확인).

---

## 3. Q4 — 수용하되 C1 서술의 모순을 정정

C1은 옵션 (B)를 "registry 변경 없이 runtime 확인"으로 정의해놓고, 권고에서는
*"TSU record에 `"metadata_source": "sidecar"`를 기록하면 됩니다"* 라고 썼다.
필드를 기록하는 것은 (B)가 아니라 (A)의 축소판이며, 두 서술은 양립하지 않는다.

**CUE 채택안:** 필드를 기록하되 **registry가 아니라 TSU record에만** 둔다.
- registry(`identity_registry.py:163-164`) 스키마 무변경 → Metadata Model 변경 회피
- TSU record에 `metadata_source` 선택 필드 추가 (`embedded` | `sidecar`)
- 값이 없으면 기존 동작과 동일(전방 호환)

C1의 결론(TSU record 쪽에 두어 범위를 줄인다)은 타당하므로 채택한다. 서술 모순은
결론에 영향을 주지 않는다.

---

## 4. Q1 — 답변되지 않음 (재요청 필요)

**요청서 §3 Q1 원문:**

> **Metadata Model 변경 범위 판정** — D-2의 3키 스키마가 기존 Metadata Model
> (`DocumentContext`, `identity_registry.py:163-164`, `tsu_builder.py:382-383`)에
> **필드를 추가하지 않고** 기존 `title`/`author`를 채우기만 하는 것이 맞는가?
> 그렇다면 이것은 "Model 변경"인가 "Model 무변경 + 새 데이터 소스 추가"인가?
> 후자라면 C1 Review 트리거 자체가 과잉이었는지도 함께 판정 바란다.

**C1이 Q1로 답한 내용:** `.meta.json` 확장자 충돌 방지(= 요청서 D-1)의 타당성.

**→ 다른 질문에 답했다.** D-1은 검토 질문이 아니라 제안 설계 항목이다.

이 질문이 중요한 이유: 본 검토를 발동시킨 트리거가 "Metadata Model 변경"이었다.
Q1이 미해결이면 **이 검토가 필요했는지, 향후 유사 변경에 C1 Review가 필요한지**의
판단 기준이 서지 않는다. 거버넌스 질문이므로 CUE가 자답하지 않는다.

---

## 5. 갱신된 게이트

GREEN 전환에 필요한 잔여 항목:

```md
- [ ] C2  source 를 `<제공처>|<식별자>|<필드>` 형식으로 강제 + 파서 검증   (설계 반영, 즉시 가능)
- [ ] Q4  TSU record 에 metadata_source 선택 필드 (registry 무변경)        (설계 반영, 즉시 가능)
- [ ] C3  doc_type 변경 영향 문서 목록 산출 → HQ 승인                      (구현 전 산출물)
- [ ] Q1  Metadata Model 변경 여부 판정 — C1 재요청                        (거버넌스, 미해결)
- [x] C1  빈 문자열 간극 — 기각 (이미 구현됨, 실증 완료)
- [ ] Q2-잔여  비어 있지 않은 쓰레기 값 처리 — C1 재요청                   (미해결)
```

**착수 조건 불변:** Evidence Before Promotion Rule에 따라 GREEN + HQ 승인 전까지
스텁·스키마·데이터를 포함한 어떤 선행 구현도 하지 않는다. 본 검증 문서 작성으로
코드·코퍼스·registry는 변경되지 않았다.

---

## 6. C1 재요청 사항 (2건)

1. **Q1 재답변** — 요청서 §3 Q1 원문에 답할 것. D-1이 아니라 Metadata Model
   변경 범위 판정이다.
2. **Q2 잔여분** — 빈 문자열이 아니라 **비어 있지 않은 쓰레기 내장 값**
   (`Untitled`, 제작 도구명, mojibake)이 정확한 사이드카 값을 이기는 경우를
   어떻게 다룰지. 판정 기준이 필요하다면 그 기준은 무엇인가. 답변 전
   `core/extractors.py` 108-190행 **함수 본문을 읽을 것**(조건 C1 오진의 원인).

---

## 7. 기록

```
STATUS:      C1 결과 접수 · 대조 검증 완료
판정 변화:   YELLOW 유지 (조건 구성이 바뀜 — C1 기각, Q1·Q2잔여 추가)
Changed:     문서 2건만 (C1 원문 보존 + 본 검증서). 코드·코퍼스·registry 무변경
Tests:       해당 없음 (검증은 기존 코드 읽기 + 실증 1건)
Next:        C1 재요청 2건 → 회신 후 설계 확정 → HQ 승인 → 구현 착수
```
