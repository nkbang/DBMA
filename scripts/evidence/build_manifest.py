#!/usr/bin/env python3
"""build_manifest.py — Generate manifest.json per Evidence Package Standard v1.1 §6.

Usage:
    python -m scripts.evidence.build_manifest --package evidence/<TASK-ID>/<PACKAGE-ID>
    python scripts/evidence/build_manifest.py --package evidence/<TASK-ID>/<PACKAGE-ID>

Scans all files under <PACKAGE_ROOT> recursively, computes SHA256/size/media_type,
and writes manifest.json following the standard §"manifest.json 규격" schema.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# Extensions mapped to media types per standard convention
MEDIA_TYPE_MAP = {
    ".md": "text/markdown",
    ".json": "application/json",
    ".txt": "text/plain",
    ".csv": "text/plain",
    ".py": "text/x-python",
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".xml": "application/xml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".log": "text/plain",
    ".sha256": "text/plain",
    ".pem": "application/x-pem",
    ".key": "application/x-key",
    ".crt": "application/x-certificate",
}

# Files to always exclude from manifest
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


def get_media_type(filepath: Path) -> str:
    """Infer media type from file extension."""
    ext = filepath.suffix.lower()
    return MEDIA_TYPE_MAP.get(ext, "text/plain")


def build_manifest(package_root: Path) -> dict:
    """Build manifest dict for all files under package_root.

    Returns:
        Manifest dictionary per standard schema.
    """
    files = []
    excluded_paths = []

    package_root = package_root.resolve()

    for dirpath, _dirnames, filenames in os.walk(package_root):
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel_path = fpath.relative_to(package_root)
            rel_str = str(rel_path)

            # Skip excluded files
            if fname in EXCLUDED_FILES:
                excluded_paths.append(rel_str)
                continue

            # Skip .DS_Store
            if fname == ".DS_Store":
                excluded_paths.append(rel_str)
                continue

            abs_path = fpath.resolve()
            size = abs_path.stat().st_size
            sha256 = compute_sha256(abs_path)
            media_type = get_media_type(abs_path)

            files.append({
                "path": rel_str,
                "sha256": sha256,
                "size": size,
                "media_type": media_type,
            })

    # Sort files by path for deterministic output
    files.sort(key=lambda x: x["path"])
    excluded_paths.sort()

    # Always include manifest.json and seal.json in excluded_paths even if not found
    for name in EXCLUDED_FILES:
        rel = f"{name}"
        if rel not in excluded_paths:
            excluded_paths.append(rel)
    excluded_paths.sort()

    package_id = package_root.name

    manifest = {
        "schema_version": "1.1",
        "package_id": package_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hash_algorithm": "sha256",
        "files": files,
        "excluded_paths": excluded_paths,
    }

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate manifest.json for an Evidence Package."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to the package root (e.g., evidence/TASK-ID/PACKAGE-ID)",
    )
    parser.add_argument(
        "--package-id",
        default=None,
        help="Override package_id (defaults to last path segment of --package)",
    )
    args = parser.parse_args()

    package_root = Path(args.package)

    if not package_root.is_dir():
        print(f"ERROR: Package root does not exist: {package_root}", file=sys.stderr)
        sys.exit(1)

    manifest = build_manifest(package_root)

    # Override package_id if specified
    if args.package_id:
        manifest["package_id"] = args.package_id

    # Check for duplicate SHA256 and warn
    sha_map = {}
    for f in manifest["files"]:
        sha = f["sha256"]
        if sha not in sha_map:
            sha_map[sha] = []
        sha_map[sha].append(f["path"])

    for sha, paths in sha_map.items():
        if len(paths) > 1:
            print(
                f"WARNING: Duplicate SHA256 {sha[:16]}... found in: {', '.join(paths)}",
                file=sys.stderr,
            )

    # Write manifest.json
    output_path = package_root / "manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"manifest.json written to {output_path}")
    print(f"  package_id: {manifest['package_id']}")
    print(f"  files: {len(manifest['files'])}")
    print(f"  excluded: {len(manifest['excluded_paths'])}")


if __name__ == "__main__":
    main()