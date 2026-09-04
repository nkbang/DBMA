# Phase 1 — Bottleneck Analysis (Evidence-Based)

- analyzed_at: 2026-08-16T21:30:00Z
- baseline_source: .automation/evidence/night-shift/corpus-factory-transition/PHASE0-VOL01-BASELINE.md
- 이 문서는 NAE Corpus Factory 전환의 병목 분석 결과다.

## Vol.1 Production Baseline Summary

| 항목 | 값 |
|---|---|
| Total candidates | 5452 |
| TSU generated (is_claim=true) | 3643 (66.8%) |
| Skipped (is_claim=false) | 1808 (33.2%) |
| Failed (LLM error) | 1 |
| Total time | 57727s (16.04h) |
| Avg latency/candidate | 10.59s |
| Throughput | 340.0/hour |
| GPU utilization | ~99% (llama-server -np 1) |
| Model | my-theology-bot-v2:latest (70.6B, 53GB) |

## Q1. 전체 처리시간 중 LLM inference 비율은?

→ Baseline에 LLM-only time 별도 기록 없음.
→ 그러나 GPU ~99% utilization + avg_latency 10.59s에서
   LLM inference가 처리시간의 95% 이상을 차지하는 것으로 추정.
→ 나머지 5% 미만: state I/O, JSON parse, metadata merge 등

## Q2. candidate filtering으로 제거 가능한 비율은?

→ is_claim=false로 skipped: 1808/5452 = 33.2%
→ 이 33.2%는 LLM 호출 후 '아니오' 판정 — LLM 호출 전 filtering 가능
→ deterministic filtering으로 이 비율을 LLM 호출 전에 제거 가능

## Q3. 동일/중복 candidate가 존재하는가?

→ baseline: duplicate claim text = 15건, duplicate source_text = 1건
→ 전체 5452 중 16건 (0.29%) — 미미한 수준

## Q4. deterministic filtering이 가능한 유형은?

→ baseline에 '명백한 비신학적 구조물' 별도 기록 없음
→ 그러나 is_claim=false 1808건 중 일부는:
   - page number/header/footer (OCR artifact)
   - 지나치게 짧은 fragment
   - 반복 boilerplate
   - 명백한 비신학적 구조물
→ 이 유형들을 rule로 먼저 걸러내면 LLM 호출 감소 가능

## Q5. GPU가 실제 병목인가?

→ YES. GPU ~99% utilization, llama-server -np 1 고정
→ model이 53GB로 GPU에 100% 상주 — unload/reload 불가
→ 병렬화 실험은 baseline 확보 후 CUE 승인 필요 (§13)

## Q6. CPU/RAM/I/O가 병목인가?

→ RAM: 총 128GB 중 83% 사용 — 여유 있음
→ I/O: state.json read/write는 경량 — 병목 아님
→ CPU: GPU 대기 중 idle — 병목 아님

## Q7. n8n orchestration overhead가 존재하는가?

→ 해당 없음. TSU 생성은 n8n을 거치지 않음 (명시적 확인)

## Q8. Review가 전체 TSU를 막는 병목이 될 가능성은?

→ baseline: review_status = {'generated': 3643}
→ 현재 Human Review 단계로 넘어가지 않음 — 병목 아님
→ 그러나 향후 scale-up 시 Q4 (Confidence-based Review) 병목 가능성

## Q9. Embedding/Qdrant가 TSU extraction보다 빠른가?

→ baseline에 Embedding/Qdrant 시간 미포함 (Vol.1은 TSU Extraction만)
→ Qdrant point count = 3319 (baseline 유지)

## Q10. 각 단계가 독립 queue로 분리될 필요가 있는가?

→ YES. 현재 단일 worker pipeline이 병목:
   - TSU Extraction이 느리면 Embedding 대기
   - 한 source 실패 시 전체 중단
→ Phase 3에서 독립 queue worker로 분리 필요 (§5)

## Phase 1 결론

1차 병목: GPU (llama-server -np 1, model 53GB 상주)
2차 병목: LLM inference time (candidate당 10.59s 중 ~95%+)
3차 병목: 단일 worker pipeline (동시 처리 불가)

개선 기회:
  A. LLM 호출 전 deterministic filtering (33.2% is_claim=false 제거)
  B. 독립 queue worker로 pipeline 분리 (Phase 3)
  C. GPU 병렬화 실험 (CUE 승인 후, §13)
