# Grounded Synthesis P3A → Final — 여정 인덱스 · 공통 규칙 · CUE 교차검증 절차

- 작성: CUE, 2026-09-27
- 근거: HQ "P4 → Final Conclusion 전체 작업여정 및 심층 점검 지시서"(2026-09-27),
  CUE 검토 `docs/architecture/DBMA-Grounded-Synthesis-P4-Final-Journey-CUE-Review-2026-09-27.md`
- 설계 정본: `docs/architecture/ADR-036-Grounded-Synthesis-Boundary.md` (Proposed)
- 이 폴더의 작업 지시서(WO)는 **한 번에 하나씩** C1에게 전달한다.
  다음 WO는 이전 Phase가 CUE GREEN + HQ 승인을 받은 뒤에만 전달한다.

---

## 1. 기본값으로 정한 결정 (HQ가 바꾸면 해당 WO를 개정)

| ID | 결정 | 기본값 | 근거 |
|---|---|---|---|
| D1 | 로드맵 정본 | **이번 HQ 지시서의 P4~P12가 정본.** 기존 로드맵의 Context Expansion / Evidence Classification / Multi-Source Assembly는 **폐기가 아니라 보류**(후속 여정 후보)로 둔다 | HQ의 최신 지시 |
| D2 | 생성 권위 | **(a) 병렬 검증 계층.** `core/generation.py`는 운영 경로로 그대로 두고, Grounded Synthesis는 P12까지 UI에 연결하지 않는다 | 운영 경로 교체는 되돌리기 어렵다. 연결은 P12 이후 별도 ADR로 다룬다 |
| D3 | 감사 게이트 | HQ 원문대로 **P10 / P11 / P12를 따로** 운영한다. HQ가 원하면 세 WO를 한 번에 전달해도 된다 | HQ 원문 구조 존중 |
| O1 | 교단 지시문(`_DENOMINATION_DIRECTIVE`) | Grounded Synthesis 프롬프트에서 **제외**한다 | 교리 주입 이슈가 HQ 판단 대기 중. 근거 경계를 넓히는 요소이므로 기본값은 제외 |

## 2. Phase 목록과 선행 게이트

| Phase | WO 파일 | 핵심 산출물 | 선행 게이트 |
|---|---|---|---|
| G0 | (HQ 결정) | C1 트리에 staged된 비-GS 변경 6건 처리 | — |
| P3A | `GS-P03A-WO-Assembly-Manifest.md` | `EvidenceAssembly` manifest (질의→근거 연결 보존) | P3 진행 중(보고 전 적용) |
| P4 | `GS-P04-WO-Synthesis-Input-Boundary.md` | `core/grounded_synthesis_input.py` | P3(+P3A) GREEN·HQ 승인, ADR-036 존재 |
| P5 | `GS-P05-WO-Claim-Evidence-Binding.md` | `core/grounded_claims.py` | P4 승인 |
| P6 | `GS-P06-WO-Grounded-Answer.md` | `core/grounded_answer.py` | P5 승인 |
| P7 | `GS-P07-WO-Citation-Provenance.md` | `core/grounded_citation.py` | P6 승인 |
| P8 | `GS-P08-WO-Failure-Paths.md` | `tests/test_grounded_failure_paths.py` | P7 승인 |
| P9 | `GS-P09-WO-Integration.md` | 실행 스크립트 2개 + 통합 테스트 + 실모델 실행 | P8 승인 |
| P10 | `GS-P10-WO-Regression.md` | 회귀·아키텍처 무결성 보고 | P9 승인 |
| P11 | `GS-P11-WO-Production-Safety.md` | 운영 안전 감사 보고 | P10 승인 |
| P12 | `GS-P12-WO-Scope-Audit-Final-Report.md` | 감사 팩 + 최종 구현 보고서 | P11 승인 |
| Final | `GS-FINAL-CUE-VALIDATION.md` | CUE 최종 검증(7문항) | P12 보고 수신 |

### G0 — C1 트리의 staged 변경 (P3 커밋 전에 HQ 결정 필요)

`/Users/David/DBMA`(feat/peb-v0.1)의 인덱스에 Grounded Synthesis와 **무관한 변경 6건이 staged 상태**로 있다
(2026-09-27 00:08~00:20 생성, 주석 표기 "[P1 최적화]" = 성능 작업이며 GS P1과 다름).

```
M config.yaml                       (modules.nae_pd.enabled false → true)
M core/candidate_generator.py       (색인 최신성 검사를 tsu_manifest.json tsu_count로 대체)
M core/hybrid_candidate_pipeline.py (tsu_by_id lazy loading 등, +149/-?)
A scripts/merge_nae_corpus.py
A scripts/process_unprocessed_nae.py
A scripts/test_default_corpus_query.py
```

- 위험: 경로를 지정하지 않고 `git commit`을 하면 이 retrieval 변경이 **GS 커밋에 섞인다**
  (STOP #4·#15에 해당하는 이력 오염).
- HQ 결정 필요: (a) 소유 작업을 확인해서 별도 브랜치로 옮기거나, (b) 그대로 두되 GS 커밋은 경로 지정 커밋만 허용.
- **결정 전 기본값: (b).** 공통 규칙 R1이 경로 지정 커밋을 강제한다.
  P10 회귀는 이 변경의 영향을 받지 않도록 clean worktree에서 실행한다.

## 3. 공통 규칙 (모든 WO에 적용 — 각 WO에 요약본 포함)

- **R1 커밋·푸시**
  - C1은 CUE GREEN과 HQ 승인 전에는 커밋하지 않는다.
  - 승인 후 커밋은 반드시 경로를 지정한다: `git commit -m "<msg>" -- <허용 파일들>`.
  - 커밋 직후 `git show --stat HEAD` 출력을 보고한다. 허용 파일 외의 파일이 들어가 있으면 즉시 보고한다(되돌리기는 HQ 지시로만).
  - push 대상은 `origin feat/peb-v0.1`이다. force push는 금지한다.
- **R2 범위**
  - WO의 "허용 파일" 외에는 생성·수정하지 않는다.
  - G0의 staged 파일 6건은 열람만 가능하고 **stage/unstage/수정 모두 금지**한다.
- **R3 판정 금지**
  - C1은 GREEN / APPROVED / ARCHITECTURE APPROVED를 선언하지 않는다.
  - 보고서 마지막 줄은 다음 셋 중 하나다: `HOLD` / `CUE READ-ONLY REVALIDATION REQUESTED` / `STOP CONDITION TRIGGERED`.
- **R4 증거**
  - 보고서의 모든 수치(테스트 수, 파일 수, 건수)에는 그 수치를 만든 **명령과 출력 원문**을 붙인다.
  - 출력 없이 쓴 수치는 CUE가 무효로 처리한다.
- **R5 불변 계약**
  - 다음은 수정하지 않는다. 수정이 필요해지면 STOP한다:
    `core/evidence_model.py`, `core/evidence_pool.py`, `core/evidence_adapters/*`, `core/retrieval.py`,
    `core/hybrid_candidate_pipeline.py`, `core/candidate_generator.py`, `core/generation.py`, `core/claim_guard.py`, `ui/*`.
  - 승인된 이전 Phase 모듈의 공개 계약도 수정하지 않는다.
- **R6 금지 import·호출** (`core/evidence_assembly.py`, `core/grounded_*.py`)
  - import 금지: `ollama`, `qdrant_client`, `tantivy`, `requests`, `httpx`, `urllib`, `subprocess`, `socket`
  - 호출·import 금지: `QueryProcessor`, `HybridQueryProcessor`, `RetrievalEngine`, `HybridRetriever`, `CandidateGenerator`, `GenerationService`
  - 예외: `core.retrieval.RankedCandidate`(타입), `core.generation._GROUNDING_DIRECTIVE`(상수 읽기 — P6만 허용)
  - 실행 스크립트(P9)는 호출자 자격으로 검색 프로세서와 ollama를 사용할 수 있다.
- **R7 테스트 격리**
  - 테스트는 파일을 `tmp_path`에만 쓴다.
  - 경로 인자에 기본값이 있으면 테스트에서 전부 override한다.
  - 운영 데이터 경로(`output/bench/*`, `NAE/*`, Qdrant)는 열지 않는다.
- **R8 결정성**
  - 단위·통합 테스트는 stub LLM만 사용하며 네트워크와 GPU 없이 통과해야 한다.
  - 실모델 결과는 품질 근거로만 따로 보고한다(P9).
- **R9 실행 환경**
  - `~/envs/dbma311/bin/python -m pytest`로 실행한다. 다른 venv는 사용하지 않는다.
  - 작업 위치: `/Users/David/DBMA`, 브랜치 `feat/peb-v0.1`.

## 4. STOP 조건

HQ 원문의 1~18에 CUE가 19~23을 추가한다. 하나라도 해당하면 수정해서 계속하지 말고
`STOP CONDITION TRIGGERED`로 보고한다(몇 번 조건인지, 발견 위치, 근거 출력 포함).

1. 기존 retrieval 인터페이스가 문서화된 구조와 다름
2. Evidence 모델 수정이 필요함
3. EvidencePool 공개 계약 수정이 필요함
4. RetrievalEngine 수정이 필요함
5. 새 retrieval 경로가 필요함
6. 새 ranking 로직이 필요함
7. Query expansion 엔진이 필요함
8. LLM retrieval이 도입됨
9. 외부 검색이 도입됨
10. Qdrant mutation 발생
11. Tantivy mutation 발생
12. TSU mutation 발생
13. Benchmark 인프라를 바꿔야 함
14. 기존 테스트가 회귀함
15. 승인 범위 밖 파일이 필요함
16. Citation을 Evidence까지 추적할 수 없음
17. Claim을 Evidence에 결속할 수 없음
18. 근거 부족을 안전하게 표현할 수 없음
19. core 모듈에서 LLM을 직접 호출해야 함(새 LLM client나 운영 프롬프트 경로가 필요함)
20. 합성 입력 선택에 점수 계산이나 재정렬이 필요함
21. `ui/` 또는 운영 모듈이 grounded 모듈을 import해야 함(D2 위반)
22. G0 staged 변경과 GS 변경을 분리할 수 없음
23. 승인된 이전 Phase의 공개 계약 변경이 필요함

## 5. CUE 교차검증 절차 (C1 보고를 받을 때마다 CUE가 매번 수행)

| 단계 | 내용 | 명령/방법 |
|---|---|---|
| V0 | 보고 원문 보존 | `docs/grounded_synthesis/reviews/GS-Pn-C1-REPORT-rN.md`로 저장 |
| V1 | 환경 확인 | `git -C /Users/David/DBMA rev-parse --show-toplevel`, `branch --show-current`, `rev-parse HEAD`, `remote -v` — 다른 저장소나 브랜치를 감사하는 사고를 막는다 |
| V2 | 범위 확인 | `git status --porcelain`(untracked 포함) vs 허용 파일. `git diff --cached --stat`이 G0 기록(6건)과 같은지 |
| V3 | 정적 검사 | R6 금지 import·호출 grep, `to_dict(` 사용 여부, 파일 쓰기(`open(`, `write_text`) 위치 |
| V4 | 코드 정독 | WO의 AC를 한 줄씩 대조. 테스트가 동어반복(tautology)인지도 확인 |
| V5 | 독립 재실행 | `PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest -p no:cacheprovider <이번 Phase 테스트> <이전 Phase 테스트> -q` |
| V6 | 수치 대조 | C1 보고의 수치와 CUE 실측이 다르면 불일치로 기록(날조·오래된 보고 탐지) |
| V7 | 적대적 프로브 | CUE가 scratchpad에서 이번 Phase의 핵심 불변식을 C1 테스트와 무관한 입력으로 직접 실행 |
| V8 | 판정 | GREEN / HOLD / RED. HOLD·RED이면 REWORK WO(`GS-Pn-REWORK-rN.md`)를 함께 발행 |
| V9 | 기록 | `docs/grounded_synthesis/reviews/GS-Pn-CUE-REVIEW-rN.md` + 메모리 갱신. HQ에게 15줄 이내로 보고 |

판정 기준:
- **GREEN**: 모든 AC 충족, V2·V3 위반 0, V5 전부 PASS, V6 불일치 0(또는 무해함을 설명 가능), V7 통과
- **HOLD**: 수정 가능한 결함(AC 미충족, 테스트 누락, 보고 수치 불일치)
- **RED**: STOP 조건 해당, 불변 계약 위반, 범위 밖 수정, 증거 날조

CUE는 코드를 고치지 않는다. 결함은 REWORK WO로만 되돌려 보낸다.

## 6. 운영 데이터 기준선

`reviews/GS-SAFETY-BASELINE-CUE-20260927.json` — P4 착수 전 CUE가 읽기 전용으로 기록했다
(tsu_dataset.jsonl sha256, tsu_manifest.json, tantivy_index 집계 해시 132개 파일).
- Qdrant는 기록 시점에 미실행이었으므로 P9 실행 전 스냅샷에서 기록한다.
- 매 Phase 교차검증(V2)에서 이 해시가 변하지 않았는지 확인한다.
- 변했다면 GS 작업 때문인지 외부 작업 때문인지 판별해서 기록한다.

## 7. 보고서 공통 양식 (C1)

```
PHASE n WORK ORDER REPORT
1. Files changed          (git status --porcelain 원문)
2. Existing Architecture Verification (읽은 파일:줄, 확인한 인터페이스)
3. Design                 (구현한 공개 API 시그니처 전문)
4. Implementation notes
5. Tests                  (pytest 명령 + 마지막 요약줄 원문, 테스트명 목록)
6. AC 대조표              (AC-id | 충족 여부 | 근거: 테스트명 또는 출력)
7. Production safety      (R5·R6·R7 준수 확인 방법과 출력)
8. Remaining issues       (숨긴 가정 없이 전부)
9. Phase recommendation   → 마지막 줄: HOLD | CUE READ-ONLY REVALIDATION REQUESTED | STOP CONDITION TRIGGERED
```

## 8. 진행 현황

- [x] P1 Evidence Data Model — `2dd40d2e`
- [x] P2 EvidencePool — `db677ac6`
- [x] P3 + P3A Multi-Query Assembly + Manifest — `14fccb54` (r1 HOLD → r2 HOLD → r3 GREEN, HQ 승인 2026-09-27)
- [x] ADR-036 Grounded Synthesis Boundary — Accepted (2026-09-27, P3A 승인과 함께 처리)
- [x] P4 Synthesis Input Boundary — `9eae5167` (r1 첫 제출 GREEN, HQ 승인 2026-09-27)
- [x] P5 Claim-Evidence Binding — `20bf6ddd` (r1 첫 제출 GREEN, HQ 승인 2026-09-27)
- [x] P6 Grounded Answer — `2e3eaeea` (r0 잘못된 대상 오전달 → r1 재지시 후 GREEN, HQ 승인 2026-09-27)
- [x] P7 Citation/Provenance — `f9f4a55f` (r1 HOLD: id_exists short-circuit 결함 → r2 GREEN, HQ 승인 2026-09-27)
- [x] P8 Negative/Failure-path Validation — `e5eecd5f` (r1 HOLD: Case C/D P3A 미통과 → r2 HOLD: citation check 대체pool 우회(+1회 재전송) → r3 GREEN, HQ 승인 2026-09-27)
- [x] P9 Full Integration Test — `5738c709` (r1 HOLD: 프롬프트 evidence_id 누락 → r2 HOLD: 정본 결과파일 미갱신(+2회 재전송) → r3 GREEN, HQ 승인 2026-09-28. 첫 실모델 실행: A1/B1 grounded 도달 실증)
- [x] P10 Regression/Architecture Integrity Audit — `0d265afc` (r1 첫 제출 GREEN, HQ 승인 2026-09-28)
- [ ] G0 staged 변경 처리 결정 (HQ) — 계속 보류, GS 커밋은 경로 지정으로 계속 격리
- [ ] P11 ~ P12, Final

진행률: 약 73% (P1/P2/P3A/P4~P10 GREEN, ADR-036 Accepted, P11 발급)
- 이월 이슈: Claim ID 전역 고유성(P5 CUE 리뷰) — 아직 실사용에서 문제 재현 안 됨, P12에서 재확인
