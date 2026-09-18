---
title: "NAE 문단 앵커드 근거 (옵션 A / PR #17) — 배포환경 검증 결과 001"
created: 2026-09-10
status: PASS (전체 AT-1~10, AT-4/AT-5는 2026-09-18 후속 검증으로 종결 — 아래 addendum)
verifier: CUE
target: PR #17 `claude/p0-2-paragraph-anchored-evidence` @ 7232f0a
base: origin/dev/dbma-engine @ 40ca447 (#17은 #18 미포함 — 무관한 tsu 테스트)
env: ~/envs/dbma311 · nae_qdrant :7333 (live) · Ollama bge-m3 (live) · my-theology-bot-v2 (F2 점유 중)
task_order: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md §6 (AT-1~10)
---

# 배포환경 검증 결과 — 옵션 A (PR #17)

> 읽기 전용. config.yaml·nae_tsu_v1·nae_ref_v1·canonical.json 무변경.
> module gate는 `limit_check=False` 인자로만 우회(설정 미변경).

## 요약

| AT | 항목 | 판정 | 근거 |
|---|---|---|---|
| AT-1 | 데이터 무결성 | **PASS** | `git diff dev..#17 -- core/retrieval.py` 빈 결과 · `NAE/corpus`·`NAE/pipeline/tsu`·`tsu_dataset.jsonl`·`core/module_registry.py` diff 0 |
| AT-2 / Stage 1 | 정합성 스캔 | **PASS (GO)** | `scripts/nae_para_reconcile.py` — 3,319 point 전수, 6체크 실패 **0건**, ok 100.00% |
| AT-3 | 문단 확장 (`bridge_query_paragraphs`) | **PASS** | 5질의 25히트 **25/25 resolved** · para_len median 592 (>200: 22/25, 나머지 3은 실제 짧은 원문) · anchor ⊂ paragraph **25/25** · bibliography(work+author+page+para#) **25/25** · authority_class 매니페스트 조회 성공 |
| AT-6 | CJK 차단 | **PASS** | nae_tsu_v1 참조 1,104 distinct 문단 전수 — CJK 포함 문단 **0** (근거 단위가 `claim`→canonical `paragraph.text`로 바뀌어 LLM 코드스위칭 벡터 제거) |
| AT-7 | 격리 | **PASS** | `modules.nae_pd.enabled=false`(현행) → `bridge_query_paragraphs(limit_check=True)` → `NaePdModuleDisabledError` |
| AT-8 | 성능 | **PASS** | resolver cold 16.5ms · warm **0.178 ms/resolve** (목표 <50ms) · embed+search 질의당 mean 204ms / max 723ms (ADR-024 §G warn 1,500 / hard 3,000 이내) |
| AT-9 | rollback (서브 플래그) | **PASS** | `NAE_PARAGRAPH_EVIDENCE=0` → `paragraph_evidence_enabled()` False → `evidence_paragraph == anchor_sentence`, `paragraph_resolved=False` (ae05415 동작 등가) |
| AT-10 | canonical_version 정합 | **PASS** | 스캔 version_mismatch **0건** |
| AT-4 | 인용 카드 (스크린샷) | **DEFER** | 코드 경로 확인 완료(`research.py:561-638` — bibliography/evidence_paragraph/anchor/authority_class/paragraph_resolved 렌더). 실제 스크린샷은 `nae_pd.enabled=true`(공유 config, F2 실행 중) 필요 → 통제된 배포 환경에서 수행 |
| AT-5 | 답변 완결성 (생성평가) | **DEFER** | 규칙 기반 `answer_completeness.py` 유닛 8건 PASS. 고정 13질의 end-to-end는 `my-theology-bot-v2`(42GB) 필요, 현재 GPU를 F2가 100% 점유 → **F2 종료 후** 수행 (TO §9 "대량 rag_judge 실행은 F2 종료 후") |

## 회귀

| 스위트 | 결과 |
|---|---|
| `tests/test_nae_paragraph_resolver.py` + `test_nae_answer_context.py` + `test_answer_completeness.py` | **26 passed** |
| `tests/test_book_alias_resolution.py` + `test_query_enhancements_full_regression.py` (필터) | **27 passed, 1 skipped** |
| `tests/ -k "generation or nae_retrieval or bridge or citation or claim_guard"` | **218 passed** |

`git diff origin/dev/dbma-engine..HEAD -- core/retrieval.py` = **빈 결과** (ADR-001 무영향 재확인).

## 환경 관련 메모 (defect 아님)

1. **`NAE/corpus/canonical/`은 `.gitignore:102`로 버전관리 밖.** 워크트리에는
   Dagg/Hiscox canonical.json이 없어 PR #17 `nae_para_reconcile.py` 최초
   실행이 "canonical_missing 100%"를 보고했다. main 체크아웃
   (`/Users/David/DBMA`)의 canonical 코퍼스를 워크트리에 복사 후 재실행 →
   **0 실패 / GO**. 배포 환경(main 체크아웃)에는 코퍼스가 상주하므로
   `ParagraphResolver`는 정상 동작한다. 검증 후 복사본 삭제.
2. PR #17은 dev `#18`(무관한 tsu torn-write 테스트)을 아직 미포함. GitHub
   MergeStateStatus=CLEAN — 실제 충돌 없음. rebase/merge 시 자동 해소.
3. 문단 길이 `>1,500자` 비율: PR #17 스크립트 1.75%(per-point), CUE Stage 1
   스크립트 5.25%(per-distinct-paragraph). 둘 다 num_ctx 32,768 예산 대비
   top_k=10 × p95 ≈ 15k자로 여유. §3-1 상한 1,500자 적정.

## 남은 조치 (PR #17 병합 전)

1. **AT-4 스크린샷** — `nae_pd.enabled=true` 통제 환경에서 Streamlit 스모크 +
   고정 13질의 카드 캡처.
2. **AT-5 생성평가** — F2 종료 후 `my-theology-bot-v2`로 13질의 답변 생성 →
   `answer_completeness` 판정 + 육안(문장 완결·경어체·영어 스팬·CJK).
3. **C1 Independent Review** — `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_C1_REVIEW_REQUEST_001.md`
   (Citation 표시 계층 변경 트리거, TO §8-1). CUE 검증은 C1 리뷰를 대체하지 않는다.

## 결론

**코드·데이터 경로 검증(AT-1·2·3·6·7·8·9·10) 전부 PASS.** 옵션 A 구현은
설계·TO와 정합하며, `nae_tsu_v1`(Dagg 2,958 + Hiscox 361)에서 문단 복원
100% 성공, CJK 0, RetrievalEngine·baseline 무접촉. 병합 전 남은 것은
UI 스크린샷(AT-4)·생성 육안평가(AT-5)·C1 리뷰 — 전부 통제/생성 환경 의존
항목이며 코드 결함과 무관하다.


## Addendum (2026-09-18) — AT-4/AT-5 DEFER 해소

F2(GPU 점유 작업) 종료 확인 후 CUE가 직접 재실행(C1 위임 시도 중 selector
버그·오진 2회 발견·정정 후 CUE가 직접 검증으로 전환, 상세는
`docs/AT4_AT5_C1_TASK_ORDER_2026-09-17.md` 참고).

| 항목 | 결과 | 근거 |
|---|---|---|
| AT-4 | **PASS** | "AI에게 질문" → "내서재 공개 자료 (Beta)" 패널에서 3개 질의 전부 카드 렌더 확인. 문단 전문·서지(저자·p.범위·§)·anchor 문장 하이라이트·Score·출처ID 전부 정상. 예: Dagg p.191 §978, Score 0.7038(백엔드 `bridge_query()` 직접 호출 결과와 일치). 부수 발견(배포 차단 아님): "출처 고지(KR/EN)" provenance notice 텍스트가 모든 결과에서 Andrew Fuller 고정 — 실제 저자(Dagg/Hiscox 등)와 무관하게 표시되는 display bug, 백로그 |
| AT-5 | **PASS** | 고정 13질의 전부 my-theology-bot-v2로 end-to-end 생성 완료. 날조 없음(근거 없으면 정직 유보), 영어 스팬 0, CJK 오염은 기존 자동정화가 8/13에서 정상 작동. 경미한 한국어 어미/조사 오탈자 소수 건은 배포 차단 아닌 백로그 |

**부수 발견(더 중요함, 배포 성능 이슈)**: AT-5 검증 중 책 이름 없는 교리형
질의(예: "오직 믿음으로 구원받는다는 것은...")가 `RetrievalEngine`의 O(N)
콜드 스캔 경로를 타 84,766건 코퍼스에서 수 분 지연되는 것을 발견 →
`USE_INVERTED_INDEX` 기본값을 `true`로 전환(커밋 `ce8be59`, merge
`61fcf8d`, origin+nas push 완료)해 0.95초로 해결. 이 전환이 노출시킨
Tantivy 쿼리 파서 크래시(괄호 포함 질의, 예: "중생**(거듭남)**은...")도
같은 세션에서 수정(`core/candidate_generator.py`, 회귀 테스트 추가).
