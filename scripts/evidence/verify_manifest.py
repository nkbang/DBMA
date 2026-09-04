#!/usr/bin/env python3
"""verify_manifest.py — Verify manifest.json against actual files per Evidence Package Standard v1.1 §7.

Usage:
    python -m scripts.evidence.verify_manifest --package evidence/<TASK-ID>/<PACKAGE-ID>
    python scripts/evidence/verify_manifest.py --package evidence/<TASK-ID>/<PACKAGE-ID>

Checks:
  (a) Every file in manifest.json exists and matches size/sha256.
  (b) Every actual file under package root (excluding manifest.json, seal.json,
      excluded_paths) is listed in manifest.json — bidirectional check.

Exit code: 0 if all match, 1 if any mismatch.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


EXCLUDED_FILES = {"manifest.json", "seal.json"}


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_manifest(package_root: Path) -> dict:
    """Load manifest.json from package root."""
    manifest_path = package_root / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_manifest(package_root: Path) -> tuple:
    """Verify manifest against actual files.

    Returns:
        (success: bool, errors: list[str])
    """
    errors = []
    manifest = load_manifest(package_root)
    package_root = package_root.resolve()

    # Build set of manifest paths
    manifest_paths = set()
    for entry in manifest.get("files", []):
        manifest_paths.add(entry["path"])

    # Check (a): every manifest entry exists and matches
    for entry in manifest.get("files", []):
        rel_path = entry["path"]
        abs_path = package_root / rel_path

        if not abs_path.exists():
            errors.append(f"MISSING: {rel_path} (declared in manifest but not on disk)")
            continue

        actual_size = abs_path.stat().st_size
        actual_sha256 = compute_sha256(abs_path)

        if actual_size != entry["size"]:
            errors.append(
                f"SIZE MISMATCH: {rel_path} "
                f"(manifest={entry['size']}, actual={actual_size})"
            )

        if actual_sha256 != entry["sha256"]:
            errors.append(
                f"SHA256 MISMATCH: {rel_path} "
                f"(manifest={entry['sha256'][:16]}..., actual={actual_sha256[:16]}...)"
            )

    # Collect actual files under package root
    actual_paths = set()
    excluded = set(manifest.get("excluded_paths", [])) | EXCLUDED_FILES

    for dirpath, _dirnames, filenames in os.walk(package_root):
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel_path = str(fpath.relative_to(package_root))
            if fname in EXCLUDED_FILES or fname == ".DS_Store":
                continue
            if rel_path in excluded:
                continue
            actual_paths.add(rel_path)

    # Check (b): every actual file is in manifest
    for apath in sorted(actual_paths):
        if apath not in manifest_paths:
            errors.append(f"UNDECLARED: {apath} (on disk but not in manifest)")

    # Check (c): every manifest path that is an excluded file should be in excluded_paths
    declared_excluded = set(manifest.get("excluded_paths", [])) | EXCLUDED_FILES
    for entry in manifest.get("files", []):
        rel_path = entry["path"]
        fname = os.path.basename(rel_path)
        if fname in EXCLUDED_FILES and rel_path not in declared_excluded:
            errors.append(
                f"EXCLUDED FILE IN FILES: {rel_path} "
                f"(should be in excluded_paths, not files)"
            )

    success = len(errors) == 0
    return success, errors


def main():
    parser = argparse.ArgumentParser(
        description="Verify manifest.json against actual package files."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to the package root (e.g., evidence/TASK-ID/PACKAGE-ID)",
    )
    args = parser.parse_args()

    package_root = Path(args.package)

    if not package_root.is_dir():
        print(f"ERROR: Package root does not exist: {package_root}", file=sys.stderr)
        sys.exit(1)

    success, errors = verify_manifest(package_root)

    if success:
        print("MANIFEST VERIFIED")
        print(f"  All {len(load_manifest(package_root).get('files', []))} entries match.")
        sys.exit(0)
    else:
        print("BLOCKED — MANIFEST PAYLOAD SET MISMATCH")
        for err in errors:
            print(f"  FAIL: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()