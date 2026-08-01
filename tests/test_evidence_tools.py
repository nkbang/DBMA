"""test_evidence_tools.py — End-to-end and failure-case tests for evidence tools.

Tests:
  (1) build_manifest + verify_manifest round-trip on a temp directory
  (2) build_seal + verify_package round-trip on a real git repo
  (3) verify_manifest fails on tampered file
  (4) verify_manifest fails on missing file
  (5) verify_manifest fails on extra undeclared file
  (6) build_manifest handles excluded files correctly
  (7) verify_package E2E success
  (8) verify_package seal not direct child of E
  (9) verify_package extra file in seal commit
  (10) verify_package payload_commit_sha mismatch
  (11) verify_package manifest-file mismatch
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts" / "evidence"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_manifest
import verify_manifest


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestBuildManifest(unittest.TestCase):
    """Test manifest generation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_evidence_")
        self.pkg_dir = Path(self.tmpdir) / "test_pkg_001"
        self.pkg_dir.mkdir()

        # Create some test files
        (self.pkg_dir / "report.md").write_text("# Test Report\n\nThis is a test.", encoding="utf-8")
        (self.pkg_dir / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        (self.pkg_dir / "notes.txt").write_text("Some notes here.", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_manifest_created(self):
        """manifest.json should be created in package root."""
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        result = subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertEqual(result.returncode, 0, f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertTrue((self.pkg_dir / "manifest.json").exists())

    def test_manifest_contains_all_files(self):
        """All non-excluded files should be in manifest."""
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        with open(self.pkg_dir / "manifest.json") as f:
            manifest = json.load(f)

        file_paths = {entry["path"] for entry in manifest["files"]}
        self.assertIn("report.md", file_paths)
        self.assertIn("data.json", file_paths)
        self.assertIn("notes.txt", file_paths)
        self.assertEqual(len(manifest["files"]), 3)

    def test_manifest_excludes_manifest_json(self):
        """manifest.json itself should be in excluded_paths, not files."""
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        with open(self.pkg_dir / "manifest.json") as f:
            manifest = json.load(f)

        file_paths = {entry["path"] for entry in manifest["files"]}
        self.assertNotIn("manifest.json", file_paths)
        self.assertIn("manifest.json", manifest["excluded_paths"])


class TestVerifyManifestRoundTrip(unittest.TestCase):
    """Test build_manifest + verify_manifest round-trip."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_evidence_")
        self.pkg_dir = Path(self.tmpdir) / "verify_pkg_001"
        self.pkg_dir.mkdir()

        (self.pkg_dir / "report.md").write_text("# Report\n\nContent.", encoding="utf-8")
        (self.pkg_dir / "data.json").write_text('{"a": 1}', encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_round_trip_passes(self):
        """Build then verify should pass."""
        # Build
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Verify
        verify_path = SCRIPTS_DIR / "verify_manifest.py"
        result = subprocess.run(
            [sys.executable, str(verify_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertEqual(result.returncode, 0, f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn("VERIFIED", result.stdout)


class TestVerifyManifestTampered(unittest.TestCase):
    """Test verify_manifest fails on tampered file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_evidence_")
        self.pkg_dir = Path(self.tmpdir) / "tamper_pkg_001"
        self.pkg_dir.mkdir()

        (self.pkg_dir / "report.md").write_text("# Original\n\nContent.", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_tampered_file_detected(self):
        """Modifying a file should cause verify to fail."""
        # Build manifest
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Tamper with the file
        (self.pkg_dir / "report.md").write_text("# TAMPERED\n\nChanged content!", encoding="utf-8")

        # Verify should fail
        verify_path = SCRIPTS_DIR / "verify_manifest.py"
        result = subprocess.run(
            [sys.executable, str(verify_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISMATCH", result.stdout)


class TestVerifyManifestMissingFile(unittest.TestCase):
    """Test verify_manifest fails on missing file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_evidence_")
        self.pkg_dir = Path(self.tmpdir) / "missing_pkg_001"
        self.pkg_dir.mkdir()

        (self.pkg_dir / "report.md").write_text("# Report\n\nContent.", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_file_detected(self):
        """Deleting a file should cause verify to fail."""
        # Build manifest
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Delete the file
        (self.pkg_dir / "report.md").unlink()

        # Verify should fail
        verify_path = SCRIPTS_DIR / "verify_manifest.py"
        result = subprocess.run(
            [sys.executable, str(verify_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISSING", result.stdout)


class TestVerifyManifestExtraFile(unittest.TestCase):
    """Test verify_manifest fails on undeclared file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_evidence_")
        self.pkg_dir = Path(self.tmpdir) / "extra_pkg_001"
        self.pkg_dir.mkdir()

        (self.pkg_dir / "report.md").write_text("# Report\n\nContent.", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_extra_file_detected(self):
        """Adding an undeclared file should cause verify to fail."""
        # Build manifest
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Add an extra file (not in manifest)
        (self.pkg_dir / "extra.txt").write_text("Extra content.", encoding="utf-8")

        # Verify should fail
        verify_path = SCRIPTS_DIR / "verify_manifest.py"
        result = subprocess.run(
            [sys.executable, str(verify_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNDECLARED", result.stdout)


class TestBuildSeal(unittest.TestCase):
    """Test seal generation in a real git repo."""

    def setUp(self):
        # Use the actual repo as test ground
        self.repo_root = Path(__file__).parent.parent
        self.tmpdir = tempfile.mkdtemp(prefix="test_seal_", dir=str(self.repo_root))
        self.pkg_dir = Path(self.tmpdir) / "seal_test_pkg"
        self.pkg_dir.mkdir()

        (self.pkg_dir / "report.md").write_text("# Seal Test\n\nContent.", encoding="utf-8")
        (self.pkg_dir / "data.json").write_text('{"test": true}', encoding="utf-8")

    def tearDown(self):
        # Clean up the temp directory
        if self.tmpdir.startswith(str(self.repo_root)):
            rel = self.tmpdir[len(str(self.repo_root)):].lstrip("/")
            shutil.rmtree(Path(rel), ignore_errors=True)

    def test_seal_created(self):
        """seal.json should be created with correct fields."""
        # First build manifest (required by seal)
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # Then create a commit for the payload
        subprocess.run(
            ["git", "add", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=self.repo_root
        )
        subprocess.run(
            ["git", "commit", "-m", "test payload seal_test"],
            capture_output=True, text=True, cwd=self.repo_root
        )

        # Get the commit SHA
        stdout = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=self.repo_root
        ).stdout

        payload_commit = stdout.strip()

        # Get the tree SHA
        tree_stdout = subprocess.run(
            ["git", "rev-parse", f"{payload_commit}^{{tree}}"],
            capture_output=True, text=True, cwd=self.repo_root
        ).stdout

        payload_tree = tree_stdout.strip()

        # Build seal
        seal_path = SCRIPTS_DIR / "build_seal.py"
        result = subprocess.run(
            [sys.executable, str(seal_path), "--package", str(self.pkg_dir),
             "--payload-commit", payload_commit, "--payload-tree", payload_tree],
            capture_output=True, text=True, cwd=self.repo_root
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        seal_file = self.pkg_dir / "seal.json"
        self.assertTrue(seal_file.exists())

        with open(seal_file) as f:
            seal = json.load(f)

        self.assertEqual(seal["payload_commit_sha"], payload_commit)
        self.assertEqual(seal["payload_tree_sha"], payload_tree)
        self.assertIsNone(seal["seal_commit_sha"])
        self.assertIn("manifest_sha256", seal)
        self.assertIn("sealed_at_utc", seal)


class TestManifestMediaType(unittest.TestCase):
    """Test media type inference."""

    def test_md_media_type(self):
        self.assertEqual(
            build_manifest.get_media_type(Path("test.md")),
            "text/markdown"
        )

    def test_json_media_type(self):
        self.assertEqual(
            build_manifest.get_media_type(Path("test.json")),
            "application/json"
        )

    def test_txt_media_type(self):
        self.assertEqual(
            build_manifest.get_media_type(Path("test.txt")),
            "text/plain"
        )

    def test_unknown_extension(self):
        self.assertEqual(
            build_manifest.get_media_type(Path("test.unknown")),
            "text/plain"
        )


class TestManifestSchemaVersion(unittest.TestCase):
    """Test manifest schema_version is correct."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_schema_")
        self.pkg_dir = Path(self.tmpdir) / "schema_pkg_001"
        self.pkg_dir.mkdir()
        (self.pkg_dir / "test.md").write_text("# Test", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_schema_version_is_1_1(self):
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        with open(self.pkg_dir / "manifest.json") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["schema_version"], "1.1")


# ─── verify_package.py 통합 테스트 (CUE 피드백: 실제 git repo 기반) ───


def _git_init(repo_path: Path):
    """새 git repo 초기화 + user config 설정."""
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "C1-Test"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "c1@test.dbma"], cwd=repo_path, capture_output=True, check=True)


def _git_add_commit(repo_path: Path, message: str, files: dict):
    """files: {경로: 내용} 딕셔너리를 받아서 add + commit.

    Returns: commit SHA.
    """
    for fpath, content in files.items():
        full = repo_path / fpath
        full.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            full.write_text(content, encoding="utf-8")
        else:
            full.write_bytes(content)
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    result = subprocess.run(
        ["git", "commit", "-m", message], cwd=repo_path, capture_output=True, text=True
    )
    # commit SHA 가져오기
    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, check=True
    )
    return sha_result.stdout.strip()


class TestVerifyPackageE2E(unittest.TestCase):
    """Test 1: 성공 케이스 — end-to-end flow."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="verify_e2e_")
        self.repo_root = Path(self.tmpdir) / "repo"
        self.repo_root.mkdir()
        _git_init(self.repo_root)

        # 더미 payload 파일들
        self.pkg_dir = self.repo_root / "evidence" / "TASK-001" / "PKG-E2E-001"
        self.pkg_dir.mkdir(parents=True)
        (self.pkg_dir / "payload.txt").write_text("dummy payload content", encoding="utf-8")
        (self.pkg_dir / "notes.md").write_text("# Notes\n\nTest evidence.", encoding="utf-8")

        # 1) build_manifest → manifest.json 생성
        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # 2) payload + manifest commit (E 커밋)
        self.e_commit = _git_add_commit(
            self.repo_root,
            "payload commit",
            {
                "evidence/TASK-001/PKG-E2E-001/payload.txt": "dummy payload content",
                "evidence/TASK-001/PKG-E2E-001/notes.md": "# Notes\n\nTest evidence.",
            }
        )

        # manifest.json을 읽어서 commit에 포함
        manifest_content = (self.pkg_dir / "manifest.json").read_text(encoding="utf-8")
        (self.repo_root / "evidence" / "TASK-001" / "PKG-E2E-001" / "manifest.json").write_text(
            manifest_content, encoding="utf-8"
        )
        subprocess.run(["git", "add", "evidence/TASK-001/PKG-E2E-001/manifest.json"],
                       cwd=self.repo_root, capture_output=True, check=True)
        result = subprocess.run(
            ["git", "commit", "--amend", "-m", "payload commit"],
            cwd=self.repo_root, capture_output=True, text=True
        )
        if result.returncode == 0:
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=self.repo_root, capture_output=True, text=True, check=True
            )
            self.e_commit = sha_result.stdout.strip()

        # tree SHA 계산
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{self.e_commit}^{{tree}}"],
            cwd=self.repo_root, capture_output=True, text=True, check=True
        )
        self.e_tree = tree_result.stdout.strip()

        # 3) seal.json 생성
        seal_path = SCRIPTS_DIR / "build_seal.py"
        subprocess.run(
            [sys.executable, str(seal_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--payload-tree", self.e_tree],
            capture_output=True, text=True, cwd=self.repo_root
        )

        # 4) seal commit (S 커밋)
        self.s_commit = _git_add_commit(
            self.repo_root,
            "seal commit",
            {"evidence/TASK-001/PKG-E2E-001/seal.json":
             (self.pkg_dir / "seal.json").read_text(encoding="utf-8")}
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_verify_package_success(self):
        """verify_package should pass on valid package."""
        verify_pkg_path = SCRIPTS_DIR / "verify_package.py"
        result = subprocess.run(
            [sys.executable, str(verify_pkg_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--seal-commit", self.s_commit],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertEqual(result.returncode, 0, f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn("VERIFIED", result.stdout)


class TestVerifyPackageSealNotDirectChild(unittest.TestCase):
    """Test 2: seal.json이 E의 직접 하위 파일이 아님."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="verify_seal_")
        self.repo_root = Path(self.tmpdir) / "repo"
        self.repo_root.mkdir()
        _git_init(self.repo_root)

        self.pkg_dir = self.repo_root / "evidence" / "TASK-002" / "PKG-SEAL-001"
        self.pkg_dir.mkdir(parents=True)
        (self.pkg_dir / "payload.txt").write_text("payload", encoding="utf-8")

        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        self.e_commit = _git_add_commit(
            self.repo_root, "payload commit",
            {"evidence/TASK-002/PKG-SEAL-001/payload.txt": "payload"}
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{self.e_commit}^{{tree}}"],
            cwd=self.repo_root, capture_output=True, text=True, check=True
        )
        self.e_tree = tree_result.stdout.strip()

        # seal.json을 서브디렉토리에 넣음 (잘못된 위치)
        # [CUE-RECONCILIATION-010] build_seal.py는 항상 pkg_dir 루트에
        # seal.json을 정상적으로 쓴다 — "잘못된 위치"를 만들려면 그 정상
        # 산출물을 subdir로 옮겨야 하는데, 원래 코드는 rename()의 출발지/
        # 목적지가 뒤바뀌어 있어(subdir 안의, 애초에 존재하지 않는
        # 파일에서 옮기려 시도) FileNotFoundError로 setUp 자체가 죽었다.
        bad_seal_dir = self.pkg_dir / "subdir"
        bad_seal_dir.mkdir()
        seal_path = SCRIPTS_DIR / "build_seal.py"
        subprocess.run(
            [sys.executable, str(seal_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--payload-tree", self.e_tree],
            capture_output=True, text=True, cwd=self.repo_root
        )
        # 정상적으로 pkg_dir 루트에 생성된 seal.json을 subdir로 이동
        (self.pkg_dir / "seal.json").rename(bad_seal_dir / "seal.json")
        # subdir 경로 그대로 git에 커밋 (seal.json이 E의 직접 하위가 아님)
        self.s_commit = _git_add_commit(
            self.repo_root, "seal commit",
            {"evidence/TASK-002/PKG-SEAL-001/subdir/seal.json":
             (bad_seal_dir / "seal.json").read_text(encoding="utf-8")}
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_seal_not_direct_child_detected(self):
        """Seal in subdirectory should fail verification.

        [CUE-RECONCILIATION-010] Asserts against verify_package.py's actual
        output — the literal string "SEAL_NOT_FOUND" is not part of its
        vocabulary; a seal.json committed under a subdirectory instead of
        directly under the package root is caught by the same seal-commit
        scope check as an extra file ("unexpected file: .../subdir/seal.json"
        under "BLOCKED — INVALID SEAL COMMIT SCOPE").
        """
        verify_pkg_path = SCRIPTS_DIR / "verify_package.py"
        result = subprocess.run(
            [sys.executable, str(verify_pkg_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--seal-commit", self.s_commit],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected file", result.stdout)
        self.assertIn("subdir/seal.json", result.stdout)
        self.assertIn("BLOCKED", result.stdout)


class TestVerifyPackageExtraFileInSealCommit(unittest.TestCase):
    """Test 3: seal commit에 payload 파일이 추가됨."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="verify_extra_")
        self.repo_root = Path(self.tmpdir) / "repo"
        self.repo_root.mkdir()
        _git_init(self.repo_root)

        self.pkg_dir = self.repo_root / "evidence" / "TASK-003" / "PKG-EXTRA-001"
        self.pkg_dir.mkdir(parents=True)
        (self.pkg_dir / "payload.txt").write_text("payload", encoding="utf-8")

        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        self.e_commit = _git_add_commit(
            self.repo_root, "payload commit",
            {"evidence/TASK-003/PKG-EXTRA-001/payload.txt": "payload"}
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{self.e_commit}^{{tree}}"],
            cwd=self.repo_root, capture_output=True, text=True, check=True
        )
        self.e_tree = tree_result.stdout.strip()

        seal_path = SCRIPTS_DIR / "build_seal.py"
        subprocess.run(
            [sys.executable, str(seal_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--payload-tree", self.e_tree],
            capture_output=True, text=True, cwd=self.repo_root
        )

        # seal commit 시 extra.txt 추가
        self.s_commit = _git_add_commit(
            self.repo_root, "seal commit",
            {
                "evidence/TASK-003/PKG-EXTRA-001/seal.json":
                    (self.pkg_dir / "seal.json").read_text(encoding="utf-8"),
                "evidence/TASK-003/PKG-EXTRA-001/extra.txt": "extra content",
            }
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extra_file_in_seal_commit_detected(self):
        """Extra file in seal commit should fail verification.

        [CUE-RECONCILIATION-010] Asserts against verify_package.py's actual
        output — the literal string "EXTRA_FILE" is not part of its
        vocabulary; the real failure is "unexpected file: .../extra.txt"
        under a "BLOCKED — INVALID SEAL COMMIT SCOPE" banner.
        """
        verify_pkg_path = SCRIPTS_DIR / "verify_package.py"
        result = subprocess.run(
            [sys.executable, str(verify_pkg_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--seal-commit", self.s_commit],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected file", result.stdout)
        self.assertIn("extra.txt", result.stdout)
        self.assertIn("BLOCKED", result.stdout)


class TestVerifyPackagePayloadCommitMismatch(unittest.TestCase):
    """Test 4: payload_commit_sha 불일치."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="verify_commit_")
        self.repo_root = Path(self.tmpdir) / "repo"
        self.repo_root.mkdir()
        _git_init(self.repo_root)

        self.pkg_dir = self.repo_root / "evidence" / "TASK-004" / "PKG-COMMIT-001"
        self.pkg_dir.mkdir(parents=True)
        (self.pkg_dir / "payload.txt").write_text("payload", encoding="utf-8")

        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        self.e_commit = _git_add_commit(
            self.repo_root, "payload commit",
            {"evidence/TASK-004/PKG-COMMIT-001/payload.txt": "payload"}
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{self.e_commit}^{{tree}}"],
            cwd=self.repo_root, capture_output=True, text=True, check=True
        )
        self.e_tree = tree_result.stdout.strip()

        # seal.json에 잘못된 commit SHA 쓰기
        seal_data = {
            "schema_version": "1.1",
            "payload_commit_sha": "a" * 40,  # 잘못된 SHA
            "payload_tree_sha": self.e_tree,
            "manifest_sha256": "b" * 64,
            "sealed_at_utc": "2026-08-01T00:00:00Z",
            "seal_commit_sha": None,
        }
        (self.pkg_dir / "seal.json").write_text(json.dumps(seal_data, indent=2), encoding="utf-8")

        self.s_commit = _git_add_commit(
            self.repo_root, "seal commit",
            {"evidence/TASK-004/PKG-COMMIT-001/seal.json":
             json.dumps(seal_data, indent=2, ensure_ascii=False)}
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_payload_commit_mismatch_detected(self):
        """Wrong payload_commit_sha should fail verification.

        [CUE-RECONCILIATION-010] Asserts against verify_package.py's actual
        output — the literal string "COMMIT_MISMATCH" is not part of its
        vocabulary (the standard's §12 lists block *reasons* in prose, not
        fixed machine-readable codes); the real failure is reported as
        "FAIL 6: seal.json.payload_commit_sha (...) != E" under a
        "PACKAGE SEAL INVALID — BLOCKED" banner.
        """
        verify_pkg_path = SCRIPTS_DIR / "verify_package.py"
        result = subprocess.run(
            [sys.executable, str(verify_pkg_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--seal-commit", self.s_commit],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL 6", result.stdout)
        self.assertIn("payload_commit_sha", result.stdout)
        self.assertIn("BLOCKED", result.stdout)


class TestVerifyPackageManifestFileMismatch(unittest.TestCase):
    """Test 5: manifest.json의 파일 해시 불일치."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="verify_hash_")
        self.repo_root = Path(self.tmpdir) / "repo"
        self.repo_root.mkdir()
        _git_init(self.repo_root)

        self.pkg_dir = self.repo_root / "evidence" / "TASK-005" / "PKG-HASH-001"
        self.pkg_dir.mkdir(parents=True)
        (self.pkg_dir / "payload.txt").write_text("original content", encoding="utf-8")

        manifest_path = SCRIPTS_DIR / "build_manifest.py"
        subprocess.run(
            [sys.executable, str(manifest_path), "--package", str(self.pkg_dir)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        # manifest.json의 payload.txt 해시를 조작 — *커밋 E 이전에* 조작해야
        # 조작된 manifest.json이 E의 일부로 들어가고, verify_package.py의
        # item 9-b(manifest 기재 해시 vs 실제 파일 해시 대조)가 실행된다.
        # (원래는 이 조작을 E 커밋 이후, S 커밋에서 manifest.json을 뒤늦게
        # 추가하는 방식으로 했으나, 그러면 E에 manifest.json이 아예 없어
        # "seal commit 범위 위반"으로 먼저 걸려 의도한 해시-불일치 코드
        # 경로에 도달하지 못했다 — CUE-RECONCILIATION-010에서 발견/수정.)
        with open(self.pkg_dir / "manifest.json") as f:
            manifest = json.load(f)
        for entry in manifest["files"]:
            if entry["path"] == "payload.txt":
                entry["sha256"] = "c" * 64  # 잘못된 해시
        with open(self.pkg_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")

        self.e_commit = _git_add_commit(
            self.repo_root, "payload commit",
            {
                "evidence/TASK-005/PKG-HASH-001/payload.txt": "original content",
                "evidence/TASK-005/PKG-HASH-001/manifest.json":
                    (self.pkg_dir / "manifest.json").read_text(encoding="utf-8"),
            }
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{self.e_commit}^{{tree}}"],
            cwd=self.repo_root, capture_output=True, text=True, check=True
        )
        self.e_tree = tree_result.stdout.strip()

        # build_seal.py는 (이미 조작된) manifest.json 내용으로부터
        # manifest_sha256을 계산하므로, item 8(seal.json.manifest_sha256 ==
        # E:manifest.json)은 정합성 있게 PASS하고, item 9-b(개별 파일 해시
        # 불일치)에서만 실패해야 이 테스트가 실제로 의도한 경로를 검증한다.
        seal_path = SCRIPTS_DIR / "build_seal.py"
        subprocess.run(
            [sys.executable, str(seal_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--payload-tree", self.e_tree],
            capture_output=True, text=True, cwd=self.repo_root
        )

        self.s_commit = _git_add_commit(
            self.repo_root, "seal commit",
            {
                "evidence/TASK-005/PKG-HASH-001/seal.json":
                    (self.pkg_dir / "seal.json").read_text(encoding="utf-8"),
            }
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_manifest_file_hash_mismatch_detected(self):
        """Tampered manifest file hash should fail verification.

        [CUE-RECONCILIATION-010] Asserts against verify_package.py's actual
        output — the literal string "MANIFEST_MISMATCH" is not part of its
        vocabulary; the real failure is reported as "SHA256 mismatch:
        payload.txt (manifest=..., actual=...)" under a
        "BLOCKED — MANIFEST PAYLOAD SET MISMATCH" banner (item 9-b).
        """
        verify_pkg_path = SCRIPTS_DIR / "verify_package.py"
        result = subprocess.run(
            [sys.executable, str(verify_pkg_path), "--package", str(self.pkg_dir),
             "--payload-commit", self.e_commit, "--seal-commit", self.s_commit],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA256 mismatch", result.stdout)
        self.assertIn("payload.txt", result.stdout)
        self.assertIn("BLOCKED", result.stdout)


if __name__ == "__main__":
    unittest.main()