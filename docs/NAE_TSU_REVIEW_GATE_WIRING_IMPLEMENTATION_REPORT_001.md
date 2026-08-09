# NAE TSU Review Gate Wiring Implementation Report 001

**Project:** NAE-TSU-REVIEW-GATE-WIRING-IMPLEMENTATION-001
**작성일:** 2026-08-07
**성격:** Review Gate를 실제 Indexer 입력 경로에 배선 — BGE-M3 실행,
Qdrant 생성, Vector Index 생성 전부 미수행(dry-run만).
**Git Commit/Push:** 미수행.

---

## Index Flow

### Before

```
tsu.json (또는 tsu_verified.json)
        ↓ (review_status 검사 없음 — tsu_verified.json 존재 여부만 확인)
Indexer(load_records)
        ↓
Embedding
```

### After

```
tsu.json (또는 tsu_verified.json)
        ↓
Review Gate(filter_embedding_eligible — review_status=="verified"만 통과)
        ↓ PASS
Indexer(load_records_with_gate_summary)
        ↓
Embedding(dry_run=False일 때만 — 이번 작업은 dry_run만 검증)
```

`load_records()`는 기존 시그니처를 그대로 유지하면서 내부적으로
Gate를 통과한 레코드만 반환하도록 바뀌었다 — 기존 호출자(있다면)는
코드 수정 없이 자동으로 보호받는다.

---

## Files

### 생성

```
tests/test_indexer_review_gate_wiring.py
docs/NAE_TSU_REVIEW_GATE_WIRING_IMPLEMENTATION_REPORT_001.md
```

### 변경

```
NAE/pipeline/index/indexer.py
```

주요 변경:
1. `load_records_with_gate_summary()` 신규 — `review_gate.
   filter_embedding_eligible()`을 호출해 Gate를 통과한 레코드 +
   집계(`ReviewGateBatchSummary`)를 함께 반환
2. `load_records()`는 위 함수에 위임(하위 호환 시그니처 유지)
3. `index_identifier()`에 `dry_run: bool = False` 파라미터 추가 —
   `True`면 embedding 호출/Qdrant 접근/파일 쓰기 전부 건너뛰고
   `gate_pass`/`gate_block`/`would_index`만 계산해 반환
4. `index_all()`에도 `dry_run` 전달 경로 추가
5. 손상된 TSU 파일(JSON 파싱 실패, list가 아닌 형식) 처리 —
   예외 대신 빈 결과로 graceful degradation(배치 전체가 죽지 않음)

**`core/retrieval.py`, `builder.py`, Crosswalk schema, Manifest,
Registry, RAW, Canonical — 전부 무수정**(§Forbidden Path Check).

---

## 필수 테스트 대응(10개 항목, `tests/test_indexer_review_gate_wiring.py` 28개)

| 요구 항목 | 테스트 클래스 |
|---|---|
| 1. generated → index 제외 | `TestGeneratedExcluded`(2) |
| 2. reviewed → index 제외 | `TestReviewedExcluded`(2) |
| 3. verified → index 포함 | `TestVerifiedIncluded`(2) |
| 4. rejected → index 제외 | `TestRejectedExcluded`(2) |
| 5. missing review_status → index 제외 | `TestMissingReviewStatus`(2) |
| 6. tsu_verified.json 존재 vs review_status=verified 혼동 방지 | `TestVerifiedFileVsReviewStatusNotConflated`(3) |
| 7. batch indexing | `TestBatchIndexing`(2) |
| 8. empty corpus | `TestEmptyCorpus`(3) |
| 9. corrupted TSU | `TestCorruptedTsu`(3) |
| 10. regression(시그니처 하위호환) | `TestRegression`(2) |
| (추가) dry-run 부작용 없음 | `TestDryRunNoSideEffects`(2) |
| (추가) 실제 Production 데이터 dry-run 검증 | `TestProductionTsuReadOnlyDryRun`(3) |

```
$ pytest tests/test_indexer_review_gate_wiring.py -q
28 passed(요구 20건 초과)
```

### 항목 6 상세(가장 중요한 검증)

```python
# tsu_verified.json이 존재해도(중복탐지 완료) review_status가
# verified가 아니면 여전히 제외된다.
_write_tsu(tmp_path, "Book", [_tsu_record(review_status="generated")], filename="tsu_verified.json")
assert indexer.load_records("Book", tsu_root=tmp_path) == []
```

이 테스트가 `NAE_TSU_REVIEW_GATE_IMPLEMENTATION_REPORT_001.md`가
지적한 "이름 충돌"(tsu_verified.json의 "verified" ≠ review_status의
"verified") 문제가 실제로 해소됐음을 증명한다.

---

## 검증(Task 지시 항목)

### indexer 실제 실행 dry-run

실제 Production TSU(`NAE/corpus/tsu/`, Dagg 2건 + Hiscox 0건, 전부
`review_status="unverified"`)를 대상으로 `index_all(dry_run=True)`
실행:

```python
>>> indexer.index_all(dry_run=True)
{'processed': 2, 'indexed': 0, 'identifiers': [
    {'identifier': 'Hiscox_Standard_Manual', 'indexed': 0},
    {'identifier': 'Dagg_Church_Order', 'indexed': 0}
]}
```

**`indexed: 0` — 배선 전이었다면(이전 코드) `tsu_verified.json`이
없으므로 `tsu.json`을 그대로 읽어 2건이 embedding 후보가 됐을
것이다. 배선 후에는 review_status가 전부 `unverified`이므로 정확히
차단됐다.**

### embedding 실행 금지 확인

`dry_run=True` 경로는 `embed_client.embed_text()`를 호출하는 코드
분기에 아예 도달하지 않는다(코드상 `if dry_run: return {...}`로
early return, §Files 변경사항 3). 실행 중 Ollama/embedding 서비스
호출 없음(에러 없이 즉시 반환된 것이 그 증거 — 서비스가 떠있지
않아도 dry-run은 항상 성공).

### vector DB 변경 금지 확인

동일한 이유로 `qdrant_store.get_client()`/`ensure_collection()`/
`upsert_points()` 전부 dry-run 분기에서 호출되지 않는다.

```
$ find NAE/corpus/tsu -name "index_report.json"
(결과 없음 — dry-run은 파일도 쓰지 않음)
```

---

## Regression

```
$ pytest tests/test_crosswalk*.py tests/test_tsu_pipeline_wiring.py \
         tests/test_manual_crosswalk_pilot.py tests/test_tsu_review_gate.py \
         tests/test_indexer_review_gate_wiring.py \
         tests/test_source_validator_v2.py tests/test_validator_v22.py \
         tests/test_manifest_validator.py tests/test_authority_validator.py \
         tests/test_authority_validator_canonical.py tests/test_migration_lock.py \
         tests/test_migration_checkpoint.py tests/test_migration_engine.py \
         tests/test_registry_adapter.py tests/test_manifest_adapter.py \
         tests/test_pilot_executor.py tests/test_comment_preservation.py -q
387 passed(직전 359 + 신규 28, 감소 없음)
```

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## Forbidden Path

```
$ git diff --stat core/retrieval.py NAE/pipeline/tsu/builder.py scripts/crosswalk/schema.py
(출력 없음 — 전부 0줄 변경)

$ git status --short core/ resources/theological_sources/ NAE/corpus/raw NAE/corpus/canonical docs/architecture/ | grep "^ M"
(M로 시작하는 줄 없음)
```

**PASS.**

---

## 완료 보고

```
STATUS: COMPLETE (Review Gate wired into indexer.py — dry-run verified only, no embedding/Qdrant execution)

FILES CREATED:
tests/test_indexer_review_gate_wiring.py
docs/NAE_TSU_REVIEW_GATE_WIRING_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
NAE/pipeline/index/indexer.py (load_records_with_gate_summary 신규, load_records 내부 위임, index_identifier/index_all에 dry_run 파라미터 추가, 손상 TSU 파일 graceful 처리)

INDEX FLOW BEFORE:
tsu.json/tsu_verified.json -> Indexer(review_status 미검사) -> Embedding

INDEX FLOW AFTER:
tsu.json/tsu_verified.json -> Review Gate(review_status=="verified"만) -> Indexer -> Embedding

TEST:
28 passed(요구 20건 이상, 10개 필수 항목 전부 커버)

REGRESSION:
387 passed(직전 359 + 신규 28, 감소 없음)

DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0)

FORBIDDEN PATH:
PASS (core/retrieval.py, builder.py, Crosswalk schema, Manifest, Registry, RAW, Canonical 전부 무수정)

BLOCKER:
0

WARNING:
0(직전 보고서의 WARNING 1번 — "Gate가 배선되지 않음" — 이번 작업으로 해소됨. WARNING 2번 — tsu_verified.json/review_status 이름 충돌 — 코드는 두 개념을 정확히 분리해 처리하도록 배선했으나, 파일명 자체의 혼동 소지는 여전히 남아있어 향후 문서화 보강 권고로 격하)

NEXT STEP:
실제 review_status="verified" 승격 절차(사람이 TSU claim 품질을 확인하는 워크플로우, 아직 미설계) 정의 → 승격 후 실제 embedding/Qdrant 실행(dry_run=False)은 별도 승인 작업

GIT:
NOT PERFORMED
```
