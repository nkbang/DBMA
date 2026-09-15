---
title: "NAE 문단 답변 전달 — Stage 1 정합성 게이트 결과 001"
created: 2026-09-10
status: DATA GATE PASS · CONCURRENCY GATE HOLD
task_order: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md §1
design_doc: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md §6 (AT-2/AT-10), §9 (가정 1·2·8)
executor: CUE
base_at_scan: origin/dev/dbma-engine @ 09d8ac2
env: ~/envs/dbma311, nae_qdrant :7333 (read-only)
---

# Stage 1 — 정합성 게이트 결과

> 읽기 전용. 어떤 코드·데이터·인덱스·설정도 변경하지 않았다.
> 스캔 스크립트: `/private/tmp/nae_para/reconcile.py` (CUE 작성, read-only scroll).

---

## 결론

| 게이트 | 판정 | 근거 |
|---|---|---|
| **데이터 정합성** (TO §1-3, 설계 가정 1·2) | **GO** | `nae_tsu_v1` 3,319 point 전수 스캔, 6개 체크 **실패 0건** (0.00% ≪ 5% STOP 임계) |
| **컨텍스트 예산** (TO §1-4, 설계 가정 8) | **GO** | 문단 p95 1,511자, top_k=10 × p95 ≈ 15,110자 ≈ ~5k tok ≪ num_ctx 32,768 |
| **동시 작업 / base freshness** (TO §1-1·§1-2) | **HOLD** | 미병합 PR #11–#15가 TO 대상 파일 4개 수정, PR #14가 §3/§5와 다른 메커니즘으로 중첩 → HQ 결정: **#11–#15 병합까지 보류** (2026-09-10) |

**다음 조치**: PR #11–#15가 `dev/dbma-engine`에 병합되면 → TO를 새 base로 rebase,
§3-1(컨텍스트 블록)을 PR #14의 `출처:` 주입 방식과 정합화, base freshness
재확인 후 Stage 1 커밋 + Stage 2 착수.

---

## 1-3. 데이터 정합성 스캔 (`nae_tsu_v1`, 3,319 point)

체크 항목 (point 단위):

| # | 체크 | 실패 | 비율 |
|---|---|---|---|
| A | `identifier` 존재 | 0 | 0.00% |
| B | `paragraph` 존재 (not None) | 0 | 0.00% |
| C | `NAE/corpus/canonical/<identifier>/canonical.json` 존재 | 0 | 0.00% |
| D | `paragraphs[]`에 `index == payload.paragraph` 존재 | 0 | 0.00% |
| E | `payload.canonical_version` == `canonical.json.pipeline_version` | 0 | 0.00% |
| F | `norm(payload.source_text)` ⊂ `norm(paragraph.text)` (공백 정규화) | 0 | 0.00% |

**해석**: 설계 §9 가정 1(canonical.json 존재 + `paragraphs[].index` ↔ payload
`paragraph` 정렬 + 버전 일치)과 가정 2(`paragraph` 필드 전수 채움)가 프로덕션
`nae_tsu_v1`에서 **완전히 성립**한다. `ParagraphResolver`의 폴백 경로는
프로덕션 데이터에서는 발동하지 않을 것으로 예상되나, 코드에는 유지한다
(신규 corpus admission 대비).

### corpus 구성 (실측)

| identifier | points |
|---|---|
| `Dagg_Church_Order` | 2,958 |
| `Hiscox_Standard_Manual` | 361 |
| **합계** | **3,319** |

- **Fuller는 `nae_tsu_v1`에 없다** — F2/sandbox 단계, processing HOLD
  (memory: ADR-030 A-2a-PREP). sandbox 컬렉션 `nae_tsu_fuller_sandbox_v0`도
  **현재 존재하지 않음** (임시 컬렉션, 정리됨). `nae_ref_v1`(34,948)은 스캔
  대상 아님(Smith reference, CON-006 범위 밖).
- **영향**: TO §7 acceptance는 **Dagg/Hiscox만** 커버 가능. Fuller 경로
  검증이 필요하면 Stage 7 전에 sandbox 재빌드가 선행되어야 한다(별도 판단).

---

## 1-4. 문단 길이 분포 (`nae_tsu_v1`이 참조하는 distinct 문단)

| 지표 | 값 (chars) |
|---|---|
| distinct (identifier, paragraph) | 1,104 |
| min / median / mean | 25 / 513 / 607 |
| p90 / p95 / p99 / max | 1,236 / 1,511 / 2,071 / 2,554 |
| > 1,500자 | 58 (5.25%) |
| est. top_k=10 × p95 | 15,110자 (~5,036 tok 러프) vs num_ctx 32,768 |

**해석**:
- TO §3-1의 문단 길이 상한 **1,500자**는 적정 — 전체의 ~5%만 축약 대상.
  여유가 크므로 상한을 **2,100자(p99)**로 올려도 top_k=10에서
  10 × 2,071 ≈ 20,710자 ≈ ~6.9k tok로 예산 내. Stage 3에서 재결정.
- 컨텍스트 예산 압박은 없음. 축약 정책은 "안전망"으로만 두고 기본은
  문단 전문 전달.

---

## 1-1 / 1-2. Base freshness · 동시 작업 (HOLD 사유)

### 관측

`origin/dev/dbma-engine` @ `09d8ac2` (본 설계 PR #10 병합만 반영).

미병합 PR (전부 OPEN, 2026-09-10):

| PR | 제목 | 브랜치 |
|---|---|---|
| #11 | P0-1: 근거 강제 · 한국어 QueryParser · 교단 프로파일 통합 | `claude/p0-1-quality-integration` |
| #12 | P0-4: ClaimGuard TrustTier 위장 제거 + 규칙 2a | `claude/p0-4-trust-tier-honesty` |
| #13 | P0-6: 검색 근거 0건이면 유보 문구 | `claude/p0-6-no-evidence-hold` |
| #14 | 선결 #3: LLM 문맥 블록에 서지정보(`출처:`) 주입 | `claude/p0-3-context-bibliography` |
| #15 | 선결 #5·#6: SourceTierBonus 실효화 + 모델 SYSTEM 전통 일치 | `claude/p0-5-6-tier-bonus-denomination` |

(누적 브랜치 `claude/p0-2-paragraph-anchored-evidence` @ `4007926`가 위 8개
커밋을 담고 있음. 브랜치명은 P0-2를 예고하나 현재 커밋은 위 P0 항목들이며
**문단 리졸버/문단 확장 구현은 없음**.)

### TO 대상 파일과의 충돌

| 파일 | 동시 변경 (미병합) | TO 항목 | 성격 |
|---|---|---|---|
| `NAE/retrieval_adapter.py` | `_map_nae_to_citation_metadata`에 `source_text` 전문 키 추가 + `RankedCandidate.content = source_text` (ae05415 = 커밋 `8cfd321`) | §2-2 | **TO가 추가하려던 바로 그것** — 재구현 금지, 그 위에 `evidence_paragraph`만 얹어야 함 |
| `core/generation.py` | `_GROUNDING_DIRECTIVE` 2종 + 교단 프로파일 확장(+102줄), ADR-009 Amendment A(미승인) | §3-2 | `_GROUNDING_DIRECTIVE` 문구 정본 — 그 위에 브리지 조항 추가 |
| `core/retrieval.py` | **PR #14** — `ContextAssembler`가 LLM 문맥 블록에 `출처:` 라인 주입 (+307줄, 신규 `tests/test_context_assembler_source_label.py`) | §3-1 | **직접 중첩.** TO §3-1은 "`ContextAssembler` 무수정"을 전제했고 §5 결함 B를 옵션 A가 부수 해결한다고 봤으나, PR #14가 **다른 메커니즘**으로 이미 해결 중 → 설계 정합화 필요 |
| `ui/pages/research.py` | 같은 클러스터에서 수정(+16) | §4 | `_render_nae_section` 재작성 시 diff 재확인 |

### 결정 (HQ, 2026-09-10)

**"#11–#15 병합까지 보류."** TO §0 NO-GO 조건("인접 브랜치 미병합이면
§1-3 결정 후에만 진행") 및 memory [[feedback_stale_base_verify]] /
[[feedback_concurrent_c1_file_edits]] 준수. Stage 1 데이터 게이트는
통과했으므로 재실행 불요 — 본 문서가 그 결과를 고정한다.

### 재개 시 체크리스트

1. `git fetch origin dev/dbma-engine` → #11–#15 병합 확인.
2. TO를 새 `dev/dbma-engine` tip으로 rebase.
3. §2-2: `NAE/retrieval_adapter.py`의 병합된 `source_text` 경로 위에
   `evidence_paragraph`만 추가 (중복 구현 금지).
4. §3-1: PR #14의 `출처:` 주입과 옵션 A의 `<자료 work=... author=...>`
   블록 포맷을 **하나로 정합화** — 둘 다 넣지 말 것. 브리지 경로가
   PR #14 포맷을 재사용할 수 있으면 §3-1 신규 포맷 함수 축소.
5. §3-2: 병합된 `_GROUNDING_DIRECTIVE` 문구 재확인 후 브리지 조항 추가.
6. base freshness 재확인(건드릴 4개 파일이 origin에서 또 바뀌었는지).
7. 본 문서 1-3/1-4 결과는 유효 — canonical corpus 무변동 시 재스캔 불요.
   (단 #11–#15에 `NAE/corpus/` 또는 `nae_tsu_v1` 재색인이 포함되면 재스캔.)
