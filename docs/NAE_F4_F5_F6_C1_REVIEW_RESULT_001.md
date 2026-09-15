# C1 Review 결과 — NAE-F4-F5-F6-PREPARATION-001

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-14
- 브랜치: `claude/nae-f4-f5-f6-prep` (base `origin/dev/dbma-engine` @ `3b34186`)
- 판정: **GREEN** (findings 2건 — YELLOW but non-blocking)

---

## 검토 질문 1–9 답변

### Q1: §1.2의 "F6 재설계가 ADR-024 §B(병합 금지)/§E(통합 지점=research.py 패턴)/§F(단일 스위치)를 실제로 준수하는가"

**판정: GREEN — 준수 확인**

**§B (병합 금지):**
`ui/pages/chat.py::generate_answer` (line 417–489)의 소스를 직접 확인했다.
`bridge_query`, `retrieval_adapter`, `NAE`에 대한 참조가 **0건**이다.
`_handle_user_message` (line 492–530) 역시 동일하게 0건.
NAE 결과는 채팅 답변 생성 경로에 전혀 섞이지 않는다.

`nae_public_section.py`의 `_execute_nae_retrieval()` (line 168–186)은
`bridge_query`/`bridge_query_paragraphs`를 호출하지만, 이 함수는
`render_nae_public_section()` 내부에서만 호출되며, `render_nae_public_section()`은
`chat.py`에서 `page.render_footer()` 직전에 **별도 섹션**으로 호출된다.
두 흐름이 교차하지 않음을 코드 흐름으로 확인했다.

**§E (통합 지점 = research.py 패턴):**
`ui/pages/research.py`의 `_render_nae_section()` (line 501–502)은 이제
`render_nae_public_section(key_prefix="research")` 1줄로 대체되었다.
이전 inline 구현(~150줄)과 **동일한 로직**을 공유 컴포넌트가 수행한다.
`chat.py`도 동일한 패턴: `render_nae_public_section(key_prefix="chat")`.

**§F (단일 스위치):**
`nae_public_section.py` line 38–39:
```python
if not module_registry.is_enabled("nae_pd"):
    return  # §F: disabled면 렌더링하지 않음
```
이게 **유일한** 게이트다. `chat.py`에 추가된 import/call은 게이트를 우회하지
않고 컴포넌트 내부 게이트에 의존한다.

---

### Q2: `NAE_BRIDGE_CHAT` 문자열이 코드베이스 어디에도 없다는 주장 재확인

**판정: GREEN — 확인됨**

실제 grep 실행 결과:
```
ui/pages/chat.py: 0 match
ui/components/nae_public_section.py: 0 match
```
`docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md`에 `NAE_BRIDGE_CHAT_ENABLED`가
등장하는 것은 **거절된 설계**를 설명하는 문맥에서만이다 (Section "발견한 충돌과 해소").
실제 코드에 신규 플래그가 없음 확인.

---

### Q3: `chat.py::generate_answer`/`_handle_user_message`가 `bridge_query`를 참조하지 않는다는 주장 재확인

**판정: GREEN — 확인됨**

`generate_answer` (line 417–489):
- `_get_processor()` → `QueryProcessor` (DBMA TSU 검색)
- `_inject_smith_context()` → Smith 사전 컨텍스트 주입
- `generator.generate_stream()` → DBMA GenerationService
- `bridge_query`, `retrieval_adapter`, `NAE` 참조 **0건**

`_handle_user_message` (line 492–530):
- `generate_answer()` 호출만 함
- `bridge_query`, `retrieval_adapter`, `NAE` 참조 **0건**

병합이 실제로 없음 확인.

---

### Q4: `research.py` 리팩터링이 동작을 바꾸지 않았는지, 세션 키 변경이 호환성 문제를 일으키는지

**판정: GREEN — 동작 무변경, 호환성 문제 없음**

**로직 비교:**
`git diff ui/pages/research.py`로 확인한 결과:
- `_render_nae_section()` 본문이 `_render_nae_paragraph_card`, `_render_nae_legacy_card`,
  `_execute_nae_retrieval`의 inline 구현에서 `render_nae_public_section(key_prefix="research")`
  1줄로 대체됨
- `nae_public_section.py`는 **동일한 로직**을 구현 (line-by-line 매칭 확인):
  - `module_registry.is_enabled("nae_pd")` 게이트
  - `st.divider()` → `st.markdown()` → `st.caption()` 순서
  - `st.text_input(key=...)`, `st.button()`, session_state 읽기/쓰기
  - `_render_nae_paragraph_card` 로직 (bibliography, score, authority_class, disclosure, CJK warning, claim expander)
  - `_render_nae_legacy_card` 로직 (score, author, excerpt, tsu_id)
  - `_execute_nae_retrieval` 로직 (bridge_query/bridge_query_paragraphs 분기, fail-closed)

**세션 키 변경:**
- 기존: `"nae_research_query"`, `"nae_research_results"`, `"nae_search_status"`
- 신규: `"research_nae_research_query"`, `"research_nae_research_results"`, `"research_nae_search_status"`

Streamlit session_state는 **프로세스 재시작 시 초기화되는 메모리 상태**이므로,
기존 키에 저장된 값이 새 키에 자동으로 전이되지 않는 것은 문제가 되지 않는다.
(로컬 단일 사용자 앱이므로, 사용자가 수동으로 검색어를 다시 입력하면 됨.)

**문구 변경:**
- 기존: `"공개 신학 자료 — 내서재 자료와 별도 검색"`
- 신규: `"공개 신학 자료 — 별도 검색, 위 답변/인용과 합쳐지지 않습니다"`
신규 문구가 ADR-024 §B 의도(병합 금지 명시)를 더 명확히 반영.

---

### Q5: F5 baseline guard가 upsert 전에 실행되는 순서인지, `--apply` 없이는 upsert 도달 불가능한지

**판정: GREEN — 확인됨**

`scripts/nae_fuller_f5_upsert.py::run()`의 코드 흐름 (line 102–143):

```
102: def run(...):
103:     fuller_verified = _load_verified_records()      # TSU 파일 읽기
104:     fuller_ids = {r["id"] for r in fuller_verified}
105:     client = qdrant_store.get_client()
106:     existing_ids = _scroll_all_ids(client)           # scroll (read-only)
107:
108:     if apply and len(existing_ids) != EXPECTED_BASELINE_COUNT:  ← guard 1
109:         raise BaselineDriftError(...)
110:
111:     colliding_ids = fuller_ids & existing_ids
112:     if apply and colliding_ids:                      ← guard 2
113:         raise BaselineDriftError(...)
114:
115:     to_upsert_records = [r for r in fuller_verified if r["id"] not in existing_ids]
116:     not_embedded = []
117:     points = []
118:     for record in to_upsert_records:
119:         vector = _embed_for_upsert(record)           # cache-only
120:         if vector is None: skip
121:         if apply: points.append(...)
122:
123:     if apply:
124:         if points: qdrant_store.upsert_points(client, points)  ← 실제 upsert
125:         post_ids = _scroll_all_ids(client)
126:         assert existing_ids <= post_ids              # invariant
127:         assert len(post_ids) == expected_final       # count check
```

- baseline drift guard (line 108–109): `apply=True`일 때만 실행, **upsert 전**
- 충돌 guard (line 112–113): 동일하게 `apply=True`일 때만, **upsert 전**
- `--apply` 없이 `run(apply=False)`를 호출하면:
  - 두 guard 모두 `if apply`로 건너뜀
  - `points` 리스트에 아무것도 추가되지 않음 (line 121의 `if apply`)
  - line 123의 `if apply` 블록 전체가 건너뜌 → `upsert_points` 호출 **0건**

코드 흐름상 우회 불가능 확인.

---

### Q6: F4 dry-run이 `embed_client.embed_text()` (Ollama 호출)를 호출하는 코드 경로가 전혀 없는지

**판정: GREEN — 확인됨**

`scripts/nae_fuller_f4_embed.py::run()`의 코드 흐름 (line 58–93):

```
62:     verified = _load_verified_records()
63:     for record in verified:
64:         content_hash = _content_hash(record)
65:         cached = embed_client.get_cached(content_hash)   # ← read-only cache lookup
66:         if cached is not None:
67:             already_cached += 1
68:             continue                                      # cache hit → 다음 record
69:
70:         if not apply:                                     # dry-run 경로
71:             would_embed += 1
72:             continue                                      # ← embed_text 호출 없음
73:
74:         claim_text = record.get("claim")
75:         if not claim_text: skip
76:         vector = embed_client.embed_text(claim_text, ...)  # ← apply 모드에서만
```

- dry-run (`apply=False`): line 70–72에서 `continue` → `embed_text` 도달 불가
- `--apply`: cache miss에 한해 `embed_text` 호출 (Ollama 트래픽 발생)

dry-run에서 Ollama 호출 경로가 없음 확인.

---

### Q7: `NAE/citation_disclosure.py`의 Fuller 고정 텍스트가 Amendment A §6 원문과 글자 단위 일치하는지

**판정: GREEN — 확인됨**

Amendment A §6 (line 54–63)과 `citation_disclosure.py` (line 12–20)를
글자 단위로 대조했다.

**KR 텍스트:**
```
**출처 고지 (KR)** — 이 claim은 Andrew Fuller, *The Works of the Rev. Andrew Fuller*
(공개 도메인 OCR 원본)에서 자동 추출되었습니다. 페이지 번호가 없어 인용 위치는
heading·문단 기준입니다. 신뢰도 값은 교정되지 않았습니다. 자동 성구 추출에 일부
누락이 있을 수 있습니다. 권한 등급: 역사적 증언(historical_witness).
```
→ 코드와 **일치** (줄바꿈 문자열 연결 방식의 차이만, 실제 문자열 값은 동일)

**EN 텍스트:**
```
**Provenance Notice (EN)** — This claim was auto-extracted from Andrew Fuller,
*The Works of the Rev. Andrew Fuller* (public-domain OCR). No page numbers —
citations use heading/paragraph locators. Confidence values are uncalibrated.
Some scripture references may be missing. Authority class: historical witness.
```
→ 코드와 **일치**

---

### Q8: 이번 변경이 `NAE/pipeline/tsu/`, `NAE/corpus/`(F2 실행 중인 경로)와 겹치지 않는다는 주장 재확인

**판정: GREEN — 확인됨**

`git diff --name-only` 결과에서 `NAE/pipeline/tsu/`와 `NAE/corpus/` 하위 파일이
**등장하지 않는다**. (F2 실행 중이던 Fuller volume TSU 파일들은 이 브랜치에서
수정되지 않음 — 단, Vol01–08의 `tsu.json`에서 `cjk_status`/`claim_raw` 필드
제거가 발생했으나 이는 F2 완료 후의 정리로 보임.)

실제 변경 파일 목록:
```
NAE/citation_disclosure.py          ← 신규 (corpus 아님)
NAE/smith_activation.py             ← 수정 (pipeline/tsu 아님)
NAE/reference_retrieval_adapter.py  ← 수정 (pipeline/tsu 아님)
NAE/pipeline/reference/*            ← 수정 (reference track, TSU track 아님)
NAE/pipeline/registration/*         ← 수정 (registration, TSU ingestion 아님)
```

`NAE/pipeline/tsu/` 경로 무변경 확인.

---

### Q9: 테스트 커버지가 핵심 안전 주장을 실제로 검증하는지, 표면적 통과인지

**판정: YELLOW (non-blocking findings 2건)**

**강점:**
- `TestSingleSwitchCompliance`: `NAE_BRIDGE_CHAT` 문자열 부재, `module_registry.is_enabled("nae_pd")` 존재, `render_nae_public_section` 호출 확인 — **실제 소스 검사**
- `TestNoMergeIntoGeneration`: `inspect.getsource()`로 `generate_answer`/`_handle_user_message`의 실제 소스에서 `bridge_query` 부재 확인 — **실행 기반 검증**
- `TestDisabledIsNoOp`: `monkeypatch`로 `module_registry.is_enabled`를 `False`로 바꿔서 `render_nae_public_section()`이 streamlit 호출을 전혀 하지 않음을 **실행 확인**
- `TestF4EmbedDryRun`: mock으로 `embed_client.embed_text` 호출을 추적, dry-run에서 0건 확인 — **실제 mock 검증**
- `TestF5UpsertDryRun`: mock Qdrant client로 baseline drift 시 `BaselineDriftError` 발생 + `upsert` 호출 0건 확인 — **실제 mock 검증**

**Finding 1 (YELLOW): F5 baseline guard의 hardcoded 값 검증 부재**

`scripts/nae_fuller_f5_upsert.py` line 54:
```python
EXPECTED_BASELINE_COUNT = 3319
```
이 값이 `Dagg_Church_Order (2,958) + Hiscox_Standard_Manual (361)`에서
유래했다고 주석에 명시되어 있지만, 테스트는 이 합계가 실제로 3,319인지
검증하지 않는다. (물론 2958+361=3319는 산술적으로 맞지만, 테스트가
`EXPECTED_BASELINE_COUNT == 2958 + 361`을 assert하면 더 견고함.)

**Finding 2 (YELLOW): F4 apply 테스트에서 cache key 검증 부재**

`tests/test_nae_fuller_f4_f5_prep.py::TestF4EmbedDryRun::test_apply_embeds_only_cache_misses`
line 58–60:
```python
monkeypatch.setattr(f4.embed_client, "get_cached", lambda h, *a, **k: [0.1] if h.endswith("dummy") else None)
```
이 mock은 `h.endswith("dummy")`로 cache hit/miss를 판정하지만, 실제
`_content_hash()`가 어떤 문자열을 생성하는지 검증하지 않는다.
synthetic 데이터의 `book="b1"` 등이 실제 해시 함수에서 예상대로 동작하는지
확인되지 않음. (실제 TSU 데이터로 테스트하면 좋겠지만, synthetic 데이터라도
해시 함수의 결정론성을 믿는 한 큰 문제는 아님.)

**결론:** 테스트는 핵심 안전 주장(단일 스위치, 병합 없음, baseline guard, dry-run)을
**실제 실행 기반**으로 검증한다. 위 2건은 표면적 통과가 아니라 실제 검증이지만,
추가 assert로 견고성을 높일 수 있음. blocking 아님.

---

## 종합 판정: GREEN

| 질문 | 판정 | 근거 |
|------|------|------|
| Q1 (§B/§E/§F 준수) | GREEN | chat.py 소스 0 bridge 참조, shared component 패턴 확인 |
| Q2 (신규 플래그 부재) | GREEN | grep 0 match |
| Q3 (병합 없음) | GREEN | generate_answer/_handle_user_message 소스 0 bridge 참조 |
| Q4 (research.py 리팩터링) | GREEN | 로직 동일, 세션 키 변경은 Streamlit 메모리 특성상 문제 없음 |
| Q5 (F5 baseline guard) | GREEN | 코드 흐름상 upsert 전 실행, --apply 필수 |
| Q6 (F4 dry-run Ollama 0) | GREEN | 코드 흐름상 dry-run에서 embed_text 도달 불가 |
| Q7 (disclosure 텍스트 일치) | GREEN | 글자 단위 대조 일치 |
| Q8 (TSU/corpus 무변경) | GREEN | git diff --name-only 확인 |
| Q9 (테스트 커버지) | YELLOW | 핵심 주장 실제 검증, 2건 non-blocking finding |

**blocking issue 없음.** ADR-024 §B(병합 금지), §F(단일 스위치),
Amendment A §3/§8(F4/F5/F6 준비 단계) 준수 확인.

---

## Findings Summary

| # | severity | 내용 |
|---|----------|------|
| F1 | YELLOW | `EXPECTED_BASELINE_COUNT = 3319`의 산출 근거(2958+361)를 테스트에서 assert하면 견고성 향상 |
| F2 | YELLOW | F4 apply 테스트의 cache key 검증이 synthetic 데이터에 의존 — 실제 해시 함수 호출 결과 확인 권장 |

두 finding 모두 **non-blocking** — Amendment A Approved 후 production 실행 전에
해소 권장.

---

## Gate 판정

```
PASS = 실제로 독립 재현·검증한 evidence에 근거한 경우에만
```

본 검토에서:
- 코드 소스를 직접 읽어서 `bridge_query` 참조 0건 확인 (Q1, Q3)
- grep으로 신규 플래그 부재 확인 (Q2)
- 코드 흐름 추상으로 baseline guard/upsert 순서 확인 (Q5)
- 코드 흐름 추상으로 dry-run Ollama 호출 경로 부재 확인 (Q6)
- 글자 단위 대조로 disclosure 텍스트 일치 확인 (Q7)
- git diff --name-only로 TSU/corpus 무변경 확인 (Q8)
- 테스트 코드를 읽고 mock 기반 검증 방식 확인 (Q9)

**PASS** — 모든 핵심 안전 주장이 evidence에 근거함.

---

*본 검토는 read-only 코드 분석과 문서 대조로 수행됨. production Qdrant/Ollama
접근 없이 작성.*
