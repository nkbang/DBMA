#!/usr/bin/env python3
"""build_seal.py — Generate seal.json per Evidence Package Standard v1.1 §5.

Usage:
    python -m scripts.evidence.build_seal --package evidence/<TASK-ID>/<PACKAGE-ID> \
      --payload-commit <SHA> --payload-tree <SHA>
    python scripts/evidence/build_seal.py --package evidence/<TASK-ID>/<PACKAGE-ID> \
      --payload-commit <SHA> --payload-tree <SHA>

Computes SHA256 of manifest.json and writes seal.json with:
  - payload_commit_sha (from --payload-commit)
  - payload_tree_sha (from --payload-tree)
  - manifest_sha256 (computed from manifest.json in package root)
  - sealed_at_utc (current UTC time)
  - seal_commit_sha = null (not yet committed)
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def compute_sha256_file(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Generate seal.json for an Evidence Package."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to the package root (e.g., evidence/TASK-ID/PACKAGE-ID)",
    )
    parser.add_argument(
        "--payload-commit",
        required=True,
        help="Git commit SHA of the payload commit (E)",
    )
    parser.add_argument(
        "--payload-tree",
        required=True,
        help="Git tree SHA of the payload commit (from git write-tree)",
    )
    args = parser.parse_args()

    package_root = Path(args.package)
    manifest_path = package_root / "manifest.json"

    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    # Compute manifest SHA256
    manifest_sha256 = compute_sha256_file(manifest_path)

    # Load manifest to get package_id
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    seal = {
        "schema_version": "1.1",
        "package_id": manifest.get("package_id", package_root.name),
        "payload_commit_sha": args.payload_commit,
        "payload_tree_sha": args.payload_tree,
        "manifest_sha256": manifest_sha256,
        "sealed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seal_commit_sha": None,
    }

    seal_path = package_root / "seal.json"
    with open(seal_path, "w", encoding="utf-8") as f:
        json.dump(seal, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"seal.json written to {seal_path}")
    print(f"  package_id: {seal['package_id']}")
    print(f"  payload_commit_sha: {seal['payload_commit_sha']}")
    print(f"  payload_tree_sha: {seal['payload_tree_sha']}")
    print(f"  manifest_sha256: {seal['manifest_sha256'][:16]}...")
    print(f"  sealed_at_utc: {seal['sealed_at_utc']}")


if __name__ == "__main__":
    main()