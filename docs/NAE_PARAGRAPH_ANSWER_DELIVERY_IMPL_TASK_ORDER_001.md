---
title: "Task Order — NAE 완성 문단 답변 전달 (옵션 A) 구현 001"
created: 2026-09-10
status: DRAFT — 미착수. HQ 승인 + PR #10(설계 v1) 병합 후 실행.
issuer: CUE
executor: CUE (Primary Implementation Agent). 기계적 하위단계는 C1 위임 가능 (§9 표기).
verifier: CUE 자체 검증 + C1 Independent Review (§8 트리거 해당 — Citation 모델 표시 계층 변경)
design_doc: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md
base: dev/dbma-engine (실행 시점 origin 최신으로 재확인 — §1)
venv: ~/envs/dbma311
---

# Task Order — NAE 완성 문단 답변 전달 (옵션 A) 구현 001

> 설계 근거: `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md` §4.4 / §6 / §8 / §9 / §10.
> 본 TO는 그 설계의 **옵션 A만** 구현한다. B·C·D는 범위 밖.

---

## 0. 목적과 Definition of Done (DoD)

**목적**: NAE `bridge_query()` 경로의 근거 전달 단위를 "200자 절단 문장 조각"에서
**`canonical.json` 원문 문단 전체**로 올려, 목회자 사용자가 "의미적으로 완성된
문단" 형태의 근거와 문법적으로 완결된 한국어 답변을 받게 한다. 검색 단위(TSU)·
임베딩·인덱스·`builder_version`은 **변경하지 않는다.**

**DoD — 아래 전부 충족 시 "구현 완료"**:

1. `git diff core/retrieval.py` **빈 결과** (ADR-001).
2. `nae_tsu_v1` points_count == **3,319**, `nae_ref_v1` == **34,948** (실행 전후 대조, ADR-030).
3. `output/bench/tsu_dataset.jsonl` sha256 불변. `NAE/corpus/tsu/**` 무수정.
   `NAE/pipeline/tsu/**` 무수정 (F2 실행 영역 — 충돌 금지).
4. 설계 §6 AT-1 ~ AT-10 **전부 PASS**, raw 산출물 캡처.
5. 회귀: `tests/test_book_alias_resolution.py`,
   `tests/test_query_enhancements_full_regression.py`,
   `pytest -k "generation or nae_retrieval or bridge or citation or claim_guard"`
   **전부 PASS** (착수 전 baseline 대비 신규 실패 0).
6. `modules.nae_pd.enabled: false`(기본값) 상태에서 DBMA 기본 경로·`chat.py`
   답변이 **바이트 동일** (AT-7).
7. Build Report 작성 (`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_BUILD_REPORT_001.md`).
8. C1 Independent Review 완료 (§8).

**NO-GO / STOP 조건**:
- §1 정합성 스캔에서 canonical.json ↔ payload `paragraph` 불일치율이
  **> 5%** → STOP, HQ 보고 (가정 1 붕괴 — 폴백만으로는 목적 미달).
- 인접 브랜치 `claude/theological-pastoral-response-quality-89b049`(ae05415)가
  `dev/dbma-engine`에 **미병합**이면 §1-3 결정 후에만 진행.
- ADR-024 §C에 `Citation` 필드 추가가 필요하다고 판정되면 → Amendment 각주
  초안을 먼저 HQ에 제출, 승인 후 Stage 2 재개 (§2-4).

---

## 1. Stage 1 — 선행 확인 및 정합성 게이트 (코드 변경 없음)

### 1-1. Base freshness (memory: Verify Base Freshness)
```bash
git fetch origin dev/dbma-engine
git log --oneline -1 origin/dev/dbma-engine
git merge-base --is-ancestor <작업브랜치 base> origin/dev/dbma-engine && echo OK
# 건드릴 파일이 origin에서 이미 바뀌었는지:
git log --oneline origin/dev/dbma-engine -- NAE/retrieval_adapter.py ui/pages/research.py core/generation.py
```

### 1-2. 인접 브랜치 병합 상태 확인
```bash
git merge-base --is-ancestor ae05415 origin/dev/dbma-engine && echo "MERGED" || echo "NOT merged"
```
- **MERGED**: `NAE/retrieval_adapter.py`가 이미 `source_text` 전문을
  `RankedCandidate.content`에 넣고 `_GROUNDING_DIRECTIVE`가 있다 — 그 위에 쌓는다.
- **NOT merged**: 본 TO가 그 수정(근거강제 지시문 + `source_text` 전문화)을
  **선반영**한다. 단 중복 구현이 되지 않도록 ae05415의 diff를 그대로 cherry-pick
  또는 동등 재현하고 Build Report에 출처를 명시한다. `_GROUNDING_DIRECTIVE`
  문구는 ae05415 원문을 정본으로 삼는다(재작성 금지).

### 1-3. 정합성 스캔 (가정 1·2 — AT-10, AT-2 선행)
읽기 전용 스크립트 `/private/tmp/nae_para/reconcile.py` 작성·실행:

- `nae_qdrant`(7333) `nae_tsu_v1` 전체 point를 scroll (payload만, 벡터 제외).
- 각 point에 대해:
  - `identifier` 존재? `paragraph` 채워짐? (가정 2)
  - `NAE/corpus/canonical/<identifier>/canonical.json` 존재?
  - `paragraphs[]`에 `index == payload.paragraph`인 항목 존재?
  - `payload.canonical_version` == `canonical.json.pipeline_version`?
  - `payload.source_text`가 그 문단 `text`의 부분문자열? (공백·개행 정규화 후)
- 출력: 총 point 수, 각 체크 실패 건수·비율, 실패 샘플 20건(tsu_id + 사유).

**게이트**:
| 결과 | 조치 |
|---|---|
| 모든 체크 실패율 ≤ 1% | GO — 폴백 경로로 흡수 가능 |
| 부분문자열 실패 1~5% (OCR 정규화 차이 추정) | GO, 단 정규화 함수 강화 후 재측정 |
| 임의 체크 실패율 > 5% | **STOP · HQ 보고** (NO-GO) |

### 1-4. 문단 길이 분포 측정 (가정 8 — 컨텍스트 예산)
`nae_tsu_v1`에 등장하는 (identifier, paragraph) 고유 조합의 문단 `text` 길이:
중앙값 / p95 / max / >1,500자 비율. Build Report에 기록. `num_ctx` 32768 기준
`top_k=10` × p95 문단이 예산 안인지 산정 → Stage 3 상한 정책 임계값 결정.

### Stage 1 산출물
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_RECONCILE_001.md` — 1-2/1-3/1-4 결과.
NO-GO면 여기서 종료.

---

## 2. Stage 2 — ParagraphResolver + bridge 매핑 확장

### 2-1. `ParagraphResolver` 신규 모듈
- 위치: **`NAE/pipeline/canonical/paragraph_lookup.py`** (신규). `NAE/pipeline/tsu/`
  아님 — F2 충돌 회피.
- API:
  ```python
  @dataclass
  class ResolvedParagraph:
      text: str
      page_start: int | None
      page_end: int | None
      index: int
      scripture_references: list
      canonical_version: str

  def resolve(identifier: str, paragraph_index: int, *,
              canonical_root: Path = tsu_config.CANONICAL_ROOT,
              neighbors: int = 0) -> ResolvedParagraph | None
  ```
- 구현: `NAE/pipeline/verify/consistency.py:44-49` 패턴 재사용.
  `@functools.lru_cache(maxsize=32)`로 identifier 단위 canonical.json 파싱 캐시
  (2,250 문단/권 → dict 인덱스 1회 빌드).
- `neighbors > 0`: `index-n … index+n` 문단 `text`를 순서대로 `\n\n` 결합
  (같은 identifier 내, 범위 밖 인덱스는 건너뜀).
- 실패(파일 부재 / 인덱스 부재 / `canonical_version` 불일치): `None` 반환 +
  `logger.warning` (예외 전파 금지 — ADR-024 §G 정합).

### 2-2. bridge 매핑 확장 (`NAE/retrieval_adapter.py`)
`_map_nae_to_citation_metadata(hit)` 반환 dict에 추가 (기존 키 유지):
```
evidence_paragraph : ResolvedParagraph.text  (resolve 성공 시)
                     else payload.source_text 전문  (폴백)
paragraph_resolved : bool
anchor_sentence    : payload.source_text
bibliography : { author, work(=book), edition_id, volume_id,
                 page_start, page_end, paragraph_index, identifier }
authority_class : (2-3)  또는 생략
```
- `content_excerpt`(=`source_text[:200]`)는 **그대로 유지** — ADR-024 §C 계약.
- `RankedCandidate.content` = `evidence_paragraph` (ae05415가 이미 `content`를
  계약 밖으로 규정 — Build Report에 그 근거 인용).

### 2-3. `authority_class` 조회 어댑터
- 소스: `NAE/authority/source_manifest.yaml` (+ `authors.yaml`/`works.yaml` 필요 시).
- `payload.source_id` → manifest record → `authority_class` 필드.
- 조회 실패 / 필드 부재 → dict에서 키 생략 (카드는 나머지 서지로 정상 동작 —
  설계 가정 5).
- **TSU 레코드·payload에 쓰지 않는다** (ADR-030 §7). 읽기·표시 전용.

### 2-4. `Citation` 변경 여부 결정 (설계 가정 3)
- **1순위 (권장)**: `Citation` dataclass **무변경**. `bridge_query()`가 반환하는
  것은 기존 `list[Citation]` 그대로 두고, 문단·서지·앵커는 **별도 리스트**
  (`list[dict]`, citation_id로 조인)로 함께 반환하거나, UI(`_render_nae_section`)가
  `ResolvedParagraph`를 직접 조회. → ADR-024 §C 무영향, Amendment 불요.
- **2순위**: 부득이하면 `evidence_paragraph: Optional[str] = None` 후행 옵셔널
  1개 추가. 이 경우 **Stage 중단** → ADR-024 Amendment 각주 초안을 HQ 제출,
  승인 후 재개.
- 결정과 근거를 Build Report에 기록.

### Stage 2 산출물
- `NAE/pipeline/canonical/paragraph_lookup.py` (신규)
- `NAE/retrieval_adapter.py` (매핑 확장 + `bridge_query` 조립부)
- `tests/test_nae_paragraph_resolver.py` (신규): resolve 정확도, 폴백, 캐시,
  neighbors, canonical_version 불일치 → None.

---

## 3. Stage 3 — 생성 컨텍스트 블록 + 프롬프트

### 3-1. 브리지 전용 컨텍스트 포맷 함수
- 위치: `NAE/retrieval_adapter.py` (또는 신규 `NAE/answer_context.py`).
  **`core/retrieval.py::ContextAssembler`는 수정하지 않는다** (Chat/Research
  공용 — ADR-001, 감사 §5 결함 B 주석). 설교 경로
  `core/generation.py::_format_sermon_context()`가 선례.
- 히트당 블록:
  ```
  <자료 id="{tsu_id}" work="{work}" author="{author}" page="p.{start}–{end}" para="§{idx}">
  {evidence_paragraph}
    <일치문장>{anchor_sentence}</일치문장>
  </자료>
  ```
- **문단 길이 상한** (Stage 1-4 결과로 임계값 확정, 기본 1,500자):
  초과 문단은 `anchor_sentence`를 중심으로 앞뒤 ~600자 window로 축약하고
  `truncated="true"` 속성 표기. (window 계산은 canonical `sentences[]` 경계 존중.)
- `top_k` 합계가 `num_ctx` 예산(문자 기준 보수 추정) 초과 시 하위 랭크부터
  드롭하고 드롭 수를 로그.

### 3-2. 생성 프롬프트 조항 (요구 3·4·1)
- base = ae05415 `_GROUNDING_DIRECTIVE` (문구 원문 유지).
- NAE 브리지 답변 경로에 **추가 조항**(브리지 전용 분기 또는 조건부 병합):
  1. "각 `<자료>`는 완결된 원문 문단이다. 조각을 그대로 붙여넣지 말고,
     문단의 논지를 **2~4개의 완결된 한국어 문단**으로 재구성하라."
  2. "각 문단에서 최소 1개 `<자료>`를 근거로 명시하고, 본문에서 저자·저작
     (`work`/`author` 속성)을 밝혀라."
  3. "`<일치문장>`은 검색이 걸린 지점 표시다. 그 문장만이 아니라 문단 전체를
     근거로 삼아라."
- sandbox의 "3~6문장 간결" 상한
  (`scripts/nae_fuller_sandbox_search_app.py:59`)은 **프로덕션 경로에 이식하지
  않는다.** (sandbox 스크립트 자체는 수정 대상 아님.)

### Stage 3 산출물
- 위 파일 diff + `tests/test_nae_answer_context.py` (신규): 블록 포맷, 상한
  축약, 예산 드롭, 프롬프트 조항 존재.

---

## 4. Stage 4 — 인용 카드 (요구 3)

### 4-1. `ui/pages/research.py::_render_nae_section()` 결과 렌더 교체
현재(`research.py:544-559`)는 `st.markdown`/`st.caption` 인라인 + `excerpt[:300]`.
교체:
- 본문: `evidence_paragraph` **전문** (`st.markdown`, 300자 절단 제거).
- 서지 라인: `{author} · {work} · {edition} · p.{start}–{end} · §{para}`.
- `anchor_sentence` **하이라이트** (`:orange[...]` 또는 `st.info` 분리) +
  라벨 "이 문단에서 질의와 일치한 문장".
- `paragraph_resolved is False`면 "원문 문단 복원 실패 — 문장 근거만 표시" 캡션.
- TSU `claim`: 기본 접힘(`st.expander("AI 요지 요약")`), "AI가 생성한 한국어
  요약 — 원문 아님" 명시. 카드 본문으로 쓰지 않는다 (감사 §4.3).
- CJK/비-라틴 문자가 `evidence_paragraph`에 있으면 ⚠ 배지
  (`scripts/nae_fuller_sandbox_search_app.py`의 `🈲CJK` 선례). **자동 편집 금지.**
- `authority_class` 있으면 배지로 표시 (없으면 생략).

### 4-2. `render_citation_card` 사용 여부
- 현 `_render_nae_section`은 `render_citation_card`를 쓰지 않는다. 이번엔
  **인라인 렌더 확장만** 한다 (`ui/components/citation_card.py` 시그니처 변경은
  Chat 경로 영향 → 범위 밖). 필요 시 별도 TO.

### Stage 4 산출물
- `ui/pages/research.py` diff.
- 수동 스모크: `nae_pd` enable + Streamlit 기동, 질의 3건 스크린샷
  (Build Report 첨부).

---

## 5. Stage 5 — 답변 완결성 판정 (요구 4)

### 5-1. 규칙 기반 판정기 (즉시 구현)
`core/evaluation/` 신규 `answer_completeness.py`:
- 입력: 답변 텍스트.
- 체크: (a) 모든 문장이 한국어 완결 어미로 종료 (b) 40자 초과 연속 라틴
  문자 스팬 0 (c) 비-한글/라틴/기호 문자(CJK·태국어 등) 0
  (d) 경어체 일관 (`습니다/입니다` 계열) (e) 최소 2개 문단.
- 출력: `{passed: bool, violations: list[str]}`.
- **생성을 차단하지 않는다** — 결과를 `GenerationResult`에 부가 + UI 캡션.

### 5-2. rag_judge 확장 (설계 gate — 즉시 구현 아님)
- `core/evaluation/rag_judge.py`에 `judge_fluency()` / `judge_completeness()`
  추가는 **ADR-010 Phase 2 범위**. 지표 정의(특히 `question_answering_quality`
  reference-free)는 ADR-010 미확정 항목 → 본 TO에서 **설계 초안만** 작성
  (`docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md`), 구현은 별도 TO + C1 Review.
- 본 TO의 AT-5는 **5-1 규칙 기반 판정기 + 고정 질의셋 육안 평가**로 판정.

### Stage 5 산출물
- `core/evaluation/answer_completeness.py` + `tests/test_answer_completeness.py`.
- `docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md` (설계 초안).

---

## 6. Stage 6 — 서브 플래그 + 격리

### 6-1. `NAE_PARAGRAPH_EVIDENCE` 서브 플래그
- 읽기: **요청마다 조회** (`os.environ.get("NAE_PARAGRAPH_EVIDENCE", "1")`,
  기본 on). 모듈 상수·`__init__` 캐시 금지 (Conflict Register CON-009 B).
- off: `bridge_query()`가 문단 확장을 건너뛰고 ae05415 동작
  (`source_text` 전문)으로 폴백. 카드도 문단 없이 렌더.
- 목적: 검증 중 A/B, 문단 경로 결함 시 즉시 무력화(코드 롤백 없이).

### 6-2. 격리 테스트 (AT-7, AT-9)
- `modules.nae_pd.enabled: false` → `ParagraphResolver` 미호출,
  `bridge_query` `NaePdModuleDisabledError`, `_render_nae_section` 무렌더.
- DBMA 기본 경로(Research 일반 검색 + Chat) 답변이 착수 전과 **바이트 동일**
  (고정 질의 5건, `GenerationService` 출력 해시 대조).
- `NAE_PARAGRAPH_EVIDENCE=0` → `bridge_query` 반환이 ae05415 동작과 동일.

---

## 7. Stage 7 — Acceptance 실행

설계 §6 AT-1 ~ AT-10을 순서대로 실행하고 **raw 산출물(stdout/JSON/스크린샷)**
을 `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_ACCEPTANCE_001.md`에 캡처. 서술 요약만으로
PASS 판정 금지.

- 고정 질의셋: `docs/NAE_FULLER_VOL01_SANDBOX_RETRIEVAL_TEST_001.md`의 교리
  질의 13건을 사용 (재현성).
- 대조 컬렉션: `nae_tsu_v1`(프로덕션) + `nae_tsu_fuller_sandbox_v0`(sandbox,
  존재 시). sandbox 없으면 `nae_tsu_v1`만.
- AT-6(CJK): Vol.01 CJK 366 claim의 부모 문단을 `reconcile.py` 재사용해 추출,
  LLM-CJK 0 확인 (OCR 잔존은 허용, 배지 처리 확인).

회귀: DoD §5의 3개 pytest 스위트.

---

## 8. Stage 8 — Review · Build Report · Git

### 8-1. C1 Independent Review 트리거
CUE Operating Policy §"C1 Review 요청 시점" 중 **"Citation 모델 표시 계층
변경"** 해당 → C1 Review 요청. 검토 대상:
- ADR-001 무영향 (`core/retrieval.py` diff 0) 재확인.
- ADR-024 §C 계약(`content_excerpt`) 무변경, `Citation` dataclass 변경 여부·근거.
- ADR-030 baseline(3,319 / 34,948) 무접촉.
- 폴백 경로가 `nae_qdrant` 외 접근 없음(grep).

### 8-2. Build Report
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_BUILD_REPORT_001.md`:
STATUS / Changed Files / Tests / Regression / Acceptance(AT-1~10 표) /
ADR Compliance / Assumptions 검증 결과(가정 1~8) / Rollback 확인 / Git.

### 8-3. Git (CUE 자동화 범위)
DoD 전부 충족 시 자동 commit + push (현재 작업 브랜치, `origin`). Force/history
rewrite 금지. `main`/`dev/dbma-engine` 직접 병합 금지 → PR 생성, HQ + C1 승인.
- Commit 분할: `feat(nae): ParagraphResolver + bridge 문단 확장` /
  `feat(nae): 브리지 답변 컨텍스트·프롬프트 문단화` /
  `feat(ui): NAE 인용 카드 문단 표시` / `test(nae): acceptance + 회귀` /
  `docs(nae): build report + acceptance 산출물`.

---

## 9. 범위 · 금지 · 위임

### 범위 밖 (별도 TO)
- DBMA 기본 경로(`tsu_dataset.jsonl` / `RetrievalEngine` / `chat.py`) 문단화
  — ADR-007/008 Proposed, Architecture Freeze.
- F6 (`chat.py` ↔ `bridge_query` 배선) 및 `modules.nae_pd.enabled: true` 전환
  — HQ 별도 승인.
- Smith(`nae_ref_v1`) 문단 확장·citation 승격 — CON-006/CON-011 (rights 부재).
- 한국어 QueryParser (감사 §9 항목 3), 교단 프로파일/ADR-009 (요구 2).
- rag_judge fluency/completeness **구현** — 설계 초안만 (§5-2).

### 금지
- `core/retrieval.py`, `core/module_registry.py` 수정.
- `NAE/pipeline/tsu/**`, `NAE/corpus/tsu/**`, `NAE/corpus/canonical/**` **쓰기**
  (canonical은 read-only). `output/bench/tsu_dataset.jsonl` 쓰기.
- 재임베딩 / 재색인 / Qdrant upsert / `builder_version` 변경.
- `nae_tsu_v1` / `nae_ref_v1` mutation. sandbox 컬렉션 생성·삭제.
- ADR-024 §C 계약 필드(`content_excerpt`) 시맨틱 변경.
- 인접 브랜치 `_GROUNDING_DIRECTIVE` 문구 재작성 (원문 정본).
- F2 실행 중 `NAE/pipeline/` 및 GPU 점유 벤치 — Stage 7 육안 평가는 F2와
  GPU 공유 시 응답 지연 감수(정확도엔 무영향), 대량 rag_judge 실행은 F2 종료 후.

### C1 위임 가능 (CUE 검증 전제)
- §1-3 `reconcile.py` **실행** (스크립트는 CUE 제공, C1은 raw 출력 보고).
- `tests/test_nae_paragraph_resolver.py` 등 **픽스처 생성** (경로 override
  전부 확인 — memory: Test Fixture Path Overrides).
- Stage 7 AT 실행 중 기계적 캡처 (판정은 CUE).
- **위임 금지**: ParagraphResolver/컨텍스트 포맷/프롬프트 조항/`Citation` 결정/
  ADR 정합 판단 (감사 §"세션 운용 메모" — 설계·ADR 판단 C1 이양 금지).

---

## 10. 산출물 목록

| 파일 | 종류 |
|---|---|
| `NAE/pipeline/canonical/paragraph_lookup.py` | 신규 코드 |
| `NAE/retrieval_adapter.py` | 수정 (매핑·조립·서브플래그) |
| `NAE/answer_context.py` *(또는 adapter 내 함수)* | 신규/수정 |
| `core/generation.py` | 수정 (브리지 프롬프트 조항; ae05415 미병합 시 선반영) |
| `core/evaluation/answer_completeness.py` | 신규 코드 |
| `ui/pages/research.py` | 수정 (`_render_nae_section` 렌더) |
| `tests/test_nae_paragraph_resolver.py` / `test_nae_answer_context.py` / `test_answer_completeness.py` | 신규 테스트 |
| `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_RECONCILE_001.md` | Stage 1 결과 |
| `docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md` | 설계 초안 |
| `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_ACCEPTANCE_001.md` | AT raw 산출물 |
| `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_BUILD_REPORT_001.md` | Build Report |

---

## 11. 실행 순서 요약

```
Stage 1 (게이트: 정합성 스캔 > 5% 실패 → STOP)
  → Stage 2 (Resolver + 매핑; Citation 필드 추가 필요 시 STOP·Amendment)
  → Stage 3 (컨텍스트 블록 + 프롬프트)
  → Stage 4 (인용 카드 UI)
  → Stage 5 (규칙 기반 완결성 판정 + 지표 설계 초안)
  → Stage 6 (서브 플래그 + 격리 테스트)
  → Stage 7 (AT-1~10 + 회귀)
  → Stage 8 (C1 Review → Build Report → commit/push/PR)
```

*본 TO는 DRAFT다. HQ 승인 및 설계 PR #10 병합 전에는 착수하지 않는다.*
