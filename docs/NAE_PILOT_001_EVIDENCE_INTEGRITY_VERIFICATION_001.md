# NAE Pilot 001 — Evidence Integrity Verification (CUE Direct Re-verification)

**작성일:** 2026-08-08
**성격:** READ-ONLY FORENSIC VERIFICATION. C1로부터 전달받은 두 차례 보고서
(`/tmp/NAE_PILOT_001_FINAL_MATRIX.md`, `/tmp/NAE_PILOT_001_C1_RELAY_REWORK_REPORT.md`)
가 반복적으로 사실 오류(저자명, TSU-0003893 source_text 부재 주장 등)를
포함하고 있어, CUE가 Production TSU + canonical.json을 직접 재조회해
Task 5/6/7/8/9을 독자적으로 재검증한 결과다.
**Production TSU 수정 없음. Claim 수정 없음. Human Decision 작성/변경 없음.
Promotion/Embedding/Qdrant 미실행. Git commit/push 미수행.**

---

## 대상 6건

```
TSU-0000199, TSU-0003525, TSU-0003893, TSU-0000713, TSU-0000330, TSU-0000033
```

---

## Task 5 — Evidence Classification(재검증)

| TSU | C1 2차 보고서 판정 | CUE 재검증 판정 | 근거 |
|---|---|---|---|
| TSU-0000199 | CONTEXT_SUPPORTED | **CONTEXT_SUPPORTED**(일치) | 대상 문장의 "this process"가 무엇을 가리키는지는 context_before("an application of the liquid to the solid")를 봐야만 확정됨 |
| TSU-0003525 | CONTEXT_SUPPORTED | **CONTEXT_SUPPORTED**(일치) | "All this"가 context_before(TSU-0003524의 내용)를 가리킴 — 아래 Task 7 참고 |
| TSU-0003893 | UNSUPPORTED("source_text 확인 불가") | **정정: EXPLICITLY_SUPPORTED**(불일치, C1 오류) | source_text가 Production에 실제로 존재하며(직접 재조회 확인), claim("일부 사람들은 ~라고 생각한다")이 source_text("To them it seems...")를 정확히 반영함 — "확인 불가"는 사실이 아님 |
| TSU-0000713 | EXPLICITLY_SUPPORTED | **정정: CONTEXT_SUPPORTED**(불일치) | claim의 "비교되었으며"(compared) 부분은 대상 문장에 없고 context_before("the churches were compared with each other")에만 있음 — claim이 context_before 내용을 일부 흡수하고 있어 대상 문장만으로는 완전히 뒷받침되지 않음 |
| TSU-0000330 | EXPLICITLY_SUPPORTED | **EXPLICITLY_SUPPORTED**(일치) | 대상 문장 자체에 "we should keep Christ's death in memory... by the eating of bread"가 명시적으로 포함되어 claim과 직접 대응 |
| TSU-0000033 | EXPLICITLY_SUPPORTED | **EXPLICITLY_SUPPORTED**(일치) | 대상 문장과 claim이 거의 1:1 대응 |

**2건에서 C1 2차 보고서와 다른 결론**: TSU-0003893(오류 정정), TSU-0000713(과대평가 하향 조정).

---

## Task 6 — 언어 요소 보존 확인

| TSU | 주어/목적어 | 화자 구분 | 수량어(all/some/only) | 직접인용 vs 해설 | 판정 |
|---|---|---|---|---|---|
| TSU-0000199 | 주어(동사 banro)/목적어(과정) 보존 | 저자 본인 주장, 해당 없음 | 해당 없음 | 저자 해설(학술 논증) | PASS |
| TSU-0003525 | 주어("All this") pronoun을 claim이 "악한 정서와 파당적인 분쟁"으로 명시적으로 풀어씀 — **원문에 없는 해석적 확장**이지만 context_before와 정확히 일치 | 저자 본인 권면 | 해당 없음 | 저자 해설 | PASS(단, context 의존 명시 필요) |
| TSU-0003893 | 주어("them"=일부 사람들)를 claim이 "일부 사람들은"으로 정확히 보존 — **저자 자신의 입장으로 오인되지 않도록 화자 구분이 잘 되어 있음** | 저자가 소개하는 제3자 견해 — 구분 보존 양호 | "all"→"모든 사람들" 보존 | 저자 해설(간접화법) | PASS |
| TSU-0000713 | 주어(교회들)/목적어(인사·연락) 보존 | 저자 서술, 해당 없음 | 해당 없음 | 직접 인용("As distinct bodies...")을 저자가 인용부호로 표시 — claim은 이를 정확히 반영 | PASS(단 "비교되었으며" 부분은 context 유래, 위 Task 5 참고) |
| TSU-0000330 | 주어(we/우리)가 한국어 claim에서 비인칭화("~것이 더 적절하다")됨 | 저자 본인 신학적 결론 | 해당 없음 | 저자 해설 | PASS(의미 손실 없는 자연스러운 한국어 변환) |
| TSU-0000033 | 주어(He=Christ)/목적어(us=우리) 정확히 대응("그분"/"우리를 위해") | 저자 서술 | 해당 없음 | 저자 해설 | PASS |

---

## Task 7 — TSU-0003525 Cross-TSU Contamination(특별 요청 재검증)

**판정: CONTEXT_DEPENDENT**(C1 2차 보고서와 일치, 정확함)

```
TSU-0003525.source_text = "All this should, if possible, be avoided."
TSU-0003524.claim(=context_before) = "The evil passions of even good men may
    triumph over piety, and partisan strife may destroy the peace and the
    prosperity of the body of Christ."
```

- **문자 그대로의 오염(literal text leakage)은 없음** — TSU-0003525의
  `source_text` 필드 자체에는 TSU-0003524의 문구가 전혀 섞여 있지 않다
  (필드 값 자체는 깨끗함).
- **그러나 의미적/지시적 의존성이 실재함** — "All this"가 가리키는
  대상이 TSU-0003525 레코드 안에는 전혀 존재하지 않고, 오직
  TSU-0003524(바로 앞 문장, 동일 문단)에만 있다. TSU-0003525의 claim은
  이 지시대명사를 사람이 이미 해석해(=TSU-0003524 내용을 대입해)
  재진술한 것이다.
- **1차 C1 보고서의 오류 재확인**: "Dagg 책에는 이 문장이 없다 →
  오염 없음"이라는 판정은 원 질문("이전 TSU에서 유입된 내용이 있는가")에
  대한 답이 아니다 — Cross-TSU contamination은 다른 책(Dagg) 간의 문제가
  아니라 **같은 책(Hiscox) 내 인접 TSU 간의 문맥 의존성** 문제였다.

---

## Task 8 — Scripture Verification(재검증)

대상 6건 중 성경 관련 근거가 있는 것은 **TSU-0000713**뿐이다(나머지
5건은 `citations`/`scriptures` 모두 빈 배열이거나 신학 논증/학술 각주뿐).

### TSU-0000713 상세 재검증

```
source_text: "No church communicated with me as concerning giving and
              receiving, but ye only."³ "As distinct bodies, they sent
              and received salutations,"* and held intercourse by
              messengers.'
citations:   ["* Rom. xvi. 16; 1 Cor. xvi. 19."]
scriptures:  []
```

**신규 발견(양쪽 C1 보고서 모두 놓친 부분)**: 이 문장은 사실 **두 개의
독립된 각주(위첨자 "3"과 "*")를 가진 두 개의 서로 다른 인용**이다.

1. 첫 문장("No church communicated with me... but ye only.", 각주 "3")은
   **빌립보서 4:15(KJV) 거의 정확한 직접 인용**이다 — "Now ye
   Philippians know also, that in the beginning of the gospel, when I
   departed from Macedonia, **no church communicated with me as
   concerning giving and receiving, but ye only.**" 그러나 이 인용의
   출처(빌 4:15)는 `citations`/`scriptures` **어디에도 기록되어 있지
   않다** — 각주 "3"이 존재한다는 사실만 원문 표기(`³`)로 남아있고,
   실제 참조는 유실됨.
2. 두 번째 문장("As distinct bodies... salutations", 각주 "*")에 대한
   근거로 `citations`에 "Rom. xvi. 16; 1 Cor. xvi. 19."가 기록되어
   있다 — 이건 정확히 대응(로마서 16:16 "Salute one another...", 고전
   16:19 "The churches of Asia salute you...").

**결론**: `citations` 필드가 완전히 빈 것은 아니지만, **실제 인용된 두
성경 구절 중 하나(빌립보서 4:15)가 통째로 누락**되어 있다 — 단순히
"scriptures 필드가 비어있다"는 기존 두 보고서의 지적보다 더 구체적이고
정확한 문제다. Claim의 해석적 확대는 없음(claim이 원문보다 더 강하게
주장하지 않음).

---

## Task 9 — Per-TSU Readiness(재검증, 개별 판정)

| TSU | C1 2차 보고서 | CUE 재검증 | 사유 |
|---|---|---|---|
| TSU-0000199 | NEEDS_CONTEXT | **NEEDS_CONTEXT**(일치) | "this process" 지시 대상이 context_before 없이는 불명확 |
| TSU-0003525 | NEEDS_CONTEXT | **NEEDS_CONTEXT**(일치) | TSU-0003524와 함께 검토해야 "All this"의 의미가 완전해짐 |
| TSU-0003893 | NEEDS_SOURCE_CORRECTION(오류) | **정정: READY_FOR_HUMAN_REVIEW**(단, Q4 AMBIGUOUS 플래그 필수) | source_text는 정상 존재·정상 지원됨(오류 정정). 다만 화자("them"=제3자 개방성찬 옹호자)가 저자 본인 입장으로 오독될 위험은 여전히 실재하므로 Q4 플래그는 유지 |
| TSU-0000713 | READY_FOR_HUMAN_REVIEW | **정정: NEEDS_CONTEXT** | claim 일부가 context_before 유래(Task 5), 빌립보서 4:15 인용 출처 누락(Task 8) — 두 가지 실질적 이슈로 인해 하향 조정 |
| TSU-0000330 | READY_FOR_HUMAN_REVIEW | **READY_FOR_HUMAN_REVIEW**(일치) | 자체 완결적, evidence 명시적 |
| TSU-0000033 | READY_FOR_HUMAN_REVIEW | **READY_FOR_HUMAN_REVIEW**(일치) | 자체 완결적, evidence 명시적 |

**주의**: 위 readiness는 Human Decision(A/R/C)이 아니다. CUE는 신학적
승인/거부를 판단하지 않았다.

---

## 종합

```
Evidence Integrity:    6/6 재검증 완료(전부 Production 실측 대조)
Claim Fidelity:        4/6 문제 없음, 2/6(TSU-0000199, TSU-0003525) context 의존
Context Sufficiency:   3/6 NEEDS_CONTEXT(TSU-0000199, TSU-0003525, TSU-0000713 — 마지막 1건은 재분류로 추가됨)
Cross-TSU Dependency:  TSU-0003525 확인(CONTEXT_DEPENDENT, C1 2차 보고서와 일치)
Scripture Evidence:    TSU-0000713에서 빌립보서 4:15 인용 출처 누락 신규 발견(양쪽 C1 보고서 모두 놓침)
Packet Readiness:      READY_FOR_HUMAN_REVIEW 3건, NEEDS_CONTEXT 3건(TSU-0000713 하향 조정 포함)

Production Mutation = 0
Human Decision = 0
Promotion = 0
Embedding = 0
Qdrant = 0
Git = NOT PERFORMED
```

## C1 보고서 대비 정정 요약

| 항목 | C1 보고서 오류 | 정정 근거 |
|---|---|---|
| TSU-0003893 Evidence Classification | UNSUPPORTED("source_text 확인 불가") | 실제 Production 조회 결과 source_text 정상 존재, claim과 정확히 대응 |
| TSU-0003893 Readiness | NEEDS_SOURCE_CORRECTION | 소스 자체는 문제 없음 — READY_FOR_HUMAN_REVIEW(Q4 AMBIGUOUS 플래그 유지)로 정정 |
| TSU-0000713 Evidence Classification | EXPLICITLY_SUPPORTED | claim 일부가 context_before 유래 확인 — CONTEXT_SUPPORTED로 하향 정정 |
| TSU-0000713 Scripture Evidence | "scriptures 필드 공백"만 언급 | 실제로는 빌립보서 4:15 인용 자체가 citations에서도 누락된, 더 구체적인 문제 |
| TSU-0000713 Readiness | READY_FOR_HUMAN_REVIEW | 위 2건 근거로 NEEDS_CONTEXT로 하향 정정 |

이 문서가 이번 Pilot 001의 Task 5/6/7/8/9에 대한 **최종적으로 신뢰
가능한 검증 결과**다.
