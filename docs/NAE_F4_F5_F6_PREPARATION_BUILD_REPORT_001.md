# Build Report — NAE-F4-F5-F6-PREPARATION-001

**작성:** CUE · 2026-09-12
**설계:** `docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md`
**브랜치:** `claude/nae-f4-f5-f6-prep` (base `origin/dev/dbma-engine` @ `3b34186`)

---

## STATUS

**IMPLEMENTED — 회귀 PASS. C1 Independent Review 요청서 작성 완료, 검토·HQ 승인 대기.**

작업 명령서 초안(신규 플래그 `NAE_BRIDGE_CHAT_ENABLED`, `chat.py` 답변에 NAE 결과
병합)이 Approved ADR-024 §B/§E/§F와 충돌함을 CON-012 선결 판독 중 발견 →
Architecture Freeze Rule에 따라 구현 중단, 사용자 확인 → **"ADR-024 그대로 준수"**로
확정(2026-09-12) → 이하 F6을 그 결정대로 재설계·구현했다.

F4/F5는 코드·단위테스트만 — Ollama/Qdrant 실호출 없음(Amendment A §8: F4/F5/F6
실행은 Amendment Approved 이후). F4 dry-run은 실제로 1회 실행해 verified=0(no-op)을
확인했고, F5는 dry-run조차 production `nae_qdrant`에 대해 실행하지 않았다(전부 mock
단위테스트로 검증).

---

## Changed Files

| 파일 | 변경 |
|---|---|
| `docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md` | 신규 — CON-012 판독 결과, ADR-024 충돌·해소, F4/F5/F6 설계, 제약 준수표, acceptance 계획 |
| `docs/NAE_F4_F5_F6_C1_REVIEW_REQUEST_001.md` | 신규 — C1 검토 요청서 + relay 문구 |
| `docs/NAE_F4_F5_F6_PREPARATION_BUILD_REPORT_001.md` | 본 문서 |
| `ui/components/nae_public_section.py` | 신규 — `research.py`의 NAE 섹션 렌더 로직을 `key_prefix` 파라미터화해 추출·공유. Amendment A §6 disclosure 렌더 추가(`_render_nae_paragraph_card`). |
| `ui/pages/research.py` | `_render_nae_section()` 본문(~155줄)을 공유 컴포넌트 호출 1줄로 교체. import 1줄 추가. 동작 동일(로직 이동만), session_state 키만 `research_` 접두로 변경. |
| `ui/pages/chat.py` | import 1줄 + `render_nae_public_section(key_prefix="chat")` 호출 1줄(footer 직전). `generate_answer`/`_handle_user_message` 등 답변 생성 경로 무수정. |
| `NAE/citation_disclosure.py` | 신규 — Amendment A §6 고정 KR/EN disclosure 텍스트, `get_disclosure(authority_class)` |
| `scripts/nae_fuller_f4_embed.py` | 신규 — F4 준비 스크립트. dry-run 기본(Ollama 호출 0), `--apply` 게이트. Fuller verified TSU만 대상, 기존 embed client/hashing 재사용. |
| `scripts/nae_fuller_f5_upsert.py` | 신규 — F5 준비 스크립트. dry-run 기본(Qdrant 쓰기 0), `--apply` 게이트 + baseline(3,319) drift/point-id 충돌 시 `BaselineDriftError`로 즉시 거부. F4 캐시만 소비. `nae_corpus_reconcile.py` 통합. |
| `tests/test_nae_f6_chat_wiring.py` | 신규(9건) — 단일 스위치, 병합 없음, disabled=no-op, key 네임스페이스, disclosure 매핑 |
| `tests/test_nae_fuller_f4_f5_prep.py` | 신규(5건) — F4/F5 dry-run 외부호출 0건, baseline drift 거부 |

**무접촉 확인**: `core/retrieval.py` git diff 없음. `NAE/pipeline/tsu/`, `NAE/corpus/`
무수정(`git status --porcelain` 확인, F2 실행 트리와 미충돌). `nae_ref_v1`/Smith
경로 무수정. `config.yaml` 무수정(`modules.nae_pd.enabled` 기본값 `false` 그대로).

---

## Tests

- 신규 `tests/test_nae_f6_chat_wiring.py` — 9 passed.
- 신규 `tests/test_nae_fuller_f4_f5_prep.py` — 5 passed.
- `scripts/nae_fuller_f4_embed.py` 실제 dry-run 1회 실행 — `verified_total: 0,
  would_embed: 0` (Fuller F3 미착수 상태와 일치, no-op 확인).

## Regression

- `pytest tests/test_dbma_nae_module_packaging.py tests/test_nae_bridge_full_source_text.py tests/test_nae_retrieval_bridge_integration.py` — 27 passed (기존 NAE bridge/module-gating 회귀 무영향).
- `pytest tests/ -k "nae or chat or research or module_packaging"` — 866 passed, 2099 deselected.
- 전체 스위트는 돌리지 않음([memory: Verification Cost Discipline] — 이번 변경이
  건드린 표면(ui/pages/{chat,research}.py, NAE/, scripts/nae_fuller_*)을 스코프
  회귀로 충분히 덮음, 건드리지 않은 나머지 코드는 전체 스위트를 매번 돌릴 근거 없음).

## Git (Commit/Push)

- 브랜치 `claude/nae-f4-f5-f6-prep`를 `origin/dev/dbma-engine`(`3b34186`) 기준으로
  새로 생성(작업 시작 시 worktree가 오래된 별도 브랜치였음 — base freshness 확인
  후 전환, [memory: Verify Base Freshness]).
- 이 Build Report 커밋 후 CUE Operating Policy에 따라 자동 커밋. TSU Pipeline/
  retrieval architecture 변경 트리거에 해당해 C1 Independent Review 요청서를
  작성했으므로(§ 위), **push는 하되 C1 Review·HQ 승인 전까지 `dev/dbma-engine`
  병합(PR merge)은 하지 않는다** — 이는 policy의 "예외" 목록(architecture 변경)에
  해당하는 신중 조치.

## Next

1. `docs/NAE_F4_F5_F6_C1_REVIEW_REQUEST_001.md` §5의 relay 문구를 C1(Cline)에
   전달 — 독립 검토 요청.
2. C1 GREEN + HQ 승인 → Amendment A 승격 4조건 중 "구현+회귀+C1 검토" 3개 충족
   (F2/F3 자체 완료는 별도 트랙). 승격 후에만 F4/F5 `--apply`, F6
   `modules.nae_pd.enabled: true` 실제 전환 가능.
3. Fuller F3(인간 검수) 완료로 verified count가 늘어나면 F4 dry-run 리포트로
   재확인.
