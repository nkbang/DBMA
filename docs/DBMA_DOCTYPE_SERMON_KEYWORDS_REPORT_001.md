# 설교 유형 영어 키워드 추가 Build Report 001

- 작성자: CUE
- 일자: 2026-09-15
- 대상: `core/document_identity.py::_DOC_TYPE_KEYWORDS`
- 결과: **STATUS = 성공**

---

## 1. 문제

5개 문서 유형 중 **`설교`만 영어 키워드가 0개**였다.

| 유형 | 한국어/한자 | 영어 |
|---|---:|---|
| 주석 | 2 | 1 — `commentary` |
| **설교** | 5 | **0** |
| 사전 | 3 | 2 — `dictionary`, `encyclopedia` |
| 논문 | 4 | 1 — `abstract` |
| 조직신학 | 1 | 1 — `systematic theology` |

무료 배포 기본 코퍼스가 전량 영어 퍼블릭 도메인 설교이므로 배포 대상 전체가
`기타`로 떨어지는 직격 결함이었다(`docs/DBMA_DOCTYPE_IMPACT_REPORT_001.md` §4).

---

## 2. 키워드 선정 — 실측으로 골랐다

후보를 넣어보고 고른 것이 아니라, **두 개의 실데이터 집합에 돌려 오탐/재현율을
측정한 뒤** 결정했다.

- 오탐 검증셋: 백업 코퍼스 **122개 출처**(주석·조직신학·사전·선교학 포함)
- 재현율 검증셋: archive.org 설교 **67종**의 PDF docinfo title

### 2.1 후보 조합 비교 (백업 122건 기준 오탐)

| 조합 | 재분류 | 오탐 |
|---|---:|---|
| A. `sermon`+`pulpit`+`preaching`+`homily` | 2건 | **2건** |
| B. `sermon`+`pulpit`+`homily` | 1건 | **1건** |
| **C. `sermons`+`pulpit`+`homily` (채택)** | **0건** | **0건** |
| D. `pulpit`+`homily` | 0건 | 0건 (재현율 손실) |

### 2.2 `preaching` 제외 — 일반 서술문에 걸린다

백업 코퍼스 `7. The Fundamentals.pdf`(선교 고전 모음집)에서 실제 매칭된 문장:

> "there have been great awakenings **without much preaching**, and there have
> been great awakenings with absolutely no music."

장르 신호가 아니라 평범한 산문이다. 나아가 `preaching`은 **설교를 다룬 책**까지
설교집으로 만든다 — Dargan *A History of Preaching*(2권), Broadus *Lectures on
the History of Preaching*은 설교학·설교사이지 설교집이 아니다. 제외로 정확히
걸러진다(실측 확인).

### 2.3 단수 `sermon` 제외 — 출판사 시리즈 광고에 걸린다

백업 코퍼스 `Hebrews … (Preaching the Word)`(Kent Hughes 주석 시리즈 한 권)에서
실제 매칭된 위치:

> "john | david l. allen revelation | james m. hamilton jr. **the sermon on the
> mount** | r. kent hughes preaching the word hebrews"

책 앞부분에 실린 **같은 시리즈 다른 권 광고 목록**이다. 주석서가 설교로
오분류됐다.

**복수형만 써도 손실이 없음을 확인했다** — archive.org 설교 67종 중 title에
`sermons` 복수 포함 **12건**, 단수 `sermon`만 포함 **0건**.

### 2.4 채택안

```python
"설교": ["설교", "말씀", "제목:", "본문:", "본문 말씀:", "sermons", "pulpit", "homily"]
```

백업 122개 출처 기준 **오탐 0건**.

---

## 3. 재현율

archive.org 설교 67종을 **title만으로** 분류 시 **38/67건**이 `설교`로 잡힌다.

이 값은 **하한**이다 — 실제 처리 경로에서는 본문 앞 2000자도 haystack에 들어가므로
더 높다(현 코퍼스의 *Till He Come*이 그 사례: title에는 신호가 없고 본문의
`Pulpit`으로 분류됨).

미분류 29건을 확인한 결과 **상당수가 올바른 제외**다:

| 미분류 자료 | 판정 |
|---|---|
| Dargan *A History of Preaching* ×2 | ✅ 올바름 — 설교사 저작 |
| Broadus *Lectures on the History of Preaching* | ✅ 올바름 — 설교학 |
| Spurgeon *Commenting and Commentaries* | ✅ 올바름 — 주석 서지 |
| Keach *Tropologia* | ✅ 올바름 — 성경 은유 사전류 |
| Maclaren *Expositions of Holy Scripture* ×17 | ⚠️ 본문 반영 시 재측정 필요 |

Maclaren 강해 17권은 title에 신호가 없어 title-only 측정에서 빠졌다. 실제 적재
시 본문으로 잡히는지 별도 확인이 필요하다(현재 미적재 자료).

---

## 4. 변경 내역

| 파일 | 내용 |
|---|---|
| `core/document_identity.py` | `설교` 키워드에 `sermons`·`pulpit`·`homily` 추가 + 선정 근거 주석 |
| `tests/test_doc_type_english_sermon_keywords.py` | 신규 14건 |
| `scripts/doctype_impact_report.py` | `--keywords-json` 옵션 추가 — 키워드 표 변경의 재분류 영향 산출 |

### 테스트 구성

- 언어 커버리지 불변식 — **어떤 유형도 영어 키워드 0개로 남지 않는다**(이번 결함의 근본 형태를 고정)
- 진양성 — 영어 설교 title/본문 분류
- **오탐 방지 — §2.2·§2.3에서 실제 관측된 두 문장을 그대로 고정**
- 설교학·설교사 저작이 설교로 분류되지 않음
- 기존 동작 보존 — 주석 우선순위, 한국어 키워드, 무신호 시 `기타` 폴백

작성 중 테스트 1건이 실패했는데 **코드가 아니라 테스트가 틀렸다** — *Till He
Come*이 title로 분류된다고 잘못 가정했고, 실제로는 본문의 `Pulpit`이 판정한다.
그 구분을 명시한 테스트로 교체했다(`test_till_he_come_classifies_via_body_not_title`).

---

## 5. 검증

```
신규 테스트    14 passed
회귀           230 passed / 2 failed
```

실패 2건(`test_m2_source_registry_governance.py`)은 **사전 존재**하며 본 변경과
무관하다 — `NAE/corpus/raw/`가 `.gitignore` 대상이라 일부 원본이 이 머신에 없는
환경 갭으로, 앞서 `git stash` 대조로 확인했다
(`docs/DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md` §4).

---

## 6. 적용 범위 — 기존 registry는 아직 그대로다

`doc_type`은 **처리 시점에 계산돼 registry에 저장**된다. 따라서 이번 변경은
**다음 처리부터** 반영되고, 이미 등록된 4건은 재처리 전까지 `기타`로 남는다.

재처리 시 예상되는 변화(`scripts/doctype_impact_report.py --keywords-json` 산출):

| 문서 | 현재 | 재처리 후 |
|---|---|---|
| `Spurgeon_Till_He_Come.txt` | 기타 | **설교** |
| `Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol01.txt` | 기타 | **설교** |
| `Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol02.txt` | 기타 | **설교** |
| `Spurgeon_Lectures_to_My_Students.txt` | 기타 | 기타 (설교학 — 올바른 유지) |

**3건 전부 개선 방향이며 퇴행은 없다.** 다만 재처리는 registry·TSU 변경을
수반하므로 HQ 승인 전까지 수행하지 않는다.

---

## 7. 기록

```
STATUS:      성공
Changed:     core/document_identity.py, tests/test_doc_type_english_sermon_keywords.py (신규),
             scripts/doctype_impact_report.py (--keywords-json 추가)
Tests:       14 passed
Regression:  230 passed / 2 failed (사전 존재, 본 변경과 무관)
Architecture: ADR-001 무위반 — 검색 경로·Retrieval Engine 무변경
             Metadata Model 무변경 — 기존 doc_type 필드의 분류 규칙만 보강
Git:         commit + push (dev/dbma-engine)
Next:        기존 4건 재처리 여부 HQ 결정 (§6)
             Maclaren 강해 17권 본문 기반 재현율 확인 (적재 시)
```
