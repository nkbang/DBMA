---
title: DBMA DocumentContext Registry Schema Parity Design v1
category: architecture
status: draft (design only — 구현 없음)
based_on:
  - core/document_context.py (현재 구현, from_metadata_dict()/to_metadata_dict())
  - core/identity_registry.py (registry 레코드 스키마 전수 조사)
  - scripts/ingest_logos_export.py (registry 레코드에 직접 쓰는 side-channel 필드)
  - core/index_orchestrator.py, core/processing.py (통합 시도에서 발견된 필드 갭)
created: 2026-07-27
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA DocumentContext Registry Schema Parity Design v1

목적: `index_orchestrator.py`/`processing.py` SKIP 경로 통합을 검토하다가
발견한 사실 — **`DocumentContext.to_metadata_dict()`가 registry 레코드의
부분집합만 직렬화한다** — 를 해소하기 위해, registry 스키마 전체를 커버하도록
확장하는 설계를 제시한다. **코드는 작성하지 않는다.**

---

## 0. 전제 — 왜 지금 이 설계가 필요한가

직전 조사에서 두 곳(`core/processing.py` SKIP 경로, `core/index_orchestrator.py`
전체)에 `DocumentContext`를 통합하려다 **필드 유실 위험**으로 보류했다:

- `processing.py` SKIP 경로: `source_file`을 통째로 덮어쓰면 파일명 변경
  추적(SPRINT21-G-2 Option C)이 깨짐 — 이건 스키마 갭이 아니라 **부분 병합
  vs 전체 재구성**의 문제라 이번 설계로 해결되지 않는다(§6에서 범위 명시).
- `index_orchestrator.py`: `build_tsu_records()`가 읽는 `source_provenance`
  (`source_tier`/`logos_location`/`rights`/`export_method`/`content_hash`/
  `review_status`), `doc_type`, `superseded_by` 등이 `to_metadata_dict()`
  출력에 없어 **왕복 시 데이터가 사라진다** — 이건 순수 스키마 갭이라
  이번 설계로 해결 가능하다.

---

## 1. 필드 갭 전수 조사

`core/identity_registry.py` 전체(스토리지 생성 로직 + 마이그레이션 +
`mark_superseded()`)와 `scripts/ingest_logos_export.py`(registry에 직접
쓰는 side-channel)를 대조해 확인한 registry 레코드의 전체 필드:

| 필드 | 현재 `DocumentContext`에 있는가 | 현재 `to_metadata_dict()`가 직렬화하는가 | 비고 |
|---|---|---|---|
| `document_id` | ✅ | ✅ | |
| `file_hash` | ✅ | ✅ | |
| `source_file` | ✅ | ✅ | |
| `created_at`(레코드 키, 실제로는 registered_at) | ✅(`registered_at`) | ✅ | 이미 이전 설계에서 처리됨 |
| `processing_version` | ✅ | ✅ | |
| `status`("processed" 고정값) | ❌ | ❌ | §6에서 "모델링 불필요"로 결정 |
| `chunk_count` | ✅ | ✅ | |
| `language` | ✅ | ✅ | |
| `noise_score` | ✅ | ✅ | |
| `noise_mode` | ✅ | ✅ | |
| `source_type` | ✅ | ✅ | |
| `is_ocr` | ✅ | ✅ | |
| `book`/`chapter`/`page` | ✅ | ✅ | |
| `title`/`author` | ✅ | ✅ | |
| `doc_type` | ❌ | ❌ | **갭 — `build_tsu_records()`가 읽음** |
| `pipeline_state` | ✅ | ✅ | |
| `superseded_by` | ❌ | ❌ | **갭 — `mark_superseded()`가 씀, `find_by_source_file()`가 읽음** |
| `supersedes` | ❌ | ❌ | **갭 — 위와 동일 메커니즘의 역방향 링크** |
| `last_content_hash` | ❌ | ❌ | **갭 — `classify_ingest_decision()` B5/B6 판정에 씀** |
| `ingest_status` | ✅ | ❌ | **필드는 있는데 직렬화가 안 됨 — 순수 누락** |
| `retry_count` | ✅ | ❌ | **필드는 있는데 직렬화가 안 됨** |
| `max_retries` | ❌ | ❌ | **갭 — `classify_ingest_decision()` B3/B4 판정에 씀** |
| `last_failure_reason` | ✅ | ❌ | **필드는 있는데 직렬화가 안 됨** |
| `last_processed_at` | ✅ | ❌ | **필드는 있는데 직렬화가 안 됨** |
| `pipeline_flags` | ✅ | ❌ | **필드는 있는데 직렬화가 안 됨** |
| `source_provenance.*`(6개 하위 필드) | ❌ | ❌ | **갭 — Logos import 문서 전용, `build_tsu_records()`가 읽음** |
| (registry 최상위) `schema_version`/`created_at`/`updated_at`/`_meta` | 해당 없음 | 해당 없음 | §6에서 "DocumentContext 범위 밖"으로 명시 |

**정리**: 갭은 두 종류다 — (a) `DocumentContext` 필드 자체가 없는 것(진짜 신규
필드 추가 필요: `doc_type`, `superseded_by`, `supersedes`, `last_content_hash`,
`max_retries`, `source_provenance`), (b) 필드는 이미 있는데 `to_metadata_dict()`가
빼먹은 것(`ingest_status`, `retry_count`, `last_failure_reason`,
`last_processed_at`, `pipeline_flags` — 단순 직렬화 누락).

---

## 2. 확장 원칙

1. **Additive only**: 기존 `to_metadata_dict()` 출력의 키를 하나도 제거하거나
   이름을 바꾸지 않는다. 새 키만 추가한다 — `identity_registry.py::
   migrate_registry_schema()`가 이미 확립한 append-only 원칙을 그대로 적용.
2. **버전 분기 없음**: `to_metadata_dict(full=True)` 같은 플래그를 만들지
   않는다. 확장된 필드들은 대부분 `Optional`/기본값이 있어 항상 포함해도
   기존 호출자(`register_document()`)에 해가 없다 — `register_document()`는
   `metadata.get(key, default)` 패턴이라 모르는 키는 무시하고, 아는 키가
   더 채워지면 오히려 더 정확해진다(현재 `doc_type`은 registry 쪽에서 이미
   `metadata.get("doc_type")`로 받고 있는데 `DocumentContext`가 안 줘서
   항상 `None`이 되고 있었다 — 이건 사실상 **버그**에 가깝다, §5 참조).
3. **원본이 없는 필드는 만들지 않는다("never invent")**: `source_provenance`처럼
   대부분의 문서에 해당 없는 필드는 `None`이 기본값이며, 억지로 빈 dict를
   채우지 않는다.

---

## 3. DocumentContext 신규 필드 설계

```python
# core/document_context.py — 추가될 필드 (기존 dataclass에 append)

    # [신규] doc_type — registry가 이미 소비하지만 DocumentContext에 없던 필드
    doc_type: Optional[str] = None

    # [신규] 문서 버전 연결 (SPRINT21-G-2 Option C의 supersedes/superseded_by)
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None

    # [신규] classify_ingest_decision() B5/B6가 참조하는 콘텐츠 해시 이력
    # file_hash와 개념적으로 구분: file_hash는 "이번 처리 시점"의 해시,
    # last_content_hash는 "직전 성공 처리 시점"에 확정된 해시(update_content_hash()가
    # 갱신). 둘을 하나로 합치지 않는다 — identity_registry.py가 이미 별개
    # 필드로 유지하는 이유(REPROCESS 판정에 두 값의 비교가 필요)를 그대로 존중.
    last_content_hash: Optional[str] = None

    # [신규] classify_ingest_decision() B3/B4 재시도 상한
    max_retries: int = 3

    # [신규] Logos export 등 외부 소스 provenance — 대부분의 문서는 None
    # (scripts/ingest_logos_export.py 전용 side-channel 필드, "never invent"
    # 원칙에 따라 해당 없는 문서는 절대 채우지 않는다)
    source_provenance: Optional[dict] = None
```

**`source_provenance`를 중첩 dict로 유지하는 이유**: registry 레코드에서도
이 6개 필드(`source_tier`, `logos_location`, `rights`, `export_method`,
`content_hash`, `review_status`)가 항상 같이 붙어다니는 하나의 "출처 증빙"
묶음이다(`scripts/ingest_logos_export.py`가 한 번에 채움). 개별 필드로
풀어서 `DocumentContext`에 흩뿌리면 "이 문서가 Logos 출처인가"를 판단하려면
6개 필드를 각각 `None`인지 확인해야 한다 — 중첩 dict 하나로 두면
`if ctx.source_provenance:` 한 줄로 판정 가능하다.

---

## 4. `to_metadata_dict()` 확장 설계

```python
# 기존 반환 dict에 추가될 키 (기존 키는 그대로 유지)

    return {
        # ...기존 키 전부 그대로...

        # [확장] 이미 필드는 있었으나 직렬화가 누락됐던 것 (§1 (b) 종류)
        "ingest_status": self.ingest_status,
        "retry_count": self.retry_count,
        "last_failure_reason": self.last_failure_reason,
        "last_processed_at": self.last_processed_at,
        "pipeline_flags": dict(self.pipeline_flags),

        # [확장] §3 신규 필드 (§1 (a) 종류)
        "doc_type": self.doc_type,
        "superseded_by": self.superseded_by,
        "supersedes": self.supersedes,
        "last_content_hash": self.last_content_hash,
        "max_retries": self.max_retries,
    }

    # source_provenance는 register_document()가 직접 다루지 않는 필드
    # (scripts/ingest_logos_export.py가 registry에 별도로 씀)이므로
    # to_metadata_dict()에는 포함하지 않는다 — register_document()에
    # 전달되면 register_document()가 모르는 키라 조용히 버려지고, 그러면
    # "DocumentContext를 거치면 provenance가 사라진다"는 새로운 함정이
    # 생긴다. 대신 §5에서 별도 API로 분리한다.
```

**`source_provenance`를 `to_metadata_dict()`에서 제외하는 이유**: 이 필드는
`register_document()`가 아예 모르는 키라서, `to_metadata_dict()`에 넣어도
`register_document()`를 거치는 순간 조용히 사라진다(현재 코드가 `metadata.get(key, default)`
패턴이라 모르는 키를 그냥 무시함). "직렬화에는 있는데 저장 경로에서
사라진다"는 상태는 갭을 메우는 게 아니라 새로운 함정을 만드는 것이다.
따라서 `source_provenance`는 `to_metadata_dict()`가 아니라 **별도의
읽기 전용 접근자**로 분리한다(§5).

---

## 5. `source_provenance`를 위한 별도 API (register_document() 확장 없이)

`register_document()` 자체를 확장해 `source_provenance`를 받아 저장하게
만드는 방법도 검토했으나, 이는 `core/identity_registry.py` 코드 변경이
필요해 이번 설계(`DocumentContext` 쪽 확장) 범위를 벗어난다. 대신:

```python
# core/document_context.py에 추가될 별도 classmethod (to_metadata_dict()와
# 별개 — register_document()로 가는 경로가 아니라 조회 전용)

@classmethod
def source_provenance_from_registry_record(cls, record: dict) -> Optional[dict]:
    """registry 레코드에서 source_provenance 6개 필드만 골라 dict로 묶어
    반환한다. 6개 필드가 전부 없으면 None(문서가 Logos 출처가 아님).
    register_document()가 이 값을 쓰지 않으므로 to_metadata_dict()의
    출력과는 독립적이다 — Logos provenance는 여전히
    scripts/ingest_logos_export.py가 쓰는 경로로만 registry에 반영된다.
    """
```

이 메서드는 `from_metadata_dict()`가 registry 레코드를 받을 때 내부적으로
호출해 `ctx.source_provenance`를 채우는 데 쓰인다(§5-1). **쓰기는 여전히
`ingest_logos_export.py` 전용 경로로만** 이뤄진다 — `DocumentContext`가
이 필드의 쓰기 책임을 가져오지 않는다(이미 확립된 "Does Not Own" 원칙,
SPRINT16-C-1 §2와 동일한 논리).

### 5-1. `from_metadata_dict()` 대칭 확장

```python
# from_metadata_dict() 내부에 추가

ctx.doc_type = meta.get("doc_type")
ctx.superseded_by = meta.get("superseded_by")
ctx.supersedes = meta.get("supersedes")
ctx.last_content_hash = meta.get("last_content_hash")
ctx.max_retries = meta.get("max_retries", 3)
ctx.source_provenance = cls.source_provenance_from_registry_record(meta)
```

이 확장은 이미 구현된 `from_metadata_dict()`의 기존 필드 처리 방식과
동일한 패턴(`.get(key, default)`)이라 추가 리스크가 없다.

---

## 6. 이번 설계에서 다루지 않는 것 (명시적 경계)

- **registry 최상위 필드**(`schema_version`, 최상위 `created_at`/`updated_at`,
  `_meta.total_documents`) — 이건 **레지스트리 컬렉션 전체**의 메타데이터이지
  개별 문서 상태가 아니다. `DocumentContext`는 문서 1건을 표현하는 객체이므로
  이 필드들을 담을 이유가 없다 — SPRINT16-C-1의 "다수 문서를 집계하는 건
  ExecutionContext의 역할"이라는 경계를 그대로 유지한다.
- **`status`("processed" 고정값) 필드** — 코드 확인 결과 이 필드는 항상
  `"processed"`로 하드코딩되며 다른 값을 가진 적이 없다(레코드 생성 시
  1회성 상수). `ingest_status`/`pipeline_state`가 이미 실질적인 상태를
  담당하므로, 이 필드는 모델링 가치가 없는 레거시 잔재로 판단해 제외한다.
- **`register_document()` 자체의 확장**(`source_provenance` 쓰기 지원) —
  `core/identity_registry.py` 코드 변경이 필요해 이번 설계 범위 밖.
- **`processing.py` SKIP 경로 재통합** — 이건 스키마 갭이 아니라 "부분 병합
  vs 전체 재구성" 설계 문제이므로 이번 확장으로 자동 해결되지 않는다.
  스키마 패리티가 확보된 뒤에도, SKIP 경로는 여전히 `source_file`/
  `source_type`/`is_ocr`만은 현재 실행값을 유지해야 한다는 제약이 남는다
  (별도 재검토 필요, 이번 문서 범위 밖).
- **실제 코드 구현** — SPRINT 구현 단계로 이월.

---

## 7. 이 설계가 완료되면 무엇이 가능해지는가

`index_orchestrator.py`의 `reindex_document()`가 다음과 같은 형태로
`DocumentContext`를 경유할 수 있게 된다(구현은 이번 설계 범위 밖, 가능성만 확인):

```text
registry["documents"][document_id] (dict)
  → DocumentContext.from_metadata_dict(record)   [§5-1 확장 후 무손실]
  → (필요 시 사람이 읽기 좋은 형태로 검사/로깅)
  → ctx.to_metadata_dict()                        [§4 확장 후 무손실]
  → build_tsu_records({"documents": {document_id: 위 dict}}, out_dir)
```

단, `source_provenance`는 `to_metadata_dict()` 출력에 없으므로(§4의 의도적
제외), 이 경로를 실제로 쓰려면 `build_tsu_records()`에 넘기기 직전에
`ctx.source_provenance`를 별도로 병합하는 한 줄이 추가로 필요하다 —
이 역시 §6에서 이월한 구현 세부사항이다.

---

*본 문서는 설계만 다루며 어떤 코드도 작성하지 않았다. `core/`, `scripts/`,
`tests/`, `config.yaml`은 수정하지 않았다.*
