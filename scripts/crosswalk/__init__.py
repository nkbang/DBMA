"""scripts/crosswalk — NAE Identifier Crosswalk Layer (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001).

Connects Registry/Manifest `source_id` (Authority Layer, unchanged —
ADR-017 Option B) to Corpus/TSU `identifier` (Corpus Layer). See
docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md and
docs/NAE_IDENTIFIER_CROSSWALK_REVIEW_PACKAGE_001.md (C1 Approved) for
the architecture this package implements.

This package does not decide where Crosswalk records are persisted
(ADR-019 Storage Decision is still conditionally deferred) — `schema.py`
and `repository.py` are storage-agnostic; only `InMemoryCrosswalkRepository`
is provided here as a reference/test implementation.
"""
