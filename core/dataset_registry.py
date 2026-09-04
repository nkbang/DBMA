"""Dataset Registry — Pydantic models and SQLite CRUD for DBMA search trust pipeline.

This module manages dataset provenance/trust tier at registration time.
It uses only the sqlite3 standard library — no new dependencies.

Constraints:
- Same dataset_id + version registration raises ValueError (never overwrite).
- tag_definition unique key is (tag_namespace, tag_name, version), not tag_name alone.
"""

from enum import Enum
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TrustTier(str, Enum):
    T1 = "T1"  # 본문/원어/객관 구조 데이터
    T2 = "T2"  # 검증된 큐레이션 의미 데이터
    T3 = "T3"  # 주석/사전/논문 등 문헌 근거
    T4 = "T4"  # 자동 분류 및 LLM 추론


class LicensePolicy(str, Enum):
    METADATA_ONLY = "metadata_only"
    LOCAL_USE = "local_use"
    REDISTRIBUTABLE = "redistributable"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ClaimPolicy(BaseModel):
    allowed: list[str] = []
    prohibited: list[str] = []


class DatasetRegistry(BaseModel):
    dataset_id: str
    dataset_name: str
    dataset_type: str
    provider: str
    version: str
    released_at: date | None = None
    trust_tier: TrustTier
    annotation_scope: list[str] = []
    tag_definition_uri: str | None = None
    license_status: str = "unverified"
    license_policy: LicensePolicy = LicensePolicy.LOCAL_USE
    retrieval_enabled: bool = False
    ranking_weight: float = 1.0
    claim_policy: ClaimPolicy = ClaimPolicy()
    ingested_at: datetime | None = None
    ingestion_pipeline_version: str | None = None


class QueryAuditLog(BaseModel):
    query_id: str
    user_query: str
    executed_at: datetime
    intent: list[str] = []
    query_expansions: list[str] = []
    datasets_used: list[dict] = []
    claim_guard_risk_level: str | None = None
    claim_guard_scope_qualifier_applied: bool = False
    claim_guard_absolute_claim_blocked: bool = False
    claim_guard_alternative_candidates_retrieved: bool = False
    answer_model: str | None = None
    prompt_policy_version: str | None = None


class TagDefinition(BaseModel):
    tag_namespace: str
    tag_name: str
    version: str
    definition_text: str | None = None
    definition_uri: str | None = None
    dataset_id: str | None = None


# ---------------------------------------------------------------------------
# Helper: JSON serialization
# ---------------------------------------------------------------------------

def _to_json(value):
    """Serialize a value to JSON string for storage."""
    if value is None:
        return None
    return json.dumps(value)


def _from_json(text, default=None):
    """Deserialize JSON string to value."""
    if text is None:
        return default
    return json.loads(text)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS dataset_registry (
    dataset_id TEXT NOT NULL,
    version TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    dataset_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    released_at TEXT,
    trust_tier TEXT NOT NULL,
    annotation_scope TEXT NOT NULL DEFAULT '[]',
    tag_definition_uri TEXT,
    license_status TEXT NOT NULL DEFAULT 'unverified',
    license_policy TEXT NOT NULL DEFAULT 'local_use',
    retrieval_enabled INTEGER NOT NULL DEFAULT 0,
    ranking_weight REAL NOT NULL DEFAULT 1.0,
    claim_policy TEXT NOT NULL DEFAULT '{}',
    ingested_at TEXT,
    ingestion_pipeline_version TEXT,
    PRIMARY KEY (dataset_id, version)
);

CREATE TABLE IF NOT EXISTS tag_definition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_namespace TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_text TEXT,
    definition_uri TEXT,
    dataset_id TEXT,
    UNIQUE(tag_namespace, tag_name, version),
    FOREIGN KEY (dataset_id) REFERENCES dataset_registry(dataset_id)
);

CREATE TABLE IF NOT EXISTS query_audit_log (
    query_id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    intent TEXT NOT NULL DEFAULT '[]',
    query_expansions TEXT NOT NULL DEFAULT '[]',
    datasets_used TEXT NOT NULL DEFAULT '[]',
    claim_guard_risk_level TEXT,
    claim_guard_scope_qualifier_applied INTEGER NOT NULL DEFAULT 0,
    claim_guard_absolute_claim_blocked INTEGER NOT NULL DEFAULT 0,
    claim_guard_alternative_candidates_retrieved INTEGER NOT NULL DEFAULT 0,
    answer_model TEXT,
    prompt_policy_version TEXT
);

CREATE TABLE IF NOT EXISTS bible_tag_annotation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_reference TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    tag_namespace TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    scope TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name)
);

CREATE TABLE IF NOT EXISTS dataset_license (
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    license_status TEXT NOT NULL,
    license_policy TEXT NOT NULL,
    license_note TEXT,
    verified_at TEXT,
    PRIMARY KEY (dataset_id, dataset_version)
);

CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    records_total INTEGER NOT NULL DEFAULT 0,
    records_ingested INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    records_duplicate INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
"""


# ---------------------------------------------------------------------------
# SQLite CRUD functions
# ---------------------------------------------------------------------------

def init_db(db_path: str) -> None:
    """Initialize the SQLite database with all required tables."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
    finally:
        conn.close()


def _dataset_row_to_model(row) -> DatasetRegistry:
    """Convert a database row to a DatasetRegistry model."""
    return DatasetRegistry(
        dataset_id=row["dataset_id"],
        version=row["version"],
        dataset_name=row["dataset_name"],
        dataset_type=row["dataset_type"],
        provider=row["provider"],
        released_at=date.fromisoformat(row["released_at"]) if row["released_at"] else None,
        trust_tier=TrustTier(row["trust_tier"]),
        annotation_scope=_from_json(row["annotation_scope"], []),
        tag_definition_uri=row["tag_definition_uri"],
        license_status=row["license_status"],
        license_policy=LicensePolicy(row["license_policy"]),
        retrieval_enabled=bool(row["retrieval_enabled"]),
        ranking_weight=row["ranking_weight"],
        claim_policy=ClaimPolicy(**_from_json(row["claim_policy"], {})) if row["claim_policy"] else ClaimPolicy(),
        ingested_at=datetime.fromisoformat(row["ingested_at"]) if row["ingested_at"] else None,
        ingestion_pipeline_version=row["ingestion_pipeline_version"],
    )


def _query_audit_row_to_model(row) -> QueryAuditLog:
    """Convert a database row to a QueryAuditLog model."""
    return QueryAuditLog(
        query_id=row["query_id"],
        user_query=row["user_query"],
        executed_at=datetime.fromisoformat(row["executed_at"]),
        intent=_from_json(row["intent"], []),
        query_expansions=_from_json(row["query_expansions"], []),
        datasets_used=_from_json(row["datasets_used"], []),
        claim_guard_risk_level=row["claim_guard_risk_level"],
        claim_guard_scope_qualifier_applied=bool(row["claim_guard_scope_qualifier_applied"]),
        claim_guard_absolute_claim_blocked=bool(row["claim_guard_absolute_claim_blocked"]),
        claim_guard_alternative_candidates_retrieved=bool(row["claim_guard_alternative_candidates_retrieved"]),
        answer_model=row["answer_model"],
        prompt_policy_version=row["prompt_policy_version"],
    )


def register_dataset(db_path: str, dataset: DatasetRegistry) -> None:
    """Register a dataset in the registry.

    Raises ValueError if the same dataset_id + version already exists.
    """
    conn = sqlite3.connect(db_path)
    try:
        # Check for duplicate
        cursor = conn.execute(
            "SELECT 1 FROM dataset_registry WHERE dataset_id = ? AND version = ?",
            (dataset.dataset_id, dataset.version),
        )
        if cursor.fetchone():
            raise ValueError(
                f"Dataset already exists: dataset_id={dataset.dataset_id}, version={dataset.version}"
            )

        conn.execute(
            """INSERT INTO dataset_registry (
                dataset_id, version, dataset_name, dataset_type, provider,
                released_at, trust_tier, annotation_scope, tag_definition_uri,
                license_status, license_policy, retrieval_enabled, ranking_weight,
                claim_policy, ingested_at, ingestion_pipeline_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dataset.dataset_id,
                dataset.version,
                dataset.dataset_name,
                dataset.dataset_type,
                dataset.provider,
                dataset.released_at.isoformat() if dataset.released_at else None,
                dataset.trust_tier.value,
                _to_json(dataset.annotation_scope),
                dataset.tag_definition_uri,
                dataset.license_status,
                dataset.license_policy.value,
                int(dataset.retrieval_enabled),
                dataset.ranking_weight,
                _to_json(dataset.claim_policy.model_dump()),
                dataset.ingested_at.isoformat() if dataset.ingested_at else None,
                dataset.ingestion_pipeline_version,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_dataset(db_path: str, dataset_id: str) -> DatasetRegistry | None:
    """Get a single dataset by its dataset_id. Returns None if not found."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM dataset_registry WHERE dataset_id = ? ORDER BY version DESC LIMIT 1",
            (dataset_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _dataset_row_to_model(row)
    finally:
        conn.close()


def list_datasets(db_path: str, trust_tier: TrustTier | None = None) -> list[DatasetRegistry]:
    """List all datasets, optionally filtered by trust_tier."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        if trust_tier is not None:
            cursor = conn.execute(
                "SELECT * FROM dataset_registry WHERE trust_tier = ? ORDER BY dataset_id",
                (trust_tier.value,),
            )
        else:
            cursor = conn.execute("SELECT * FROM dataset_registry ORDER BY dataset_id")
        return [_dataset_row_to_model(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def log_query_audit(db_path: str, entry: QueryAuditLog) -> None:
    """Log a query audit entry."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO query_audit_log (
                query_id, user_query, executed_at, intent, query_expansions,
                datasets_used, claim_guard_risk_level,
                claim_guard_scope_qualifier_applied,
                claim_guard_absolute_claim_blocked,
                claim_guard_alternative_candidates_retrieved,
                answer_model, prompt_policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.query_id,
                entry.user_query,
                entry.executed_at.isoformat(),
                _to_json(entry.intent),
                _to_json(entry.query_expansions),
                _to_json(entry.datasets_used),
                entry.claim_guard_risk_level,
                int(entry.claim_guard_scope_qualifier_applied),
                int(entry.claim_guard_absolute_claim_blocked),
                int(entry.claim_guard_alternative_candidates_retrieved),
                entry.answer_model,
                entry.prompt_policy_version,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_query_audit(db_path: str, query_id: str) -> QueryAuditLog | None:
    """Get a query audit entry by query_id. Returns None if not found."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM query_audit_log WHERE query_id = ?",
            (query_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _query_audit_row_to_model(row)
    finally:
        conn.close()


def list_query_audits(db_path: str, limit: int = 100) -> list[QueryAuditLog]:
    """List recent query audit entries."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM query_audit_log ORDER BY executed_at DESC LIMIT ?",
            (limit,),
        )
        return [_query_audit_row_to_model(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def register_tag_definition(db_path: str, tag: TagDefinition) -> None:
    """Register a tag definition.

    Unique key is (tag_namespace, tag_name, version) — not tag_name alone.
    Raises ValueError if the same (namespace, name, version) already exists.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO tag_definition (tag_namespace, tag_name, version, definition_text, definition_uri, dataset_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tag.tag_namespace,
                tag.tag_name,
                tag.version,
                tag.definition_text,
                tag.definition_uri,
                tag.dataset_id,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(
            f"Tag definition already exists: namespace={tag.tag_namespace}, "
            f"name={tag.tag_name}, version={tag.version}"
        )
    finally:
        conn.close()


def get_tag_definitions(db_path: str, dataset_id: str | None = None) -> list[TagDefinition]:
    """Get tag definitions, optionally filtered by dataset_id."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        if dataset_id is not None:
            cursor = conn.execute(
                "SELECT tag_namespace, tag_name, version, definition_text, definition_uri, dataset_id "
                "FROM tag_definition WHERE dataset_id = ? ORDER BY tag_namespace, tag_name",
                (dataset_id,),
            )
        else:
            cursor = conn.execute(
                "SELECT tag_namespace, tag_name, version, definition_text, definition_uri, dataset_id "
                "FROM tag_definition ORDER BY tag_namespace, tag_name"
            )
        rows = cursor.fetchall()
        return [
            TagDefinition(
                tag_namespace=row["tag_namespace"],
                tag_name=row["tag_name"],
                version=row["version"],
                definition_text=row["definition_text"],
                definition_uri=row["definition_uri"],
                dataset_id=row["dataset_id"],
            )
            for row in rows
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Sprint B: Pydantic Models (bible_tag_annotation / dataset_license / ingestion_run)
# ---------------------------------------------------------------------------

class BibleTagAnnotation(BaseModel):
    canonical_reference: str
    dataset_id: str
    dataset_version: str
    tag_namespace: str
    tag_name: str
    scope: str  # "verse" | "clause" | "discourse_unit"
    created_at: datetime


class DatasetLicense(BaseModel):
    dataset_id: str
    dataset_version: str
    license_status: str  # "verified" | "unverified" | "restricted"
    license_policy: str  # LicensePolicy enum value string
    license_note: str | None = None
    verified_at: datetime | None = None


class IngestionRun(BaseModel):
    run_id: str
    dataset_id: str
    dataset_version: str
    started_at: datetime
    finished_at: datetime | None = None
    records_total: int = 0
    records_ingested: int = 0
    records_rejected: int = 0
    records_duplicate: int = 0
    error_summary: list[str] = []


# ---------------------------------------------------------------------------
# Sprint B: SQLite CRUD functions
# ---------------------------------------------------------------------------

def register_tag_annotation(db_path: str, annotation: BibleTagAnnotation) -> None:
    """Register a bible tag annotation.

    Raises ValueError if the unique key (canonical_reference, dataset_id,
    dataset_version, tag_namespace, tag_name) already exists.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO bible_tag_annotation
               (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                annotation.canonical_reference,
                annotation.dataset_id,
                annotation.dataset_version,
                annotation.tag_namespace,
                annotation.tag_name,
                annotation.scope,
                annotation.created_at.isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(
            f"Tag annotation already exists: canonical_reference={annotation.canonical_reference}, "
            f"dataset_id={annotation.dataset_id}, dataset_version={annotation.dataset_version}, "
            f"tag_namespace={annotation.tag_namespace}, tag_name={annotation.tag_name}"
        )
    finally:
        conn.close()


def get_tag_annotation(db_path: str, canonical_reference: str, dataset_id: str) -> BibleTagAnnotation | None:
    """Get a bible tag annotation by canonical_reference + dataset_id. Returns None if not found."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM bible_tag_annotation WHERE canonical_reference = ? AND dataset_id = ? ORDER BY created_at DESC LIMIT 1",
            (canonical_reference, dataset_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return BibleTagAnnotation(
            canonical_reference=row["canonical_reference"],
            dataset_id=row["dataset_id"],
            dataset_version=row["dataset_version"],
            tag_namespace=row["tag_namespace"],
            tag_name=row["tag_name"],
            scope=row["scope"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
    finally:
        conn.close()


def record_license(db_path: str, license_rec: DatasetLicense) -> None:
    """Record or update dataset license info.

    Raises ValueError if the primary key (dataset_id, dataset_version) already exists.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO dataset_license
               (dataset_id, dataset_version, license_status, license_policy, license_note, verified_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                license_rec.dataset_id,
                license_rec.dataset_version,
                license_rec.license_status,
                license_rec.license_policy,
                license_rec.license_note,
                license_rec.verified_at.isoformat() if license_rec.verified_at else None,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(
            f"License record already exists: dataset_id={license_rec.dataset_id}, "
            f"dataset_version={license_rec.dataset_version}"
        )
    finally:
        conn.close()


def get_license(db_path: str, dataset_id: str) -> DatasetLicense | None:
    """Get license info for a dataset. Returns None if not found."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM dataset_license WHERE dataset_id = ? ORDER BY dataset_version DESC LIMIT 1",
            (dataset_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return DatasetLicense(
            dataset_id=row["dataset_id"],
            dataset_version=row["dataset_version"],
            license_status=row["license_status"],
            license_policy=row["license_policy"],
            license_note=row["license_note"],
            verified_at=datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
        )
    finally:
        conn.close()


def start_ingestion_run(db_path: str, run: IngestionRun) -> None:
    """Record the start of an ingestion run."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO ingestion_run
               (run_id, dataset_id, dataset_version, started_at, finished_at,
                records_total, records_ingested, records_rejected, records_duplicate, error_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id,
                run.dataset_id,
                run.dataset_version,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.records_total,
                run.records_ingested,
                run.records_rejected,
                run.records_duplicate,
                _to_json(run.error_summary),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def finish_ingestion_run(db_path: str, run_id: str, finished_at: datetime,
                         records_ingested: int, records_rejected: int,
                         records_duplicate: int, error_summary: list[str]) -> None:
    """Update an ingestion run record with final counts."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """UPDATE ingestion_run SET finished_at = ?, records_ingested = ?,
               records_rejected = ?, records_duplicate = ?, error_summary = ?
               WHERE run_id = ?""",
            (
                finished_at.isoformat(),
                records_ingested,
                records_rejected,
                records_duplicate,
                _to_json(error_summary),
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_ingestion_run(db_path: str, run_id: str) -> IngestionRun | None:
    """Get an ingestion run by run_id. Returns None if not found."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM ingestion_run WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return IngestionRun(
            run_id=row["run_id"],
            dataset_id=row["dataset_id"],
            dataset_version=row["dataset_version"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            records_total=row["records_total"],
            records_ingested=row["records_ingested"],
            records_rejected=row["records_rejected"],
            records_duplicate=row["records_duplicate"],
            error_summary=_from_json(row["error_summary"], []),
        )
    finally:
        conn.close()
