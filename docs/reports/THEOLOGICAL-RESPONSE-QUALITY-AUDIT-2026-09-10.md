---
title: 신학·목회 답변 품질 감사 (배포 기준 적합성)
created: 2026-09-10
status: 감사 완료 — 우선순위 1·2 수정됨(커밋 `ae05415`), 3·4·5 미착수
scope: core/generation.py, core/retrieval.py, NAE/retrieval_adapter.py, core/chunking_optimizer.py, NAE/corpus/tsu/
baseline: `32f59c9` (감사 시점) → `ae05415` (수정 후)
venv: `~/envs/dbma311`
---

# 신학·목회 답변 품질 감사

## 감사 기준 (Rev. Bang 제시, 2026-09-10)

배포 시 목회자 사용자가 받아야 하는 답의 조건:

1. 처리된 자료에 근거할 것 — 웹·타 AI 자료의 무분별한 혼입 차단
2. 사용자의 교단 신학·개인 신학이 건강하게 적용될 것
3. 청크가 의미 집합적으로 완성된 문단 형태일 것
4. 사용자 주 언어(한국어)로 문법적·문학적으로 완결된 문장일 것
5. 일반 상식을 넘어 정확한 자료에 기반한 고도의 답일 것

## 요약

**5개 요구 중 감사 시점에 충족된 것은 "외부 호출의 물리적 차단" 하나뿐이었다.**
2026-09-10 우선순위 1·2를 수정해 1번이 논리적으로도 충족되기 시작했으나,
2·3·5번은 구조적 미구현 상태이며 4번은 근본 원인이 남아 있다.

| # | 요구 | 감사 시점 | 현재 (2026-09-10 수정 후) |
|---|---|---|---|
| 1 | 근거 기반 / 외부 혼입 차단 | 물리 O · 논리 X | **개선** — 지시문 강제 |
| 2 | 교단·개인 신학 반영 | 미구현 | 미구현 |
| 3 | 완결 문단 청크 | 미달 (문장 단위 + 200자 절단) | **부분 개선** — 절단 제거, 단위는 그대로 |
| 4 | 한국어 완결 문장 | 방어만 존재 | 부분 개선 — 근본 원인 잔존 |
| 5 | 정확한 자료 기반 | 부분 | 부분 |

---

## 1. 근거 기반 · 외부 혼입 차단

### 물리적 격리 — 충족 (감사 시점부터)

`core/`·`ui/` 전체에 외부 API 호출이 없다. `requests`/`httpx`/`openai`/`anthropic`
어느 것도 쓰이지 않으며, 유일한 네트워크 호출은 `core/embedder.py`의 `urllib`
→ 로컬 Ollama다. 벡터 저장소는 `localhost:6333`.

```bash
grep -rn "requests.get\|httpx\|urllib.request\|openai\|anthropic" core/ ui/ | grep -v "localhost\|127.0.0.1"
```

### 논리적 강제 — 감사 시점 부재, 2026-09-10 수정

감사 시점 `GenerationService._build_prompt()`가 만드는 프롬프트 전문:

```
문맥:
{llm_context_block}

질문:
{question}
```

"자료에만 근거하라"는 지시가 **없었다.** 모델 SYSTEM 프롬프트에도 없었다
(§6 참고). 따라서 70B 모델의 내장 지식(출처 불명 웹 학습 데이터)이 검색
근거와 무구분으로 섞였다 — 물리적 차단을 해 놓고도 실제로는 막지 못하던
지점이다.

**수정**: `core/generation.py::_GROUNDING_DIRECTIVE` 추가, 자료 블록과 질문
사이에 삽입(끝쪽 고정 위치 — 긴 문맥이 앞설 때 지시가 희석되는 것을 피함).
라벨 `문맥:` → `자료:`. 문맥이 없는 분기는 `_GROUNDING_DIRECTIVE_NO_CONTEXT`
축약본 사용.

### ClaimGuard의 실제 범위 (오해 주의)

`core/claim_guard.py`는 **사후 탐지만** 한다.

- 탐지 방식: `ABSOLUTE_SUPERLATIVE_TERMS` 26개 한국어 단어 문자열 매칭
- `generation.py`는 결과를 `GenerationResult`에 붙일 뿐 **답변을 수정하지 않는다**
- UI는 경고 배너만 표시 (`ui/pages/chat.py:524`)
- **"출처 없이 지어낸 진술" 자체는 탐지 대상이 아니다** — 절대 표현이 없으면 통과

---

## 2. 교단·개인 신학 반영 — 미구현

코드 전체에 교단/신학전통 설정이 없다.

```bash
grep -rn "교단\|denomination\|tradition\|confession" core/ ui/
# → core/tsu_builder.py:472 의 메타 필드 1개뿐. 검색·랭킹·생성 어디서도 읽지 않음.
```

유일한 신학 색채는 모델 SYSTEM 프롬프트 한 줄(`"복음주의 및 개혁주의 관점"`)이며,
세 가지 문제가 있다:

1. **버전관리 밖**이었다 — `~/.ollama/models/blobs/`에만 존재
   → 2026-09-10 `resources/models/Modelfile.theology-bot-v2`로 원문 그대로 기록(변경 아님)
2. **사용자별 변경 불가** — 모델에 구워져 있음
3. **코퍼스와 불일치** — 실제 수집물은 Fuller/Dagg/Hiscox/1689 런던 침례교
   신앙고백 등 **침례교** 계열인데 SYSTEM은 "개혁주의" 일반

ADR-009(SIL Theology Engine)가 이 자리를 위한 설계지만 Status "Accepted(구조만)",
어휘 미확정, 미구현.

---

## 3. 청크 단위 — 두 경로 모두 미달

### 3-1. 개인 서재 경로 (질의응답)

`core/chunking_optimizer.py`는 **문자 수만** 본다(`chunk_size`/`chunk_overlap`).
의미 경계 판정기는 존재하나 **어떤 프로덕션 경로도 import하지 않는다**:

```bash
grep -rn "semantic_boundary_detector\|hierarchical_chunk_builder" --include='*.py' core ui scripts
# → tests/ 와 자기 자신 외에 호출자 없음 (dormant)
```

| 모듈 | 상태 |
|---|---|
| `core/semantic_boundary_detector.py` (492줄) | dormant, 미배선 |
| `core/hierarchical_chunk_builder.py` (227줄) | dormant, 미배선 |
| ADR-007 (D-5 Rebuild Gate) | **Proposed** — §1 판정 기준 미확정, 통과/실패 판정 자체가 불가 |
| ADR-008 (Semantic Chunking Production Path) | **Proposed** — 전환 미결정 |

→ **여기가 3번 요구의 진짜 병목.** Architecture Freeze Rule상 새 ADR 없이 진행 불가.

### 3-2. NAE 연구 코퍼스 — 문장 단위

TSU는 문단이 아니라 **문장** 단위다. Fuller Vol01 실측(`NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json`):

| 지표 | 값 |
|---|---|
| 레코드 수 | 3,643 |
| `source_text` 평균 | 204자 |
| 중앙값 | 173자 |
| 200자 미만 비율 | **59.4%** |
| `scriptures` 채워진 건 | **0건** |
| `review_status` | 3,643건 전부 `generated` (사람 검토 0) |
| `extraction_method` | 전부 `llm` |

실제 레코드(`TSU-0004128`): `source_text`는 OCR 잡음을 포함한 영어 한 문장
(`"Though the Gospel, strictly speaking-, is not a Law..."`).

재측정:
```bash
~/envs/dbma311/bin/python -c "
import json, statistics
d=json.load(open('NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json'))
L=[len(r['source_text']) for r in d]
print(len(d), statistics.mean(L), statistics.median(L), sum(1 for x in L if x<200)/len(L))"
```

### 3-3. 200자 절단 — 2026-09-10 수정됨

감사 시점 `bridge_query()`가 `RankedCandidate.content`에
`content_excerpt`(=`source_text[:200]`)를 넣었고, 그 값이
`ContextAssembler.assemble()`을 지나 `llm_context_block`이 되었다.
평균 204자 코퍼스에서 상한이 실제로 물려, **모델이 문장 중간에서 잘린 조각을
근거로 받았다.**

**수정**: 매핑 dict에 `source_text`(전문) 필드를 추가하고
`RankedCandidate.content`가 이를 사용. `Citation.content_excerpt` 200자는 유지.

> **ADR-024 판단 (재조사 불요)**: ADR-024는 **Approved**이고 §C 표에
> `content_excerpt = content[:200]`이 있다. 그러나 그 표가 정의하는 것은
> **Citation 필드**이며 `RankedCandidate.content`는 표에 없다. 둘을 같은
> 값으로 쓰던 것은 계약이 아니라 계약 밖 구현 편법이었다.
> → **Freeze Rule 위반 없음, Amendment 불요.**

---

## 4. 한국어 완결 문장

### 존재하는 방어 (양호)

`core/generation.py:74-95` — CJK/태국어 오염 문자 탐지 → 동일 프롬프트 재시도
2회 → 최종 `_sanitize_script_contamination()`. 2026-07-21 실측 근거가 코드
주석에 남아 있다(temperature 0.3/0.2/0.1/0.0 전 구간에서 오염 재현 — 온도
조정은 해결책이 아님).

### 남은 근본 문제

1. **최종 방어선이 오염 문자를 삭제한다** → 문장이 손상된 채 사용자에게 간다.
   "완성된 문장" 요구와 정면 충돌.
2. **언어 불일치**: 근거는 19세기 영어, 답변은 한국어. 모델이 매 답변마다
   번역+해석을 겸하는데 감사 시점 프롬프트에 그 지시가 없었다
   → 2026-09-10 `_GROUNDING_DIRECTIVE` §3으로 명시.
3. **TSU `claim` 필드는 LLM 생성 한국어 요약**이다. 근거로 노출하면
   "AI 생성물을 근거로 인용"하는 셈. 현재 검색은 `source_text`를 쓰므로
   당장 발생하지 않으나 **설계상 위험이 남아 있다** — 향후 `claim`을 검색
   대상에 넣자는 제안이 오면 이 항목을 먼저 볼 것.

---

## 5. 정확한 자료 기반 — 부분

### 구현되어 있는 것 (구조는 양호)

하이브리드 랭킹(`core/retrieval.py:1657`): `0.25×BM25 + 0.20×vector +
0.30×theological + …`. Citation/Evidence 계층(SPRINT17~19)도 실제로 동작한다.

### 결함 A — QueryParser가 영어 전용

| 항목 | 위치 | 문제 |
|---|---|---|
| `INTENT_PATTERNS` | `core/retrieval.py:321` | 영문 정규식 5종 |
| `THEME_KEYWORDS` | `core/retrieval.py:288` | 영어 어휘 14테마 |
| 폴백 intent 판정 | `core/retrieval.py:367` | `God\|Jesus\|Christ...` 영문 |
| 장절 파서 | `_extract_scripture_refs()` | 영문 책명 패턴 |
| 책명 사전 | `BOOK_ID_TO_NAMES` (`:202`) | 한글 일부 등록됨 |

→ 한국어 질의는 `intent="unknown"`, `themes=[]`로 떨어져 **가중치가 가장 큰
theological_score(0.30)가 제대로 붙지 않는다.**

### 결함 B — 문맥 블록에 서지 정보 없음

`core/retrieval.py:1843`이 만드는 블록은 `<context id="TSU-..." score="...">`
뿐이다. 저자·서명·페이지가 없어 **모델이 본문 안에서 "풀러는 …라고 말한다"
식으로 출처를 밝힐 수 없다.** (Citation 객체에는 있으나 LLM에는 안 간다.)

### 결함 C — 성경 연결 부재

Fuller Vol01 3,643건 중 `scriptures` 채워진 건 **0건**(§3-2).

---

## 6. 생성 모델

| 항목 | 값 |
|---|---|
| 태그 | `my-theology-bot-v2:latest` (`config.yaml: ollama.default_gen_model`) |
| 제원 | llama 아키텍처, 70.6B, Q4_K_M, 42GB |
| `num_ctx` | 32768 (모델 기본 context length는 131072) |
| `temperature` | 모델 기본 0.3 / 앱 전달값 `DEFAULT_TEMPERATURE` 0.2 |
| SYSTEM | 4줄 — 문체(경어체)·역사문법적 주해·출처 표기·설교 대지 구성 |
| 저장소 사본 | `resources/models/Modelfile.theology-bot-v2` (2026-09-10 신설) |

SYSTEM에 **근거 제한 지시가 없다**(§1). 교단 지정은 "복음주의 및 개혁주의"
한 구절뿐(§2).

---

## 7. 평가 계층

- `core/evaluation/rag_judge.py` — groundedness **단일 지표**(0~5). 교단 정합성·
  문장 완성도·인용 정확도 지표 없음.
- 연결 지점이 **설교 초안 경로뿐**이다. 일반 질의응답(chat/research) 답변은
  자동 채점되지 않는다.
- → §1 수정(지시문)의 **준수 여부는 아직 측정되지 않았다.**

---

## 8. 2026-09-10 수정 내역

커밋 `ae05415`, 브랜치 `claude/theological-pastoral-response-quality-89b049`.
상세: [Build Report](./DBMA-GROUNDING-EVIDENCE-FIX-BUILD-REPORT-001.md)

| 파일 | 변경 |
|---|---|
| `core/generation.py` | `_GROUNDING_DIRECTIVE` 2종 추가, `_build_prompt()` 삽입, `문맥:`→`자료:` |
| `NAE/retrieval_adapter.py` | `source_text` 전문 필드 추가, `RankedCandidate.content`가 사용 |
| `resources/models/Modelfile.theology-bot-v2` | 신규 — SYSTEM 원문 기록 |
| `tests/test_generation_conversation_history.py` | 전문 리터럴 비교 → 구조 검증 + `TestGroundingDirective` |
| `tests/test_nae_bridge_full_source_text.py` | 신규 4건 |

검증: `pytest -k "generation or nae_retrieval or bridge or citation or claim_guard"` → **184 passed**

---

## 9. 남은 작업 (우선순위)

| # | 항목 | 선행 조건 | 규모 |
|---|---|---|---|
| 3 | 한국어 QueryParser | 없음 — 즉시 착수 가능 | 중 |
| 4 | 청크 단위 정책 확정 | **ADR-007/008이 Proposed** — 새 ADR/Amendment 선행 필수 | 대 |
| 5 | 교단 프로파일 계층 | ADR-009 되살리기 + 교단 확정(침례교?) | 대 |
| — | 문맥 블록에 서지 정보 추가 (§5 결함 B) | ADR-024 §C 영향 확인 필요 | 소 |
| — | groundedness 판정을 chat 경로에 연결 | ADR-010 Phase 2 | 소~중 |

### 세션 운용 메모

- 항목당 한 세션으로 분리할 것 — 탐색 컨텍스트가 누적되면 토큰이 편집이
  아니라 재탐색에 소모된다. 본 문서가 그 재탐색을 대체한다.
- 설계·ADR 판단은 로컬 모델(C1)에 이양하지 말 것. §3-3의 ADR-024 범위 판단이
  전형인데, 틀려도 테스트는 통과하므로 오류가 드러나지 않는다.
  이양 적합 구간은 어휘 사전 작성·픽스처 생성·기계적 치환.
