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

## 목표 (제안, HQ 확정 필요)

1. LLM raw output이 여러 문단(복수 claim)으로 구성된 경우, **문단별로 개별
   claim을 생성**하고 각 claim에는 **해당 문단에 실제로 등장한 evidence_id만**
   바인딩한다 (전역 스캔 방식 폐기, 문단 단위 로컬 스캔으로 전환).
2. 기존 단일-claim 사례(문단이 1개뿐인 출력)는 현재 동작과 동일하게 유지 —
   회귀 없음.
3. CW-01(prompt-echo skip)·CW-02(marker 제거)의 계약은 문단 단위 파싱으로
   확장될 때도 그대로 유지한다 — 각 문단 처리 시 동일하게 적용.
4. `core/grounded_claims.py::bind_claims()`의 `evidence_ids ⊆
   included_evidence_ids` fail-closed 계약은 변경하지 않는다.

**주의 — CUE는 구체적 구현 방식(정규식 재설계 vs. 문단 분할 전처리 vs. 다른
접근)을 지시하지 않는다.** 이는 C1이 제안하고 CUE가 검증하는 통상 절차를
따른다. 위 목표(1)의 "문단 단위 파싱"이 유일한 해법이라고 CUE가 단정하지도
않는다 — HQ가 다른 검증 경로(예: C-03처럼 정책 결정으로 우회)를 택할 수도
있다는 점을 인지하고 있다.

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

- [ ] 문단별 claim 분리가 실제로 동작하는가 (RPV-05 질의 재실행,
      야고보서 문단이 별도 claim으로 나오는지)
- [ ] 각 claim의 evidence_ids가 해당 문단에 실제 등장한 것만으로
      한정되는가 (전역 오염 없는지)
- [ ] CW-01(prompt-echo skip)이 문단 단위 파싱에서도 여전히 동작하는가
- [ ] CW-02(marker 제거)가 문단 단위 파싱에서도 여전히 동작하는가
- [ ] 기존 단일-문단 사례(02/03a/03b/04/07/08a/08b) 회귀 없음 — 재실행해
      claim 개수·evidence_ids·valid 여부 동일한지
- [ ] `bind_claims()` 계약 불변 (evidence_ids ⊆ included_evidence_ids
      fail-closed 유지)
- [ ] 기존 P5 tests(`tests/test_grounded_claims.py` 등) 통과

CUE는 GREEN을 선언하지 않는다 — 검증 결과만 HQ에 제출한다.

## 현재 상태

**DRAFT — HQ 승인 대기.** 구현 착수 승인 전까지 C1/CUE 누구도 이 파일을
수정하지 않는다. HQ가 (a) 이 WO를 승인하여 구현 착수를 지시하거나,
(b) 다른 검증 경로(예: 문단 단위 파싱 대신 다른 접근, 혹은 corrective
WO 없이 관찰만 기록)를 택할지 결정한 후 다음 단계로 진행한다.
