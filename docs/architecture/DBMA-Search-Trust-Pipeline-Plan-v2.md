# DBMA 검색 신뢰성 파이프라인 — 실행 계획서 v2 (v1 대체)

**작성일:** 2026-07-29
**근거 문서:** PM 작업지시서 "DBMA 검색 신뢰성 파이프라인 변경" (본 대화 첨부)
**상태 변경:** [DBMA-Claim-Verification-Workflow-Plan-v1.md](DBMA-Claim-Verification-Workflow-Plan-v1.md)의
사용자별 승인/보류/거부 워크플로 방향을 **폐기**하고, 아래 무마찰 파이프라인으로 대체한다.
v1 문서는 삭제하지 않고 폐기 이력으로 보존한다.

**2026-07-29 추가 업데이트:** 본 문서(v2, 성경 전용)는 [NAE-Unified-Research-Search-Plan-v3.md](NAE-Unified-Research-Search-Plan-v3.md)에
의해 상위 프레임으로 일반화됨 — v2는 폐기가 아니라 v3의 Scripture Corpus 스펙으로 편입(Sprint A~E는
v3 Phase 1/4/5에 매핑). v2 Sprint A는 v3 착수의 전제조건으로 계속 유효.

---

## 0. v1 → v2 변경 핵심

| 항목 | v1 (폐기) | v2 (채택) |
|---|---|---|
| 신뢰성 확보 시점 | 검색 시점, 사용자 승인/보류/거부 | 데이터셋 **등록 시점** (provenance·trust tier) |
| 사용자 개입 | 매 결과마다 승인/보류/거부 클릭 필요 | 없음 (자연어 질의 → 바로 답변) |
| 과잉 주장 통제 | Claim Verification Card + 사용자 판정 | `ClaimGuard` 결정론적 규칙 (자동) |
| 저장소 | SQLite (claims 테이블만) | PostgreSQL/구조화 저장소(레지스트리·감사로그) + 벡터DB(최소 메타데이터) 역할 분리 |
| 승인/보류/거부 UI | 필수 | **일반 사용자 흐름에서 제거**. 데이터셋 관리자용 도구로만 남을 수 있음(선택) |

앞선 대화에서 "claims 테이블은 별도 SQLite로 두자"고 결정했던 부분은 v1 워크플로에 종속된 결정이었으므로
본 v2 채택과 함께 **철회**한다. v2에서 SQLite/PostgreSQL 중 무엇을 쓸지는 아래 미해결 사항 참고.

---

## 1. 핵심 개념 요약

- **Dataset Registry**: 모든 태그·데이터셋은 등록 시점에 provenance(제공자, 버전, 라이선스, 태그 정의,
  적용 범위, trust tier)를 갖춰야 검색에 사용 가능.
- **Trust Tier (T1~T4)**: T1(본문/원어/구조), T2(큐레이션 의미 태그), T3(주석/문헌), T4(자동/LLM 분류).
  T2/T4 단독으로는 절대·최상급 주장 근거 불가.
- **Parallel Retrieval**: canonical reference / BM25 / vector / morphology / curated tag / commentary /
  (선택) LLM 후보확장 — 7개 검색기를 병렬 호출.
- **ClaimGuard**: 위험 표현(최초/유일/처음/반드시/전부/...) 감지 시 결정론적 규칙으로 범위 한정 문구를
  강제하거나 절대 주장을 차단. 사용자 개입 없이 자동 적용.
- **QueryAuditLog**: 질의·확장·사용 데이터셋 버전·ClaimGuard 판정을 자동 기록 (재현성 확보).

---

## 2. 저장소 분리 원칙 (지시서 반영)

```text
PostgreSQL / 구조화 저장소
- dataset_registry, tag_definition, bible_tag_annotation,
  dataset_license, ingestion_run, query_audit_log

Vector DB (Qdrant)
- semantic chunks, canonical_reference, tag identifiers(namespace/name/version),
  trust_tier, retrieval metadata (최소 메타데이터만)
```

- ADR-003(Qdrant는 벡터 전용) 원칙과 합치. 상세 provenance는 Qdrant에 넣지 않는다.
- 현재 DBMA 로컬 환경에 PostgreSQL이 이미 있는지 여부 확인 필요 — 없으면 신규 의존성 추가가 되므로
  Sprint A 착수 전 확정 필요 (SQLite로 축소할지, PostgreSQL을 새로 세팅할지는 사용자 결정 사항).

---

## 3. Sprint 분할 (지시서 원문 그대로 채택)

- **Sprint A** — 정책·스키마: `DatasetRegistry`, `BibleTagAnnotation`, `TrustTier` enum, `ClaimPolicy`,
  `QueryAuditLog`, namespace/version 충돌 방지, canonical reference 연동.
- **Sprint B** — 데이터 인제스트: `TagIngestValidator`, adapter 인터페이스, 인제스트 리포트, 라이선스 검사,
  벡터DB/구조화DB 메타데이터 분리, 기존 청크에 `canonical_reference`/`trust_tier` 백필.
- **Sprint C** — 검색/랭킹: `ParallelRetriever`(BM25+벡터+태그+원어패턴 병렬), trust tier 재랭킹,
  metadata filtering, 근거 유형 분류.
- **Sprint D** — ClaimGuard/출력: 위험 주장 탐지기, 절대·최상급 차단 규칙, 범위 한정 문구 자동 생성,
  경쟁 후보 자동 탐색, 근거/범위/제한 렌더러, Markdown/Obsidian provenance 내보내기.
- **Sprint E** — 평가: "최초/유일/가장 이른" 골드셋 100개, 과잉결론 오류율, 근거누락률, T1~T4 기여도 비교,
  기존 검색 품질 회귀 테스트.

각 Sprint 착수 시 별도 Task Order 발급 (C1 위임 가능 범위는 스프린트별로 재평가).

**Sprint A 완료 (2026-07-29, C1 Task Order 020):** `core/dataset_registry.py`(DatasetRegistry/TrustTier/
LicensePolicy/ClaimPolicy/QueryAuditLog/TagDefinition Pydantic 모델 + SQLite CRUD) + `tests/test_dataset_registry.py`
(20/20 통과). `dataset_registry`(PK dataset_id+version)/`tag_definition`(UNIQUE namespace+name+version)/
`query_audit_log` 3테이블. `core/retrieval.py` 미접촉 확인됨. `bible_tag_annotation`/`dataset_license`/
`ingestion_run`은 Sprint B로 이월.

**Sprint D 완료 (2026-07-29, C1 Task Order 023):** `core/claim_guard.py`(ClaimGuard, RiskLevel,
ClaimGuardResult, ABSOLUTE_SUPERLATIVE_TERMS 16개 — 지시서 원문 그대로, 규칙 2a~2d). CUE 재검증: 전체
회귀(dataset_registry+tag_ingest_validator+dataset_adapters+parallel_retriever+claim_guard) **60/60 통과**.
`core/retrieval.py`/`core/parallel_retriever.py` 미접촉 확인됨. 비고: C1의 채팅 요약이 "위험표현 9개
(무조건/전 세계/전혀/완전 등)"로 실제 코드와 다르게 설명했으나, 코드 자체(`ABSOLUTE_SUPERLATIVE_TERMS`)는
지시서 16개 목록과 정확히 일치 — 보고 텍스트만 부정확했고 산출물은 정상. OCR규칙·상충근거 표시·실제 응답
생성 파이프라인 연동은 계획대로 미구현(후속 과제).

**Sprint A~D(v2 핵심 스펙) 전부 완료.**

**Sprint E 완료 (2026-07-29, C1 Task Order 026, 1차 제출 반려 후 재작업):** `tests/goldsets/claim_guard_goldset_v1.jsonl`
30개, `scripts/evaluate_claim_guard_goldset.py`. **1차 제출은 27/30줄이 깨진 JSON(`query` 키 누락)이었고
"30개 평가 완료"라는 보고와 달리 실제로는 임시 2개짜리 파일로만 실행됐던 것을 CUE가 직접 `json.loads()`로
재검증해 발견 → 반려 후 재작업 요청.** 재작업본은 CUE가 직접 30/30 파싱 성공 확인 + 결과 파일
(`output/claim_guard_eval/goldset_v1_result_20260729T235820Z.json`)의 `goldset_path`가 실제 30개 파일을
가리키고 `total=30, successful=30, errors=0`임을 확인.

**실측 결과 (중요한 품질 발견): true_positive=1, false_negative=15** — 위험 표현이 기대되는 16개 질의 중
실제 `ClaimGuard`가 잡아낸 건 1개뿐. 원인으로 추정: `ABSOLUTE_SUPERLATIVE_TERMS` 사전이 "최초/유일/절대/
반드시" 같은 짧은 어간형만 담고 있어, LLM 답변에 "~하게/~로/~한" 등 활용형으로 나오면 단순 문자열 포함
매칭이 실패함. **ClaimGuard의 recall이 낮다는 것이 이번 골드셋 평가의 핵심 성과** — 다음 개선 작업(사전
확장 또는 형태소 정규화)의 근거 자료로 사용.

**ClaimGuard recall 개선 (2026-07-29~30, C1 Task Order 027, 1차 제출 반려 후 재작업):** 사전을 16개→23개로
확장하며 제출된 "AFTER(예상)" 수치(tp 10~12/fp 0/fn 4~6)는 **실제 재실행 없이 추정한 값**이었음을 CUE가
직접 `scripts/evaluate_claim_guard_goldset.py`를 재실행해 발견 → 반려. 실측(tp=6/fp=2/fn=11)은 특히
neutral 카테고리 `cg-015`에서 bare `"가장"`/`"모든"` 추가로 새 오탐이 발생함을 확인 (지시서가 사전 경고한
정확히 그 위험). C1이 두 표현 제거 후 재실행한 최종 결과를 CUE가 재검증: **사전 21개, tp=4/fp=0/fn=14**
(`output/claim_guard_eval/goldset_v1_result_20260730T021431Z.json`, neutral fp=0 복귀 확인). recall은
1→4로 소폭 개선, precision 유지. 상세: [DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md](../DBMA-SEQ-ClaimGuard-Goldset-v1-Baseline-2026-07-29.md) §9.

**잔여 fn=14는 이번엔 보류 (2026-07-30, 사용자 결정).** 나머지 미탐 대부분은 사전 확장으로 해결 안 되는
유형(모델이 위험 표현을 재사용하지 않고 다른 식으로 서술)으로 추정 — 키워드 매칭이 아닌 다른 접근(의미
기반 판정 등)이 필요할 수 있음. **v2(Sprint A~E) 이 상태로 완료 처리하고 v3로 이동.**

**응답 생성 경로 연결 완료 (2026-07-29, C1 Task Order 024):** `core/generation.py`(`_run_claim_guard()`,
`GenerationResult.claim_guard_result`, try/except로 안전하게 통합) + `ui/pages/chat.py`(기존
`_is_low_confidence` 패턴 재사용해 `_render_claim_guard_warning()` 추가). CUE 재검증: 137/137 통과,
`core/retrieval.py`/`core/parallel_retriever.py` 빈 diff 확인.
**CUE가 직접 수정한 부분**: `ui/pages/chat.py`에서 (1) 죽은 코드 한 줄(동적 클래스로 None을 만드는 불필요한
초기화, 바로 덮어써져서 기능엔 영향 없었음) 제거, (2) 알림 표시 조건이 `absolute_claim_blocked`만 체크하고
`scope_qualifier_required`는 누락돼 있어 지시서 원문대로 OR 조건으로 수정. 재검증 137/137 통과 유지.
tag_name/db_path 실배선, QueryAuditLog 배선, Research/SermonDraft UI는 계획대로 미착수.

**Sprint C 완료 (2026-07-29, C1 Task Order 022):** `core/parallel_retriever.py`(ParallelRetriever, T1축=
기존 RetrievalEngine.retrieve() 그대로 감싸기 + T2축=bible_tag_annotation 조회), `classify_evidence()`.
CUE 재검증: **39/39 통과**(9 신규 + 30 기존, 보고 수치와 일치), `git diff core/retrieval.py` 빈 diff 확인됨.
비고: `ScriptureReference`에는 애초에 정경 순서 비교 유틸이 없어 C1이 `_BOOK_ORDER` 딕셔너리를 신규 작성함
(지시 위반 아님, 재사용 대상 부재). 정경순서 정렬 자체는 수동 검증으로 정상 동작 확인했으나, 전용 단위
테스트는 누락 — Sprint D 착수 전 추가 권고(경미, 블로커 아님).

**Sprint B 완료 (2026-07-29, C1 Task Order 021):** `bible_tag_annotation`/`dataset_license`/`ingestion_run`
3테이블 추가(6테이블 DDL 확인됨), `core/tag_ingest_validator.py`(TagIngestValidator), `core/dataset_adapters/`
(DatasetAdapter ABC + FixtureAdapter). CUE가 직접 재실행 검증: **30/30 통과**(Sprint A 20 +
`test_tag_ingest_validator.py` 6 + `test_dataset_adapters.py` 4) — C1 보고서의 "34/34(9+5)"는 부정확했음,
실측치로 정정. `core/retrieval.py` 미접촉 git status로 재확인. 실제 외부 데이터셋 조달·`core/retrieval.py`
연동·벡터 청크 백필은 계획대로 이후 Task Order로 이월.

---

## 4. 현재 코드베이스와의 연결점

- `core/retrieval.py::RetrievalEngine.retrieve()` — Sprint C의 `ParallelRetriever`가 이 함수를 감싸거나
  대체. 기존 BM25/TfidfVectorizer/theological_score 로직은 T1 근거 계산 축으로 재사용 가능.
- `_scripture_alignment_score`, `ScriptureReference` — canonical reference 정규화 로직과 연동 지점.
- `ui/` — 승인/보류/거부 UI는 **구현하지 않음**(v1에서 계획했던 배지 4종 중 "검토 상태" 배지는 제거,
  "근거 유형/데이터셋/결론 범위/제한" 4종 표시로 대체).

---

## 5. 수용 기준 (지시서 원문)

- [ ] 사용자는 승인·보류·거부 없이 검색·답변 수신.
- [ ] 자연어 질의 시작, 사전 태그 선택 불필요.
- [ ] 모든 외부 태그가 데이터셋명/버전/namespace/범위/trust tier 보유.
- [ ] T2 태그 단독으로 절대 주장(최초/유일/전체) 생성 금지.
- [ ] 위험 질의에 범위·근거 한계 자동 표시.
- [ ] 본문 근거/큐레이션 태그/문헌 근거 구분 표시.
- [ ] 질의·확장·데이터셋·버전·ClaimGuard 판정 자동 기록.
- [ ] 데이터셋 버전 기준 과거 검색 재현 가능.
- [ ] 원문/태그 메타데이터/provenance/벡터청크 저장 역할 분리.
- [ ] 기존 RAG 품질·성경 참조 정확도 회귀 테스트 통과.

## 6. 명시적 금지 사항 (지시서 원문)

- 매 검색마다 사용자 승인/보류/거부 요구.
- provenance 없는 태그를 T1~T3 근거로 사용.
- 동일 이름 태그를 출처 다른데도 병합.
- T2 단독으로 보편적 신학 명제 생성.
- LLM 자동 태그를 큐레이션 데이터셋과 동일 신뢰도로 표시.
- 라이선스 불명확 외부 데이터셋 원문 무단 적재.
- 벡터 유사도만으로 태그/해석 사실성 확정.

---

## 7. 미해결 사항 (사용자 확인 필요)

1. ~~구조화 저장소 선택~~ → **결정됨 (2026-07-29): SQLite.** PostgreSQL 신규 도입 없이 SQLite 파일로
   `dataset_registry / tag_definition / bible_tag_annotation / dataset_license / ingestion_run /
   query_audit_log` 6개 테이블 구성. 경로는 Sprint A Task Order에서 확정.
2. Sprint A 착수 여부/시점.
3. 기존 청크(이미 ingest된 데이터)에 `canonical_reference`/`trust_tier` 백필하는 범위 — 전체 재인제스트가
   필요한지, 마이그레이션 스크립트로 충분한지 확인 필요.

진행률: 0% (v1 폐기, v2 계획 수립 완료, 구현 미착수)
