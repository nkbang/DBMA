# STEP4-D Test Report

작성일: 2026-07-31

## 테스트 1 — 기존 DBMA 문서 regression 없음

명령: `pytest tests/test_tsu_structure.py tests/test_tsu_manifest.py tests/test_build_tsu_dataset_chapter.py tests/test_build_tsu_dataset_book_id.py tests/test_build_tsu_dataset_verse_mapping.py tests/test_tsu_content_quality.py tests/test_tsu_sermon_fields.py tests/test_tsu_builder_heading_integration.py`

결과: **40 passed** — `core/tsu_builder.py` 수정 후에도 기존 TSU 관련 테스트 전부 통과. 추가로 `tests/test_reindex_document.py`, `tests/test_dedupe_tsu_dataset.py` **6 passed**.

판정: PASS

## 테스트 2 — NAE metadata 존재

방법: 임시 디렉토리(스크래치패드, 운영 `output/` 미사용)에서 `scripts/ingest_nae_source.py`로 테스트 픽스처 1건 ingest → `scripts/build_tsu_dataset.py --dry-run`으로 TSU 생성 확인.

**주의**: 실제 원문(New Hampshire Confession 1833)은 다운로드 승인 대상이 아니었으므로, 이번 테스트는 구조를 흉내 낸 합성 텍스트(synthetic test fixture, 3개 조항)로 진행함 — 명시적으로 "[TEST FIXTURE]"로 라벨링. 실제 원문에 대한 검증은 아직 미실행.

결과 (dry-run TSU record 발췌):
```json
"nae_metadata": {
  "theological_position": "historical_baptist",
  "denomination_context": "Test fixture for STEP4-D pipeline validation",
  "content_genre": ["confession"],
  "copyright_status": "public_domain"
}
```

manifest에 입력한 4개 필드가 정확히 `nae_metadata` 블록에 반영됨을 확인.

판정: PASS (합성 픽스처 기준. 실제 원문 검증은 별도)

## 테스트 3 — TSU output 보존

방법: 위 dry-run 출력에서 기존 필드(`tsu_id`, `document_id`, `content`, `verse_mapping`, `title`, `author`, `content_quality`, `structure`, `theological_claim`, `doctrine_category`, `baptist_theme`, `source_provenance`) 전부 존재 여부 확인.

결과: 전부 정상 존재. `source_provenance: null`(Logos 출처 아니므로 정상), `baptist_theme: []`, `doctrine_category: []`(태깅 로직 미착수이므로 정상). `nae_metadata`는 신규 추가된 필드 1개뿐, 기존 필드 값/타입 변경 없음.

판정: PASS

## 테스트 4 — retrieval compatibility

방법: `core/retrieval.py` 자체를 수정하지 않았고, 신규 필드(`nae_metadata`)를 이 모듈이 읽는 코드가 없음을 코드 조사(STEP4_CODE_IMPACT_REVIEW.md, STEP4-C에서 이미 확인)로 재확인. 이번 STEP4-D에서는 검색 관련 테스트를 별도로 재실행하지 않음(모듈 자체가 무수정이므로 회귀 위험 없음, [[feedback_verification_cost_discipline]] 원칙에 따라 불필요한 전체 재실행 생략).

판정: PASS (코드 무수정 근거)

## 관찰 사항 (버그 아님, 기록용)

- dry-run 결과에서 `verse_mapping: {"book_id": "EST"}`가 나타남 — 픽스처 파일명(`nhc_1833_test_fixture.txt`)의 일부 문자열이 기존 `_resolve_book_id()`(파일명 기반 성경 책 추정 로직, `core/tsu_builder.py`)에 우연히 매칭된 것으로 추정됨. 이는 **이번 변경과 무관한 기존 로직의 동작**이며, `content_genre=["confession"]`인 비-성경 문서에 대해 `verse_mapping`이 의미 없이 채워질 수 있음을 보여주는 사례 — 실제 문서 ingest 시 재확인 필요 항목으로 기록(코드 수정은 이번 범위 밖).

## 종합

| 항목 | 결과 |
|---|---|
| 기존 DBMA 문서 regression | PASS (46 tests) |
| NAE metadata 존재 | PASS (합성 픽스처) |
| TSU output 보존 | PASS |
| retrieval compatibility | PASS (무수정 근거) |
