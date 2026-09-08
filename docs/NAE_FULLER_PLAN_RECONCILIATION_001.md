# CUE 정합 검토 — Fuller 두 계획 문서 충돌

- 작성: CUE / 2026-09-08
- 트리거: `docs/NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` (`05e6871`) 통보

---

## 판정: 🟡 병행 문서 충돌 — HQ 정합 결정 필요 (착수 보류)

CLAUDE.md "작업 명령서와 기존 승인 설계 문서 충돌 시 중단·확인" 규칙에 따라
자동 진행하지 않고 아래를 HQ에 제시한다.

---

## 1. 현재 두 갈래

| | RESUMPTION_PLAN_v1 | Vol.01 파일럿 트랙 |
|---|---|---|
| 커밋 | `05e6871` | `177e981` |
| 브랜치 | `claude/corpus-fuller-validation-63c292` (**`dev/dbma-engine` 아님**) | `origin/dev/dbma-engine` (push됨) |
| 범위 | Vol.01–08 전체, F0–F6 | Vol.01 단독 |
| 상태 인식 | P-1 HOLD 해제 "미승인", P-4 C1 Review "미요청" | HQ 결정 B 완료, tiered 설계 APPROVED, 검수 배치 37개 생성 |

→ RESUMPTION_PLAN은 **Vol.01 파일럿 진행 상황을 반영하지 않은 병행 산출물**
(SPRINT34 / PR #4 중복 재구현과 동일 패턴 — [[feedback_stale_base_verify]]).

---

## 2. 겹치는 부분 (정상)

- F0→F6 골격 ≈ 파일럿 Phase 0→3 + Vol.02–08(파일럿은 정당하게 제외)
- F4/F5/F6 (embed / additive index / retrieval 활성화) = 파일럿 Phase 3과 동일 실체
- P-5 (3,319 baseline additive-only) = 파일럿 설계와 일치

## 3. RESUMPTION_PLAN이 **추가로 드러낸 실제 갭** (파일럿이 놓침)

1. **Provenance / citation 한계** (canonical `normalize_report.json` 실측):
   - `page_count = 1` → **page-level citation locator 불가** (전 문단이 page 1)
   - Vol.03 / Vol.07 `scripture_references_found = 0`
   - `footnotes_extracted = 0` (8/8), confidence uncalibrated (모델 self-report)
   - 생성 모델 `my-theology-bot-v2:latest`
   → 파일럿의 검수 절차서·배치에는 **citation locator 규칙도 disclosure 정책도 없음.**
     David 검수 착수 전(늦어도 F5 retrieval 노출 전)에 확정 필요 = 플랜의 **F1**.
2. **ADR-030 Amendment (P-2)** — provenance 한계 수용·citation disclosure 명문화.
   파일럿은 미작성.
3. **C1 Review (P-4)** — "TSU pipeline 진입 직전" 트리거. CUE가 보류 항목으로만
   표시했고 **실제 요청 안 함.**

## 4. 충돌 지점

| 항목 | RESUMPTION_PLAN | 파일럿 | 정리 방향 |
|---|---|---|---|
| HOLD 해제 권한 | ADR-030 Amendment 필요 (P-2) | HQ 결정 B로 진행 | **HQ 판단**: 결정 B로 충분한가, Amendment 선행인가 |
| F3 검수 방식 | `batch_manager.py` + 균일 검수 | 전용 드라이버 + tiered(P1/P2) | 파일럿 방식 채택 (`batch_manager.py::TSU_IDENTIFIERS` 하드코딩 때문에 전용 드라이버가 옳음) |
| Vol.01 배치 | 미생성 전제 | `fuller_v01_batch_0001..0037` 생성·커밋됨 | 파일럿 산출물 유지 |
| 브랜치 | `claude/corpus-fuller-validation-63c292` | `dev/dbma-engine` | `05e6871`를 `dev/dbma-engine`로 병합 |

---

## 5. CUE 권고

1. **RESUMPTION_PLAN_v1을 상위(우산) 계획으로 채택.** Vol.01 파일럿 = 그
   계획의 F2(Vol.01)+F3(Vol.01) 진행 중 인스턴스로 편입. F1은 아직 미이행.
2. `05e6871` → `dev/dbma-engine` 병합, 두 문서 상호 참조 추가.
   플랜 §2/§3를 Vol.01 파일럿 상태로 갱신(P-1 = Vol.01 한정 결정 B 완료 /
   배치 생성됨 / tiered). 플랜 F3를 전용 드라이버·tiered로 수정.
3. **F1 먼저 실행** (canonical 8권 재검증 + citation locator 규칙 + disclosure
   정책) — David 검수 착수 **전**. 산출물 `NAE_FULLER_CANONICAL_VERIFICATION_001.md`.
4. **C1 Review(P-4) 요청** — TSU pipeline 진입 트리거. 대상 = 파일럿 배치 설계
   + F1 provenance 규칙 + F2 계획.
5. ADR-030 Amendment(P-2) 필요 여부·범위 = HQ 결정. 최소한 citation
   disclosure 규칙은 Amendment 또는 처리 지시서로 고정.

---

## 6. HQ 결정 요청

- [ ] RESUMPTION_PLAN_v1 = 우산 계획으로 채택? (Vol.01 파일럿을 그 안에 편입)
- [ ] `05e6871`를 `dev/dbma-engine`로 병합 승인?
- [ ] F1(canonical/provenance 검증) 을 David 검수 착수 전 선행으로?
- [ ] C1 Review(P-4) 지금 요청?
- [ ] ADR-030 Amendment(P-2) 착수 여부·범위?
- [ ] HOLD 해제 권한: HQ 결정 B로 충분 vs Amendment 선행?
