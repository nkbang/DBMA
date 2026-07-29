---
title: "ADR-010: DBMA-REQ — RAG Evaluation & Quality (LLM-as-Judge Pointwise 평가)"
category: architecture
sprint: DBMA-REQ Phase 1
based_on:
  - scripts/rag_benchmark.py (기존 검색 품질 벤치마크)
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
created: 2026-07-21
status: Architecture Decision (구조 확정 — 미확정 항목 2건 중 1건 해결(2026-07-29, 골든셋 3→7건 확대), 나머지 1건(question_answering_quality reference-free 재정의)만 HQ 결정 필요)
scope_modified: docs/architecture/ + core/evaluation/(신규) + scripts/run_rag_eval.py(신규)
---

# ADR-010: DBMA-REQ — RAG Evaluation & Quality

| | |
|---|---|
| Status | Accepted (구조) — Phase 1 착수 전 2건 결정 대기 |
| Date | 2026-07-21 |
| Deciders | HQ(사용자) 승인 / CUE 설계, C1 초안 병합 |
| Supersedes | — |
| Superseded by | — |

---

## Context

PM(사용자)이 외부 RAG 가이드 문서를 근거로, LLM 생성 답변을
`coherence / fluency / groundedness / safety / instruction_following /
question_answering_quality` 6개 지표(Google Vertex AI Gen AI
Evaluation Service의 pointwise autorater 지표명과 동일)로 채점하는
평가 체계 도입을 요청했다.

현재 DBMA 파이프라인 점검 결과:

```
Source Documents → Extraction → Normalization → Chunking → Embedding
→ TSU dataset(in-memory) → RetrievalEngine(BM25+Vector+Theological scoring)
→ GenerationService → Research UI
```

- **검색 품질 평가는 이미 존재**: `scripts/rag_benchmark.py`
  (Hit@K, MRR, 청킹 전략 × 임베딩 모델 비교), `scripts/rag_benchmark_dashboard.py`.
- **생성 품질 평가는 없음** — groundedness, QA quality 등 답변 자체의
  품질을 측정하는 경로가 전무.
- **Reranker(cross-encoder)도 없음** — `RetrievalEngine`의 "ranking"은
  자체 theological scoring이며 별도 cross-encoder 모델이 아님
  (`core/retrieval.py` 확인 완료, 코드베이스 전체에 `CrossEncoder`/
  `rerank` 클래스 없음).

C1(Cline, `dbma-planner-r1-q6:70b`)이 초안 계획을 제출했고, CUE가
파일 존재 여부(`scripts/rag_benchmark.py` 등)를 코드로 재검증한 뒤
CUE의 선행 계획과 병합했다. 진척 상태 점검 결과 `core/evaluation/`,
`tests/test_rag_judge.py`, `scripts/run_rag_eval.py`, `output/eval/`
전부 미착수(0%) 확인됨.

---

## Decision — 확정되는 것 (구조)

### 1. 신규 모듈 배치

```
core/evaluation/
├── __init__.py          # RagEvalScore export
├── schemas.py           # RagEvalScore dataclass
└── rag_judge.py         # judge LLM 호출 래퍼

scripts/run_rag_eval.py  # 배치 실행 (rag_benchmark.py와 동일 패턴)
tests/test_rag_judge.py  # TDD, groundedness 우선

output/eval/{run_id}_eval.jsonl  # 평가 결과 저장 (append-only,
                                  # _chunks_meta.json의 ChunkQuality와
                                  # 동일한 additive 저장 패턴)
```

기존 `RetrievalEngine`, `GenerationService`는 수정하지 않는다 —
평가 모듈은 그 출력(`ResponsePackage`, `GenerationResult`)을 읽기만
하는 별도 read-only 경로다 (ADR-001 "One Retrieval Engine" 원칙 유지).

### 2. 단계적 지표 도입 순서 (6개 동시 구현 금지)

1. **groundedness** 단일 지표로 인프라(스키마·judge·저장·테스트) 검증
2. 베이스라인 측정 — 기존 `rag_benchmark.py`(검색 품질) + `rag_judge.py`
   (생성 품질)를 나란히 리포트 → "검색이 빗나갔는지 생성이 약한지" 구분
3. **Reranker(cross-encoder, 예: bge-reranker-v2-m3) 도입**은 groundedness
   측정 도구가 갖춰진 뒤 진행 — 도입 전/후 점수 델타로 효과를 정량 검증한다.
   먼저 reranker부터 넣지 않는다.
4. 필요성이 실측으로 확인되는 지표만 순차 확장
   (question_answering_quality → coherence → fluency → safety →
   instruction_following)

### 3. Judge 모델 전략 — 검증 우선

1차: 로컬 Ollama(`dbma-planner-r1-q6:70b`)로 시도하되, **골든셋
(사람이 채점한 5~10개 사례) 대조 검증을 Phase 1 완료 조건에 포함**한다
— 이 모델은 개방형 코드/서술 작업에서 반복 실패 이력이 있어(별도
기록, C1 라우팅 정책 참고), 좁은 JSON 스코어링 과제에서도 신뢰도를
별도로 확인해야 한다. 신뢰도 부족 확인 시 2차로 별도 API judge 검토.

### 4. 벡터DB 범위

**정정 (2026-07-21)**: 초안 작성 시 "Qdrant만 사용한다"고 잘못 서술함 —
ADR-001 Correction/ADR-003이 이미 확정한 사실은 production authority가
TSU dataset + in-memory 유사도 검색이며, Qdrant/Chroma는 legacy corpus
history로만 보존되고 `RetrievalEngine` 검색 경로에서 쿼리되지 않는다는
것이다. 이 평가 모듈도 동일 원칙을 따른다 — 신규 벡터DB(Qdrant든
Chroma든)를 도입하지 않고 기존 TSU+in-memory 경로만 읽는다.

---

## Decision — 확정되지 않는 것 (Phase 1 착수 전 별도 결정 필요)

1. **골든셋 라벨링 담당·소요시간** — ✅ **해결 (2026-07-21 착수 → 2026-07-29 확대 완료)**.
   담당: 사용자(David) 직접 채점. `QueryProcessor` + `GenerationService`로
   실제 파이프라인을 실행해 얻은 실제 질문·청크·답변에 사용자가 0~5점
   groundedness를 직접 채점했다. 최초 3건(요한복음 15장/로마서 8장/
   히브리서 대제사장)에서 `judge_groundedness()`(judge_model=
   `dbma-planner-r1-q6:70b`)와 대조한 결과, **순위는 3사례 전부 사람과
   일치**했으나 절대 점수는 judge가 관대한 경향(평균 절대 오차 0.83/5,
   gold-1 사례 +1.6 편차)이 확인됐다.
   **2026-07-29 gold-4~7 확대(총 7건, 목표 5~10건 달성)**: RAG 축
   4건 전부 judge·사람 완전 일치(0.0 또는 5.0), 전체 MAE 0.83→0.36으로
   개선(단, 신규 4건이 극단값이라 순수 개선으로만 보기는 어려움 —
   gold-1의 +1.6 편차는 여전히 유효한 경고). 설교 축(SEQ004~007)도
   대조해 judge가 사람보다 최대 1점 관대한 경향 재확인 — 결과 전체는
   `tests/fixtures/rag_eval_golden_set.json`(RAG),
   `docs/DBMA-SEQ-Phase1-Groundedness-Baseline-2026-07-27.md`(설교)에
   저장. **결론**: 절대 점수를 그대로 신뢰하기보다 **상대 비교(reranker
   도입 전/후 델타 측정) 용도로 우선 사용**하는 기존 방침 유지 — 표본
   목표는 달성했으므로 추가 확대는 필요 시에만.
2. **`question_answering_quality`의 reference-free 재정의 여부** —
   DBMA의 실제 용례(설교 개요 생성)는 정답이 없는 open-ended 작업이라,
   정답 존재를 전제로 한 QA 벤치마크식 지표를 그대로 쓸 수 없다.
   groundedness(정답 불필요)는 문제없음. **미해결** — Phase 4(지표
   확장) 착수 전 별도 결정 필요.

---

## Consequences

**장점**
- 기존 검색 품질 벤치마크(`rag_benchmark.py`)와 상호 보완 — 신규 구축
  아님, 확장.
- reranker 등 향후 구조 변경을 "도입 전/후 수치 비교"로 검증 가능하게
  만드는 계측 인프라 확보.
- `RetrievalEngine`/`GenerationService` 무변경 — 회귀 위험 최소.

**비용/리스크**
- 로컬 70B judge 추론 비용(배치 오프라인 실행 전제, 실시간 아님).
- 골든셋 라벨링에 사용자 시간 소요(담당·일정 미정, 위 미확정 항목 1).
- 지표 확장을 언제 멈출지 명시적 임계값이 없으면 무한 확장 위험 —
  Phase별 완료 조건(예: groundedness 평균 목표 점수)을 각 Phase 착수
  시 문서에 명시한다.
- `RagEvalScore`에 judge 프롬프트 버전 필드(`judge_prompt_version`)
  누락 상태로 시작하면 추후 프롬프트 수정 시 과거 점수와 비교 불가 —
  Phase 1 스키마 설계 시 반영한다.

---

## Next Steps

1. ~~미확정 항목 2건 HQ 결정~~ — **골든셋 항목은 2026-07-29 해결**(3→7건
   확대 완료, 위 참고). QA quality reference-free 여부는 **아직 미해결
   — Phase 4 착수 전 HQ 결정 필요**(아래 참고).
2. ~~`core/evaluation/schemas.py` — `RagEvalScore` TDD 작성~~ 완료
   (`core/evaluation/schemas.py`, `tests/test_rag_eval_schemas.py`)
3. ~~`tests/test_rag_judge.py` — TDD~~ 완료 (mock 기반 10케이스).
   실모델 골든셋 대조는 3→7건으로 확대 완료(2026-07-29)
4. ~~`core/evaluation/rag_judge.py` — groundedness 최소 구현~~ 완료
5. ~~골든셋 표본 5~10개로 확대~~ **완료(2026-07-29, 7건)** → 다음 단계:
   Phase 2(베이스라인 측정, `scripts/run_rag_eval.py`) 착수 → Reranker
   도입 검토(Phase 3)로 이관. **단, Phase 4(지표 확장) 착수 전에는
   아래 미해결 결정(question_answering_quality reference-free 재정의)이
   먼저 필요.**
6. **별도 후속 확인(이 ADR 범위 밖)**: 메타데이터(저자·출판연도·페이지·
   언어·문서 유형)가 TSU 레코드에 실제로 채워지는지 `core/tsu_builder.py`
   재확인 — 채워지지 않으면 필터링·인용 품질에 영향. 이 ADR은 평가/
   reranker 범위만 다루므로 메타데이터 보강은 별도 ADR 또는 작업으로
   분리한다.
