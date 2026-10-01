# Phase 0 사실 충돌 재검증 (READ-ONLY)

- 작성: CUE · 2026-09-30
- 범위: HQ가 지정한 C1~C6만 확인했다. FU-007 A/B/C는 다시 평가하지 않았다(C = APPROVED).
- 기준 ref(fetch 직후)
  - `origin/dev/dbma-engine` `195189b8`
  - FU-007 C `b39572aa`
  - `origin/main` `88ca969b`
- **MUTATION: NONE** — 코드·ADR·prompt·index 모두 변경하지 않았다. index는 메타 JSON만 읽었다.

## C1. FU-007 C 검색 코어의 dev 착지 여부 → **FU007-C-NOT-IN-DEV**

| 확인 | 결과 |
|---|---|
| ancestry | `git merge-base --is-ancestor b39572aa origin/dev/dbma-engine` → **아님**. `97ec140e`·`ab4f021c`도 dev에 없다. `b39572aa`를 가진 원격 브랜치는 `origin/tmp/fu007-combined-translation` 하나다 |
| `core/query_translation.py` | blob이 다르다(dev `caffb902` / C `6c78c7a6`). `git diff` 기준 +331 / −36. dev에는 `QUERY_TRANSLATION_VERSION`, `translate_query_terms`, `_HANGUL_ANY_RE`, 교단명 항목이 **없다**(C에서는 L36 `"4"`, L172, L261, L343) |
| `core/hybrid_candidate_pipeline.py` | blob이 다르다(`40cc1cbd` / `0ee269f2`). +82 / −7 |
| `core/candidate_generator.py` | blob이 다르다(`f3b6dbfc` / `f2b91169`). +48 |
| provenance (`git log -S`) | 아래 세 문자열을 dev 이력에서 찾으면 **0건**이다: `_carry_scripture_notation`, `_HANGUL_ANY_RE`, `QUERY_TRANSLATION_VERSION = 4`. `git grep`으로 dev tree를 찾아도 0건이다 |
| dev에서 이 3파일의 마지막 변경 | `398bc5cd`(09-26, dev 쪽 LLM 번역 = B), `64286013`(09-22), `fbb59191`(09-18) |

## C2. FU-007 C 전용 테스트 → **dev에 없음**

- `tests/test_fu007_combined_translation.py`의 위치
  - `b39572aa`: 있다(blob `c0a1d6a5`, 78줄)
  - dev: **없다**
- 같은 역할의 테스트가 dev에 있는지 찾아봤다. dev `tests/`에서 `carry_scripture`, `presbyterian`, `_VERSE_PHRASE_BOOST`, `scripture_ref_phrases`를 `git grep`하면 0건이다.
- provenance: `git log -S test_fu007_combined`로 찾으면 문서 커밋에만 나온다. dev에는 없다.

## C3. Tantivy 스키마 → **REBUILD-NOT-REQUIRED** (FU-007 C를 착지하는 것 때문에 재빌드가 필요하지는 않다)

| 확인 | 결과 |
|---|---|
| 1. dev 코드가 기대하는 스키마 | `candidate_generator.py` L123~136 기준 12개 필드: `title/content/author`(stored, default) + `title_search/content_search/author_search`(stored=False, default) + `tsu_id/document_id/source_file/book_id/language`(raw) + `page`(i64) |
| 2. 앱이 쓰는 인덱스 경로 | `DEFAULT_CANDIDATE_INDEX_DIR = os.path.join(DEFAULT_BENCH_DIR, "tantivy_index")`이고 `bench_dir: "output/bench"`다(dev `config.py` L72·L78, `config.yaml` L35). 실제 경로는 `~/DBMA/output/bench/tantivy_index` |
| 3~6. 실제 인덱스 스키마(`meta.json`) | 12개 필드의 이름·stored·tokenizer가 1번과 **같다**. `title_search`·`content_search`·`author_search` 셋 다 있다(stored=False, tokenizer default) |
| 7. 문서 수 | 세그먼트 22개의 max_doc 합(삭제 0) = **119,595**. `index_meta.json`의 `record_count` 119,595와 `tsu_dataset.jsonl` 줄 수 119,595가 서로 같다 |
| 색인 시점 코드의 동일성 | `build_schema`, `_tsu_to_tantivy_doc`, `build_index`, `_tokenize_for_index`는 **dev와 C에서 같다**. 함수 본문을 diff하면 C 쪽에 `_VERSE_PHRASE_BOOST` 상수 추가만 있고, 이 상수는 검색할 때만 쓴다 |
| 대조 | `origin/main`의 스키마에는 `*_search` 필드가 없다. 그래서 main 코드로 만든 인덱스라면 맞지 않는다 |

판정 근거:
- 인덱스를 만드는 코드가 dev와 C에서 같다.
- 현재 인덱스는 그 스키마로 되어 있다.
- 따라서 C를 착지해도 인덱스 형식은 바뀌지 않는다.
- 인덱스가 어떤 경위로 만들어졌는지(C4)는 이 판정과 별개로 확인되지 않았다.

## C4. 현재 인덱스의 생성 provenance → **UNKNOWN** (일부만 확인)

| 항목 | 결과 |
|---|---|
| 생성 함수 | `build_index`만 인덱스를 만든다. 호출 경로는 `open_or_build_index`(메타 파일이 없거나 레코드 수가 다를 때)와 `rebuild_tsu_index`다. 이 중 어느 경로로 만들어졌는지는 **UNKNOWN** |
| 시각 | `meta.json`·`index_meta.json`은 09-29 15:05:59, `tsu_dataset.jsonl`은 15:05에 쓰였다 |
| dataset | `tsu_manifest.json`: `generated_at 2026-09-29T15:05:35`, `build_commit c2cdf147`(`origin/feat/peb-v0.1` 계열), `builder_script scripts/build_tsu_dataset.py`, `dataset_sha256 bd246f22…` |
| 인덱스를 만든 코드 | **UNKNOWN**. `build_tsu_dataset.py`는 Tantivy 인덱스를 만들지 않는다(코드에 호출 없음). 다만 `c2cdf147`의 `candidate_generator.py` blob은 dev와 같은 `f3b6dbfc`다 |
| 생성 당시 kiwipiepy | **UNKNOWN**. 현재 venv는 0.23.2다. dev `requirements.txt`는 버전을 고정하지 않았고, C는 0.23.2로 고정했다 |
| 현재 dev 코드와의 스키마 일치 | 일치한다(C3) |

## C5. 호출자 범위 (사실만 정리. ④ 범위는 바꾸지 않음)

| 호출 위치 | 실제 호출 | GS 통합 영향 |
|---|---|---|
| `ui/pages/chat.py` L481 (C; dev L479) | `generate_answer()` 안의 `generate_stream` 호출. 스트림을 버퍼로 다 읽은 뒤 `to_result()` | ④의 "chat.py 2곳" 중 하나 |
| `ui/pages/chat.py` L566 (C; dev L564) | 채팅 화면: `st.write_stream` → `to_result()` | ④의 "chat.py 2곳" 중 하나 |
| `ui/pages/research.py` L317·L928 | `generate_answer()` 호출(L37에서 import) | L481을 바꾸면 **함께 영향을 받는다**. ④에 명시된 범위는 아님 |
| `scripts/smith_e2e_verify.py` L94 | `generate_answer()` 호출 | 같음(검증 스크립트) |
| `ui/pages/sermon_draft.py` | dev·C 모두 `generate_answer`·`generate_stream` 호출 **없음** | 영향 없음 |

- research.py와 smith_e2e_verify.py까지 범위를 넓힐지는 HQ가 정할 사항이다. CUE는 넓히거나 좁히지 않았다.

## C6. ④-5 문구 — 현재 코드와 HQ 확정 문구 비교 (HQ 문구는 바꾸지 않음)

| 내부 상태 | HQ 확정 문구 | 현재 코드 문구 (C 기준) |
|---|---|---|
| `grounded` | "사용자의 자료를 근거로 답을 드렸습니다." | **없음**(dev·C 전체에 없다) |
| `span_found_in_text == False` | "현 자료 근거로 하나를 채택하기에 부족한 부분이 있습니다." | **없음** |
| `insufficient_evidence` | "현 자료 내용이 충분하지 않습니다." | `core/grounded_answer.py` L89·L116: "이 질문은 현재 등록된 자료로는 답할 수 없습니다." / 근거 0건일 때 `chat.py` L93 `_NO_EVIDENCE_HOLD_TEXT`: "현재 등록된 자료에서 이 질문에 답할 근거를 찾지 못했습니다. …" |
| citation_verifier 경고 | "지정하신 자료를 재확인하세요." | `chat.py` L670과 `nae_public_section.py` L177: "⚠️ 출처 확인 필요 — 아래 인용은 이번에 검색된 근거로 확인되지 않았습니다." + 이슈별 줄. dev에는 이 경고가 없다 |

## 충돌 정리

- **해소된 것**
  - FU-007 C는 dev에 없다. ancestry·blob·`-S` 세 방법이 모두 같은 결과를 냈다.
  - C 전용 테스트도 dev에 없다.
  - 현재 인덱스 스키마에는 `*_search` 필드가 있고, dev와 C 코드가 기대하는 스키마와 같다.
  - C를 착지한다는 이유로 재빌드할 필요는 없다.
  - `generate_answer`의 호출자는 위 표와 같다.
  - 현재 문구와 HQ 문구의 차이는 C6 표와 같다.
- **남은 것**
  - 현재 인덱스를 만든 실행 경위와 그때의 kiwipiepy 버전은 UNKNOWN이다.
  - research.py·smith_e2e_verify.py를 범위에 넣을지는 HQ가 정할 사항이다. 사실 충돌은 아니다.
