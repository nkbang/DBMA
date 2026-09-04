# C1 Task Order 020 — Sprint A: DatasetRegistry/TrustTier/ClaimPolicy 스키마 (SQLite)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (검색 신뢰성 파이프라인 v2/v3 착수의 전제 작업)
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md) §3 Sprint A,
[docs/architecture/NAE-Unified-Research-Search-Plan-v3.md](../../architecture/NAE-Unified-Research-Search-Plan-v3.md)
**작성일**: 2026-07-29
**모드 제약**: 이번 Task Order는 스키마·CRUD 정의만 다룬다. `core/retrieval.py`의 기존 검색 로직은
**절대 수정하지 말 것** (Sprint C에서 다룸). ACT MODE로 바로 구현 가능 — 이번 범위는 신규 파일 생성 위주라
넓은 탐색이 필요 없음.

---

## 1. 배경

DBMA 검색 신뢰성 파이프라인은 사용자별 승인/보류/거부 UI(v1, 폐기됨) 대신 **데이터셋 등록 시점의
provenance/trust tier 관리 + ClaimGuard 자동 규칙**으로 신뢰성을 확보하는 방향(v2)으로 확정됐다.
이 Task Order는 그 첫 단계 — 데이터를 담을 스키마와 최소 CRUD를 SQLite로 구현하는 작업이다.

**저장소는 SQLite로 확정됨** (PostgreSQL 도입 안 함). 신규 파일 `data/dataset_registry.db` 하나에
아래 6개 테이블을 둔다.

---

## 2. 구현 범위

### 2.1 신규 모듈 — `core/dataset_registry.py`

다음 Pydantic 모델과 SQLite DDL/CRUD 함수를 구현한다.

**Pydantic 모델:**

```python
from enum import Enum
from pydantic import BaseModel
from datetime import date, datetime

class TrustTier(str, Enum):
    T1 = "T1"  # 본문/원어/객관 구조 데이터
    T2 = "T2"  # 검증된 큐레이션 의미 데이터
    T3 = "T3"  # 주석/사전/논문 등 문헌 근거
    T4 = "T4"  # 자동 분류 및 LLM 추론

class LicensePolicy(str, Enum):
    METADATA_ONLY = "metadata_only"
    LOCAL_USE = "local_use"
    REDISTRIBUTABLE = "redistributable"

class ClaimPolicy(BaseModel):
    allowed: list[str]       # 예: ["dataset-scoped statement", "structural observation"]
    prohibited: list[str]    # 예: ["absolute first occurrence", "universal theological conclusion"]

class DatasetRegistry(BaseModel):
    dataset_id: str                  # 예: "lexham.propositional_outline.ot" — namespace.name 형식
    dataset_name: str
    dataset_type: str
    provider: str
    version: str
    released_at: date | None
    trust_tier: TrustTier
    annotation_scope: list[str]      # 예: ["verse", "clause", "discourse_unit"]
    tag_definition_uri: str | None
    license_status: str              # "verified" | "unverified" | "restricted"
    license_policy: LicensePolicy
    retrieval_enabled: bool
    ranking_weight: float
    claim_policy: ClaimPolicy
    ingested_at: datetime | None
    ingestion_pipeline_version: str | None

class QueryAuditLog(BaseModel):
    query_id: str
    user_query: str
    executed_at: datetime
    intent: list[str]
    query_expansions: list[str]
    datasets_used: list[dict]        # [{"dataset_id": ..., "version": ..., "trust_tier": ...}]
    claim_guard_risk_level: str | None
    claim_guard_scope_qualifier_applied: bool
    claim_guard_absolute_claim_blocked: bool
    claim_guard_alternative_candidates_retrieved: bool
    answer_model: str | None
    prompt_policy_version: str | None
```

**SQLite 테이블 (지시서 원문 6종, 이번 Task Order는 아래 3종만 우선 구현 — 나머지는 §2.3 참고):**

- `dataset_registry` — 위 `DatasetRegistry` 모델 컬럼 그대로 (list/dict 필드는 JSON 직렬화해 TEXT 컬럼에 저장)
- `tag_definition` — `tag_namespace`, `tag_name`, `version`, `definition_text`, `definition_uri`, `dataset_id`(FK)
- `query_audit_log` — 위 `QueryAuditLog` 모델 컬럼 그대로

**CRUD 함수 (동기, sqlite3 표준 라이브러리만 사용 — 신규 의존성 추가 금지):**

```python
def init_db(db_path: str) -> None: ...
def register_dataset(db_path: str, dataset: DatasetRegistry) -> None: ...
def get_dataset(db_path: str, dataset_id: str) -> DatasetRegistry | None: ...
def list_datasets(db_path: str, trust_tier: TrustTier | None = None) -> list[DatasetRegistry]: ...
def log_query_audit(db_path: str, entry: QueryAuditLog) -> None: ...
```

### 2.2 핵심 제약 (반드시 지킬 것)

- **namespace/version 충돌 방지**: `register_dataset()`은 같은 `dataset_id`+`version` 조합이 이미 있으면
  `ValueError`를 던진다 (덮어쓰기 금지 — never overwrite 원칙). 버전이 다르면 별도 레코드로 추가.
- **동일 태그 이름, 다른 출처 = 다른 레코드**: `tag_definition`의 유일 키는 `(tag_namespace, tag_name, version)`
  이지 `tag_name` 단독이 아니다. 예: `lexham.propositional_outline:prayer`와 `dbma.discourse_annotation:prayer`는
  별개 레코드.
- **T2/T4는 절대 주장 근거 불가**를 코드로 강제하지는 않음 (그건 Sprint D의 ClaimGuard 역할) — 이번
  Task Order는 스키마에 `claim_policy` 필드를 정확히 저장/조회만 하면 됨.

### 2.3 이번 범위에서 제외 (다음 Task Order로 미룸)

- `bible_tag_annotation`, `dataset_license`, `ingestion_run` 테이블 — Sprint B(인제스트)에서 실제 데이터가
  들어올 때 같이 설계하는 게 맞음. 지금 빈 스키마만 미리 만들면 필드가 맞지 않아 재작업 위험.
- canonical Bible reference parser 연동 — `core/retrieval.py`의 기존 `ScriptureReference` 클래스(51행)를
  재사용할지 여부는 Sprint C에서 결정. 이번엔 건드리지 않음.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_dataset_registry.py` 신규):
   - `init_db()` 호출 시 3개 테이블이 정상 생성되는지
   - `register_dataset()` 정상 등록 + 조회(`get_dataset`) 일치 확인
   - 동일 `dataset_id`+`version` 재등록 시 `ValueError` 발생 확인
   - 버전이 다르면 재등록 허용되는지
   - `list_datasets(trust_tier=TrustTier.T2)` 필터링 정상 동작
   - `log_query_audit()` 저장 + 조회 확인
   - `ClaimPolicy`/`intent`/`query_expansions` 같은 list/dict 필드가 왕복(round-trip) 시 원본과 동일한지
2. 기존 테스트 스위트 회귀 없음 확인 (`pytest tests/ -q` 전체는 무거우면 관련 디렉토리만).

---

## 4. 보고 형식

1. `core/dataset_registry.py` + `tests/test_dataset_registry.py` diff
2. 테스트 실행 결과 (pass 수)
3. DDL 스키마 최종본 (CREATE TABLE 문 전체)
4. 다음 Task Order(Sprint B) 착수 전 확인이 필요한 사항이 있으면 별도 기록

---

## 5. 다음 조치

Sprint A 완료·검증 후 Sprint B(TagIngestValidator, 데이터셋 adapter) Task Order를 CUE가 별도 발급.
