# C1 Task Order 018 — doc_type을 DocumentContext에 실제로 배선

**상태**: 승인됨 — 구현 착수 가능 (2026-07-29, David 승인)
**선행 작업**: Task Order 017(`docs/agents/c1/C1-TASK-ORDER-017.md`, 커밋 `ed82921`) —
`DocumentContext`/`to_metadata_dict()`에 `doc_type` 필드·직렬화는 이미 추가됨.
**이번 작업**: 그 필드에 실제 값을 채워 넣는 배선(wiring)만 남음.
**작성일**: 2026-07-29

---

## 1. 배경

Task Order 017 더블첵 과정에서 C1이 명시적으로 짚었던 잔여 문제: `core/
processing.py`가 `_document_context.doc_type`을 세팅하는 코드가 어디에도
없다 — `doc_type = guess_doc_type(...)`(약 686행)로 값은 계산되지만, 그
값이 `_document_context`에 전달되지 않은 채 `to_metadata_dict()`가
호출된다(약 815행). 그 결과 정상 파이프라인을 거친 문서는 registry에
`doc_type=None`으로 저장되고, 이를 읽는 `ui/pages/dashboard.py`(문서
그룹핑/필터링/표시)와 `scripts/report_chunk_summary.py`(값 없으면 `"?"`
표시)에서 실제로 관측되는 분류 오류로 이어진다.

Task Order 017은 스키마 왕복(직렬화/역직렬화)만 다뤘고 이 배선은 의도적으로
범위 밖으로 남겼다 — 이번 Task Order가 그 나머지를 다룬다.

---

## 2. 구현 범위

### 2.1 PROCESS 경로 — `core/processing.py` 약 790~797행 sync 블록

기존:
```python
_document_context.language = language
_document_context.noise_score = noise["score"]
_document_context.noise_mode = noise.get("mode", "-")
_document_context.source_type = ext
_document_context.is_ocr = is_ocr
_document_context.chunk_count = len(chunks)
```

이 블록에 한 줄 추가:
```python
_document_context.doc_type = doc_type
```
(`doc_type` 변수는 이미 약 686행에서 `guess_doc_type(final_text, source_name,
extracted_title)`로 계산돼 있음 — 새로 계산하지 말고 그 값을 그대로 쓸 것.)

### 2.2 SKIP 경로 — `core/processing.py` 약 590~608행 sync 블록

기존 `existing_record`에서 필드를 복사하는 블록(`_document_context.title = ...`
등)에 한 줄 추가:
```python
_document_context.doc_type = existing_record.get("doc_type")
```
SKIP 경로는 콘텐츠가 안 변했다는 뜻이므로, registry에 이미 있는 값을
그대로 유지하는 게 맞다(다른 필드들과 동일한 패턴).

### 2.3 손대지 말 것

- `core/document_context.py`, `core/identity_registry.py` — Task Order 017에서
  이미 완료, 이번 작업은 값 배선만
- `ui/pages/dashboard.py`, `scripts/report_chunk_summary.py`,
  `ui/pages/sermon_review.py` — 이미 `doc_type`을 올바르게 읽고 있음(값이
  없어서 "?"였을 뿐), 렌더링 로직 자체는 수정 대상 아님
- 기존에 이미 registry에 등록된 문서(과거 처리분)의 `doc_type=None`을
  일괄 백필하는 마이그레이션 — 이번 배선은 **앞으로 (재)처리되는 문서부터만**
  적용된다. 기존 문서 백필이 필요하면 별도 스크립트/Task Order로 분리 제안할 것
  (예: `scripts/backfill_doc_type.py`류) — 이번 범위에 포함하지 않는다

---

## 3. 검증 계획

1. **단위/통합 테스트**: `core/processing.py`의 PROCESS 경로를 실행하는 기존
   테스트(예: `tests/test_processing.py` 또는 관련 파일)에서, 처리 완료 후
   registry record의 `doc_type`이 `guess_doc_type()` 결과와 일치하는지
   검증하는 테스트 추가
2. **SKIP 경로 테스트**: 기존 `existing_record`에 `doc_type` 값이 있는 상태로
   SKIP 처리했을 때, 결과 record의 `doc_type`이 그대로 유지되는지 검증
3. **회귀 확인**: `pytest tests/ -k "processing or document_context"` 범위로
   좁혀서 실행 — 전체 회귀는 불필요
4. **실사용 확인(선택, 가능하면)**: 실제 문서 하나를 파이프라인으로 처리해
   registry에 `doc_type`이 채워지는지, 대시보드에서 "?" 대신 실제 유형이
   표시되는지 스크린샷 없이 registry JSON만으로도 확인 가능

---

## 4. 보고 형식

1. 코드 diff (`core/processing.py` 두 곳)
2. 신규/수정 테스트 diff + `pytest --collect-only -q` 실제 결과
3. 관련 테스트 통과 여부
4. 기존 등록 문서 백필이 이번 범위에 없다는 점 재확인 — 필요하면 후속 제안

---

**다음 조치**: 이 Task Order 완료 후에도 여전히 기존 등록 문서들은
`doc_type=None`으로 남는다 — 대시보드에서 "과거 문서 전부 '?' 표시"가
계속 보이면 그건 이 배선이 실패한 게 아니라 백필이 필요한 것임을 헷갈리지
말 것.
