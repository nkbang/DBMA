---
title: "NAE 완성 문단 형태 답변 전달 설계 (Paragraph Answer Delivery Design) v1"
created: 2026-09-10
status: DESIGN ONLY — 구현 금지, 구현 Task Order 별도
scope: NAE 교단신학 corpus(Dagg / Hiscox / Fuller) 대상 답변 조립·인용·생성 경계
base: dev/dbma-engine @ d86b60a (감사 시점), venv ~/envs/dbma311
authors: CUE
related:
  - docs/DBMA_NAE_EVIDENCE_BASED_IMPROVEMENT_PROPOSAL_v1.md
  - docs/DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md
  - docs/NAE_FULLER_VOL01_SANDBOX_RETRIEVAL_TEST_001.md
  - docs/reports/THEOLOGICAL-RESPONSE-QUALITY-AUDIT-2026-09-10.md (branch claude/theological-pastoral-response-quality-89b049)
adr_refs:
  - ADR-001 (Retrieval Engine Authority) — Accepted
  - ADR-002 §5 (Retrieval Citation Strategy) — Accepted
  - ADR-024 §C/§D/§H/§I (NAE Production Retrieval Bridge) — Approved
  - ADR-030 v2.1 §7/§8/§11 (NAE Sermon Corpus Governance) — IMPLEMENTED
  - ADR-010 (RAG Evaluation & Quality) — Accepted(구조)
  - ADR-007 / ADR-008 (Semantic Chunking) — Proposed (본 설계의 대상 아님)
---

# NAE 완성 문단 형태 답변 전달 설계 v1

> **본 문서는 설계안이다. 어떤 코드·설정·데이터·인덱스·서비스도 변경하지 않는다.**
> 구현은 별도 Task Order로 발급된다. 전체 corpus 재청킹·재임베딩·재색인은 D안으로만
> 기록하며 현 권고가 아니다.

---

## 0. 한 줄 요약

검색 단위는 TSU(문장 단위 원자 재진술)로 **그대로 두고**, **답변 조립 시점에** 각
검색 히트를 그 히트가 유래한 `canonical.json`의 **원문 문단 전체**로 확장해
생성 컨텍스트와 인용 카드에 "의미적으로 완성된 문단"으로 제공한다. 재임베딩·
재색인·`builder_version` 변경 없음 → **옵션 A(문단 앵커드 근거) 권고**.

---

## 1. 문제 정의

### 1.1 제품 목표 (Rev. Bang, 2026-09-10)

배포 시 목회자(설교자) 사용자가 받아야 하는 답의 조건:

1. **처리된 자료에 근거** — 웹·타 AI 자료의 무분별한 혼입 차단
2. 사용자의 **교단 신학·개인 신학**이 건강하게 적용
3. 인용/근거 자료가 **"의미 집합적으로 완성된 문단, 완전한 문단의 형태"**
4. 사용자 주 언어(**한국어**)로 **문법적·문학적으로 완결된 문장·문단**
5. 일반 상식을 넘어 **정확한 자료에 기반한 고도의 신학적·목회적** 답

### 1.2 현재 구조의 긴장점

NAE TSU 파이프라인:

```
canonical.json
  → parser.build_candidates() : 문단의 각 "문장"을 claim 후보로 분해
  → claim.extract_claim(LLM)  : 문장 1개 → 재진술 claim 1개 (+ doctrine, refs)
  → TSU record                : 원자적 단문 1개
  → bge-m3 임베딩(claim 필드) → nae_qdrant / nae_tsu_v1
```

**TSU는 원자적 단문**이다. 사용자가 요구하는 전달 단위("완전한 문단")와
근본적으로 불일치한다. 그러나 **검색 단위**(TSU, 정밀도가 높음 — 3.2 참고)와
**답변 근거 전달 단위**(완성된 문단)는 분리 가능한 별개 문제다. 본 설계는
검색 정밀도를 유지한 채 전달 단위만 문단으로 올린다.

### 1.3 이 트랙의 범위

- **대상**: NAE 교단신학 corpus(Dagg / Hiscox / Fuller). `bridge_query()` 경로.
- **비대상**: DBMA 기본 경로(`output/bench/tsu_dataset.jsonl`, 현재 MAT 단일
  문서, 1200/120 청크). 이쪽의 청크 단위 문제는 ADR-007/008(Proposed) 영역이며
  Architecture Freeze Rule상 새 ADR 없이 진행 불가 — 본 설계가 다루지 않는다.
- **산출물**: 본 설계 문서 하나. 구현 Task Order 별도.

---

## 2. 현 구조 사실 (코드·데이터 실측)

### 2.1 canonical.json에 문단 구조가 보존되어 있다

실측 (`NAE/corpus/canonical/Fuller_Complete_Works_Vol01/canonical.json`):

```
top keys : identifier, pipeline_version, source, page_count,
           paragraphs, footnotes, scripture_references
paragraph: { index, type, text, page_start, page_end,
             sentences:[{sentence_index, text}], scripture_references }
```

- `paragraphs[]`는 2,250개(Vol.01). 각 문단은 `text`에 **문단 전문**을 갖는다
  (예: index 24, page_start 1, 614자).
- 문단별 `scripture_references`가 **문단 레벨에 존재**한다 — TSU 레코드의
  `scriptures`가 0건(3.3)인 것과 대조적.

### 2.2 TSU 레코드 / Qdrant payload가 문단으로 역추적 가능한 키를 갖는다

- TSU 레코드(`NAE/pipeline/tsu/builder.py:247-254`): `identifier`,
  `source_identifier`, `canonical_version`, `page`, **`paragraph`**(문단 index),
  **`sentence`**(문장 index), `source_text`(문장 원문), `claim`.
- Qdrant payload(`NAE/pipeline/index/qdrant_store.py:41-88`)에 `identifier`,
  `paragraph`, `sentence`, `page`, `canonical_version`, `source_text`,
  `source_id`/`work_id`/`edition_id`/`volume_id` 등이 **이미 상주**한다.
- `context_before`/`context_after`는 claim 추출에만 쓰이고 TSU 레코드엔 저장되지
  않는다(`builder.py:233-234`) — 즉 "앞뒤 문장"은 payload에 없지만
  `(identifier, paragraph)`로 canonical.json에서 언제든 복원 가능.

### 2.3 문단 복원은 이미 프로젝트 안에 검증된 패턴이 있다

`NAE/pipeline/verify/consistency.py:44-49`가 build-time과 무관하게 canonical.json
에서 문단을 직접 재도출한다:

```python
for paragraph in canonical_json.get("paragraphs", []):
    if paragraph.get("index") == record.get("paragraph"):
        paragraph_text = paragraph.get("text", "")
        break
```

옵션 A의 "문단 리졸버"는 이 패턴의 재사용이다(신규 알고리즘 아님).

### 2.4 검색 → 인용 → 생성 경계 (현행)

| 계층 | 파일·위치 | 현행 동작 |
|---|---|---|
| 검색(정본) | `core/retrieval.py::RetrievalEngine` / `QueryProcessor` | TSU dataset + in-memory 유사도. Qdrant 미쿼리(ADR-001 Correction, ADR-024 §Context 3) |
| NAE 브리지 | `NAE/retrieval_adapter.py::bridge_query()` | query_text → bge-m3 → `nae_qdrant` 검색 → `_map_nae_to_citation_metadata()` → `CitationBuilder.build_citations()` → `list[Citation]`. `nae_pd` 모듈 게이트(기본 false) |
| 컨텍스트 조립 | `core/retrieval.py::ContextAssembler.assemble()` (1809-1848) | 히트당 `<context id="{tsu_id}" score="…">{content}</context>`. **서지 정보 없음** |
| 인용 | `core/retrieval.py::CitationBuilder.build_citations()` (1880-1917) | `verse_mapping` 파생 `scripture_reference` + `content_excerpt = content[:200]` |
| 생성(Q&A) | `core/generation.py::GenerationService._build_prompt()` (262-276) | `문맥:\n{llm_context_block}\n\n질문:\n{question}` — **근거 강제·완결성 지시 없음** |
| 생성(설교) | `core/generation.py` `_QUALITY_DIRECTIVE` / `_format_sermon_context()` | `[자료N]` 라벨 + "최소 1회 인용" — Q&A 경로엔 미적용 |

### 2.5 현행 값 손실 지점 (옵션 A가 겨냥하는 곳)

- **200자 절단**: `bridge_query()`가 `RankedCandidate.content =
  meta.get("content_excerpt", "")`로 넣는다(`NAE/retrieval_adapter.py:222`,
  `content_excerpt = source_text[:200]` `:138`). Fuller Vol.01 `source_text`
  평균 204자·중앙값 173자·**59.4%가 200자 미만**(감사 §3-2) — 상한이 실제로
  물려 모델이 **문장 중간에서 잘린 조각**을 근거로 받는다.
- **원자 단문이 근거로 노출**: `source_text`(문장 1개) 또는 `claim`(LLM 생성
  한국어 요약)이 인용 단위가 된다. "완전한 문단" 요구와 불일치.
- **서지 정보가 LLM에 안 감**: `ContextAssembler`의 `<context>` 블록에 저자·서명·
  페이지가 없어(감사 §5 결함 B) 모델이 본문 안에서 출처를 밝히지 못한다.
  `Citation` 객체엔 있으나 생성 프롬프트엔 전달되지 않는다.

### 2.6 인접 세션의 in-flight 수정 (base에 미병합)

브랜치 `claude/theological-pastoral-response-quality-89b049`(커밋 `ae05415`,
`dev/dbma-engine`에 **미병합**)이 다음을 이미 만들었다:

- `core/generation.py::_GROUNDING_DIRECTIVE` / `_GROUNDING_DIRECTIVE_NO_CONTEXT`
  — "위 자료에 실제로 적힌 내용만 근거", "완결된 한국어 문장", "경어체" 지시.
  `_build_prompt()`가 자료 블록과 질문 사이에 삽입, 라벨 `문맥:` → `자료:`.
- `NAE/retrieval_adapter.py` — 매핑 dict에 `source_text` **전문** 필드 추가,
  `RankedCandidate.content`가 이를 사용(200자 절단 제거). `Citation.content_excerpt`
  200자는 유지(ADR-024 §C 계약).
- 판단 기록: **`RankedCandidate.content`는 ADR-024 §C 계약 대상이 아니다** →
  Freeze Rule 위반 없음, Amendment 불요.

→ **본 설계는 이 수정 위에 쌓는다.** 옵션 A는 `RankedCandidate.content`를
`source_text` 전문에서 **문단 전문**으로 한 단계 더 올리고, 서지·앵커 문장·
문단 인덱스를 추가한다. 인접 브랜치가 병합되지 않은 상태로 구현이 시작되면
`base가 origin/dev/dbma-engine 최신인지` 재확인이 선행되어야 한다(중복 재구현
방지).

---

## 3. 검색 품질·결함 현황 (Fuller Vol.01 sandbox 실측)

`docs/NAE_FULLER_VOL01_SANDBOX_RETRIEVAL_TEST_001.md` (2026-09-09):

### 3.1 파이프라인 정상

canonical → TSU(3,643) → bge-m3(claim 필드, 프로덕션 경로) → Qdrant → 검색
end-to-end 작동. `nae_tsu_v1` 3,319 무변동, `nae_ref_v1` 무접촉.

### 3.2 검색 정밀도 — Vol.01이 다루는 교리에서 강함

| 질의 유형 | FULLER-V01 top1 | baseline top1 | 판정 |
|---|---|---|---|
| 믿음=의무 | 0.915 | 0.745 | Fuller 압도 |
| 오직 은혜 구원 | 0.870 | 0.718 | Fuller 우세 |
| 미회심자의 믿을 의무 | 0.832 | 0.670 | Fuller 압도 |
| 세례 대상 | 0.659 | **0.722** | baseline 우세 |
| 교회 권징 | 0.566 | **0.692** | baseline 우세, Fuller off-topic |

→ TSU 벡터 검색의 **주제 정밀도는 유지 가치가 있다**. 약점은 (a) 비교·관계형
질의 (b) 소스 커버리지 편중이지 "검색 단위가 문장이라서"가 아니다. **옵션
A는 이 정밀도를 건드리지 않는다.**

### 3.3 품질 결함

| 결함 | 건수 | 비율 | 원인 |
|---|---|---|---|
| claim에 한자(CJK) 혼입 | 366 | 10.0% | `my-theology-bot-v2`(Qwen 계열) 부하 시 코드스위칭 — **모델 출력 결함** |
| 의문문 형태 claim | 58 | 1.6% | 추출기가 수사의문문을 claim화 |
| `scriptures` 0건 | 3,643 | 100% | TSU 레벨 성경 매핑 미채움 (문단 레벨엔 존재, 2.1) |
| `review_status=generated` | 3,643 | 100% | 사람 검토 0 (sandbox) |

→ **CJK 10%는 `claim` 필드의 결함이다.** 옵션 A는 근거 단위를 `claim`이 아니라
**canonical.json의 원문 문단**(사람 저작 OCR 텍스트)으로 바꾸므로 이 벡터를
**근거 계층에서 제거**한다(잔존은 OCR 노이즈 ~1.7%뿐).

---

## 4. 옵션 비교 (A ~ D)

### 4.1 옵션 정의

- **A. 문단 앵커드 근거 (answer-time enrichment) — 권고**
  검색 = TSU 유지. 답변 조립 시 각 히트를 `(identifier, paragraph)`로
  canonical.json에서 **원문 문단 전체**로 확장 → 생성 컨텍스트·인용 카드에
  완성 문단으로 제공. 히트의 원래 `source_text`는 "앵커 문장"으로 문단 안에
  표시(검색이 왜 걸렸는지). 재임베딩·재색인·`builder_version` 변경 없음.
  변경 지점: `NAE/retrieval_adapter.py`(문단 리졸버 + 매핑 확장),
  선택적으로 `ContextAssembler` 컨텍스트 포맷, 인용 카드(UI).

- **B. 이중 granularity 색인**
  TSU + 문단 단위 임베딩을 **병행 색인**(새 컬렉션 `nae_para_v1` 등). TSU로
  검색 → 문단으로 확장하되 문단도 벡터로 검색 가능. 문단 임베딩 재계산·
  저장 비용. Amendment(신규 임베딩 대상) 필요.

- **C. 문단 단위 재청킹**
  parser가 문장이 아니라 문단 단위 candidate를 emit. claim 정밀도 손실
  (문단 하나에 여러 주장 혼재 → doctrine 분류·중복 제거·검색 정밀도 저하),
  `builder_version` 상승, Amendment A 갱신, 전체 재빌드. 대규모.

- **D. 대규모 교체/재작성** — D안으로만 기록, **현 권고 아님**
  vector DB 전환, NAE bridge 기본 활성화, 전체 재청킹·재임베딩·재색인, 생성
  모델 교체, LoRA. `DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md` Conflict
  Protocol §5: 최소 변경(A/B)으로 해결 불가함이 **정량 입증된 뒤에만** 재상정.

### 4.2 비교표

| 기준 | A. 문단 앵커드 | B. 이중 색인 | C. 문단 재청킹 | D. 대규모 |
|---|---|---|---|---|
| 데이터 무결성 (`nae_tsu_v1` 3,319 / `nae_ref_v1` 34,948 / `tsu_dataset.jsonl`) | **불변 — read-only** | 불변 + 신규 컬렉션 추가 | **파괴적 — 전체 재빌드** | 파괴적 |
| 기존 경로 보존 (ADR-001 RetrievalEngine) | **무수정** (답변 조립 계층만) | 무수정, 검색 경로 1개 추가 | 무수정하나 데이터셋 교체 | 수정 |
| `builder_version` / Amendment A / F2~F4 게이트 | **무영향** | 신규 임베딩 대상 → Amendment 갱신 | `3.0.0` 상승 → Amendment 재작성 | 재작성 |
| 검색 품질 | 유지 (검색 미변경) | 유지 + 문단 검색 옵션 | **저하 위험** (문단당 다주제) | 불확실 |
| 인용 정확성 | **개선** — 원문 문단 verbatim, CON-003 오매핑 회피 | 개선 | 개선하나 claim 추적성 약화 | 불확실 |
| 답변 완결성 (요구 3·4) | **직접 해결** (완성 문단 컨텍스트) | 해결 | 해결 | 해결 |
| CJK 오염(3.3) | **근거 계층에서 제거** (문단=사람 저작) | 부분 (문단 임베딩도 원문 기반) | 부분 | 부분 |
| 성능 | +문단 리졸브 ~수십 ms (canonical.json LRU 캐시) | +문단 임베딩 저장/검색 비용 | 재빌드 수 시간 | 수일 |
| rollback | **config 1줄 / 단일 파일 revert** | 컬렉션 drop + 코드 revert | 데이터셋 롤백 필요 | 대규모 |
| backward compat | 완전 (additive, `nae_pd` 게이트) | 높음 | 낮음 (스키마·ID 변동) | 낮음 |
| acceptance 비용 | 낮음 (문단 복원 대조 + 완결성 판정) | 중 | 높음 (전체 회귀) | 매우 높음 |
| 의존성·위험 | canonical.json 존재·정합(가정 1), UI 카드 변경 | Qdrant 용량, 이중 검색 랭킹 정책(ADR 필요) | Amendment A 재승인, claim 파이프라인 재설계 | 다수 |
| ADR 충돌 | 없음 (ADR-002 §5 확장 지점, ADR-024 §C 비계약 필드) | ADR-013/024 개정 필요 | Amendment A + ADR-030 §11 재검토 | 다수 |

### 4.3 권고: **옵션 A**

근거:
1. 요구 3·4를 **검색 정밀도 손실 없이, 데이터 무결성 위반 없이** 해결하는
   유일한 최소-변경 경로.
2. 복원 메커니즘이 이미 프로젝트 안에 검증돼 있다(2.3, `consistency.py`).
3. `nae_pd` 모듈 게이트 안에 완전히 들어가 DBMA 기본 경로·`chat.py`에 무영향
   (요구된 F6 배선과 독립).
4. CJK 10% 결함을 근거 계층에서 제거(부수 효과).
5. rollback이 config 1줄. Conflict Protocol 준수(파괴적 변경 0).

한계(4.4에서 완화):
- 문단이 매우 길면(>1,500자) 컨텍스트 토큰 압박 — 상한·요약 정책 필요.
- canonical.json ↔ payload `paragraph` 인덱스 정합이 **가정**(가정 1) —
  구현 전 reconciliation 체크 필수.
- 교단 신학 반영(요구 2)은 옵션 A 범위 밖 — ADR-009(SIL) 별도 트랙.

### 4.4 옵션 A 상세 설계

**4.4.1 문단 리졸버 (`ParagraphResolver`)**

- 위치(제안): `NAE/retrieval_adapter.py` 헬퍼 또는 신규
  `NAE/pipeline/canonical/paragraph_lookup.py`.
- 입력: `(identifier, paragraph_index)` — 둘 다 Qdrant payload에 상주(2.2).
- 동작: `canonical_root/<identifier>/canonical.json` 로드(identifier 단위
  `functools.lru_cache` 또는 프로세스 캐시) → `paragraphs[]`에서
  `index == paragraph_index`인 항목 → 반환:
  ```
  { text, page_start, page_end, index,
    scripture_references,          # 문단 레벨 (TSU엔 0건)
    canonical_version }            # payload.canonical_version와 대조용
  ```
- 실패 처리(fail-soft): canonical.json 부재 / 인덱스 불일치 /
  `canonical_version` 불일치 → 리졸브 실패를 로그로 남기고 **해당 히트는
  `source_text` 전문으로 폴백**(인접 브랜치 동작). 예외를 호출자에
  전파하지 않는다(ADR-024 §G fail-closed 원칙과 정합).
- 멀티 문단: parser가 문장을 문단 단위로 귀속시키므로 1 TSU = 정확히 1 문단.
  기본은 단일 문단. 튜닝 옵션으로 `±1` 이웃 문단 포함 가능
  (`NAE_PARAGRAPH_NEIGHBORS`, 기본 0).

**4.4.2 매핑 확장 (`_map_nae_to_citation_metadata` 이후)**

히트당 다음을 조립:
- `evidence_paragraph`: 문단 전문 (생성 컨텍스트·인용 카드 본문)
- `anchor_sentence`: 원래 `source_text` (문단 안에서 하이라이트)
- `bibliography`: `author` / `book`(work) / `edition_id` / `volume_id` /
  `page_start`–`page_end` / `paragraph` index / `identifier`
  (전부 payload + 리졸버 결과에서 옴, 신규 추론 없음 — ADR-024 §C 정신)
- `authority_class`: `source_id` → `NAE/authority/` 매니페스트 조회(ADR-030
  §8, source manifest). 표시 전용. 조회 실패 시 생략.

**4.4.3 생성 컨텍스트 블록 (`ContextAssembler` 또는 브리지 로컬 포맷)**

현행:
```
<context id="TSU-0004289" score="0.8321">
회심하지 않은 죄인들은 그리스도를 믿어야 할 의무가 있다.
</context>
```
옵션 A:
```
<자료 id="TSU-0004289" work="The Gospel Worthy of All Acceptation"
       author="Andrew Fuller" page="p.132" para="§418">
{문단 전문 — 의미적으로 완결된 원문 문단}
  <일치문장>회심하지 않은 죄인들은 그리스도를 믿어야 할 의무가 있다.</일치문장>
</자료>
```
- `ContextAssembler.assemble()`은 Chat/Research 공용이므로(감사 §5 결함 B
  주석) **브리지 전용 포맷 함수**를 두는 편이 안전(설교 경로
  `_format_sermon_context()` 선례). `core/retrieval.py` 무수정 유지 →
  ADR-001 무영향.
- 서지 속성이 블록에 들어가므로 감사 §5 결함 B도 동시 해소.

**4.4.4 생성 프롬프트 (요구 4·1)**

인접 브랜치 `_GROUNDING_DIRECTIVE` 위에 문단·완결성 조항 추가(브리지 경로
한정, 또는 `_GROUNDING_DIRECTIVE`에 조건부 병합):
- "각 `<자료>`는 완결된 원문 문단이다. 인용할 때 조각을 그대로 붙여넣지 말고,
  문단의 논지를 **2~4개의 완결된 한국어 문단**으로 재구성하라."
- "각 문단에서 최소 1개 `<자료>`를 근거로 명시하고, 본문 안에서
  '풀러는 …라고 말한다' 식으로 저자·저작을 밝혀라."(서지 속성 활용)
- sandbox의 "3~6문장 간결" 상한(`scripts/nae_fuller_sandbox_search_app.py:59`)
  은 **프로덕션 목회 답변 경로에서 제거** — 길이 상한 대신 "완결성" 기준
  (4.4.6 판정).

**4.4.5 인용 카드 (요구 3)**

`ui/pages/research.py::_render_nae_section()` / `render_citation_card` 확장:
- 본문 = `evidence_paragraph` 전문(≠ `content_excerpt[:200]`)
- 서지 라인 = 저자 · 저작명 · edition · `p.{start}–{end}` · `§{para}`
- `anchor_sentence` 하이라이트 = "이 문단에서 질의와 일치한 문장"
- TSU `claim`(LLM 생성 한국어 요약)은 **접힌 '요지' 줄로만**, "AI 요약" 라벨
  명시(감사 §4.3 위험). 카드 본문으로 쓰지 않는다.
- 문단에 CJK/OCR 노이즈가 있으면 ⚠ 배지(sandbox `🈲CJK` 선례). **원문 표시를
  자동 편집하지 않는다.**
- `Citation` dataclass는 **변경하지 않는 경로를 우선**: UI가 리졸버를 직접
  호출해 문단을 얻는다. 부득이 필드를 추가하면
  `evidence_paragraph: Optional[str] = None`(후행 옵셔널, 기존 패턴과 동일,
  additive) — 이 경우 ADR-024 §C에 **Amendment 각주 1줄** 추가 권고(가정 3).

**4.4.6 답변 완결성 판정 (요구 4)**

`core/evaluation/rag_judge.py` 확장(설계만 — ADR-010 Phase 2):
- 현행 `groundedness` 단일 지표에 `fluency`·`completeness` 추가(ADR-010이
  이미 지표명으로 열거).
- 한국어 특화 규칙: 모든 문장이 완결 어미로 끝남 / 매달린 종속절 없음 /
  40자 초과 영어 원문 스팬 0 / 경어체 일관.
- 판정 경로를 **chat/research 답변에 연결**(현재 설교 초안 경로뿐 — 감사 §7).

---

## 5. 하위 문제별 접근

### 5.1 답변 텍스트의 문법적·문학적 완전성

**근본 원인**: Q&A 생성 프롬프트가 `문맥:\n…\n질문:\n…`뿐이고(2.4), 모델
SYSTEM에도 완결성 지시가 없다(감사 §6). 근거가 200자 절단 조각이라 모델이
"빈칸 메우기"로 내장 지식·상투구를 섞는다.

**접근**:
1. 인접 브랜치 `_GROUNDING_DIRECTIVE` §3("완결된 한국어 문장")·§4(경어체)를
   base로 병합/유지.
2. 근거를 **완성 문단**으로 올려(옵션 A) 모델이 원문에서 재구성할 재료를
   충분히 받게 한다 — 이것이 완결성의 1차 조건.
3. 브리지 프롬프트에 "2~4 완결 문단 재구성" 조항 추가, sandbox의 "3~6문장"
   상한 제거(4.4.4).
4. `_detect_script_contamination` + 2회 재시도 + `_sanitize` 유지. 단
   `_sanitize`가 발동한 답변은 **문장이 손상된 상태**이므로(감사 §4.1) 사용자
   에게 "재생성 권장" 표식과 함께 제공(자동 배포 금지).
5. **검증**: 6장 AT-5 (rag_judge fluency/completeness + 영어 스팬 0 + 어미
   완결 + ≥1 인용).

### 5.2 근거(citation) 단위 = 완전한 원문 문단

**접근**: 4.4.1 리졸버 + 4.4.5 카드. 요점:
- 카드 본문 = canonical.json `paragraph.text` verbatim.
- 서지·페이지 범위·문단 인덱스·`identifier` 동반 → 학술 인용 가능 수준
  (PB-02 / CON-002 부분 완화).
- `anchor_sentence`로 TSU 정밀도 신호는 유지하되 원자 claim을 인용 본문으로
  삼지 않는다.
- **교단 위계**: `authority_class`(ADR-030 §7 — source/manifest 계층, TSU
  레코드에 쓰지 않음)를 `source_id`로 조회해 표시 전용으로 부기.
- CON-003(verse_mapping ↔ 본문 불일치): 옵션 A는 `verse_mapping` 파생
  `scripture_reference`를 **locator로 신뢰하지 않는다**. locator = 실제 문단
  텍스트 + `§para` + `p.range`(틀릴 수 없는 값). 문단 레벨
  `scripture_references`(2.1)가 TSU `verse_mapping`보다 신뢰도 높음.

### 5.3 NAE vs DBMA 기본 경로 / F6와의 관계

- 활성 Chat(`ui/pages/chat.py`)은 `bridge_query`를 호출하지 않는다. NAE 경로는
  `ui/pages/research.py:185` `_render_nae_section()` 하나뿐이며
  `modules.nae_pd.enabled=false`로 꺼져 있다(ADR-024 §F).
- 옵션 A의 코드는 전부 `bridge_query()` / `_render_nae_section()` 안에 들어가
  **모듈 게이트를 그대로 상속**한다. DBMA 기본 경로
  (`tsu_dataset.jsonl`, RetrievalEngine)와 `chat.py`에 **바이트 무영향**.
- **F6(chat.py ↔ bridge 배선)**: 별도 승인 사항. 옵션 A는 F6과 독립적으로
  sandbox(`nae_tsu_fuller_sandbox_v0`) + `nae_tsu_v1`에서 검증 완료 상태로
  대기시킬 수 있다. F6이 승인되면 옵션 A는 이미 준비된 상태로 함께 활성화.
- DBMA 기본 경로의 문단화는 ADR-007/008(Proposed) — 본 트랙 대상 아님(1.3).

### 5.4 CJK 오염의 답변 전파 차단

3계층 방어:
1. **근거 계층**: 근거 단위를 `claim`(모델 출력, CJK 10%)에서 **canonical.json
   문단**(사람 저작)으로 전환 → LLM 코드스위칭 CJK가 근거에서 사라짐. 잔존은
   OCR 노이즈(~1.7%)뿐. (F2→F3 재추출은 `claim` 정화용으로 병행하되 옵션 A의
   전제 조건은 아님.)
2. **생성 출력**: `_detect_script_contamination` + 재시도 + `_sanitize` 유지
   (5.1-4). sanitize 발동 시 "재생성 권장" 표식.
3. **카드 표시**: 문단 verbatim + ⚠ 배지. 자동 편집 금지.

### 5.5 웹/타 AI 무분별 혼합 방지

- **물리적**: `core/`·`ui/`에 외부 API 호출 없음(감사 §1). 유일 네트워크 =
  로컬 Ollama / 로컬 Qdrant. 옵션 A는 canonical.json(로컬 파일)만 추가로
  읽는다 — 신규 네트워크 경로 0.
- **논리적**: `_GROUNDING_DIRECTIVE` §1("위 자료에 실제로 적힌 내용만"). 옵션
  A가 이를 강화 — 완성 문단은 모델이 **원문에서 답할** 재료를 주므로 파라메트릭
  지식 회귀 유인이 감소.
- **소스 분리**: `bridge_query`는 `nae_qdrant`/`nae_tsu_v1`만(ADR-024 §H),
  리졸버는 `NAE/corpus/canonical/`만 — 둘 다 NAE corpus 내부. DBMA corpus·웹
  접근 없음. NAE 결과는 별도 섹션·배지(ADR-024 §B/§H).
- **ClaimGuard**: 현재 절대표현 사후 탐지만(감사 §1.3), 날조 자체는 미탐지.
  **권고(설계 레벨)**: rag_judge groundedness 게이트를 chat 경로에 연결해
  "제공 문단에 정합하지 않는 문장"을 플래그(ADR-010 Phase 2). ClaimGuard 자체
  변경은 본 설계 범위 밖.
- DatasetRegistry / ClaimGuard v3(NAE Unified Search v3, memory) — 향후 트랙,
  옵션 A의 선행 조건 아님.

---

## 6. Acceptance Test

| ID | 목적 | 판정 기준 |
|---|---|---|
| AT-1 | 데이터 무결성 | `nae_tsu_v1` points_count == 3,319 · `nae_ref_v1` == 34,948 · `output/bench/tsu_dataset.jsonl` sha256 불변 · `builder_version` 쓰기 0 · `git diff core/retrieval.py` 빈 결과 |
| AT-2 | 문단 복원 정확도 | 표본 N(≥200) 히트에 대해 `ParagraphResolver(identifier, paragraph).text` == canonical.json `paragraphs[paragraph].text` 완전 일치 · payload `source_text`가 복원 문단의 부분문자열인 비율 ≥ 95%(OCR 정규화 여유 허용) · 불일치는 crash 없이 로그 + `source_text` 폴백 |
| AT-3 | 생성 컨텍스트 | NAE 질의의 `llm_context_block`이 문단 전문(len > 200, canonical 대조 일치) + `work`/`author`/`page` 속성 포함 · 200자 절단 흔적 0 |
| AT-4 | 인용 카드 | 카드 본문 = 문단 전문(≠ excerpt) · 서지 라인(저자·저작·edition·`p.range`·`§para`) 렌더 · `anchor_sentence` 하이라이트 · TSU `claim`은 "AI 요약" 라벨의 접힌 줄로만 |
| AT-5 | 답변 완결성 | 고정 질의셋 10~15건(sandbox 문서의 Vol.01 교리 질의)에서 rag_judge fluency·completeness ≥ 임계 · 40자 초과 영어 원문 스팬 0 · 모든 문장 완결 어미 · ≥ 1 인용 참조 |
| AT-6 | CJK 차단 | Vol.01 CJK 오염 366 claim의 **부모 문단**에 LLM-CJK 0(OCR 잔존만) · 생성 출력 CJK율 가드 후 0 |
| AT-7 | 격리 | `modules.nae_pd.enabled=false` → 리졸버 미호출 · `bridge_query` disabled 예외 · DBMA 기본 경로 답변 바이트 동일 |
| AT-8 | 성능 | canonical.json LRU 워엄 상태에서 문단 리졸브 추가 지연 < ~50ms/질의 · 콜드 로드 < 500ms/vol · 실측 기록 |
| AT-9 | rollback | `NAE/retrieval_adapter.py` + 리졸버 모듈 단일 revert로 이전 동작 복귀 · `nae_pd=false` 즉시 비활성 |
| AT-10 | 정합성 게이트 | 인덱싱된 모든 `identifier`에 canonical.json 존재 · payload `canonical_version` == canonical.json `pipeline_version` (가정 1 해소) |

기존 회귀: `tests/test_book_alias_resolution.py`,
`tests/test_query_enhancements_full_regression.py`,
`pytest -k "generation or nae_retrieval or bridge or citation or claim_guard"`
전부 PASS 유지(ADR-024 §J 준용).

---

## 7. Rollback

| 계층 | 조치 | 즉시성 |
|---|---|---|
| 설정 | `config.yaml: modules.nae_pd.enabled: false` | 즉시, 재배포 불필요 (ADR-024 §I) |
| 서브 플래그 | `NAE_PARAGRAPH_EVIDENCE=0`(기본 off) — `nae_pd`는 켠 채 문단 확장만 차단, 검증 중 A/B용 | 즉시(요청마다 조회, CON-009 B) |
| 코드 | 신규 리졸버 모듈 + `NAE/retrieval_adapter.py` diff revert. `core/retrieval.py` 무수정이므로 DBMA production 무연쇄(ADR-024 §I) | 단일 PR revert |
| 컨텍스트 포맷 | 브리지 전용 포맷 함수 → 이전 `ContextAssembler.assemble()` 호출로 되돌림 | 함수 1개 revert |
| 데이터 | **없음** — 아무것도 쓰지 않음 | N/A |

---

## 8. ADR 정합 (CON-012 준수 — 관련 Approved ADR 본문 확인 결과)

| ADR | Status | 조항 | 옵션 A 정합 |
|---|---|---|---|
| **ADR-001** Retrieval Engine Authority | Accepted | "신규 검색/RAG 기능은 `core/retrieval.py` 계약 위에서만; 새 병행 검색 경로 금지" | **정합.** 옵션 A는 검색이 아니라 **답변 조립 계층**. 스코어링·랭킹·벡터스토어 쿼리 없음 — payload에 이미 있는 ID로 하는 결정적 dict 조회. ADR-024가 `CitationBuilder` 재사용을 "병행 경로 아님"으로 규정한 것과 동일 성격. `RetrievalEngine` 무수정(AT-1). |
| **ADR-002 §5** Retrieval Citation Strategy | Accepted | "표시 계층 현행 유지 + 추적성 필드 추가", "`CitationBuilder`가 `source_file`을 각주로 부기할 수 있는 **확장 지점을 열어둔다**" | **정합 — 옵션 A가 그 확장 지점을 구현.** 문단 + 서지 provenance를 인용에 부기하는 표시 계층 변경. |
| **ADR-024 §C/§D** NAE Production Retrieval Bridge | Approved | §C: `Citation` 11필드 매핑표. §D: `bridge_query() -> list[Citation]`. §H: `nae_qdrant`만 접근. §I: config 롤백 | **정합.** `RankedCandidate.content`는 §C 계약 대상 아님(감사 §3-3, 인접 브랜치 판단). 문단은 `content` 및 신규 표시값으로 전달. `Citation`에 필드 추가 시에만 §C Amendment 각주 필요(가정 3, UI-resolve 경로면 불요). `nae_qdrant` 외 접근 없음(리졸버는 로컬 파일). |
| **ADR-030 v2.1 §7/§8/§11** Sermon Corpus Governance | IMPLEMENTED | "CLEAN baseline `nae_tsu_v1`=3,319 / `nae_ref_v1`=34,948 **변경 금지**". §11: ACQUIRED ≠ EMBEDDING ELIGIBLE ≠ EMBEDDED ≠ RETRIEVAL-ELIGIBLE. §7: `authority_class`는 source/manifest 계층, **TSU 레코드에 쓰지 않음** | **정합.** 옵션 A는 canonical.json read-only, mutation 0. retrieval-eligible 집합 불변. `authority_class`는 조회·표시만(TSU 레코드 미기입). |
| **ADR-030 Amendment A** Fuller 처리 인가 | PROPOSED | F4 임베딩은 `review_status==verified`만, `bge-m3` 1024d, `builder_version` `3.0.0` 고정. 추출 프롬프트·모델·doctrine 분류기 변경은 Amendment 갱신 필요 | **정합.** 옵션 A는 추출·임베딩·분류기 무변경. Amendment 갱신 불요. |
| **ADR-010** RAG Evaluation & Quality | Accepted(구조) | `fluency`/`coherence`/`groundedness` 등 pointwise autorater. `question_answering_quality` reference-free 재정의는 Phase 4까지 보류 | **정합(설계 레벨).** 5.1/4.4.6의 rag_judge 확장은 ADR-010 지표 체계 안. 새 지표 정의는 Phase 2 구현 Task Order에서. |
| **ADR-007 / ADR-008** Semantic Chunking | Proposed | 판정 기준 미확정, 전환 미결정 | **무관.** 옵션 A는 재청킹이 아님. DBMA 기본 경로 문단화는 본 트랙 대상 아님(1.3). |

**Conflict Register 관련 항목**:
- **CON-012 (HOLD blocking)**: 본 문서가 그 선결 과제(retrieval/citation/generation
  경계 Approved ADR 본문 확인)를 위 표로 이행. 옵션 A는 Approved ADR과 충돌
  없음.
- **CON-003 (CONFIRMED_CONFLICT)**: 옵션 A가 `verse_mapping` locator 의존을
  제거(5.2) — 완화 방향.
- **CON-002 (COMPATIBILITY_CONSTRAINT)**: `source_title` null을 canonical.json
  `source` 블록 + payload `work_id`/`edition_id`로 부분 대체 — sidecar 없이.
- **CON-006 / CON-011 (Smith / rights)**: 리졸버는 Smith(`nae_ref_v1`)에도
  기술적으로 적용 가능하나, **본 설계는 `nae_tsu_v1` + Fuller로 범위 한정**.
  Smith 문단 확장·citation 승격은 rights 필드 부재(CON-011 REJECT) 해소 전까지
  별도. `nae_ref_v1` baseline 무접촉.

---

## 9. 미확인 가정

| # | 가정 | 확인 방법 | 미충족 시 |
|---|---|---|---|
| 1 | 인덱싱된 모든 `identifier`의 canonical.json이 디스크에 존재하고, `paragraphs[].index`가 payload `paragraph` 값과 정렬돼 있다(TSU 빌드 이후 canonical.json 재빌드 없음) | AT-10: payload `canonical_version` == canonical.json `pipeline_version` 전수 대조. `NAE/pipeline/verify/consistency.py` 방식 재사용 | 불일치 identifier는 `source_text` 폴백 + 재빌드 backlog 등록 |
| 2 | `paragraph` payload 필드가 프로덕션 3,319 포인트 전부에 채워져 있다(Fuller sandbox=확인, Dagg/Hiscox=미확인) | `nae_tsu_v1` payload 전수 스캔 (read-only) | null인 포인트는 폴백 |
| 3 | `Citation` dataclass에 옵셔널 필드 추가가 ADR-024 §C 계약 위반이 아니다 | 구현 Task Order에서 확인. 권고: **UI가 리졸버를 직접 호출**해 `Citation` 무변경 경로 우선 | Amendment 각주 1줄 추가 후 진행 |
| 4 | rag_judge의 한국어 fluency/completeness 지표를 ADR-010 구조 안에서 정의 가능 | ADR-010 Phase 2 구현 Task Order. `question_answering_quality` reference-free 재정의는 이 문서가 해결하지 않음 | 지표 없이 AT-5를 규칙 기반(어미·영어 스팬)으로만 운용 |
| 5 | `NAE/authority/` 매니페스트가 인덱싱된 모든 `source_id`의 `authority_class`를 커버(ADR-030 §8: source_manifest 10 records; Fuller Vol.01–08 = ADMITTED, memory) | 매니페스트 ↔ payload `source_id` 조인 대조 | `authority_class` 표시 생략(카드는 나머지 서지로 동작) |
| 6 | F6(chat.py ↔ bridge 배선)과 `nae_pd` 활성화는 별도 승인이며 본 설계 범위 밖 | — | 옵션 A는 sandbox + `nae_tsu_v1`에서 검증 후 대기 |
| 7 | 1 TSU = 1 문단(parser가 문장을 문단에 귀속). 멀티 문단 근거가 필요한 비교형 질의는 `±1` 이웃 문단 옵션으로 충분 | sandbox 비교형 질의 5건 재실측 | 이웃 문단 기본값 상향 검토(별도) |
| 8 | 문단 길이 분포가 컨텍스트 예산(`num_ctx` 32768) 안에 top_k개 들어간다 | Vol.01 문단 길이 분포 측정(중앙값·p95·max) | `>1,500자` 문단은 앵커 문장 중심 ±window로 축약하는 상한 정책 추가 |

---

## 10. 구현 Task Order로 넘길 항목 (본 문서에서 결정하지 않음)

1. 문단 리졸버 배치 위치(`retrieval_adapter` 헬퍼 vs 신규 모듈) 및 캐시 전략.
2. `ContextAssembler` 브리지 전용 포맷 함수의 정확한 스키마·태그명.
3. `Citation` 무변경(UI-resolve) vs 옵셔널 필드 추가 — 가정 3 확인 후.
4. `_GROUNDING_DIRECTIVE` 병합 형태(브리지 전용 분기 vs 조건부 조항).
5. rag_judge fluency/completeness 지표의 구체 정의(ADR-010 Phase 2).
6. 문단 길이 상한·축약 정책 임계값(가정 8).
7. `authority_class` 매니페스트 조회 어댑터(ADR-030 §8).
8. AT-2/AT-10 정합성 게이트를 CI에 넣을지 여부.

---

*본 문서는 설계안이며, 어떤 코드·설정·데이터·인덱스·서비스·플래그도 변경하지
않았다. §8 표의 "정합" 판정은 나열된 ADR 본문(ADR-001, ADR-002, ADR-010,
ADR-024, ADR-030 v2.1)을 직접 판독한 결과다.*
