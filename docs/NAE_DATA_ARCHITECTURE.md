# NAE Data Architecture

작성일: 2026-07-31
조사 방식: 읽기 전용 (`config.yaml`, `core/config.py`, `.gitignore`, 실제 디렉토리 트리, `scripts/build_tsu_dataset.py` 코드) 열람. 파일 이동/삭제 없음.

## 조사 대상 최상위 구조

```
resources/   — git 추적됨 (.gitignore에 없음)
data/        — git 미추적 (.gitignore 2행)
output/      — git 미추적 (.gitignore 85행)
archive/     — git 미추적 (.gitignore 38행), 레거시 코드/RAW 격리 보관소 (ADR-001/003)
```

**핵심 구분**: `resources/`는 유일하게 git 추적 대상 — 작고 버전 관리가 필요한 스키마/설정/사전(hunspell) 등을 담는 곳. `data/`/`output/`/`archive/`는 전부 로컬 전용, 대용량·재생성 가능 데이터를 담는 곳. 이번 조사에서 만든 `resources/theological_sources/`(스키마만)와 `data/nae/`(실 데이터용)의 역할 구분이 이 원칙과 우연히도 이미 일치함을 확인.

## 1. RAW 원문 위치

| 위치 | 용도 | git 추적 | 상태 |
|---|---|---|---|
| `data/RAW/` | **DBMA 전체의 공식 RAW 디렉토리** (`config.yaml: directories.raw_dir`, `core/config.py::DEFAULT_RAW_DIR`) — `core/processing.py`가 참조하는 유일한 정본 | 미추적 | 운영 중, 실 데이터 존재 |
| `data/nae/sources/{baptist,theology,commentary,public_domain}/` | NAE 전용 inbox — `scripts/ingest_nae_source.py`의 `DEFAULT_NAE_INBOX_DIR` 기본값. `data/RAW/`와 의도적으로 분리(Logos ingest 선례와 동일 원칙: 별도 inbox로 문서 네임스페이스 충돌 방지) | 미추적 | STEP1에서 생성, 현재 비어 있음 |
| `resources/theological_sources/{denom}/{genre}/source_manifest.yaml` | RAW 원문의 **메타데이터만**(스키마: `source_manifest.schema.yaml`) — 원문 텍스트 자체는 담지 않음 | **추적됨** | 이번 세션에서 생성, 스키마만 존재·데이터 없음 |

**결론**: 실제 RAW 텍스트 파일은 `data/nae/sources/`에 두고, `resources/theological_sources/`에는 그 파일을 가리키는 manifest(메타데이터)만 둔다 — 두 위치는 경쟁 관계가 아니라 상호보완 관계로 이미 설계되어 있었음(단, 이 관계가 명시적으로 문서화된 적은 없었음 — 이번 문서가 최초).

## 2. Processing 위치

| 위치 | 용도 | git 추적 |
|---|---|---|
| `data/제련완성본/` (`config.yaml: directories.output_dir`) | **DBMA 공식 처리 결과물 디렉토리** — `registry/documents.json`(identity registry), `cache/embeddings/`, `research/`, `_logs/` 등. `core/processing.py`의 기본 output | 미추적 |
| `data/nae/processed/` | NAE 전용 output — `scripts/ingest_nae_source.py`의 `DEFAULT_NAE_OUTPUT_DIR`. 별도 registry(`data/nae/processed/registry/documents.json`)를 가짐 — 메인 코퍼스 registry와 물리적으로 분리(Logos 선례와 동일 원칙) | 미추적 |

**결론**: NAE는 메인 코퍼스와 별도의 registry 파일을 가지므로 `data/제련완성본/registry/documents.json`과 충돌하지 않음 — 이는 의도된 설계(NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md에서 이미 확인된 원칙의 재확인).

## 3. TSU Dataset 위치

| 위치 | 용도 |
|---|---|
| `output/bench/tsu_dataset.jsonl` (`config.yaml: directories.bench_dir`, `core/config.py::DEFAULT_TSU_DATASET_PATH`) | **DBMA 전체의 유일한 TSU 데이터셋 경로 — NAE 포함 예외 없음** |

**⚠️ 충돌 위험 (이번 조사에서 신규 발견)**: `scripts/build_tsu_dataset.py::main()`을 코드 레벨로 재확인한 결과,

```python
output_dir = Path(args.output_dir)                       # --output-dir로 변경 가능
registry_path = Path(registry_path_for(args.output_dir))  # --output-dir 따라 registry 경로도 변경됨
dataset_path = Path(DEFAULT_TSU_DATASET_PATH)              # ← 고정값! --output-dir와 무관
```

즉 `--output-dir data/nae/processed`로 NAE registry를 읽더라도, **TSU 산출물은 항상 `output/bench/tsu_dataset.jsonl`에 쓰인다(`write_tsu_dataset()`은 `open(dataset_path, "w", ...)`로 덮어씀).** 이는 실제(비-dry-run) 실행 시 **NAE 전용 TSU가 메인 코퍼스의 운영 TSU 데이터셋을 통째로 덮어쓰는** 심각한 데이터 손실 위험이었다.

- STEP4-D/STEP5 전 과정에서 `--dry-run`만 사용해온 것이 결과적으로 이 위험을 회피해왔음(의도적 설계는 아니었음 — 승인 절차상 우연히 안전했던 것)
- **[해결됨, 2026-07-31]** `scripts/build_tsu_dataset.py`에 `--dataset-path` CLI 인자를 추가 — 기본값은 기존과 동일한 `output/bench/tsu_dataset.jsonl`(`DEFAULT_TSU_DATASET_PATH`)로 유지되어 기존 실행 방식은 그대로 동작하고, `--output-dir`이 non-default 레지스트리를 가리킬 때는 `--dataset-path`로 별도 출력 경로를 명시해 충돌을 피할 수 있음. 예: `python -m scripts.build_tsu_dataset --output-dir data/nae/processed --dataset-path output/nae/bench/tsu_dataset.jsonl`
- `--manifest-path`(manifest.json도 동일하게 하드코딩된 `DEFAULT_TSU_MANIFEST_PATH`)는 이번 변경 범위 밖 — 여전히 고정 경로이므로, manifest까지 완전히 격리하려면 별도 확장 필요(추후 과제로 남김)
- 신규 회귀 테스트: `tests/test_build_tsu_dataset_output_path.py` — override 시 지정 경로에만 쓰기, 생략 시 기존 기본 경로 유지, `--help`에 플래그가 노출되는지 3가지 확인

## 4. Embedding Cache 위치

| 위치 | 용도 | 상태 |
|---|---|---|
| `data/제련완성본/cache/embeddings/` | 공식 임베딩 캐시 디렉토리 | 존재하나 현재 비어 있음(확인됨) |
| `cache/embeddings_backup_20260720` | 임베딩 캐시의 과거 백업 1건 | 존재 |
| `data/nae/embeddings/` | STEP1에서 생성된 NAE 전용 임베딩 캐시 자리 | **어떤 코드도 이 경로를 참조하지 않음** — `scripts/ingest_nae_source.py`, `core/tsu_builder.py` 모두 미사용. 용도 미정의 상태로 방치됨 |

**결론**: `data/nae/embeddings/`는 현재 죽은 디렉토리(dead directory) — 실제 임베딩 생성 단계는 아직 설계되지 않았고(이전 STEP들에서 "Embedding 미착수"로 일관되게 보고됨), 이 디렉토리가 실제로 쓰일지조차 결정된 바 없음.

## 5. Vector DB 위치

| 위치 | 용도 |
|---|---|
| `chroma_db/` (최상위, `config.yaml: directories.chroma_db_path`, `vector_db.chroma.persist_directory`) | **공식 Vector DB — Chroma, 단일 인스턴스**. 현재 약 100MB `chroma.sqlite3` 존재(운영 데이터로 추정) |
| `config.yaml`의 `vector_db.qdrant` 설정 | 존재하나 [[project_charter_qdrant_conflict]] 메모리 기준 **ADR-003으로 이미 사용 중단 결정됨** — 참고용 잔존 설정으로 판단, 실제 미사용 |

**결론**: NAE 전용 별도 Vector DB는 없으며, 만들 계획도 이번까지 문서화된 바 없음. "One Retrieval Engine" 원칙(CLAUDE.md)에 따라 NAE 데이터도 결국 이 단일 `chroma_db/`에 합류하는 것이 원칙에 부합 — 단, 그 통합 시점의 TSU 생성 단계에서 위 3번 항목의 경로 충돌 문제를 먼저 해결해야 함.

## 6. Backup 정책

| 위치 | 패턴 | 정책 여부 |
|---|---|---|
| `backup/`, `backups/` (최상위) | `backups/reconcile_pre_backup_20260717_193555`, `backups/chroma_backup_20260715_233708` 등 타임스탬프 폴더 | **공식 정책 문서 없음** — 특정 작업(reconcile, chroma 마이그레이션) 직전 수동 스냅샷으로 추정, 자동 로테이션/보존기간 규칙 미확인 |
| `output/bench/backup/` | bench 산출물 백업 | 동일 — 수동/ad-hoc으로 추정 |
| `cache/embeddings_backup_20260720` | 임베딩 캐시 백업 1건 | 동일 |

**결론**: 공식 backup 정책은 이번 조사 범위에서 문서화된 곳을 찾지 못함. NAE 데이터에 대한 백업 정책도 현재 없음 — 필요 시 별도 결정 사항.

## 원칙 적용 확인 (RAW immutable / Processed 재생성 가능 / Vector rebuild 가능 / TSU 검증 대상)

| 원칙 | 기존 구조 검증 | NAE 확장 적용 |
|---|---|---|
| **RAW는 immutable** | `core/processing.py::copy_source_file()`이 원본을 절대 이동/삭제하지 않음(주석 확인, "Sprint 2 policy") — `scripts/check_raw_only_originals.py`가 이 불변성이 실제로 깨졌는지(수동 삭제 등) 탐지하는 안전장치로 존재 | `data/nae/sources/`도 동일 원칙 적용 필요 — 단, 이 폴더를 감시하는 `check_raw_only_originals.py`류의 스크립트는 `data/RAW`만 대상으로 하드코딩되어 있어(코드 확인: `RAW_DIR = Path("data/RAW")`) **NAE RAW는 이 안전장치의 보호를 받지 못함** — 별도 확장 또는 새 스크립트 필요(이번 문서는 발견만, 구현 없음) |
| **Processed는 재생성 가능** | `data/제련완성본/`은 `data/RAW/`로부터 언제든 재처리 가능 — registry가 유실되어도 원본이 살아있으면 복구 가능 | `data/nae/processed/`도 `data/nae/sources/`가 보존되는 한 동일하게 재생성 가능 — 원칙 위반 없음 |
| **Vector는 rebuild 가능** | `chroma_db/`는 TSU 데이터셋으로부터 재생성 가능(전제: TSU 데이터셋이 살아있어야 함) | 동일 원칙 적용되나, 3번 항목의 TSU 경로 충돌이 해결되지 않으면 "재생성"이 오히려 "덮어쓰기 사고"로 이어질 수 있음 — 원칙 자체는 유효하나 현재 도구가 이를 안전하게 보장하지 못함 |
| **TSU는 검증 대상** | STEP3~STEP5 전 과정에서 이미 이 원칙을 따라옴(dry-run 우선, 채점 기준 문서화 등) | NAE TSU도 동일 — STEP4_TSU_QUALITY_CRITERIA.md 기준 계속 적용 |
