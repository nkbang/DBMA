# ADR-034 Sentence-Window Context Expansion — Build Report 001

- 근거: [docs/architecture/ADR-034-Sentence-Window-Context-Expansion.md](architecture/ADR-034-Sentence-Window-Context-Expansion.md)
- 선행 게이트: 설계 승인(사용자, 2026-09-18) → C1 Task Order 061 APPROVE
  (`docs/agents/c1/C1-TASK-ORDER-061-REPORT.md`)
- 일자: 2026-09-18

---

## 1. 구현 범위

`core/retrieval.py`에만 추가 — 신규 함수/파라미터, 기존 시그니처는 하위
호환(옵션 인자, 기본값으로 기존 동작 유지 안 됨: `CONTEXT_WINDOW_NEIGHBORS`
기본값 1이 ADR/C1 승인값이라 기본 활성 상태, 아래 §4 참고).

| 위치 | 변경 |
|---|---|
| `core/config.py` | `CONTEXT_WINDOW_NEIGHBORS`(기본 1, `rag.context_window_neighbors`로 override 가능) 신설 |
| `core/retrieval.py::RetrievalEngine.__init__` | `_chunk_id_to_idx`, `_doc_chunk_order` 초기화 + `_build_neighbor_index()` 호출 (로드 시 1회) |
| `core/retrieval.py::RetrievalEngine._build_neighbor_index()` | 신규 — 기존 `document_id`/`chunk_id` 필드만으로 인덱스 구축, TSU 스키마/파이프라인 무변경 |
| `core/retrieval.py::RetrievalEngine.get_neighbor_context()` | 신규 — (before, after) `(chunk_id, content)` 리스트 반환, 문서 경계/미인식 시 빈 리스트 |
| `core/retrieval.py::ContextAssembler.assemble()` | `neighbor_lookup`/`num_neighbors` 옵션 파라미터 추가, LLM 컨텍스트 블록에서만 이웃 텍스트 이어붙임(이미 top_k에 있는 chunk는 dedup) |
| `core/retrieval.py::QueryProcessor.process()` | `assemble()` 호출에 `self.engine.get_neighbor_context`/`CONTEXT_WINDOW_NEIGHBORS` 전달 |

**변경하지 않은 것**(ADR/C1 검증 대상 그대로 유지):
- `RetrievalEngine.retrieve()` 랭킹/스코어링 파이프라인 — 무변경
- `RankedCandidate.content`/`final_score`/`metadata` — 이웃 확장이 원본 객체를 절대 수정하지 않음(테스트로 검증)
- `CitationBuilder.build_citations()` — `candidate.content[:200]` 그대로, 이웃 텍스트 비노출
- TSU 스키마, `core/tsu_builder.py` — 무변경

---

## 2. 테스트

신규: [tests/test_sentence_window_context_expansion.py](../tests/test_sentence_window_context_expansion.py) 12건
- `RetrievalEngine.get_neighbor_context()`: 중간/첫/끝 청크, 단일 청크 문서, 미인식 chunk_id, document_id 누락, num_neighbors=0, 문서 경계 미교차 — 7건
- `ContextAssembler.assemble()`: lookup 미지정 시 기존 동작 그대로, 이웃 삽입, top_k 중복 dedup, RankedCandidate 원본 무변경 — 5건

```
tests/test_sentence_window_context_expansion.py .......... 12 passed
```

## 3. 회귀

```
tests/ 전체: 2986 passed, 17 skipped, 0 failed (92s)
```
(기존 `tests/test_context_assembler_source_label.py`, `test_query_enhancements_full_regression.py`,
`test_book_alias_resolution.py` 등 RetrievalEngine/ContextAssembler 계약 테스트 포함 — 전부 PASS,
neighbor_lookup 미전달 시 기존 시그니처와 동일하게 동작함을 확인)

## 4. 실측 (C1 조건부 권고 #1 이행)

합성 코퍼스(84,000 TSU, 2,000 문서 × 42청크 — C1 리포트가 인용한 실제 규모
84,766건과 근접)로 측정:

| 항목 | 값 |
|---|---|
| `_build_neighbor_index()` (로드 시 1회) | 10.34 ms |
| `get_neighbor_context()` 호출당 | ~0.0008 ms |
| `RetrievalEngine.__init__` 총(로드+인덱스) | 102.8 ms |

ADR §Consequences가 예상한 "무시 가능한 수준"과 일치. 실제 프로덕션 TSU
데이터셋으로는 이 워크트리에 파일이 없어(gitignore) 재현하지 못함 —
합성 벤치마크로 대체.

**남은 실측(미이행)**: Top-K 후보가 같은 문서에 밀집될 때 컨텍스트 블록
길이 증가량(토큰 예산 영향) — `_apply_document_diversity()`가 이미 밀집도를
제한하고 있어(C1 리포트 §3 리스크1) 낮은 리스크로 평가되나, 실제 골든셋
질의로 Before/After 블록 길이 비교는 아직 안 함. 프로덕션 트래픽 관찰
또는 골든셋 재실행으로 후속 확인 권장.

## 5. Git

- STATUS: 구현 완료, 테스트/회귀 PASS
- Changed Files: `core/config.py`, `core/retrieval.py`,
  `tests/test_sentence_window_context_expansion.py`(신규),
  `docs/architecture/ADR-034-Sentence-Window-Context-Expansion.md`,
  `docs/ADR-034-SENTENCE-WINDOW-BUILD-REPORT-001.md`(신규, 이 문서)
- Commit/Push: **보류 — 사용자 확인 대기**. CLAUDE.md CUE Operating Policy
  예외 목록의 "Retrieval Engine 변경"은 ADR/C1 승인과 별개로 커밋·푸시
  자동화에서 항상 승인을 요구하므로, 여기서 멈추고 확인을 구한다.

## 6. Next

- 사용자 승인 시 commit → push
- 병합 후: 실제 TSU 데이터셋으로 §4 남은 실측(블록 길이 증가) 확인
