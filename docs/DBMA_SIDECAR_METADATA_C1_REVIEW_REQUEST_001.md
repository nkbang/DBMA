# C1 Review 요청 — 사이드카 메타데이터 도입 (설계 검토, 구현 전)

- 요청자: CUE
- 일자: 2026-09-15
- 유형: **C1 Review — 설계 검토** (구현 아님. **아직 코드가 존재하지 않는다**)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점 — **Metadata Model 변경**"
- HEAD: `0b428b48878fbd5a70a937031e2a075868493879`
- Branch: `dev/dbma-engine`
- Toplevel: `/Users/David/DBMA`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`

> **중요 — 이 요청은 기존 C1 요청서와 성격이 다르다.** 통상의 요청은 구현이 끝난
> 코드를 검토받았으나, 이번에는 **구현 전 설계안**을 검토받는다. 검토 대상은 diff가
> 아니라 §3의 설계 결정 7건이다. C1이 GREEN을 주기 전에는 코드를 작성하지 않는다.

---

## 1. 요청 배경

### 1.1 해결된 부분 (본 검토 대상 아님)

`core/extractors.py::extract_text_from_file()`이 EPUB·HTML에서 title/author를
추출하지 않던 결함을 2026-09-15에 수정했다
(`docs/DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md`, 신규 테스트 8건 PASS).

### 1.2 남은 문제 (본 검토의 대상)

현재 기본 코퍼스로 적재된 스펄전 4종(6,380 TSU)은 archive.org OCR 산출물인
**`.txt`이며, `.txt`에는 내장 메타데이터라는 것이 존재하지 않는다.** 따라서 위
수정으로도 `title`/`author`가 여전히 `null`이고 인용 표기가 불가능하다.

### 1.3 대안 실측 — 이미 기각된 경로

`docs/DBMA_LECTURES_PDF_TEXT_QUALITY_MEASUREMENT_001.md`에서 "원본 PDF 재적재"를
실측 판정했다.

| 지표 | ocr.txt (현행) | PDF 추출 | |
|---|---:|---:|---|
| 사전 일치율 | 90.2% | 57.2% | −32.9%p |
| noise score | 10.9 | 27.0 | 2.5배 악화 |

원인은 PDF 텍스트 레이어의 단어 경계 소실(`andallthe restof them`,
`sinnerswhoare perishingfor lackof knowledge`) — producer가
`Recoded by LuraDocument PDF v2.28`. 기존 `_fix_ocr_word_splits()`는 *잘린* 단어를
잇는 용도라 *붙은* 단어를 가르지 못한다. **기각.** 같은 폴더의 `hocr.html`도
`<title>`이 비어 있어 기각.

→ 텍스트 품질(90.2%)은 이미 양호하고 결함은 **형식의 한계뿐**이므로, 텍스트는
그대로 두고 메타데이터만 별도 파일로 공급하는 안을 제안한다.

### 1.4 선례

NAE 트랙에 **이미 동일 패턴이 운영 중**이다 — `NAE/corpus/raw/archive_org/
missions/Fuller_Complete_Works_Vol07/metadata.json`:

```json
{ "title": "The Works of the Rev. Andrew Fuller… Vol. 7: Sermons on Various Subjects",
  "creator": "Andrew Fuller", "publisher": "S. Converse",
  "source_id": "BAP-MISS-FULLER-VOL07", "work_id": "FULLER-COMPLETE-WORKS-001", … }
```

본 제안은 이 패턴의 **최소 부분집합**을 DBMA production 트랙에 도입하는 것이다.

---

## 2. 제안 설계 (검토 대상)

### D-1. 파일 규약

원본과 같은 디렉터리에 **전체 파일명 + `.meta.json`**.

```
data/RAW/Spurgeon_Lectures_to_My_Students.txt
data/RAW/Spurgeon_Lectures_to_My_Students.txt.meta.json
```

확장자를 치환(`…_Students.meta.json`)하지 않고 전체 이름에 덧붙이는 이유는
`x.txt`와 `x.pdf`가 같은 사이드카를 공유하는 충돌을 막기 위함이다.

### D-2. 스키마 v1 — 최소

```json
{ "title": "Lectures to my students : being addresses delivered to the
             students of the Pastors' College, Metropolitan Tabernacle",
  "author": "Spurgeon, C. H. (Charles Haddon), 1834-1892",
  "source": "archive.org original.pdf docinfo" }
```

- 인식 키는 `title`, `author`, `source` **3개뿐**. 미지의 키는 무시(전방 호환).
- `book`/`chapter`/`page`/`doc_type`은 **v1 범위 밖** — 추론 위험이 크고 기존
  resolver가 담당하는 영역이기 때문.
- `source`는 값의 출처를 사람이 읽을 수 있게 남기는 **필수** 필드.

### D-3. 우선순위 — 내장 메타데이터 우선

```
내장 메타데이터(PDF docinfo / DOCX / EPUB dc / HTML) 가 있으면  → 그 값을 쓴다
내장이 None 인 필드에 한해서만                                  → 사이드카로 채운다
```

사이드카가 내장을 **덮어쓰지 않는다.** 반대안(사이드카 우선)은 낡은 사이드카가
올바른 EPUB `dc:title`을 조용히 가리는 사고가 가능해 기각했다.

### D-4. 호출 위치 — 추출기가 아니라 처리 단계

`extract_text_from_file()`의 계약은 docstring에 **"the file's own embedded
metadata … never inferred"**로 명시돼 있다. 사이드카는 "파일 자신의" 것이 아니므로
이 계약을 깨지 않기 위해 추출기에 넣지 않는다.

`core/processing.py::process_one_file()`에서 추출 직후,
`_load_sidecar_metadata(src_path)`라는 **이름으로 드러나는 별도 단계**로 처리한다.

```python
extracted_title  = raw_result.get("title")
extracted_author = raw_result.get("author")
# 신규 — 내장이 비어 있을 때만 보충
sidecar = _load_sidecar_metadata(src_path)
extracted_title  = extracted_title  or sidecar.get("title")
extracted_author = extracted_author or sidecar.get("author")
```

### D-5. 실패 시 거동

사이드카 부재·JSON 파싱 실패·타입 불일치는 **경고 로그 + `{}` 반환**으로 강등한다.
문서 처리 전체를 중단시키지 않는다(기존 PDF/DOCX 메타데이터 경로와 동일 방침).

### D-6. RAW 무결성

`.json`은 `core/config.py::SUPPORTED_EXTENSIONS`(`pdf/txt/md/docx/epub/html/htm/rtf`)에
**포함되지 않음을 확인**했다. 따라서 `_build_file_list()`의 `rglob` 필터에서 탈락하며
사이드카가 문서로 오등록되지 않는다.

### D-7. 알려진 파급 — `doc_type`

`processing.py:688`의 `guess_doc_type(final_text, source_name, extracted_title)`가
title을 입력으로 받는다. 따라서 사이드카로 title이 채워지면 **doc_type 분류 결과가
바뀐다.** (2026-09-15 EPUB 수정에서 실측: title이 채워지자 `기타` → `주석`으로 개선)
개선 방향이지만 **기존 문서 재처리 시 분류가 달라질 수 있는 부작용**이다.

---

## 3. C1 검토 질문

1. **Metadata Model 변경 범위 판정** — D-2의 3키 스키마가 기존 Metadata Model
   (`core/document_context.py::DocumentContext`, `identity_registry.py:163-164`,
   `tsu_builder.py:382-383`)에 **필드를 추가하지 않고** 기존 `title`/`author`를
   채우기만 하는 것이 맞는가? 그렇다면 이것은 "Model 변경"인가 "Model 무변경 +
   새 데이터 소스 추가"인가? 후자라면 C1 Review 트리거 자체가 과잉이었는지도 함께 판정 바란다.

2. **우선순위 규칙(D-3)의 타당성** — "내장 우선, 사이드카는 빈 필드만 보충"이
   맞는 선택인가? 반대 사례가 있는가 — 예컨대 PDF docinfo에 `Untitled`나
   제작 도구명(`LuraDocument`)이 들어간 쓰레기 값이 있을 때, 그 쓰레기가
   사이드카의 정확한 값을 이기는 결과가 되지 않는가? 그렇다면 "내장이 비었거나
   **신뢰 불가할 때**"로 완화해야 하는가, 그 판정 기준은 무엇이어야 하는가?

3. **추론 금지 원칙과의 정합** — SPRINT17-Phase5-C2 M2-a "never inferred from
   filename or content" 원칙에 사이드카 도입이 저촉되는가? CUE 판단은 "저촉되지
   않는다 — 사이드카 값은 같은 자료의 원본 PDF docinfo에서 **전사**하는 것이고
   지어내는 것이 아니다"인데, 이 논리가 성립하는가? 성립한다면 **전사 출처를
   강제할 방법**(D-2의 `source` 필드가 필수인 것으로 충분한가, 아니면
   검증 가능한 형식이어야 하는가)은?

4. **감사 가능성** — 현재 설계로는 registry의 `title`만 보고는 그 값이 내장에서
   왔는지 사이드카에서 왔는지 **구분할 수 없다.** 구분이 필요한가? 필요하다면
   registry에 `metadata_source` 필드를 추가해야 하는데, 그것은 명백한 Metadata
   Model 변경이라 범위가 커진다. 감사 가능성과 범위 최소화 중 무엇이 우선인가?

5. **호출 위치(D-4)** — 추출기 계약을 지키기 위해 `processing.py`로 뺀 것이
   옳은가, 아니면 `extract_text_from_file()`에 `allow_sidecar=False` 기본값
   파라미터로 넣고 docstring 계약을 개정하는 편이 응집도 면에서 나은가?
   후자라면 계약 개정 자체가 또 다른 검토 대상이 되는가?

6. **`doc_type` 파급(D-7)의 허용 여부** — 사이드카 도입으로 기존 문서를
   재처리하면 `doc_type`이 바뀔 수 있다. 이것을 (a) 개선이므로 허용, (b) 재처리
   전 영향 문서 목록을 산출해 HQ 승인, (c) `doc_type`만 기존 값 고정 중
   어느 쪽으로 다뤄야 하는가?

7. **배포 파급** — `scripts/reset_for_release.py`는 `data/RAW/`를 통째로 비운다.
   사이드카도 함께 소멸한다. 무료 배포 패키지(`docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md`)
   에 기본 코퍼스를 동봉한다면 사이드카는 어디에 보관돼야 하는가 — RAW 동봉,
   별도 `data/baseline/`, 아니면 리셋 대상에서 제외?

---

## 4. 요청 형식

- 판정: **GREEN / YELLOW(조건부) / RED**
- YELLOW·RED 시: 구체 findings + 해소 방안
- 산출물: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다.** 설계 문서 검토 + 코드 read-only.
  ACT MODE 금지, PLAN MODE로만.
- 결과 문서 상단에 `git rev-parse HEAD`, `git remote -v`,
  `git rev-parse --show-toplevel` 출력을 먼저 붙일 것
  (memory: C1 Stale Status Reports — 엉뚱한 저장소·낡은 상태를 감사한 반복 사고 있음).
- **수치를 추정으로 쓰지 말 것.** 본 요청서의 수치(90.2%/57.2%, 6,380 TSU,
  테스트 8건)는 전부 재현 가능하니 필요하면 직접 재현해 반증할 것.

---

## 5. 게이트

- **GREEN + HQ 승인 → 구현 착수.** 그 전에는 스텁·스키마·데이터를 포함해
  어떤 선행 구현도 하지 않는다(Evidence Before Promotion Rule).
- YELLOW/RED → 설계 수정 후 재검토.
- 어느 경우에도 현재 적재된 기본 코퍼스 6,380 TSU와 `output/bench/` 정본은
  이번 검토 중 변경되지 않는다.

---

## 6. 참고 문서

| 문서 | 내용 |
|---|---|
| `docs/DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md` | EPUB/HTML 추출 결함 수정 (완료) — §5에 본 선택지 제시 |
| `docs/DBMA_LECTURES_PDF_TEXT_QUALITY_MEASUREMENT_001.md` | PDF 재적재 기각 실측 근거 |
| `docs/DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md` | 현재 기본 코퍼스 6,380 TSU 적재 기록 |
| `docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` | 무료 배포 방안 — §6 배포 차단 항목 B-3이 본 건 |
| `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/metadata.json` | 사이드카 선례 (NAE 트랙) |

---

## 7. C1 전달용 지시 문구 (붙여넣기)

```
C1, 독립 설계 검토를 요청한다. PLAN MODE로만 진행하고 ACT MODE는 금지한다.
구현하지 말 것 — 이번 검토 대상은 아직 코드가 존재하지 않는 설계안이다.

저장소: /Users/David/DBMA (branch dev/dbma-engine, HEAD 0b428b48)
먼저 git rev-parse HEAD / git remote -v / git rev-parse --show-toplevel 을
실행해 그 출력을 결과 문서 맨 위에 붙여라. 다른 저장소나 worktree를 보고 있으면
즉시 중단하고 보고할 것.

읽을 문서:
  docs/DBMA_SIDECAR_METADATA_C1_REVIEW_REQUEST_001.md   ← 본 요청서
  docs/DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md
  docs/DBMA_LECTURES_PDF_TEXT_QUALITY_MEASUREMENT_001.md

읽을 코드(read-only):
  core/extractors.py (extract_text_from_file 디스패치와 docstring 계약)
  core/processing.py 460-470, 688, 697
  core/identity_registry.py 112-182
  core/tsu_builder.py 371-390
  core/config.py SUPPORTED_EXTENSIONS

요청서 §3의 질문 7개에 각각 답하라. 각 답에는 근거가 되는 파일·행 번호를
붙여라. 추정치를 쓰지 말고, 확인하지 못한 것은 "확인 불가"로 표기하라.

판정은 GREEN / YELLOW(조건부) / RED 중 하나로 내리고,
결과를 docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md 에 작성하라.
```
