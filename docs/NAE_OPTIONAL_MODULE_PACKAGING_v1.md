# DBMA Distribution — NAE Optional Module Packaging v1

작성일: 2026-08-11
상태: 구현 완료
ADR 신규 작성 여부: **없음** — 기존 ADR-001(RetrievalEngine 유일 정본),
ADR-013(NAE Vector Store 분리), ADR-020(NAE Incremental Ingestion)과
충돌 없음(diff로 확인, `docs/architecture/` 무수정). 이 문서는 execution
packaging 세부사항이며, 새 architecture decision이 아니다.

## 네이밍 — 내부 코드 식별자 vs 제품 브랜드

이 문서 및 관련 코드에서 **"NAE" 또는 "nae_pd"는 Dagg/Hiscox 등 공개
신학 TSU corpus 모듈을 가리키는 내부 코드 식별자**다. 제품 브랜드
"내서재"(영문 표기 시에도 "NAE"로 종종 불림, `scripts/install_nae_beta.command`
가 설치하는 DBMA 앱 전체)와는 **다른 대상**이며, 이 둘을 혼동하지 않는다.
브랜드명 자체는 변경하지 않는다(2026-07-28 Brand Freeze 결정 유지).

## 이미 성립해 있던 사실

`core/`, `ui/`는 이번 작업 이전부터 `NAE` 코드를 전혀 import하지 않았다
(grep으로 확인, 0건). 이번 작업은 이 상태를 **공식 module boundary로
명문화**한 것이지, 새로 분리한 것이 아니다.

## 구성 요소

```
config.yaml
  └── modules.nae_pd.enabled: false (기본값)

core/module_registry.py   — generic registry, NAE 코드를 import하지 않음
NAE/module.py              — NAE 자체 activation 안전성 self-check(READ-ONLY)
NAE/retrieval_adapter.py   — 명시적 opt-in adapter, RetrievalEngine 미수정
scripts/dbma_module.py     — list / status / enable / disable CLI
```

## 원칙

1. **NAE가 없어도 DBMA는 정상 동작한다**: `core/module_registry.py`는
   `config.yaml`의 `modules:` 섹션이 없어도 빈 dict를 반환한다 — 예외
   없음.
2. **`enable`은 embedding/indexing을 자동 시작하지 않는다**:
   `NAE/module.py::activate()`는 corpus/manifest 존재 여부만 확인한다
   (`embedding_calls_made: 0`, `indexing_calls_made: 0` — 실측 확인,
   §Production Safety Test 참고).
3. **corpus/index 물리적 분리**: `NAE/corpus/tsu/` ≠ `data/RAW`,
   `nae_tsu_v1`(포트 7333) ≠ `dbma_sermon`/`dbma_chunks`(포트 6333) —
   기존 ADR-013 분리를 재확인.
4. **RetrievalEngine 무수정**: `core/retrieval.py`는 이번 작업으로 단
   한 줄도 바뀌지 않았다(diff 확인). NAE 검색은 `NAE/retrieval_adapter.py`
   를 통해서만, 그리고 `nae_pd` module이 enabled일 때만 가능하다.
5. **config.yaml 주석 보존**: `set_enabled()`는 `yaml.safe_dump()`로
   전체 파일을 재작성하지 않고, `enabled:` 한 줄만 정규식으로 patch한다
   — 최초 구현에서 전체 재작성이 기존 주석 섹션을 전부 삭제하는 회귀를
   일으킨 것을 발견 즉시 수정했다(구현 중 자체 발견, Production
   config.yaml에는 반영되지 않고 즉시 `git checkout`으로 원복 후 재구현).

## Corpus/Module/Schema/Embedding/Index 버전 구분 (§10)

```
NAE Module version    : NAE/module.py::MODULE_VERSION ("1.0.0")
NAE Corpus version    : Production Manifest의 production_generation (현재 1)
NAE Schema version     : TSU 레코드의 tsu_schema_version (현재 "1")
Embedding Model version: config.yaml modules.nae_pd 미기록, NAE/pipeline/embed/config.py::DEFAULT_EMBED_MODEL="bge-m3:latest"(불변)
Index version           : Qdrant collection명 자체가 schema_version 기반(nae_tsu_v1) — ADR-013 정책
```

## Migration / Upgrade 시나리오 대응 (§12)

| 시나리오 | 대응 |
|---|---|
| A. 새 NAE corpus 추가 | `scripts/nae_incremental_ingest.py --apply`(ADR-020, 이번 작업 무관) |
| B. 새 corpus version | Production Manifest `production_generation` 증가 |
| C. BGE-M3 → 다른 embedding model | `NAE/pipeline/ingest/embedding.py`의 model-aware SKIP 로직이 자동으로 재embedding 유도(ADR-020) |
| D. NAE module 제거 | `enabled: false`(기본값) — DBMA Core는 애초에 NAE를 import하지 않으므로 코드 제거 없이도 정상 작동 |
| E. NAE module 재활성화 | 기존 Qdrant 1,281 vectors/embedding cache 재사용 — `activate()`는 재embedding을 트리거하지 않음(실측 확인) |

## Production Safety Test 실측 (READ-ONLY, 전부 실제 명령/실제 출력)

```
enable 실행 전: Dagg hash=10fc58ef2f80902c, Hiscox hash=1da2d7dd75d5235f,
                exception_queue hash=1e940d4ae63ec785, Qdrant points=1281,
                embedding cache files=1281
enable 실행:    config.yaml diff는 15줄 추가만(주석 100% 보존),
                activation_safe=true, embedding_calls_made=0, indexing_calls_made=0
disable 실행:   enabled: false로 복원(기본값)
enable 실행 후: 위 5개 값 전부 동일(hash diff 0, Qdrant 1281, cache 1281)
```

## 테스트 (19개, 전부 격리 fixture — 실제 config.yaml enabled 상태를 변경하는
테스트 없음)

Test A(disabled), B(enabled), C(corpus isolation), D(index isolation),
E(optional removal), F(incremental boundary), G(no automatic embedding),
H(manifest validation), I(existing state reusable), J(core regression 스모크)
— `tests/test_dbma_nae_module_packaging.py`, 19/19 PASS.
