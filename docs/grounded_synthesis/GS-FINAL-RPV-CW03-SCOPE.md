# CW-03 Corrective WO — P5 Parser 단일-Claim 구조 결함 (DRAFT, HQ 승인 대기)

- 작성: CUE, 2026-09-28. RPV-05 Root-Cause Trace 결과([GS-FINAL-RPV-TEST-SET-DRAFT.md](GS-FINAL-RPV-TEST-SET-DRAFT.md)
  및 채팅 제출 보고서 "RPV-05 HOLD Root-Cause Trace" 참고)에서 확인된 P5 파싱 결함의
  corrective WO 초안이다. **DRAFT 상태 — HQ 승인 전까지 C1/CUE 누구도 구현에
  착수하지 않는다.** CW-01/CW-02와 동일하게 `GS-FINAL-RPV-CW01-CW02-SCOPE.md`
  포맷을 따른다.

---

## 결함 위치 (CUE가 코드로 직접 확인)

`scripts/grounded_synthesis_integration_demo.py`:
- `parse_llm_claims()` (190번째 줄) — **결함의 정확한 위치**
- `extract_claims_with_ollama()` (72번째 줄 부근) — 호출부, 수정 대상 아님

## 근본 원인 (RPV-05 root-cause trace로 확인됨, raw LLM output 직접 재현)

`parse_llm_claims()` 내부 두 스코프의 불일치:

1. **evidence_id 수집 — 전역(global) 스코프** (205/207/209번째 줄):
   ```python
   evidence_id_patterns = re.findall(r'evidence_id:\s*([^\],\s]+(?:_[^,\]\s]+)*)', llm_output)
   tsu_ids = re.findall(r'(?:NAE-)?TSU[-_]?(?:UNK[-_])?\w+|NAE-UNC-\w+', llm_output)
   bracket_ids = re.findall(r"\[\s*(['\"])(.*?)\1\s*\]", llm_output)
   ```
   `llm_output` **전체**(모든 문단)에서 evidence_id를 스캔한다.

2. **claim_text 채택 — 로컬(local) 스코프, 첫 문단만** (226-231번째 줄):
   ```python
   lines = llm_output.strip().split("\n")
   claim_line: str | None = None
   for line in lines:
       if not _is_prompt_echo(line):
           claim_line = line.strip()
           break
   ```
   프롬프트 반복이 아닌 **첫 번째 줄(=첫 문단)만** `claim_line`으로 채택하고
   순회를 종료한다 — 이후 문단은 전부 버려진다.

3. **바인딩** (240-241번째 줄): 전역 스캔한 evidence_id 전부를 로컬(첫 문단만)
   claim_text에 통째로 붙인다.

실측(RPV-05, 재현 2회): LLM raw output은 5개 문단(로마서 2개, 야고보서 1개,
조화 설명 2개)으로 구성되고 문단마다 서로 다른 evidence_id가 정확히
개별 태그되어 있었다(LLM 생성 자체는 정상). 그러나 파서는 **첫 문단(로마서
3:24만 다룸)만** claim_text로 채택하면서, 야고보서 2장 문단에 붙어있던
`NAE-TSU-0033580`(Fuller Vol.8)을 포함한 4개 evidence_id 전부를 그
첫 문단 claim에 잘못 바인딩했다. 결과: `Claim.valid=True`, `grounded`
상태지만 claim 텍스트와 무관한 evidence_id가 섞여 있고, 실제 야고보서
관련 문단 내용은 최종 답변에서 통째로 소실됨.

## CW-01/CW-02와의 관계 (범위 분리 근거)

CW-01(`_is_prompt_echo()` 추가, 229번째 줄)과 CW-02(`_clean_evidence_markers()`
추가, 238번째 줄)는 이번 결함을 만들지도, 고치지도 않았다. "첫 줄/첫 문단만
claim으로 채택"하는 226-241번째 줄의 구조 자체는 CW-01/CW-02 이전부터
있던 것이며, 두 WO의 승인된 허용 범위(`parse_llm_claims()`, `extract_claims_with_ollama()`
함수 내부이되 위 특정 목적으로 한정)와 겹치지만 다른 결함이다 — 별도 corrective
WO로 분리해 HQ 승인을 받는다.

## Acceptance 기준 (HQ 확정, 2026-09-28)

**핵심 원칙 — "첫 문단 문제를 고친다"가 목표가 아니다.**

> Claim text와 evidence_id binding의 범위가 **동일한 synthesis unit**을
> 기준으로 일치해야 한다.

즉 구현이 "여러 문단으로 나눠서 처리"하는 형태를 취하든 다른 방식을
취하든, 성공 조건은 문단 개수를 늘리는 것 자체가 아니라 **claim_text가
가리키는 synthesis unit과 evidence_ids가 실제로 등장한 synthesis unit이
항상 동일해야 한다**는 것이다. 구현이 이 불변조건을 만족하는 한 구체적
방식(문단 분할/구조화 출력 포맷/다른 파싱 전략 등)은 C1이 제안하고
CUE가 검증한다 — CUE는 특정 구현 방식을 강제하지 않는다.

## 목표 (제안, 위 Acceptance 기준 하위)

1. synthesis unit(문단 또는 LLM이 실제로 구분한 단위) 별로 개별 claim을
   생성하고, 각 claim에는 **해당 unit에 실제로 등장한 evidence_id만**
   바인딩한다 (전역 스캔 방식 폐기).
2. 기존 단일-unit 사례(출력이 1개 unit뿐인 경우)는 현재 동작과 동일하게
   유지 — 회귀 없음.
3. CW-01(prompt-echo skip)·CW-02(marker 제거)의 계약은 unit 단위 파싱으로
   확장될 때도 그대로 유지한다.
4. `core/grounded_claims.py::bind_claims()`의 `evidence_ids ⊆
   included_evidence_ids` fail-closed 계약은 변경하지 않는다.

## 회귀 조건 (HQ 확정, Case A-E — 구현 완료의 필요조건)

**CW-03은 unit test만 통과해서 완료되는 corrective work가 아니다.** 아래
5개 케이스, 특히 Case E(RPV-05 실제 재현·해소)를 모두 충족해야 한다.

- **Case A** — 1개 문단 + 1개 evidence → 기존 정상 동작 보존(회귀 없음).
- **Case B** — 2개 이상 문단 + 서로 다른 evidence → 각 claim이 해당
  evidence와 올바르게 binding.
- **Case C** — 여러 evidence_id가 전체 output에 존재 → 다른 문단의
  evidence가 첫 claim에 누출되지 않음.
- **Case D** — CW-01/CW-02 regression 없음 → prompt echo / parser
  artifact 재발 없음.
- **Case E** (가장 중요) — RPV-05 실제 질문을 재실행해, multi-source
  synthesis(HQ 원문 표현: "Fuller Vol.7 + Fuller Vol.8을 포함한")가
  최종 claim/answer에 보존됨을 확인.
  **CUE 주석**: RPV-05 root-cause trace에서 CUE가 직접 확인한
  EvidencePool/SynthesisInput에는 Fuller Vol.8(`NAE-TSU-0033580`)만
  포함되어 있었고 Fuller Vol.7은 관측되지 않았다(포함된 5건:
  `TSU-UNK-e1e68a35c3c031676bc13dc47a06f934_chunk_00650`,
  `NAE-TSU-0025626`, `NAE-TSU-0033580`, `TSU-UNK-74edb7923a40d79e01af51e24b8e8285_chunk_00064`,
  `NAE-UNC-Smith_Bible_Dictionary_HackettAbbot_Vol2_p009893`). Case E
  검증 시점에 retrieval 결과가 그 사이 달라졌을 수 있으므로, C1/CUE는
  구현 검증 시 **그 시점의 실제 EvidencePool 구성을 다시 확인**한 뒤
  "실제로 포함된 multi-source 전부가 최종 claim/answer에 보존되는가"를
  기준으로 판정한다 — Fuller Vol.7의 존재를 가정하지 않는다.

## 허용 파일

`scripts/grounded_synthesis_integration_demo.py`의 `parse_llm_claims()`만.
(필요시 `extract_claims_with_ollama()`의 프롬프트 출력 형식 지시 문자열도
포함 가능 — 단, 파싱 로직 변경을 우선하고 프롬프트 형식 변경은 최소화한다.)

## 금지 파일

`core/grounded_claims.py`, `core/grounded_answer.py`,
`core/grounded_citation.py`, `core/grounded_synthesis_input.py`,
`core/evidence_*.py`, `core/retrieval.py`, `core/candidate_generator.py`,
`core/hybrid_candidate_pipeline.py` — P4~P7 core 계약 및 retrieval
변경 금지 (공통 금지 사항, HQ §5 재확인 — RetrievalEngine/CandidateGenerator/
ranking/candidate_k/corpus/TSU dataset/재인덱싱/Qdrant/Tantivy/신규
retrieval engine/신규 corpus/UI/LLM provider/GS architecture 확장 전부
금지).

## CUE 검증 체크리스트 (구현 후, 구현 승인 시 적용)

- [ ] Case A — 1문단+1evidence 기존 동작 보존
- [ ] Case B — 2문단 이상, 서로 다른 evidence가 각 claim에 정확히 binding
- [ ] Case C — 다른 unit의 evidence가 첫 claim에 누출되지 않음(binding
      scope = synthesis unit 일치 확인)
- [ ] Case D — CW-01(prompt-echo skip)·CW-02(marker 제거) regression 없음
- [ ] Case E — RPV-05 질의 재실행, 검증 시점의 실제 EvidencePool 구성을
      다시 확인한 뒤 그 안의 multi-source 전부가 최종 claim/answer에
      보존되는지 확인(Fuller Vol.7 존재를 가정하지 않음, 위 CUE 주석 참고)
- [ ] 기존 단일-unit 사례(02/03a/03b/04/07/08a/08b) 회귀 없음 — 재실행해
      claim 개수·evidence_ids·valid 여부 동일한지
- [ ] `bind_claims()` 계약 불변 (evidence_ids ⊆ included_evidence_ids
      fail-closed 유지)
- [ ] 기존 P5 tests(`tests/test_grounded_claims.py` 등) 통과

CUE는 GREEN을 선언하지 않는다 — 검증 결과만 HQ에 제출한다.

## 현재 상태

**DRAFT — HQ 승인 대기.** 구현 착수 승인 전까지 C1/CUE 누구도 이 파일을
수정하지 않는다. 2026-09-28 HQ 1차 검토: 방향/범위 분리는 적절하나
binding-scope acceptance 기준과 Case A-E 회귀 조건 보강을 요구 — 본
개정판에 반영 완료. HQ가 (a) 이 개정판을 승인하여 구현 착수를 지시하거나,
(b) 다른 검증 경로를 택할지 결정한 후 다음 단계로 진행한다.
