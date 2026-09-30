# GS 교차언어 검증 범위 — HQ 결정 ③ 기록 및 계약 대조 보고서

- 작성: CUE · 2026-09-30
- 단계: HQ 결정 순서 ③
  - 완료: ① 릴리스 라인 = `dev/dbma-engine`, ② ADR-036 = GS 경계 / ADR-037 = 공개 자료 근거 답변
- 기준: `tmp/fu007-integration-trial` `3ea7ece1`
  - GS 코드 blob은 결과 브랜치, `origin/main`, `tmp/fu007-combined-translation`에서 동일하다:
    - `grounded_citation.py` `b40d6a9a`
    - `grounded_claims.py` `95cf01b0`
    - `grounded_answer.py` `4261db5a`
- 방법: 읽기 전용. 코드 통합·수정 없음.
- 표기: [CONFIRMED] 코드·문서로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인

## 1. HQ 결정 ③ (원문 요지 기록)

**DECISION: 원문 언어 기준의 결정적(deterministic) citation span 검증만 GS 계약에 포함한다.**

| 구분 | 내용 |
|---|---|
| GS가 보장할 것 | ① 인용한 evidence ID가 included evidence set에 있는가 ② citation span이 해당 **원문** evidence text에 실제로 있는가 ③ evidence provenance를 추적할 수 있는가 — 원문 언어 기준의 결정적 정확 일치 |
| GS가 보장하지 않을 것 | 언어가 다른 경우의 의미적 동등성(영어 근거 → 한국어 답변, 그 반대), 번역의 의미 보존, paraphrase·semantic entailment, 신학적 해석의 논리적 도출 |
| 명칭 규칙 | 검증 결과의 정확한 의미는 **"citation/provenance span verified"**다. **"claim semantically grounded"로 해석하는 것은 금지**다 |
| 별도 BACKLOG | 근거 ID는 맞지만 내용이 근거로 뒷받침되지 않는 경우, 근거 없는 교단 틀, 출처 오귀속, 질문 불일치, 기타 의미 grounding 문제 |
| 의미 grounding을 넣으려면 | B6과 C-03의 경계를 재검토 → 필요 시 ADR Amendment 또는 별도 ADR → HQ 승인 → 별도 구현 |
| 이번 단계 금지 | GS 코드 수정, GenerationService 통합, 교차언어 의미 검증기 구현, prompt·ClaimGuard·ADR 내용 변경 |

## 2. 현재 구현과 ③ 계약의 대조

| ③ 계약 항목 | 현재 구현 | 위치 | 판정 |
|---|---|---|---|
| ① ID ∈ included set | `id_exists = eid in included_ids` | `grounded_citation.py` L154~L156 | [CONFIRMED] **일치** |
| ① (결합 단계) | `bind_claims`: 인용 ID가 모두 included면 `valid=True` | `grounded_claims.py` L85~L95 | [CONFIRMED] 일치 |
| ② citation span이 원문에 있음 | `_check_span_in_text(claim.text, ev.text)`: 5자 미만이면 실패, 그 외 대소문자 구분 정확 부분일치 | `grounded_citation.py` L110~L119, L170~L176 | [CONFIRMED] **알고리즘은 일치.** 단 검사 대상이 별도의 인용 구간이 아니라 **claim 본문 전체**다(3.1절) |
| ③ provenance 추적 | `provenance_ok = ev.has_provenance` | `grounded_citation.py` L178~L179 | [CONFIRMED] 일치 |
| 결정성 | GS 모듈에 LLM 호출 없음(`ollama` import 없음, B9) | `grounded_citation.py` L24~L33 | [CONFIRMED] 일치 |
| 의미 검증 미포함 | GS에 의미·교차언어 판정 코드 없음 | GS 4개 모듈 | [CONFIRMED] ③ 범위와 일치 |

## 3. ③ 범위 안에서 확인된 한계 (구현하지 않음, 기록만)

### 3.1 "citation span" 필드가 없다
- [CONFIRMED] GS 경계 ADR의 B8 정본 `Claim`은 `claim_id`, `text`, `evidence_ids`, `valid`뿐이다. 인용 구간 필드가 없다(ADR-036 B8, p4 브랜치; `grounded_claims.py` L37~L43).
- [CONFIRMED] B8의 `CitationCheckResult` 주석은 "인용 구간이 Evidence.text에 실재하는가"다. 구현은 **claim 본문 전체를 인용 구간으로 사용**한다(`grounded_citation.py` L52~L53, L173).
- [INFERRED] 따라서 현재 ②가 통과하려면 claim 본문이 원문 근거의 어떤 구간과 **글자 그대로** 같아야 한다.
  - 한국어 답변 문장이 영어 근거를 인용하면 ②는 **항상 실패**한다. 의미가 맞아도 실패하고, 틀려도 실패한다.
  - 이는 ③이 "보장하지 않는다"고 정한 의미 판정과는 다른 문제다. **원문 언어의 인용 구간을 담을 자리가 계약에 없다**는 문제다.
- [INFERRED] 한국어 답변에서 ③ 계약을 실제로 쓰려면 claim과 별개로 원문 언어 인용 구간을 담는 구조가 필요하다. 이는 B8(정본 시그니처) 변경이며 **④ 생성 계약의 결정 사항**이다. ADR Amendment 필요 여부는 [UNKNOWN](B8이 "각 Phase가 정확히 이 형태로 구현"이라고 명시).

### 3.2 같은 언어에서도 생기는 결정적 불일치
- [CONFIRMED] 공백·줄바꿈·OCR 차이에 대한 정규화가 없다(대소문자 구분, 원문 그대로 비교, `grounded_citation.py` L41~L57).
- [CONFIRMED] 실례(P0-5 P6):
  - H2 근거 4위 원문 "…to utterly 1096 ClassicChristianLibrary.com 1690 Chariots of Iron — Judges 1:19-20 exterminate those condemned races…"에는 쪽 머리글이 문장 중간에 끼어 있다.
  - 인용문 "utterly exterminate those condemned races"는 정확 일치로 찾을 수 없다. CUE도 이 때문에 한 번 오판했다.
- [INFERRED] 결정적 검사는 이런 경우 **거짓 음성**(실제로는 원문에 있는데 없다고 판정)을 낸다. 거짓 양성보다는 안전한 쪽이지만, 사용자 표시에 쓰려면 이 성질을 알아야 한다. 정규화 도입 여부는 별도 결정 사항이다.

### 3.3 "grounded" 상태 라벨의 실제 의미
- [CONFIRMED] `GroundedAnswer.status == "grounded"`는 **valid claim이 하나 이상이라는 사실만으로** 결정된다(`grounded_answer.py` L111~L124). span 검사와 provenance 검사 결과는 사용하지 않는다(이 모듈은 citation 검사를 import하지 않음, L24~L31).
- [CONFIRMED] C-03 결정("grounded = 구조적 검증만 의미")과 일치한다.
- [INFERRED] ③의 명칭 규칙 아래에서 이 라벨은 "citation/provenance span verified"보다도 **좁은 의미**(ID 소속만)다.
  - 운영 통합 시 이 라벨을 사용자 문구("근거 확인됨" 등)로 옮기면 ③이 금지한 확대 해석이 된다.
  - 라벨 변경은 B8 변경이므로 이번에는 기록만 한다.

## 4. 교차언어 현황 (명시)

| 경우 | ② span 검증 결과 | 의미 판정 |
|---|---|---|
| 영어 근거 → 영어 원문 그대로 인용한 claim | 일치하면 통과 | 범위 밖 |
| 영어 근거 → 한국어 claim(번역·의역) | **항상 실패**(3.1절) | 범위 밖(③) |
| 한국어 근거 → 영어 claim | 항상 실패 | 범위 밖 |
| 같은 언어의 paraphrase | 실패 | 범위 밖 |

- [CONFIRMED] 현재 코퍼스(`output/bench`, 119,595 TSU)의 한국어 비율은 0.00%(FU-007 시점 dev 코드 주석 기준)다. 사용자 질의와 답변은 한국어다. 따라서 **제품의 기본 경우가 "영어 근거 → 한국어 claim"**이며, 현재 ②는 이 경우에 사용할 수 없다.

## 5. B6·C-03과의 충돌 여부

- [CONFIRMED] **충돌 없음.**
  - B6은 결정적 검사를 "evidence_id 실재 여부, manifest 소속 여부, 인용 구간이 Evidence.text에 실제로 존재하는지"로 정하고, 의미 지지 판정을 자동 채점과 분리한다. 이는 ③ 결정과 같은 경계다.
  - C-03은 이 분리를 유지한다고 결정했다.
  - GS 코드에 의미 판정 구현은 없다.
- [CONFIRMED] 운영 경로의 `core/citation_verifier.py`(숫자·라틴 단어 휴리스틱, 경고 전용)는 GS가 아니므로 ③의 대상이 아니다. 운영 통합 시 두 검증의 관계는 ④ 이후 결정 사항이다.

## 6. P0-5 문제와 ③의 관계 (해결로 간주하지 않음)

| P0-5 문제 | ③ 결정 이후 상태 |
|---|---|
| 근거 ID는 맞지만 내용이 근거 밖(D1·C1·C2) | **해결 안 됨** — 의미 판정은 범위 밖. BACKLOG |
| 근거 없는 교단 틀(A3·B1·G3) | **해결 안 됨** — BACKLOG |
| 출처 오귀속(A3·D2) | **해결 안 됨** — 원문 인용 구간이 계약에 들어오면(④) 일부 탐지 가능성이 생긴다([INFERRED]). 현재는 BACKLOG |
| 근거 없는 직접 인용(B1) | **해결 안 됨** — 원문 언어 인용이면 ②로 탐지 가능. 한국어로 옮긴 인용은 불가. 현재 한국어 claim에 대해 ②를 쓸 수 없음(3.1절) |
| 질문 불일치(E3) | **해결 안 됨** — BACKLOG |

## 7. 다음 단계(④)로 넘기는 사실

1. 원문 언어 인용 구간을 담을 필드가 B8 Claim에 없다. 한국어 답변에서 ③ 계약을 쓰려면 생성 계약(④)과 B8이 이를 포함해야 한다.
2. 정확 일치의 거짓 음성(공백·OCR·쪽 머리글)을 허용할지, 정규화할지는 별도 결정 사항이다.
3. "grounded" 라벨의 사용자 노출 방식은 ③의 명칭 규칙을 따라야 한다.
4. 의미 grounding은 B6/C-03 재검토와 새 ADR 경로로만 다룬다(③).

## 8. MUTATION

- 코드·ADR·prompt·ClaimGuard 변경 없음. GenerationService 통합 없음.
- 이 보고서의 커밋·푸시만 수행한다.
