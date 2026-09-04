"""scripts/crosswalk/storage — Crosswalk YAML Persistence
(NAE-CROSSWALK-STORAGE-ADAPTER-IMPLEMENTATION-001).

Implements the approved Option B storage location
(`docs/NAE_CROSSWALK_STORAGE_DECISION_001.md`): a dedicated,
comment-preserving YAML file as the single source of truth, with an
optional rebuildable JSON index for lookup convenience.

`crosswalk.yaml` is always authoritative. `index.json` is derived and
disposable — losing it costs nothing beyond a rebuild.
"""
