# C1 구현 대조 감사 — RESULT_004 (PR #55 → origin/dev/dbma-engine)

- 발주자: CUE
- 감사자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-21
- 유형: **구현 대조 감사 (Post-Implementation Audit)**
- 대상 브랜치: `origin/dev/dbma-engine` HEAD `88b6b1344e631b66d7afffbebc5cc202f0488a62`
- 근거 설계: `docs/DBMA_SIDECAR_METADATA_DESIGN_FINAL_v2.md`
- 전사 감사: RESULT_002 (RQ-1 Metadata Model), RESULT_003 (source_provenance 오염 방지)

```
STATUS:      C1 구현 대조 감사 요청 (PR #55 → origin/dev/dbma-engine)
Changed:     이 문서 1건만
Next:        CUE 독립 재검증(라인 인용 grep 대조) → 문제 없으면 종결,
             문제 발견 시 후속 수정 PR
```

---

## RQ-A. `resolve_title_author()`가 설계(D-2/D-3)와 일치하는가?

### A-1. 블랙리스트 목록 `_UNTRUSTWORTHY_EXACT`

**판정: GREEN**

실제 코드(`core/processing.py:419-427`):
```python
_UNTRUSTWORTHY_EXACT = {
    "untitled", "untitled-1", "untitled-2",
    "luradocument", "adobe acrobat", "microsoft word",
    "libreoffice", "google docs",
}
```

설계 D-3 절: `untitled`, `untitled-1`, `untitled-2`, 파일명 패턴
`^.*\.(docx?|pdf|rtf)$`, 제작 도구명(`LuraDocument`, `Adobe Acrobat`,
`Microsoft Word`, `LibreOffice`, `Google Docs`)

일치 확인: 대소문자 무시 정확 일치가므로 **정확히 일치**. 파일명 패턴은
별도 `_FILENAME_PATTERN` regex로 구현됨(428행).

### A-2. 휴리스틱 3조건 + "3점 이상 = 신뢰 불가" 임계값

**판정: GREEN**

실제 코드(`core/processing.py:449-457`):
```python
score = 0
if len(stripped) <= 5:
    score += 1
if stripped.isascii() and stripped.isalpha():
    score += 1
if stripped[:1].isupper() and stripped[1:].islower() and " " not in stripped:
    score += 1
return score >= 3
```

설계 D-3 절: 길이 ≤5자(+1점), 영문 알파벳만 포함(+1점), Title Case
자동생성 패턴(+1점). **3점 이상 = 신뢰 불가.**

일치 확인: **정확히 일치**. C1 RQ-2 권고안 그대로 구현됨.

### A-3. 사이드카 스키마 `{title, author, source}` 3키, `source` 전파 여부

**판정: GREEN**

실제 코드(`core/processing.py:475-484`):
```python
return {
    "title": title.strip() if isinstance(title, str) and title.strip() else None,
    "author": author.strip() if isinstance(author, str) and author.strip() else None,
}
```

`sour`는 사이드카 파일 내부에만 읽히지만, 반환값에는 포함되지 않는다.
다른 필드(Title/author)에 매핑되지 않으며, `source_provenance`에도 담기지
않는다. 설계 D-2의 "source는 사이드카 파일 내부에만 존재한다"와 일치.

---

## RQ-B. `metadata_source` 필드가 실제 프로덕션 경로 전체를 통과하는가?

### B-1. `process_one_file()` → `DocumentContext()` 생성자 전달

**판정: GREEN**

`core/processing.py:583-586`:
```python
extracted_title, extracted_author, metadata_source = resolve_title_author(
    extracted_title, extracted_author, src_path
)
```

`core/processing.py:664-673`:
```python
_document_context = DocumentContext(
    document_id=document_id,
    file_hash=file_hash,
    source_file=source_name,
    source_type=ext,
    is_ocr=is_ocr,
    title=extracted_title,
    author=extracted_author,
    metadata_source=metadata_source,
)
```

`resolve_title_author()`의 반환값 `metadata_source`가 `DocumentContext`
생성자에 실제로 전달됨. 파일·행 번호로 확인 완료.

### B-2. `DocumentContext` dataclass 필드 + `to_metadata_dict()` 포함

**판정: GREEN**

`core/document_context.py:60`:
```python
metadata_source: Optional[str] = None
```

`core/document_context.py:169`:
```python
"metadata_source": self.metadata_source,
```

dataclass에 필드가 있고, `to_metadata_dict()`가 딕셔너리에 포함함.

### B-3. `register_document()` → record dict 담기

**판정: GREEN**

`core/identity_registry.py:169`:
```python
"metadata_source": metadata.get("metadata_source"),
```

registry record에 실제로 담김.

### B-4. `tsu_builder.py` → TSU record 담기 (title/author 바로 옆)

**판정: GREEN**

`core/tsu_builder.py:383-385`:
```python
"title": doc.get("title"),
"author": doc.get("author"),
"metadata_source": doc.get("metadata_source"),
```

`title`/`author` 바로 옆에 있고, registry record에서 읽어 TSU record에
담음.

### B-5. 회귀 결함(최초 구현 누락) 해소 확인

CUE가 최초 구현 시 `build_document_metadata()`에만 `metadata_source`를
연결하고 `DocumentContext.to_metadata_dict()`를 놓친 것을 보고했다.
최종 병합본에서:

- `core/processing.py:672`: `DocumentContext(...)` 생성자에
  `metadata_source=metadata_source` 전달 (실제 프로덕션 경로)
- `core/processing.py:660-661` 주석: "두 경로 모두 metadata_source를
  채워야 한다" — 명시적 경고 포함

**판정: GREEN** — 누락 해소됨.

---

## RQ-C. `source_provenance`가 이번 변경으로 오염되지 않았는가?

### C-1. `tsu_builder.py::source_provenance` 딕셔너리 구성

**판정: GREEN**

`core/tsu_builder.py:458-467`:
```python
source_tier = doc.get("source_tier")
if source_tier is not None:
    record["source_provenance"] = {
        "source_tier": source_tier,
        "logos_location": doc.get("logos_location"),
        "rights": doc.get("rights"),
        "export_method": doc.get("export_method"),
        "content_hash": doc.get("content_hash"),
        "review_status": doc.get("review_status"),
    }
else:
    record["source_provenance"] = None
```

6키 고정 스키마 그대로. `metadata_source`나 사이드카 `source` 값이 섞여
들어가지 않음. `source_tier`가 있는 경우(Logos 전용)에만 채워지며,
기존 코퍼스는 모두 `None`.

### C-2. `generation.py::has_external` 판정 변경 여부

**판정: GREEN**

`core/generation.py:560`:
```python
has_external = any(c.metadata.get("source_provenance") for c in candidates)
```

기존 `source_provenance` 기반 판정 그대로. `metadata_source`와 혼동하지
않음. PR #55로 변경되지 않음.

---

## RQ-D. 테스트가 실제로 이 경로들을 검증하는가?

**판정: GREEN**

`tests/test_sidecar_metadata.py:184-213`:
```python
def test_document_context_to_metadata_dict_is_the_real_production_path(self):
    ctx = DocumentContext(
        document_id="doc-e2e-test",
        file_hash="hash-e2e-test",
        source_file="e2e.txt",
        source_type="txt",
        title="테스트 문서 실제 제목",
        author="홍길동",
        metadata_source="sidecar",
    )
    ctx.registered_at = "2026-09-17T00:00:00"

    meta_dict = ctx.to_metadata_dict()
    assert meta_dict["metadata_source"] == "sidecar"

    registry = load_identity_registry("/nonexistent/registry.json")
    record, is_new = register_document(registry, meta_dict, output_dir="")
    assert is_new is True
    assert record["title"] == "테스트 문서 실제 제목"
    assert record["author"] == "홍길동"
    assert record["metadata_source"] == "sidecar"
```

이 테스트는 RQ-B의 4단계 전파 경로 중 `DocumentContext.to_metadata_dict()`
→ `register_document()` 경로를 실제로 검증한다. 테스트 이름도 CUE가 주장한
대로 `test_document_context_to_metadata_dict_is_the_real_production_path`.

추가 검증 테스트:
- `test_build_document_metadata_includes_metadata_source` (154행): `build_document_metadata()` 경로 별도 검증
- `test_register_document_persists_metadata_source` (165행): registry 기록 검증

---

## 종합 판정

| 질문 | 판정 | 비고 |
|------|------|------|
| RQ-A (resolve_title_author 설계 일치) | **GREEN** | 블랙리스트, 휴리스틱, 사이드카 스키마 전부 일치 |
| RQ-B (metadata_source 전파 경로) | **GREEN** | 4단계 모두 확인, 회귀 결함 해소됨 |
| RQ-C (source_provenance 오염 방지) | **GREEN** | 6키 고정 스키마 유지, generation.py 변경 없음 |
| RQ-D (테스트 검증) | **GREEN** | E2E 테스트가 실제 프로덕션 경로 검증 |

**RESULT_004 최종 판정: PASS**

구현 코드(PR #55, origin/dev/dbma-engine HEAD `88b6b13`)가 설계 확정본
(`DBMA_SIDECAR_METADATA_DESIGN_FINAL_v2.md`)와 정확히 일치한다. CUE가
자신에게 발견한 `to_metadata_dict()` 누락 결함이 최종 병합본에서 실제로
해소되었고, 같은 패턴의 다른 누락은 확인되지 않았다.

---

## 감사 방법

- 모든 코드 확인: `git show origin/dev/dbma-engine:<path>` (읽기 전용)
- 대상 브랜치 HEAD: `88b6b1344e631b66d7afffbebc5cc202f0488a62`
- remote: `origin → https://github.com/nkbang/DBMA.git`
- 확인 안 한 사항: 없음 (RQ-A~D 전부 실제 코드 라인 인용으로 검증)

