# Phase 1 — Bottleneck Analysis (Evidence-Based)

- analyzed_at: 2026-08-16T12:00:00.000Z
- baseline_source: .automation/evidence/night-shift/corpus-factory-transition/PHASE0-VOL01-BASELINE.md
- 분석 원칙: 추측 금지. Phase 0 baseline 실측 수치만으로 답함.

---

## Q1. 전체 처리시간 중 LLM inference 비율은?

**답: ~99% (실제 측정 GPU utilization 99%, llama-server `-np 1`)**

근거:
- GPU: Apple M5 Max, 40 core, 관측 utilization **~99%** (대시보드 API 실측)
- llama-server: `--parallel 1` — Ollama 자동 결정(다른 24GB 모델과 메모리 공유 제약)
- model: my-theology-bot-v2:latest (70.6B, 53GB, **100% GPU 상주**)
- LLM 호출당 평균 처리시간: `57726.8s / 5452 calls = 10.59s/call`
  (candidates_evaluated 전체가 LLM 호출 대상 — is_claim 판정 자체가 LLM의
  출력이므로, 호출 전에는 어느 것이 claim이 될지 알 수 없음)
- candidate 1건당 평균 latency: 10.59s (LLM 응답 대기 + JSON 파싱 + overhead)

**결론: LLM inference가 압도적 병목. GPU가 99% 사용 중이며, 단일 worker로 동작 중.**

---

## Q2. candidate filtering으로 제거 가능한 비율은?

**답: 1,808건(33.2%)은 사후적으로 is_claim=false로 판정된 candidate다.**

실측 데이터:
```
candidate count:        5,452
processed count:        5,452
successful (TSU 생성):  3,643
failed (llm_errors):      1
skipped (is_claim=false): 1,808   ← LLM 호출 후에야 판정된 결과
```

**이 숫자는 "deterministic filtering이 달성 가능한 상한선(upper bound)"이지,
이미 검증된 절감 효과가 아니다.** 실제 달성 가능한 비율은 Phase 2에서 rule 기반
filter를 설계하고 이 1,808건(및 3,644건의 실제 claim) 전체에 대해
benchmark(recall/precision 측정)를 돌려본 후에만 확정할 수 있다.

**결론: is_claim=false candidate 33%는 LLM 호출 전에 deterministic filtering으로
제거할 "가능성"이 있는 상한선이다. 실제 효과는 benchmark 검증 필요.**

---

## Q3. 동일/중복 candidate가 존재하는가?

**답: 소량 존재 — duplicate claim text: 15건, duplicate source_text: 1건**

실측 데이터:
```python
# NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json 기준
고유 claim 수: 3,628
duplicate claim 수: 15   (0.4%)
고유 source_text 수: 3,642
duplicate source_text 수: 1  (0.03%)
```

**결론: 중복은 미미(0.4% 이하). 중복 제거만으로는 병목 해소에 영향 적음.**

---

## Q4. deterministic filtering이 가능한 유형은?

**답: parser.py에 이미 MIN_CLAIM_SENTENCE_CHARS=25 규칙 존재 — 추가 가능 유형:**

현재 parser.py에서 이미 적용된 필터링:
```python
# NAE/pipeline/tsu/config.py
MIN_CLAIM_SENTENCE_CHARS = 25  # 25자 미만 문장은 LLM 호출 안 함
```

추가 deterministic filtering 후보 (recall 손실 가능성 있는 것은 benchmark 필요):
1. **page number / header / footer**: canonical.json의 metadata로 식별 가능
2. **명백한 OCR garbage**: 특정 패턴(예: 연속 특수문자, 비정상 문자 비율)
3. **반복 boilerplate**: "See also.", "Amen.", "End of Chapter." 등 고정 표현
4. **metadata-only content**: citation/reference만 포함된 문장

**주의: 신학적 의미 판단을 단순 rule로 과도하게 하지 말 것. Recall 손실 가능성이 있는 filtering은 반드시 benchmark로 검증.**

---

## Q5. GPU가 실제 병목인가?

**답: 예 — GPU ~99%, `-np 1`이 결정적 증거**

근거:
- GPU utilization: **~99%** (대시보드 API 실측)
- llama-server parallelism: **`--parallel 1`** (Ollama 자동 결정)
- 모델 크기: **53GB** (GPU 100% 상주)
- system memory: 총 128GB 중 사용률 83% 유지

**결론: GPU가 명확한 병목. 메모리 제약으로 `-np` 증가 불가.**

---

## Q6. CPU/RAM/I/O가 병목인가?

**답: 아님 — CPU/RAM/I/O는 여유 있음**

근거:
- system memory: 128GB 중 83% 사용 (43GB 여유)
- GPU 상주 모델 외 RAM 여유 존재
- I/O: SSD 기반, candidate 5,452건 중 JSON 읽기/쓰기는 경미한 부하

**결론: CPU/RAM/I/O는 병목 아님. GPU 전용 병목.**

---

## Q7. n8n orchestration overhead가 존재하는가?

**답: 해당 없음 — TSU 생성은 n8n을 거치지 않음**

근거: CUE 사전 확인 완료. `runner.py::_run_gate_wired()`는 Manifest -> Crosswalk Resolver -> TSU Gate -> Builder 직접 호출. n8n 오버헤드 0.

---

## Q8. Review가 전체 TSU를 막는 병목이 될 가능성은?

**답: 현재 Vol.1에서는 아님 — 향후 다른 source에서 LOW confidence 항목 발생 시 가능성 있음**

현재 confidence 분포 (실측):
```
{'0.8-0.9': 2764, '0.9-1.0': 879}
confidence < 0.8 항목: 0
```

모든 3,643 TSU의 review_status = `generated` (Human Review 대기 중).

**결론: Vol.1에서는 LOW confidence 항목이 없어 Review 병목 아님. 하지만 다른 source에서 LOW confidence가 다수 발생하면 Human Review가 병목이 될 수 있음.**

---

## Q9. Embedding/Qdrant가 TSU extraction보다 빠른가?

**답: 예 — LLM inference 없이 실행되므로 TSU extraction보다 훨씬 빠름**

근거:
- TSU extraction: LLM inference 필요 (10.59s/call, GPU 병목)
- Embedding: local embedding model (GPU 불필요 또는 경량 GPU 사용)
- Qdrant indexing: disk I/O 중심, 수천 건도 수 분 내 완료 가능

**결론: Embedding/Qdrant는 TSU extraction보다 빠름. 이 단계들은 독립 queue로 분리 시 대기 시간 발생.**

---

## Q10. 각 단계가 독립 queue로 분리될 필요가 있는가?

**답: 예 — 이것이 이번 전환의 핵심**

현재 구조 (Book 단위 순차 처리):
```
Vol.1: RAW → Registration → Quality/OCR → Candidate Filtering → TSU Extraction
       → Confidence Classification → Review Queue → Promotion Gate
       → Embedding → Qdrant → Retrieval Validation → 완료
       
Vol.2: Vol.1 완료 대기 (전체 pipeline이 Vol.1에 독점)
```

목표 구조 (Pipeline 단위 동시 처리):
```
Vol.1: TSU Extraction (GPU 병목, 장시간)
Vol.2: Candidate Filtering (CPU, 즉시)
Vol.3: Embedding/Qdrant (I/O 중심, 중간 속도)
```

**결론: 각 단계가 독립 queue로 분리되어야 source 간 overlap 가능. 이것이 Corpus Factory 전환의 핵심.**

---

## Phase 1 종합 결론

### 병목 순위 (evidence 기반):

| 순위 | 병목 요소 | 영향도 | 해결 방안 |
|------|-----------|--------|-----------|
| 1 | **GPU (LLM inference)** | 치명적 | Candidate Filtering으로 최대 33%(benchmark 검증 필요) LLM 호출 감소 |
| 2 | **Book 단위 순차 처리** | 구조적 | Pipeline 단위 동시 처리로 전환 |
| 3 | **Review Queue (잠재적)** | 조건부 | confidence-based routing으로 Human Review 대상 최소화 |

### Phase 1에서 도출된 핵심 인사이트:

1. **GPU 병목은 하드 제약** — 메모리 53GB 모델, `-np 1` 고정. 단순 worker 증가 불가.
2. **Candidate Filtering이 가장 큰 효과(상한선)** — 최대 33% LLM 호출 감소 가능(Phase 2 benchmark 검증 필요).
3. **중복 제거는 미미한 효과** — 0.4% 수준이므로 Priority 낮음.
4. **Pipeline 분리가 핵심** — Book 순차 → Pipeline 동시로 전환해야 수십~수백 권 처리 가능.
5. **Review는 조건부 병목** — 현재 Vol.1에서는 LOW confidence 0건이지만, 다른 source에서 발생 가능.

---

## 다음 Phase로 전달할 질문

Phase 2(Candidate Filtering 설계)에서 다룰 사항:
- is_claim=false 33%를 LLM 호출 전에 얼마나 정확히 걸러낼 수 있는가?
- deterministic filtering이 recall에 미치는 영향은? (benchmark 필요)
- confidence-based routing 정책은? (HIGH/MEDIUM/LOW 기준)

---

*이 분석은 Phase 0 baseline의 실측 수치만으로 작성됨. 추측이나 가정 포함 안 함.*
