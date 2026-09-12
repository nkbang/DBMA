# NAE F4/F5/F6 Preparation — Design v1

- 작성: CUE, 2026-09-12
- 브랜치: `claude/nae-f4-f5-f6-prep` (base `origin/dev/dbma-engine` @ `3b34186`)
- 범위: **코드·테스트·설계 문서만.** F4/F5/F6 production 실행은 이 작업 범위 밖 —
  ADR-030 Amendment A §8이 "F4/F5/F6는 Amendment Approved 후에만 착수"로 고정.
  Amendment A는 현재 **PROPOSED**(4조건 중 F2 자체분만 구현/회귀 충족, C1 Review·
  HQ 승인 미완).

---

## 0. CON-012 선결 — Approved ADR 본문 판독 결과

`docs/DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md` CON-012(HOLD blocking, 2026-09-10)의
요구대로, 아래 문서 **전문을 판독**했다(발췌 인용이 아니라 본문 전체):

| ADR | Status | 이번 작업 관련 조항 |
|---|---|---|
| **ADR-013** NAE Vector Store | Accepted | `nae_qdrant`/`nae_tsu_v1`은 `NAE/` 전용, `RetrievalEngine` 미연결. "향후 production 경로 통합은 이 ADR을 개정하는 신규 ADR 필요" — 그 신규 ADR이 ADR-024. |
| **ADR-024** NAE Production Retrieval Bridge | **Approved** (2026-08-17) | §A 모듈게이트 adapter, §B **결과 병합 금지**(별도 섹션), §C Citation 필드 매핑, §D `bridge_query()` 계약, §E 통합 지점 = `ui/pages/research.py`, §F 게이트 = `modules.nae_pd.enabled` 단일 스위치("별도의 두 번째 스위치를 만들지 않는다"), §G fail-closed, §H corpus isolation. |
| **ADR-030 v2.1** Sermon Corpus Governance | IMPLEMENTED | §11 Human Eligibility Governance(ACQUIRED≠EMBEDDING ELIGIBLE≠EMBEDDED≠RETRIEVAL-ELIGIBLE), §14 baseline 3,319/34,948 불변. |
| **ADR-030 Amendment A** Fuller Processing Authorization | **PROPOSED** | §3 F4/F5/F6 표, §6 Citation Disclosure(historical_witness 고정 문구), §7 Freeze 목록, §8 승격 4조건. |
| **ADR-029** Research Corpus Expansion Pipeline Lock | Approved | grep 결과 F4/F5/F6/bridge_query/chat.py/retrieval 무관 — 충돌 없음(Amendment A §7이 이미 확인한 결론 재확인). |

이전 유사 검토(중복 조사 회피): PR #17(`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md` §8)이
같은 CON-012 선결을 옵션 A(DBMA 기본 경로 문단화) 범위에서 이미 수행했고, 그 문서 자체가
"F6(`chat.py` ↔ `bridge_query` 배선)은 별도 승인 사항, 본 설계 범위 밖"이라고 명시적으로
분리해 두었다(§8 표, §9 가정 6). 이번 작업이 바로 그 "별도 승인 사항"이다.

### 발견한 충돌과 해소

작업 명령서 초안은 `chat.py`에 신규 플래그(`NAE_BRIDGE_CHAT_ENABLED`)를 두고 NAE 결과를
문단 앵커드 답변에 **병합**하는 설계를 요청했다. 이는:

- ADR-024 §F("별도의 두 번째 스위치를 만들지 않는다") 위반,
- ADR-030 Amendment A §3 F6 행("게이트 = `config.yaml modules.nae_pd`")과 불일치,
- ADR-024 §B("같은 순위 리스트에 병합하지 않는다")·§E(통합 지점 = `research.py`, 별도 섹션)
  위반

세 지점에서 Approved ADR과 충돌한다. CUE Operating Policy(Architecture Freeze Rule)에
따라 구현을 중단하고 사용자에게 확인했다 — **"ADR-024 그대로 준수"**로 결정(2026-09-12).
이하 설계는 그 결정을 반영한다.

---

## 1. F6 — 검색 노출 배선 (재설계, ADR-024 준수)

### 1.1 게이트

`config.yaml modules.nae_pd.enabled` 단일 스위치만 사용한다. **신규 플래그 없음** —
`NAE_BRIDGE_CHAT_ENABLED` 같은 두 번째 스위치를 만들지 않는다(ADR-024 §F,
Amendment A §3 F6 행과 일치). 기본값은 기존과 동일하게 `false`.

### 1.2 통합 지점과 병합 금지

`ui/pages/research.py`가 이미 ADR-024 §E가 지정한 통합 지점으로 구현되어 있었다
(`_render_nae_section` → 독립 "내서재 공개 자료 (Beta)" 섹션, 자체 검색어 입력·버튼·
결과 카드, DBMA 검색 결과와 완전히 분리). 이번 작업은 이 **동일한 패턴**을
`ui/pages/chat.py`에도 적용한다 — `chat.py`의 답변 생성(`generate_answer`,
`_handle_user_message`)에는 손대지 않고, 페이지 하단에 독립된 섹션만 추가한다.

두 벌 유지 시 드리프트 위험이 있어(§F가 이미 지적한 CON-012류 문제 패턴), 구현을
`ui/components/nae_public_section.py`로 추출해 `research.py`/`chat.py` 양쪽이
공유한다. `key_prefix` 인자로 Streamlit session_state 키를 페이지별로 분리한다
(`chat_nae_research_query` vs `research_nae_research_query`).

```
chat.py::render_chat_page()
    ... (기존 DBMA 채팅 흐름 — 무수정) ...
    render_nae_public_section(key_prefix="chat")   # ← 신규 호출 1줄
    page.render_footer()
```

- `render_nae_public_section()`은 `modules.nae_pd.enabled`가 false면 아무것도
  그리지 않고 즉시 반환한다 — DBMA 기본 경로에 바이트 단위 무영향.
- NAE 결과는 `bridge_query`/`bridge_query_paragraphs`(ADR-024 §D, 기존 함수 재사용,
  수정 없음)로 조회하고, `CitationBuilder`나 답변 생성 프롬프트로 전달하지 않는다 —
  §B "병합 금지"를 그대로 지킨다.

### 1.3 문단 앵커드 근거 / 근거부족-유출차단 적용 범위

작업 명령서 §4가 요구한 "PR #17 문단 앵커드 로직"과 "PR #25/#26 근거부족-유출차단"은
**이미 이 경로에 적용되어 있다** — 둘 다 `research.py`의 기존 NAE 섹션이 사용하는
`bridge_query_paragraphs()`(옵션 A, `NAE/answer_context.paragraph_evidence_enabled()`)
경로를 그대로 재사용하기 때문이다. `core/generation.py`의 근거부족-유출차단은애초에
**생성 프롬프트 레벨**의 안전장치인데, NAE 섹션은 답변을 생성하지 않고(검색 결과 카드만
표시) 별도의 "AI 요지 요약" expander만 TSU 레코드의 기존 `claim` 필드를 보여준다 —
이 경로에 새로 생성 호출을 추가하지 않았으므로 유출차단 로직이 걸릴 새 생성 호출
자체가 없다. §B(병합 금지) 준수가 이 항목을 자동으로 충족시킨다.

### 1.4 Citation Disclosure UI (Amendment A §6)

`NAE/citation_disclosure.py::get_disclosure(authority_class)` — `authority_class ==
"historical_witness"`일 때 Amendment A §6의 고정 KR/EN 문구를 그대로 반환한다.
`ui/components/nae_public_section.py::_render_nae_paragraph_card()`가 카드마다
`hit.get("authority_class")`를 이 함수에 넘겨 결과가 있으면 `st.warning()`으로
노출한다(자료 등급 캡션 바로 아래). 현재 `historical_witness`는 Fuller 하나뿐이라
문구를 Fuller로 고정했다 — 두 번째 `historical_witness` 출처가 생기면 per-work
lookup으로 일반화해야 한다(모듈 docstring에 명시).

`nae_ref_v1`(Smith)은 이번 범위 밖 — `NAE/citation_disclosure.py`는 `nae_tsu_v1`
payload의 `authority_class`만 다루고 Smith 경로를 건드리지 않는다.

---

## 2. F4 — Fuller 임베딩 준비 (코드만, 미실행)

`scripts/nae_fuller_f4_embed.py`:

- 대상: `NAE/corpus/tsu/Fuller_Complete_Works_Vol01..08/tsu.json`의
  `review_status == "verified"` 레코드만. 현재(2026-09-12) 전 volume이 100%
  `generated`이므로 verified count = 0 — 지금 실행해도 0건 처리(no-op), 그래도
  `--apply`를 쓰지 않았다(안전장치 자체를 검증하는 것이 목적).
- 기존 `NAE/pipeline/embed/{client,hashing}.py`를 그대로 재사용(재구현 없음) —
  `bge-m3:latest`, content-hash 캐시.
- 기본은 dry-run: `embed_client.get_cached()`만 호출(Ollama 트래픽 0), cache
  hit/miss 카운트만 리포트. `--apply`가 있어야 cache miss에 한해
  `embed_client.embed_text()`(Ollama 실호출)를 호출한다.
- Qdrant를 전혀 건드리지 않는다(F5의 책임) — 캐시 파일만 additive로 채운다.

## 3. F5 — additive upsert 준비 (코드만, 미실행)

`scripts/nae_fuller_f5_upsert.py`:

- **baseline guard**: upsert 전 `nae_tsu_v1`을 scroll해 현재 point 수를 세고,
  `--apply` 모드에서 정확히 `EXPECTED_BASELINE_COUNT = 3319`(Dagg 2,958 + Hiscox
  361)가 아니면 `BaselineDriftError`를 던지고 **아무것도 쓰지 않는다**. Fuller
  tsu_id가 기존 baseline point id와 충돌하는 경우도 동일하게 거부한다 — "3,319
  baseline 무접촉"이 주석이 아니라 실행되는 가드다.
- F4가 채운 캐시만 읽는다(`embed_client.get_cached()`) — F5는 Ollama를 호출하지
  않는다(F4/F5 책임 분리). 캐시 miss는 에러로 리포트하고 skip한다.
- `--apply` 성공 후 `scripts/nae_corpus_reconcile.py --json`을 subprocess로 실행해
  drift 0을 리포트에 포함한다(Amendment A §3 F5 게이트 요구사항).
- upsert 후 `len(existing_ids) + newly_upserted == post_upsert_count`를 자체
  assert한다(코드 내 invariant, 테스트가 아니라 런타임에서도 확인).
- 이번 세션에서는 `--apply`는 물론 dry-run조차 프로덕션 `nae_qdrant`(7333)에 대해
  실행하지 않았다 — 단위 테스트가 `qdrant_store.get_client()`를 mock으로 대체해
  전부 검증했다(§4 참고). GPU full-load window·서비스 가용성 여부와 무관하게
  안전하게 유지.

---

## 4. 제약 준수 확인

- `nae_tsu_v1` 3,319 / `nae_ref_v1` 34,948 — 무접촉(코드 준비만, 실행 없음).
- `NAE/pipeline/tsu/`, `NAE/corpus/` — 무수정(F2 실행 중인 파일 트리와 겹치지 않음,
  `git diff --stat`으로 확인).
- Retrieval Engine(`core/retrieval.py`) / Embedding Engine 코드 — 무수정.
- `nae_ref_v1`(Smith) 경로 — 무수정.
- GPU 실호출 없음(모든 테스트가 mock 사용, 실제 F4 dry-run 실행은 verified=0이라
  Ollama를 호출하지 않음을 실행으로 확인).

---

## 5. 회귀 / Acceptance 테스트

| 파일 | 확인 내용 |
|---|---|
| `tests/test_nae_f6_chat_wiring.py` | (a) 단일 스위치 준수 — `NAE_BRIDGE_CHAT` 문자열이 코드베이스에 없음. (b) 병합 없음 — `generate_answer`/`_handle_user_message` 소스에 `bridge_query` 참조 없음. (c) disabled 시 `render_nae_public_section()`이 streamlit 호출을 전혀 하지 않음(실행 확인). (d) `chat`/`research` key_prefix가 session_state 키를 분리함. (e) disclosure 매핑(historical_witness → Fuller 문구, 그 외 → None). |
| `tests/test_nae_fuller_f4_f5_prep.py` | F4 dry-run이 embed 호출 0건인지 실행 확인, apply 모드가 cache miss만 embed하는지, 누락 volume을 에러 없이 skip하는지. F5 dry-run이 `client.upsert` 0건인지, baseline drift 시 `BaselineDriftError`로 즉시 거부하고 upsert가 호출되지 않는지(mock Qdrant client). |
| 기존 `tests/test_dbma_nae_module_packaging.py`, `tests/test_nae_bridge_full_source_text.py`, `tests/test_nae_retrieval_bridge_integration.py` | 27건 전부 PASS 유지 확인(무회귀). |
| 스코프 회귀 | `pytest tests/ -k "nae or chat or research or module_packaging"` — 866 passed. |

플래그 off(`modules.nae_pd.enabled: false`, 기본값) 상태에서 DBMA 기본 경로가
바이트 단위로 무변경이라는 것은 (b)+(c) 조합으로 실행 확인된다 — 병합 지점 자체가
없고(b), disabled 시 아무 UI도 그려지지 않는다(c).

---

## 6. 미확인 가정 / 후속 과제

1. F6 acceptance test(작업 명령서 §4 "플래그 on 상태에서 sandbox Qdrant/mock으로
   chat.py가 NAE 소스를 포함한 답변을 만들고 disclosure가 붙는지 검증")는 이번
   설계상 "답변에 포함"이 아니라 "별도 섹션에 노출"로 재해석된다(§1.2/§1.3의
   ADR-024 준수 결과) — `tests/test_nae_f6_chat_wiring.py::TestKeyNamespacing`와
   기존 `research.py` 섹션의 실제 동작(동일 컴포넌트 재사용)이 그 증거를 대신한다.
   실제 Qdrant/Ollama를 띄운 end-to-end 수동 확인은 이번 범위 밖(§ 실행 금지).
2. Fuller F3(인간 검수) 완료 후 verified count가 0에서 늘어나면, F4 dry-run 리포트의
   `verified_total`이 그만큼 증가하는지 재확인이 필요하다(로직은 이미 그 케이스를
   커버하지만 synthetic 데이터로만 검증됨, §5).
3. `historical_witness` 두 번째 출처 admission 시 `NAE/citation_disclosure.py`를
   per-work lookup으로 일반화해야 한다(§1.4).
