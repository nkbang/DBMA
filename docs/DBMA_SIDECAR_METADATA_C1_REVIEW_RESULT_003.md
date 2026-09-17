# C1 Review 결과 — 사이드카 메타데이터 설계 검토 (RQ-1 재답변, source_provenance 반영)

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-17
- 유형: **C1 Review — RQ-1 재답변 (source_provenance 필드 반영)**
- HEAD: `185a0fdd5ece1e743475cc88e6073b7543c12d11`
- Toplevel: `/Users/David/DBMA`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`

```
HEAD: 185a0fdd5ece1e743475cc88e6073b7543c12d11
nas	http://100.94.139.122:3000/David/DBMA.git (fetch)
nas	http://100.94.139.122:3000/David/DBMA.git (push)
origin	https://github.com/nkbang/DBMA.git (fetch)
origin	https://github.com/nkbang/DBMA.git (push)
toplevel: /Users/David/DBMA
```

> **보존 원칙:** 이 문서는 C1이 제출한 원문을 수정 없이 기록한 것이다.
> RQ-1만 재답변한다. RQ-2는 확정됨(재답변 금지).
> 추정치를 쓰지 않으며, 확인하지 못한 것은 "확인 불가"로 표기한다.

---

## 판정: YELLOW (기존 GREEN → source_provenance 충돌 발견으로 하향)

RQ-1의 기존 결론("D-2 스키마는 기존 Model 변경 아님")은 **부분적으로만 정확하다**.
`sourced_provenance` 필드를 고려하면, 사이드카의 `source` 키를 기존 필드에 매핑하는
방식은 의미 충돌을 일으킨다. 별개 필드(`metadata_source`) 추가가 필요하다.

---

## RQ-1 재답변 — Metadata Model 변경 범위 판정 (source_provenance 반영)

### 질문 재진술 (C1-TASK-ORDER-067 §재답변 요청)

1. D-2의 사이드카 `source` 키(예: `"archive.org original.pdf docinfo"`)가
   `source_provenance`(dict)에 담기도록 설계하는 것이 타당한가, 아니면
   `source_provenance`는 이미 다른 용도(외부 소스 청크 판정, TSU record
   전파)로 쓰이고 있어 같은 필드를 공유하면 의미 충돌이 생기는가?
2. 위 판단에 따라 RQ-1의 최종 결론("D-2 스키마는 기존 Model 변경 아님")이
   그대로 유지되는가, 아니면 수정이 필요한가?

### 사실 확인 — `source_provenance` 필드의 실제 용도

#### (1) 정의 위치: `core/document_context.py:76`

```python
source_provenance: Optional[dict] = None
```

`DocumentContext` dataclass의 필드. Task Order 017 (§3)에서 registry schema parity
필드로 추가됨. **죽은 필드가 아님** — 아래에서 실제 사용 확인.

#### (2) TSU record 전파: `core/tsu_builder.py:458-467`

```python
record["source_provenance"] = {
    "source_tier": source_tier,
    "logos_location": doc.get("logos_location"),
    "rights": doc.get("rights"),
    "export_method": doc.get("export_method"),
    "content_hash": doc.get("content_hash"),
    "review_status": doc.get("review_status"),
}
```

registry의 document record에서 6개 필드를 추출해 TSU record에 전파.
**Logos Bible Software 등 외부 소스에서 가져온 문서의 콘텐츠 출처를 추적**하는 용도.
`source_tier`, `logos_location`, `rights` 등은 모두 **문서 콘텐츠의 원천**을 나타냄.

#### (3) DocumentContext → registry 추출: `core/document_context.py:281-297`

```python
FIELDS = ("source_tier", "logos_location", "rights",
          "export_method", "content_hash", "review_status")
parts = {k: record.get(k) for k in FIELDS}
if all(v is None for v in parts.values()):
    return None
return parts
```

registry 레코드에서 6개 provenance 필드를 dict로 묶어 `DocumentContext.source_provenance`에
할당. **Logos 출처 문서 전용** — Logos가 아닌 문서는 `None`.

#### (4) 외부 소스 판정 + 인용 라벨링: `core/generation.py:560-589`

```python
# 560행: 외부 소스 유래 청크 판정
has_external = any(c.metadata.get("source_provenance") for c in candidates)
if not has_external:
    return ""  # 외부 소스 없음 → no-op

# 589행: Logos location을 인용 라벨에 병기
provenance = c.metadata.get("source_provenance")
```

`source_provenance`가 있는 청크는 **Logos 등 외부 소스에서 가져온 콘텐츠**로 간주됨.
- 560~570행: 외부 소스 인용 규칙(요약·재진술 의무, 원저작물 위치 언급)을 프롬프트에 추가
- 589행: `provenance.get("logos_location")`을 인용 라벨에 병기해 원저작물 위치 추적

### `source_provenance`의 의미 분석

| 속성 | 값 |
|------|-----|
| **타입** | `Optional[dict]` |
| **키 구성** | `source_tier`, `logos_location`, `rights`, `export_method`, `content_hash`, `review_status` (6개 고정) |
| **의미** | "이 문서/청크의 **콘텐츠**가 어디에서 왔는가?" (문서 원천 추적) |
| **활용처** | TSU record 전파 → retrieval metadata → generation 외부 소스 판정 + 인용 라벨링 |
| **범위** | Logos Bible Software 등 외부 소스에서 가져온 문서만 채워짐. 일반 코퍼스는 `None` |

### 사이드카의 `source` 키의 의미 분석

| 속성 | 값 |
|------|-----|
| **타입** | `str` (예: `"archive.org original.pdf docinfo"`) |
| **의미** | "이 메타데이터 값이 **어디에서 추출되었는가**?" (메타데이터 추출원 추적) |
| **범위** | 사이드카 파일에 저장된 모든 문서의 메타데이터 출처 |

### 두 개념의 비교

```
source_provenance:  "이 문서의 콘텐츠가 Logos에서 왔는가?"  → 문서/청크 레벨
sidecar source:     "이 title/author 값이 archive.org docinfo에서 왔는가?"  → 메타데이터 필드 레벨
```

**서로 다른 차원의 개념이다:**

- `source_provenance`는 **문서 콘텐츠의 원천**(document content origin)을 추적 — Logos export 여부, 권리 정보, 해시 등
- 사이드카의 `source`는 **메타데이터 값의 추출원**(metadata extraction source)을 추적 — PDF docinfo, EPUB dc, HTML meta 등

사이드카의 `source: "archive.org original.pdf docinfo"`가 `source_provenance` dict에 담기면:
- `source_provenance`의 6개 키 구조(`source_tier`, `logos_location` 등)와 호환되지 않음
- `generation.py:560`의 `has_external` 판정이 사이드카 출처에 따라 엉뚱하게 True가 될 수 있음
- `generation.py:589`에서 `provenance.get("logos_location")`이 None이 아닌 다른 값을 반환해 인용 라벨이 왜곡됨
### RQ-1 답변

#### 질문 1: 사이드카의 `source`를 `source_provenance`에 담는 것이 타당한가?

**답: 아니오, 의미 충돌이 발생한다.**

근거:
1. `source_provenance`(tsu_builder.py:458-467)는 Logos 등 외부 소스 문서의 **콘텐츠 원천**을 6개 키 구조로 추적 — 사이드카의 `source` 문자열은 메타데이터 추출원을 나타냄. 서로 다른 개념.
2. `generation.py:560`에서 `source_provenance` 유무가 "외부 소스 유래 청크" 판정에 쓰임 — 사이드카 출처를 여기에 넣으면 Logos가 아닌 문서도 외부 소스 규칙이 적용되는 오류 발생.
3. `generation.py:589`에서 `logos_location`을 인용 라벨에 병기 — 사이드카 `source` 값이 여기에混入되면 인용 표기가 왜곡됨.

#### 질문 2: RQ-1의 기존 결론("D-2 스키마는 기존 Model 변경 아님")이 유지되는가?

**답: 수정 필요하다.**

기존 결론의 문제점:
- "사이드카의 `source` 키는 어디에도 직접 매핑되지 않는다"(002 문서 99행) — 이 진술은 정확하지만, `source_provenance`를 고려하지 않은 채 "필드가 없다"고 단정했던 것은 오류.
- 사이드카의 `source`가 기존 필드에 매핑되지 않는 것은 맞으나, **별도 필드 추가**가 필요하다는 결론이 누락됨.

수정된 결론:
- D-2 스키마의 `title`/`author`는 기존 필드 재채움 → Model 무변경 (기존 GREEN 유지)
- D-2 스키마의 `source`는 **별도 선택 필드 `metadata_source` 추가 필요** → Model에 additive 변경 발생
- 따라서 RQ-1 판정은 GREEN에서 **YELLOW**로 하향: "D-2의 3키 중 2키는 무변경이지만, `source` 키가 별도 필드 추가를 요구하므로 완전한 Model 무변경은 아님"

---

## 종합 판정

| 질문 | 판정 | 비고 |
|------|------|------|
| RQ-1 (Metadata Model 변경 범위) | **YELLOW** | `title`/`author`는 무변경, `source`는 별도 `metadata_source` 필드 추가 필요 → additive 변경 |
| RQ-2 (쓰레기 내장 값 처리) | YELLOW (확정) | 재답변 금지 — 002 문서 결론 유지 |

**최종 판정: YELLOW** — RQ-1에서 `source` → `metadata_source` 별도 필드 추가 설계가 필요.

---

## 요약

| 항목 | 판정 | 근거 파일·행 |
|------|------|-------------|
| RQ-1: `title`/`author` 매핑 | GREEN (무변경) | `core/document_context.py:53~54`, `core/identity_registry.py:163~164`, `core/tsu_builder.py:382~383` — 기존 필드 재채움 |
| RQ-1: `source` 매핑 | **YELLOW** (별도 필드 필요) | `core/document_context.py:76` (`source_provenance`)는 Logos 콘텐츠 원천 추적용 — 사이드카 `source`(메타데이터 추출원)와 의미 충돌. 별도 `metadata_source` 선택 필드 추가 필요 |
| RQ-2: 쓰레기 내장 값 처리 | YELLOW (확정) | 재답변 금지 — 002 문서 결론 유지 |

---

## 기록

```
STATUS:      C1 RQ-1 재답변 완료 (source_provenance 반영)
판정:        YELLOW — source → metadata_source 별도 필드 추가 필요
Changed:     이 문서 1건만. 코드·코퍼스·registry 무변경 (PLAN MODE)
Tests:       해당 없음 (설계 검토 — 구현 전)
Next:        RQ-1: source → metadata_source 별도 필드 설계 반영 → 설계 확정 → HQ 승인 → 구현 착수
             RQ-2: 002 문서 결론 유지 (휴리스틱+블랙리스트 설계 반영)
```
