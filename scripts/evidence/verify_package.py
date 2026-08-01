#!/usr/bin/env python3
"""verify_package.py — Verify Evidence Package seal per Evidence Package Standard v1.1 §7.

Usage:
    python -m scripts.evidence.verify_package --package evidence/<TASK-ID>/<PACKAGE-ID> \
      --payload-commit <E-SHA> --seal-commit <S-SHA>
    python scripts/evidence/verify_package.py --package evidence/<TASK-ID>/<PACKAGE-ID> \
      --payload-commit <E-SHA> --seal-commit <S-SHA>

Checks all 10 items in order. Reports all failures (does not stop on first).
Uses git tree operations (git show / git ls-tree) to inspect the E commit's
tree, NOT the working directory. This is the core security property: it catches
tampering of files after the payload commit was made.

Exit code: 0 if all 10 items pass, 1 if any fail.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def run_git(args: list, cwd: Path = Path(".")) -> tuple:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def git_show_file(repo_root: Path, commit: str, file_path: str) -> bytes:
    """Read a file from a git commit. Returns raw bytes."""
    rc, stdout, stderr = run_git(
        ["show", f"{commit}:{file_path}"], cwd=repo_root
    )
    if rc != 0:
        raise FileNotFoundError(
            f"File {file_path} not found in commit {commit}: {stderr.strip()}"
        )
    # git show outputs text; we need raw bytes for SHA256
    # Re-run with binary output
    # [CUE-RECONCILIATION-010] was missing the "git" executable prefix —
    # ran the literal command "show" instead of "git show", so this call
    # always failed and every caller (item 8/9 manifest hash checks) always
    # hit the FileNotFoundError branch below regardless of the file's real
    # presence in the commit.
    result = subprocess.run(
        ["git", "show", "-p", f"{commit}:{file_path}"],
        capture_output=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise FileNotFoundError(
            f"File {file_path} not found in commit {commit}: {result.stderr.decode().strip()}"
        )
    return result.stdout


def git_ls_tree_files(repo_root: Path, commit: str, package_root_rel: str) -> list:
    """List all files under package_root in a git commit.

    Returns:
        List of (rel_path, blob_sha, size) tuples.
    """
    rc, stdout, stderr = run_git(
        ["ls-tree", "-r", f"{commit}:{package_root_rel}"], cwd=repo_root
    )
    if rc != 0:
        return []

    files = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        # Format: <mode> <type> <blob_sha>\t<file_path>
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        meta = parts[0].split()
        blob_sha = meta[2]
        file_path = parts[1]
        files.append((file_path, blob_sha))
    return files


def git_diff_name_status(repo_root: Path, commit_a: str, commit_b: str) -> str:
    """Run git diff --name-status between two commits. Returns the output string."""
    rc, stdout, stderr = run_git(
        ["diff", "--name-status", commit_a, commit_b], cwd=repo_root
    )
    if rc != 0:
        return ""
    return stdout


def git_rev_parse(repo_root: Path, ref: str) -> str:
    """Run git rev-parse <ref>. Returns the SHA string."""
    rc, stdout, stderr = run_git(["rev-parse", ref], cwd=repo_root)
    if rc != 0:
        return ""
    return stdout.strip()


def verify_package(package_root: Path, payload_commit: str, seal_commit: str) -> tuple:
    """Verify all 10 items per standard §7.

    Returns:
        (success: bool, results: list[str])
    """
    package_root = package_root.resolve()
    repo_root = package_root  # Assume git repo is at or above package root
    # Find actual git repo root
    rc, stdout, stderr = run_git(["rev-parse", "--show-toplevel"], cwd=package_root)
    if rc == 0:
        repo_root = Path(stdout.strip())
    else:
        # Not a git repo — can't verify
        return False, ["FATAL: Not a git repository"]

    results = []
    all_passed = True

    # --- Item 1: E commit exists ---
    rc, _, _ = run_git(["cat-file", "-e", payload_commit], cwd=repo_root)
    if rc == 0:
        results.append(f"[PASS] 1. Payload commit E exists: {payload_commit[:12]}")
    else:
        results.append(
            f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
            f"  FAIL 1: Payload commit E does not exist: {payload_commit}"
        )
        all_passed = False

    # --- Item 2: S commit exists ---
    rc, _, _ = run_git(["cat-file", "-e", seal_commit], cwd=repo_root)
    if rc == 0:
        results.append(f"[PASS] 2. Seal commit S exists: {seal_commit[:12]}")
    else:
        results.append(
            f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
            f"  FAIL 2: Seal commit S does not exist: {seal_commit}"
        )
        all_passed = False

    # --- Item 3: S's direct parent is E ---
    if all_passed:
        s_parent = git_rev_parse(repo_root, f"{seal_commit}^")
        if s_parent == payload_commit:
            results.append(f"[PASS] 3. Seal commit S's parent is E: {s_parent[:12]}")
        else:
            results.append(
                f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
                f"  FAIL 3: Seal commit S's parent ({s_parent[:12]}) != E ({payload_commit[:12]})"
            )
            all_passed = False

    # --- Item 4 & 5: git diff --name-status between E and S ---
    if all_passed:
        diff_output = git_diff_name_status(repo_root, payload_commit, seal_commit)
        lines = [l for l in diff_output.strip().split("\n") if l]

        expected_path = str(package_root.relative_to(repo_root)) + "/seal.json"
        expected_line = f"A\t{expected_path}"

        if len(lines) == 1 and lines[0] == expected_line:
            results.append(f"[PASS] 4. Seal commit scope: exactly one file added ({expected_path})")
            results.append(f"[PASS] 5. seal.json is newly added (A) in seal commit")
        else:
            # Determine what went wrong
            issues = []
            if len(lines) != 1:
                issues.append(f"expected 1 changed file, got {len(lines)}")
            for line in lines:
                if line != expected_line:
                    status, fpath = line.split("\t", 1) if "\t" in line else ("?", line)
                    if status != "A":
                        issues.append(f"unexpected change: {status}\t{fpath}")
                    elif fpath != expected_path:
                        issues.append(f"unexpected file: {fpath}")
            results.append(
                f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
                f"  FAIL 4/5: Seal commit scope mismatch (expected only 'A\\t{expected_path}')"
            )
            for issue in issues:
                results.append(f"    {issue}")
            all_passed = False

    # --- Item 6: seal.json.payload_commit_sha == E ---
    if all_passed:
        seal_path = package_root / "seal.json"
        with open(seal_path, "r", encoding="utf-8") as f:
            seal = json.load(f)
        if seal.get("payload_commit_sha") == payload_commit:
            results.append(f"[PASS] 6. seal.json.payload_commit_sha matches E")
        else:
            results.append(
                f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
                f"  FAIL 6: seal.json.payload_commit_sha ({seal.get('payload_commit_sha', 'MISSING')[:12] if seal.get('payload_commit_sha') else 'MISSING'}) != E"
            )
            all_passed = False

    # --- Item 7: seal.json.payload_tree_sha == E^{tree} ---
    if all_passed:
        e_tree = git_rev_parse(repo_root, f"{payload_commit}^{{tree}}")
        with open(package_root / "seal.json", "r", encoding="utf-8") as f:
            seal = json.load(f)
        if seal.get("payload_tree_sha") == e_tree:
            results.append(f"[PASS] 7. seal.json.payload_tree_sha matches E's tree")
        else:
            results.append(
                f"BLOCKED — INVALID SEAL COMMIT SCOPE\n"
                f"  FAIL 7: seal.json.payload_tree_sha ({seal.get('payload_tree_sha', 'MISSING')[:12] if seal.get('payload_tree_sha') else 'MISSING'}) != E's tree ({e_tree[:12] if e_tree else 'N/A'})"
            )
            all_passed = False

    # --- Item 8: seal.json.manifest_sha256 == E:manifest.json SHA256 ---
    if all_passed:
        with open(package_root / "seal.json", "r", encoding="utf-8") as f:
            seal = json.load(f)
        # Read manifest.json from the E commit's tree
        manifest_rel = str(package_root.relative_to(repo_root)) + "/manifest.json"
        try:
            manifest_bytes = git_show_file(repo_root, payload_commit, manifest_rel)
        except FileNotFoundError:
            results.append(
                f"BLOCKED — MANIFEST PAYLOAD SET MISMATCH\n"
                f"  FAIL 8: manifest.json not found in commit E at {manifest_rel}"
            )
            all_passed = False
            manifest_bytes = None

        if manifest_bytes is not None:
            actual_manifest_sha = compute_sha256_bytes(manifest_bytes)
            declared_manifest_sha = seal.get("manifest_sha256", "")
            if actual_manifest_sha == declared_manifest_sha:
                results.append(f"[PASS] 8. seal.json.manifest_sha256 matches E:manifest.json")
            else:
                results.append(
                    f"BLOCKED — MANIFEST PAYLOAD SET MISMATCH\n"
                    f"  FAIL 8: manifest_sha256 mismatch "
                    f"(declared={declared_manifest_sha[:16]}..., actual={actual_manifest_sha[:16]}...)"
                )
                all_passed = False

    # --- Item 9: Manifest bidirectional completeness (against E commit tree) ---
    if all_passed:
        with open(package_root / "seal.json", "r", encoding="utf-8") as f:
            seal = json.load(f)
        manifest_rel = str(package_root.relative_to(repo_root)) + "/manifest.json"

        # Load manifest from E commit
        try:
            manifest_bytes = git_show_file(repo_root, payload_commit, manifest_rel)
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            results.append(
                f"BLOCKED — MANIFEST PAYLOAD SET MISMATCH\n"
                f"  FAIL 9: Cannot read manifest from E commit: {exc}"
            )
            all_passed = False
            manifest = None

        if manifest is not None:
            manifest_files = {}
            for entry in manifest.get("files", []):
                manifest_files[entry["path"]] = entry

            excluded = set(manifest.get("excluded_paths", [])) | {"manifest.json", "seal.json"}

            # 9-a: Get all files in E's package root via git ls-tree
            pkg_rel = str(package_root.relative_to(repo_root))
            tree_files = git_ls_tree_files(repo_root, payload_commit, pkg_rel)

            actual_in_tree = set()
            for fpath, blob_sha in tree_files:
                if fpath in excluded:
                    continue
                actual_in_tree.add(fpath)

            manifest_declared = set(manifest_files.keys())

            # Check 9-a: every file in tree is in manifest
            missing_from_manifest = actual_in_tree - manifest_declared
            # Check 9-b: every manifest entry exists in tree with correct size/sha256
            errors_9b = []
            for fpath, entry in manifest_files.items():
                if fpath not in actual_in_tree:
                    errors_9b.append(f"MISSING in tree: {fpath}")
                    continue
                # Verify SHA256 by reading from git tree
                blob_rel = str(package_root.relative_to(repo_root)) + "/" + fpath
                try:
                    file_bytes = git_show_file(repo_root, payload_commit, blob_rel)
                    actual_sha = compute_sha256_bytes(file_bytes)
                    if actual_sha != entry["sha256"]:
                        errors_9b.append(
                            f"SHA256 mismatch: {fpath} "
                            f"(manifest={entry['sha256'][:16]}..., actual={actual_sha[:16]}...)"
                        )
                except FileNotFoundError:
                    errors_9b.append(f"NOT FOUND in tree: {fpath}")

            all_9_errors = []
            for p in sorted(missing_from_manifest):
                all_9_errors.append(f"  9-a UNDECLARED: {p}")
            for e in errors_9b:
                all_9_errors.append(f"  9-b {e}")

            if missing_from_manifest or errors_9b:
                results.append(
                    "BLOCKED — MANIFEST PAYLOAD SET MISMATCH\n"
                    f"  FAIL 9: Manifest bidirectional completeness check failed:"
                )
                all_9_errors_sorted = sorted(all_9_errors)
                for err in all_9_errors_sorted:
                    results.append(err)
                all_passed = False
            else:
                results.append(f"[PASS] 9. Manifest bidirectional completeness verified (against E tree)")

    # --- Item 10: package_id and package root string match ---
    if all_passed:
        with open(package_root / "seal.json", "r", encoding="utf-8") as f:
            seal = json.load(f)
        with open(package_root / "manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)

        seal_pkg_id = seal.get("package_id", "")
        manifest_pkg_id = manifest.get("package_id", "")
        pkg_root_name = package_root.name

        errors_10 = []
        if seal_pkg_id != manifest_pkg_id:
            errors_10.append(
                f"package_id mismatch: seal={seal_pkg_id}, manifest={manifest_pkg_id}"
            )
        if seal_pkg_id != pkg_root_name:
            errors_10.append(
                f"package_id mismatch: seal={seal_pkg_id}, package_root={pkg_root_name}"
            )

        if not errors_10:
            results.append(f"[PASS] 10. package_id consistent across seal.json, manifest.json, and package root")
        else:
            results.append("BLOCKED — MANIFEST PAYLOAD SET MISMATCH\n  FAIL 10:")
            for e in errors_10:
                results.append(f"    {e}")
            all_passed = False

    return all_passed, results


def main():
    parser = argparse.ArgumentParser(
        description="Verify Evidence Package seal per standard §7."
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
        "--seal-commit",
        required=True,
        help="Git commit SHA of the seal commit (S)",
    )
    args = parser.parse_args()

    package_root = Path(args.package)

    if not package_root.is_dir():
        print(f"ERROR: Package root does not exist: {package_root}", file=sys.stderr)
        sys.exit(1)

    success, results = verify_package(package_root, args.payload_commit, args.seal_commit)

    for line in results:
        print(line)

    if success:
        print()
        print("=" * 60)
        print("PACKAGE SEAL VERIFIED")
        print(f"  Payload commit (E): {args.payload_commit}")
        print(f"  Seal commit (S):    {args.seal_commit}")
        print(f"  Package root:       {package_root}")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("PACKAGE SEAL INVALID — BLOCKED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()