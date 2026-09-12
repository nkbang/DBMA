# C1 Review 요청 — NAE 완성 문단 답변 전달 (옵션 A)

- 요청자: CUE
- 일자: 2026-09-10
- 유형: **C1 Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점 — Citation 모델 표시 계층 변경" / Task Order §8-1
- PR: https://github.com/nkbang/DBMA/pull/17 (`claude/p0-2-paragraph-anchored-evidence` → `dev/dbma-engine`)
- HEAD: `447054ef550fbbc2081f34c099e25864bdf57176`

---

## 1. 요청 배경

PM 정렬 감사(`docs/reports/PM-PRODUCT-ALIGNMENT-AUDIT-2026-09-10.md`) 선결 #4 (P0-2).
NAE `bridge_query` 경로의 근거 전달 단위를 "200자 절단 문장 조각"에서
`canonical.json` **원문 문단 전체**로 올린다. 검색 단위(TSU)·임베딩·인덱스·
`builder_version` 무변경. 설계 문서 `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md`
의 옵션 A만 구현. Task Order = `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md`.

Stage 1 데이터 게이트는 PR #16(`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_RECONCILE_001.md`)
이 이미 GO(3,319 point 전수 스캔, 6개 체크 실패 0건)로 통과시켰다.

---

## 2. 검토 대상 산출물

| # | 파일 | 종류 |
|---|---|---|
| A | `NAE/pipeline/canonical/paragraph_lookup.py` | 신규 — ParagraphResolver |
| B | `NAE/answer_context.py` | 신규 — `<자료>` 블록 포맷 + 프롬프트 조항 + 서브 플래그 |
| C | `NAE/retrieval_adapter.py` | 수정 — payload pass-through, `bridge_query_paragraphs()`, `_enrich_hit_with_paragraph()`, `_authority_class_for()` |
| D | `core/evaluation/answer_completeness.py` | 신규 — 규칙 기반 완결성 판정 |
| E | `ui/pages/research.py` | 수정 — `_render_nae_paragraph_card` / `_render_nae_legacy_card` 분기 |
| F | `scripts/nae_para_reconcile.py` | 신규 — Stage 1 스캔(라이브 Qdrant) |
| G | `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_BUILD_REPORT_001.md` | Build Report |
| H | `docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md` | Stage 5-2 설계 초안 |
| I | `tests/test_nae_paragraph_resolver.py` / `test_nae_answer_context.py` / `test_answer_completeness.py` | 신규 26건 |

---

## 3. C1 검토 질문

1. **ADR-001 무영향**: `git diff origin/dev/dbma-engine -- core/retrieval.py` 가
   빈 결과인가? 옵션 A가 `RetrievalEngine`/`QueryProcessor`/`RankingEngine`/
   `ContextAssembler` 어느 것도 수정하지 않고, 스코어링·랭킹·벡터스토어 쿼리
   없이 payload에 이미 있는 ID로 하는 결정적 dict 조회에 그치는가?

2. **ADR-024 §C/§D 계약**:
   - `bridge_query() -> list[Citation]` 시그니처·동작이 바이트 무변경인가?
   - `Citation` dataclass가 무변경인가? (신규 필드 추가 없음 — `bridge_query_paragraphs`가
     별도 `list[dict]` 반환하는 UI-resolve 경로 채택. 설계 가정 3 1순위.)
   - `content_excerpt = source_text[:200]` 계약이 유지되는가?
   - §H: `bridge_query_paragraphs` 폴백 포함 어느 경로도 `nae_qdrant`(7333) 외
     스토어에 접근하지 않는가? (리졸버는 `NAE/corpus/canonical/` 로컬 파일만 —
     `grep -n "localhost\|7333\|qdrant\|requests\.\|httpx\|urllib" NAE/pipeline/canonical/paragraph_lookup.py NAE/answer_context.py` 로 확인)

3. **ADR-030 v2.1 §7/§8/§11 baseline 보호**:
   - `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) mutation·upsert·재색인 코드
     경로가 전혀 없는가?
   - `NAE/corpus/canonical/**` 는 read-only인가? (`json.load` 만, write 없음)
   - `authority_class` 가 TSU 레코드·payload에 기입되지 않고 조회·표시 전용인가?
     (`NAE/pipeline/registration/state/source_manifest.yaml` / `NAE/authority/source_manifest.yaml` 조회)

4. **#16 재개 체크리스트 §3-1 정합화**: `NAE/answer_context.py::format_nae_context_block`
   이 PR #14의 `core/retrieval.py::_format_context_source_label` 을 재사용해
   DBMA 경로와 같은 `출처:` 한 줄을 emit하고, `work=/author=/page=/para=`
   병렬 속성 어휘를 만들지 않는가? 두 경로가 서지 표기를 **이중으로** 넣는
   지점이 없는가? (`_GROUNDING_DIRECTIVE` §5 ↔ `NAE_PARAGRAPH_PROMPT_CLAUSE` §6~7
   중복 없음 확인)

5. **fail-soft 정합**: 리졸버 실패(파일 부재 / 인덱스 부재 / `canonical_version`
   불일치)가 예외를 호출자에 전파하지 않고 `source_text` 전문 폴백 + 로그로
   흡수되는가? (ADR-024 §G fail-closed 정신)

6. **격리(AT-7/AT-9)**: `modules.nae_pd.enabled=false` 에서 `bridge_query_paragraphs`
   가 `NaePdModuleDisabledError` 를 던지고 `_render_nae_section` 이 그 앞에서
   return하는가? `chat.py` 는 어떤 bridge 함수도 호출하지 않는가?
   `NAE_PARAGRAPH_EVIDENCE=0` 이 문단 확장만 끄고 ae05415 등가 dict를 반환하는가?

7. **regression**: `~/envs/dbma311/bin/python -m pytest -q tests/` → 2,930 passed /
   15 skipped 재현되는가? 신규 26건이 실제로 의미 있는 검증인가(fixture 경로
   override 포함 — memory: Test Fixture Path Overrides)?

---

## 4. 요청 형식

- 판정: **GREEN / YELLOW(조건부) / RED**
- YELLOW·RED 시: 구체 findings + 해소 방안
- 산출물: `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다**. 문서 검토 + 코드 read-only.
- 먼저 `git rev-parse HEAD`, `git remote -v`, `git rev-parse --show-toplevel`
  출력을 결과 문서 상단에 붙일 것 (memory: C1 Stale Status Reports).

## 5. 게이트

- C1 Review **GREEN** + 라이브 Acceptance(AT-1/3/5/6/8, Dagg/Hiscox) + HQ 승인
  → PR #17 병합 가능.
- YELLOW/RED → 해소 후 재검토.
- 라이브 Acceptance는 C1 Review와 병행 가능(독립).
