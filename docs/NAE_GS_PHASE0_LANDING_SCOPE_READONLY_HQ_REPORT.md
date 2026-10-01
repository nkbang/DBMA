# Phase 0 dev 착지 범위 — READ-ONLY 비교 보고

- 작성: CUE · 2026-09-30
- 전제
  - FU-007 = **C** (HQ APPROVED, 결정 자료 `81ac087f`). 이 문서에서 A/B/C를 다시 평가하지 않는다.
  - ④ 계약 = `bf68c38a`
- 방법
  - git tree/blob 대조, `git merge-tree` 병합 시뮬레이션(ref·worktree는 바꾸지 않음), 앱 인덱스 메타데이터 읽기
  - 코드·테스트는 실행하지 않았다. 회귀 수치는 기존 측정값이다.
- 표기: [CONFIRMED] 코드·tree로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인
- **MUTATION: NONE** (코드·ADR·prompt·index 모두)

## 0. 기준 ref (2026-09-30 fetch)

| ref | commit | 날짜 | 내용 |
|---|---|---|---|
| `origin/dev/dbma-engine` | `195189b8` | 09-26 | 릴리스 라인. FU-007 시도 이후 변동 없음 |
| `origin/main` | **`88ca969b`** | 09-30 | FU-007 시도 기준점 `d1c06d25` **이후 9커밋이 더 쌓였다**(4.1절) |
| `origin/tmp/fu007-combined-translation` (C) | `b39572aa` | 09-29 | `97ec140e`(= `d1c06d25` ⊕ `195189b8` 병합) + C 1커밋 |
| `origin/tmp/fu007-integration-trial` (결과 브랜치) | `81ac087f` | 09-30 | `d1c06d25` + 문서 커밋 |

- [CONFIRMED] **결과 브랜치에는 C 코드가 없다.**
  - 결과 브랜치의 코드 = main `d1c06d25`의 코드 + ② ADR-037 번호 변경 커밋 `3ea7ece1`이 바꾼 주석 3파일(`NAE/public_answer.py`, `ui/components/nae_public_section.py`, `tests/test_nae_public_answer.py`)
  - C 코드와 dev 병합 결과는 `b39572aa`에만 있다.
- [CONFIRMED] `origin/dev/dbma-engine`은 `b39572aa`의 조상이다. 따라서 dev 쪽에서는 새로 반영할 변경이 없다.

## 1. Phase 0 착지 대상 전체 목록 (dev → C 차이)

`git diff 195189b8 b39572aa` 결과: 85파일 변경. 이 중 docs를 뺀 코드·테스트는 52파일이다(+9,714 / −91).

| 묶음 | 파일 | 분류 |
|---|---|---|
| ① FU-007 C 검색 | `core/query_translation.py`, `core/hybrid_candidate_pipeline.py`, `core/candidate_generator.py`, `tests/test_fu007_combined_translation.py`, `tests/test_query_translation.py`, `tests/test_book_filter_unk_corpus_fallback.py`, `tests/test_candidate_generator.py` | 검색 코어 |
| ② main 쪽 검색 부속 | `core/index_page_detector.py`(신규), `core/retrieval.py`, `core/query_enhancements.py`, `core/search_cache.py`, `tests/test_index_page_detector.py`, `tests/test_search_cache_thread_safety.py` | 검색 코어(main 고유, 병합으로 함께 들어옴) |
| ③ GS 모듈 | `core/grounded_answer.py`, `core/grounded_citation.py`, `core/grounded_claims.py`, `core/grounded_synthesis_input.py`, `scripts/grounded_synthesis_integration_demo.py`, `tests/test_grounded_*.py` 6개 | GS (운영 경로 미연결) |
| ④ 근거 계층 | `core/evidence_model.py`, `core/evidence_pool.py`, `core/evidence_assembly.py`, `core/evidence_adapters/tsu_adapter.py`(신규), `core/evidence_adapters/__init__.py`(수정), `tests/test_evidence_{model,pool,assembly}.py` | GS의 의존 대상 |
| ⑤ 인용 검증 | `core/citation_verifier.py`, `tests/test_citation_verifier.py`, `core/generation.py`(+27: `_run_citation_check`), `ui/pages/chat.py`(경고 표시) | 운영 경로 **연결됨**(경고 전용) |
| ⑥ 공개 자료 답변(ADR-037) | `NAE/public_answer.py`(신규), `NAE/citation_disclosure.py`, `NAE/retrieval_adapter.py`, `ui/components/nae_public_section.py`, `tests/test_nae_public_answer.py`, `tests/test_citation_disclosure_source_aware.py`, `tests/test_nae_retrieval_failure_signal.py` | ④ 결정상 GS 범위 밖 |
| ⑦ 기타 main 고유 | `ui/components/display_quality.py`(신규), `ui/components/citation_card.py`, `ui/pages/monitor.py`, `ui/pages/sermon_review.py`, `core/identity_registry.py`, `requirements.txt`(`kiwipiepy==0.23.2` 고정), 테스트 `test_display_quality.py`, `test_ad01_ad02_corpus_membership.py`, `test_no_hardcoded_absolute_paths.py` | 병합으로 함께 들어옴 |
| ⑧ 문서 | `docs/architecture/ADR-036-NAE-Public-Evidence-in-Answer-Generation.md` 외 문서 33개 | 6절 참고 |

- [CONFIRMED] main→dev 병합은 위 묶음 ①~⑧을 **한꺼번에** 가져온다.
- [INFERRED] 일부 묶음을 빼려면 병합 뒤 되돌리는 커밋이나 선별 반영(cherry-pick)이 필요하다. 이 방법을 쓰면 계보가 복잡해진다(① 결정 자료의 계보 논의).

## 2. 파일·구성요소별 상태 (결과 브랜치 ↔ dev)

T = 결과 브랜치 `81ac087f`, D = dev `195189b8`, C = `b39572aa`.

| 구성요소 | T | D | C | 착지 필요 | 의존성 |
|---|---|---|---|---|---|
| `core/grounded_answer.py` | 있음 | **없음** | 있음(T와 동일) | 필요 | `grounded_claims`, `grounded_synthesis_input` |
| `core/grounded_citation.py` | 있음 | **없음** | 있음(동일) | 필요 | `evidence_model`, `evidence_pool`, `grounded_answer`, `grounded_synthesis_input` |
| `core/grounded_claims.py` | 있음 | **없음** | 있음(동일) | 필요 | `grounded_synthesis_input` |
| `core/grounded_synthesis_input.py` | 있음 | **없음** | 있음(동일) | 필요 | `evidence_assembly`, `evidence_model`, `evidence_pool` |
| `core/evidence_model.py` | 있음 | **없음** | 있음(동일) | 필요 | 없음 |
| `core/evidence_pool.py` | 있음 | **없음** | 있음(동일) | 필요 | `tsu_adapter`, `evidence_model`, `core.retrieval` |
| `core/evidence_assembly.py` | 있음 | **없음** | 있음(동일) | 필요 | `tsu_adapter`, `evidence_model`, `evidence_pool`, `core.retrieval` |
| `core/evidence_adapters/tsu_adapter.py` | 있음 | **없음** | 있음(동일) | 필요 | `core.config`, `evidence_model`, `core.retrieval` |
| `core/evidence_adapters/{base,__init__}.py`, `core/evidence_unit.py` | 있음 | **있음** | 있음 | `__init__`만 수정(+17) | — |
| `core/citation_verifier.py` | 있음 | **없음** | 있음(동일) | 필요(④-5 4번 문구의 출처) | 의존 없음. `generation.py`가 import |
| GS 테스트 `tests/test_grounded_*.py` 6개 | 있음(105개 수집) | **없음** | 있음(동일) | 필요 | 위 모듈 |
| `core/grounded_synthesis*_executor.py` | **없음** | 없음 | 없음 | Phase 0 대상 아님(새 ADR 이후 구현) | B9 예외 이름 |
| 데모 `scripts/grounded_synthesis_integration_demo.py` | 있음 | 없음 | 있음 | 선택 사항(참고용) | — |
| `core/claim_guard.py` | 있음 | 있음 | 있음 | 이미 있음 | — |
| `NAE/public_answer.py` | 있음(주석: ADR-037) | **없음** | 있음(주석: ADR-036) | HQ 결정 필요(5절) | `nae_public_section.py` |
| `ui/components/nae_public_section.py` | 있음 | 있음(답변 생성 없음) | 있음(+147, 답변 생성 버튼) | HQ 결정 필요(5절) | `chat.py` L47·L123이 렌더함 |

- 위 표의 "동일"은 blob이 같다는 뜻이다. T와 C의 GS·근거 계층·citation_verifier 파일은 **blob이 같다** [CONFIRMED].
- **정정** [CONFIRMED]: `6f693a02` 등 이전 보고에서는 "dev에는 근거 계층 전체가 없다"고 썼다. 실제로 dev에 없는 것은 `evidence_model`·`evidence_pool`·`evidence_assembly`·`tsu_adapter` 4개뿐이다. `evidence_unit`과 `evidence_adapters/base`는 dev에도 있다.

## 3. FU-007 C 착지 범위

| 파일 | dev → C 변경 | 기존 검색 경로 영향 |
|---|---|---|
| `core/query_translation.py` | main API와 dev API를 한 모듈에 함께 둔다. dev `_HANGUL_RE` → `_HANGUL_ANY_RE`, 교단명 5항목 추가, `QUERY_TRANSLATION_VERSION` 3→4 | 버전 값이 캐시 키에 들어가므로 **기존 검색 캐시가 무효화된다** [INFERRED: 키 구성 기준] |
| `core/hybrid_candidate_pipeline.py` | main `_demote_index_pages`·`fetch_k` 과다 수집 + dev `_generate_candidates`·업프론트 LLM 번역 + C `_carry_scripture_notation()`, 텔레메트리 표기 통일 | `HybridRetriever.retrieve` Stage-1 전에 동작한다 |
| `core/candidate_generator.py` | dev 형태소 질의 유지 + `translated_terms`·`_VERSE_PHRASE_BOOST` 복원 + 0건이면 책 필터 해제 | `CandidateGenerator.search` 질의 구성이 바뀐다 |
| `core/retrieval.py` 등 ② 묶음 | main 고유 변경(권말 색인 강등, 구절 구문 가중 등) | `RetrievalEngine` 경로 |

- 회귀(기존 측정, `b39572aa`, 2026-09-29): **0 failed / 3,554 passed / 17 skipped** (FU-007 결과 문서 8.2절). 이번에 다시 실행하지 않았다.
- [CONFIRMED] `git merge-tree`로 확인한 결과, C ⊕ 새 main(`88ca969b`)은 **텍스트 충돌 없이 병합된다**(tree `78ceeb0c`). 이 병합 결과의 회귀는 측정한 적이 없다 [UNKNOWN].

## 4. GS 착지 범위와 정합성 위험

### 4.1 새 main 9커밋 (`d1c06d25..88ca969b`)

| 커밋 | 내용 | 영향 |
|---|---|---|
| `732fb435` (PR #89) | `fix(chat)`: Baptist 주석 컬렉션을 reference 검색에 연결 | **`ui/pages/chat.py` 변경** — GS 연결 대상 파일 |
| `ba0dd1a3` (PR #95) | supersession 순환·dangling 방어 | `core/identity_registry.py` |
| `274a8db9` (PR #96) | Production Registry supersession 링크 7건 정정 도구 + 실행 기록 | 스크립트·문서(데이터 파일 변경 없음) |
| `969dd7e3` (PR #103) | FU-004 문서 | 문서 |
| `2deb718e` | 스크립트 스텁 시그니처 수정 | `scripts/smith_e2e_verify.py` |

- [CONFIRMED] C는 옛 main(`d1c06d25`) 위에 만든 것이다. 새 main을 포함해 착지할지는 **HQ가 정할 사항**이다.
- [INFERRED] 새 main을 빼고 착지하면, 나중에 main→dev를 다시 병합할 때 `chat.py`가 두 번째로 병합된다.

### 4.2 GS 착지 자체

- [CONFIRMED] GS 모듈은 운영 경로에 연결되지 않은 상태로 들어간다. dev에서 `grounded_*`를 import하는 운영 코드는 없다. 이는 ADR-036 B1이 말하는 "운영 경로 교체"가 아니다 [INFERRED].
- [CONFIRMED] `citation_verifier`는 **운영 경로에 연결된 채** 들어간다(`generation.py` `_run_citation_check`, `chat.py` L46·경고 표시). 동작은 경고만 내고 답변을 막지 않는다. 그래도 dev 채팅 화면에 새 경고 문구가 나타난다.

## 5. Tantivy 인덱스

| 확인 | 결과 |
|---|---|
| 스키마 | **dev와 C의 스키마·문서 필드 정의가 같다**(`candidate_generator.py`의 `add_*_field`·`add_text` 목록을 diff, 차이 0) [CONFIRMED]. main 스키마에는 `*_search` 필드가 없다 |
| 앱 인덱스 `~/DBMA/output/bench/tantivy_index` | 필드 목록에 `title_search/content_search/author_search`가 **이미 있다**. `record_count` 119,595는 데이터셋 줄 수와 같다. 수정 시각은 09-29 15:05 [CONFIRMED] |
| 자동 재빌드 조건 | `open_or_build_index`는 `index_meta.json`이 없거나 레코드 수가 다를 때만 재빌드한다. **스키마 불일치는 감지하지 않는다** [CONFIRMED: `candidate_generator.py` L211~] |
| 토크나이저 | C는 `kiwipiepy==0.23.2`로 고정한다(dev는 버전 미지정). 운영 venv `~/envs/dbma311`도 0.23.2다 [CONFIRMED] |

- [INFERRED] **스키마 때문에 재빌드가 필요하지는 않다.** dev 코드와 C 코드로 만든 인덱스는 같은 형식이고, 현재 앱 인덱스도 이미 그 형식이다. FU-007 결과 문서 1절의 "재빌드 필요"는 main 코드로 만든 인덱스를 전제로 한 말이다.
- [UNKNOWN] 현재 앱 인덱스를 **어느 코드로 만들었는지**는 확인하지 못했다. 시각상 FU-007 10절의 병행 실행(메인 체크아웃, 결합안 코드)과 겹친다.
  - `_tokenize_for_index`는 dev와 C가 같다.
  - 다만 C 묶음 ②의 `retrieval.py` 등이 색인 대상 텍스트를 바꾸는지는 검증하지 않았다.

재빌드를 할 경우의 계획(실행하지 않음, HQ 승인 대상):

| 항목 | 내용 |
|---|---|
| 대상 | 배포 환경의 `output/bench/tantivy_index`(`core/config.py` `DEFAULT_CANDIDATE_INDEX_DIR`). 원천은 `output/bench/tsu_dataset.jsonl`이며 RAW·임베딩·Qdrant는 손대지 않는다 |
| 순서 | dev 반영 승인 → 기존 인덱스를 백업(디렉터리 복사) → `build_index` 실행 → 메타·필드 확인 |
| 검증 | `meta.json`에 `*_search` 필드가 있는지, `record_count`가 데이터셋 줄 수와 같은지, P0-5 24건 검색 단계 재현(FU-007 3·8절 하네스)으로 C 측정값(대리 지표 60/120)과 비교 |
| 기존 인덱스 영향 | 같은 경로에 덮어쓴다. 백업이 없으면 되돌릴 수 없다 |

## 6. ADR 상태

| ADR | 위치(tree) | 상태 | Phase 0 관계 |
|---|---|---|---|
| ADR-036 **GS boundary** (`ADR-036-Grounded-Synthesis-Boundary.md`) | **`origin/claude/p4-final-validation-guide-b3af47` `55be70b1`에만 있다**. main·dev·C·결과 브랜치에는 없다 | Accepted (2026-09-27) | GS 코드가 B1~B9를 인용하는데 근거 ADR 파일이 착지 대상에 없다 |
| ADR-037 public evidence answer | 결과 브랜치에서만 ADR-037이다(`3ea7ece1`). **main·C에서는 여전히 `ADR-036-NAE-Public-Evidence-…`이다** | Proposed (main판). EUAT판은 Approved(BACKLOG) | **C에서 그대로 착지하면 dev에 ADR-036 번호가 공개 자료 문서로 들어간다** — ② 결정과 충돌한다 |
| ADR-035 Pastoral Library | dev·C에 있다(main에는 없다) | — | 영향 없음 |
| ADR-009 Amendment A | dev·main 모두 `docs/architecture/ADR-009-Amendment-A.md` | **Proposed**. 승격 조건: C1 ⬜, 사용자 승인 ⬜ | `_DENOMINATION_DIRECTIVE`(C `generation.py` L355)는 그대로 둔다. 별도 트랙 |
| 새 GS integration ADR | 없음 | — | Phase 0 이후. ADR-036 B1 "운영 경로 교체가 필요해지면 P12 이후 새 ADR" |

## 7. ④ 계약과 현재 코드의 차이 (C 기준)

| ④ 확정값 | 현재 코드 | 차이 |
|---|---|---|
| B 생성 후 추출 | core에는 `ClaimExtractor` Protocol과 Stub만 있다(`grounded_claims.py`). LLM 추출은 데모 `parse_llm_claims`뿐이다(첫 줄 1개만 claim으로 만든다) | **추출기를 새로 만들어야 한다**(executor 쪽, B9) |
| 3-b 검증용 Claim | 오케스트레이터가 없다. `grounded_synthesis*_executor.py`는 모든 브랜치에 없다 | 새로 만들어야 한다. 운영 프롬프트에는 근거 ID가 없고 `출처:` 라벨만 있다 |
| S-C 버퍼 | `chat.py` L566~572: `st.write_stream` → `to_result()`(표시가 검증보다 먼저) | 바꿔야 한다 |
| 호출자 = `chat.py` 2곳 | L481 `generate_answer()`는 이미 버퍼 방식이다(`for _ in stream: pass`). **이 함수는 `ui/pages/research.py` L317·L928과 `scripts/smith_e2e_verify.py` L94에서 호출된다** | L481을 바꾸면 research 화면도 함께 바뀐다 — 범위 해석이 필요하다 |
| 전면 유보 / B5 | `grounded_answer.py` L63 고정 문구 "이 질문은 현재 등록된 자료로는 답할 수 없습니다."(같은 문장이 생성 지시문에도 있다) | ④-5 문구 "현 자료 내용이 충분하지 않습니다."와 다르다. B5 본문은 문구를 정하지 않는다 [CONFIRMED]. [INFERRED] UI 표시 단계에서 바꾸면 prompt를 고칠 필요가 없다 |
| "확인된 claim" | `assemble_grounded_answer`는 `valid`(ID 소속)만 본다 | 정의가 아직 없다(새 ADR 사항) |
| `grounded` 문구 / span 문구 | UI 코드가 없다 | 새로 만들어야 한다 |
| citation_verifier 문구 "지정하신 자료를 재확인하세요." | `chat.py` L670 "⚠️ 출처 확인 필요 — 아래 인용은 이번에 검색된 근거로 확인되지 않았습니다." + 이슈별 줄 | 문구를 바꿔야 한다 |
| normalization 제외 | `grounded_citation.py`에 정규화가 없다 | 일치 |
| `_DENOMINATION_DIRECTIVE` 별도 처리 | `generation.py`에 그대로 있다 | 일치(그대로 둔다) |
| GenerationResult | 필드: `citations`, `claim_guard_result`, `citation_check`. GS 필드는 없다 | 선택 필드를 더해야 한다(⑤ 설계) |
| ADR-037 제외 | `nae_public_section.py` L147이 `generate_stream`을 호출한다(C) | GS 연결 대상에서 빼야 한다 |

## 8. 예상 충돌·의존성

1. **ADR 번호**: C의 문서를 그대로 착지하면 ② 결정(공개 자료 = ADR-037)이 dev에 반영되지 않는다. 결과 브랜치의 `3ea7ece1`(파일명·머리글·주석 3파일)을 함께 반영해야 한다 [CONFIRMED].
2. **GS boundary ADR-036 파일**: p4 브랜치에만 있다. dev로 가져올지는 HQ 결정 사항이다.
3. **새 main 9커밋**: `chat.py` 변경이 들어 있다. 시뮬레이션에서는 충돌이 없었지만 회귀는 확인하지 않았다.
4. **공개 자료 답변 경로**: 병합하면 함께 들어온다. `chat.py`가 `render_nae_public_section`을 렌더하므로, 사용자 화면에 "이 근거로 답변 생성" 버튼이 생긴다 [CONFIRMED: C L136].
5. **citation_verifier**: 경고 문구가 dev 채팅에 나타난다. ④-5 문구로 바꾸는 일은 Phase 0 이후 구현에서 한다.
6. **검색 캐시**: `QUERY_TRANSLATION_VERSION` 3→4로 기존 캐시 항목을 쓰지 않게 된다 [INFERRED].
7. **메인 체크아웃 미커밋 17개**: `core/candidate_generator.py`·`hybrid_candidate_pipeline.py` 등이 staged 상태다. 이 파일들은 착지 원천이 아니며 건드리지 않는다.

## 9. HQ가 승인해야 할 항목

| # | 항목 | 선택지(사실 그대로) |
|---|---|---|
| H1 | 착지 원천 | `b39572aa`(옛 main 기준) 그대로 / 새 main `88ca969b`을 포함해 다시 병합 |
| H2 | 공개 자료 답변 경로(묶음 ⑥) | 함께 착지(GS에는 미연결) / 착지에서 제외(되돌리는 커밋 필요) |
| H3 | ADR 문서 | ② 번호 변경 `3ea7ece1` 반영 여부, GS boundary ADR-036 파일(p4) 반입 여부 |
| H4 | citation_verifier 운영 연결 | 착지와 동시에 경고 표시 활성 / 별도 조치 |
| H5 | 검색 코어 변경(묶음 ①②) | CLAUDE.md 예외 "Retrieval Engine 변경"이므로 승인 필수 |
| H6 | Tantivy 인덱스 | 재빌드 불필요 판단을 채택 / 확인 목적으로 백업 후 재빌드 |
| H7 | dev 반영 방식 | `origin/dev/dbma-engine` 푸시는 현재 금지 상태다. PR 경유 여부 |
| H8 | 착지 후 회귀 기준 | 3,554 passed 기준선을 새 병합 결과로 다시 측정 |

## 10. Phase 0 이후 게이트

```text
CUE READ-ONLY 비교 (이 문서)
→ HQ Phase 0 범위 승인 (H1~H8)
→ CUE 착지 (tmp 브랜치에서 병합·회귀, dev 푸시 없음)
→ C1 독립 검토 (READ-ONLY)
→ HQ dev 반영 승인 (검색 코어 변경, 인덱스 조치 포함)
→ dev 반영
→ [이후] CUE 새 ADR(Proposed) → C1 검토 → HQ 착수 승인 → CUE 구현 → …
```

- 역할: 구현은 CUE, 독립 검토는 C1, 승인은 HQ다.
- 검색 코어 변경과 Tantivy 재빌드는 HQ 승인 없이 하지 않는다.

## MUTATION

- 코드·ADR·prompt·index를 바꾸지 않았다. 인덱스와 데이터셋은 메타데이터만 읽었다.
- `git fetch`로 원격 추적 ref만 갱신했다.
- `git merge-tree --write-tree`는 객체 DB에 tree를 썼지만 ref·worktree는 바꾸지 않았다.
- 이 문서를 커밋·푸시하는 것만 수행한다.
