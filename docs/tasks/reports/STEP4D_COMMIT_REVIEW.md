# STEP4-D Commit Review

작성일: 2026-07-31
상태: Implementation APPROVED — **commit 미실행, HQ 승인 대기**

## 포함 파일 (Commit 대상)

1. `scripts/ingest_nae_source.py` (신규)
2. `core/tsu_builder.py` (수정, +18줄 — `git diff` 확인: `nae_metadata` additive 블록만 추가, 기존 코드 무변경)
3. STEP4-D 관련 reports 문서 (`docs/tasks/reports/` 하위):
   - STEP3 계열: `STEP3_TSU_PIPELINE_ANALYSIS.md`, `STEP3_SAMPLE_DOCUMENT_SPEC.md`, `STEP3_TSU_MAPPING.md`, `STEP3_VALIDATION_PLAN.md`, `STEP3_REPORT.md`
   - STEP3-B/C 계열: `NAE_METADATA_BLOCK_DESIGN_v1.md`, `NAE_SOURCE_TYPE_MODEL_v1.md`, `ADR_NAE_THEOLOGICAL_METADATA.md`, `STEP3B_REPORT.md`, `NAE_METADATA_POLICY_v1.md`, `NAE_PILOT_ANNOTATION_TEMPLATE.md`, `STEP3C_REPORT.md`
   - STEP4 계열: `STEP4_TSU_PIPELINE_ANALYSIS.md`(중복 표기 방지 — 실제 파일명은 STEP3 소속), `STEP4_SOURCE_REGISTRATION.md`, `STEP4_PIPELINE_DRYRUN.md`, `STEP4_TSU_QUALITY_CRITERIA.md`, `STEP4_READINESS_REPORT.md`
   - STEP4-A 계열: `NAE_SOURCE_REGISTRY_SCHEMA_v1.md`, `STEP4_PILOT_SOURCE_ENTRY.md`, `STEP4_PD_VERIFICATION.md`, `STEP4_CODE_IMPACT_REVIEW.md`
   - STEP4-B 계열: `STEP4_PROCESSING_METADATA_FLOW.md`, `STEP4_METADATA_FLOW_DIAGRAM.md`, `STEP4_METADATA_ADAPTER_PROPOSAL.md`
   - STEP4-C 계열: `NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md`, `NAE_METADATA_INPUT_STRATEGY.md`, `NAE_METADATA_ADAPTER_TEST_PLAN.md`, `STEP4C_REPORT.md`
   - STEP4-D 계열: `STEP4D_IMPLEMENTATION_PLAN.md`, `STEP4D_TEST_REPORT.md`, `STEP4D_REPORT.md`, 본 문서(`STEP4D_COMMIT_REVIEW.md`)

## 제외 파일 (Commit 대상 아님)

- `core/config.py` — 이번 세션에서 생성하지 않은 기존 미커밋 변경(+14줄). [[feedback_concurrent_c1_file_edits]] 기준 다른 세션(C1 등) 소유로 추정.
- `ui/pages/library.py` — 동일 사유(+135줄, -1줄)
- `scripts/sample_library_content/` (신규 디렉토리) — 이번 세션에서 생성하지 않음, `library.py` 변경과 연관된 별도 작업으로 추정
- `scripts/seed_sample_library.py` (신규) — 동일 사유
- `docs/DBMA-UX-003-SAMPLE-LIBRARY-PLAN.md` — 기존부터 미커밋 상태였던 C1 UX 관련 파일 (이전 STEP1/2 세션에서도 동일하게 제외 처리됨)

## git diff --stat (전체, 참고용)

```
core/config.py      |  14 ++++++
core/tsu_builder.py |  18 +++++++
ui/pages/library.py | 135 +++++++++++++++++++++++++++++++++++++++++++++++++++-
3 files changed, 166 insertions(+), 1 deletion(-)
```

→ 이 중 **`core/tsu_builder.py`만 이번 STEP4-D 산출물**. 나머지 2개 파일(config.py/library.py)은 제외 대상.

## git diff -- core/tsu_builder.py (전체 diff, 검증용)

```diff
@@ -436,6 +436,24 @@ def build_tsu_records(registry: dict, output_dir: Path) -> list[dict[str, Any]]:
             else:
                 record["source_provenance"] = None
 
+            # [STEP4-D, docs/tasks/reports/NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md]
+            # Additive-only — same contract as content_quality/structure/
+            # source_provenance above. Populated only for documents whose
+            # registry entry carries nae_theological_position (i.e. ingested
+            # via scripts/ingest_nae_source.py); every field defaults to
+            # None/[] rather than being invented, so non-NAE documents are
+            # unaffected and this block is a no-op for the existing corpus.
+            nae_theological_position = doc.get("nae_theological_position")
+            if nae_theological_position is not None:
+                record["nae_metadata"] = {
+                    "theological_position": nae_theological_position,
+                    "denomination_context": doc.get("nae_denomination_context"),
+                    "content_genre": doc.get("nae_content_genre", []),
+                    "copyright_status": doc.get("nae_copyright_status"),
+                }
+            else:
+                record["nae_metadata"] = None
+
             records.append(record)
 
     return records
```

기존 코드(`source_provenance` 블록 등) 삭제/변경 없음, 순수 추가(+18줄)만 확인됨.

## git status (전체, 참고용)

- Modified(3): `core/config.py`, `core/tsu_builder.py`, `ui/pages/library.py` — 이 중 commit 대상은 `core/tsu_builder.py` 하나
- Untracked 다수: STEP4-D 관련 신규 문서 및 `scripts/ingest_nae_source.py`(포함 대상), `scripts/sample_library_content/`/`scripts/seed_sample_library.py`/`docs/DBMA-UX-003-SAMPLE-LIBRARY-PLAN.md`(제외 대상)

## 테스트 결과 (STEP4D_TEST_REPORT.md 요약)

| 항목 | 결과 |
|---|---|
| 기존 DBMA 문서 regression | PASS |
| NAE metadata 존재 | PASS (synthetic 픽스처) |
| TSU output 보존 | PASS |
| retrieval compatibility | PASS (무수정 근거) |

## Regression 결과

`pytest tests/test_tsu_structure.py tests/test_tsu_manifest.py tests/test_build_tsu_dataset_chapter.py tests/test_build_tsu_dataset_book_id.py tests/test_build_tsu_dataset_verse_mapping.py tests/test_tsu_content_quality.py tests/test_tsu_sermon_fields.py tests/test_tsu_builder_heading_integration.py tests/test_reindex_document.py tests/test_dedupe_tsu_dataset.py`

→ **46 passed, 0 failed**

## 결론

commit 대상은 명확히 분리됨(신규 스크립트 1개 + `core/tsu_builder.py` 1개 + reports 다수). 제외 대상 5건(config.py/library.py/sample_library 관련 3건)은 다른 세션 소유로 추정되며 손대지 않음. **이번 문서 작성만 수행, git add/commit은 실행하지 않았음.**
