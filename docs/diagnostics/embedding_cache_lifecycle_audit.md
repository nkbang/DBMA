# Embedding Cache Lifecycle Audit

상태: Phase A — Audit only. 코드 변경 없음.

## 배경

```text
TSU 데이터셋:  output/bench/tsu_dataset.jsonl — 50,789 TSU (manifest valid)
캐시(복원됨):  cache/embeddings ← cache/embeddings_backup_20260720
               파일 20,976개, 전부 valid JSON, 벡터 차원 1024(BGE-M3)
정합성:        50,789 vs 20,976, 교집합 19,870, 정합률 39.12%
데이터 손상:   없음
```

---

## 1. EmbeddingCache Lifecycle 추적

### 클래스 위치 (문서 드리프트 발견)

```text
실제 정의: core/retrieval.py:570 class EmbeddingCache

core/index_orchestrator.py:10의 주석은 "core/embedder.py::EmbeddingCache가
지연 계산"이라고 서술하나, core/embedder.py에는 EmbeddingCache 클래스가
존재하지 않는다(core/embedder.py는 _OllamaEmbedder/get_embedder/embed만
포함). 이는 코드 이동 후 주석이 갱신되지 않은 문서 드리프트로 판단된다
— 이번 Phase A 범위상 수정하지 않고 발견만 기록한다.
```

### 메서드별 확인 결과

```text
__init__(cache_dir="cache/embeddings")   core/retrieval.py:583
  캐시 디렉터리만 생성(mkdir). 기존 파일을 스캔/로드하지 않는다 —
  "load" 단계가 별도로 존재하지 않는다(생성자는 상태를 갖지 않는
  순수 파일시스템 경로 핸들).

lookup(text, embed_fn)                    core/retrieval.py:593
  SHA256(text)[:16] 파일이 있으면 읽어서 반환(hit). 없으면 embed_fn(text)
  호출 후 insert()로 저장(miss → 즉시 생성). **이것이 사실상의
  "embedding 생성 트리거 지점"이다.**

insert(hash_key, text, vector)            core/retrieval.py:626
  단일 항목을 JSON 파일로 저장. lookup()의 miss 경로에서 호출.

batch_insert(items)                       core/retrieval.py:636
  insert()를 반복 호출하는 래퍼. **호출부가 코드베이스 전체에서
  rebuild() 내부(§ 아래) 외에는 존재하지 않는다.**

validate()                                core/retrieval.py:657
  캐시 디렉터리의 모든 JSON을 스캔해 무결성 확인. **호출부 없음**
  (정의만 존재, dead code — 이번 감사에서 HQ가 제공한 "20,976 files,
  valid JSON 20,976"이라는 사전 검증 수치도 이 함수가 아니라 별도
  외부 검증으로 산출된 것으로 추정).

rebuild(tsu_dataset_path, embed_fn)       core/retrieval.py:685
  TSU JSONL을 순회하며 캐시에 없는 content만 embed_fn으로 계산해
  batch_insert. **호출부 없음 — 코드베이스 전체(worktree/테스트 제외)
  검색 결과 정의부 1곳 외 어디에서도 rebuild(를 호출하지 않는다.**
```

---

## 2. Call Graph — 실제 임베딩 생성이 트리거되는 경로

```text
ui/state/query_processor.py::get_shared_query_processor()
  st.session_state["shared_query_processor"] = QueryProcessor()
  (세션당 1회, TSU manifest의 dataset_sha256이 바뀌면 재생성)
        │
        ▼
core/retrieval.py::QueryProcessor.__init__()          line 1568
  self.engine = RetrievalEngine(tsu_dataset_path=...)  # 전체 TSU 로드
  self.cache  = EmbeddingCache()                       # line 1576
        │
        ▼  (사용자가 검색을 실행할 때마다)
core/retrieval.py::QueryProcessor.process(query)       line 1581
  self.engine.retrieve(parsed_query, embedding_cache=self.cache)
        │
        ▼
core/retrieval.py::RetrievalEngine.retrieve()          line 1101
  STEP 1 metadata filter → STEP 2 BM25 top-K(candidate_k=100, 기본값)
        │
        ▼  (BM25 top-K 후보에 대해서만, 한 쿼리당 최대 candidate_k개)
  embedding_cache.lookup(content, embed_fn)             line 1185
        │
        ├─ hit  → 캐시된 벡터 반환
        └─ miss → embed_fn(content) 호출(Ollama BGE-M3) → insert() 저장

호출 UI 진입점(둘 다 동일 QueryProcessor 경유):
  ui/pages/chat.py:72      processor.process(question, ..., k=5)
  ui/pages/research.py:80  processor.process(query, ..., k=top_k)

그 외 QueryProcessor(engine) 생성부(각각 독립 EmbeddingCache 인스턴스,
단 물리 디렉터리는 cache/embeddings로 동일하게 공유):
  scripts/run_book_level_benchmark.py
  scripts/run_chapter_level_benchmark.py
  scripts/run_evidence_quality_benchmark.py
```

---

## 3. dbma_ui.py / RetrievalEngine이 자동으로 누락된 embedding을 재구축하는가?

```text
결론: 아니오.

- dbma_ui.py, ui/app.py 전체에 "embedding"/"EmbeddingCache" 참조 0건
  — UI 시작 시점에 캐시 상태를 확인하거나 채우는 로직이 없다.
- RetrievalEngine.__init__()(line 1044)은 TSU 코퍼스만 메모리에
  로드한다. EmbeddingCache와 무관하다(QueryProcessor가 별도로 소유).
- 캐시 population은 오직 "쿼리 실행 시 BM25 top-K에 든 후보"에
  대해서만, 그 쿼리 처리 도중에 lazy하게 일어난다(§2). TSU 데이터셋
  전체를 선제적으로(eagerly) 임베딩하는 경로는 어디에도 없다.
- scripts/dbma_doctor.py::check_embedding_backend()(line 172)는
  Ollama 서버 연결/모델 설치 여부만 확인한다 — 캐시 커버리지(몇 %가
  채워져 있는지)는 검사하지 않는다.
```

### 왜 캐시가 20,976건뿐인가 — 명확한 설명

```text
설계 자체가 "전체 사전 색인"이 아니라 "질의 시점 지연 채움(lazy
fill)"이다(core/index_orchestrator.py:9-11 주석이 이 설계 의도를
명시 — 단, 모듈 경로 참조는 부정확함, §1 참고). candidate_k=100이
기본값이므로 한 번의 검색은 최대 100건까지만 캐시에 추가할 수 있다.

20,976건은 "지금까지 실행된 모든 서로 다른 검색 쿼리들이 누적적으로
BM25 top-K 후보로 끌어올린 TSU chunk의 합집합"을 의미한다 — TSU
데이터셋이 50,789건으로 늘어난 뒤에도 이 늘어난 부분을 채워 넣는
메커니즘이 전혀 없으므로, TSU가 늘어날수록 정합률은 자연히 더
낮아지는 구조다. 데이터 손상이 아니라 **애초에 "완전한 캐시"를
보장하는 코드 경로가 존재한 적이 없다.**
```

---

## 4. rebuild()는 Dead Code인가, Reachable한가?

```text
Dead code로 확정한다.

근거: 코드베이스 전체(core/, ui/, scripts/, *.py 루트, .claude/worktrees
제외)에서 "rebuild(" 문자열을 검색한 결과, core/retrieval.py:685의
정의부 자체를 제외하면 호출부가 0건이다. batch_insert()도 rebuild()
내부 호출을 제외하면 다른 호출부가 없다. validate()도 호출부가
0건이다.

즉 EmbeddingCache는 "완전한 캐시를 만드는 기능(rebuild/validate)"을
이미 갖추고 있으나, 그 기능을 실행시켜 줄 진입점(CLI 명령, UI 버튼,
startup hook 등 무엇도)이 만들어진 적이 없다 — 기능 부재가 아니라
연결 부재(missing connection point) 문제다.
```

---

## 5. Missing Connection Points 요약

```text
1. rebuild()/validate()를 호출하는 CLI 스크립트가 없다
   (scripts/에 build_tsu_dataset.py는 있으나 embedding rebuild 스크립트는 없음).
2. dbma_ui.py 시작 시점에 캐시 커버리지를 확인/경고하는 로직이 없다.
3. scripts/dbma_doctor.py는 backend 연결만 확인하고 캐시 완전성은
   확인하지 않는다.
4. TSU rebuild(core/index_orchestrator.py::rebuild_tsu_index /
   reindex_document)가 완료된 뒤 embedding cache를 갱신하라는 신호를
   보내는 hook이 없다 — TSU와 embedding cache 두 계층이 서로의 상태
   변화를 전혀 인지하지 못한다.
```

---

## 6. 권고 — 최소 침습 해법 비교

```text
Option A — Automatic Incremental Rebuild
  RetrievalEngine 또는 QueryProcessor 생성 시점(또는 TSU manifest
  변경 감지 시)마다 자동으로 rebuild()를 호출.
  장점: 사용자 개입 불필요.
  단점: RetrievalEngine.__init__()/QueryProcessor.__init__()은 현재
  동기적이고 가벼운 초기화만 수행하도록 설계되어 있다(§2) — 50,789건
  중 미채워진 항목을 매번(또는 dataset_sha256 변경 시마다) 자동으로
  임베딩하면 Ollama에 대량 요청이 발생해 세션 시작 지연이 매우 커짐.
  "Scope 금지: RetrievalEngine 재설계 금지"와 충돌 위험이 가장 큼.

Option B — Explicit Maintenance Command
  scripts/rebuild_embedding_cache.py(신규) 하나를 추가해
  EmbeddingCache().rebuild(DEFAULT_TSU_DATASET_PATH, embed_fn) 호출을
  노출. dbma_doctor.py 관례(이미 존재하는 진단 스크립트 패턴)와
  일관되며, RetrievalEngine/TSU builder/chunking pipeline 어느 것도
  건드리지 않는다.
  장점: 가장 침습이 적음. 기존 rebuild()/batch_insert()를 그대로
  재사용(신규 로직 없음, 이미 구현되어 있던 것을 "연결"만 함).
  단점: 사용자가 수동으로 실행해야 함(자동화 없음).

Option C — Startup Validation and Repair
  dbma_ui.py 또는 scripts/dbma_doctor.py에 캐시 커버리지 percentage를
  계산해 경고만 표시(자동 복구는 하지 않음).
  장점: 가시성 확보, 침습 없음.
  단점: 그 자체로는 39.12% 문제를 해결하지 않음 — Option B와 함께
  쓰여야 완결됨.

권고: Option B를 최소 안전 해법으로 우선 채택하고, Option C(dbma_doctor.py
에 커버리지 percentage 리포트 추가)를 낮은 리스크의 보완으로 함께
고려. Option A는 이번 scope의 "RetrievalEngine 재설계 금지" 제약과
직접 충돌할 위험이 있어 권고하지 않음.
```

---

## Acceptance Criteria 충족 확인

```text
✅ 캐시가 20,976건뿐인 이유 — §3에서 명확히 설명(lazy query-time
   fill 설계, TSU 증가를 따라잡는 메커니즘 부재, 데이터 손상 아님)
✅ Option A/B/C 권고 — §6에서 비교, Option B 우선 권고
✅ 최소 침습 해법 우선 — Option B는 기존 rebuild()/batch_insert()를
   그대로 재사용, 신규 스크립트 1개 추가만 필요
✅ Phase A 이후 코드 미수정 — core/, ui/ 무접촉, docs/diagnostics/만 신규 생성
```
