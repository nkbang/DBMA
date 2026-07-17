# DBMA Changelog

## 목적

이 문서는 DBMA 프로젝트의 중요한 변경 사항을 날짜별로 기록한다.
구조 변경, 파이프라인 변경, 문서 변경, 기능 변경을 간단히 추적하기 위해 사용한다.

---

## 기록 형식

```md
## YYYY-MM-DD
- 변경 사항:
- 대상 파일:
- 이유:
- 결과:
```

---

## 변경 기록

### 2026-06-22

- 변경 사항: CLAUDE.md 운영 규칙 정리
- 대상 파일: `CLAUDE.md`
- 이유: 프로젝트 원칙과 개발 흐름을 한 문서로 통합하기 위해서다.
- 결과: DBMA의 기본 운영 기준이 정리되었다.

### 2026-06-22

- 변경 사항: 문서 체계 분리
- 대상 파일: `docs/TODO.md`, `docs/DBMA_MAP.md`, `docs/ARCHITECTURE.md`, `docs/PIPELINE.md`
- 이유: 구조, 흐름, 상태, 기록을 분리해 보기 쉽게 만들기 위해서다.
- 결과: 문서 목적이 더 분명해졌다.

### 2026-06-22

- 변경 사항: 상태와 로그 문서 추가
- 대상 파일: `docs/STATE.md`, `docs/PROCESS_LOG.md`
- 이유: 진행률과 작업 기록을 따로 관리하기 위해서다.
- 결과: 현재 상태와 이력 추적이 쉬워졌다.

### 2026-06-22

- 변경 사항: 문서 인덱스 추가
- 대상 파일: `docs/INDEX.md`, `docs/README_DOCS.md`
- 이유: 문서 접근성을 높이기 위해서다.
- 결과: 문서 전체를 빠르게 찾을 수 있는 기준이 생겼다.

### 2026-07-14

- 변경 사항: 회귀 테스트에 실제 assert 추가
- 대상 파일: `tests/test_query_enhancements_full_regression.py`
- 이유: 6개 테스트 함수가 전부 `return {dict}`로 끝나고 `assert`가 없어, 실제 결과와 무관하게 항상 PASS로 보고되고 있었다.
- 결과: 숨어있던 실제 버그(성경 책명 4건 오탐지)가 드러났고, 이후 항목에서 수정되었다.

### 2026-07-14

- 변경 사항: 성경 책명 코드 통일 및 한글 신약 태깅 UNKNOWN 버그 수정
- 대상 파일: `core/retrieval.py`, `scripts/repair_tsu_book_metadata.py`, `tests/test_book_alias_resolution.py`
- 이유: Joel/Amos/Obadiah/Zechariah 4권의 코드가 파일마다 제각각(JOL/JOE, AMO, OBD/OBA, ZCH/ZEC)이었고, `KOREAN_TO_ENGLISH`의 26개 항목 중 24개가 영문 성경명 대신 코드를 값으로 저장해 2차 조회가 항상 실패, "마가복음" 등 흔한 한글 파일명이 `confidence=HIGH`로 표시되면서도 `book_id=UNKNOWN`으로 잘못 태깅되고 있었다.
- 결과: `core/retrieval.py`의 66권 코드를 단일 기준으로 삼아 전체 통일. 한글 신약 26권 태깅 정상화 확인.

### 2026-07-14

- 변경 사항: 히브리어/그리스어 원어 감지 및 청킹 보호
- 대상 파일: `core/text_normalizer.py`, `core/chunking_optimizer.py`
- 이유: 한글·영어 산문에 삽입된 히브리어·그리스어 원어 인용이 언어 감지 로직에서 전혀 인식되지 않아 `"other"`로 분류되거나, 긴 원어 인용이 문장 경계 없이 임의 위치에서 절단될 위험이 있었다.
- 결과: 기존 `label`(ko/en/mixed) 판정은 그대로 두고 `has_original_language` 플래그를 병렬로 추가하는 2계층 설계 적용. 히브리어 절 구분 부호(sof pasuq)를 분할 구분자에 추가하고, 단어 경계를 보존하는 슬라이서로 교체. 10개 청크 기준 단어 경계 위반 0건 확인.

### 2026-07-14

- 변경 사항: BGE-M3 시맨틱 벡터 검색 연결 및 임베더 실패 캐싱 버그 수정
- 대상 파일: `core/retrieval.py`, `core/embedder.py`
- 이유: STEP 3(벡터 검색)이 실제로는 TF-IDF 코사인 유사도만 수행하면서 "Vector search (Qdrant or stub)"로 잘못 문서화되어 있었고, `QueryProcessor`가 만들어둔 `EmbeddingCache`가 `retrieve()` 호출에 전달되지 않아 한 번도 쓰이지 않고 있었다. 또한 임베딩 백엔드 로딩 실패가 매 쿼리마다 반복되어(네트워크 재시도 비용 5초 이상) 검색이 사실상 마비되는 문제가 있었다.
- 결과: BGE-M3(Ollama) 우선, 실패 시 항목별 TF-IDF 폴백으로 STEP 3 재구현. `EmbeddingCache` 배선 연결. 임베더 로딩 실패를 프로세스 수명 동안 고정(sticky)시켜 반복 지연 제거(전체 테스트 스위트 80초 → 6초로 복구).

### 2026-07-14

- 변경 사항: DBMA-ECP 자동화가 병행 생성한 커밋(`ce8fd83`)과의 충돌 해소, DBMA-ECP 개발 제외
- 대상 파일: `core/feature_flags.py`(신규), `dbma.py`, `core/text_normalizer.py`, `core/chunking_optimizer.py`, `.gitignore`
- 이유: `DBMA-ECP`가 동일 세션 중 독립적으로 히브리어/그리스어 감지를 다르게 구현하고, `SPRINT2_FEATURES`를 `True`로 전환해 의도적으로 비활성화해 둔 임베딩/벡터DB/RAG shadow 코드를 조용히 재활성화했다.
- 결과: 결정에 따라 `DBMA-ECP`를 향후 개발에서 제외. `SPRINT2_FEATURES`는 `False`로 복원. 히브리어/그리스어 구현은 기존 설계(2계층, label 불변)를 유지. `ce8fd83`의 `.gitignore` 개선분(`output_sav/` 등)은 중복 제거 후 보존.

### 2026-07-14

- 변경 사항: 저장소 위생 정리
- 대상 파일: `.gitignore`, 및 이미 gitignore 대상이었지만 계속 추적되던 `temp/`, `archive/`, `backup/dbma_sprint1.py`, `logs/project_events.jsonl`, 생성된 다이어그램(`*.png`/`*.svg`/`*.dot`)
- 이유: `.gitignore` 규칙 추가 이전에 커밋된 파일들은 규칙이 소급 적용되지 않아 계속 추적되고 있었다. 루트에는 따옴표 없는 `pip install pkg>=X.Y.Z` 실행으로 생긴 `=0.8.0`, `=10.4.0` 잔여 파일도 있었다.
- 결과: 위 파일들을 git 추적에서 해제(로컬 디스크에는 보존). `=0.8.0`/`=10.4.0`은 완전 삭제. `.gitignore`에 `backup/`, `*.svg`, `=*` 패턴 추가로 재발 방지.

### 2026-07-16

- 변경 사항: SPRINT19 (Evidence/Citation 기반 마련) + SPRINT20 (Citation Layer 및 Research Grade 신뢰성 확보)
- 대상 파일: `core/retrieval.py`, `core/generation.py`, `core/config.py`, `core/identity_registry.py`, `scripts/build_tsu_dataset.py`, `scripts/check_environment.py`(신규), `requirements.txt`, `environment.yml`, `README.md`, `.github/instructions/*`, `tests/*`
- 이유: TSU 검색 결과를 사람이 검증 가능한 출처 단위(Citation)로 승격시키고, 그 위에서 발견된 세 가지 governance 결함(레지스트리 경로 혼동, PyYAML 누락 시 config.yaml silent fallback, root logger 강제 ERROR 설정으로 인한 optional-dependency 경고 억제)을 근본 원인부터 제거하기 위해서다.
- 결과:
  - SPRINT19-A~D: TSU `verse_mapping`에 `verse_start`/`verse_end` 추가, Scripture Evidence Resolver v1(`provenance.confidence`), Evidence-aware retrieval ranking, 독립 Evidence Quality Benchmark 신설.
  - SPRINT20-A~C: Citation Architecture Audit → `Citation` 구조화 객체(`core/retrieval.py`) 도입 및 `GenerationResult`까지 pass-through(commit `b05160e`) → 1,500개 chapter gold query 기준 Citation Quality baseline 확정(Completeness Top-10 49.85%, Traceability(title/author) 35.60%).
  - SPRINT20-D~D1: Registry 경로 4곳 분산 및 `core/identity_registry.py` docstring의 stale 경로 암시 발견, docstring 정정(commit `dd3225c`).
  - SPRINT20-E~E3: Registry의 `source_file`/`language`/`source_type`을 TSU→Citation까지 propagate(commit `f520a13`), TSU 재빌드 중 PyYAML 누락 시 `DEFAULT_OUTPUT_DIR`이 stale `"output"`으로 조용히 폴백해 8,079건이 6,307건(빈 본문)으로 손상될 뻔한 사고 발견, `core/config.py`를 PyYAML 누락 시 `RuntimeError`로 hard-fail하도록 수정(commit `3c75078`).
  - SPRINT20-F~F2: 공식 Python 버전(3.11.x) 확정 및 `scripts/check_environment.py` 신설(commit `cd73ad9`), 실제 테스트 baseline이 170이 아니라 **222 passed**였음을 확인(그동안 `.venv`가 Python 3.14로 잘못 구성되어 5개 테스트 파일이 collection 단계에서 조용히 제외되고 있었음), TSU manifest에 `build_commit`/`registry_sha256`/`dataset_sha256`/`config_sha256` provenance 필드 추가(commit `224ebd5`).
  - SPRINT20-G1~G3: 이미 존재하던 `ADR-001-Retrieval-Engine-Authority.md`(accepted) 재발견 — `dbma.py`의 레거시 `query_rag()` 경로는 폐기 대상, `dbma_ui.py`→`ui/app.py`가 공식 진입점임을 확인. README/`.github/instructions/*`를 공식 경로로 정렬(commit `5061329`). `core/config.py`가 import 시점에 root logger를 강제로 `ERROR`로 설정해 `core/extractors.py`의 optional-dependency 경고가 전역 억제되던 문제를 발견 및 제거(commit `1c220f8`).
  - 최종 테스트 baseline: **228 passed**(clean Python 3.11 환경 기준), benchmark 33 passed.

---

## 기록 기준

- 큰 변화만 적는다.
- 사소한 수정은 `docs/PROCESS_LOG.md`에 둔다.
- 날짜는 실제 작업 날짜를 쓴다.
- 결과는 짧게 적는다.
- 변경 이유를 꼭 함께 적는다.

---

## 변경 분류

### 구조 변경

- 폴더 추가
- 파일 역할 변경
- 연결 구조 수정

### 기능 변경

- 파싱 수정
- 청킹 수정
- RAG 수정
- UI 수정

### 문서 변경

- CLAUDE.md 수정
- 아키텍처 갱신
- 파이프라인 갱신
- 상태 문서 갱신

---

## 비고

이 문서는 DBMA의 중요한 전환점을 기록하는 장소다.
세부 작업은 `docs/PROCESS_LOG.md`에, 전체 변화는 이 문서에 남긴다.