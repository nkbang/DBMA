# NAE Pilot 001 — Embedding Execution Report 001

**작성일:** 2026-08-09
**성격:** 사용자 승인에 따른 실제 Embedding + Qdrant upsert 실행.
**이 프로젝트 최초의 실제 Vector Index 실행.**
**Authority:** `docs/NAE_VECTOR_INDEX_PREFLIGHT_002.md`(BLOCKER 0) + 사용자 명시적 승인("승인")
**Git Commit/Push:** 미수행.

---

## 1. 실행 내용

```
$ indexer.index_all(dry_run=False)
{'processed': 6, 'indexed': 10,
 'identifiers': [{'Hiscox_Standard_Manual': 5 indexed}, {'Dagg_Church_Order': 5 indexed}, ...]}
```

verified 10건(TSU-0000025/0000033/0000199/0000330/0000713/0003524/
0003525/0003647/0003661/0003893) 전부에 대해 `bge-m3:latest`로 실제
Embedding을 계산하고 `nae_qdrant`(nae_tsu_v1 컬렉션)에 upsert했다.

---

## 2. 검증 결과

### 2.1 Qdrant 실측

```
points_count: 10(정확히 일치)
```

실제 point 1건(TSU-0000025) 조회 결과, payload에 `claim`/`source_text`/
`doctrine`/`review_status=verified`/`source_id`/`author_id`/`work_id`/
`edition_id` 등 Metadata Schema 1.1.0 필드 전부 정상 포함.

### 2.2 Embedding 캐시

```
NAE/corpus/embeddings/cache/: 10개 파일(정확히 일치)
```

### 2.3 index_report.json

```
Dagg_Church_Order:      records_total_raw=3377, gate_pass=5, gate_block=3372, indexed=5, embedding_errors=0
Hiscox_Standard_Manual: records_total_raw=740,  gate_pass=5, gate_block=735,  indexed=5, embedding_errors=0
```

### 2.4 Production TSU 파일 무변경

```
$ Dagg/Hiscox tsu.json checksum: Embedding 실행 전후 동일
```

`index_identifier()`는 `index_report.json`만 별도로 쓰며 `tsu.json`
자체는 건드리지 않음(코드 구조상 원천적으로 분리) — 재확인됨.

### 2.5 Architecture Boundary

```
$ git diff --stat core/retrieval.py core/tsu_builder.py
(0줄 변경)
```

`nae_qdrant`(7333/7334)와 legacy `qdrant`(6333) 물리적 분리 유지,
`core/retrieval.py::RetrievalEngine`은 이번 Embedding과 무관하게
무수정.

---

## 3. Regression

```
$ pytest(관련 스위트) 206 passed
$ pytest -q --ignore=output(전체) 2044 passed, 2 failed
```

2건은 기존 무관 baseline(`tests/test_nae_embed.py`, 불변). **신규
regression 0건**(테스트 1건 수정 — `test_no_index_report_written_to_production_by_dry_run`이
"index_report.json이 절대 존재하면 안 된다"는 낡은 전제였는데, 이제
실제 인덱싱이 정당하게 수행되어 report가 존재하는 게 정상 상태이므로
"dry_run이 기존 report를 변경하지 않는다"는 원래 취지에 맞게 재작성함
— 회귀 아님).

### Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 완료 보고

```
STATUS: PASS

EMBEDDING EXECUTED: YES(10건, bge-m3:latest)
QDRANT UPSERT EXECUTED: YES(10건, nae_tsu_v1 컬렉션)

QDRANT POINTS_COUNT: 10(검증됨)
EMBEDDING CACHE: 10개(검증됨)
EMBEDDING ERRORS: 0

PRODUCTION TSU MUTATION: 0(tsu.json 무변경, index_report.json만 신규 생성)

REGRESSION: 2044 passed / 2 failed(기존 무관 baseline), 신규 regression 0건

DRIFT: 0

ARCHITECTURE BOUNDARY: PASS(core/retrieval.py, core/tsu_builder.py 무수정, NAE/DBMA legacy 물리적 분리 유지)

FILES MODIFIED:
tests/test_indexer_review_gate_wiring.py(낡은 테스트 전제 1건 재작성)

GIT: NOT PERFORMED

NEXT STEP:
Pilot 001 End-to-End 사이클(Migration -> Payload Contract -> Human Review
Gate -> Promotion -> Remediation -> Embedding -> Qdrant) 완료. 다음은
Retrieval Benchmark(Gold Query Set 신규 작성 필요, 기존 placeholder
데이터셋과 TSU ID 네임스페이스 불일치) 또는 Pilot 범위를 4,107건
generated TSU로 확장하는 Human Review 계속 진행 중 선택 필요 — 별도
작업 명령 대기.
```
