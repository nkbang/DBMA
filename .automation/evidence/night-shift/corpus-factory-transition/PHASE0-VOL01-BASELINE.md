# Phase 0 — Vol.1 (Fuller_Complete_Works_Vol01) Baseline

- captured_at: 2026-08-16T11:46:50.000Z
- 이 문서는 NAE Corpus Factory 전환의 영구 비교 기준(baseline)이다. 이후
  최적화 결과는 전부 이 수치와 대조한다.

## Processing

| 항목 | 값 |
|---|---|
| source_id | BAP-MISS-FULLER-VOL01 |
| volume | Fuller_Complete_Works_Vol01 |
| candidate count | 5452 |
| processed count | 5452 |
| successful count (TSU 생성) | 3643 |
| failed count (llm_errors) | 1 |
| skipped count (is_claim=false) | 1808 |
| total processing time | 57726.8s (16.04h) |
| average candidate latency | 10.59s |
| throughput/hour (누적 평균 기준) | 340.0/h |
| peak throughput (시간당 감시 샘플 관측 범위) | 약 300-400/h (정밀 peak 미추적 — 시간당 스냅샷 기반 근사치) |
| ETA 정확도 | 최초 예측 ~20.8h(C1, 100건 샘플) vs 최종 실측 16.0h — 초기 샘플이 후반보다 느려 과대추정됨 |

## TSU

| 항목 | 값 |
|---|---|
| generated TSU count | 3643 |
| rejected candidate count (is_claim=false) | 1808 |
| confidence distribution | {'0.8-0.9': 2764, '0.9-1.0': 879} |
| extraction failure count (llm_errors) | 1 |
| malformed output count | claim.py의 JSON parse 실패는 llm_errors에 합산되어 별도 집계 불가(현재 0이므로 무관) |
| duplicate claim text count | 15 |
| duplicate source_text count | 1 |
| doctrine breakdown | {'Soteriology': 2314, 'Scripture / Authority': 73, 'Sanctification': 279, 'Justification': 271, 'Providence': 204, 'Election': 165, 'Trinity': 21, 'Ecclesiology': 98, 'Eschatology': 61, 'Other': 10, 'Baptism': 9, 'Confession': 2} |
| review_status breakdown | {'generated': 3643} |

## System (baseline 조건)

- GPU: Apple M5 Max, 40 core, 관측 utilization ~99% (대시보드 API 실측)
- llama-server: `--parallel 1` (`-np 1`) — Ollama 자동 결정(다른 24GB 모델과
  메모리 공유로 인한 제약, CUE 앞선 조사에서 확인)
- model: my-theology-bot-v2:latest (70.6B, 53GB, 100% GPU 상주)
- system memory: 총 128GB 중 사용률 83% 내외로 실행 내내 유지(대시보드 관측)

## Integrity

| 항목 | 값 |
|---|---|
| registration_state.json 항목 수 | 10 |
| registration_state QUALITY_PASSED 수 | 10 |
| NAE/corpus/tsu/ git status | M NAE/corpus/tsu/tsu_id_state.json
?? NAE/corpus/tsu/Fuller_Complete_Works_Vol01/ |
| production boundary git diff (core/retrieval.py, tsu/, ingest/, registration/pipeline.py) | ```
(변경 없음)
``` |
| Qdrant nae_tsu_v1 points (baseline 유지 여부) | 3319 |

## 결론

이 데이터가 Corpus Factory 전환 Phase 1(병목 분석)의 유일한 근거다. 이후
모든 처리량 비교는 이 baseline과 대조한다.
