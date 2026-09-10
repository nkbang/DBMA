---
title: "Build Report — NAE 완성 문단 답변 전달 (옵션 A) 구현 001"
created: 2026-09-10
author: CUE
status: 코드 구현·유닛 검증 완료 · 라이브 Acceptance(Stage 1 게이트·Stage 7)·C1 Review 대기
audit_item: PM 정렬 감사 선결 #4 (P0-2)
design_doc: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md
task_order: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md
base: claude/p0-5-6-tier-bonus-denomination (체인 #11→#12→#13→#14→#15→본 건)
venv: ~/envs/dbma311
---

# Build Report — NAE 완성 문단 답변 전달 (옵션 A)

## STATUS

**코드 구현 + 유닛/회귀 검증 완료.** 라이브 `nae_qdrant`(포트 7333)와 생성
모델이 이 샌드박스 워크트리에 없어 아래는 **미실행 → 배포 환경에서 실행 필요**:
- Stage 1 정합성 게이트 (`scripts/nae_para_reconcile.py` — 딜리버리 완료, 실행 대기)
- Stage 7 Acceptance AT-1/AT-3/AT-5/AT-6/AT-8/AT-10 (라이브 검색·생성 필요)
- Stage 4 Streamlit 스모크 스크린샷
- Stage 8 C1 Independent Review (Citation 표시 계층 변경 트리거 — TO §8-1)

## Changed Files

| 파일 | 종류 | 내용 |
|---|---|---|
| `NAE/pipeline/canonical/paragraph_lookup.py` | 신규 | `ParagraphResolver` — `(identifier, paragraph)` → canonical.json 원문 문단. identifier 단위 `lru_cache`, `neighbors`, `canonical_version` 대조, fail-soft(None) |
| `NAE/answer_context.py` | 신규 | `format_nae_context_block()`(`<자료>` 블록 + 서지 속성 + `<일치문장>` + 길이 상한 축약 + 예산 드롭), `NAE_PARAGRAPH_PROMPT_CLAUSE`, `build_nae_answer_prompt()`, `paragraph_evidence_enabled()` 서브 플래그 |
| `NAE/retrieval_adapter.py` | 수정 | `_map_nae_to_citation_metadata`에 payload pass-through 필드(`identifier`/`paragraph`/`page`/`canonical_version`/`volume_id`) 추가. 신규 `bridge_query_paragraphs()`(→ list[dict], 문단 확장), `_enrich_hit_with_paragraph()`, `_authority_class_for()`. **`bridge_query()`(→ list[Citation], ADR-024 §D)는 바이트 무변경** |
| `core/evaluation/answer_completeness.py` | 신규 | 규칙 기반 한국어 완결성 판정(종결 어미·영어 스팬·오염 문자·경어체·문단 수). 생성 차단 안 함 |
| `ui/pages/research.py` | 수정 | `_execute_nae_retrieval`이 플래그 on이면 `bridge_query_paragraphs` 사용. `_render_nae_paragraph_card()`(문단 전문·서지 라인·앵커 하이라이트·AI 요약 접힘·CJK 배지) / `_render_nae_legacy_card()` 분기 |
| `scripts/nae_para_reconcile.py` | 신규 | Stage 1 정합성 스캔(읽기 전용, 라이브 Qdrant 필요) |
| `docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md` | 신규 | Stage 5-2 rag_judge fluency/completeness 설계 초안 |
| `tests/test_nae_paragraph_resolver.py` / `test_nae_answer_context.py` / `test_answer_completeness.py` | 신규 | 34건 |

## 설계 결정 (TO §10 — 위임 금지 항목)

| # | 결정 | 근거 |
|---|---|---|
| 1 | 리졸버 위치 = `NAE/pipeline/canonical/paragraph_lookup.py` | F2(`NAE/pipeline/tsu/`) 충돌 회피, canonical 계층에 귀속 (TO §2-1) |
| 2 | 컨텍스트 포맷 = 신규 `NAE/answer_context.py` | `core/retrieval.py::ContextAssembler` 무수정(Chat/Research 공용, ADR-001). 설교 `_format_sermon_context` 선례 |
| 3 | **`Citation` dataclass 무변경** | 가정 3 1순위 — `bridge_query_paragraphs`가 별도 `list[dict]` 반환, `bridge_query`/`Citation`/`content_excerpt` 계약 불변 → ADR-024 §C Amendment 불요 |
| 4 | 프롬프트 조항 = 별도 상수 `NAE_PARAGRAPH_PROMPT_CLAUSE` | `_GROUNDING_DIRECTIVE`(ae05415 정본) 재작성 금지. F6 배선 시 `build_nae_answer_prompt()`가 근거강제→문단조항→교단 순서로 조립 |
| 6 | 문단 길이 상한 기본 1500자(`NAE_PARAGRAPH_MAX_CHARS`), 컨텍스트 예산 24000자(`NAE_PARAGRAPH_CONTEXT_BUDGET`) | Stage 1-4 실측 전 보수적 기본값. 초과 시 앵커 중심 window 축약 + 하위 랭크 드롭 |
| 7 | `authority_class` = `NAE/pipeline/registration/state/source_manifest.yaml`(우선) / `NAE/authority/source_manifest.yaml` 조회, 표시 전용 | ADR-030 §7 — TSU 레코드·payload 미기입. 실패 시 키 생략(가정 5) |

## Tests

- 신규: `test_nae_paragraph_resolver.py`(11) + `test_nae_answer_context.py`(9) + `test_answer_completeness.py`(8) + budget 1 = **34 passed**
  - resolver: 문단 verbatim 복원(합성 + 실제 `PBC1765` canonical), 파일/인덱스 부재 → None, canonical_version 불일치 → None, neighbors 결합·경계, identifier 캐시 1회 파싱
  - answer_context: 서지 속성·앵커 문장·200자 절단 없음·상한 축약·unresolved 표시·프롬프트 조항·순서·예산 드롭
  - completeness: 정상 통과 / 빈 답변 / 오염 문자 / 영어 스팬 / 미완결 문장 / 단일 문단 / 경어체 없음
- **회귀 `pytest tests/`: 2930 passed, 15 skipped** (착수 전 2904 + 26)
- 대상 회귀(TO §5): `test_book_alias_resolution`, `test_query_enhancements_full_regression`,
  `-k "generation or nae_retrieval or bridge or citation or claim_guard"` — 전부 PASS

## DoD 대조

| # | 조건 | 상태 |
|---|---|---|
| 1 | `git diff core/retrieval.py` 빈 결과 | ✅ (본 브랜치 diff 없음) |
| 2 | `nae_tsu_v1`==3319 / `nae_ref_v1`==34948 | ⏸ 라이브 Qdrant 필요 — mutation 코드 경로 없음(정적 확인) |
| 3 | `tsu_dataset.jsonl` sha256 불변 / `NAE/corpus/**` `NAE/pipeline/tsu/**` 무수정 | ✅ (git status로 확인) |
| 4 | AT-1~10 PASS | 🟡 AT-2(합성+실제 canonical 유닛으로 대체 검증), AT-4/AT-7/AT-9 로직 유닛 검증 · AT-1/3/5/6/8/10 라이브 대기 |
| 5 | 대상 회귀 PASS | ✅ |
| 6 | `nae_pd=false`에서 DBMA·chat 바이트 동일 | ✅ (코드상 `bridge_query*`는 `module_registry.is_enabled("nae_pd")` 게이트 내부, `_render_nae_section`은 그 앞에서 return. `chat.py`는 bridge 미호출) |
| 7 | Build Report | ✅ (본 문서) |
| 8 | C1 Independent Review | ⏸ 대기 |

## ADR Compliance (설계 §8 재확인)

- **ADR-001**: `core/retrieval.py` diff 0. 옵션 A는 답변 조립 계층 — 스코어링·랭킹·벡터 쿼리 없음.
- **ADR-024 §C/§D**: `bridge_query() -> list[Citation]` 무변경, `content_excerpt`(=`source_text[:200]`) 계약 유지. 신규 `bridge_query_paragraphs`는 §D 계약 밖 별도 함수. `nae_qdrant` 외 접근 없음 — 리졸버는 `NAE/corpus/canonical/` 로컬 파일만.
- **ADR-030 v2.1 §7/§8/§11**: canonical.json read-only, mutation 0. `authority_class` 조회·표시만(TSU 레코드 미기입).
- **ADR-007/008**: 무관 — 재청킹 아님.

## Assumptions (설계 §9)

| # | 가정 | 검증 상태 |
|---|---|---|
| 1 | canonical.json 존재·`paragraph` 인덱스 정합 | ⏸ `scripts/nae_para_reconcile.py` 실행 필요 (>5% 실패 시 NO-GO) |
| 2 | `paragraph` payload 전 포인트 채워짐 (Dagg/Hiscox 미확인) | ⏸ 동 스크립트 |
| 3 | `Citation` 옵셔널 필드 추가가 §C 위반 아님 | ✅ 회피 — Citation 무변경 경로 채택 |
| 5 | authority manifest가 모든 source_id 커버 | 🟡 조회 실패 시 생략(구현 반영) |
| 7 | 1 TSU = 1 문단 | 🟡 `NAE_PARAGRAPH_NEIGHBORS` 옵션 제공(기본 0) |
| 8 | 문단 길이가 `num_ctx` 예산 안 | 🟡 상한(1500)·예산 드롭 구현 · 실측은 reconcile 스크립트 §1-4 |

## Rollback (설계 §7)

- `config.yaml: modules.nae_pd.enabled: false` — 즉시, `bridge_query_paragraphs` 게이트 상속.
- `NAE_PARAGRAPH_EVIDENCE=0` — `nae_pd` 켠 채 문단 확장만 차단(`bridge_query_paragraphs`가 ae05415 등가 dict 반환).
- 코드 revert = 신규 3파일 + `NAE/retrieval_adapter.py`/`ui/pages/research.py` diff. `core/retrieval.py` 무연쇄.
- 데이터 롤백 없음 — 아무것도 쓰지 않음.

## Git

브랜치 `claude/p0-2-paragraph-anchored-evidence`. 커밋 후 PR → `dev/dbma-engine`.
HQ + C1 승인 전 병합 금지. `main`/`dev` 직접 병합·force·history rewrite 없음.

## 배포 환경에서 남은 실행 (순서)

1. `~/envs/dbma311/bin/python scripts/nae_para_reconcile.py` → `RECONCILE_001.md`.
   실패율 > 5% → STOP·HQ.
2. `nae_pd` enable + Streamlit 기동, 고정 질의 13건(sandbox 문서) → 카드 스크린샷.
3. AT-5/AT-6 육안 평가(생성 모델 필요), `answer_completeness` 결과 기록.
4. C1 Independent Review (§8-1 체크리스트).
5. 결과를 `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_ACCEPTANCE_001.md`에 raw 캡처.
