# GS 운영 통합 ④ 계약 5항목 — HQ 결정 자료

- 작성: CUE · 2026-09-30
- 단계: HQ 결정 순서 ④ 생성·스트리밍 계약(결정 대기)
- 입력 문서(모두 `tmp/fu007-integration-trial`)
  - [④ 생성·스트리밍 계약 사실 브리프](NAE_GS_GENERATION_CONTRACT_BRIEF_HQ_REPORT.md)
  - [⑤ 구현 설계 자료](NAE_GS_IMPLEMENTATION_DESIGN_BRIEF_HQ_REPORT.md)
  - 위 두 문서의 호출자 수 정정 `517c0c2e`
  - ⑤ C1 검토에 대한 CUE 교차검증(정정 4건)
- 성격: **결정 자료이며 추천하지 않는다.** 이 문서에서 새로 추가하는 것은 항목 간 **의존 관계**와 **서로 맞지 않는 조합**(사실에 근거)뿐이다.
- 표기: [CONFIRMED] 코드·문서로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인
- **MUTATION: NONE**

## 0. 결정과 무관하게 고정된 사실

| 사실 | 근거 |
|---|---|
| 어떤 조합을 고르든 **새 ADR이 필요**하다 | ADR-036 B1 "두 경로 공존, 병합은 별도 ADR" / "P12 이후 새 ADR과 HQ 승인". P12 완료(`ec204adf`) [CONFIRMED] |
| GS 계약은 A(citation provenance) + B(원문 언어 citation span)까지다. C(semantic grounding)는 어느 조합으로도 해결되지 않는다 | ③ 결정, ADR-036 B6, C-03 [CONFIRMED] |
| 현재 앱은 검증 전에 답변을 표시한다(display-before-validation) | dev `ui/pages/chat.py` L569 `st.write_stream` → L570 `to_result()` [CONFIRMED] |
| 현재 검증은 모두 경고 전용이다(fail-open) | ClaimGuard, citation_verifier [CONFIRMED] |
| 릴리스 라인 dev에는 GS·근거 계층·인용 검증기가 없다. 앱 호출자는 dev 4곳 / main·b39572aa 5곳 | ① 결정 자료, `517c0c2e` 정정 [CONFIRMED] |
| GS 모듈은 `GenerationService`를 import할 수 없다. 연결은 운영 경로가 GS를 부르는 방향이다(B9 예외 이름 `core/grounded_synthesis*_executor.py`, 현재 없음) | ADR-036 B9 [CONFIRMED] |

## 1. 항목별 결정 자료

### ④-1 생성 방식

| 선택지 | 무엇이 바뀌나 | 이미 있는 것 | 없는 것 | 확인된 한계 |
|---|---|---|---|---|
| **A 구조화 생성** | 모델이 claim + 근거 ID(+ 원문 구간)를 형식에 맞춰 출력 | ID를 붙이는 프롬프트와 출력 형식이 **데모에만** 있음(`scripts/grounded_synthesis_integration_demo.py` L90·L100). P9 실모델 3건에서 ID 복사를 관찰 | core 파서. 데모 파서는 첫 줄 1개만 claim으로 만든다(L153). 운영 `_build_prompt`와 GS `prompt_text`에 근거 ID가 없다 | 실모델 표본 3건뿐 |
| **B 생성 후 추출** | 현행 자유 서술을 유지하고 두 번째 단계에서 claim·ID를 추출 | `ClaimExtractor` Protocol(`grounded_claims.py` L47~), Stub 구현 | LLM 추출기. B9상 GS 모듈 안에 둘 수 없다 | 답변에는 ID가 없고 `출처: 제목 — 저자, p.N` 라벨만 있다(`retrieval.py` L2241). 같은 라벨의 근거가 여러 개면 ID가 하나로 정해지지 않는다 [INFERRED] |
| **C 혼합** | A·B를 조합 | — | A·B에 필요한 것의 합 | 기존 구현 없음 |

### ④-2 스트리밍과 차단

| 선택지 | 표시 순서 | 필요 변경 | 확인된 사실 |
|---|---|---|---|
| **S-A 비스트리밍** | 생성 → 검증 → 표시 | UI 호출자를 `generate()`로 전환 | `generate()`가 이미 검증 결과를 담은 결과를 반환한다(b39572aa L600~). P0-5 생성 시간은 32~276초 |
| **S-B 현행** | 스트림 → 표시 → 검증 | 없음 | display-before-validation 유지 |
| **S-C 버퍼** | 스트림 → 버퍼 → 검증 → 표시 | UI가 `st.write_stream` 대신 스트림을 소비한 뒤 표시 | 버퍼는 `GenerationStream._answer_parts`에 이미 있다(dev L434·L460) |

차단 정책은 S-A·S-C에서만 의미가 있다.

| 정책 | 동작 | 사실 |
|---|---|---|
| 경고만 | 현행과 같은 fail-open | — |
| 부분 차단 | 확인되지 않은 claim을 본문에서 제외 | GS `assemble_grounded_answer`는 이미 `valid` claim만 조립한다(`grounded_answer.py` L111~L124) |
| 전면 유보 | 확인된 claim이 0개면 고정 문구 | `grounded_answer.py` L89 (B5) |

### ④-3 원문 인용 구간의 저장 위치

| 선택지 | 내용 | ADR 영향 | 확인된 사실 |
|---|---|---|---|
| **3-a** | B8 `Claim`에 원문 구간 필드 추가 | B8 정본 변경. 새 ADR에서 다룰지 ADR-036 Amendment로 할지 [UNKNOWN](Freeze Rule에 규정 없음) | 현재 구간을 저장하는 자리가 어디에도 없다(`Claim` L37~L43, `CitationCheckResult`는 bool만) |
| **3-b** | GS 모듈은 그대로 두고, 오케스트레이터가 구간마다 검증용 Claim(text = 원문 구간)을 만들어 기존 검사에 넣는다 | B8 무변경 | `Claim.text`가 "주장"과 "구간" 두 뜻으로 쓰이게 된다(설계 부채) |
| **3-c** | 구간을 저장하지 않음 | 없음 | 한국어 답변은 `claim.text`(한국어)를 영어 `Evidence.text`에서 정확 일치로 찾게 되어 **B 검사가 항상 실패한다**(`grounded_citation.py` L173, L110~L119) |

### ④-4 새 ADR의 범위

| 선택지 | dev 기준 포함 호출자 | 확인된 사실 |
|---|---|---|
| **채팅만** | `chat.py` 2곳 | 가장 좁은 범위 |
| **앱 호출자 전부** | + `passage_commentary_panel.py` L94, `_passage_commentary_tab.py` L119 (dev 4곳) | 착지 후에는 공개 자료 답변 `nae_public_section.py` L147이 더해진다(main·b39572aa 5곳) |
| **공개 자료 답변(ADR-037) 포함 여부** | — | ADR-037은 "기존 근거 강제 지시문 재사용"을 계약으로 한다. 이 경로(`NAE/public_answer.py`)는 dev에 아직 없다 |

범위와 관계없이 걸리는 사실: 운영 생성 경로의 교단 지시문(`_DENOMINATION_DIRECTIVE`)은 **ADR-009 Amendment A(Proposed)**에 근거한다. 생성 계약이 바뀌면 교단 지시문을 어디에 둘지도 새 ADR이 정해야 한다.

### ④-5 사용자 노출 문구

| 내부 상태 | 실제 의미(코드) | ③이 금지한 표현 | 기존 계약 |
|---|---|---|---|
| `GroundedAnswer.status == "grounded"` | `valid` claim이 1개 이상(ID 소속만). span·출처 검사 결과는 반영하지 않는다(`grounded_answer.py` L111~L124) | "근거로 확인됨", "검증된 답변", "claim semantically grounded" | 사용자 의미를 정한 계약은 없다 [CONFIRMED] |
| `span_found_in_text == False` | 원문 구간을 정확 일치로 찾지 못함. 공백·OCR·쪽 머리글 때문에 실제로 있는데 없다고 나오는 경우 포함 | — | 없음 |
| `insufficient_evidence` | 근거 0건이거나 valid claim 0개 | — | B5 고정 문구 |
| (현행) citation_verifier 경고 | 숫자·라틴 단어 휴리스틱. main·b39572aa에서만 표시(dev에는 없음) | — | FU-003 |

## 2. 항목 간 의존 관계 [CONFIRMED / INFERRED]

```text
④-1 생성 방식 ──┬──► ④-2 스트리밍 (A는 구조화 출력이라 S-B 그대로면 표기가 화면에 노출)
                └──► ④-3 구간 저장 (B는 한국어 claim에서 원문 구간을 결정적으로 찾을 수 없음)
④-3 구간 저장 ─────► 새 ADR 경로 (3-a는 B8 변경)
④-2 스트리밍 ─────► ④-5 노출 문구 (무엇을 언제 보여 주는지가 정해져야 문구를 정할 수 있음)
④-4 범위 ─────────► Phase 0 착지 (공개 자료 답변을 포함하면 ADR-037 경로를 먼저 dev에 들여와야 함)
```

## 3. 서로 맞지 않는 조합 (사실 근거)

| 조합 | 문제 | 근거 |
|---|---|---|
| ④-1 A + ④-2 S-B | 구조화 출력(claim·ID 표기)이 가공 전에 그대로 표시된다 | `st.write_stream`이 원문 토큰을 표시(dev L569) [INFERRED] |
| ④-3 3-c + ③ 계약 B 유지 | 제품 기본 경우(영어 근거 → 한국어 답변)에 B가 항상 실패해, B 계약이 실효를 잃는다 | ③ 보고서 3.1·4절 |
| ④-1 B + ④-3 3-a/3-b | 원문 구간을 추출기가 만들어야 하는데, 한국어 claim에서 영어 구간을 찾는 일은 ③이 제외한 의미 대응이다 | ④ 브리프 C7 [INFERRED] |
| ④-2 S-B + 차단 정책(부분 차단·전면 유보) | 이미 표시된 뒤라 차단할 수 없다 | C2 [CONFIRMED] |
| ④-5에서 "grounded"를 "근거 확인됨"으로 표시 | ③ 명칭 규칙 위반. 실제 의미는 ID 소속뿐이다 | `grounded_answer.py` L111~L124 |

## 4. 어떤 조합도 해결하지 않는 것

- P0-5의 주 실패 유형: 근거 ID는 맞지만 내용이 근거 밖(D1·C1·C2). C(semantic grounding)의 영역이다.
- 근거 없는 교단 틀(A3·B1·G3), 질문 불일치(E3)
- 이들을 GS에 넣으려면 B6·C-03 재검토와 별도 ADR이 필요하다(③).

## 5. 결정 후 다음 단계

1. HQ가 ④-1~④-5를 결정한다(2절의 의존 순서를 참고).
2. FU-007 번역 방식 결정(Phase 0의 전제)
3. 새 ADR 작성 지시 → C1 Review → HQ 승인
4. 그 뒤에야 구현 Task Order(⑤ 단계 2~)

## 6. MUTATION

- 코드·ADR·prompt 변경 없음. 이 문서의 커밋·푸시만 수행한다.
