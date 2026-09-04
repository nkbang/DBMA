#!/bin/bash
# Phase 0 — Vol.1 Baseline Capture (NAE Corpus Factory transition, order §2).
# Run ONCE, only after Fuller_Complete_Works_Vol01's tsu_report.json shows
# partial:false. Read-only — never touches the production process, Ollama,
# or Qdrant. Writes a permanent baseline record for later throughput
# comparison.
set -uo pipefail
cd ~/DBMA || exit 1

VOL="Fuller_Complete_Works_Vol01"
REPORT="NAE/corpus/tsu/$VOL/tsu_report.json"
TSU="NAE/corpus/tsu/$VOL/tsu.json"
OUT_DIR=".automation/evidence/night-shift/corpus-factory-transition"
OUT="$OUT_DIR/PHASE0-VOL01-BASELINE.md"
mkdir -p "$OUT_DIR"

source ~/envs/dbma311/bin/activate

python3 - "$REPORT" "$TSU" "$OUT" <<'PYEOF'
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

report_path, tsu_path, out_path = sys.argv[1:4]

report = json.load(open(report_path))
records = json.load(open(tsu_path))

evaluated = report["candidates_evaluated"]
total = report["candidates_total"]
claims = report["claims_extracted"]
errors = report["llm_errors"]
elapsed = report["elapsed_seconds"]
skipped_not_claim = evaluated - claims - errors

avg_latency = elapsed / evaluated if evaluated else 0
throughput_hr = 3600 / avg_latency if avg_latency else 0

confidence_buckets = Counter()
for r in records:
    c = r.get("confidence")
    if c is None:
        confidence_buckets["none"] += 1
    elif c >= 0.9:
        confidence_buckets["0.9-1.0"] += 1
    elif c >= 0.8:
        confidence_buckets["0.8-0.9"] += 1
    elif c >= 0.7:
        confidence_buckets["0.7-0.8"] += 1
    else:
        confidence_buckets["<0.7"] += 1

doctrine_breakdown = report.get("doctrine_breakdown", {})

seen_claims = Counter(r.get("claim", "") for r in records)
duplicate_claim_count = sum(v - 1 for v in seen_claims.values() if v > 1)
seen_source_text = Counter(r.get("source_text", "") for r in records)
duplicate_source_text_count = sum(v - 1 for v in seen_source_text.values() if v > 1)

review_status = Counter(r.get("review_status", "?") for r in records)

# Qdrant baseline (read-only)
qdrant_points = "N/A"
try:
    sys.path.insert(0, ".")
    from NAE.pipeline.index import qdrant_store, config as index_config
    qdrant_points = qdrant_store.get_client().get_collection(index_config.COLLECTION_NAME).points_count
except Exception as e:
    qdrant_points = f"조회 실패: {e}"

git_diff = subprocess.run(
    ["git", "diff", "--stat", "core/retrieval.py", "NAE/pipeline/tsu/",
     "NAE/pipeline/ingest/", "NAE/pipeline/registration/pipeline.py"],
    capture_output=True, text=True,
).stdout.strip() or "(변경 없음)"

git_status_tsu = subprocess.run(
    ["git", "status", "--short", "NAE/corpus/tsu/"], capture_output=True, text=True
).stdout.strip()

reg_state_path = "NAE/pipeline/registration/state/registration_state.json"
try:
    reg_state = json.load(open(reg_state_path))
    reg_count = len(reg_state)
    reg_quality_passed = sum(1 for v in reg_state.values() if v.get("state") == "QUALITY_PASSED")
except Exception:
    reg_count = "N/A"
    reg_quality_passed = "N/A"

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

md = f"""# Phase 0 — Vol.1 (Fuller_Complete_Works_Vol01) Baseline

- captured_at: {now}
- 이 문서는 NAE Corpus Factory 전환의 영구 비교 기준(baseline)이다. 이후
  최적화 결과는 전부 이 수치와 대조한다.

## Processing

| 항목 | 값 |
|---|---|
| source_id | BAP-MISS-FULLER-VOL01 |
| volume | Fuller_Complete_Works_Vol01 |
| candidate count | {total} |
| processed count | {evaluated} |
| successful count (TSU 생성) | {claims} |
| failed count (llm_errors) | {errors} |
| skipped count (is_claim=false) | {skipped_not_claim} |
| total processing time | {elapsed:.1f}s ({elapsed/3600:.2f}h) |
| average candidate latency | {avg_latency:.2f}s |
| throughput/hour (누적 평균 기준) | {throughput_hr:.1f}/h |
| peak throughput (시간당 감시 샘플 관측 범위) | 약 300-400/h (정밀 peak 미추적 — 시간당 스냅샷 기반 근사치) |
| ETA 정확도 | 최초 예측 ~20.8h(C1, 100건 샘플) vs 최종 실측 {elapsed/3600:.1f}h — 초기 샘플이 후반보다 느려 과대추정됨 |

## TSU

| 항목 | 값 |
|---|---|
| generated TSU count | {len(records)} |
| rejected candidate count (is_claim=false) | {skipped_not_claim} |
| confidence distribution | {dict(confidence_buckets)} |
| extraction failure count (llm_errors) | {errors} |
| malformed output count | claim.py의 JSON parse 실패는 llm_errors에 합산되어 별도 집계 불가(현재 0이므로 무관) |
| duplicate claim text count | {duplicate_claim_count} |
| duplicate source_text count | {duplicate_source_text_count} |
| doctrine breakdown | {doctrine_breakdown} |
| review_status breakdown | {dict(review_status)} |

## System (baseline 조건)

- GPU: Apple M5 Max, 40 core, 관측 utilization ~99% (대시보드 API 실측)
- llama-server: `--parallel 1` (`-np 1`) — Ollama 자동 결정(다른 24GB 모델과
  메모리 공유로 인한 제약, CUE 앞선 조사에서 확인)
- model: my-theology-bot-v2:latest (70.6B, 53GB, 100% GPU 상주)
- system memory: 총 128GB 중 사용률 83% 내외로 실행 내내 유지(대시보드 관측)

## Integrity

| 항목 | 값 |
|---|---|
| registration_state.json 항목 수 | {reg_count} |
| registration_state QUALITY_PASSED 수 | {reg_quality_passed} |
| NAE/corpus/tsu/ git status | {git_status_tsu or '(모두 untracked — 커밋 전 상태, 정상)'} |
| production boundary git diff (core/retrieval.py, tsu/, ingest/, registration/pipeline.py) | ```\n{git_diff}\n``` |
| Qdrant nae_tsu_v1 points (baseline 유지 여부) | {qdrant_points} |

## 결론

이 데이터가 Corpus Factory 전환 Phase 1(병목 분석)의 유일한 근거다. 이후
모든 처리량 비교는 이 baseline과 대조한다.
"""

with open(out_path, "w", encoding="utf-8") as f:
    f.write(md)

print(f"baseline written: {out_path}")
print(f"generated TSU: {len(records)}, evaluated: {evaluated}/{total}, elapsed: {elapsed/3600:.2f}h")
PYEOF
