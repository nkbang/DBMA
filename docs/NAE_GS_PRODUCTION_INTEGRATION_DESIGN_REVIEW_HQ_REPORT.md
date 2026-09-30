# GS Production Integration — Design Review HQ 보고서

- 작성: CUE · 2026-09-30
- 단계: P0-5 이후 첫 여정. GS Feasibility → **Design Review(이 문서)** → HQ 결정
- 기준 코드: `tmp/fu007-combined-translation` `b39572aa` (P0-5에서 실행한 코드)
- 선행 문서: [P0-5 HQ 보고서](NAE_EUAT_001_FU007_P0_5_HQ_REPORT.md)
- 입력:
  - C1 feasibility trace
  - C1 v2 independent verification
  - CUE 읽기 전용 교차검증(grep, sed, git show, cat-file, merge-base)
- **MUTATION: NONE** — 코드·git 변경, 실행 모두 없음. 이 문서 커밋만 한다.

> 이 문서는 구현 승인이 아니다. 구현 여부와 architecture 선택은 HQ가 결정한다.

## 1. 결론

**STATUS: YELLOW**

- 연결에 필요한 구조는 코드에 있다: 입력 변환 사슬, B4의 근거 ID 결합, B6의 결정적 검사.
- 그러나 다섯 가지 계약 결정이 HQ 승인을 필요로 한다: 착지 라인, 생성 계약, 교차언어 검증, 스트리밍, ADR 번호·경계.
- 교차언어 grounding은 "결정적 인용 구간 확인"까지만 해결할 수 있다. 의미 지지 판정은 B6 설계상 자동 흐름 밖에 있다.

**핵심 한계**: P0-5의 주된 실패 유형은 "근거 ID는 맞게 달았는데 내용은 근거에 없다"(D1·C1·C2)이다. GS를 연결해도 이 유형은 결정적 검사로 탐지되지 않는다.

## 2. 현행 production 경로 (OBSERVED)

| 항목 | 사실 | 위치 |
|---|---|---|
| 앱 호출자 | 5곳 모두 `generate_stream()` | `ui/pages/chat.py` L481·L566, `ui/components/nae_public_section.py` L147, `ui/components/passage_commentary_panel.py` L94, `ui/pages/_passage_commentary_tab.py` L119 |
| `generate()` | 앱에서 호출되지 않음(비스트리밍·테스트 경로, 평가 스크립트) | `core/passage_commentary.py` L344, `scripts/p0_5_run_all.py` L94 등 |
| 프롬프트 | 이전 대화 → 자료 → `_GROUNDING_DIRECTIVE` → `_DENOMINATION_DIRECTIVE` → 질문 | `core/generation.py` `_build_prompt` L554~, 지시문 L315·L355 |
| 표시 시점 | 토큰을 청크마다 yield해 즉시 표시. 검증은 그 뒤 | `GenerationStream.__iter__` L461~, `chat.py` L566 `st.write_stream` → L567 `to_result()` |
| 사후 검사 | ClaimGuard + 인용 검증기. 경고 전용이며 fail-open | `to_result` L491~, `_run_citation_check` |
| ClaimGuard 범위 | 절대·최상급 표현 사전 탐지 + 같은 태그의 경쟁 후보 확인 | `core/claim_guard.py` L22~, L69·L81·L100~ |
| 근거 부족 게이트 | **근거 0건일 때만** 유보 | `chat.py` L473·L546 |

P0-5의 일반화: P0-5는 `generate()`로 실행했다. 앱은 `generate_stream()`을 쓰지만 프롬프트(`_build_prompt`)를 공유한다. 따라서 근거 밖 진술 유형은 사용자 경로에도 해당할 것으로 **추론**한다. 재시도와 오염 처리 차이의 영향은 미확인이다.

## 3. GS 현재 구조 (OBSERVED)

| 모듈 | 역할 | 강제 수준 |
|---|---|---|
| `grounded_synthesis_input.build_synthesis_input` L46 | 근거 선택(라운드로빈), `prompt_text` 구성 | `prompt_text`에 **근거 ID 없음**(`[출처: …]`만) |
| `grounded_claims.bind_claims` L57 | claim과 근거 ID 결합 | 인용한 ID가 선택된 집합에 모두 속하면 valid. **내용 대조 없음** |
| `grounded_answer.assemble_grounded_answer` L46 | 상태 판정과 본문 조립 | valid claim만 본문에 넣음. 유보는 고정 문구(L89) |
| `grounded_citation.check_citation_provenance` L122 | 출처 검사 | ID 존재, **claim 전문의 대소문자 구분 정확 부분일치**(L110-L119), 출처 메타데이터 |
| claim 추출기 | core에는 `StubClaimExtractor`뿐 | 실제 LLM 계약(`[evidence_id: …]` 프롬프트와 `parse_llm_claims`)은 `scripts/grounded_synthesis_integration_demo.py`에만 있음(P9 실모델 실행 3건) |

- 입력 변환 사슬: `top_k_results` → `assemble_evidence_pool_with_manifest` → `build_evidence_pool_from_ranked_candidates` → `RankedCandidateEvidenceAdapter` → `EvidencePool` + `AssemblyManifest` → `build_synthesis_input`. 모두 core에 있다. 제품 호출은 0이다.
- 앱 import: GS 4개 모듈 모두 0(테스트 6개와 데모 1개에서만 사용).

## 4. 계보 (OBSERVED)

| 파일 묶음 | main | peb | dev/dbma-engine | b39572aa |
|---|---|---|---|---|
| GS 4개 모듈 | 있음 | 있음 | **없음** | 있음 |
| 근거 계층(evidence_pool / assembly / model / adapters) | 있음 | 있음 | **없음** | 있음 |
| `citation_verifier.py` | 있음 | 없음 | 없음 | 있음 |

merge-base는 main↔dev, main↔peb 모두 `39026424`이다.

## 5. 설계 결정 항목

### D1. 착지 라인
- L1: main을 기준으로 착지. 필요한 것이 이미 있다. main이 릴리스 라인이 되어야 한다(방안 I).
- L2: dev를 기준으로 착지. GS·근거 계층·인용 검증기를 모두 들여와야 한다(사실상 main→dev, 방안 II).
- L3: FU-007 통합본(b39572aa 계열)을 경유. 필요한 모든 것과 결합안 번역이 있지만 임시 상태다. L1/L2 결정 뒤 반영한다.
- FU-007 릴리스 라인 결정과 **같은 결정**이다.

### D2. 생성 계약
- 현재: 자유 서술 + "(출처: …)" 표기. core에는 근거 ID를 요구하는 프롬프트와 파서가 없다.
- Option A(구조화 생성): 데모의 ID 프롬프트와 파서를 core로 옮기고 `_build_prompt`를 교체한다.
  - 근거: P9 실모델 3건에서 모델이 ID를 달아 출력했다.
  - 대가: 문단형 출력(D5)과 토큰 스트리밍(D4)에 영향.
- Option B(생성 후 추출): 현 답변을 유지하고 두 번째 LLM 호출로 claim과 ID를 추출한다.
  - 위험: 추출 단계가 ID를 지어낼 수 있다. 지연이 늘어난다(P0-5 생성 중앙값 약 80초, 추출 지연은 미확인).
  - 이미 표시된 답변은 검증과 무관하게 남는다.
- 공통: 어느 쪽이든 **core에 없는 제품 코드**(ID 프롬프트, 파서)가 필요하다.

### D3. 교차언어 grounding
- 현재 검사는 영어 근거와 한국어 claim에서 **항상 불일치**다.
- GS 경계 ADR의 B6은 결정적 검사에 "인용 구간이 Evidence.text에 실제로 존재"를 포함한다. 의미 지지 판정은 "사람 또는 CUE 표본 검토"로 분리한다. HQ C-03 결정이 이 분리를 유지한다.

| 모델 | 내용 | ADR | 보장 범위 |
|---|---|---|---|
| A | claim마다 원문 언어 인용 구간을 따로 출력하고 정확 일치로 검증 | B6 범위 안 | 인용 존재 + 인용 구간 존재. 한국어 claim의 번역·의역 충실도는 미보장. Claim에 span 필드가 필요하며, B8 변경 여부는 미확인 |
| B | 구조화 출력만 | — | 의미 관계 검증 근거 없음 |
| C | 자동 의미·교차언어 검증기 | **B6·C-03 변경 → Amendment 필요** | 추가 로컬 모델 의존 |
| D | A + 표본 기반 의미 검토 | B6 원안과 일치 | 의미 판정은 제품 흐름 밖 |

세 층 구분:
- citation exists: A에서 결정적으로 보장
- citation supports claim: 인용 구간 존재까지만 결정적
- claim is grounded: 자동으로는 보장하지 않음(B6 설계 의도)

### D4. 스트리밍
- 현재: 검증 전 텍스트가 화면에 먼저 노출된다(post-generation 검증, pre-display 제약 없음).
- 선택지:
  - A. 전체 버퍼 후 검증된 결과만 표시: 강제력 최대, 대기 김(P0-5 생성 32~276초)
  - B. 표시 후 경고: 현행 연장, 막지 못함
  - C. claim 단위 버퍼: D2 Option A 필요
  - D. 스트리밍 뒤 최종본 교체: 이미 본 텍스트가 바뀜
- 호출자 5곳에 같은 결정을 적용할지는 미확인이다.

### D5. 출력
- GS 본문은 valid claim을 이어 붙인 것이다(`grounded_answer` L111~). 현행 답변은 자유 문단 + 출처 표기다.
- 설계 방향: 내부 표현(claim + ID + 원문 구간)과 사용자 표현(목회 문단 + 각주·출처)을 분리하고, 문장이 claim ID를 가리키게 한다.
- PR #17(`5568165b`, paragraph-anchored evidence)의 출력 계약과의 관계는 미확인이다.

### D6. ADR 영향

| 대상 | 판정 | 근거 |
|---|---|---|
| GS 경계 ADR-036 문서 위치 | **CONFLICT** | Accepted(2026-09-27)이지만 `origin/claude/p4-final-validation-guide-b3af47`에만 있음. main에 병합된 GS 코드가 main에 없는 ADR을 인용 |
| ADR-036 번호 | **CONFLICT** | GS 경계 문서와 공개 자료 근거 답변 문서가 같은 번호 |
| B4 | UNCHANGED | D2 A/B 모두 |
| B6 | Model A·D는 UNCHANGED, Model C는 **AMENDMENT REQUIRED** | 자동 채점과 의미 판정의 분리 |
| B8 | UNKNOWN | Claim에 인용 구간 필드를 추가할 때 |
| 공개 자료 ADR-036 | UNKNOWN(적용 범위) | main은 Proposed, EUAT 브랜치는 Approved(`c9650a22`). 해당 경로도 generate_stream 호출자 |
| ClaimGuard 계약 | UNCHANGED | docstring상 삽입 위치는 범위 밖 |
| 인용 검증기 | 병행이면 UNCHANGED, 차단 방식이면 AMENDMENT REQUIRED | 경고 전용 계약 |
| PR #17 | UNKNOWN | 내용 미추적 |

## 6. P0-5 문제 대응표

"막음(PREVENT) / 탐지(DETECT) / 경고만(WARN ONLY) / 미대응(NOT COVERED)"으로 구분한다.

| P0-5 문제 | 현행 production | GS 현재 | GS + D3 Model A |
|---|---|---|---|
| 근거 밖 진술 | NOT COVERED | ID 없는 claim만 제외(부분 PREVENT) | 동일 + 인용 구간 없는 claim 제외. **근거 ID를 달았지만 내용이 다른 유형은 미탐지** |
| 출처 오귀속 | WARN ONLY(라벨 토큰 겹침) | NOT COVERED(ID 소속만) | 인용 구간이 다른 근거에 있으면 DETECT |
| 근거 없는 직접 인용 | WARN ONLY(숫자·라틴어만) | NOT COVERED | 원문 구간이면 DETECT·PREVENT. 한국어로 옮긴 인용의 충실도는 미검증 |
| 교단 틀 문장 | NOT COVERED | ID 없으면 제외(추출기 의존) | 동일 |
| 질문 불일치 | NOT COVERED | NOT COVERED | NOT COVERED |
| 근거 부족 | 0건만 PREVENT | pool 0 / valid 0만 PREVENT | 동일. 얇은 근거는 미대응 |
| 인용 검증 | WARN ONLY | 구조 DETECT | 구조 + 인용 구간 DETECT |
| 교차언어 | NOT COVERED | NOT COVERED | 인용 구간 존재만. 의미는 NOT COVERED(B6 설계) |

## 7. C1 보고 교차검증 요약

- **CONFIRMED**: 호출자 5곳, 표시 → `to_result` 순서, 앱 import 0, 변환 사슬 실재, ID 소속만 검사, 정확 일치, B4·B6 원문, GS 경계 ADR Accepted, 20칸 계보 표, merge-base.
- **CORRECTED**:
  - 공개 자료 ADR-036 상태: C1은 Proposed로 보고. EUAT 브랜치는 Approved이며, Status 비교를 수행하지 않았다.
  - 대응표 과대평가:
    - ClaimGuard가 근거 밖 주장과 교단 틀을 탐지한다고 판정(실제로는 표현 사전과 경쟁 후보만)
    - 현행이 근거 부족을 막는다고 판정(0건만)
    - GS가 오귀속을 탐지한다고 판정(ID 소속만)
  - 주장 출처 오표기: C1-F는 CUE의 주장이다.
  - 추출기 "구현 예정" → 데모에 구현과 P9 실모델 실행 기록이 있다(core에는 없음).
  - "new code 아님" → ID 프롬프트·파서·인용 구간 필드는 core에 없다.
- **형식 위반**: APPENDIX (b)(c)가 원문 출력이 아님. ClaimGuard 행 번호 근사치.
- 첫 feasibility trace의 오류(앱 호출자 2곳 누락, 변환 사슬 "없음" 보고)는 v2에서 해소됐다.

## 8. 구현 대상 (구현 승인 시, 현 단계 변경 없음)

- `core/generation.py`: `_build_prompt` L554, `generate_stream` L583, `GenerationStream.__iter__` L461 / `to_result` L491, `GenerationResult` L533
- `core/grounded_synthesis_input.py`: `prompt_text`(근거 ID 포함)
- `core/grounded_claims.py`: Claim 인용 구간 필드, 제품 추출기(데모 `parse_llm_claims` L121~ 기반)
- `core/grounded_citation.py`: `_check_span_in_text` 대상 변경(claim 전문 → 인용 구간)
- `core/grounded_answer.py`: 사용자 출력 조립(D5)
- `core/evidence_assembly.py`: 제품 호출
- UI 5곳: `chat.py` L481/L566, `nae_public_section.py` L147, `passage_commentary_panel.py` L94, `_passage_commentary_tab.py` L119
- 테스트: `tests/test_grounded_*.py` 6개, `test_generation_*`
- 기준선: P0-5 APPINDEX 24건(`1b1ac017`)

## 9. BLOCKERS

1. 릴리스 라인 미결정. dev에는 GS와 근거 계층이 없다.
2. ADR-036 번호 중복, GS 경계 ADR 미병합.
3. 의미 지지 판정의 위치: B6·C-03이 자동 흐름 밖에 두었다. P0-5의 주 실패 유형은 결정적 검사로 잡히지 않는다.
4. 스트리밍과 검증 시점의 충돌.
5. core에 생성 계약(ID 프롬프트·파서)이 없다.

## 10. HQ 결정 요청

1. **D1 착지 라인**: L1 main / L2 dev / L3 FU-007 통합본 경유. FU-007 릴리스 라인 결정과 같은 결정이다.
2. **D6 ADR 정리**: GS 경계 ADR의 main 반영 여부, 두 ADR-036 중 하나의 번호 재부여.
3. **D3 범위**: Model A/D(B6 유지, 결정적 인용 구간까지, ADR 변경 없음) 또는 Model C(자동 의미 검증, B6 Amendment 선행).
4. **D2 생성 계약**: 구조화 생성 / 생성 후 추출.
5. **D4 스트리밍**: 버퍼 / claim 단위 / 표시 후 경고 / 교체. 적용 호출자 범위.
6. **D5 출력**: 내부 claim 표현과 사용자 문단의 분리 방식. PR #17 계약 확인 포함.

## 11. 권장 다음 Task

1. HQ가 결정 1·2·3을 먼저 내린다. 코드 변경이 없고, 나머지 결정의 전제다.
2. 그 뒤 "GS Integration Design Doc(+ 필요 시 ADR Amendment 초안)"을 작성한다.
   - 범위: D2·D4·D5 확정안, 인터페이스 명세, 테스트 계획
   - 성공 기준: P0-5 24건 기준선 대비 재검증. 구조 지표는 자동으로, 의미 지지는 B6대로 CUE 표본 검토로 분리해 보고한다.
   - C1 Review 대상(새 아키텍처 층)
3. 구현 Task Order는 설계 문서가 승인된 뒤에 낸다.
