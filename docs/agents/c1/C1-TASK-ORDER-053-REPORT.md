# C1 Task 053 — 보고서 (재작업본): Chat 파일 선택 목록에서 삭제된 원본 필터링

## §-1. 반려 사유 재확인

이전 제출본에서 `registry_path=None`일 때 `tsu_dataset_path`에서 registry 경로를 **추론**하는 로직을 넣었다. 이 추론 가정이 실제 설정과 맞지 않아 프로덕션에서 버그가 그대로 재현되었다:

```
DEFAULT_TSU_DATASET_PATH = "output/bench/tsu_dataset.jsonl"
DEFAULT_OUTPUT_DIR       = "data/제련완성본" (config.yaml override 시)
DEFAULT_REGISTRY_PATH    = "data/제련완성본/registry/documents.json"  ← 실제 정답

C1의 추론 결과          = "output/registry/documents.json"           ← 존재하지 않음
```

추론된 경로가 존재하지 않으므로 `registry_path`가 `None`으로 남고, "후진 호환성" 분기가 TSU 원본을 필터링 없이 그대로 반환 — 원래 버그 재현.

## §1. 근본 원인 (재확인)

`core/retrieval.py:1276` `list_source_files()`:

```python
def list_source_files(self) -> list[str]:
    """Unique tsu["source_file"] values in the loaded corpus, sorted."""
    return sorted({sf for t in self.tsus if (sf := t.get("source_file"))})
```

TSU 데이터셋(`self.tsus`)에 있는 `source_file`을 그대로 중복제거해 반환 — **registry나 RAW와 전혀 대조하지 않음**.

## §2. 수정 내용

### 선택한 대안: Core 함수 수정 (§2 첫 번째 옵션)

`list_source_files()` 의 `registry_path` 기본값을 `core.config.DEFAULT_REGISTRY_PATH` 상수로 변경 — 추론 로직 완전히 삭제.

**이유**:
1. **지시사항 준수**: CUE가 명시적으로 "`registry_path`를 `core.config.DEFAULT_REGISTRY_PATH`로 기본값 지정" 지시
2. **관례 일치**: 같은 파일의 `QueryProcessor.__init__`이 `RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)`처럼 상수 기본값을 사용
3. **추론 불필요**: `DEFAULT_REGISTRY_PATH` 상수가 항상 실제 registry 위치를 가리키므로 추론 필요 없음
4. **후진 호환성 유지**: registry 파일 자체가 없는 신규 설치 대응 — "registry 없으면 TSU 원본 그대로" 분기 유지

### 변경 diff (core/retrieval.py)

**① import 추가 (line 40)**:
```diff
- from core.config import DEFAULT_TSU_DATASET_PATH, RETRIEVAL_DOCUMENT_CAP
+ from core.config import DEFAULT_REGISTRY_PATH, DEFAULT_TSU_DATASET_PATH, RETRIEVAL_DOCUMENT_CAP
```

**② `list_source_files()` 메서드 (line 1276-1302)**:
```diff
-    def list_source_files(self, registry_path: str | None = None) -> list[str]:
-        """Unique source_file values in the loaded corpus that are still valid
-        in the identity registry (ingest_status == "PROCESSED" and no
-        superseded_by), sorted. Used by UI file-scope pickers.
-
-        Args:
-            registry_path: Optional explicit path to documents.json. If omitted,
-                inferred from tsu_dataset_path (assumes the standard layout where
-                tsu_dataset_path is under {output_dir}/bench/).
-        """
-        if registry_path is None:
-            # Infer from tsu_dataset_path: output/bench/tsu_dataset.jsonl -> output/registry/documents.json
-            inferred = Path(self.tsu_dataset_path).parent.parent / "registry" / "documents.json"
-            if inferred.exists():
-                registry_path = str(inferred)
-
-        registry_provided = registry_path is not None and os.path.exists(registry_path)
+    def list_source_files(self, registry_path: str = DEFAULT_REGISTRY_PATH) -> list[str]:
+        """Unique source_file values in the loaded corpus that are still valid
+        in the identity registry (ingest_status == "PROCESSED" and no
+        superseded_by), sorted. Used by UI file-scope pickers.
+
+        Args:
+            registry_path: Path to documents.json. Defaults to
+                DEFAULT_REGISTRY_PATH from core.config. If the registry file
+                does not exist, returns all TSU source_files (backward
+                compatibility for installations without a registry).
+        """
         valid_sources: set[str] = set()
-        if registry_provided:
+        if os.path.exists(registry_path):
             from core.identity_registry import load_identity_registry
             registry = load_identity_registry(registry_path)
             for doc in registry.get("documents", {}).values():
@@ -1304,7 +1298,7 @@
                         valid_sources.add(sf)

         result = {sf for t in self.tsus if (sf := t.get("source_file"))}
-        if registry_provided:
+        if os.path.exists(registry_path):

         return sorted(result)
```

**핵심 변경점**:
1. **추론 로직 완전 삭제**: `registry_path=None`일 때 inferred path 계산하는 코드 제거
2. **기본값을 상수로**: `registry_path: str = DEFAULT_REGISTRY_PATH` — 실제 config 상수 사용
3. **간소화된 조건부**: `registry_provided` 플래그 대신 `os.path.exists(registry_path)` 직접 사용
4. **후진 호환성 유지**: registry 파일이 없으면 TSU 원본 그대로 반환

## §3. 테스트 결과

### 신규 테스트 (8개, 모두 임시 픽스처 디렉토리 사용)

| # | 테스트 이름 | 검증 내용 | 결과 |
|---|-----------|----------|------|
| 1 | `test_only_valid_processed_files_returned` | registry에 PROCESSED + superseded_by=None 인 문서만 반환 | ✅ PASS |
| 2 | `test_no_registry_file_returns_all_from_tsu` | registry 파일이 없으면 TSU 원본 그대로 반환 (후진 호환성) | ✅ PASS |
| 3 | `test_empty_registry_returns_empty` | registry 가 비어있으면 빈 리스트 반환 | ✅ PASS |
| 4 | `test_missing_registry_file_returns_all_from_tsu` | registry 파일이 없으면 TSU 원본 그대로 반환 | ✅ PASS |
| 5 | ~~`test_inferred_registry_path_used_when_none`~~ | ~~추론 로직 테스트~~ | ❌ **삭제** (추론 로직 삭제됨) |
| 6 | `test_all_registry_docs_excluded_returns_empty` | registry의 모든 문서가 EXCLUDED 이면 빈 리스트 반환 | ✅ PASS |
| 7 | `test_no_source_file_in_registry_ignored` | registry에 source_file 필드가 없거나 빈 문자열인 문서는 무시 | ✅ PASS |
| 8 | `test_deduplication_across_tsu_records` | TSU에 중복 source_file이 있어도 중복 제거됨 | ✅ PASS |
| 9 | **`test_default_values_point_to_config_constants`** (회귀 방지) | **`list_source_files()` 인자 없이 호출 시 `load_identity_registry`가 `DEFAULT_REGISTRY_PATH`로 호출되는지 mock 검증** | ✅ **PASS** |

### 회귀 방지 테스트 상세

**`test_default_values_point_to_config_constants`**:
- `DEFAULT_REGISTRY_PATH`와 `DEFAULT_TSU_DATASET_PATH`를 실제로 import
- `RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH).list_source_files()` 인자 없이 호출
- `load_identity_registry`를 mock으로 patch하여 어떤 경로로 호출되었는지 확인
- **이 테스트가 없으면** "실제 상수 관계를 안 쓰고 임의 추론을 넣는" 실수가 다시 테스트로 통과 — TASK-053 반려 사유와 동일한 실수 방지

### 기존 관련 테스트 통과 결과

**실행 명령**: `pytest tests/test_retrieval_missing_dataset.py tests/test_retrieval_book_coverage.py tests/test_retrieval_lazy_tfidf.py tests/test_list_source_files_registry_filter.py -v`

**결과**: 17개 테스트 모두 통과 (0 실패)

| 파일 | 테스트 수 | 결과 |
|------|----------|------|
| test_list_source_files_registry_filter.py | 8 | ✅ 모두 PASS |
| test_retrieval_missing_dataset.py | 2 | ✅ 모두 PASS |
| test_retrieval_book_coverage.py | 3 | ✅ 모두 PASS |
| test_retrieval_lazy_tfidf.py | 4 | ✅ 모두 PASS |
| **합계** | **17** | **✅ 모두 PASS** |

## §4. 변경 범위 자가 점검 (§3 준수)

| 금지 항목 | 준수 여부 |
|----------|----------|
| `core/retrieval.py` 의 다른 메서드/클래스 건드리기 | ✅ `list_source_files()` 만 수정 + import 추가 |
| 실제 data/RAW, data/제련완성본, output/bench/tsu_dataset.jsonl 경로 스크립트로 조회·수정 | ✅ 임시 픽스처 디렉토리만 사용 |
| registry 스키마 변경 | ✅ 변경 없음 |
| `find_orphaned_processed_documents()`/`cleanup_orphaned_document()`/`delete_raw_source()` 로직 변경 | ✅ 변경 없음 |
| 경로 추론 로직 유지 | ✅ **완전 삭제** |

## §5. 대안 선택 근거

**선택**: Core 함수 수정 (§2 첫 번째 옵션) — `registry_path: str = DEFAULT_REGISTRY_PATH`

**근거**:
1. **지시사항 준수**: CUE가 명시적으로 "registry_path를 core.config.DEFAULT_REGISTRY_PATH로 기본값 지정" 지시 — 선택이 아님
2. **관례 일치**: 같은 파일의 `QueryProcessor.__init__`이 `RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)`처럼 상수 기본값 사용
3. **추론 불필요**: `DEFAULT_REGISTRY_PATH` 상수가 항상 실제 registry 위치를 가리킴
4. **회귀 방지 테스트**: 실제 상수 값을 써서 검증 — 이번처럼 "실제 상수 관계를 안 쓰고 임의 추론을 넣는" 실수가 테스트로 걸러짐
5. **후진 호환성**: registry 파일이 없으면 TSU 원본 그대로 반환 — 신규 설치 상황 대응

---

## §6. CUE 최종 판단 (CUE 작성)

| 항목 | 판정 | 근거 |
|---|---|---|
| 추론 로직 제거 + `DEFAULT_REGISTRY_PATH` 기본값 | **채택 — PASS** | `core/retrieval.py:1276` 직접 대조, `inferred`/`parent.parent` 잔존 없음 확인 |
| `DEFAULT_REGISTRY_PATH`가 실제 프로덕션 registry를 가리킴 | **확인 — PASS** | CUE가 직접 재계산·`os.path.exists()` 확인, True |
| 회귀 방지 테스트 (`test_default_values_point_to_config_constants`) | **확인 — PASS** | mock 검증 방식이 실제로 이번 반려 사유를 재현·차단하는 구조인지 코드 읽고 확인 |
| 17개 테스트 | **확인 — PASS** | CUE가 직접 재실행 |
| 변경 범위 준수 | **확인 — PASS** | `core/retrieval.py` 33줄 diff만, 범위 밖(사전 존재하던 무관한 수정 포함) 없음 |
| 절차(C1이 CUE 판단·종료를 대신 쓰지 않음) | **준수 확인** | 이번 보고서에는 없음 — 정상 |

**TASK-053 — CUE가 지금 이 보고서로 공식 종료한다.** 반려 사유(경로 추론이
실제 설정과 불일치)가 근본적으로 해소됐고, 재발 방지 테스트까지
확보됐다. 실제 브라우저 화면 확인은 범위에 없었으므로 해당 없음.
