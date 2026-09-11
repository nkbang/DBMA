# DBMA/NAE 2차 운영 검증 보고서 (Notch 3)

> ## ⚠ 관측 기준점 (Provenance) — dev/dbma-engine 전달 시 추가
>
> 이 보고서는 `main` 계열 워크트리에서 **코드를 판독**하고, `/Users/David/DBMA`
> 설치본에서 **런타임을 관측**해 작성됐다. 두 대상의 커밋이 다르다.
>
> | 항목 | 값 |
> |------|-----|
> | 런타임 관측 대상 | **`dev/dbma-engine` @ `daca402`** (2026-09-09 14:36:29 -0500) |
> | 코드 판독 위치 | `main` @ `32f59c9` (2026-09-08) — 관측 대상과 **다름** |
> | 관측 시각 | 2026-09-09 22:50 ~ 2026-09-10 00:49 (local) |
> | 작성 시 `dev/dbma-engine` tip과의 거리 | 관측 이후 **29 커밋** 유입 |
>
> ### 이 문서 중 이미 무효화된 항목
>
> 관측 이후 `dev/dbma-engine`에 들어온 수정으로 **아래 서술은 현재 코드와 다르다.**
> 나머지 서술은 `5146fa7` 기준으로 재확인했을 때 유효하다.
>
> | 무효화된 서술 | 대체한 상류 커밋 |
> |---------------|------------------|
> | 한국어 질의 `keywords=[]` → BM25 0 → fallback 슬라이스 | `31ef590` feat(retrieval): 한국어 QueryParser — 질의/문서 토큰화 비대칭 해소 |
> | `ContextAssembler`가 `<context id=…>`만 조립 | `bb688c4` feat(retrieval): LLM 문맥 블록에 서지정보(출처:) 주입 |
> | `wrap_ranked_candidates`가 `trust_tier=T1` 고정 (부록 B §B.2) | `5f1ccaa` fix(claim_guard): 검색 결과 TrustTier T1 위장 제거 + 규칙 2a 활성화 |
> | `compute_source_tier_bonus`가 전 코퍼스에 0.0 반환 | `4007926` feat(retrieval): SourceTierBonus를 source_tier 반영형으로 실효화 |
> | NAE on-disk TSU 합계 **7,760** (저작 3개) | Fuller Vol02·03·04 생성 → 현재 **14,453** (저작 6개). `nae_tsu_v1`은 여전히 3,319, Fuller 전권 `indexed=0` |
>
> ### 여전히 유효한 핵심 결론 (`5146fa7`에서 재확인)
>
> - `core/retrieval.py`의 `qdrant_url`은 보유만 하고 조회에 쓰이지 않음
> - BM25 무히트 시 `candidate_pool[:candidate_k]` 무순위 슬라이스 경로 존재
> - `Citation` 데이터클래스에 검수 상태·인용 가능 여부 필드 없음
> - `core/extractors.py` 무변경 → EPUB 서지(title/author) 판독 부재
> - `core/heading_provider.py` 무변경 → EPUB heading provider 미등록
> - `ui/components/citation_card.py` 무변경 → 부록 A의 카드 렌더 관측 그대로 유효
> - `ui/pages/chat.py:557-566` 구조 동일 → 부록 B의 "차단 아님, caption 1줄" 결론 유효
> - `ui/pages/chat.py:657-658` 조건 없음 → 부록 B §B.4(히스토리 재생 시 빈 caption) 유효


- 작성일: 2026-09-09 (검증 실행 22:50 ~ 23:40 KST 기준 로컬 시각)
- 대상: `/Users/David/DBMA` 실 설치본 + 로컬 실행 환경
- 코드 판독 위치: `/Users/David/DBMA/.claude/worktrees/confident-dewdney-a10c0e`
  — **정정(2026-09-10)**: 작성 당시 설치본과 "동일 커밋"이라고 적었으나 사실이 아니다.
  워크트리는 `main` @ `32f59c9`, 런타임 관측 대상 설치본은 `dev/dbma-engine` @ `daca402`였다.
  상단 Provenance 표 참조.
- 성격: 점검 보고서. 개선안·계획·우선순위를 포함하지 않는다

---

# 2차 점검 범위와 무변경 확인

## 수정 여부 (맨 위 명시)

**코드·설정·데이터·인덱스·데이터베이스·프롬프트·UI를 수정하지 않았다.**

| 대상 | 기준 SHA256(앞 16자) | 검증 후 | 결과 |
|------|---------------------|---------|------|
| `output/bench/tsu_dataset.jsonl` | `fc9705c844e339da` | `fc9705c844e339da` | **동일** |
| `output/bench/tsu_manifest.json` | `7539a6e0cc309c32` | `7539a6e0cc309c32` | **동일** |
| `output/bench/bible_index.sqlite3` | `a09a81822cf23ebd` | `a09a81822cf23ebd` | **동일** |
| `data/제련완성본/registry/documents.json` | `dcd7040dc858c743` | `dcd7040dc858c743` | **동일** |
| `config.yaml` | `f664eda6107dfd09` | `f664eda6107dfd09` | **동일** |
| `output/bench/` 파일 수 | 67 | 67 | **동일** |
| Qdrant `nae_ref_v1` / `nae_tsu_v1` | 34,948 / 3,319 pts | 34,948 / 3,319 pts | **동일** (scroll/count만 사용) |
| 컨테이너 `nae_qdrant` / `dbma_n8n` / `open-webui` | Up 2 weeks | Up 2 weeks | **미조작** |
| `dbma_qdrant` | Exited (143) | Exited (143) | **미기동** |
| 환경변수 `USE_INVERTED_INDEX` | unset | unset | **미변경** |
| `config.yaml modules.nae_pd.enabled` | `false` | `false` | **미변경** |

## 검증 과정에서 발생한 파생 상태 변화 (전부 공개)

읽기 전용을 목표했으나, **실제 실행을 관측하는 행위 자체가 만든 파생 산출물**이 3건 있다. 원본·정제본·TSU·인덱스·설정은 위 표대로 불변이다.

| # | 변화 | 원인 | 규모 |
|---|------|------|------|
| D1 | `cache/embeddings/` 파일 **2,144 → 2,160개 (+16)** | `core/retrieval.py::EmbeddingCache.lookup()`이 캐시 미스 시 `insert()`를 호출한다(=설계된 동작). 실제 질의 실행의 불가피한 부산물 | +16 JSON 파일 |
| D2 | `data/chat_session_history.json` **신규 생성 (144 bytes)** | Streamlit Chat에 질의를 제출하면 `ui/pages/chat.py`가 매 턴 디스크에 미러링한다. 내용은 사용자 질문 2건뿐이며 assistant 턴은 없다 | 신규 파일 1개 |
| D3 | Ollama에 `my-theology-bot-v2:latest`(53.7GB)가 VRAM 상주 | 답변 생성 호출로 모델이 로드됨. 서비스 자체는 시작·중지·재시작하지 않았다 | 런타임 메모리 |

> D2에 대해: 사용자 질문이 2건 기록된 것은, Chat 입력창에서 Return 키와 "Send message" 버튼이 각각 한 번씩 제출로 처리되었기 때문이다. 삭제는 별도 금지 사항이므로 그대로 두었다.

## 검증 중 발생한 부수 행위 1건

`my-theology-bot-v2`의 응답 지연 원인을 확인하려고 `curl http://localhost:11434/api/generate`(`num_predict=16`)를 1회 호출했다. 이 호출은 120초 타임아웃까지 응답이 없었고, 그 과정에서 **두 번째 `llama-server` 프로세스가 일시적으로 생성**되었다가 자연 종료되었다. 진행 중이던 Streamlit 생성 요청과 경합했을 가능성을 배제할 수 없으므로 기록한다.

## 일시 기동 후 종료한 서비스

| 서비스 | 명령 | 종료 확인 |
|--------|------|-----------|
| Streamlit (`dbma_ui.py`) | `python -c "os.chdir('/Users/David/DBMA'); streamlit run dbma_ui.py --server.headless=true --server.port=8501"` (pid 10949) | `pid 10949 terminated`, `8501 listeners: 0` |

---

# 실행 환경과 활성 경로

## 실행 위치 의존성 (실행으로 확인)

`core/config.py:72`의 `DEFAULT_BENCH_DIR = _yaml_dirs.get("bench_dir", "output/bench")`는 **BASE_DIR이 아니라 cwd 기준 상대 경로**다. 따라서 TSU 데이터셋·bible index·tantivy index·telemetry 경로가 모두 프로세스의 현재 디렉터리에 종속된다.

```
cwd: /Users/David/DBMA
DEFAULT_TSU_DATASET_PATH: output/bench/tsu_dataset.jsonl exists: True
```

반면 `DATA_DIR`은 `BASE_DIR`(= `core/`의 상위) 기준 절대 경로다. 본 검증의 모든 실행은 `os.chdir('/Users/David/DBMA')` 후 수행했다.

## 활성 경로 판정 (실행 + 코드 판독)

| 경로 | 게이트 | 실행 관측 |
|------|--------|-----------|
| `core.retrieval.QueryProcessor` (legacy) | `USE_INVERTED_INDEX` unset → `is_enabled()==False` | **실행됨.** `QueryProcessor class: QueryProcessor  engine: RetrievalEngine` |
| `HybridQueryProcessor` (tantivy 역인덱스) | 동일 게이트 | 실행되지 않음 (환경변수 미설정, 변경하지 않음) |
| `NAE.reference_retrieval_adapter.search_reference` | 게이트 없음 | **실행됨** (아래 별도 절) |
| `NAE.retrieval_adapter.search` / `bridge_query` | `modules.nae_pd.enabled=false` | **실행 시 예외 발생 확인** (아래 별도 절) |
| Qdrant `:6333` (`dbma_qdrant`) | 컨테이너 Exited | 미기동. 아래 참조 |

`RetrievalEngine` 인스턴스는 `qdrant_url`/`collection_name`을 **보유하지만 사용하지 않는다**. 실행 시 확인된 값:

```
engine.qdrant_url=http://localhost:6333  collection=dbma_sermon
corpus loaded (engine.tsus): 1363   candidate_k=100
cache dir: /Users/David/DBMA/cache/embeddings
```

`grep -n 'qdrant' core/retrieval.py` → 1202행(파라미터 기본값), 1208행(대입) 2곳뿐. 조회 호출 없음.

## 로드된 모델 (실행 관측)

```
loaded: bge-m3:latest 566.70M F16 vram=673,049,476
loaded: my-theology-bot-v2:latest 70.6B Q4_K_M vram=53,736,510,586  context_length=32768
```

UI 사이드바 설정 콤보박스: `Selected my-theology-bot-v2:latest. 답변 생성 모델`.

---

# Streamlit UI 및 Chat 런타임 관측

## Q1. Streamlit UI가 기동되는가 → **기동된다 (실행 확인)**

```
Uvicorn server started on 0.0.0.0:8501
Local URL: http://localhost:8501
```

`lsof -nP -iTCP:8501 -sTCP:LISTEN` → `Python 10949 ... TCP *:8501 (LISTEN)`.

## 실제 렌더 관측 결과

| 화면 | 관측 결과 |
|------|-----------|
| 온보딩 | 렌더됨. 브라우저 탭 제목 `내서재 · NAE`. "연구 시작하기 / 자료 불러오기 / 나중에 하기" 버튼 존재. 코드 판독 결과 `st.session_state["show_onboarding"]`만 변경하며 디스크 기록 없음 |
| 홈(Dashboard) | 렌더됨. **"문서 1권 · 마지막 업데이트 2026-09-07 23:29"**, "처리 완료 1권 · 미처리 0권", 최근 자료에 `주석 / 매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub / 2026-09-07` |
| AI에게 질문(Chat) | 렌더됨. "검색 범위" expander에 `전체 파일 / 다중 파일 / 단일 파일` 라디오, "대화 초기화" 버튼, 입력창 `질문을 입력하세요...` |
| 연구하기(Research, `자료 찾기`) | 렌더됨. "검색어" textarea, "결과 수" 슬라이더(기본 10, 범위 1~50), "검색 실행" 버튼, `AI 답변` / `참고한 자료` / `검색 분석` 3개 섹션 |
| 사이드바 | 9개 항목: 홈 / 내 자료 / 자료 등록 / 자료 찾기 / AI에게 질문 / 연구하기 / 설교 준비 / 설교 모음 정리 / 도움말 + 설정 |

## 답변 생성이 완료되지 않음 (실행 관측)

| 시도 | 경로 | 질의 | 결과 |
|------|------|------|------|
| 1 | Chat (`ui/pages/chat.py`) | `마태복음 6:9-13 주기도문 해석` | 질의 제출 후 **약 23분간 assistant 턴 미생성**. `chat_session_history.json`은 72B → 144B(사용자 턴 2건)에서 정지, `"role": "assistant"` 0건. 화면의 assistant 말풍선은 빈 상태 유지 |
| 2 | Research (`ui/pages/research.py`) | 동일 | "검색 실행" 클릭 후 **약 5분 경과 시점에 브라우저 pane 연결이 끊어져 Streamlit 세션 리셋**. 재시도에서 다시 클릭 후 약 4분간 `stStatusWidget` 존재(=스크립트 실행 중) 유지, 결과 미렌더 |

관측된 프로세스 상태:

```
t=1s   llama_cpu=12  streamlit_cpu=0.0
t=61s  llama_cpu=12  streamlit_cpu=0.0
t=151s llama_cpu=10  streamlit_cpu=0.0
t=287s llama_cpu=10  streamlit_cpu=0.0
```

`llama-server`(pid 58568)는 10~13% CPU로 지속 동작, Streamlit(pid 10949)은 0.0%로 응답 대기. `lsof -p 10949` → `127.0.0.1:52306->127.0.0.1:11434 (ESTABLISHED)`, `127.0.0.1:56131->127.0.0.1:11434 (ESTABLISHED)` 2개 연결 유지.

동일 시간대 별도 검증: `curl http://localhost:11434/api/generate`(`my-theology-bot-v2`, `num_predict=16`)이 **120초 타임아웃까지 무응답**.

`ui/pages/research.py:277` 주석 `# Always run AI answer path alongside search (UX-007 §4.1)` — Research 경로도 `generate_answer()`를 항상 호출하므로, 검색 결과·citation card는 생성이 끝나야 화면에 그려진다. 따라서 **두 경로 모두 답변 생성 완료에 의존한다.**

> 참고: `output/eval/test_run_002_eval.jsonl`의 2건 레코드 타임스탬프는 `06:11:37` → `06:18:18`(약 6.7분/2건)이며, 당시 judge 모델도 70B였다. 이번 관측치와 비교되는 과거 기록으로만 제시한다. 원인 규명은 하지 않았다.

**결론: citation card의 화면 렌더는 이번 검증에서 관측하지 못했다.** 아래 "Citation Card" 절의 값은 화면 관측이 아니라 코드 경로 실행 결과이며, 그렇게 명시한다.

---

# 기본 DBMA 검색 실행 결과

`QueryProcessor.process()`를 실제 코퍼스에 대해 직접 실행한 결과다(화면 렌더 아님, 실행 결과임).

## Q3. 1,363개 청크를 실제로 검색하는가 → **적재는 1,363건, 실제 점수 계산은 최대 100건**

```
corpus loaded (engine.tsus): 1363   candidate_k=100
```

`retrieve()`의 STEP 2 이후 downstream 스코어링은 `bm25_top_k_indices`(≤ `candidate_k=100`)로 제한된다. 실행으로 확인한 후보 풀 형성:

| 질의 | `_metadata_filter()` 결과 | candidate_pool | BM25 non-zero | 실제 사용 풀 |
|------|--------------------------|----------------|---------------|--------------|
| `매튜 풀 주석에서 마태복음의 핵심 해석을 찾아라.` | **1363** (필터 무효) | 1363 | **0** | `pool[:100]` = 코퍼스 인덱스 **0..99** |
| `마태복음 6:9-13 주기도문 해석` | **16** | 16 | **0** | 16건 전체 (인덱스 157..1269) |

## BM25가 0인 이유 (실행 + 코드 판독)

`QueryParser.parse()` 실행 결과:

```
'매튜 풀 주석에서 마태복음의 핵심 해석을 찾아라.'   keywords=[] refs=[]            intent=unknown
'구하라 그리하면 너희에게 주실 것이요 …'            keywords=[] refs=[]            intent=unknown
'마태복음 6:9-13 주기도문 해석'                     keywords=[] refs=['MAT 6:9-13'] intent=unknown
'grace and forgiveness in Matthew'                keywords=['grace','forgiveness','matthew'] refs=[] intent=theological
```

`core/retrieval.py:470` — `words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())`. **ASCII 라틴 문자만 추출**하므로 한국어 질의는 `keywords=[]`가 된다. `bm25_score([], text)` → `0.0` (실행 확인).

한편 문서 토크나이저는 한국어를 처리한다: `_tokenize('구하라 그리하면 너희에게')` → `['구하', '그리', '너희']`. 두 경로가 다르다.

## Q5. top-k로 반환되는 후보 (실행 결과, k=5)

### A1 `매튜 풀 주석에서 마태복음의 핵심 해석을 찾아라.`
`wall=109ms total_ms=106 vector=92ms bm25=0.18ms theo=12.5ms`

| # | score | chunk | verse_mapping | 발췌 |
|---|------:|-------|---------------|------|
| 1 | 0.3472 | `chunk_00017` | `{book_id: MAT}` | 그리스도인들로 하여금 우리 구주의 언행을 네 명의 복음서 기자… |
| 2 | 0.3409 | `chunk_00016` | `{book_id: MAT}` | (요한복음 21:25은 이것을 분명하게 밝힌다), 주님이 말씀하신 것들이나… |
| 3 | 0.3293 | `chunk_00018` | `{MAT, ch25, v1-13}` | 탄생과 그 이전의 일들에 대해서 좀 더 자세하게 다룬다… |
| 4 | 0.3246 | `chunk_00006` | `{book_id: MAT}` | 따라서 사람들이 다른 책들을 읽느라고 성경을 읽으려 하지 않는다면… |
| 5 | 0.3231 | `chunk_00005` | `{book_id: MAT}` | 이라 불리는데 ("성경"이라는 말은 헬라어에서 "책"을 뜻하는 '비블로스'… |

반환된 5건은 모두 코퍼스 인덱스 0~99 구간(문서 앞부분, 서문·총론)에 속한다.

### A2 `구하라 그리하면 너희에게 주실 것이요 찾으라 그리하면 찾아낼 것이요` (본문에 실재하는 정확 문구)
`wall=82ms total_ms=82 vector=75ms`

| # | score | chunk | 발췌 |
|---|------:|-------|------|
| 1 | 0.3558 | `chunk_00090` | 원하건대 들을지어다 너희가 사람을 괴롭히고서… (이사야/아하스 문맥) |
| 2 | 0.3384 | `chunk_00089` | 하지만 아하스는 하나님이 말씀하신 것이 옳다는 것을… |
| 3 | 0.3359 | `chunk_00087` | 예물로 보내" 환심을 사서, 결국 동맹을 이끌어낸다 (왕하 16:7-8)… |
| 4 | 0.3314 | `chunk_00098` | 될 것이다." 왜냐하면, 당시에 르신은 유다 성읍 엘랏을 점령하였을… |
| 5 | 0.3309 | `chunk_00095` | 구하기를 거절하였지만, 하나님은 네게 네가 구하기를 두려워하는 징조를… |

**질의 문구를 그대로 포함하는 청크는 `chunk_00280`인데, top-5에 포함되지 않았다.** 반환된 5건은 모두 인덱스 87~98 구간(0..99 fallback 풀 내부)이다. zero-hit은 아니며 5건이 반환되었다.

### A3 `마태복음 6:9-13 주기도문 해석`
`wall=1708ms total_ms=1707 vector=1699ms`  `scripture_refs=['MAT 6:9-13']`

| # | score | chunk | verse_mapping |
|---|------:|-------|---------------|
| 1 | 0.5372 | `chunk_00280` | `{MAT, ch6, v9-13}` |
| 2 | 0.5144 | `chunk_01027` | `{MAT, ch6, v1-34}` |
| 3 | 0.4962 | `chunk_01028` | `{MAT, ch6, v1-34}` |
| 4 | 0.4736 | `chunk_00261` | `{MAT, ch6, v14}` |
| 5 | 0.4582 | `chunk_00849` | `{MAT, ch6, v15}` |

성경 참조가 인식된 질의에서는 `_metadata_filter()`가 1363 → 16으로 좁혔고, A2에서 누락됐던 `chunk_00280`이 1위로 반환되었다.

## Q4. 전체 코퍼스가 LLM으로 전달되는가 → **아니다. top-k만 전달된다 (실행 확인)**

`ContextAssembler.assemble(candidates[:k], ...)` 실행 결과 `llm_context_block` 크기:

| 질의 | k | context 문자수 |
|------|---:|---------------:|
| A1 | 5 | 3,478 |
| A2 | 5 | 2,324 |
| A3 | 5 | 5,033 |

`tsu_dataset.jsonl` 전체는 3,414,842 bytes다. 컨텍스트 블록 형식은 `<context id="{tsu_id}" score="{f}">…</context>` 반복이며, 전체 코퍼스가 투입되는 경로는 관측되지 않았다.

## 관측된 부수 사실

- `ResponsePackage.candidates`와 `.top_k_results`는 **동일 객체**다(`r.candidates is r.top_k_results` → `True`). 따라서 `to_dict()`의 `total_candidates`는 후보 풀 크기가 아니라 k와 같다.
- A1 #3(`chunk_00018`)은 `verse_mapping`이 `MAT 25:1-13`이지만 본문은 마태복음 서론이다. A3 #4(`chunk_00261`)는 `MAT 6:14`로 매핑됐으나 본문은 주기도문 12절 해설이다. verse_mapping과 본문 내용의 대응은 일부 어긋난다(관측 사실만 기록).

---

# Citation Card 및 ResponsePackage 관측

> **이 절의 값은 코드 경로 실행 결과이며, 화면 렌더 관측이 아니다.** 화면 렌더는 답변 생성 미완료로 관측하지 못했다(위 절 참조).

## Q6. citation card에 전달되는 실제 인자값 (A3, k=3)

| 인자 | #1 | #2 | #3 |
|------|----|----|----|
| `source_file` | `'매튜 풀 청교도 성경주석 14  마태복음 (매튜 풀).epub'` | 동일 | 동일 |
| `text_location` | **`None`** | **`None`** | **`None`** |
| `doc_type` | **`None`** | **`None`** | **`None`** |
| `author` | **`None`** | **`None`** | **`None`** |
| `citation_title` | **`None`** | **`None`** | **`None`** |
| `relevance_score` | 0.5372 | 0.5144 | 0.4962 |

`ui/components/citation_card.py`는 값이 falsy인 필드를 행 자체로 만들지 않는다(`if author:` / `if citation_title:` …). 따라서 실제로 생성되는 meta 행은:

```
실제 렌더되는 meta 행: ['문서']
미표시:               ['저자', '출처', '본문 위치', '자료 유형']
별점:                 ★★★☆☆ (0.5372) / ★★★☆☆ (0.5144) / ★★☆☆☆ (0.4962)
```

headline(`_render_clickable_source`)의 `display_label`은 `heading_hierarchy or source_file or "출처 미상"` 순으로 결정되며, `heading_path`가 비어 있어 **3건 모두 파일명**이 된다.

## Q7. page/chapter/title/heading_path 결측의 실제 영향

`tsu_dataset.jsonl` 1,363건 전건 집계(1차 보고서 재확인):

| 필드 | non-null |
|------|---------:|
| `title` | 0 |
| `author` | 0 |
| `page` | 0 |
| `chapter` | 0 |
| `structure.heading_path` 비어있지 않음 | 0 |

원인 경로(코드 판독 + 실행):

1. `core/extractors.py`에는 `_extract_pdf_title_author()`(108행)와 `_extract_docx_title_author()`(124행)만 있고 EPUB용 서지 판독 함수가 없다. 원본 EPUB에는 값이 존재한다 — `ebooklib` 직접 판독: `title=('매튜 풀 청교도 성경주석 14 : 마태복음',)`, `creator=('매튜 풀', role=aut)`, `publisher=('크리스챤다이제스트',)`, ISBN `978-89-447-8472-9`.
2. `core/heading_provider.py:151-155`에 등록된 provider는 `md`/`markdown`/`txt`/`pdf`뿐이다. `core/tsu_builder.py:305`는 `if source_type == "pdf":`일 때만 assembler 경로를 타고, EPUB은 `HeadingStack` ATX 경로로 간다.
3. 정제본 `매튜 풀 …_epub.md`의 ATX 헤딩 수: `grep -c '^#'` → **0**. 따라서 ATX 경로에서도 heading_path가 생성되지 않는다.

`Citation` 데이터클래스(`core/retrieval.py:1852`)의 필드는 `citation_id, tsu_id, scripture_reference, source_title, source_author, document_id, content_excerpt, evidence_confidence, retrieval_score, source_file, language, source_type`이다. **검수 상태·인용 가능 여부에 해당하는 필드는 없다.**

실행된 `Citation` 값(A3):

```
CIT[1] ref='MAT 6:9-13'  title=None author=None conf=0.5 file='매튜 풀 …epub'
CIT[2] ref='MAT 6:1-34'  title=None author=None conf=0.5
CIT[3] ref='MAT 6:1-34'  title=None author=None conf=0.5
CIT[4] ref='MAT 6:14'    title=None author=None conf=0.4
CIT[5] ref='MAT 6:15'    title=None author=None conf=0.4
```

A1처럼 `verse_mapping`에 chapter가 없는 경우 `scripture_reference`는 **`'MAT ?:?'`** 문자열로 생성된다(실행 확인). `evidence_confidence`는 `metadata["provenance"]["confidence"]`에서 오며 `None`인 건도 있었다(A1 #4, #5).

---

# NAE Reference Qdrant 경로 관측

## Q8. Smith 결과가 실제로 context에 삽입되는가 → **삽입된다 (실행 확인)**

### `should_activate_smith()` 실행 결과

| 질의 | activate | rewrite |
|------|----------|---------|
| `모세는 누구인가?` | **True** | `'모세는 누구인가'` |
| `베들레헴은 어떤 곳인가?` | **True** | `'베들레헴은 어떤 곳인가'` |
| `Who was Aaron?` | **True** | `'Who was Aaron'` |
| `매튜 풀 주석에서 마태복음의 핵심 해석을 찾아라.` | **True** | `None` |
| `마태복음 6:9-13 주기도문 해석` | **True** | `None` |
| `구하라 그리하면 너희에게 주실 것이요 …` | False | `None` |

일반 주석 질의(A1)와 성경 참조 질의(A3)에서도 활성화된다.

### `search_reference()` 실행 결과

| 질의 | latency | results | 첫 결과 |
|------|--------:|--------:|---------|
| `모세는 누구인가` | **416 ms** | 3 | `BAP-REF-SMITH-VOL03` vol_3 p.237~237, `heading_context='2016 MORTER'` |
| `베들레헴은 어떤 곳인가` | **79 ms** | 3 | `BAP-REF-SMITH-VOL01` vol_1 p.312~314, `heading_context='BETHXEHEH'` |
| `마태복음 6:9-13 주기도문 해석` | **70 ms** | 3 | `BAP-REF-SMITH-VOL02` vol_2 p.68~68, `heading_context='11. 1-12'` |

zero-hit·timeout·예외 없음. 반환 키: `chunk_index, content_type, heading_context, page_end, page_start, source_id, text, volume`. `chat.py`의 smith 필터(`"smith" in source_id/volume`)는 전부 매치.

### `_inject_smith_context()` 실행 결과

| 질의 | context BEFORE | AFTER | delta | inject_ms | entries |
|------|---------------:|------:|------:|----------:|--------:|
| `모세는 누구인가` | 4,623 | **8,022** | +3,399 | 234 | 3 |
| `마태복음 6:9-13 주기도문 해석` | 5,033 | **6,753** | +1,720 | 15 | 3 |

`'<reference>' in llm_context_block` → **True**. 삽입된 실제 블록:

```
참고: 아래 <reference> 항목은 보조 자료(Smith Bible Dictionary)입니다. 주요 근거는
위 신학 문헌(TSU) 및 성경 본문을 우선하고, 이 참고 자료가 그 해석을 대체하거나
덮어쓰지 않도록 하십시오.

<reference>
[참고 자료: Smith Bible Dictionary]

[1] 2016 MORTER (Vol. vol_3, p.237)
[2016 MORTER]

• MOSE'ROTH (rrTip'TB: Msuroiyott; Vat in ver. 30, Mo<roup»8: Mo

MO'SES (Heb. Md$heJt, TWjiti ^ drawn: LXX, Josephus, Philo, the most ancient MSS.
of N. T., M»So-ij», declined Mo-So-sW, Ma-Oni or M»Bof , M»Wa or MoCo^r: …
```

삽입 텍스트의 OCR 상태는 위 원문 그대로다(`Msuroiyott`, `BETHXEHEH`, `Beil-lnhm`, `Motet` 등). 관측 사실로만 기록한다.

`ui/pages/chat.py`에서 `_inject_smith_context()`의 반환값은 컨텍스트 삽입에 쓰이며, **Smith 항목이 `render_citation_card`로 전달되는 호출은 코드에 없다**(`grep render_citation_card` 결과: `chat.py:770`은 TSU candidate 기준). 화면 렌더는 관측하지 못했으므로 이 항목은 코드 판독 결과다.

---

# NAE TSU와 Qdrant 인덱스 정합성 관측

## Q9. `nae_tsu_v1`이 활성 query path에서 사용되는가 → **사용되지 않는다 (실행 확인)**

플래그를 바꾸지 않고 호출한 결과:

```
NAE.retrieval_adapter.search([0.1]*1024)
  -> NaePdModuleDisabledError: nae_pd module is disabled —
     enable via `scripts/dbma_module.py enable nae_pd` first

NAE.retrieval_adapter.bridge_query("교회 회원권과 권징")
  -> NaePdModuleDisabledError: (동일)
```

호출처는 `ui/pages/research.py:566` 1곳뿐이며 `ui/pages/chat.py`는 호출하지 않는다(코드 판독).

## Q10. payload 주요 필드 분포 (전 포인트 scroll, 읽기 전용)

### `nae_tsu_v1` — 3,319 포인트 전수

| 필드 | 분포 |
|------|------|
| `review_status` | `'verified'` : **3,319 (100%)** |
| `usage_permission` | `'research'` : 3,319 (100%) |
| `copyright_status` | `'public_domain'` : 3,319 (100%) |
| `access_control` | `'public'` : 3,319 (100%) |
| `tsu_access` | `'full'` : 3,319 (100%) |
| `page` | non-null : **3,319 (100%)** |
| `citation_policy` | `None` : **3,319 (100%)** |
| `citation_policy_status` | `'AUTHORITATIVE_SOURCE_MISSING'` : 3,319 (100%) |
| `category_status` | `'AUTHORITATIVE_SOURCE_MISSING'` : 3,319 (100%) |
| `source_type` | `'reference'` : 3,319 (100%) |
| `source_id` | `BAP-CHURCH-DAGG-001` : 2,958 / `BAP-CHURCH-HISCOX` : 361 |
| `identifier` | `Dagg_Church_Order` : 2,958 / `Hiscox_Standard_Manual` : 361 |

### `nae_ref_v1` — 34,948 포인트 전수

| 필드 | 분포 |
|------|------|
| `source_id` | `BAP-REF-SMITH-VOL04` 9,532 / `VOL01` 8,841 / `VOL02` 8,391 / `VOL03` 8,184 |
| `volume` | `vol_4` 9,532 / `vol_1` 8,841 / `vol_2` 8,391 / `vol_3` 8,184 |
| `content_type` | `'reference_dictionary'` : 34,948 (100%) |
| `page_start` | non-null **33,802** / null **1,146** (3.3%) |
| `page_end` | non-null 33,802 / null 1,146 |
| `heading_context` | non-empty 34,910 / empty·null 38 |
| `review_status` | **필드 자체 부재 : 34,948 (100%)** |
| `usage_permission` | **필드 자체 부재 : 34,948 (100%)** |
| `copyright_status` | **필드 자체 부재 : 34,948 (100%)** |
| `citation_policy` | **필드 자체 부재 : 34,948 (100%)** |

`page_start` 범위: min=1, max=987 (n=33,802).

## Q11. on-disk vs Qdrant 차이의 집중 지점 → **`review_status`에 정확히 대응 (읽기 전용 추적 완료)**

on-disk `NAE/corpus/tsu/*/tsu.json`의 `id` 집합과 `nae_tsu_v1`의 `tsu_id` 집합을 대조:

| identifier | on-disk | 인덱스 일치 | 미색인 | 미색인 건의 `review_status` |
|------------|--------:|-----------:|------:|-----------------------------|
| `Dagg_Church_Order` | 3,377 | **2,958** | 419 | `generated` 397, `rejected` 22 |
| `Hiscox_Standard_Manual` | 740 | **361** | 379 | `generated` 379 |
| `Fuller_Complete_Works_Vol01` | 3,643 | **0** | 3,643 | `generated` 3,643 |
| 합계 | 7,760 | **3,319** | 4,441 | `generated` 4,419 / `rejected` 22 |

on-disk `review_status` 분포:

| identifier | verified | generated | rejected |
|------------|---------:|----------:|---------:|
| `Dagg_Church_Order` | **2,958** | 397 | 22 |
| `Hiscox_Standard_Manual` | **361** | 379 | 0 |
| `Fuller_Complete_Works_Vol01` | 0 | 3,643 | 0 |

**`review_status == "verified"` 건수 합계 3,319 = `nae_tsu_v1` 포인트 수와 정확히 일치한다.** `duplicate_of`가 설정된 레코드는 세 저작 모두 0건이다.

## Q12. 경로별 지연시간과 zero-hit

| 경로 | 질의 | 지연 | 결과 수 | zero-hit |
|------|------|-----:|--------:|----------|
| 기본 DBMA 검색 | A1 | 109 ms (vector 92) | 5 | 아니오 |
| 기본 DBMA 검색 | A2 | 82 ms (vector 75) | 5 | 아니오 |
| 기본 DBMA 검색 | A3 | 1,708 ms (vector 1,699) | 5 | 아니오 |
| Smith reference | `모세는 누구인가` | 416 ms | 3 | 아니오 |
| Smith reference | `베들레헴은 어떤 곳인가` | 79 ms | 3 | 아니오 |
| Smith reference | `마태복음 6:9-13 …` | 70 ms | 3 | 아니오 |
| NAE bridge | `교회 회원권과 권징` | 즉시 예외 | 0 | **예외 반환** (`NaePdModuleDisabledError`) |
| 답변 생성 (UI Chat) | `마태복음 6:9-13 …` | **미완료 (≈23분)** | — | 결과 미도달 |
| 답변 생성 (UI Research) | 동일 | **미완료 (≈4~5분 후 관측 중단)** | — | 결과 미도달 |

임베딩 캐시 통계(3질의 연속 실행): `hits=200 miss=16 hit_rate=0.926`. 
현재 코퍼스에 대한 캐시 커버리지는 전건 대조 결과 **102 / 1,363 = 7.5%**이며, 실제 질의에서 히트율이 높았던 이유는 fallback 풀(코퍼스 앞부분 0..99)과 A3의 metadata 필터 결과가 이미 캐시된 구간에 몰려 있었기 때문이다.

---

# Gold Query와 현재 Corpus 호환성

## Q13. 100개 gold query와 현재 corpus의 source coverage

현재 corpus:
```
book_id 집합    : ['MAT']
source_file 집합 : {'매튜 풀 청교도 성경주석 14  마태복음 (매튜 풀).epub'}
```

`tests/gold_queries.json`의 레코드 스키마: `id, category, query, expected_books, expected_documents, expected_ranking_priority, notes`. **TSU ID나 document ID를 직접 참조하는 필드는 없다** — 대조 가능한 축은 `expected_books`뿐이다.

| 판정 | 건수 | 비고 |
|------|-----:|------|
| **FULL** (expected_books ⊆ 현재 corpus) | **3** | `BK002`, `MP001`, `KO002` — 모두 `['MAT']` |
| **PARTIAL** (일부 교집합) | **10** | `TH008`, `TH014`, `DO003`, `DO008`, `DO010`, `DO011`, `DO012`, `OG007`, `AM007`, `AM012` |
| **NONE** (교집합 없음) | **73** | |
| **expected_books 없음** | **14** | `KO003·KO005·KO006·KO007` + `NG001`~`NG010`(negative 범주 전체) |
| 합계 | 100 | |

corpus에 없는 `expected_book` 상위: `ROM` 29, `JN` 17, `GAL` 12, `HEB` 10, `GEN` 9, `1CO` 9, `EPH` 9, `PSA` 8, `PHP` 8, `EXO` 8, `ACT` 6, `1PE` 5, `JAS` 5, `JER` 5, `REV` 4. 골드셋이 참조하는 고유 성경 book 종류는 **45종**이고 현재 corpus는 **1종(MAT)**이다.

범주 분포: `book_reference` 15, `theme` 15, `ambiguous` 14, `doctrine` 12, `historical` 10, `negative` 10, `original_language` 8, `mission_pastoral` 8, `korean` 8.

## Q14. `output/eval/*.jsonl`이 현 corpus와 연결 가능한가 → **연결되지 않는다**

현재 corpus: `tsu_id` 1,363개, `document_id` **1개**(`c6618c640f79…`).

| 파일 | records | chunk_id 참조 | 현재 corpus에 존재 | timestamp 범위 | groundedness |
|------|--------:|--------------:|------------------:|----------------|--------------|
| `test_run_001_eval.jsonl` | 2 | 4 | **0** | 2026-07-27T06:05 ~ 06:07 | n=2, 전부 0.0 |
| `test_run_002_eval.jsonl` | 2 | 4 | **0** | 2026-07-27T06:11 ~ 06:18 | n=2, 전부 0.0 |
| `baseline_002_sermon_eval.jsonl` | 3 | 0 (`retrieved_candidate_ids` 스키마) | — | 2026-07-27T23:53 ~ 2026-07-28T00:05 | n=3, 전부 5.0 |
| `beta_llama31_8b_…_sermon_eval.jsonl` | 3 | 0 (동일) | — | 2026-07-28T18:59 ~ 19:04 | n=3, 전부 5.0 |

`test_run_*`이 참조하는 document_id는 `b968aae3a042d481…`, `d02a5e7097fe861a…`, `3474a6826061ff33…` 3종이며, **현재 registry의 유일한 PROCESSED 문서와 일치하지 않는다.** 두 sermon eval 파일은 스키마가 달라(`retrieved_candidate_ids`, `generated_text`, `scripture_and_theme`) chunk 단위 대조 축이 없다.

---

# ClaimGuard 및 관측성 점검

## Q15. ClaimGuard 정상 실행 및 fail-open → **둘 다 관측됨**

`core/generation.py::_run_claim_guard(answer, response)` 실제 실행:

| 입력 | 결과 |
|------|------|
| `"이것은 성경 전체에서 유일하게 나타나는 최초의 기도이며, 모든 학자가 반드시 동의한다."` | `risk_level=RiskLevel.HIGH`<br>`matched_terms=['최초','유일','반드시','성경 전체에서','모든 학자','유일하게']`<br>`absolute_claim_blocked=True`<br>`reason="전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)"`<br>`scope_qualifier_required=False`, `suggested_wording=None`, 소요 0 ms |
| `"매튜 풀은 주기도문을 세 가지 간구로 나누어 설명한다."` | `risk_level=RiskLevel.NONE`, `matched_terms=[]`, 소요 0 ms |

fail-open 경로 — `core.generation.ClaimGuard`를 **인메모리에서만** 예외 발생 객체로 치환(파일 미수정, 프로세스 종료와 함께 소멸):

```
[GenerationService._run_claim_guard] ClaimGuard 실패 (답변은 계속 사용): forced failure for observation
반환: risk_level=RiskLevel.NONE  reason='claim_guard 실패: forced failure for observation'
```

예외가 발생해도 `RiskLevel.NONE` 결과를 반환하고 답변은 그대로 사용된다(fail-open). `absolute_claim_blocked=True`가 답변 자체를 차단하는지는 답변 생성이 완료되지 않아 UI에서 확인하지 못했다(UNKNOWN 항목 참조).

관련 테스트 read-only 실행:
```
pytest tests/test_generation_claim_guard.py tests/test_rag_judge.py \
       tests/test_dbma_nae_module_packaging.py -q
→ 102 passed, 7 warnings in 4.00s
```

## Q16. 로그·telemetry 부재가 관측을 막는가 → **기본 경로에는 지속 저장이 없다**

총 6회의 `QueryProcessor.process()` 실행 + UI 질의 2건 이후 상태:

| 경로 | 상태 |
|------|------|
| `output/bench/search_telemetry.sqlite3` | **ABSENT** |
| `output/bench/search_cache.sqlite3` | **ABSENT** |
| `logs/` (config `directories.logs_dir`) | **ABSENT** |
| `data/chat_session_history.json` | **생성됨** — 사용자 질문 2건만, assistant 턴 0건 |
| `cache/embeddings/` | 2,144 → 2,160 (+16) |

배선 상태(코드 판독):
- `SearchTelemetry.record_query()` 호출은 `core/hybrid_candidate_pipeline.py:323` 1곳뿐이며, 이 경로는 `USE_INVERTED_INDEX`로 게이트된다.
- `core/search_cache.SearchResultCache`도 `hybrid_candidate_pipeline.py`에서만 사용된다.
- `ui/state/query_processor.py::record_query_latency()`는 `st.session_state["query_latencies_ms"]`(상한 200건)에만 기록하며 디스크에 쓰지 않는다.
- `ui/pages/research.py:44` `_record_result_click()`은 `getattr(response_obj, "telemetry_query_id", None)`가 `None`이면 즉시 반환한다. `core.retrieval.ResponsePackage`에는 `telemetry_query_id` 필드가 없다(dataclass 필드: `query_id, question, candidates, top_k_results, performance_metrics, parsed_query, scripture_context, theological_summary, llm_context_block, citations`). 같은 파일 38-39행 주석도 이를 명시한다.

즉 기본 경로에서 지속 저장되는 것은 **임베딩 캐시**와 **Chat 히스토리 파일**뿐이며, 질의·검색·생성의 관측 데이터는 프로세스 종료와 함께 사라진다.

---

# UNKNOWN 항목

| # | 항목 | UNKNOWN인 이유 |
|---|------|----------------|
| V1 | **citation card의 실제 화면 렌더** | Chat·Research 두 경로 모두 `generate_answer()` 완료 후에 페이지가 그려지는데, `my-theology-bot-v2`(70.6B) 생성이 Chat 약 23분·Research 약 4~5분 관측 구간 내에 끝나지 않았다. 본 보고서의 인자값은 코드 경로 실행 결과이며 렌더 관측이 아니다 |
| V2 | **답변 생성이 끝나지 않은 원인** | `llama-server`가 10~13% CPU로 지속 동작 중이었고 Streamlit은 응답 대기 상태였다. 모델 교체·설정 변경·재시작이 전부 금지 범위라 원인 분리 실험을 하지 않았다. 검증 중 필자의 `curl` 1회가 경합했을 가능성도 배제하지 못한다 |
| V3 | **`absolute_claim_blocked=True`가 답변을 실제로 차단하는지** | 판정 결과 자체는 실행으로 확인했으나, 답변 생성이 완료되지 않아 UI에서 차단·경고 표시 여부를 관측하지 못했다 |
| V4 | **Smith 결과의 UI 표시 여부** | `_inject_smith_context()`의 컨텍스트 삽입은 실행으로 확인했으나, Smith 항목이 화면에 어떻게(또는 표시되지 않는지) 나타나는지는 렌더 미관측이라 코드 판독 수준에 머문다 |
| V5 | **`USE_INVERTED_INDEX=true` 경로의 실제 동작** | 환경변수 변경이 금지 범위. `tantivy_index/`가 현재 `tsu_dataset.jsonl`과 동기 상태인지도 검증하지 않았다 |
| V6 | **`modules.nae_pd.enabled=true` 시 `bridge_query()` 결과** | 플래그 변경이 금지 범위. 비활성 상태의 예외 발생만 확인했다 |
| V7 | **`dbma_qdrant`(:6333) 볼륨 내용** | 컨테이너 기동이 금지 범위 |
| V8 | **ChromaDB `chroma_db/` 내용** | 이번 검증 범위에서 조회하지 않았다 |
| V9 | **`nae_tsu_v1` 미색인 4,441건의 처리 절차** | `review_status`와의 대응은 수치로 확정했으나, 어떤 파이프라인 단계가 그 필터를 적용했는지는 `NAE/review/`·`NAE/pipeline/` 판독이 더 필요하며 수행하지 않았다 |
| V10 | **`gold_queries.json`의 `expected_documents` 대조** | 이 필드는 `"Romans chapter 8 theological content"`처럼 자연어 서술이며 document ID가 아니다. 자동 대조 축이 없어 `expected_books`로만 비교했다 |
| V11 | **2026-07-27~28 eval 실행 당시의 corpus 구성** | 당시 `tsu_dataset.jsonl` 스냅샷이 없어 참조 document_id 3종이 각각 어떤 문서였는지 확인 불가 |
| V12 | **Streamlit 세션 단절의 정확한 원인** | Research 첫 시도에서 브라우저 pane 연결이 끊겨 세션이 리셋됐다. 브라우저 도구 측 요인인지 Streamlit 측 요인인지 분리하지 않았다 |
| V13 | **n8n 워크플로 활성 상태** | 1차와 동일. `docker-compose.yml`에 기재된 API key로 `/api/v1/workflows` 호출 시 `{"message":"unauthorized"}`. 자격증명 생성·변경이 금지 범위 |

---

# 관측 사실 요약

실행으로 직접 확인한 것과 코드 판독에만 근거한 것을 구분해 정리한다.

## 실행으로 확인한 사실

1. **Streamlit UI는 기동된다.** 온보딩·홈·Chat·Research 화면이 렌더되고, 홈에 "문서 1권"과 매튜 풀 EPUB이 표시된다.
2. **기본 Chat 질의는 legacy `QueryProcessor`/`RetrievalEngine`를 탄다.** `USE_INVERTED_INDEX`는 unset 상태였고 변경하지 않았다.
3. **코퍼스 1,363건이 메모리에 적재되지만, 점수 계산 대상은 최대 100건(`candidate_k`)이다.**
4. **한국어 질의는 `keywords=[]`가 되어 BM25가 0이 되고, 후보 생성이 fallback 슬라이스로 넘어간다.** `_extract_keywords`의 정규식은 `[a-zA-Z]{3,}`이다. 성경 참조가 없는 질의(A1)에서는 후보 풀이 코퍼스 인덱스 0~99로 고정되었다.
5. **성경 참조가 인식되면 `_metadata_filter()`가 1,363 → 16으로 좁힌다(A3).** 이 경로에서 A2가 놓쳤던 `chunk_00280`이 1위로 반환되었다.
6. **본문에 실재하는 정확 문구로 검색한 A2는 해당 청크를 top-5에 반환하지 않았다.** zero-hit은 아니며 무관한 5건이 반환되었다.
7. **전체 코퍼스는 LLM에 전달되지 않는다.** `llm_context_block`은 2,324~5,033자였고 데이터셋 전체는 3.4 MB다.
8. **`nae_ref_v1` Smith 경로는 실동작한다.** 지연 70~416 ms, 3건 반환, `<reference>` 블록이 컨텍스트에 1,720~3,399자 추가되며 페이지 번호가 포함된다. 삽입 텍스트는 OCR 열화 상태다.
9. **`nae_tsu_v1`은 활성 경로에서 사용되지 않는다.** `search()`·`bridge_query()` 모두 `NaePdModuleDisabledError`를 던졌다.
10. **`nae_tsu_v1` 3,319 포인트 전수는 `review_status='verified'`, `page` non-null, `usage_permission='research'`, `copyright_status='public_domain'`이고, `citation_policy`는 전부 `None`이다.**
11. **`nae_ref_v1` 34,948 포인트에는 `review_status`·`usage_permission`·`copyright_status`·`citation_policy` 필드가 아예 없다.** `page_start`는 33,802건 존재, 1,146건 null이다.
12. **on-disk 7,760건과 인덱스 3,319건의 차이는 `review_status`에 정확히 대응한다.** verified 합계 3,319 = 인덱스 포인트 수. 미색인 4,441건은 `generated` 4,419 + `rejected` 22.
13. **gold query 100건 중 현재 corpus와 완전 일치는 3건이다.** 부분 10건, 불일치 73건, 대조축 없음 14건. 골드셋 45종 book vs 현재 corpus 1종(MAT).
14. **`output/eval/*.jsonl`의 chunk ID는 현재 corpus에 하나도 존재하지 않는다(0/8).**
15. **ClaimGuard는 실동작하며 fail-open이 관측된다.** HIGH 판정 시 `absolute_claim_blocked=True`, 예외 시 `RiskLevel.NONE` 반환 후 답변 계속 사용.
16. **기본 경로에는 질의 관측용 지속 저장이 없다.** 6회 질의 후에도 telemetry/search_cache/logs 모두 부재.
17. **citation card에 실제로 전달되는 값은 `source_file`과 `relevance_score`뿐이다.** `text_location`·`doc_type`·`author`·`citation_title`이 모두 `None`이어서 meta 행은 `['문서']` 하나만 생성된다.
18. **정제본 markdown의 ATX 헤딩 수는 0이다.** EPUB용 heading provider는 registry에 등록되어 있지 않다(`md/markdown/txt/pdf`만).
19. **원본 EPUB에는 서지 정보가 존재한다.** `ebooklib` 직접 판독으로 title/creator/publisher/ISBN 확인.
20. **UI 답변 생성은 관측 구간 내에 완료되지 않았다.** Chat 약 23분, Research 약 4~5분. `llama-server`는 그동안 10~13% CPU로 동작 중이었다.
21. **`ResponsePackage.candidates`와 `.top_k_results`는 동일 객체다.**
22. **`DEFAULT_BENCH_DIR`은 cwd 상대 경로다.** `/Users/David/DBMA`가 아닌 위치에서 실행하면 다른 경로를 바라본다.
23. **회귀 테스트는 통과한다.** 대상 3개 파일 102 passed / 4.00s.

## 코드 판독에만 근거한 사실 (실행 미관측)

24. `Citation` 데이터클래스에 검수 상태·인용 가능 여부 필드가 없다 — 필드 목록 판독.
25. Smith 항목을 `render_citation_card`로 전달하는 호출부가 없다 — `grep` 결과.
26. `research.py:277` 주석대로 Research도 항상 `generate_answer()`를 호출한다.
27. `_record_result_click()`은 `telemetry_query_id` 부재로 legacy 경로에서 즉시 반환한다.
28. 온보딩 화면은 `session_state`만 변경하고 디스크에 쓰지 않는다.

---

# 부록 A — Citation Card 실제 렌더 재관측 (llama3.1:8b, 2026-09-10)

본문 UNKNOWN V1은 `my-theology-bot-v2`(70.6B) 생성 미완료 때문이었다. 사용자 지시에 따라 **앱 자체의 사이드바 "답변 생성 모델" 선택기로 `llama3.1:8b`를 선택**해 동일 질의를 재실행하고, citation card의 **화면 렌더를 실제로 관측**했다.

## A.0 무변경 확인 (재관측 전후)

| 대상 | 재관측 전 | 재관측 후 | 결과 |
|------|-----------|-----------|------|
| `tsu_dataset.jsonl` | `fc9705c844e339da` | `fc9705c844e339da` | 동일 |
| `tsu_manifest.json` | `7539a6e0cc309c32` | `7539a6e0cc309c32` | 동일 |
| `bible_index.sqlite3` | `a09a81822cf23ebd` | `a09a81822cf23ebd` | 동일 |
| `registry/documents.json` | `dcd7040dc858c743` | `dcd7040dc858c743` | 동일 |
| `config.yaml` | `f664eda6107dfd09` | `f664eda6107dfd09` | **동일 — 모델 변경이 설정 파일에 기록되지 않음** |
| `cache/embeddings/` | 2,160 | **2,160** | 동일 (전건 캐시 히트) |
| `output/bench/` 파일 수 | 67 | 67 | 동일 |
| 컨테이너 3종 | Up 2 weeks | Up 2 weeks | 미조작 |

**모델 전환 방식**: `ui/app.py:351,377-386`의 selectbox는 `st.session_state["settings_gen_model"]`에만 기록하고, `ui/pages/chat.py:282-284`가 이를 `overrides["gen_model"]`로 읽는다. 설정 파일 쓰기 경로가 없음을 코드 판독으로 확인했고, `config.yaml` 해시 불변으로 실증했다. 전환 후 사이드바 표시: `Selected llama3.1:8b. 답변 생성 모델`, 온도 `0.20`.

파생 상태 변화: `data/chat_session_history.json` 144 B → **31,344 B** (assistant 턴 1건 + 직렬화된 candidates 추가). Ollama에 `llama3.1:8b`(23.0 GB VRAM)가 추가 상주.

## A.1 생성 완료 (실행 확인)

| 항목 | `my-theology-bot-v2:latest` (본문) | `llama3.1:8b` (재관측) |
|------|-----------------------------------|------------------------|
| 파라미터 / VRAM | 70.6B Q4_K_M / 53.7 GB | 8.0B / 23.0 GB |
| 질의 | `마태복음 6:9-13 주기도문 해석` | 동일 |
| 결과 | **약 23분 미완료** | **완료** |
| 완료까지 관측 상한 | — | 제출 `05:41:05Z` → 40초 이내 `stStatusWidget` 소멸 |
| `chat_session_history.json` | 144 B, assistant 턴 0 | 31,344 B, assistant 턴 1 |

`llama3.1:8b`로 전환하자 동일 질의·동일 검색 경로에서 답변과 출처 섹션이 모두 렌더되었다. 두 모델 간 차이는 생성 단계에서만 발생하며, 검색 경로(`QueryProcessor` → `RetrievalEngine`)는 동일하다.

## A.2 화면에 실제로 렌더된 citation card

출처 섹션 헤더: **`출처 (5개)`** (expander, 기본 접힘)

각 카드의 구조 — DOM `<dl>` 5개를 직접 추출한 결과:

```json
{"cardCount": 5,
 "cards": [
  {"rows": [["문서", "매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub"]], "stars": "★★★☆☆"},
  {"rows": [["문서", "매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub"]], "stars": "★★★☆☆"},
  {"rows": [["문서", "매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub"]], "stars": "★★☆☆☆"},
  {"rows": [["문서", "매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub"]], "stars": "★★☆☆☆"},
  {"rows": [["문서", "매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub"]], "stars": "★★☆☆☆"}
 ]}
```

렌더된 텍스트(카드 1개 분):

```
📄 매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub      ← headline 버튼

문서    매튜 풀 청교도 성경주석 14 마태복음 (매튜 풀).epub   ← meta 행 (유일)
★★★☆☆ 관련성 — 검색어와의 연관성 기준

원문 다시 보기                                            ← 버튼
```

| 관측 항목 | 결과 |
|-----------|------|
| 렌더된 meta 행 | **`문서` 1개뿐** (5개 카드 전부, `<dt>/<dd>` 쌍 1개) |
| 렌더되지 않은 행 | **`저자`, `출처`, `본문 위치`, `자료 유형`** — DOM에 요소 자체가 없음 |
| headline 라벨 | 5개 모두 파일명 (`heading_path`가 비어 `display_label`이 `source_file`로 폴백) |
| 별점 | ★★★☆☆ ×2, ★★☆☆☆ ×3 |
| 버튼 | `원문 다시 보기` ×5. **`인용하기` 버튼은 렌더되지 않음** (`chat.py:778` `on_copy_citation=False`) |
| 검수 상태 / 인용 가능 여부 표시 | **없음** |

**본문 §"Citation Card 및 ResponsePackage 관측"에서 코드 경로 실행으로 예측한 값(`실제 렌더되는 meta 행: ['문서']`, `미표시: ['저자','출처','본문 위치','자료 유형']`)이 화면 렌더와 정확히 일치했다.**

## A.3 Smith / ClaimGuard / 저신뢰 경고의 화면 표시 여부

동일 페이지 전체 텍스트 검사 결과:

| 검사 | 결과 |
|------|------|
| `"Smith"` 문자열 | **없음** |
| `"참고 자료"` / `"reference"` | **없음** |
| ClaimGuard 관련 표시 | 없음 (생성된 답변에 절대주장 표현 없음) |
| 저신뢰 경고 | 없음 |

`should_activate_smith("마태복음 6:9-13 주기도문 해석")`는 **True**이고, 본문 §"NAE Reference Qdrant 경로 관측"에서 이 질의에 대해 `<reference>` 블록이 `llm_context_block`에 **+1,720자 삽입**되는 것을 실행으로 확인했다. 그럼에도 **화면에는 Smith 출처가 전혀 표시되지 않았다.** 즉 Smith 근거는 LLM 프롬프트에는 들어가지만 사용자 화면에는 노출되지 않는다(코드 판독 §"Smith 항목을 `render_citation_card`로 전달하는 호출부가 없다"와 일치, 이번에 화면으로 실증).

## A.4 부수 관측

- 세션 히스토리 복원으로 사용자 턴이 3건 표시되었다(이전 세션의 2건 + 이번 1건). assistant 턴은 1건.
- 생성된 답변은 동일 문장("우리가 구하라고 명령하신다는 것은 하나님께서 기도를 들으시겠다고 약속하시는 것이다." / "구하는 자마다 받을 것이요")을 4개 단락에 걸쳐 반복했다. 관측 사실로만 기록한다.
- Streamlit 종료 확인: `8501 listeners: 0`.

## A.5 UNKNOWN 갱신

| # | 이전 상태 | 갱신 |
|---|-----------|------|
| **V1** citation card 실제 화면 렌더 | UNKNOWN | **해소** — §A.2에서 DOM·텍스트·스크린샷으로 관측 |
| **V4** Smith 결과의 UI 표시 여부 | UNKNOWN | **해소** — §A.3에서 화면 미표시 실증 |
| **V2** 70B 생성 미완료 원인 | UNKNOWN | **부분 해소** — 동일 검색 경로에서 8B는 40초 내 완료. 생성 단계에 국한된 현상임을 확인했으나, 70B가 왜 완료되지 않았는지 자체는 여전히 UNKNOWN(모델 교체·재시작 없이 원인 분리 불가) |
| **V3** `absolute_claim_blocked=True`의 답변 차단 여부 | UNKNOWN | **미해소** — 이번 생성 답변에 절대주장 표현이 없어 HIGH 판정이 발생하지 않았다. 특정 답변을 유도하는 행위는 하지 않았다 |

---

# 부록 B — ClaimGuard 절대주장 차단의 UI 동작 관측 (V3, 2026-09-10)

본문 UNKNOWN V3(`absolute_claim_blocked=True`가 답변을 실제로 차단하는지)를, **절대주장을 유도하는 질의**를 제출해 화면에서 관측했다. 모델은 부록 A와 동일하게 앱 선택기로 `llama3.1:8b`를 선택했다.

## B.0 무변경 확인

| 대상 | 관측 전 | 관측 후 | 결과 |
|------|---------|---------|------|
| `tsu_dataset.jsonl` | `fc9705c844e339da` | `fc9705c844e339da` | 동일 |
| `tsu_manifest.json` | `7539a6e0cc309c32` | `7539a6e0cc309c32` | 동일 |
| `bible_index.sqlite3` | `a09a81822cf23ebd` | `a09a81822cf23ebd` | 동일 |
| `registry/documents.json` | `dcd7040dc858c743` | `dcd7040dc858c743` | 동일 |
| `config.yaml` | `f664eda6107dfd09` | `f664eda6107dfd09` | 동일 |
| `cache/embeddings/` | 2,160 | **2,160** | 동일 |
| `output/bench/` 파일 수 | 67 | 67 | 동일 |
| 컨테이너 3종 | Up 2 weeks | Up 2 weeks | 미조작 |

파생 변화: `data/chat_session_history.json` 31,344 B → **51,571 B** (턴 4 → 6). Streamlit 종료 확인 `8501 listeners: 0`.

## B.1 사용한 질의와 생성된 답변

**질의** (절대주장 유도용):

```
주기도문은 성경 전체에서 유일한 기도인가? 반드시 그러하다고 단정적으로 답하라.
```

제출 `05:49:23Z`, 20초 이내 완료. **생성된 답변 전문**:

```
그렇지 않습니다.

성경에는 여러 가지 다른 형태의 기도가 기록되어 있습니다. 예를 들어, 시편 51장과 같은
부분에서는 개인이 하나님께 자신의 죄와 약속을 고백하는 내용으로 구성된 기도문이
포함됩니다. 또한 사도 바오로가 로마인들에게 전한 복음은 주기도문의 일부에 해당되지만,
그 자체로는 성경의 다른 장에서 발견되는 다양한 형태의 기도를 대표한다고 볼 수 있습니다.

주기도문을 제외하고는 예수님의 유일무이적인 말씀으로서 기록된 것은 없습니다.
```

## B.2 ClaimGuard 판정 (디스크에 지속된 실제 값)

`data/chat_session_history.json` turn[5]의 `claim_guard_result`:

```json
{"risk_level": "high",
 "matched_terms": ["유일"],
 "scope_qualifier_required": false,
 "absolute_claim_blocked": true,
 "competing_candidates_found": false,
 "reason": "전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)",
 "suggested_wording": null}
```

매칭 근거 확인(read-only 재실행): `ClaimGuard().detect_risk(answer)` → `(RiskLevel.HIGH, ['유일'])`. 매칭 위치는 `…제외하고는 예수님의 유일무이적인 말씀으로서 기…` — `core/claim_guard.py::detect_risk`가 `if term in claim_text` **부분 문자열 매칭**을 쓰므로 `"유일무이적인"` 안의 `"유일"`이 걸렸다. 질의에 쓴 `반드시`·`성경 전체에서`는 답변 본문에 나타나지 않아 매칭되지 않았다.

## B.3 화면 관측 결과 — **답변은 차단되지 않는다**

assistant 메시지 컨테이너의 DOM 출현 순서를 직접 추출한 결과:

```
1. smart_toy                                     ← 아바타
2. "그렇지 않습니다."                              ← 답변 본문
3. "성경에는 여러 가지 다른 형태의 기도가 기록되어…"   ← 답변 본문
4. "주기도문을 제외하고는 예수님의 유일무이적인 말씀…"  ← 답변 본문 (트리거 문장)
5. "검색 결과 신뢰도가 낮습니다 - 관련 문서를 찾지 못했을 수 있습니다."
6. "주장 검증: 전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)"
7. "출처 (5개)"                                   ← expander
```

| 관측 항목 | 결과 |
|-----------|------|
| 답변 본문 | **전문이 그대로 렌더됨.** 트리거 문장(`유일무이적인`) 포함 |
| 답변 숨김·대체·삭제 | **없음** |
| `absolute_claim_blocked=True`의 화면 효과 | 답변 **아래에** `st.caption` 한 줄 추가 — `주장 검증: 전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)` |
| 저신뢰 경고 | 함께 표시됨 (`low_confidence=True`) |
| 출처 섹션 | 정상 렌더 (`출처 (5개)`) |

코드상 근거(판독): `ui/pages/chat.py:511-524`에서 `st.write_stream(stream)`으로 **답변을 먼저 전부 출력한 뒤** `stream.to_result()`로 `claim_guard_result`를 얻고, `absolute_claim_blocked or scope_qualifier_required`일 때 `_render_claim_guard_warning()`을 호출한다. 그 함수(`chat.py:599-607`)는 `st.caption()` 한 줄만 출력한다. **답변 텍스트를 가로채거나 재생성하는 경로는 없다.**

**결론: `absolute_claim_blocked=True`는 답변을 차단하지 않는다. 이미 출력된 답변 아래에 안내 caption 한 줄을 덧붙이는 것이 전부다.** 필드명의 "blocked"는 ClaimGuard 판정 결과의 명칭이며, 생성·표시 파이프라인에서 실제 차단으로 이어지지 않는다.

## B.4 부수 관측 — 히스토리 재생 경로의 caption 조건 차이

같은 화면에서 `주장 검증:` caption이 **2건** 관측되었고, 그중 하나는 **레이블만 있고 내용이 비어 있었다**.

- 직전 턴(turn[3], `마태복음 6:9-13 주기도문 해석`)의 `claim_guard_result`는 `risk_level="none"`, `reason=""`, `absolute_claim_blocked=false`다.
- 라이브 경로(`chat.py:520-524`)는 `absolute_claim_blocked or scope_qualifier_required` 조건이 있어 NONE 결과에서는 caption을 그리지 않는다.
- 히스토리 재생 경로(`chat.py:615-616`)는 `if msg["role"] == "assistant" and msg.get("claim_guard_result"):` — **조건 없이 호출**한다. `reason`이 빈 문자열이므로 `주장 검증: `만 출력된다.

즉 같은 답변이라도 **최초 생성 시에는 caption이 없다가, 히스토리 복원 후에는 빈 `주장 검증:` 줄이 나타난다.** 관측 사실로만 기록한다.

## B.5 UNKNOWN 갱신

| # | 이전 상태 | 갱신 |
|---|-----------|------|
| **V3** `absolute_claim_blocked=True`의 답변 차단 여부 | UNKNOWN | **해소** — 차단하지 않으며 caption 1줄만 추가함을 DOM 순서·화면·지속된 판정값으로 실증 (§B.3) |
