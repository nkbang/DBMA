# CW-01 / CW-02 Corrective WO — 범위 고정 (HQ 승인, 미구현)

- 작성: CUE, 2026-09-28. HQ가 승인한 corrective WO 2건의 범위를 코드
  레벨로 고정한다. **이 문서는 구현하지 않는다** — C1 착수는 HQ의
  별도 "corrective implementation 승인" 이후.

---

## CW-01 — P5 Claim Extraction / Parsing 수정

### 결함 위치 (CUE가 코드로 직접 확인)

`scripts/grounded_synthesis_integration_demo.py`:
- `extract_claims_with_ollama()` (72번째 줄) — 프롬프트 구성 및 Ollama 호출
- `parse_llm_claims()` (121번째 줄) — **버그의 정확한 위치**

### 근본 원인 (raw 데이터로 확인됨, `output/bench/rpv_real_03a.json`,
`rpv_real_04.json`)

`parse_llm_claims()` 152-155번째 줄:
```python
# 첫 줄을 claim text로 사용
first_line = llm_output.strip().split("\n")[0]
if len(first_line) >= 5 and unique_ids:
    raw_claims.append((first_line, unique_ids))
```
LLM 출력의 **첫 줄을 무조건 claim text로 취급**한다 — 그 줄이 실제
claim인지, 프롬프트 지시문을 되풀이한 것인지 구분하지 않는다.
동시에 135번째 줄의 evidence_id 정규식(`re.findall(r'evidence_id:\s*...')`)은
`llm_output` **전체**에서 매칭하므로, 첫 줄이 지시문이어도 다른 곳에서
그럴듯한 evidence_id를 주워 담아 "형태는 claim처럼 보이지만 내용은
지시문"인 레코드가 만들어진다.

실측: RPV-03a·04 둘 다 `claim.text ==
"(evidence_ids는 위에서 본 [evidence_id: ...] 값을 그대로 써야 합니다.)"`
— 프롬프트 94-103번째 줄의 지시문 텍스트와 정확히 일치.

### 목표 (HQ 지시 그대로)

1. 프롬프트 지시문이 Claim으로 추출되지 않음
2. `evidence_ids` instruction이 Claim text에 혼입되지 않음
3. invalid Claim은 기존 fail-closed 경로 유지(`core/grounded_claims.py::bind_claims()`,
   `evidence_ids ⊄ included_evidence_ids`면 `valid=False` — **이 계약은
   그대로 둔다**)
4. `core/grounded_claims.py`(P5 core 모듈)는 건드리지 않는다 — 버그는
   참조 구현 스크립트의 LLM 출력 파싱 로직에 있지, P5 core의
   `bind_claims()` 자체에는 없음(이번 9건 전부 `bind_claims()`는
   정확하게 evidence_ids ⊆ included_evidence_ids를 판정했음 — CUE 확인).

### 허용 파일

`scripts/grounded_synthesis_integration_demo.py`의 `parse_llm_claims()`,
`extract_claims_with_ollama()`만. (필요시 이 스크립트가 참조하는 프롬프트
템플릿 문자열도 포함 가능 — 단, 출력 형식 지시를 바꾸는 것과 파싱 로직을
바꾸는 것 중 최소 변경 쪽을 우선한다.)

### 금지 파일

`core/grounded_claims.py`, `core/grounded_answer.py`,
`core/grounded_citation.py`, `core/grounded_synthesis_input.py`,
`core/evidence_*.py` — P4~P7 core 계약 변경 금지.

---

## CW-02 — Final Answer Prompt Artifact 제거

### 결함 위치 (CUE가 코드로 직접 확인)

`output/bench/rpv_real_03b.json`의 `grounded_answer.text_preview`:
```
"(침례교 신앙고백에서 성찬은... 전제조건으로 간주됩니다.,
 [evidence_id: NAE-TSU-0003698, evidence_id: NAE-TSU-0003462])"
```
`[evidence_id: ...]` 태그가 `Claim.text`(LLM 원출력)에 그대로 포함된
채로 `GroundedAnswer.text`(사용자 노출 텍스트)까지 전파됨.
`core/grounded_answer.py::assemble_grounded_answer()`가 `claim.text`를
그대로 이어붙여 `GroundedAnswer.text`를 만들기 때문 — claim text 자체에
포맷 아티팩트가 섞여 들어오면 정제 없이 통과한다.

### 목표 (HQ 지시 그대로)

1. `[evidence_id: ...]`, 내부 parser marker, prompt instruction, 기타
   내부 grounding protocol이 사용자-facing answer에 노출되지 않음
2. 내부 Evidence binding과 provenance는 그대로 보존 — 즉 **정제는
   표시용 텍스트에만 적용**하고, `Claim.evidence_ids`나 P7
   `citation_check`가 참조하는 원본 claim text 자체를 손상시키지 않는다
   (원본은 내부적으로 보존, 표시본만 별도로 정제하는 방식을 권장 —
   단 구체적 구현 방식은 C1이 CW-01/CW-02 구현 시 제안하고 CUE가 검증)

### 허용 파일

CW-01과 같은 범위(`scripts/grounded_synthesis_integration_demo.py`) 우선
검토. 만약 이 정제 로직이 참조 스크립트가 아니라 향후 실제 운영 경로에
공통으로 필요하다고 판단되면, 그 결정 자체를 HQ에 먼저 보고 — 이번 CW-02
범위를 core 모듈로 확장할지는 CUE가 임의로 정하지 않는다.

---

## 공통 금지 사항 (HQ §5 그대로, 재확인)

RetrievalEngine 재작성, CandidateGenerator 재작성, ranking 변경,
candidate_k 변경, corpus 변경, TSU dataset 변경, 재인덱싱, Qdrant 변경,
Tantivy 변경, 새 retrieval engine 도입, 새 corpus 추가, UI 전면 개편,
LLM provider 변경, GS architecture 확장 — 전부 금지. 범위는 P5/P6/P7
경계와 사용자 출력 정제로 한정.

## 현재 상태

**범위만 고정됨. 구현 미착수.** HQ의 "corrective implementation 승인" 이후
C1에게 전달한다.
