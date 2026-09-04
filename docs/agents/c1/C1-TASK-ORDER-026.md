# C1 Task Order 026 — Sprint E: ClaimGuard 골드셋 평가 (오프라인 스크립트)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P2 (Sprint A~D + 응답생성 연동 완료 후, v2 마무리 평가 단계)
**선행 작업**: Task Order 020~024 완료·검증됨(137/137, 이후 전체 회귀 1020/1020으로 확장 확인).
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md) §3 Sprint E
**작성일**: 2026-07-29
**모드 제약**: `core/retrieval.py`, `core/parallel_retriever.py`, `core/generation.py`, `ui/pages/chat.py`,
`core/claim_guard.py` **전부 미접촉** (읽기 전용 import만). 이번 산출물은 `scripts/`와 `docs/`뿐이다.

---

## 1. 배경 및 범위 축소 이유 (반드시 먼저 읽을 것)

계획서 원문의 Sprint E는 "T1/T2/T3/T4별 검색 기여도 비교"를 요구하지만, **현재 DBMA에는 실제 T2(큐레이션
태그)/T3(주석·논문)/T4(자동분류) 데이터가 전혀 없다** (Sprint B는 픽스처만 검증했고, 실제 외부 데이터셋
조달은 별도 트랙으로 아직 진행 안 됨). 없는 데이터로 "기여도 비교"를 만드는 건 지어내는 것이므로,
이번 Sprint E는 **현재 실제로 존재하는 것 — T1(본문 검색)만 있는 상태에서 ClaimGuard의 위험 표현
탐지·범위 한정 문구 생성이 실제 프로덕션 코퍼스(`data/제련완성본/`)와 실제 Ollama 생성에서 얼마나
잘 작동하는지**를 측정하는 것으로 범위를 좁힌다.

- 골드셋 규모도 100개가 아니라 **30개**로 축소한다 (사람이 직접 검토 가능한 규모 — 100개를 기계적으로
  생성하면 품질 검증 없는 숫자 채우기가 된다).
- T2/T3/T4 관련 평가 항목은 "해당 없음(N/A) — 실 데이터 없음"으로 리포트에 명시하고 비워둔다.

---

## 2. 구현 범위

### 2.1 골드셋 파일 — `tests/goldsets/claim_guard_goldset_v1.jsonl`

30개 질의를 아래 형식으로 직접 작성한다 (자동 생성 금지 — 사람이 읽고 의도를 확인할 수 있는 질의여야 함).

```jsonl
{"id": "cg-001", "query": "창세기에서 가장 처음 나온 기도는 무엇인가요?", "expected_risk_terms": ["처음"], "category": "absolute_first"}
{"id": "cg-002", "query": "성경에서 유일하게 나오는 지명은 어디인가요?", "expected_risk_terms": ["유일"], "category": "absolute_only"}
{"id": "cg-003", "query": "창세기 24장의 배경은 무엇인가요?", "expected_risk_terms": [], "category": "neutral"}
...
```

**분포 (30개 배분):**
- `absolute_first`(최초/처음/가장 이른 유도) 8개
- `absolute_only`(유일/전부) 6개
- `absolute_universal`(항상/절대/명백히/성경 전체에서) 6개
- `neutral`(위험 표현 없는 일반 질의 — false positive 확인용) 10개

각 질의는 실제 DBMA 프로덕션 코퍼스(`data/제련완성본/`)가 커버하는 성경 본문/주제로 작성 —
`RetrievalEngine.book_coverage()`로 실제 커버리지가 있는 책 위주로 고를 것 (커버리지 없는 책으로 질의를
만들면 T1 근거가 항상 0이 되어 평가가 무의미해짐).

### 2.2 평가 스크립트 — `scripts/evaluate_claim_guard_goldset.py`

```text
목적: goldset의 각 질의를 실제 파이프라인(QueryProcessor.process → GenerationService.generate,
프로덕션 config의 RetrievalEngine/Ollama 모델 사용)으로 1회씩 실행하고, ClaimGuard 판정 결과를 기록한다.

절차:
1. goldset jsonl 로드
2. 각 질의에 대해:
   a. QueryProcessor.process(query) 호출 (기존 프로덕션 설정 그대로 — 신규 인자 추가 금지)
   b. GenerationService.generate(response) 호출 (스트리밍 아님, 배치 평가이므로 generate() 사용)
   c. result.claim_guard_result 기록 (risk_level, matched_terms, absolute_claim_blocked,
      scope_qualifier_required)
   d. expected_risk_terms와 실제 matched_terms 비교 — category가 neutral인데 matched_terms가 비어있지
      않으면 "예상외 탐지"로 플래그, absolute_*인데 matched_terms가 비어있으면 "미탐지(false negative)"로
      플래그
3. 결과를 JSON으로 저장 (`output/claim_guard_eval/goldset_v1_result_<timestamp>.json`)
4. 요약 리포트 출력: 정탐/오탐/미탐 개수, category별 분포, 평균 지연시간
```

- 이 스크립트는 **pytest가 아니라 독립 실행 스크립트**다 (Ollama 실제 호출 + 실제 코퍼스 검색이라 느림 —
  30개 질의 기준 수 분 소요 예상, CI/일반 회귀 테스트에 넣지 않는다).
- 실행: `python scripts/evaluate_claim_guard_goldset.py tests/goldsets/claim_guard_goldset_v1.jsonl`
- 실패한 개별 질의(Ollama 오류 등)가 있어도 스크립트 전체가 죽지 않고 해당 질의만 오류로 기록 후 계속
  진행 (`GenerationService.generate()`가 이미 예외를 안 던지고 `error` 필드로 처리하는 기존 패턴을
  그대로 따름 — 새로운 예외 처리 방식 만들지 말 것).

### 2.3 리포트 문서 — `docs/DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md` (신규)

스크립트 실행 결과를 정리한 md 문서. 최소 포함 항목:
- 30개 질의 category별 정탐/오탐/미탐 표
- 미탐지(false negative) 사례가 있다면 원문 나열 (왜 놓쳤는지 짧은 분석)
- 오탐(false positive, neutral인데 잘못 감지) 사례가 있다면 나열
- **T2/T3/T4 기여도: "N/A — 실 데이터셋 없음, 후속 과제"**로 명시
- 평균 응답 지연시간 (참고용, 성능 회귀 판단용은 아님)

---

## 3. 이번 범위에서 제외

- T2/T3/T4 실데이터 기반 평가 — §1 참고, 실 데이터 없음.
- CI 파이프라인에 이 스크립트 자동 실행 등록 — Ollama 의존 배치 작업이라 일반 pytest 스위트에 안 넣음
  (이미 §2.2에 명시).
- 미탐/오탐 발견 시 `ClaimGuard`의 `ABSOLUTE_SUPERLATIVE_TERMS`나 로직을 이번 Task Order에서 즉시
  수정하는 것 — **발견만 하고 고치지 않는다.** 수정은 리포트를 CUE가 검토한 뒤 별도 Task Order로.

---

## 4. 검증 계획

1. 스크립트 자체의 정상 동작 확인 (dry-run: goldset 3개 정도로 축소해서 먼저 실행 → 정상 종료·JSON
   저장 확인 → 그 다음 30개 전체 실행)
2. 리포트 문서가 §2.3 항목을 전부 포함하는지 확인
3. 기존 pytest 스위트(1020개) 회귀 없음 확인 — 이번엔 신규 코드가 스크립트/문서뿐이라 당연히 영향
   없어야 하지만 명시적으로 재실행해 확인.

---

## 5. 보고 형식

1. `scripts/evaluate_claim_guard_goldset.py`, `tests/goldsets/claim_guard_goldset_v1.jsonl` diff
2. 리포트 문서(`docs/DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md`) 전문
3. 스크립트 실행 로그 요약 (정탐/오탐/미탐 개수, 총 소요시간)
4. 기존 pytest 1020개 회귀 결과 (정확한 숫자 그대로 복사)
5. 미탐/오탐이 발견됐다면 그 목록 — CUE가 이걸 보고 후속 수정 여부를 판단함

---

## 6. 다음 조치

리포트 검토 후 미탐/오탐이 있으면 CUE가 `ClaimGuard` 개선 Task Order를 별도 발급. 문제 없으면 v2가
공식적으로 마무리되고, 이후 v3(Obsidian/Logos 등 나머지 코퍼스) 착수 여부를 사용자와 재논의.
