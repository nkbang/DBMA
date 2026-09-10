# C1 Review 결과 — NAE-TSU-BUILDER-RESUME-001 (Gap 1 resume + Gap 2 claim.py timeout)

- 검토 요청서: `docs/NAE_FULLER_TSU_BUILDER_RESUME_C1_REVIEW_REQUEST_001.md`
- 설계: `docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md`
- Build Report: `docs/NAE_FULLER_TSU_BUILDER_RESUME_BUILD_REPORT_001.md`
- 검토 대상: 브랜치 `claude/tsu-builder-resume-abf035` (HEAD `fbcdeef`, base `origin/dev/dbma-engine` @ `daca402`)
- 검토 주체: **C1 (Cline 독립 검토)** — 문서 검토 + 코드 read-only
- 기록: 본 문서는 **C1이 산출한 판정을 HQ가 이 세션에 릴레이한 것**을 CUE가 정리·커밋한 것 (2026-09-10). C1 원문 판정 요약을 그대로 옮기고, CUE가 pre-check로 교차 확인한 항목을 §3에 병기.

---

## 1. 판정: 🟢 GREEN

12개 검토 질문 **전부 GREEN**. 변경의 타당성, 불변식 보장, ADR 정합 모두 확인.
차단 findings 없음. 권고사항 2건(비필수) — §4.

---

## 2. 질문별 판정 (C1)

### Gap 1 — resume

| # | 질문 | 판정 | C1 비고 |
|---|---|---|---|
| 1 | `(page, paragraph_index, sentence_index)` 3-튜플 키 유일성 | 🟢 | 유일성 가정 타당 |
| 2 | canonical.json drift abort 경계 | 🟢 | canonical.json 변경 시 반드시 abort — 경계 정확 |
| 3 | `next_id` = tsu.json 권위 + sequential F2 전제 | 🟢 | id 충돌 불가 |
| 4 | 원자적 기록 + torn write | 🟢 | `os.replace` 원자성 + 기록 순서 + `max()` 보정 → 창 닫힘 |
| 5 | byte-identical 불변식 논증 | 🟢 | 논증 타당, 허점 없음 |
| 6 | 회귀 4건 커버리지 | 🟢 | 충분. torn-write 명시 테스트는 권고(비필수) |

### Gap 2 — claim.py HTTP timeout

| # | 질문 | 판정 | C1 비고 |
|---|---|---|---|
| 7 | `Client(timeout=180)` 전환이 결정성/출력에 무영향 | 🟢 | transport만 변경 — 추출 로직/출력 불변 |
| 8 | timeout → fail-soft → `llm_errors ≥ 2%` 게이트 → STOP 체인 | 🟢 | 체인 성립 |
| 9 | `CLAIM_HTTP_TIMEOUT_S = 180` 값, `_CLIENT` 모듈 레벨 재사용 | 🟢 | 180s 적정, 재사용 부작용 없음 |
| 10 | `nae_fuller_cjk_reextract.py` 동일 패턴 | 🟢 | 적용 타당 |

### 공통

| # | 질문 | 판정 | C1 비고 |
|---|---|---|---|
| 11 | `builder_version` `3.0.0` 유지 | 🟢 | 타당. Amendment A 갱신 불필요 |
| 12 | ADR-030 / 013 / 024 / 029 정합 | 🟢 | 위반·우회 없음 |

---

## 3. CUE pre-check 교차 확인 (2026-09-10, B 실행 전)

C1 판정을 뒷받침하는 CUE 측 독립 확인:

| 항목 | 결과 |
|---|---|
| Merge 방식 | `dev/dbma-engine(daca402)`가 브랜치의 조상 → **clean fast-forward** (divergence 0) |
| C1 권고 #2 — Vol.04–08 candidate 키 유일성 | ✅ **전부 dup=0** — Vol04 5,680 / Vol05 5,318 / Vol06 5,186 / Vol07 6,439 / Vol08 7,407 candidate에서 `(page,paragraph,sentence)` 중복 없음 |
| Vol.03 중단 시점 상태 | `tsu_report.json` evaluated=1,000 · claims=567 · `tsu.json` 567 records → **consistent (torn write 없음)**. `tsu_id_state.json next_id=13262` |
| 라이브 트리 반영 | merge 후 `config.CLAIM_HTTP_TIMEOUT_S`·`claim._CLIENT`·`builder.py resume`·`run_fuller_f2.sh --resume` 전부 존재 확인 |

---

## 4. 권고사항 (비필수 — 차단 아님)

1. **torn-write 명시 테스트**: `tests/test_nae_tsu_builder.py`에 "tsu.json이 tsu_report.json보다 많은 record를 가진 경우(report 기록 직전 crash)" 케이스 추가 권장. → F0 백로그.
2. **Vol.04–08 키 유일성 재확인**: → **§3에서 CUE가 확인 완료 (dup=0).** 해소됨.

---

## 5. Evidence Before Promotion Rule 상태

| 조건 | 상태 |
|---|---|
| 1. 구현 완료 | ✅ |
| 2. 회귀 테스트 통과 | ✅ (대상 스위트 61 passed, NAE 서브셋 1397 passed / 2 skipped) |
| 3. C1 독립 검토 완료 | ✅ **GREEN (본 문서)** |
| 4. HQ 승인 | ✅ 2026-09-10 (HQ가 GREEN 릴레이 + B 실행 승인) |

→ 4조건 충족. `dev/dbma-engine` 병합 및 F2 재개(`--resume`) 인가됨.

---

## 6. 후속

- 병합: `claude/tsu-builder-resume-abf035` → `dev/dbma-engine` (fast-forward `daca402..c01c1dd`) — **실행됨 2026-09-10**.
- F2 재개: Vol.03가 `--resume`으로 candidate 1,000 / 567 claims 지점부터 이어서 처리.
- Gap 3 watchdog(`scripts/nae_f2_watchdog.sh`)은 baptist-theology-research 세션이 별도 추가.
- 권고 #1(torn-write 테스트)은 F0 백로그.
