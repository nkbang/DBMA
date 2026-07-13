#!/usr/bin/env python
"""
evaluation_fingerprint.py — DBMA Evaluation Runtime Fingerprint Generator

Generates a complete runtime fingerprint for DBMA evaluations.
Run with:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate && python scripts/evaluation_fingerprint.py

Output: evaluation_fingerprint.json in the current working directory.

Fingerprint follows PT-EVALUATION-002 LOOP2 specification:
  - 9 mandatory fields (M-01 through M-09)
  - 5 recommended fields (R-01 through R-05)
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone


def get_git_commit():
    """Get full git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "NOT_GIT_REPO"


def get_git_branch():
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def get_python_version():
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_virtual_environment():
    """Get virtual environment path."""
    return sys.prefix


def get_packages_hash():
    """Hash of all installed package versions."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return sha256_bytes(result.stdout.encode("utf-8"))
    except Exception:
        pass
    # Fallback: try importlib-based approach
    try:
        packages = {}
        import pkg_resources
        for dist in pkg_resources.working_set:
            packages[dist.project_name] = dist.version
        content = "\n".join(f"{k}=={v}" for k, v in sorted(packages.items()))
        return sha256_bytes(content.encode("utf-8"))
    except Exception:
        return "COMPUTE_FAILED"


def sha256_file(filepath):
    """Compute SHA256 of a file."""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "READ_FAILED"


def sha256_bytes(data):
    """Compute SHA256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def get_tsu_dataset_hash():
    """Compute hash of TSU corpus files or vector store metadata."""
    tsu_dir = os.path.join("core", "tsu")

    # Strategy 1: Collect .jsonl/.json files
    files_to_hash = []
    if os.path.isdir(tsu_dir):
        for root, dirs, filenames in os.walk(tsu_dir):
            for fn in sorted(filenames):
                if fn.endswith((".jsonl", ".json")):
                    full_path = os.path.join(root, fn)
                    files_to_hash.append(full_path)

    if files_to_hash:
        h = hashlib.sha256()
        for fpath in files_to_hash:
            file_content = sha256_file(fpath)
            h.update(f"{os.path.basename(fpath)}:{file_content}".encode("utf-8"))
        return h.hexdigest()

    # Strategy 2: Check for Qdrant .bin/.sqlite storage files
    vector_dirs = [
        os.path.join("VectorDB"),
        os.path.join("core", "qdrant_data"),
    ]
    for vdir in vector_dirs:
        if os.path.isdir(vdir):
            vec_files = []
            for root, dirs, filenames in os.walk(vdir):
                for fn in sorted(filenames):
                    full_path = os.path.join(root, fn)
                    vec_files.append(full_path)
            if vec_files:
                h = hashlib.sha256()
                for fpath in vec_files:
                    file_content = sha256_file(fpath)
                    h.update(f"{os.path.relpath(fpath)}:{file_content}".encode("utf-8"))
                return f"qdrant_hash:{h.hexdigest()[:32]}"

    return "TSU_UNDETECTABLE"


def get_embedding_model():
    """Get embedding model from config.yaml if available."""
    try:
        with open("config.yaml", "r") as f:
            content = f.read()
        # Simple parsing for embedding.model_name or embedding.model field
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "model:" in stripped or "model_name:" in stripped:
                parts = stripped.split(":")
                if len(parts) >= 2:
                    return parts[-1].strip().strip('"\'')
    except Exception:
        pass
    return "CONFIG_NOT_FOUND"


def get_gold_query_version():
    """Get golden query dataset version."""
    gold_path = os.path.join("tests", "gold_queries.json")
    if not os.path.exists(gold_path):
        return "NOT_FOUND"
    try:
        with open(gold_path, "r") as f:
            data = json.load(f)
        version = data.get("version", None)
        if version:
            return version
        # Fallback: compute hash of the file
        return f"hash:{sha256_file(gold_path)[:16]}"
    except Exception:
        return "PARSE_FAILED"


def generate_fingerprint(output_dir="."):
    """Generate complete evaluation fingerprint."""
    os.chdir(os.getcwd())

    fingerprint = {
        "mandatory": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "git_commit": get_git_commit(),
            "git_branch": get_git_branch(),
            "python_version": get_python_version(),
            "virtual_environment": get_virtual_environment(),
            "installed_packages_hash": get_packages_hash(),
            "retrieval_py_hash": sha256_file("core/retrieval.py"),
            "query_enhancement_hash": sha256_file("core/query_enhancements.py"),
            "tsu_dataset_hash": get_tsu_dataset_hash()
        },
        "recommended": {
            "os_version": platform.platform(),
            "machine_architecture": platform.machine(),
            "embedding_model": get_embedding_model(),
            "config_hash": sha256_file("config.yaml"),
            "gold_query_version": get_gold_query_version()
        }
    }

    # Write to output file
    output_path = os.path.join(output_dir, "evaluation_fingerprint.json")
    with open(output_path, "w") as f:
        json.dump(fingerprint, f, indent=2)

    return fingerprint, output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate DBMA evaluation runtime fingerprint")
    parser.add_argument("--output-dir", default=".", help="Directory to write fingerprint.json")
    args = parser.parse_args()

    fp, path = generate_fingerprint(args.output_dir)

    print("=" * 60)
    print("DBMA Evaluation Fingerprint")
    print("=" * 60)
    print(f"\nOutput: {path}\n")

    print("--- MANDATORY ---")
    for k, v in fp["mandatory"].items():
        trunc = str(v)[:50] + "..." if len(str(v)) > 50 else str(v)
        print(f"  {k}: {trunc}")

    print(f"\n--- RECOMMENDED ---")
    for k, v in fp["recommended"].items():
        trunc = str(v)[:50] + "..." if len(str(v)) > 50 else str(v)
        print(f"  {k}: {trunc}")

    print(f"\n✅ Fingerprint written to {path}")