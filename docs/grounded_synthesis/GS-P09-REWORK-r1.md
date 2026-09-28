# REWORK WORK ORDER — Phase 9 (r2)

- 사유: `extract_claims_with_ollama()`의 프롬프트가 LLM에게 `evidence_id`를
  한 번도 보여주지 않으면서 "evidence_id에 근거해 답하라"고 요구함 — 3개
  질의 전부가 근거부족으로 끝난 근본 원인. 상세:
  `docs/grounded_synthesis/reviews/GS-P09-CUE-REVIEW-r1.md`
- 대상은 `scripts/grounded_synthesis_integration_demo.py`와
  `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md` 재실행 결과뿐이다.
  `tests/test_grounded_synthesis_integration.py`(stub, 7/7 PASS)는 문제없으니
  손대지 마라.

## 고쳐야 할 것 1 — 프롬프트에 evidence_id 명시

`extract_claims_with_ollama()`의 컨텍스트 블록 구성을 바꿔라:

```python
evidence_texts = []
for ev in pool.all():
    src = ev.source_file or ev.document_title or "미상"
    evidence_texts.append(f"[evidence_id: {ev.evidence_id}] [출처: {src}]\n{ev.text}")
```

그리고 프롬프트 지시문에 evidence_id를 그대로 복사해서 쓰라고 명시해라:

```python
prompt = (
    "다음 자료들을 읽고 질문에 대한 주장을 추출하세요.\n"
    "각 자료 앞에는 [evidence_id: ...] 표시가 있습니다. 주장의 근거로 삼은 자료의\n"
    "evidence_id를 대괄호 안의 값 그대로(수정하지 말고) 인용하세요.\n\n"
    f"자료:\n{context_block}\n\n"
    f"질문: {query}\n\n"
    "출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.\n"
    "evidence_ids는 위에서 본 [evidence_id: ...] 값을 그대로 써야 합니다.\n"
    "자료가 없으면: (근거 자료 없음, [])\n"
)
```

## 고쳐야 할 것 2 — pool.all() 대신 included_evidence_ids만 사용

ADR-036 B3(합성 입력 경계) 준수를 위해, 프롬프트에는 `pool.all()`이 아니라
`synthesis_input.included_evidence_ids`에 해당하는 Evidence만 넣어라:

```python
evidence_texts = []
for eid in synthesis_input.included_evidence_ids:
    ev = pool.get(eid)
    if ev is None:
        continue
    src = ev.source_file or ev.document_title or "미상"
    evidence_texts.append(f"[evidence_id: {ev.evidence_id}] [출처: {src}]\n{ev.text}")
```

## 고쳐야 할 것 3 — 파서 보강(선택, 권장)

`parse_llm_claims()`의 정규식이 실제 evidence_id 포맷(`NAE-TSU-...`,
`TSU-UNK-..._chunk_...`, `NAE-UNC-..._p...` 등)을 넓게 커버하는지 다시 확인해라.
프롬프트가 evidence_id를 직접 보여주므로, LLM이 대괄호 표기(`[evidence_id: X]`)
그대로 출력할 가능성이 높다 — `re.findall(r'evidence_id:\s*([^\]]+)', llm_output)`
같은 패턴도 함께 시도하도록 보강해도 좋다(필수는 아님, 최선을 다해 파싱되면 된다).

## 재실행

수정 후 동일한 3개 질의(G2, A1, B1)를 다시 실행하고
`GS-P09-REAL-MODEL-RUN-RESULTS.md`를 새로 작성해라(덮어써도 된다 — 이전
결과가 결함 있는 프롬프트로 나온 것이므로 폐기). 이번엔 다음을 시도해라:
- 최소 1개는 여전히 근거부족 경로(G2 그대로 사용 가능 — 조작된 인물이므로
  프롬프트를 고쳐도 정당하게 insufficient가 나와야 정상이다)
- A1/B1 중 최소 1개는 **grounded 경로에 도달하는지** 확인해라. 만약 프롬프트를
  고쳤는데도 둘 다 여전히 insufficient가 나오면, 그건 실제 코퍼스/검색 한계일
  수 있다 — 이번엔 그 경우 "왜 그런지"(retrieval이 실제로 관련 있는 자료를
  못 찾았는지, LLM이 evidence_id를 보고도 인용을 안 했는지)를 `[evidence_id: ...]`가
  포함된 실제 프롬프트 원문 일부와 함께 보고서에 기록해라 — 이번엔 근거
  없이 "LLM 한계"라고만 적지 마라.

## Acceptance Criteria (추가)

- AC6(신규): 프롬프트 원문(코드가 아니라 실제로 Ollama에 전달된 문자열)에
  각 evidence의 `evidence_id`가 포함됨을 재실행 결과 보고서에 원문 일부로 증명.
- AC7(신규): 프롬프트에 포함된 evidence가 `synthesis_input.included_evidence_ids`와
  정확히 일치함(전체 `pool.all()`이 아님).

## 보고

이전과 동일 양식. 보고서 파일명 `GS-P09-C1-REPORT-r2`로 새로 작성. 마지막
줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.
