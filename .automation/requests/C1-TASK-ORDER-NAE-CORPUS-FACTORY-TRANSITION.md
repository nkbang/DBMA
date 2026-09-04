# C1 Task Order — NAE Corpus Factory 전환

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's directive (2026-08-15) |
| Mission | Book-단위 순차 처리("한 권씩 완전히 끝내기")에서 Pipeline-단위 동시 처리("여러 source가 각 단계에서 동시에 전진")로 전환 |
| Priority | P0 |
| Mode | Autonomous, 단 §0 실행 조건 충족 후에만 |
| Supersedes | `.automation/night-shift/run_tsu_queue.sh`(Vol02 자동 시작 — 폐기됨, 2026-08-15 23:38 CDT 중단) |
| Baseline | `.automation/evidence/night-shift/corpus-factory-transition/PHASE0-VOL01-BASELINE.md`(Vol.1 완료 시 CUE가 자동 생성) |

---

## 0. 실행 조건 — 반드시 준수

**이 명령은 Andrew Fuller Vol.1 TSU Extraction Production Run이 완전히
종료된 후에만 실행한다.** Vol.1 완료 전에는 아래를 절대 하지 않는다:

```
❌ Production process 중단
❌ Ollama 재시작
❌ llama-server concurrency 변경
❌ 모델 교체
❌ Vol.1 재처리
❌ pipeline architecture 변경
❌ Qdrant mutation
❌ 기존 Production state 변경
```

Vol.1 완료 시점의 상태는 CUE가 자동으로 baseline으로 캡처한다
(`capture_vol01_baseline.sh`, Phase 0). 이 baseline이 준비된 뒤에만
Phase 1부터 착수한다.

## 1. Mission

현재: `Book → TSU Extraction → 완료`(책 한 권씩 순차 완료)

목표:

```
RAW → Registration → Quality/OCR → Candidate Filtering → TSU Extraction
    → Confidence Classification → Review Queue → Promotion Gate
    → Embedding → Qdrant → Retrieval Validation → 다음 작업 Queue
```

여러 source가 파이프라인의 서로 다른 단계에서 **동시에** 전진할 수 있는
구조로 전환한다.

## 2. Phase 0 — Vol.1 Baseline Capture (CUE가 자동 실행, C1 착수 불필요)

Vol.1 완료 즉시 CUE가 `capture_vol01_baseline.sh`로 아래를 전부 기록한다:
Processing(candidate/processed/successful/failed/skipped count, 처리시간,
평균 latency, throughput, ETA 정확도), TSU(생성 수, reject 수, confidence
분포, 실패/malformed/중복 수, doctrine breakdown), System(GPU/CPU/메모리,
llama-server parallelism, 모델, 프로세스 lifetime), Integrity
(registration_state, output/evidence 파일, git diff, production boundary,
Qdrant point count). 이 baseline은 영구 보존하며 이후 모든 최적화 비교의
기준이다. **C1은 이 Phase를 다시 만들 필요 없다** — 파일이 이미 준비돼
있을 것이다.

## 3. Phase 1 — 병목 분석

Vol.1 실측 evidence(Phase 0 baseline)만으로 답한다. 추측 금지.

1. 전체 처리시간 중 LLM inference 비율은?
2. candidate filtering으로 제거 가능한 비율은?
3. 동일/중복 candidate가 존재하는가? (baseline의 duplicate count 참고)
4. deterministic filtering이 가능한 유형은?
5. GPU가 실제 병목인가? (baseline: GPU ~99%, `-np 1`)
6. CPU/RAM/I/O가 병목인가?
7. n8n orchestration overhead가 존재하는가? (CUE 사전 확인: TSU 생성은
   n8n을 거치지 않음 — 이 항목은 "해당 없음"으로 답이 이미 나와 있다.
   재조사하지 말 것)
8. Review가 전체 TSU를 막는 병목이 될 가능성은?
9. Embedding/Qdrant가 TSU extraction보다 빠른가?
10. 각 단계가 독립 queue로 분리될 필요가 있는가?

## 4. Phase 2 — Candidate Filtering 설계

LLM 호출 전 값싼 deterministic preprocessing:

```
RAW candidate → Normalization → Duplicate detection
    → Obvious non-theological filtering → Candidate classification → LLM
```

LLM 호출 없이 처리 가능한지 검토: 중복 text, metadata-only content, page
number/header/footer, 명백한 OCR garbage, 지나치게 짧은 fragment, 반복
boilerplate, 명백한 비신학적 구조물.

**신학적 의미 판단을 단순 rule로 과도하게 하지 말 것.** Recall 손실
가능성이 있는 filtering은 반드시 benchmark로 검증한다.

## 5. Phase 3 — TSU Extraction Pipeline 분리

독립 Queue Worker로 분리 검토·구현:

```
TSU_EXTRACTION_QUEUE: READY → PROCESSING → EXTRACTED → CONFIDENCE_CLASSIFIED
실패: PROCESSING → FAILED → ERROR/REVIEW QUEUE
```

Retry 정책은 기존 ADR(ADR-022 §8 — 자동 재시도/자동 승격 금지 원칙)을
그대로 따른다. **새 retry semantics를 임의로 만들지 말 것.**

## 6. Phase 4 — Confidence-based Review

```
HIGH   → 자동 후속 처리 가능
MEDIUM → Sampling / Targeted Review
LOW    → Human Review
```

confidence가 신학적 진실성을 의미하지 않음을 명확히 유지. Human Review
우선 대상: LOW confidence, ambiguous doctrine, conflicting evidence,
citation uncertainty, OCR uncertainty. **속도를 이유로 신학적 품질
게이트를 제거하지 말 것.**

## 7. Phase 5 — Incremental Promotion

책 전체 완료를 기다리지 않고 검증된 TSU만 다음 단계로:

```
Verified TSU → Promotion Gate → Embedding Queue
```

`TSU 생성 ≠ Verified ≠ Production` 상태 구분 유지. 기존 NAE governance와
ADR의 state semantics 변경 금지. **schema/ADR 변경이 필요하면 CUE가 먼저
제안하고 승인 절차를 거친다 — C1이 임의로 하지 않는다.**

## 8. Phase 6 — Incremental Embedding

Promotion된 TSU만 embedding queue로. 현재 승인된 설정(BGE-M3, 1024
dimensions, cosine distance) 그대로 유지 — 변경 금지. Embedding 실패는
별도 error queue로 분리.

## 9. Phase 7 — Incremental Qdrant Indexing

```
Verified TSU → BGE-M3 → Payload validation → Qdrant
```

기존 Qdrant collection/schema 존중. **Qdrant에 데이터가 들어가는 것 자체가
신학적 승인을 의미하지 않는다.** Approved state를 통과한 데이터에만
mutation을 허용한다.

## 10. Phase 8 — Retrieval Validation

승격된 데이터가 실제 retrieval에 정상 반영되는지 검증: citation mapping,
tsu_id, source_id, edition_id, source metadata, retrieval score, provenance,
content excerpt — 기존 Citation contract 유지. **`core/retrieval.py`는
Production Retrieval Engine authority를 유지한다. NAE integration을
이유로 DBMA Core를 임의 변경하지 말 것.**

## 11. Phase 9 — n8n Orchestration

n8n은 orchestration만 담당(Registration→Quality→TSU→Review→Promotion→
Embedding→Qdrant→Validation Queue 관리). **LLM inference 자체를 n8n이
담당하게 만들지 말 것.** 실제 계산은 Python/Ollama/BGE-M3/Qdrant.

## 12. Phase 10 — Multi-Source Flow

최종 목표 형태 예시:

```
Vol.1 → Review → Embedding
Vol.2 → TSU
Vol.3 → Candidate Filtering
...
```

각 source가 파이프라인의 서로 다른 단계에서 동시 전진 가능해야 한다 —
이것이 이번 전환의 핵심.

## 13. 병렬화 정책

Vol.1 baseline(`llama-server -np 1`, GPU ~99%)을 기준으로 삼는다.
**단순히 1→2→4 worker로 바꾸지 말 것.** 아래를 전부 만족할 때만
concurrency 실험을 "제안"한다(실행이 아니라 제안 — CUE 승인 필요):

```
✅ Vol.1 Production 완료
✅ 현재 모델 unload/reload 가능한 시점
✅ 메모리 headroom 확인됨
✅ GPU thermal/power 상태 확인 가능
✅ baseline throughput 확보됨(Phase 0)
✅ production interruption 없이 실험 가능
✅ rollback 가능
```

## 14. 모델 정책

현재 local model(`my-theology-bot-v2:latest`) 기본값 유지. 새 고비용 모델
추가 금지. 외부/고비용 모델(예: Fable 5 등)은 현재 local pipeline으로
해결 불가능한 필요성이 실증된 경우에만 **CUE가 제안**한다. 속도만을
이유로 한 모델 교체는 승인 대상이 아니다.

## 15. Human-in-the-loop 정책

자동화 목적은 인간의 신학적 판단 제거가 아니라, **사람이 정말 판단해야
하는 부분에만 사람의 시간을 쓰게 하는 것**이다.
`Machine → Filtering → Extraction → Confidence → Human Review → Promotion`
구조 유지.

## 16. Failure Isolation

각 단계는 독립적으로 실패 가능해야 한다(TSU Error Queue / Embedding Error
Queue / Index Error Queue 분리). **한 권의 실패가 전체 corpus processing을
중단시키면 안 된다.** 단, data corruption이나 governance violation은
즉시 HALT 조건.

## 17. Production Boundary

절대 변경 금지: DBMA Core retrieval authority, personal corpus, NAE corpus
isolation, approved Qdrant schema, registration governance, TSU schema
governance, production state semantics, ADR-defined boundaries.

Architecture 변경 필요 시 순서: `C1 proposal → CUE review → ADR → approval
→ implementation`.

## 18. Dashboard 연계

기존 NAE Live Progress Dashboard(`.automation/night-shift/dashboard/`,
http://127.0.0.1:8799, launchd 관리)의 monitoring schema를 확장해 Corpus
Factory 상태를 표시한다: 현재 source, 각 pipeline stage, queue depth,
processing rate, completed/failed/review pending/promotion pending/
embedding pending/Qdrant indexed/retrieval validated, GPU/CPU/memory/disk/
process health. **Dashboard는 계속 READ-ONLY** — 이미 검증된 원칙
(`BUILD_REPORT.md`) 그대로 유지, write route 추가 금지.

## 19. Help 기능

각 metric에 의미/정상범위/계산방식/Production과의 관계를 설명하는 Help
기능 유지. Monitoring ON/OFF는 production control이 아님을 명확히 한다.

## 20. Acceptance Criteria

**Architecture**: pipeline stage 독립 정의, 각 stage에 queue/state 존재,
source 간 overlap 가능, failure isolation 구현.
**Performance**: Vol.1 baseline과 신규 throughput 비교 가능, LLM 호출
감소 효과 측정 가능, 병목이 evidence로 확인됨.
**Quality**: 신학적 품질 게이트 유지, confidence classification 검증,
human review path 존재, promotion gate 유지.
**Retrieval**: verified TSU→embedding→Qdrant→retrieval validation,
citation/provenance integrity 유지.
**Governance**: DBMA Core 무단 변경 없음, NAE corpus isolation 유지, ADR
변경은 승인 절차 준수, production boundary 위반 없음.
**Regression**: ADR regression, registration tests, TSU tests, embedding
tests, retrieval tests, dashboard tests 전체 PASS.

## 21. 작업 방식

```
C1 Build → CUE Audit → C1 Correct → CUE Re-audit → CUE Approve
```

C1: 구현·테스트·성능 측정. CUE: architecture·governance·독립 검증·
approval. **C1의 PASS 보고를 최종 근거로 쓰지 않는다 — 중요한 결과는
CUE가 직접 재실행해서 확인한다**(이번 세션 전체에서 이미 이 방식으로
운영 중 — Correction Order 001/002/003 참고).

## 22. 최종 목표

성공 기준은 "Fuller Vol.2를 빨리 끝내는 것"이 아니라 **NAE가 수십·수백
권의 Public-Domain theological corpus를 지속적으로 흘려보낼 수 있는
Corpus Factory가 되는 것**이다. 우선순위:

```
Correctness → Governance → Repeatability → Observability → Throughput
```

Vol.1은 이 Factory의 Production Baseline Book으로 취급한다. Phase를
순차 진행하되, Phase 사이마다 CUE가 독립 검증한다. **Vol.1 완료 전에는
이 명령의 구현을 시작하지 않는다.**
