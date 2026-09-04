"""Paths and constants for the upstream registration pipeline (ADR-021)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_ROOT = PROJECT_ROOT / "NAE" / "corpus" / "raw"

AUTHORITY_ROOT = PROJECT_ROOT / "NAE" / "authority"
LEGACY_SNAPSHOT_DIR = AUTHORITY_ROOT / "legacy_snapshot"
NEW_AUTHORS_PATH = AUTHORITY_ROOT / "authors.yaml"
NEW_WORKS_PATH = AUTHORITY_ROOT / "works.yaml"

STATE_DIR = Path(__file__).resolve().parent / "state"
DEFAULT_REGISTRATION_STATE_PATH = STATE_DIR / "registration_state.json"
DEFAULT_EXCEPTION_QUEUE_PATH = STATE_DIR / "exception_queue.json"
DEFAULT_CHECKSUM_LEDGER_PATH = STATE_DIR / "raw_checksum_ledger.jsonl"
DEFAULT_SOURCE_MANIFEST_PATH = STATE_DIR / "source_manifest.yaml"

# Raw files get this permission after preservation — accident deterrent only,
# NOT the enforcement mechanism (see raw_preservation.py / ADR-021 SS6).
RAW_READONLY_MODE = 0o444
