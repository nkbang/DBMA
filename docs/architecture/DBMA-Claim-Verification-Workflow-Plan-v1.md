# DBMA 검색 결과 검증·승인 워크플로 — 실행 계획서 v1

**작성일:** 2026-07-29
**근거 문서:** PM 작업지시서 "DBMA 검색 결과 검증·승인 워크플로 도입" (본 대화 첨부)
**현재 상태:** ⚠️ **폐기됨 (2026-07-29)** — 후속 PM 지시서에 의해 사용자별 승인/보류/거부 워크플로 방향이
철회되고 [DBMA-Search-Trust-Pipeline-Plan-v2.md](DBMA-Search-Trust-Pipeline-Plan-v2.md)의 무마찰 파이프라인
(Dataset Registry + ClaimGuard)으로 대체됨. 이 문서는 이력 보존용으로만 유지.

---

## 0. 현황 파악 요약

- 현재 검색/RAG 코어는 [core/retrieval.py](core/retrieval.py) (`RetrievalEngine`, ~2200줄) 하나에 집중되어 있다.
  - `QueryParser`, BM25, `TfidfVectorizer`, `compute_theological_score`, `_scripture_alignment_score`,
    `_thematic_relevance_score`, `_sermon_usability_score` 등 랭킹 요소는 이미 존재.
  - `Prayer`/`Command`/`Promise` 같은 **의미·담화 태그 검색 축은 아직 없음** — 이번 작업지시서가 요구하는
    "복수 검색 축 병렬 수행" 자체가 신규 기능이다.
- `claims` / `claim_evidence` / `claim_alternatives` / `claim_reviews` 데이터 모델은 존재하지 않음 (신규 테이블).
- UI(`ui/`)에도 Claim Verification Card, 승인/보류/거부 상태 배지 등 대응 컴포넌트 없음 (신규).
- 결론: 이 기능은 **기존 흐름에 신규 레이어를 얹는 작업**이며, 원본 지시서의 범위(태그 검색 축 + 검증 카드 +
  상태 관리 + UI + 내보내기 + 강한 주장 감지 규칙)를 한 번에 구현하면 CLAUDE.md의 "작은 단위 수정" 원칙을
  위반한다. 아래와 같이 단계를 쪼갠다.

---

## 1. 단계 분할 (Phase)

### Phase 0 — 스코프 고정 (선행)
- 대상 태그 1개(`Prayer`)만 시나리오로 고정. 다른 태그(Covenant/Command/...)는 구조 재사용성만 검증하고
  실 데이터는 만들지 않음.
- "강한 주장" 트리거 키워드 목록 확정: 최초/유일/처음/반드시/명백히 (한국어) + first/only/earliest 등 (영문 원문 인용 시).
- 산출물: 본 문서에 반영 완료.

### Phase 1 — 데이터 모델 (claims 테이블)
- 저장소: 별도 SQLite 파일 (예: `data/claims.db`, 경로는 Task Order 작성 시 확정). Qdrant는 벡터 전용 유지.
- 스키마: 지시서의 `claims / claim_evidence / claim_alternatives / claim_reviews` 4개 테이블 그대로 채택.
- 산출물: 마이그레이션 스크립트(SQLite DDL) + 최소 CRUD 유닛 테스트.

### Phase 2 — Candidate Generation 확장 (검색 축 추가)
- `core/retrieval.py`에 `Prayer` 태그용 후보 생성 축 1개만 추가 (어휘/화행/문법 축은 Phase 2b로 분리).
- 기존 `RetrievalEngine.retrieve()` 흐름을 깨지 않는 범위에서 병렬 후보 리스트를 반환하도록 확장.
- 산출물: 회귀 테스트로 기존 검색 결과 불변 확인 + 신규 축 단위 테스트.

### Phase 3 — 강한 주장 감지 + Claim 카드 생성
- 응답 생성 단계에서 트리거 키워드 감지 → `claims` 레코드 생성 (status=미검토) 로직.
- `alternative_candidates` 최소 1개 이상 없으면 "최초" 주장 자체를 승인 불가 처리하는 검증 규칙 구현.
- 산출물: 강한 주장 문장 → pending claim 생성 통합 테스트.

### Phase 4 — UI (배지 + 상세 패널 + 승인/보류/거부)
- `ui/` 탭 구조를 유지하며 검색 결과 카드에 배지 4종(데이터 태그/본문 근거/해석 주장/검토 상태) 추가.
- 상세 패널(쿼리/데이터셋/범위/대안 후보/승인 버튼)은 별도 컴포넌트로 분리.
- 산출물: Streamlit 컴포넌트 + 수동 시나리오 검증(스크린샷).

### Phase 5 — 표현 강도 제어 + 보고서/노트 출력 게이팅
- 보류/거부/미검토 상태의 claim은 최종 리포트·설교 초안 생성 경로에서 확정 문장으로 승격되지 않도록 게이팅.
- Obsidian/Markdown 내보내기에 frontmatter(`claim_status`, `dataset`, `alternatives_reviewed` 등) 반영.
- 산출물: 게이팅 로직 단위 테스트 + 내보내기 샘플 파일.

### Phase 6 — 재현성 (데이터셋 버전 · 검색 시점 기록)
- 동일 검색 재실행 시 데이터셋 버전/시점 기록 → `claim_evidence`에 저장.
- 수용 기준 중 "재현 가능" 항목 충족.

---

## 2. 수용 기준 매핑 (지시서 원문 → 담당 Phase)

| 수용 기준 | Phase |
|---|---|
| 데이터셋명/쿼리/범위 제한 표시 | 2, 4 |
| 강한 주장 자동 감지 → 카드 생성 제안 | 3 |
| 승인/보류/거부 + 메모 저장 | 1, 4 |
| 미검토/보류/거부 시 확정 문장 출력 금지 | 5 |
| 대안 후보 없으면 '최초' 주장 승인 불가 | 3 |
| 내보낸 Markdown에 쿼리/출처/범위/검토상태 포함 | 5 |
| 재현성(버전·시점 기록) | 6 |
| 태그를 "후보 생성용"/"강한 근거용"으로 분류 | 1, 2 |

---

## 3. C1(Cline) 위임 가능 여부

- Phase 1(스키마+CRUD), Phase 2(단일 축 추가)는 [[c1_routing_criteria]] 기준상 "단순 치환·TDD 게이팅형" 코드에
  가까워 C1 Task Order로 분리 가능.
- Phase 3(강한 주장 감지 규칙), Phase 4(UI 설계), Phase 5(게이팅 정책)는 개방형 판단이 필요해 CUE(본 세션)가
  직접 설계 후 좁은 범위만 C1에 위임.
- Task Order 문서는 각 Phase 착수 시점에 개별 작성 (현재는 미발급).

---

## 4. 리스크 / 미해결 사항

- ~~Qdrant vs 별도 관계형 스토어~~ → **결정됨 (2026-07-29): 별도 SQLite 파일로 관리**. Qdrant는 벡터 전용 유지(ADR-003 원칙 준수).
- "복수 검색 축 병렬 수행"이 기존 `RetrievalEngine.retrieve()` 성능/랭킹에 미치는 영향 미측정.
- MVP 범위를 `Prayer` 1개로 좁혔지만, 원 지시서는 "모든 의미 태그에 재사용 가능한 구조"를 요구 —
  Phase 2~3 설계 시 태그 하드코딩 금지, 태그 파라미터화 필수.

---

## 5. 다음 조치

- [ ] Phase 1 착수 여부 및 저장소(Qdrant/SQLite 등) 결정 — 사용자 확인 필요.
- [ ] Phase 1 Task Order 작성 (C1 위임 시).

진행률: 0% (계획 수립 완료, 구현 미착수)
