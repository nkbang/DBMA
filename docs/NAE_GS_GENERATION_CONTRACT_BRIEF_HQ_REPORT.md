# GS 생성·스트리밍 계약 — ④ 사실 기반 설계 브리프

> **정정(2026-09-30, ⑤ C1 검토 교차검증)**: 이 문서의 "앱 호출자 5곳"은 **main·b39572aa 기준**이다. 릴리스 라인 **dev(`195189b8`)에서는 4곳**이다(chat.py 2곳, `passage_commentary_panel.py` L94, `_passage_commentary_tab.py` L119). 공개 자료 답변(ADR-037)의 `NAE/public_answer.py`와 `nae_public_section.py`의 `generate_stream` 호출은 dev에 없고, 착지(Phase 0) 뒤에 들어온다.

- 작성: CUE · 2026-09-30
- 단계: HQ 결정 순서 ④(생성·스트리밍 계약)
  - 완료: ① 릴리스 라인 = dev, ② ADR-036 = GS 경계 / ADR-037 = 공개 자료, ③ GS 계약 = A(citation provenance) + B(citation span)
- 성격: **구현 명령이 아니다.** HQ가 다음 구현 계약을 고를 수 있도록 사실을 정리한 문서다. 옵션을 추천하지 않는다.
- 방법: 읽기 전용(`git show <ref>:<path>`, grep). 실행·테스트·수정 없음.
- 표기: [CONFIRMED] 코드·문서로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인

## 0. 기준 ref와 세 가지 구분

| ref | SHA | 쓰임 |
|---|---|---|
| `origin/dev/dbma-engine` | `195189b8` | 릴리스 라인(①). 운영 경로 사실 C1~C3·C6 |
| `tmp/fu007-combined-translation` | `b39572aa` | P0-5 실행 코드. GS가 있는 병합본. C1~C8 |
| `tmp/fu007-integration-trial` | `5d48abee` | 이 문서를 커밋하는 결과 브랜치(코드는 main `d1c06d25` 판) |
| `origin/claude/p4-final-validation-guide-b3af47` | — | ADR-036(GS 경계) 원문 |

**세 가지 구분**(③ 결정):
- **A. Citation provenance**: 이 citation이 실제 evidence를 가리키는가 → GS 계약에 포함
- **B. Citation span**: 그 원문 구간이 evidence에 실제로 있는가 → GS 계약에 포함
- **C. Semantic grounding**: 그 evidence가 claim을 실제로 지지하는가 → **GS 계약 밖. 이 문서 전체에서 해결되지 않은 별도 문제로 유지한다**

## C1. 실제 호출 경로 — CONFIRMED

`ui/pages/chat.py`의 `_handle_user_message()`(dev L496~ / b39572aa L498~):

| 단계 | dev 행 | b39572aa 행 |
|---|---|---|
| `processor.process(question, …)` | L525 | L527 |
| 근거 0건 게이트 `if not response.top_k_results` → 유보 | L544 | L546 |
| `generator.generate_stream(response, …)` | L564 | L566 |
| `st.write_stream(stream)` → `GenerationStream.__iter__()`가 청크마다 `yield` | L569 (`generation.py` L442~, yield L461) | L571 (`generation.py` L461~, yield L480) |
| `stream.to_result()` | L570 (`generation.py` L472~) | L572 (`generation.py` L491~) |
| ClaimGuard 경고 표시 | L571~L578 | L573~L580 |
| 인용 검증 경고(`issue_messages`) | **없음** | L581 |
| 대화 기록에 `result.answer` 저장 | L591 | L596 |

- 같은 모양의 다른 호출자: `generate_answer()` L479/L481(스트림을 소비만 하고 `to_result`), 공개 자료 패널 `nae_public_section.py` L147, 본문 해설 `passage_commentary_panel.py` L94·`_passage_commentary_tab.py` L119. 앱 호출자는 모두 `generate_stream()`을 쓴다 — main·b39572aa 5곳, dev 4곳(dev에는 `nae_public_section.py`의 호출이 없음).
- `generate()`(비스트리밍)는 앱에서 호출되지 않는다(평가 스크립트·테스트·`core/passage_commentary.py` L344 비스트리밍 경로에서만).

## C2. 검증 시점 — CONFIRMED: **display-before-validation**

- `st.write_stream(stream)`(dev L569 / b39572aa L571)이 토큰을 도착하는 대로 화면에 표시한다.
- ClaimGuard(`to_result` 안, dev `generation.py` L497 / b39572aa L516)와 인용 검사(b39572aa L526)는 **표시가 끝난 뒤** 실행된다.
- 검증 결과는 답변을 바꾸지 않는다. 경고로만 표시된다(fail-open).
- 표시 전에 적용되는 것은 두 가지뿐이다.
  - 근거 0건 게이트(dev L544 / b39572aa L546)
  - 청크 단위 오염 문자 표식(`__iter__` 안, dev L442~ / b39572aa L472~L477)

## C3. GenerationResult 계약 — CONFIRMED

| 필드 | dev (`generation.py` L511~L520) | b39572aa (L533~L544) |
|---|---|---|
| question, answer, gen_model, temperature, context_used, error | 있음 | 있음 |
| `citations: list[Citation]` | 있음 | 있음 |
| `claim_guard_result` | 있음 | 있음 |
| `citation_check` (citation_verifier 결과) | **없음** | 있음 |
| claims / claim별 evidence ID / citation span / validation status | **없음** | **없음** |

- `Citation`(`core/retrieval.py` L2261~L2276)은 **검색된 근거 단위**의 서지다: `citation_id`, `tsu_id`, `source_title`, `source_author`, `document_id`, `content_excerpt`, 점수.
- 답변의 어느 문장이 어느 근거를 인용했는지는 담지 않는다.

## C4. Claim → Evidence → Span 관계 — CONFIRMED

| 요소 | 현재 구조 | 위치 |
|---|---|---|
| Claim | `claim_id`, `text`, `evidence_ids`, `valid`. **인용 구간 필드 없음** | `grounded_claims.py` L37~L43, ADR-036 B8 |
| Evidence | `evidence_id`, `text`, `source_file`, `document_id`, `document_title`, `chunk_id`, provenance | `evidence_model.py` L52~L76 |
| provenance 판정 | `has_provenance = bool(source_file or document_id or chunk_id)` | `evidence_model.py` `has_provenance` |
| span 결과 | `CitationCheckResult.span_found_in_text: bool`. **구간 문자열은 저장하지 않음** | `grounded_citation.py` L59~L68 |

- [CONFIRMED] **원문 언어 인용 구간을 독립 필드로 보존할 자리가 현재 구조에 없다.** Claim, CitationCheckResult, GenerationResult 모두 없다.
- 넣으려면 B8(ADR-036이 "정본 시그니처 — 각 Phase가 정확히 이 형태로 구현"으로 고정한 구조)을 바꿔야 한다.

## C5. 교차언어 실패 조건 — CONFIRMED (어떤 필드가 어떤 값으로 비교되는가)

`check_citation_provenance()` → `_check_span_in_text(claim.text, ev.text)`(`grounded_citation.py` L173, 비교는 L110~L119의 `evidence_text.find(claim_text) >= 0`, 대소문자 구분, 5자 미만이면 실패):

| 비교 대상 | 값의 출처 |
|---|---|
| `claim.text` | 현재 유일한 실제 추출기인 데모 `parse_llm_claims()`가 **LLM 출력 전체의 첫 줄**을 claim 본문으로 만든다(`scripts/grounded_synthesis_integration_demo.py` L153 `llm_output.strip().split("\n")[0]`). 한국어 답변이면 한국어 문장이고, 근거 ID 표기가 같은 줄에 섞일 수 있다 |
| `ev.text` | `RankedCandidateEvidenceAdapter`가 `RankedCandidate.content`를 그대로 옮긴다(`tsu_adapter.py` L313, L339). 현재 코퍼스에서는 영어 TSU 본문이다 |

→ **"한국어 claim 문장 전체가 영어 근거 본문 안에 글자 그대로 있는가"**를 검사하는 셈이다. 그래서 항상 거짓이다. 별도의 원문 구간은 어디에도 보존되지 않는다(C4).

[CONFIRMED] 추가 사실: 데모 추출기는 답변당 claim을 **최대 1개**(첫 줄)만 만든다. 여러 문장으로 된 답변의 나머지 문장은 claim이 되지 않는다.

## C6. 스트리밍 계약 — CONFIRMED (현재 = B)

| 방식 | 흐름 | 현재 구조와의 관계 | 변경 지점 |
|---|---|---|---|
| A | generate → validate → display | `generate()`(b39572aa L600~)가 이미 "생성 후 검증 결과까지 담은 `GenerationResult`"를 돌려준다. 앱은 쓰지 않는다 | UI 호출자(dev 4곳 / main 5곳)를 `generate()`로 전환. 스트리밍 표시 소멸. 재시도 로직(`generate()`에만 있음)이 함께 적용됨 |
| **B (현재)** | generate_stream → display → validate | chat.py L564~L578(dev) / L566~L581(b39572aa) | 없음(현행) |
| C | generate_stream → buffer → validate → final display | 버퍼 자체는 이미 있다: `GenerationStream._answer_parts`에 청크를 모으고(dev L434·L460, b39572aa L453·L479) `to_result()`가 합친다 | UI가 `st.write_stream(stream)` 대신 스트림을 먼저 소비하고 `to_result()` 뒤에 표시. 진행 표시 방식은 별도 설계 |

[CONFIRMED] 어느 방식이든 현재 검증(ClaimGuard, citation_verifier)은 경고 전용이다. **검증 결과로 표시를 막는 코드는 없다.** A·C는 "검증 뒤 표시" 순서만 만들며, 차단 여부는 별도 계약이다.

## C7. 생성 방식 비교 — CONFIRMED (현재 코드에서 필요한 변경 지점)

| 항목 | A. Structured | B. Post-extraction | C. Hybrid |
|---|---|---|---|
| 생성 시 claim·evidence ID 생성 | 필요. 현재 운영 프롬프트(`_build_prompt` b39572aa L554~, dev L530~)와 GS `prompt_text`(`grounded_synthesis_input.py` L60~L61)에는 **근거 ID가 없다**. ID를 붙이는 프롬프트는 데모에만 있다(L90 `[evidence_id: …]`, L100 출력 형식) | 불필요(현행 자유 서술 유지) | 둘 중 한쪽 또는 둘 다를 조합한다. 기존 코드에는 해당 구현이 없다 |
| 사후 추출 | 파서 필요. 데모 `parse_llm_claims`(첫 줄 1개만)뿐 | 추출기 필요. core에는 `ClaimExtractor` Protocol(`grounded_claims.py` L47~)과 Stub만 있다. LLM 추출기는 **B9상 GS 모듈 안에 둘 수 없다**(`ollama` import 금지, 예외는 `core/grounded_synthesis*_executor.py`) | 〃 |
| 근거 ID 확보 | 모델이 프롬프트의 ID를 복사한다(P9 실모델 3건에서 관찰) | 답변에는 ID가 없고 라벨만 있다. 라벨은 `출처: {제목 — 저자, p.N, 문단 M}`(`retrieval.py` L2241). [INFERRED] 같은 라벨의 근거가 여러 개면(P0-5에서 흔함) 라벨만으로 ID가 하나로 정해지지 않는다 | — |
| 원문 인용 구간(B) | 모델이 원문 구간을 함께 출력하게 할 수 있다. 저장하려면 B8 변경이 필요하다 | [INFERRED] 한국어 claim에서 영어 원문 구간을 결정적으로 찾을 방법은 없다(찾는 일 자체가 ③이 제외한 의미 대응) | — |
| 스트리밍 | 구조화 출력을 그대로 스트리밍하면 표기가 화면에 노출된다 → 사실상 C6-C(버퍼) | 현행 스트리밍 유지 가능 | 설계에 따름 |
| 검증 전 표시 | 버퍼 시 없음 | 스트리밍 유지 시 **있음** | 설계에 따름 |
| 변경 범위 | `_build_prompt` 또는 `prompt_text`, core 파서, B8(구간), UI 호출자(dev 4곳 / main 5곳), `GenerationResult` | 추출기(GS 밖), 라벨→ID 대응, `GenerationResult`, 경고 표시 | A·B 변경의 합 |

## C8. P0-5 실패 커버리지 (현재 GS, 설계 변경 전) — CONFIRMED

| P0-5 문제 | 현재 GS가 검출 가능? | 현재 GS가 차단 가능? | 이유 |
|---|---|---|---|
| 근거 밖 주장 | 부분(근거 ID가 없거나 집합 밖인 claim만) | 부분 — 그런 claim은 `valid=False`가 되어 본문 조립에서 빠진다(`grounded_answer.py` L111~L124) | ID를 단 근거 밖 주장은 통과한다(C) |
| 교단 틀 문장 | 위와 같음(ID 없을 때만) | 위와 같음 | 추출기가 그 문장에 ID를 붙이면 통과한다 |
| 출처 오귀속 | **불가** | 불가 | `id_exists`는 집합 소속만 본다. 한국어 claim은 span 검사가 항상 실패해 구별력이 없다(C5) |
| 근거 없는 직접 인용 | 원문 언어 인용이 claim 본문 전체일 때만 | 불가 — span 결과가 상태(`grounded`)나 본문 조립에 쓰이지 않는다(`grounded_answer.py`는 citation 검사를 import하지 않음, L24~L31) | 검출 결과를 강제하는 연결이 없다 |
| 질문 불일치 | 불가 | 불가 | 질문–답 대응 검사 없음 |
| ID는 맞지만 evidence가 claim을 지지하지 않음 | **불가** | **불가** | C(semantic grounding). ③ 범위 밖 |

[CONFIRMED] `citation valid`(ID 소속)와 `claim grounded`(의미 지지)는 코드에서도 다른 것이다. `GroundedAnswer.status == "grounded"`는 앞의 것만 뜻한다(C-03).

## C9. ADR 경계 — CONFIRMED: **새 architecture decision 필요**

- ADR-036 B1 원문(p4 브랜치 L42~L47)
  - 제목: "두 경로 공존, **병합은 별도 ADR**"
  - 본문: "P12까지 `ui/`나 운영 생성 경로에 연결하지 않는다 … 운영 경로 교체가 필요해지면 **P12 이후 새 ADR과 HQ 승인**을 받는다."
- GS 여정의 P12는 완료됐다: `ec204adf`(09-28) Phase 12 Final Implementation Report, `76a5a451`(09-29) "GS-FINAL-RPV [✓ HQ] 최종 승인 — 여정 종결".
- 따라서 **GS를 `GenerationService` 운영 경로에 연결하는 것은 ADR-036의 수정이 아니라 B1이 명시한 "별도 ADR" 사항이다.**
- B9(L133~L138): GS 모듈(P4~P8)은 `GenerationService`를 import할 수 없다 → 연결 방향은 운영 경로(또는 B9 예외인 executor)가 GS를 호출하는 쪽이어야 한다.
- B6: ③ 계약(A+B)과 충돌 없음. C(의미 지지)를 자동 검증으로 넣으면 B6·C-03과 맞닿는다.
- B8: 원문 인용 구간 필드를 추가하면 정본 시그니처 변경이다. 새 ADR 안에서 다룰지, ADR-036 Amendment로 할지는 **[UNKNOWN]**(Freeze Rule에 규정 없음, ② 보고서 9절).
- 관련 운영 계약: 교단 지시문은 ADR-009 Amendment A(**Proposed**)에 근거하고, 공개 자료 답변(ADR-037)도 `generate_stream` 호출자다(`nae_public_section.py` L147). 새 ADR의 적용 범위에 들어갈지 결정해야 한다.

## C10. 독립 재현성 — CONFIRMED

- 위 모든 사실에 파일·행·ref를 적었다. 재현 명령: `git show <ref>:<path> | grep -n <symbol>`.
  - zsh에서는 `"${ref}:path"`로 감싸야 한다. `$r:u`는 대문자 수식자로 해석된다.
- 불변 조건:

```text
CODE MUTATION: NONE
ADR MUTATION: NONE
PROMPT MUTATION: NONE
TEST/PRODUCTION BEHAVIOR CHANGE: NONE
```

## 완료 판정

```text
STATUS: COMPLETE

C1  Production generation path        CONFIRMED
C2  Validation/display timing         CONFIRMED  (display-before-validation)
C3  GenerationResult contract         CONFIRMED  (claim·span·status 필드 없음)
C4  Claim/Evidence/Span contract      CONFIRMED  (원문 구간 보존 자리 없음)
C5  Cross-language limitation         CONFIRMED  (Korean claim.text ⟷ English Evidence.text 정확 일치)
C6  Streaming contract                CONFIRMED  (현재 = B, 버퍼는 내부에 존재)
C7  A/B/C design comparison           CONFIRMED  (변경 지점 제시, 일부 [INFERRED] 명시)
C8  P0-5 coverage matrix              CONFIRMED
C9  ADR boundary                      CONFIRMED  (B1: 병합은 별도 ADR, P12 완료)
C10 Independent reproducibility       CONFIRMED
```

**[INFERRED]/[UNKNOWN]으로 남긴 부분** (빈칸을 추론으로 메우지 않았다)
- 생성 후 추출 방식에서 라벨→근거 ID 대응의 모호성(C7) — P0-5 표본에서 관찰된 라벨 중복에 근거한 추론
- 한국어 claim에서 원문 구간을 결정적으로 얻을 수 없다는 판단(C7) — ③의 범위 정의에 근거한 추론
- B8 변경을 새 ADR과 Amendment 중 어디서 다룰지(C9)

## HQ가 결정할 계약 항목 (추천 없음)

1. 생성 방식: A(구조화) / B(생성 후 추출) / C(혼합)
2. 스트리밍: A(비스트리밍) / B(현행) / C(버퍼 후 표시). 검증 결과로 **차단**할지, 경고만 할지
3. 원문 인용 구간 필드(B8 변경)의 도입 여부와 ADR 경로
4. 새 ADR(B1이 요구)의 범위: 채팅만 / 앱 호출자 전부(dev 4곳, 착지 후 공개 자료 답변 포함 시 5곳) / 공개 자료 답변(ADR-037) 포함 여부
5. "grounded" 라벨의 사용자 노출 방식(③ 명칭 규칙)

C(semantic grounding)는 이 결정들과 무관하게 **미해결 별도 문제**로 남는다.
