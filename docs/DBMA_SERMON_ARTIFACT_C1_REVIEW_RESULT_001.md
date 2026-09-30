# C1 설계 검토 결과 — SermonArtifact (P1 착수 전)

- 발주자: CUE
- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-21
- 유형: **C1 Review — 설계 검토 (Pre-Implementation, 신규 Architecture Layer)**
- 근거: `docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` §3·§4·§5.1·§8
- Task Order: `docs/agents/c1/C1-TASK-ORDER-069.md` (RQ-1~4)

---

## 종합 판정: GREEN (P1 착수 가능)

| RQ | 판정 | 근거 요약 |
|----|------|----------|
| RQ-1. ADR-001 준수 | **GREEN** | 기존 `QueryProcessor.process()` 재사용, 사후 필터링으로 doc_type 선별 — 코드 경로 무변경 |
| RQ-2. Metadata Model 무변경 | **GREEN** | SermonArtifact는 별도 저장소(`data/sermon_artifacts/`)에 구현, TSU/registry 스키마 건드리지 않음 |
| RQ-3. 기존 자산 재사용 | **GREEN** | `SermonRecord`, `save_sermon_record()`, `judge_sermon_groundedness()`, `SERMON_FORMATS` 모두 실측 존재·일치 |
| RQ-4. 저장 위치·감사 추적 | **YELLOW** | `.gitignore` 일치 확인됨. `sermon_id` 네임스페이스 충돌 위험은 낮으나 registry와 완전히 분리된 식별자 체계 필요 |

---

## RQ-1. ADR-001(One Retrieval Engine) 준수 여부 — GREEN

### 확인 결과

**`QueryProcessor.process()` 실제 시그니처** (`core/retrieval.py:2367~2415`):

```python
def process(
    self,
    query: str,
    query_id: str = "",
    k: int = 10,
    file_scope: Optional[list[str]] = None,
) -> ResponsePackage:
```

**반환 타입** (`core/retrieval.py:175~196`):

```python
class ResponsePackage:
    query_id: str
    question: str
    candidates: list[RankedCandidate]
    top_k_results: list[RankedCandidate]   # ← 필터링 후 최종 결과
    ...
```

**`RankedCandidate` 구조** (`core/retrieval.py:105~127`):

```python
class RankedCandidate:
    tsu_id: str
    content: str
    metadata: dict[str, Any]   # ← title, author, source_file 등 포함
    ...
```

### 설계 주장 대조

| 설계 주장 | 실제 코드 | 판정 |
|----------|----------|------|
| 새 검색 경로/병렬 랭킹 없음 | `process()` 시그니처 변경 없음, k=30으로 호출만 하면 됨 | ✅ 일치 |
| 사후 필터(post-filter) 구현 가능 | `ResponsePackage.top_k_results` 각 candidate.metadata에 `title`, `author`, `source_file` 포함 — registry 조인으로 doc_type 판정 가능 | ✅ 가능 |
| `core/retrieval.py` 무변경 | 설계는 `process()` 재사용만 언급, 내부 수정 없음 | ✅ 일치 |

### 구체적 구현 경로

설계 §5.1의 흐름:

```
설교 대지 텍스트
  → QueryProcessor.process(대지 + 본문, k=30)     # 기존 경로 그대로
  → 사후 필터: TSU.document_id → registry.doc_type == "설교"
       (TSU 레코드에 doc_type 필드가 없으므로 registry 조인으로 판정 — 읽기 전용)
  → 상위 3건을 [출처·저자·신뢰도]와 함께 제시
```

이 흐름의 구현은 다음과 같이 가능하다:

1. `process()` 호출 → `ResponsePackage` 반환
2. `response.top_k_results` 각 항목의 `metadata["tsu_id"]`에서 `document_id` 추출 (`TSU-{book_id}-{chunk_id}` 형식에서 `{document_id}` 부분)
3. `identity_registry.load_identity_registry()`로 registry 로드 (읽기 전용)
4. `registry["documents"][document_id].get("doc_type") == "설교"`로 필터링
5. 상위 3건 선택

**결론: ADR-001을 위반하지 않는다. 기존 검색 경로 그대로 통과하고, 선별은 사후 필터로 구현 가능하다.**

---

## RQ-2. Metadata Model 무변경 주장 검증 — GREEN

### 확인 결과

**SermonArtifact 스키마** (설계 §4):

```jsonc
{
  "sermon_id": "SRM-20260915-a3f2c1",
  "created_at": "...",
  "scripture_and_theme": "...",
  "sermon_format": "주제설교",
  "outline": { ... },
  "expanded": { ... },
  "evidence": { "candidate_tsu_ids": [...], "retrieval": {...} },
  "doctrine_report": { ... },
  "groundedness": { ... },
  "generation": { ... },
  "derivations": { ... }
}
```

**TSU record 스키마** (`core/tsu_builder.py:371~445`):

```python
record = {
    "tsu_id": f"TSU-{book_id}-{chunk_id}",
    "document_id": document_id,
    "chunk_id": chunk_id,
    "content": content,
    "verse_mapping": verse_mapping,
    "themes": [],
    "title": doc.get("title"),
    "author": doc.get("author"),
    "metadata_source": doc.get("metadata_source"),
    "chapter": doc.get("chapter"),
    "page": doc.get("page"),
    "source_file": source_file,
    "language": doc.get("language"),
    "source_type": doc.get("source_type"),
    ...
}
```

**registry record 스키마** (`core/identity_registry.py:141~178`):

```python
record = {
    "document_id": doc_id,
    "file_hash": file_hash,
    "doc_type": metadata.get("doc_type"),  # ← doc_type 필터의 출처
    ...
}
```

### 설계 주장 대조

| 설계 주장 | 실제 코드 | 판정 |
|----------|----------|------|
| TSU 스키마 무변경 | SermonArtifact 필드 중 TSU record에 존재하는 것이 없음 — 완전히 별도 구조 | ✅ 일치 |
| registry 스키마 무변경 | SermonArtifact의 `candidate_tsu_ids`는 TSU ID 참조일 뿐, registry 레코드에 새 필드 추가 없음 | ✅ 일치 |
| artifact는 별도 저장소 | `data/sermon_artifacts/{sermon_id}.json` — TSU/registry와 물리적으로 분리 | ✅ 일치 |
| `doc_type == "설교"` 필터가 registry 조인만으로 가능한가? | TSU record에 `doc_type` 필드 없음. TSU의 `document_id`로 registry 조인 시 접근 가능 | ✅ 가능 (조인 필요) |

**결론: SermonArtifact 스키마는 TSU/registry 스키마와 완전히 독립적이다. 별도 저장소에 구현 가능하며, 기존 스키마를 건드리지 않는다.**

---

## RQ-3. 기존 자산 재사용 주장 검증 — GREEN

### 3-1. `SermonRecord` 및 `save_sermon_record()`

**실제 시그니처** (`core/multi_doc_splitter.py:68~75, 240~260`):

```python
@dataclass
class SermonRecord:
    title: str
    date: Optional[str]
    scripture: Optional[str]
    body: str
    start_line: int
    end_line: int
```

```python
def save_sermon_record(record: SermonRecord, raw_dir: str) -> str:
    """새 인제스트 경로를 만들지 않고 기존 흐름을 재사용."""
```

**설계 주장 대조**: §5.6 되먹임 설계 — **일치 확인**. docstring에 "새 인제스트 경로를 만들지 않고 기존 흐름을 재사용" 명시.

### 3-2. `judge_sermon_groundedness()`

**실제 시그니처** (`core/evaluation/sermon_judge.py:78~90`):

```python
def judge_sermon_groundedness(
    run_id: str, query_id: str, scripture_and_theme: str,
    retrieved_candidates: list, generated_text: str,
    text_type: str = "outline",   # ← §5.2 주장과 일치
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> SermonQualityScore:
```

**설계 주장 대조**: §5.2 "`text_type` 파라미터만 바꿔 재사용 가능" — **일치 확인**.

### 3-3. `SERMON_FORMATS`

**실제 정의** (`core/generation.py:528`):

```python
SERMON_FORMATS = ("주제설교", "강해설교")
```

**설계 주장 대조**: 값 **일치 확인**.

### 3-4. `_NO_FABRICATED_ILLUSTRATION_DIRECTIVE` (선행 조치)

**실제 존재** (`core/generation.py:631~639`) — 설계 §5.1 선행 조치와 **일치 확인**. `_EXPANSION_STYLE_GUIDANCE`에서 예화 요구 문구 제거도 확인됨.

**결론: 설계가 주장하는 모든 기존 자산이 실제로 존재하며, 시그니처·값·의도가 설계 문서와 일치한다.**

---

## RQ-4. 저장 위치·감사 추적 설계의 위험 요소 — YELLOW

### 4-1. `.gitignore` 확인

**실제 `.gitignore`**: `data/` 전체가 gitignore 대상.

**설계 주장**: "`data/` 하위는 `.gitignore` 대상"

**판정: GREEN — 일치 확인**.

### 4-2. `sermon_id` 식별자 네임스페이스

**실제 identity_registry 패턴**: `register_document(registry, metadata)` 함수가 registry dict를 인자로 받음. 단일 파일(`documents.json`)에 `{"documents": {doc_id: record}}` 구조.

**SermonArtifact 식별자**: `"SRM-20260915-a3f2c1"` — `identity_registry`의 document_id와 **서로 다른 접두사(SRM-) 사용**.

**위험 분석**:
- SermonArtifact는 `data/sermon_artifacts/{sermon_id}.json`에 **개별 파일**로 저장 — registry와 물리적으로 분리됨
- 식별자 접두사가 다름 (SRM- vs TSU-/문서 document_id)
- 같은 파일을 공유하지 않으므로 네임스페이스 충돌 위험은 낮음

**YELLOW 이유**: 설계가 "identity_registry 패턴을 차용한다"고 명시한 부분이 모호하다. 구현 단계에서 registry 코드와 불필요하게 결합될 위험이 있다. SermonArtifact 식별자는 **완전히 독립적인 네임스페이스**로 유지해야 한다.

### 4-3. 감사 추적 — `build_commit` 필드

설계가 `tsu_manifest.json`과 동일한 감사 추적 확장을 제안하는 것은 타당하다. 다만 이 필드가 실제 Git commit 해시를 담는지, 빌드 버전 문자열인지 구현 시 명확히 해야 한다.

**결론: 저장 위치는 안전. 식별자 네임스페이스 충돌 위험은 낮으나 "identity_registry 패턴"의 범위를 설계 문서에 명시해야 한다.**

---

## 부록: 확인한 파일 목록

| 파일 | 브랜치 | 확인 방법 |
|------|--------|----------|
| `docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` | origin/dev/dbma-engine | `git show origin/dev/dbma-engine:docs/...` |
| `core/retrieval.py` | origin/dev/dbma-engine | `git show ...:core/retrieval.py` |
| `core/tsu_builder.py` | origin/dev/dbma-engine | `git show ...:core/tsu_builder.py` |
| `core/identity_registry.py` | origin/dev/dbma-engine | `git show ...:core/identity_registry.py` |
| `core/multi_doc_splitter.py` | origin/dev/dbma-engine | `git show ...:core/multi_doc_splitter.py` |
| `core/evaluation/sermon_judge.py` | origin/dev/dbma-engine | `git show ...:core/evaluation/sermon_judge.py` |
| `core/generation.py` | origin/dev/dbma-engine | `git show ...:core/generation.py` |
| `.gitignore` | origin/dev/dbma-engine | `git show ...:.gitignore` |

---

## Next Steps

```
STATUS:      C1 설계 검토 완료 — GREEN (P1 착수 가능)
Changed:     이 문서 1건만
Next:        CUE가 대조검증 후 P1(SermonArtifact 저장·조회) 구현 착수
             RQ-4 YELLOW 사항("identity_registry 패턴" 범위 명시)은
             P1 구현 시 반영 권장 (-blocking 아님)
```
