# Lectures PDF 텍스트 품질 실측 보고 001

**작성일:** 2026-09-15
**목적:** `DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md` §5 선택지 (A) "원본 PDF에서 재적재"의 타당성 판정
**대상:** Spurgeon, *Lectures to My Students* (archive.org, 210쪽, 13.2MB)
**결론:** **(A) 기각** — PDF 재적재는 텍스트 품질을 크게 악화시킨다

---

## 1. 측정 방법

두 텍스트를 동일 조건으로 비교했다.

| 비교 대상 | 출처 |
|---|---|
| **현재 적재본** | `ocr.txt` (archive.org OCR 산출물) |
| **PDF 재적재 후보** | `original.pdf` → `core.extractors.extract_text_from_file()` (프로덕션 경로, PDF 후처리 포함) |

지표:
- **사전 일치율** — 추출 영단어 토큰 중 `/usr/share/dict/words`(표제어 234,456) 일치 비율
- **프로젝트 noise score** — `core.utils.calculate_noise_score()` (파이프라인이 실제 쓰는 스코어)

---

## 2. 결과

| 지표 | ocr.txt (현행) | PDF 추출 | 판정 |
|---|---:|---:|---|
| 글자 수 | 560,528 | 444,334 | PDF가 20.7% 적음 |
| 영단어 토큰 | 85,564 | 56,817 | PDF가 33.6% 적음 |
| **사전 일치율** | **90.2%** | **57.2%** | **-32.9%p** |
| 잡토큰(문자+숫자 혼합) | 0.13% | 0.20% | |
| **프로젝트 noise score** | **10.9** | **27.0** | **2.5배 악화** |
| 추출 시간 | — | 16.4초 | 속도는 문제 아님 |

---

## 3. 원인 — 단어 경계 소실

PDF 텍스트 레이어에서 **단어가 서로 붙어 있다.** 실제 추출 결과:

```
...and St. Vedast, and St. Ethelburga, andallthe restof them, andtryto
findnew saints amongthe sinnerswhoare perishingfor lackof knowledge.

Ihave known street preaching in London remarkably blestto persons whose
characterand condition would quite preclude their having been foundina
placeof worship.
```

`andallthe`, `restof`, `andtryto`, `findnew`, `amongthe`, `sinnerswhoare`,
`perishingfor`, `lackof`, `Ihave`, `blestto`, `characterand`, `foundina`,
`placeof` — 전부 한 토큰으로 붙었다.

PDF 메타데이터상 producer가 `Recoded by LuraDocument PDF v2.28`이다. 이 재인코딩
과정에서 글자 간격 정보가 손실돼 텍스트 레이어의 공백이 사라진 것으로 보인다.

**기존 후처리로 복구되지 않는다.** `core.extractors._fix_ocr_word_splits()`는
*잘린* 단어(`know- ledge`)를 잇도록 설계돼 있고, *붙은* 단어를 가르는 기능은
없다. 위 수치 57.2%는 프로젝트의 PDF 후처리를 **모두 거친 뒤**의 값이다.

---

## 4. 재적재 시 예상 피해

단어 경계 소실은 검색 품질에 직접 타격이다.

- **BM25** — `sinnerswhoare`는 사전에 없는 단일 토큰이 되어 `sinners` 질의에 걸리지 않는다. 후보 생성 단계에서 해당 문단이 아예 탈락한다.
- **임베딩(bge-m3)** — 미지 토큰이 서브워드로 쪼개지며 문장 의미 표현이 왜곡된다.
- **인용 표시** — 목회자에게 보이는 인용문에 `andallthe restof them`이 그대로 노출된다.

즉 **메타데이터(title/author)를 얻는 대가로 본문 검색 가능성을 잃는 거래**이며, 수지가 맞지 않는다.

---

## 5. 대안 점검 — hocr.html

같은 폴더의 `hocr.html`(12.6MB, ABBYY FineReader hOCR)을 메타데이터 소스로
검토했으나 **부적합**하다.

```html
<title></title>
<meta name="ocr-system" content="LuraDocument XML Exporter for ABBYY FineReader" />
```

`<title>`이 비어 있고 author 메타 태그도 없다. 2026-09-15 EPUB/HTML 메타데이터
추출 수정으로 HTML 경로가 열렸으나, 이 파일에는 읽을 메타데이터 자체가 없다.

---

## 6. 결론 및 권고

| 선택지 | 판정 |
|---|---|
| (A) 원본 PDF 재적재 | **기각** — 사전 일치율 90.2% → 57.2%, noise 10.9 → 27.0 |
| hocr.html 경유 | **기각** — 메타데이터 부재 |
| **(B) 사이드카 메타데이터** | **권고** — 텍스트 품질 유지 + 메타데이터 확보를 동시에 달성하는 유일한 경로 |
| (C) 현행 유지 | 차선 — 인용 표기 공백 존속 |

**(B) 권고 근거**

`ocr.txt`의 텍스트 품질(사전 일치율 90.2%)은 이미 양호하다. 문제는 오직
"`.txt`에는 내장 메타데이터가 없다"는 형식의 한계뿐이다. 그렇다면 텍스트는
그대로 두고 메타데이터만 파일 옆에 두는 방식이 정확히 이 문제만 해결한다.

또한 archive.org **원본 PDF의 docinfo에 실제 서지정보가 존재**하므로,
사이드카 내용을 지어낼 필요가 없다 — 같은 자료의 다른 파일에서 그대로 옮기면
된다. "추론하지 않는다"(SPRINT17-Phase5-C2 M2-a) 원칙과 충돌하지 않는다.

```
Spurgeon_Lectures_to_My_Students.txt
Spurgeon_Lectures_to_My_Students.meta.json   ← PDF docinfo에서 전사
  {"title": "Lectures to my students : being addresses delivered to
             the students of the Pastors' College, Metropolitan Tabernacle",
   "author": "Spurgeon, C. H. (Charles Haddon), 1834-1892",
   "source": "archive.org original.pdf docinfo"}
```

**단, (B)는 새 메타데이터 소스 도입이므로 CLAUDE.md §C1 Review 시점의
"Metadata Model 변경"에 해당한다. 선행 승인 없이 착수하지 않는다.**

---

## 7. 기록

```
STATUS:      측정 완료 — (A) 기각 판정
Changed:     없음 (측정만 수행, 프로덕션 코퍼스·코드 무변경)
Tests:       해당 없음
Next:        (B) 사이드카 메타데이터 도입 여부 HQ 결정 → 승인 시 C1 Review 요청
```
