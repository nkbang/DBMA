# C1 Review 결과 — 사이드카 메타데이터 도입 (설계 검토, 구현 전)

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-15
- 유형: **C1 Review — 설계 검토**
- HEAD: `cc651fae0071fd8890164578a9cf15e98534ebbf` (요청서 §7의 `0b428b48`과 이력 상 다름 — 동일 branch `dev/dbma-engine`)
- Toplevel: `/Users/David/DBMA`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`

> **보존 원칙:** 이 문서는 C1이 제출한 원문을 수정 없이 기록한 것이다.
> CUE의 대조 검증 결과는 별도 문서
> `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_001.md`에 있으며,
> 그 문서에서 아래 조건 C1이 **오진**임을 코드·실증으로 반박한다.
> 두 문서를 함께 읽어야 한다.

---

## 판정: YELLOW (조건부 GREEN)

조건 3건이 해소되어야 GREEN으로 전환됩니다 (§5 참조).

---

## 질문별 답변

### Q1. `.meta.json` 확장자 충돌 방지 — 전체 파일명 + `.meta.json` 방식의 타당성

**답: GREEN**

근거: 요청서 §2 D-1 (70-78행)에서 명시한 바와 같이, `x.txt`와 `x.pdf`가 같은 사이드카를 공유하는 충돌을 막기 위해 전체 파일명에 덧붙이는 것은 정당한 설계 결정입니다.

추가 검증: `core/config.py` 127-138행의 `SUPPORTED_EXTENSIONS`는 `(".pdf", ".txt", ".md", ".docx", ".epub", ".html", ".htm", ".rtf")`로 8종이며, `.meta.json`은 포함되지 않습니다(요청서 §3 Q1에서 언급한 바와 동일). 따라서 사이드카가 문서로 오등록될 위험은 없습니다.

**판정: GREEN** — 충돌 방지 논리가 타당하고, 기존 코드에서 `.meta.json`이 확장자로 처리되지 않음을 확인했습니다.

---

### Q2. 내장 메타데이터 우선순위 — 신뢰 불가 값(쓰레기) 처리

**답: YELLOW (조건부)**

근거: 요청서 §2 D-3 (95-102행)과 `core/extractors.py` 638행(`title, author = _extract_pdf_title_author(path)`), `core/processing.py` 466-467행(`extracted_title = raw_result.get("title")`).

**발견:** 현재 설계는 "내장 메타데이터가 있으면 그 값을 쓴다"고 합니다. 하지만 PDF docinfo의 `producer`가 `LuraDocument PDF v2.28`인 경우, `title`/`author` 필드도 쓰레기 값(빈 문자열, 인코딩 깨짐 등)일 수 있습니다. 현재 로직에서는 내장 값이 **빈 문자열("")**이면 `None`이 아니므로 사이드카가 채울 기회를 얻지 못합니다.

**구체적 문제:**
- `core/extractors.py` 638행: `_extract_pdf_title_author()`가 빈 문자열을 반환하면 `title=""`가 되고, 이는 `None`이 아님.
- `core/processing.py` 466행: `raw_result.get("title")`가 `""`이면 `extracted_title = ""`가 됨.
- 사이드카 로직은 "내장이 None 인 필드에 한해서만" 채우므로, `""`는 채워지지 않음.

**해소 방안:** `_extract_pdf_title_author()` (및 `_extract_docx_title_author()`, `_extract_epub_title_author()`, `_extract_html_title_author()`)가 빈 문자열을 반환할 때 `None`으로 강등해야 합니다. 또는 사이드카 적용 로직에서 "내장 값이 빈 문자열인 경우"도 "비어 있음"으로 간주하도록 확장해야 합니다.

**판정: YELLOW** — 내장 값이 빈 문자열일 때 사이드카가 채우지 못하는 간극이 존재합니다.

---

### Q3. 추론 금지 원칙과의 정합 — `source` 필드 필수로 충분한가?

**답: YELLOW (조건부)**

근거: 요청서 §2 D-2 (82-92행)에서 `source`를 "값의 출처를 사람이 읽을 수 있게 남기는 **필수** 필드"로 지정. SPRINT17-Phase5-C2 M2-a "never inferred from filename or content" 원칙.

**발견:** CUE의 논리("사이드카 값은 같은 자료의 원본 PDF docinfo에서 전사하는 것이고 지어내는 것이 아니다")는 **타당합니다**. 사이드카는 추론(inference)이 아니라 전사(transcription)이므로, M2-a 원칙과 충돌하지 않습니다.

**다만 `source` 필드가 검증 가능한 형식인지 확인 필요합니다:**
- 현재 설계: `"source": "archive.org original.pdf docinfo"` — 자유 텍스트.
- 문제: 이 값이 실제로 archive.org PDF에서 왔는지, 아니면 지어낸 값인지 **자동으로 검증 불가**.
- 해소 방안: `source` 필드를 검증 가능한 형식으로 강제하십시오. 예:
  ```json
  {"source": {"type": "archive.org", "doc_id": "lectures_to_my_students_1895", "field": "docinfo"}}
  ```
  또는 최소한 `"source": "archive.org|<doc_id>|docinfo"` 같은 구분자 기반 형식.

**판정: YELLOW** — `source`가 자유 텍스트이므로 감사 시 검증 불가. 검증 가능한 형식으로 강제해야 합니다.

---

### Q4. 감사 가능성 — registry에서 title 소스 구분

**답: YELLOW (조건부)**

근거: `core/identity_registry.py` 163행(`"title": metadata.get("title")`), `core/tsu_builder.py` 382행(`"title": doc.get("title")`).

**발견:** 현재 registry와 TSU 모두 `title` 값의 출처(내장 vs 사이드카)를 기록하지 않습니다. 인용 표기에서는 사용자가 title/author만 보면 되므로 실용적 문제不大하지만, **디버깅·감사**에서는 구분이 필요합니다.

**구체적 사례:**
- 어떤 TSU의 `title`이 사이드카에서 왔는지 내장에서 왔는지 registry만 보고는 알 수 없음.
- 사이드카 파일이 삭제되었을 때, 해당 title이 "실제 존재하는 값"인지 "사이드카에서 온 값"인지 구분 불가.

**해소 방안 (두 가지 옵션):**
- **(A) registry에 `metadata_source` 필드 추가** — 명백한 Metadata Model 변경이지만 감사 가능성 확보.
- **(B) 사이드카 파일 존재 여부를 runtime에 확인** — registry 변경 없이 구현 가능하지만 성능 오버헤드.

현재 설계의 범위 최소화 원칙과 충돌하므로, **(B)를 권고**합니다. 사이드카 적용 시 파일 존재 여부를 확인하고, TSU record에 `"metadata_source": "sidecar"` 또는 `"metadata_source": "embedded"`를 기록하면 됩니다. 이는 registry schema 변경이 아니라 TSU record의 **선택적 필드** 추가이므로 범위가 작습니다.

**판정: YELLOW** — 감사 가능성을 확보하려면 TSU record에 `metadata_source` 필드 추가가 필요합니다.

---

### Q5. 호출 위치(D-4) — 추출기 계약 vs processing.py

**답: GREEN**

근거: `core/extractors.py` 603-626행 docstring:
> "title/author come from the source file's own embedded metadata ... when present; None otherwise — never inferred from filename or content"

**분석:** 사이드카 메타데이터는 "파일 자신의 내장 메타데이터"가 아니므로, 추출기 계약에 포함되지 않습니다. 따라서 `processing.py`에서 처리하는 것이 **옳습니다**.

추가로, 만약 `extract_text_from_file()`에 `allow_sidecar=False` 파라미터를 추가한다면:
1. docstring 계약을 개정해야 함 → 또 다른 검토 대상.
2. 추출기의 단일 책임 원칙(SRP)을 위반할 수 있음 (추출 + 사이드카 로직).

**판정: GREEN** — 호출 위치(D-4) 설계가 적절합니다. 계약 개정이 필요하지 않습니다.

---

### Q6. `doc_type` 파급 — 재처리 시 doc_type 변경 허용 여부

**답: YELLOW (조건부)**

근거: `core/processing.py` 688행(`doc_type = guess_doc_type(final_text, source_name, extracted_title)`).

**발견:** `guess_doc_type()`이 `extracted_title`을 입력으로 받습니다. 사이드카 도입으로 `extracted_title`이 `None` → 실제 값으로 바뀌면, `doc_type`도 바뀔 수 있습니다.

**구체적 사례:**
- 요청서 §5 (DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md 83행): 매튜 풀 EPUB에서 `doc_type`이 `기타` → `주석`으로 바뀐 사례가 이미 확인됨.
- 사이드카 도입 시 `.txt` 파일의 `title`도 `None` → 실제 값으로 바뀌므로, 동일하게 `doc_type`이 변경될 수 있음.

**해소 방안:**
- **(a) 개선이므로 허용** — 하지만 재처리 전 영향 문서 목록을 산출하고 HQ 승필요.
- **(b) `doc_type`만 기존 값 고정** — 재처리 시 사이드카가 채운 `title`은 `doc_type` 추론에 사용하지 않도록 별도 플래그.

현재 설계에서는 (a)를 권고합니다. 하지만 **재처리 전 영향 문서 목록 산출이 선행 조건**입니다.

**판정: YELLOW** — 재처리 전 영향 문서 목록 산출 + HQ 승인이 선행 조건입니다.

---

### Q7. 배포 파급 — `reset_for_release.py`와 사이드카 보관 위치

**답: GREEN (정보 제공)**

근거: 요청서 §3 Q7에서 언급한 `scripts/reset_for_release.py`와 `docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md`.

**분석:** `scripts/reset_for_release.py`가 `data/RAW/`를 통째로 비우면 사이드카도 함께 소멸합니다. 무료 배포 패키지에서 기본 코퍼스를 동봉한다면:

- **권고:** 사이드카를 RAW와 **동일 디렉터리**에 보관하십시오. 그래야 "원본 파일 + 사이드카"가 항상 한 세트로 이동합니다.
- `reset_for_release.py`에서 사이드카를 제외하려면 `.meta.json`을 별도 목록에 추가해야 하지만, 이는 배포 파급이 아니라 운영 파급입니다.

**판정: GREEN** — 사이드카를 RAW와 동일 디렉터리에 보관하면 배포 시 일관성 유지됩니다. 별도 보관 위치는 불필요한 복잡성만 추가합니다.

---

## 조건부 GREEN 전환 조건

다음 3건이 해소되어야 GREEN으로 전환됩니다:

| # | 조건 | 우선순위 | 해소 방안 |
|---|------|----------|-----------|
| C1 | 내장 메타데이터가 빈 문자열일 때 사이드카가 채우지 못하는 간극 | 높음 | `_extract_*_title_author()`가 빈 문자열 → `None` 강등, 또는 사이드카 적용 로직에서 `""`도 "비어 있음"으로 간주 |
| C2 | `source` 필드가 자유 텍스트이므로 감사 시 검증 불가 | 중 | `source`를 검증 가능한 형식(예: JSON 객체 또는 구분자 기반 문자열)으로 강제 |
| C3 | 재처리 전 `doc_type` 변경 영향 문서 목록 산출 + HQ 승인 | 중 | 재처리 스크립트 실행 전 `doc_type` 변경 대상 목록을 산출하고 HQ에 보고 |

---

## 요약

| 질문 | 판정 | 비고 |
|------|------|------|
| Q1. 확장자 충돌 방지 | GREEN | 설계 타당, 코드에서 `.meta.json` 미포함 확인 |
| Q2. 내장 우선순위 / 쓰레기 값 | **YELLOW** | 빈 문자열 간극 해소 필요 |
| Q3. 추론 금지 원칙 정합 | **YELLOW** | `source` 검증 가능 형식 강제 필요 |
| Q4. 감사 가능성 | **YELLOW** | TSU record에 `metadata_source` 필드 추가 권고 |
| Q5. 호출 위치(D-4) | GREEN | 추출기 계약 위반 없음 |
| Q6. `doc_type` 파급 | **YELLOW** | 재처리 전 영향 목록 산출 + HQ 승인 필요 |
| Q7. 배포 파급 | GREEN | RAW 동일 디렉터리 보관으로 충분 |

**최종 판정: YELLOW (조건부 GREEN)** — 조건 C1-C3 해소 시 GREEN 전환 가능.
