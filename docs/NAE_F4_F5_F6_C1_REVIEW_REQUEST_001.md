# C1 Review 요청 — NAE-F4-F5-F6-PREPARATION-001

- 요청자: CUE
- 일자: 2026-09-12
- 유형: **C1 Independent Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점: TSU Pipeline 진입/변경,
  Metadata Model 변경, ID Governance 변경, Production 승격 직전"에 해당하는 후보
  작업(F4/F5/F6는 Amendment A §8 승격 4조건 중 하나) — production 실행은 아니지만
  ADR-024/Amendment A 정합성이 핵심이라 사전 검토 요청.
- 관련: `docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md` (Approved),
  `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (Proposed),
  `docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md` (본 작업의 설계 문서)

---

## 1. 배경

`docs/DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md` CON-012(HOLD blocking)의 요구대로
ADR-013/ADR-024/ADR-030/ADR-030 Amendment A 본문을 판독한 결과, 작업 명령서 초안이
제시한 F6 설계(신규 플래그 `NAE_BRIDGE_CHAT_ENABLED`, `chat.py` 답변에 NAE 결과 병합)가
**Approved ADR-024 §B/§E/§F와 직접 충돌**함을 발견했다. CUE Operating Policy의
Architecture Freeze Rule에 따라 구현을 중단하고 사용자에게 확인 — **"ADR-024 그대로
준수"**로 결정(2026-09-12). 이 브랜치는 그 결정을 반영해 F6을 재설계·구현했다.

F4/F5는 코드만 준비했고 production 실행(Ollama embed 실호출, Qdrant `--apply` upsert)은
전혀 하지 않았다 — Amendment A §8이 "F4/F5/F6는 Amendment Approved 후에만 착수"로
고정하고 있어, 지금은 코드·테스트만 갖추는 단계다.

---

## 2. 검토 대상 산출물

**브랜치:** `claude/nae-f4-f5-f6-prep` (base `origin/dev/dbma-engine` @ `3b34186`)

| # | 대상 | 내용 |
|---|---|---|
| A | `docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md` | CON-012 판독 결과 + ADR-024 충돌·해소 + F4/F5/F6 설계 + 제약 준수표 + acceptance 계획 |
| B | `ui/components/nae_public_section.py` (신규) | `research.py`에 있던 NAE 섹션 렌더 로직을 추출한 공유 컴포넌트. `key_prefix`로 session_state 네임스페이스 분리. Disclosure 렌더 추가. |
| C | `ui/pages/research.py` (수정) | `_render_nae_section()`을 공유 컴포넌트 호출 1줄로 교체(로직 동일, 위치만 이동) |
| D | `ui/pages/chat.py` (수정) | import 1줄 + `render_nae_public_section(key_prefix="chat")` 호출 1줄 (footer 직전). 그 외 무수정 — `generate_answer`/`_handle_user_message`는 손대지 않음. |
| E | `NAE/citation_disclosure.py` (신규) | Amendment A §6 고정 disclosure 텍스트, `get_disclosure(authority_class)` |
| F | `scripts/nae_fuller_f4_embed.py` (신규) | F4 dry-run 기본, `--apply` 게이트, Fuller verified TSU만 대상, cache 재사용, Qdrant 무접촉 |
| G | `scripts/nae_fuller_f5_upsert.py` (신규) | F5 dry-run 기본, `--apply` 게이트, baseline(3,319) drift/충돌 시 `BaselineDriftError`로 즉시 거부, F4 캐시만 소비(Ollama 미호출), `nae_corpus_reconcile.py` 통합 |
| H | `tests/test_nae_f6_chat_wiring.py` (신규, 9건) | 단일 스위치 준수, 병합 없음, disabled=no-op, key 네임스페이스, disclosure 매핑 |
| I | `tests/test_nae_fuller_f4_f5_prep.py` (신규, 5건) | F4/F5 dry-run이 실제로 외부 호출 0건인지, baseline drift 거부 로직 |

**영향받지 않은 것(확인됨)**: `core/retrieval.py` git diff 없음. `NAE/pipeline/tsu/`,
`NAE/corpus/` 무수정(F2 실행 트리와 겹치지 않음). `nae_ref_v1`/Smith 경로 무수정.
`config.yaml modules.nae_pd.enabled` 기본값 `false` 무변경.

---

## 3. 검토 질문

1. §1.2의 "F6 재설계가 ADR-024 §B(병합 금지)/§E(통합 지점=research.py 패턴)/§F(단일
   스위치)를 실제로 준수하는가"를 `ui/pages/chat.py` diff와 `ui/components/
   nae_public_section.py` 코드로 직접 확인해 달라.
2. `NAE_BRIDGE_CHAT` 문자열이 코드베이스 어디에도 없다는 주장(설계 문서 §5,
   `tests/test_nae_f6_chat_wiring.py::TestSingleSwitchCompliance`)을 grep으로
   재확인.
3. `chat.py::generate_answer`/`_handle_user_message`가 `bridge_query`를 참조하지
   않는다는 주장(같은 테스트 파일 `TestNoMergeIntoGeneration`)을 소스로 재확인 —
   병합이 실제로 없는지가 이 검토의 핵심.
4. `ui/pages/research.py`의 리팩터링(로직을 `nae_public_section.py`로 이동)이
   동작을 바꾸지 않았는지 — `git diff`로 로직 라인 수준 비교, 세션 키 이름 변경
   (`nae_research_query` → `research_nae_research_query`)이 기존 저장된 상태와
   호환성 문제를 일으키는지(Streamlit session_state는 프로세스 재시작 시 초기화되는
   메모리 상태이므로 영향 없다는 설계 문서 주장 검증).
5. `scripts/nae_fuller_f5_upsert.py`의 baseline guard(`EXPECTED_BASELINE_COUNT =
   3319`, `BaselineDriftError`)가 실제로 upsert 전에 실행되는 순서인지, 그리고
   `--apply` 없이는 `client.upsert`가 코드 경로상 도달 불가능한지 코드 흐름으로
   확인.
6. `scripts/nae_fuller_f4_embed.py`가 dry-run에서 `embed_client.embed_text()`
   (Ollama 호출)를 호출하는 코드 경로가 전혀 없는지(`get_cached()`만 호출) 확인.
7. `NAE/citation_disclosure.py`의 Fuller 고정 텍스트가 Amendment A §6 원문과
   글자 단위로 일치하는지 대조.
8. 이번 변경이 `NAE/pipeline/tsu/`, `NAE/corpus/`(F2 실행 중인 경로)와 겹치지
   않는다는 주장을 `git diff --stat`으로 재확인.
9. 테스트 커버리지가 "게이트 단일화"·"병합 없음"·"baseline 무접촉"이라는 이번
   작업의 핵심 안전 주장을 실제로 검증하는지, 아니면 표면적으로만 통과하는지
   (예: mock이 실제 실패 시나리오를 가리는 것은 아닌지) 비판적으로 평가.

---

## 4. 판정 기준

- **GREEN**: 질문 1–9 전부 근거와 함께 해소, ADR-024 준수·병합 없음·baseline
  guard 실효성 확인.
- **YELLOW**: 일부 findings — CUE가 패치 후 재검토.
- **RED**: ADR-024/Amendment A와의 불일치가 실제로 남아있음 — 설계 재작업.

본 변경은 `nae_tsu_v1` 3,319 / `nae_ref_v1` 34,948 baseline과 production
Qdrant/Ollama에 **무접촉**(코드·테스트만, 모든 외부 호출은 mock). F4/F5의 실제
실행(--apply)은 이 검토 범위 밖이며 Amendment A Approved 이후 별도 작업.

---

## 5. C1 붙여넣기용 지시 (relay)

```
Task: NAE-F4-F5-F6-PREPARATION-001 독립 검토 (C1 Review, 구현 아님).

브랜치 claude/nae-f4-f5-f6-prep (base origin/dev/dbma-engine@3b34186).
먼저 git -C ~/DBMA fetch 후 이 브랜치를 read-only로 확인:
  git log --oneline origin/dev/dbma-engine..claude/nae-f4-f5-f6-prep
  git diff origin/dev/dbma-engine..claude/nae-f4-f5-f6-prep -- ui/ NAE/ scripts/ tests/ docs/

읽을 문서 (같은 브랜치):
  docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md (Approved — 기준 문서)
  docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md (Proposed)
  docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md
  docs/NAE_F4_F5_F6_C1_REVIEW_REQUEST_001.md  ← 검토 질문 9개 (§3)

수행:
1. 위 요청서 §3 질문 1–9에 각각 답한다 (근거는 코드 라인 인용).
2. 코드는 read-only. 수정하지 말 것.
3. 판정 GREEN / YELLOW(조건부, findings) / RED.
4. 결과를 docs/NAE_F4_F5_F6_C1_REVIEW_RESULT_001.md로 작성,
   같은 브랜치에 커밋 (커밋만, push는 CUE가).

핵심 확인 포인트:
- ADR-024 §B(병합 금지)를 chat.py가 실제로 지키는지 — 이게 이번 검토의 핵심.
- 단일 스위치(§F) — 신규 플래그가 정말 없는지.
- F5 baseline guard가 코드 흐름상 우회 불가능한지.
- F4/F5 dry-run이 실제로 Ollama/Qdrant 쓰기를 하지 않는지.
```
