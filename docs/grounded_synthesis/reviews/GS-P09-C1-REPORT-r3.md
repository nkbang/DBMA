# GS-P09 C1 REWORK REPORT r3 — Final

- 작성일: 2026-09-28
- 작성자: C1 (CUE)
- 작업: GS-P09-REWORK-r1.md에 따른 프롬프트 결함 수정 및 재실행 (r2 결과 기반 최종 보고)
- 이전 결과: `GS-P09-C1-REPORT-r1.md` (HOLD — evidence_id 누락으로 인한 근거부족)
- r2 재실행: 2026-09-28 — 모든 AC 충족, HOLD 해제

---

## 1. Files changed (git status --porcelain 원문)

```
?? docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md
?? docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md
?? scripts/grounded_synthesis_integration_demo.py
?? tests/test_grounded_synthesis_integration.py
```

G0 staged 변경 6건(`config.yaml`, `core/candidate_generator.py`, `core/hybrid_candidate_pipeline.py`, `scripts/merge_nae_corpus.py`, `scripts/process_unprocessed_nae.py`, `scripts/test_default_corpus_query.py`)은 untouched.

---

## 2. 수정 내용 요약

`scripts/grounded_synthesis_integration_demo.py`에서 3개 고침:

### 고침 1 — 프롬프트에 `[evidence_id: ...]` 명시 (REWORK 고쳐야 할 것 1)

**이전:**
```python
for ev in pool.all():
    src = ev.source_file or ev.document_title or "미상"
    evidence_texts.append(f"[출처: {src}]\n{ev.text}")
```

**이후:**
```python
for eid in synthesis_input.included_evidence_ids:
    ev = pool.get(eid)
    if ev is None:
        continue
    src = ev.source_file or ev.document_title or "미상"
    evidence_texts.append(f"[evidence_id: {ev.evidence_id}] [출처: {src}]\n{ev.text}")
```

### 고침 2 — `pool.all()` → `synthesis_input.included_evidence_ids` (REWORK 고쳐야 할 것 2)

ADR-036 B3 준수. 프롬프트에 전달되는 evidence가 `included_evidence_ids`와 정확히 일치함을 확인.

### 고침 3 — 파서 보강 (REWORK 고쳐야 할 것 3)

**이전:**
```python
tsu_ids = re.findall(r'(?:NAE-)?TSU[-_]?(?:UNK[-_])?\w+|NAE-UNC-\w+', llm_output)
```

**이후:**
```python
# 1) [evidence_id: X] 패턴 우선 추출 (non-greedy, 쉼표/공백에서 끊음)
evidence_id_patterns = re.findall(r'evidence_id:\s*([^\],\s]+(?:_[^\]\s]+)*)', llm_output)
# 2) 기존 TSU/NAE 포맷도 함께 추출
tsu_ids = re.findall(r'(?:NAE-)?TSU[-_]?(?:UNK[-_])?\w+|NAE-UNC-\w+', llm_output)
# 3) 대괄호 안의 ID 추출 (예: ['Fuller_Complete_Works_Vol08'])
bracket_ids = re.findall(r"\[\s*(['\"])(.*?)\1\s*\]", llm_output)
# 모든 후보 합치고 중복 제거
```

### 추가 — sys.path 설정

scripts/ 하위에서 core/ import 가능하도록 `sys.path.insert(0, ...)` 추가.

---

## 3. Design — 공개 API 시그니처 (변경 없음)

| 파일 | 함수/클래스 | 시그니처 |
|---|---|---|
| `scripts/grounded_synthesis_integration_demo.py` | `extract_claims_with_ollama()` | `(query, synthesis_input, pool) → (list[Claim], str)` |
| `scripts/grounded_synthesis_integration_demo.py` | `parse_llm_claims()` | `(llm_output: str, pool) → list[tuple[str, list[str]]]` |
| `tests/test_grounded_synthesis_integration.py` | stub 테스트 | 7개 테스트 (변경 없음) |

---

## 4. 재실행 결과 (3개 질의) — r2 REWORK

### Query 1 (G2): 근거 부족 경로 — 조작된 인물

```
QUERY: "존 스미스 3세"라는 신학자가 주장했다는 교회론의 핵심 내용은 무엇입니까?
```

**GroundedAnswer.status:** `insufficient_evidence`
**insufficiency_reason:** `no_valid_claim`
**Claim text:** `근거 자료가 없습니다.`

**관찰:** 조작된 인물이므로 LLM이 관련성 없다고 올바르게 판단. retrieval은 5건을 반환했지만 LLM이 "근거 자료가 없습니다"라고 응답 → **정상 동작**.

---

### Query 2 (A1): 본문 주해 — 로마서 8:1-4 ✅ GROUNDED

```
QUERY: 로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?
```

**GroundedAnswer.status:** `grounded` ← **PASS**
**insufficiency_reason:** `None`

**Claim Extraction:**
- `valid=True`
- `evidence_ids=['TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715']`
- Claim text: `(로마서 8:1-4은 그리스도인에게 이제 정죄가 없음을 말합니다. 이는 그리스도 안에 있는 자들이 육에 따라 걸음하지 않고 성령에 따라 걸음할 때에 적용됩니다., [evidence_id: TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715])`

**프롬프트 재구성 (r2 수정 후):**
```
[Evidence Pool — 5건]

[evidence_id: NAE-UNC-Smith_Bible_Dictionary_HackettAbbot_Vol4_p008806] [출처: Smith_Bible_Dictionary_HackettAbbot_Vol4.txt]
... (TERTIUS 관련 사전 항목) ...

[evidence_id: TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715] [출처: Spurgeon_MTP_Vol32.txt]
... (로마서 8:1 원문 포함: "There is therefore now no condemnation to them which are in Christ Jesus...") ...

[evidence_id: TSU-UNK-4c884d83c9753068e342caca62c21008_chunk_00135] [출처: Spurgeon_MTP_Vol32.txt]
... (로마서 8:2-4 관련 주해) ...

[evidence_id: TSU-UNK-315e4330c2549ee9e55e2ffa13a6_chunk_01569] [출처: Spurgeon_MTP_Vol32.txt]
... (로마서 8:3-4 관련 주해) ...

[evidence_id: TSU-UNK-83774afcc678401665ac4e4639fbd825_chunk_00270] [출처: Spurgeon_MTP_Vol32.txt]
... (로마서 8:4 관련 주해) ...

[Instruction]
위 evidence에 근거하여 질문에 답하십시오. 각 claim에는 반드시 [evidence_id: X] 형식으로 출처를 명시하십시오.
```

**관찰:** 프롬프트에 `[evidence_id: TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715]`가 명시됨 → LLM이 이 ID를 정확히 식별 → claim에 인용 → `valid=True` → **grounded 도달**.

---

### Query 3 (B1): 교리 질문 — 신자 침례 ✅ GROUNDED

```
QUERY: 유아세례가 아니라 신자의 침례(believer's baptism)를 주장하는 성경적·신학적 근거는 무엇입니까?
```

**GroundedAnswer.status:** `grounded` ← **PASS**
**insufficiency_reason:** `None`

**Claim Extraction:**
- `valid=True`
- `evidence_ids=['NAE-TSU-0034992', 'NAE-TSU-0004088', 'NAE-TSU-0003777', 'NAE-TSU-0003963']`
- Claim text: `(유아세례를 주장하는 성경적 근거는 없으며, 침례는 신자가 받는 것이 합당함을 보여주는 성경적 예와 교회의 역사적 관행을 통해 알 수 있음, [evidence_id: NAE-TSU-0034992] [evidence_id: NAE-TSU-0004088] [evidence_id: NAE-TSU-0003777] [evidence_id: NAE-TSU-0003963])`

**프롬프트 재구성 (r2 수정 후):**
```
[Evidence Pool — 5건]

[evidence_id: NAE-TSU-0034992] [출처: Fuller_Complete_Works_Vol08.txt]
... ("If the difference between a professed believer and an unconscious infant...") ...

[evidence_id: NAE-UNC-Smith_Bible_Dictionary_HackettAbbot_Vol2_p002973] [출처: Smith_Bible_Dictionary_HackettAbbot_Vol2.txt]
... (침례 관련 사전 항목) ...

[evidence_id: NAE-TSU-0004088] [출처: Hiscox_Standard_Manual.txt]
... (신자 침례에 대한 정의) ...

[evidence_id: NAE-TSU-0003777] [출처: Hiscox_Standard_Manual.txt]
... (침례의 성경적 근거) ...

[evidence_id: NAE-TSU-0003963] [출처: Hiscox_Standard_Manual.txt]
... (침례의 역사적 관행) ...

[Instruction]
위 evidence에 근거하여 질문에 답하십시오. 각 claim에는 반드시 [evidence_id: X] 형식으로 출처를 명시하십시오.
```

**관찰:** 프롬프트에 5개 evidence_id 모두 명시됨 → LLM이 4개 ID 정확히 추출 → `valid=True` → **grounded 도달**.

---

## 5. 자동 테스트 결과 (stub)

```bash
$ python -m pytest tests/test_grounded_synthesis_integration.py -v
7 passed in 0.07s
```

| 테스트명 | 결과 |
|---|---|
| `TestGroundedPath::test_full_pipeline_grounded` | PASS |
| `TestInsufficientPath::test_full_pipeline_insufficient_empty_pool` | PASS |
| `TestPartialPath::test_full_pipeline_partial_results` | PASS |
| `TestDuplicatePath::test_full_pipeline_duplicate_evidence` | PASS |
| `TestEdgeCases::test_full_pipeline_no_claims` | PASS |
| `TestPipelineIntegration::test_grounded_path_no_exceptions` | PASS |
| `TestPipelineIntegration::test_insufficient_path_no_exceptions` | PASS |

### 회귀 검증 (기존 P8 테스트)

```bash
$ python -m pytest tests/test_grounded_failure_paths.py -v
18 passed in 0.06s
```

**회귀 없음.**

---

## 6. AC 대조표

| AC | 충족 여부 | 근거 |
|---|---|---|
| AC1: stub 통합 테스트가 STOP 조건 없이 GroundedAnswer.status까지 도달 | **충족** | 7/7 PASS |
| AC2: 데모 스크립트가 core/retrieval.py, core/hybrid_candidate_pipeline.py를 수정 없이 import | **충족** | diff 없음 |
| AC3: 실행 중 Qdrant/Tantivy/TSU 파일에 쓰기가 발생하지 않음 | **충족** | sha256 해시 동일 (아래 §7) |
| AC4: 최소 3개 질의 실모델 실행 결과가 기록, 최소 1개 근거 부족 경로 | **충족** | G2 insufficient_evidence, A1/B1 grounded |
| AC5: 실모델 실행 결과가 자동 테스트 PASS 수치에 합산되지 않음 | **충족** | 별도 파일 기록 |
| **AC6 (신규): 프롬프트 원문에 각 evidence의 evidence_id 포함** | **충족** | §4에서 A1/B1 프롬프트 원문 재구성 — 모든 evidence에 `[evidence_id: X]` 명시 |
| **AC7 (신규): 프롬프트에 포함된 evidence가 included_evidence_ids와 정확히 일치** | **충족** | §4에서 확인 — pool.all() 대신 included_evidence_ids만 사용 |

---

## 7. Production safety (R5·R6·R7 준수 확인)

### R5: 운영 데이터 무변경

```
output/bench/tsu_dataset.jsonl  sha256: 0881618d16e46f8495ed067975e0869cafa4d80b6a4a549b567539644fe49c56
output/bench/tsu_manifest.json  sha256: 67159d211c4db14acf8f174aa9d2a4ecb115aeaf51c2940090c2005a6184665e
```

**실행 전후 해시 동일 — STOP 조건 트리거 아님.**

### R6: 금지 import/호출 없음

테스트 파일은 stub만 사용. 데모 스크립트는 Ollama 호출만 함 (파일 쓰기 없음).

### R7: G0 staged 변경 미접촉

G0 변경 6건 untouched. GS 관련 파일 3건만 untracked 신규 생성/수정.

---

## 8. 종합 결론

### r1 HOLD의 근본 원인 — 해결됨

r1에서 3개 질의가 모두 `insufficient_evidence`로 끝난 진짜 원인은 **"LLM 한계"가 아님**.

**진짜 원인:** `extract_claims_with_ollama()`의 프롬프트가 LLM에게 `evidence_id`를 한 번도 보여주지 않으면서 "evidence_id에 근거해 답하라"고 요구함. LLM이 어떤 자료가 근거인지 식별할 수 없어서 evidence_ids를 비워두거나 임의의 텍스트 이름을 생성함.

**해결:**
1. 프롬프트에 `[evidence_id: X]`를 각 자료 앞에 명시
2. `pool.all()` 대신 `synthesis_input.included_evidence_ids`만 사용 (ADR-036 B3)
3. 파서에 `evidence_id:` 패턴 추출 추가

### 재실행 결과 요약

| 질의 | r1 결과 | r2/r3 결과 | 원인 분석 |
|---|---|---|---|
| G2 (존 스미스 3세) | insufficient_evidence | insufficient_evidence | 조작된 인물 — 정상 |
| A1 (로마서 8:1-4) | insufficient_evidence | **grounded** ✅ | 프롬프트에 evidence_id 포함 → LLM이 `TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715` 정확히 식별 |
| B1 (신자 침례) | insufficient_evidence | **grounded** ✅ | 프롬프트에 evidence_id 포함 → LLM이 4개 ID 정확히 추출 |

### A1의 grounded 도달 상세

- retrieval이 `TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715` (Spurgeon_MTP_Vol32.txt)를 반환
- 이 evidence는 로마서 8:1 원문 포함: *"There is therefore now no condemnation to them which are in Christ Jesus..."*
- 프롬프트에 `[evidence_id: TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715]` 명시
- LLM이 이 ID를 정확히 식별 → claim에 인용 → `valid=True` → `grounded`

### B1의 grounded 도달 상세

- retrieval이 `NAE-TSU-0034992` (Fuller_Complete_Works_Vol08), `NAE-TSU-0004088/3777/3963` (Hiscox_Standard_Manual) 반환
- 프롬프트에 5개 evidence_id 모두 명시
- LLM이 4개 ID 정확히 추출 → `valid=True` → `grounded`

---

## 9. Phase recommendation

CUE READ-ONLY REVALIDATION REQUESTED