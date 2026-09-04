# NAE End-to-End Production Roadmap — 2026-08-15

**작성:** CUE
**성격:** 조사 결과 기록(read-only 조사, 코드 변경 없음). 새 ADR이 아니다.
**핵심 성과:** 새로운 기능을 발견한 게 아니라, **NAE의 Production 경로가 실제로 단절되어 있다는 사실을 코드 근거로 확정**한 것.

---

## 1. 전체 구조

```
NAE Source
   ↓
ADR-021 Registration          (Approved)
   ↓
ADR-023 Automation            (Approved — n8n orchestration)
   ↓
TSU                           (실제 동작 — NAE/pipeline/tsu/builder.py)
   ↓
BGE-M3                        (실제 동작 — NAE/pipeline/embed/client.py, ollama 실호출)
   ↓
NAE Qdrant :7333              (실제 인덱싱 — NAE/pipeline/index/)
   ║
   ║  ← PRODUCTION BRIDGE MISSING
   ║
RetrievalEngine :6333         (실제 사용 — core/retrieval.py, ui/pages/research.py가 직접 import)
   ↓
Citation / Provenance         (실제 사용 — core/retrieval.py::CitationBuilder)
   ↓
Benchmark / Regression        (실행 가능 — scripts/run_rag_eval.py, ADR-010 Phase 2)
```

`NAE Qdrant :7333`과 `RetrievalEngine :6333`은 **물리적으로 다른 Qdrant 인스턴스**(포트 자체가 다름)이며, 코드 레벨에서 명시적으로 분리되어 있다:

- `NAE/pipeline/index/config.py` 주석: *"never wired into core/retrieval.py::RetrievalEngine's production query path"*
- `docs/architecture/ADR-013-NAE-Vector-Store.md`: *"이 제약은 core/retrieval.py::RetrievalEngine의 production 검색 경로를 대상으로 한다 ... RetrievalEngine의 검색 경로에는 연결하지 않는다"*

즉 ADR-021/022/023으로 아무리 신규 원문을 등록·TSU화·임베딩·인덱싱해도, **그 결과는 실제 사용자 검색 결과에 절대 반영되지 않는다.** RetrievalEngine은 완전히 별도 계보인 `tsu_dataset.jsonl`(레거시 `scripts/build_tsu_dataset.py`가 생성, in-memory 로드)을 쓴다.

## 2. 현재 상태 고정

| 영역 | 현재 상태 | 판단 |
|---|---|---|
| Source Registration | 구현/승인(ADR-021) | ✅ |
| Automation | ADR-023 Approved | ✅ |
| TSU | 실제 동작 | ✅ |
| BGE-M3 | 실제 동작 | ✅ |
| NAE Qdrant | 실제 인덱싱 | ✅ |
| RetrievalEngine | 실제 사용 | ✅ |
| Citation | 실제 사용 | ✅ |
| Benchmark | 실행 가능 | ✅ |
| **NAE → Production Retrieval 연결** | **없음** | 🔴 **Production Blocker** |

"미구현" 단계는 하나도 없다. 유일한 Production Blocker는 ①~③(NAE 신규 파이프라인)과 ④~⑥(실제 검색 엔진) 사이의 연결 부재다.

## 3. 중요한 Architecture 원칙 — 지금 결정하지 않는 것

**NAE Qdrant를 RetrievalEngine에 바로 연결한다고 지금 결정하지 않는다.**

ADR-013 및 기존 Core Engine governance(ADR-001/003)가 이미 존재하므로, Bridge를 설계하기 전에 **RetrievalEngine의 실제 extension point와 ADR-001/003/013을 먼저 재조사**해야 한다. 가능한 선택지 예시(전부 미결정):

- **A.** RetrievalEngine이 NAE Qdrant를 직접 조회
- **B.** NAE Retrieval Adapter를 별도 Domain Plugin으로 구성
- **C.** NAE index를 기존 RetrievalEngine의 허용된 backend abstraction에 연결
- **D.** 기존 `tsu_dataset` 계보를 폐기/통합

**A/B/C/D 중 무엇이 맞는지는 지금 이 문서에서 결정하지 않는다.** ADR-024(가칭) 설계 전에 별도의 read-only 조사 단계가 선행되어야 한다:

1. `core/retrieval.py::RetrievalEngine`의 실제 extension point(플러그 가능한 backend 인터페이스가 있는지, 없는지)
2. `docs/architecture/ADR-001*`(Retrieval Engine Authority)이 이런 종류의 확장을 어떻게 다루도록 이미 정해뒀는지
3. `ADR-003`(Legacy Vector Store Strategy)과 `ADR-013`(NAE Vector Store)이 서로 어떤 경계를 이미 그어놨는지
4. `tsu_dataset.jsonl` 계보(레거시)와 NAE TSU 계보의 스키마 차이가 얼마나 큰지(단순 병합 가능한지, 구조적으로 다른지)

이 조사가 끝난 뒤에야 ADR-024를 설계한다 — 지금 곧바로 설계에 들어가면 근거 없는 반복 논의가 재발할 위험이 있다.

## 4. 다음 단계

**지금 할 일**: 위 §3의 1~4번 read-only 조사. 새 ADR 작성은 그 다음.

**하지 않을 일**: A/B/C/D 중 하나를 지금 선택, RetrievalEngine이나 NAE 파이프라인 코드에 손대기, ADR-024 설계 착수.

---

## 5. 선행 조사 4항목 결과 (2026-08-15, read-only 조사 완료)

**주의**: 아래는 전부 "다음 설계 논의를 위한 참고 관찰"이며, 이 문서는 A/B/C/D 중 어느 것도 결정하지 않는다.

### 5.1 RetrievalEngine의 실제 extension point

- `core/retrieval.py::RetrievalEngine.__init__`(1180행)은 `tsu_dataset_path`를 생성자 파라미터로 받지만, 이는 "TSU JSONL 파일 경로 하나"로 고정된 형태다 — 교체 가능한 backend 인터페이스가 아니다.
- `_load_corpus()`(1225행)가 그 파일을 전부 `self.tsus: list[dict]`로 in-memory 적재하고, BM25/TF-IDF/theological scoring 전부 이 리스트를 직접 참조. `Protocol`/`ABC`/`abstractmethod` 검색 결과 **0건** — 플러그 가능한 backend 추상화가 코드에 전혀 존재하지 않는다.
- `self.qdrant_url` 파라미터는 저장만 되고 파일 전체에서 이후 한 번도 참조 안 됨(`QdrantClient` import 자체가 없음). `EmbeddingCache`도 Qdrant와 무관한 순수 로컬 파일 캐시.
- `class QueryProcessor.__init__`이 `engine: Optional[RetrievalEngine] = None`을 받는 DI 지점은 있음 — "엔진 객체 전체 교체"는 가능하나 "엔진 내부 데이터소스만 교체"는 구조상 불가능.

**관찰**: NAE Qdrant를 연결하려면 (a) `RetrievalEngine` 내부를 침습적으로 수정하거나 (b) `QueryProcessor`가 주입받는 `engine` 자리에 새 클래스를 끼워 넣거나, 둘 중 하나만 가능. "backend만 갈아끼우는" 제3의 경로는 없음.

### 5.2 ADR-001(Retrieval Engine Authority)

- Status: Accepted(최신 revision: SPRINT20-H-3 Correction, 2026-07-16).
- Decision 원문: "`core/retrieval.py::RetrievalEngine`을 DBMA의 유일한 Retrieval Engine Authority로 지정한다... 새로운 병행 검색 경로를 만들지 않는다."
- Correction 섹션: "RetrievalEngine does not currently query Qdrant"를 명시적으로 정정, "향후 vector store 재도입 여부는 별도 ADR(ADR-003)에서 다룬다"고 **판단을 위임**.

**관찰**: ADR-001 자체는 내부 확장이냐 새 backend 연결이냐를 규정하지 않고 ADR-003/013으로 넘겼다.

### 5.3 ADR-003/013이 그어놓은 경계

- ADR-003: "No production dependency may be added to Chroma/Qdrant without new ADR approval... 그런 변경이 필요하다고 판단되면 이 ADR을 개정하는 신규 ADR을 먼저 작성한다."
- ADR-013 Scope: "`core/retrieval.py::RetrievalEngine`의 검색 경로에는 연결하지 않는다 — ADR-003의 migration policy를 그대로 준수한다."
- ADR-013 Consequences: **"향후 NAE corpus를 RetrievalEngine의 production 경로에 통합하려면(예: Theology RAG Alpha 단계) 이 ADR을 개정하는 신규 ADR이 필요하다."**

**관찰**: 완전 금지가 아니라 **조건부 개방**(신규 ADR 승인 시 가능)이며, ADR-013 스스로 그 신규 ADR의 필요성을 이미 예고해뒀다. 지금 검토 중인 "ADR-024(가칭)"이 정확히 이 조항이 요구하는 문서다.

### 5.4 tsu_dataset.jsonl(레거시) vs NAE TSU 스키마

- 레거시(`core/tsu_builder.py::build_tsu_records`): `tsu_id`, `document_id`, `chunk_id`, `content`(원문 청크 그대로), `verse_mapping`, `themes`, `title`, `author`, `provenance`, `content_quality` 등.
- NAE(`NAE/pipeline/tsu/builder.py`, 실제 `tsu.json` 확인): `id`, `book`, `author`, `identifier`, `source_text`(원문 인용), `claim`(LLM 추출·재서술된 신학적 주장), `doctrine`, `scriptures`(list), `citations`, `confidence`, `review_status`.
- 겹치는 필드명은 `author`/`page` 정도. **개념 자체가 다름**: 레거시는 "원문을 그대로 청킹해 검색 대상으로 보존하는 chunk-of-text 모델", NAE는 "LLM이 원문에서 주장을 추출·재서술하고 신뢰도/검토상태를 부여하는 claim-extraction 모델".

**관찰**: 단순 필드 매핑으로는 변환 불가능해 보임 — RetrievalEngine의 BM25/TF-IDF는 `content`(원문)를 전제로 설계돼 있어, NAE의 `claim`(재서술)과 `source_text`(원문) 중 무엇을 그 자리에 넣을지부터 개념적 결정이 필요하다.

### 5.5 종합 (참고 관찰, 결론 아님)

- **A(직접 조회)**: extension point 부재(§5.1) + ADR-013 명시적 금지(§5.3, 신규 ADR 전까지)로 **현재는 막혀 있음**
- **B/C(Adapter/backend 연결)**: `QueryProcessor`의 `engine` DI 지점이 유일하게 열린 확장 경로(§5.1). ADR-013이 "신규 ADR로 통합 가능"이라 이미 길을 열어둠(§5.3)
- **D(계보 통합/폐기)**: 두 스키마가 근본적으로 다른 데이터 모델(§5.4)이라 초기 판단상 난이도 높음 — 배제도 지지도 이름

**다음 논의(ADR-024 설계 시 입력으로 사용, 지금 결정하지 않음).**

---

## 6. Bridge 설계 사실 확보 — FACT → CONSTRAINT → OPTIONS → RECOMMENDATION

**지시**: "NAE → RetrievalEngine Production Bridge가 현재 유일한 blocker임을 확인했으므로, ADR-024를 바로 작성하지 말고 먼저 기존 RetrievalEngine의 extension point, backend abstraction, ADR-001/003/013의 제약, NAE Qdrant의 schema/collection compatibility를 조사하여 Bridge 설계에 필요한 사실을 확보하라." — 이 절이 그 결과물이다. **ADR-024는 아직 작성하지 않는다.**

### FACT (조사로 확인된 사실)

| # | Fact | 근거 |
|---|---|---|
| F1 | `RetrievalEngine`에 플러그 가능한 backend 추상화가 없다(`Protocol`/`ABC`/`abstractmethod` 0건) | `core/retrieval.py` 전체 검색 |
| F2 | 유일한 DI 지점은 `QueryProcessor.__init__(engine: Optional[RetrievalEngine])` — 엔진 객체 전체 교체만 가능 | `core/retrieval.py:1930` |
| F3 | `RetrievalEngine`은 현재 Qdrant를 전혀 쿼리하지 않는다(`qdrant_url` 저장만 되고 미사용, `QdrantClient` import 없음) | `core/retrieval.py`, ADR-001 Correction 섹션 |
| F4 | `RetrievalEngine`은 in-memory TF-IDF cosine을 기본으로 쓰고, `EmbeddingCache`가 공급되면 **BGE-M3 semantic 경로도 이미 존재**(`core.embedder` 경유) | `core/retrieval.py:1481-1524` |
| F5 | `core.embedder`와 `NAE.pipeline.embed.client` 둘 다 **`bge-m3:latest`, 1024차원**으로 완전히 동일한 모델 사용(구현/캐시는 별도) | `core/embedder.py:7,162`, `NAE/pipeline/embed/config.py` |
| F6 | ADR-001: RetrievalEngine이 유일 권위, "새 병행 검색 경로 생성 금지"만 규정, backend 확장 여부는 ADR-003으로 위임 | ADR-001 Decision/Correction |
| F7 | ADR-003: "No production dependency may be added to Chroma/Qdrant without new ADR approval" — legacy Qdrant(:6333) 대상 | ADR-003 Migration Policy |
| F8 | ADR-013: NAE Qdrant(:7333, `nae_tsu_v1`)는 legacy와 컨테이너/포트/볼륨/컬렉션명 전부 물리적으로 분리, "RetrievalEngine 검색 경로에 연결하지 않는다"고 명시하되 **"통합하려면 이 ADR을 개정하는 신규 ADR이 필요하다"고 스스로 예고** | ADR-013 Scope/Consequences |
| F9 | 레거시 `tsu_dataset.jsonl`(`content`=원문 청크 그대로)과 NAE TSU(`source_text`+`claim`=LLM 추출·재서술)는 **근본적으로 다른 데이터 모델**(chunk-of-text vs claim-extraction) | `core/tsu_builder.py`, `NAE/pipeline/tsu/builder.py`, 실제 `tsu.json` |
| F10 | NAE Qdrant point는 `qdrant_store.py::build_point()`가 provenance/citation/confidence까지 payload로 실음(레거시보다 풍부한 메타데이터) | `NAE/pipeline/index/qdrant_store.py` |

### CONSTRAINT (F로부터 도출되는 제약)

| # | Constraint | 근거 |
|---|---|---|
| C1 | NAE Qdrant를 `RetrievalEngine`이 **직접 쿼리하도록 내부 코드를 수정하는 것은 현재 ADR 위반**이다(F8) — 신규 ADR 승인 없이는 금지 | F7, F8 |
| C2 | "backend만 갈아끼우는" 설계는 코드 구조상 **존재하지 않는 옵션**이다(F1) — 있는 척 설계하면 안 된다 | F1 |
| C3 | NAE TSU의 `claim`(재서술)을 레거시 `content` 자리에 그대로 넣으면 BM25/TF-IDF 스코어링의 전제(원문 그대로의 어휘 매칭)가 깨질 수 있다 — `source_text`를 쓸지 `claim`을 쓸지는 검색 품질에 직접 영향을 주는 설계 결정이지 기계적 변환 문제가 아니다 | F9 |
| C4 | 임베딩 모델 자체(BGE-M3, 1024차원)는 이미 동일하므로, **벡터 호환성 자체는 문제가 아니다** — 문제는 스키마(무엇을 임베딩하는가)와 저장소 분리이지 모델 불일치가 아니다 | F4, F5 |
| C5 | ADR-001의 "새 병행 검색 경로 생성 금지" 원칙상, Bridge는 `RetrievalEngine`을 **대체**하거나 **우회**하는 두 번째 검색 엔진을 만드는 형태가 되어서는 안 된다 — `QueryProcessor` 아래 단일 권위 구조를 유지해야 한다 | F6 |

### OPTIONS (제약 안에서 남는 선택지, 결정 아님)

| 옵션 | 설명 | C1(직접쿼리 금지) | C2(backend추상화 없음) | C5(단일권위 유지) |
|---|---|---|---|---|
| A. RetrievalEngine이 NAE Qdrant 직접 조회 | `RetrievalEngine` 내부 코드 침습 수정 | ❌ 위반(신규 ADR 없이는) | 해당 없음(추상화 우회하고 직접 수정) | ⚠️(단일 클래스 비대화) |
| B. NAE Retrieval Adapter를 별도 클래스로, `QueryProcessor.engine` 자리에 주입 | F2의 기존 DI 지점 활용 | ✅ RetrievalEngine 자체는 무수정 | ✅ 기존 DI 지점 그대로 사용 | ✅ QueryProcessor가 여전히 단일 진입점 |
| C. RetrievalEngine에 backend abstraction을 새로 도입한 뒤 연결 | 신규 추상화 계층 설계 필요 | ⚠️(RetrievalEngine 수정 필요, 규모에 따라 ADR 필요) | 추상화를 새로 만드는 것 자체가 이 옵션의 내용 | ✅ |
| D. tsu_dataset 계보를 NAE TSU로 통합/폐기 | 레거시 전체를 NAE 스키마로 전환 | 해당 없음(별도 트랙) | 해당 없음 | ✅(장기적으로 단일화) |

### RECOMMENDATION (참고 권고 — 최종 결정 아님, ADR-024에서 확정)

- B가 F2(기존 DI 지점)·F7/F8(ADR 제약)·C5(단일 권위 원칙)를 가장 적게 건드리면서 시작할 수 있는 옵션으로 보인다 — `RetrievalEngine` 자체를 무수정으로 둔 채 별도 Adapter 클래스를 `QueryProcessor.engine`에 주입하는 방식은 기존 코드 위험이 가장 낮다.
- C는 장기적으로 더 깔끔하지만 `RetrievalEngine` 내부 수정이 필요해 초기 리스크가 B보다 크다 — B로 시작해 검증 후 C로 리팩토링하는 단계적 접근도 고려 가능.
- A는 F7/F8이 명시적으로 금지하므로 **신규 ADR 승인 없이는 배제**.
- D는 C3(스키마 근본 차이)로 인해 별도의 큰 트랙이며, Bridge 자체와는 독립적으로 다뤄야 할 것으로 보인다.
- 실제 채택 여부와 세부 설계는 **ADR-024에서 CUE가 다시 정식으로 검토·확정**한다. 이 절은 그 논의의 입력일 뿐이다.

