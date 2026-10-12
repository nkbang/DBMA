# GS-P09 Real-Model Run Results — r2 REWORK 재실행

- 실행일: 2026-09-28 (r2 REWORK 재실행)
- 모델: `my-theology-bot-v2:latest` (Ollama, DEFAULT_GEN_MODEL)
- 실행 스크립트: `scripts/grounded_synthesis_integration_demo.py` (수정 후 재실행)
- 이전 결과: `GS-P09-C1-REPORT-r1.md` (HOLD — evidence_id 누락으로 인한 근거부족)
- 이 결과는 자동 테스트 PASS 수치에 합산되지 않음 (별도 파일, 별도 섹션)

---

## Query 1 (G2): 근거 부족 경로 — 조작된 인물

```
QUERY: "존 스미스 3세"라는 신학자가 주장했다는 교회론의 핵심 내용은 무엇입니까?
```

**GroundedAnswer.status:** `insufficient_evidence`
**insufficiency_reason:** `no_valid_claim`
**Claim text:** `근거 자료가 없습니다.`

**관찰:** 조작된 인물이므로 LLM이 관련성 없다고 올바르게 판단. retrieval은 5건을 반환했지만 LLM이 "근거 자료가 없습니다"라고 응답 → **정상 동작**.

---

## Query 2 (A1): 본문 주해 — 로마서 8:1-4 ✅ GROUNDED

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

## Query 3 (B1): 교리 질문 — 신자 침례 ✅ GROUNDED

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

## 자동 테스트 결과 (stub)

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

## 종합 관찰 (r2 재실행)

1. **파이프라인 전체 정상 작동**: P1→P7까지 모든 단계가 예외 없이 통과.
2. **G2 (조작된 인물)**: LLM이 "근거 자료 없음"을 올바르게 식별 → `insufficient_evidence` 경로 확인.
3. **A1 (로마서 8:1-4)**: 프롬프트에 `[evidence_id: X]` 포함 → LLM이 `TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715` 정확히 식별 → **grounded** ✅
4. **B1 (신자 침례)**: 프롬프트에 5개 evidence_id 모두 명시 → LLM이 4개 ID 정확히 추출 → **grounded** ✅
5. **운영 데이터 무변경**: 실행 전후 sha256 해시 동일 확인.
6. **실모델 실행 결과는 별도 파일에 기록** (이 문서) — 자동 테스트 PASS 수치와 절대 합산하지 않음.

---

## r1 → r2 비교 요약

| 질의 | r1 결과 | r2 결과 | 원인 분석 |
|---|---|---|---|
| G2 (존 스미스 3세) | insufficient_evidence | insufficient_evidence | 조작된 인물 — 정상 |
| A1 (로마서 8:1-4) | insufficient_evidence | **grounded** ✅ | 프롬프트에 evidence_id 포함 → LLM이 정확히 식별 |
| B1 (신자 침례) | insufficient_evidence | **grounded** ✅ | 프롬프트에 evidence_id 포함 → LLM이 4개 ID 정확히 추출 |

**r1 HOLD의 근본 원인 — 해결됨:** `extract_claims_with_ollama()`의 프롬프트가 LLM에게 `evidence_id`를 한 번도 보여주지 않으면서 "evidence_id에 근거해 답하라"고 요구함. LLM이 어떤 자료가 근거인지 식별할 수 없어서 evidence_ids를 비워두거나 임의의 텍스트 이름을 생성함.

**r2 해결책:**
1. 프롬프트에 `[evidence_id: X]`를 각 자료 앞에 명시
2. `pool.all()` 대신 `synthesis_input.included_evidence_ids`만 사용 (ADR-036 B3)
3. 파서에 `evidence_id:` 패턴 추출 추가
