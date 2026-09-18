#!/usr/bin/env python
"""scripts/reset_workspace.py — 배포 전 튜닝용 티어드 워크스페이스 리셋.

ADR-033 (Workspace Reset Utility) 구현. 즉석 `rm` 대신 재현·추적 가능한
리셋을 반복 실행하기 위한 도구.

티어 (ADR-033 §2.1):
  T1  파생물만        — output/, chroma_db/, cache/, NAE/corpus/embeddings/,
                        data/제련완성본/ 의 파생 확장자, data/normalized·processed
  T2  + 중간 코퍼스   — T1 + NAE/corpus/tsu/(비추적분), manifests/, quarantine/,
                        NAE/benchmark/, (옵션) Qdrant 컬렉션 drop
  T3  + RAW/소스      — 설계만, 구현하지 않음 (HQ 결정 2026-09-07)

안전장치 (ADR-033 §2.2 / §2.3):
  - dry-run 기본. 실제 삭제는 --apply + 정확한 확인 문구.
  - 2-층위 보호: (A) git 추적 파일 전체, (B) 명시 prefix 목록.
    gitignore된 RAW/소스는 (B)에 필수 — config에서 빠지면 하드코딩값 강제 복원.
  - hard rm 대신 backups/reset_<UTC ts>/ 로 이동 (--hard 시에만 완전 삭제).
  - 삭제 매니페스트 JSON 기록.
  - 추적 파일에 uncommitted 변경 있으면 중단 (--force 로만 우회).
  - 삭제 대상에 git 추적 파일이 남으면 ABORT (ADR-030 FROZEN baseline 보호).

Usage:
    python scripts/reset_workspace.py --tier T1                 # dry-run
    python scripts/reset_workspace.py --tier T1 --apply         # "RESET T1" 입력
    python scripts/reset_workspace.py --tier T2 --apply --drop-qdrant
    python scripts/reset_workspace.py --tier T2 --apply \\
        --yes-i-mean-it --confirm "RESET T2 INCLUDING CORPUS"   # 비대화형
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ── 상수 (ADR-033) ──────────────────────────────────────────────────────

#: 확인 문구 — 코드 하드코딩, config 재정의 불가 (ADR-033 §2.3 #2)
CONFIRM_PHRASES: dict[str, str] = {
    "T1": "RESET T1",
    "T2": "RESET T2 INCLUDING CORPUS",
}

#: 층위 B 중 RAW/소스 — config에서 빠져도 강제 복원 (ADR-033 §2.2 규칙)
RAW_SOURCE_PREFIXES: tuple[str, ...] = (
    "data/RAW/",
    "NAE/corpus/raw/",
    "data/bible/",
    "sermon_corpus/",
    "data/sermon_corpus/",
    "data/beta_corpus/",
)

#: 층위 B 하드코딩 fallback 전체 (ADR-033 §2.2 / §2.4)
HARDCODED_PROTECTED_PREFIXES: tuple[str, ...] = RAW_SOURCE_PREFIXES + (
    ".git",
    "core/",
    "ui/",
    "scripts/",
    "tests/",
    "docs/",
    "NAE/pipeline/",
    "NAE/authority/",
    "NAE/governance/",
    "config.yaml",
    ".env",
)

#: 티어별 삭제 후보 glob fallback (config.reset.tiers 로 재정의 가능)
HARDCODED_TIER_GLOBS: dict[str, list[str]] = {
    "T1": [
        "output/*",
        "chroma_db/*",
        "cache/*",
        "NAE/corpus/embeddings/*",
        "data/제련완성본/*_pdf.md",
        "data/제련완성본/*_chunks.txt",
        "data/제련완성본/*_chunks_meta.json",
        "data/제련완성본/*_pdf_chunks*.json",
        "data/normalized/*",
        "data/processed/*",
        "data/nae/*",
        "data/inbox/*",
        "reports/*",
        "evidence/*",
    ],
    "T2": [
        "NAE/corpus/tsu/*",
        "NAE/corpus/manifests/*",
        "NAE/corpus/quarantine/*",
        "NAE/benchmark/*",
    ],
}

#: T2 이상에서 Qdrant drop이 건드릴 수 있는 상한 (config whitelist는 이 안에서만 유효)
BACKUP_ROOT_NAME = "backups"


def _log(msg: str) -> None:
    print(f"[reset] {msg}")


# ── config ─────────────────────────────────────────────────────────────


def load_reset_config(config_path: Path) -> dict[str, Any]:
    """config.yaml 의 `reset:` 섹션만 읽어 반환. 없으면 빈 dict."""
    if not config_path.exists():
        return {}
    try:
        import yaml
    except ImportError:  # pragma: no cover - yaml is a hard dep elsewhere
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    section = loaded.get("reset", {}) if isinstance(loaded, dict) else {}
    return section if isinstance(section, dict) else {}


def resolve_protected_prefixes(reset_cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    """층위 B prefix 목록을 확정한다.

    config 값에 RAW/소스 prefix가 빠져 있으면 경고 후 하드코딩값을 강제
    병합한다 (ADR-033 §2.2). 반환: (최종 prefix 목록, 강제 복원된 항목).
    """
    cfg_prefixes = reset_cfg.get("protected_prefixes")
    if not isinstance(cfg_prefixes, list) or not cfg_prefixes:
        return list(HARDCODED_PROTECTED_PREFIXES), []

    normalized = [str(p).strip() for p in cfg_prefixes if str(p).strip()]
    restored: list[str] = []
    for raw in RAW_SOURCE_PREFIXES:
        if raw not in normalized:
            normalized.append(raw)
            restored.append(raw)
    if restored:
        _log(
            "WARNING: config reset.protected_prefixes 에서 RAW/소스 보호 항목이 "
            f"빠져 있어 강제 복원함: {', '.join(restored)} "
            "(ADR-033 §2.2 — Amendment 없이 제거 금지)"
        )
    return normalized, restored


def resolve_tier_globs(reset_cfg: dict[str, Any], tier: str) -> list[str]:
    """해당 티어의 삭제 후보 glob 목록 (T2는 T1을 누적 포함)."""
    cfg_tiers = reset_cfg.get("tiers", {})
    cfg_tiers = cfg_tiers if isinstance(cfg_tiers, dict) else {}

    def _for(t: str) -> list[str]:
        val = cfg_tiers.get(t)
        if isinstance(val, list) and val:
            return [str(g).strip() for g in val if str(g).strip()]
        return list(HARDCODED_TIER_GLOBS.get(t, []))

    if tier == "T1":
        return _for("T1")
    if tier == "T2":
        return _for("T1") + _for("T2")
    raise ValueError(f"지원하지 않는 티어: {tier}")


# ── git ────────────────────────────────────────────────────────────────


def _git(project_root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(project_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout


def git_tracked_files(project_root: Path) -> set[str]:
    """`git ls-files` 결과를 project_root 기준 상대 POSIX 경로 set 으로."""
    raw = _git(project_root, "ls-files")
    return {line.strip() for line in raw.splitlines() if line.strip()}


def git_branch(project_root: Path) -> str:
    return _git(project_root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def git_head(project_root: Path) -> str:
    return _git(project_root, "rev-parse", "HEAD").strip()


def git_tracked_dirty(project_root: Path) -> list[str]:
    """추적 파일 중 uncommitted 변경(스테이징 포함) 목록. `??`(untracked)는 제외."""
    raw = _git(project_root, "status", "--porcelain")
    dirty: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, _, path = line[:2], line[2], line[3:]
        if status == "??":
            continue
        dirty.append(path.strip())
    return dirty


# ── 후보 산출 / 보호 판정 ─────────────────────────────────────────────


def _rel_posix(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def expand_candidates(project_root: Path, globs: Iterable[str]) -> list[Path]:
    """glob 목록을 실제 파일 경로 목록으로 확장 (디렉터리는 재귀 파일 전개).

    `.gitkeep` 과 매니페스트/백업 루트는 후보에서 제외한다.
    """
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in globs:
        for match in sorted(project_root.glob(pattern)):
            files = [match] if match.is_file() else sorted(
                p for p in match.rglob("*") if p.is_file()
            )
            for f in files:
                if f in seen:
                    continue
                rel = _rel_posix(f, project_root)
                if f.name == ".gitkeep":
                    continue
                if rel.startswith(f"{BACKUP_ROOT_NAME}/"):
                    continue
                seen.add(f)
                out.append(f)
    return out


def is_protected(
    rel_path: str,
    protected_prefixes: Iterable[str],
    tracked: set[str],
) -> str | None:
    """보호 사유 문자열을 반환 (보호되지 않으면 None).

    층위 A: git 추적 파일.  층위 B: prefix 매칭.
    """
    if rel_path in tracked:
        return "tracked (layer A)"
    for prefix in protected_prefixes:
        if prefix.endswith("/"):
            if rel_path == prefix.rstrip("/") or rel_path.startswith(prefix):
                return f"prefix {prefix} (layer B)"
        else:
            # 파일명 또는 디렉터리명 정확 매칭
            if rel_path == prefix or rel_path.startswith(f"{prefix}/"):
                return f"prefix {prefix} (layer B)"
    return None


class ResetAbort(RuntimeError):
    """되돌릴 수 없는 위험 상태 — 삭제 없이 중단."""


def partition_candidates(
    candidates: list[Path],
    project_root: Path,
    protected_prefixes: Iterable[str],
    tracked: set[str],
) -> tuple[list[Path], list[tuple[str, str]]]:
    """(삭제 대상, [(보호된 상대경로, 사유)]) 로 분할.

    분할 후 삭제 대상에 git 추적 파일이 하나라도 남으면 ResetAbort
    (ADR-033 §2.1 — ADR-030 FROZEN baseline 보호 불변식).
    """
    protected_prefixes = list(protected_prefixes)
    to_delete: list[Path] = []
    skipped: list[tuple[str, str]] = []
    for path in candidates:
        rel = _rel_posix(path, project_root)
        reason = is_protected(rel, protected_prefixes, tracked)
        if reason:
            skipped.append((rel, reason))
        else:
            to_delete.append(path)

    leaked = [_rel_posix(p, project_root) for p in to_delete if _rel_posix(p, project_root) in tracked]
    if leaked:
        raise ResetAbort(
            "ABORT: tracked file in delete set — "
            + ", ".join(leaked[:10])
            + (" ..." if len(leaked) > 10 else "")
        )
    return to_delete, skipped


# ── Qdrant (ADR-033 §4.4) ────────────────────────────────────────────


def resolve_qdrant_whitelist(reset_cfg: dict[str, Any]) -> list[str]:
    wl = reset_cfg.get("qdrant_collection_whitelist")
    if not isinstance(wl, list):
        return []
    return [str(c).strip() for c in wl if str(c).strip()]


def drop_qdrant_collections(
    url: str,
    whitelist: list[str],
    *,
    apply: bool,
) -> list[str]:
    """whitelist 에 정확히 일치하는 컬렉션만 drop. 반환: 실제(또는 예정) drop 목록.

    whitelist 가 비어 있으면 아무것도 하지 않는다 (기본값).
    """
    if not whitelist:
        _log("qdrant: whitelist 비어 있음 — drop 건너뜀 (ADR-033 §4.4)")
        return []
    if not apply:
        _log(f"qdrant: (dry-run) drop 예정 = {whitelist} @ {url}")
        return list(whitelist)

    try:
        from qdrant_client import QdrantClient  # type: ignore
    except ImportError:
        _log("qdrant: qdrant_client 미설치 — drop 건너뜀")
        return []

    client = QdrantClient(url=url)
    existing = {c.name for c in client.get_collections().collections}
    dropped: list[str] = []
    for name in whitelist:
        if name not in existing:
            _log(f"qdrant: '{name}' 없음 — 건너뜀")
            continue
        client.delete_collection(collection_name=name)
        dropped.append(name)
        _log(f"qdrant: dropped '{name}'")
    return dropped


# ── 실행 ───────────────────────────────────────────────────────────────


def _human_bytes(n: int) -> str:
    f = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if f < 1024 or unit == "T":
            return f"{f:.1f}{unit}"
        f /= 1024
    return f"{f:.1f}T"


def _dir_size(path: Path) -> int:
    return path.stat().st_size


def run_reset(
    *,
    project_root: Path,
    config_path: Path,
    tier: str,
    apply: bool = False,
    hard: bool = False,
    force: bool = False,
    drop_qdrant: bool = False,
    confirm: str | None = None,
    non_interactive: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """리셋 1회 실행. dry-run 이면 삭제 없이 계획만 반환.

    반환값은 매니페스트 dict (apply 시 backups/reset_<ts>/manifest.json 에도 기록).
    """
    project_root = project_root.resolve()
    if tier == "T3":
        raise ResetAbort(
            "T3 (RAW/소스 삭제)는 설계만 — 구현하지 않음 (ADR-033 §2.1). "
            "필요 시 scripts/reset_for_beta.py 를 별도 승인 후 사용."
        )
    if tier not in ("T1", "T2"):
        raise ValueError(f"--tier 는 T1 또는 T2 (받음: {tier!r})")

    now = now or datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")

    reset_cfg = load_reset_config(config_path)
    protected_prefixes, restored = resolve_protected_prefixes(reset_cfg)
    globs = resolve_tier_globs(reset_cfg, tier)
    tracked = git_tracked_files(project_root)

    # 클린 트리 가드 (§2.3 #5) — dry-run 은 읽기 전용이라 통과, --apply 에서만 강제
    dirty = git_tracked_dirty(project_root)
    if apply and dirty and not force:
        raise ResetAbort(
            f"추적 파일에 uncommitted 변경 {len(dirty)}건 — 커밋/스태시 후 재시도 "
            f"(--force 로 우회 가능). 예: {', '.join(dirty[:5])}"
        )

    branch = git_branch(project_root)
    _log(f"tier={tier} branch={branch} {'(dry-run)' if not apply else ''}".rstrip())

    candidates = expand_candidates(project_root, globs)
    to_delete, skipped = partition_candidates(
        candidates, project_root, protected_prefixes, tracked
    )
    total_bytes = sum(_dir_size(p) for p in to_delete)

    manifest: dict[str, Any] = {
        "adr": "ADR-033",
        "tier": tier,
        "timestamp": ts,
        "git_branch": branch,
        "git_head": git_head(project_root),
        "dry_run": not apply,
        "hard_delete": hard,
        "forced": force,
        "protected_prefixes_restored": restored,
        "candidate_count": len(candidates),
        "delete_count": len(to_delete),
        "delete_bytes": total_bytes,
        "skipped_protected": [{"path": r, "reason": why} for r, why in skipped],
        "moved": [],
        "qdrant_dropped": [],
    }

    _log(
        f"삭제 대상 {len(to_delete)}개 ({_human_bytes(total_bytes)}), "
        f"보호로 건너뜀 {len(skipped)}개"
    )

    if not apply:
        for p in to_delete[:50]:
            print(f"  DELETE  {_rel_posix(p, project_root)}  ({_human_bytes(_dir_size(p))})")
        if len(to_delete) > 50:
            print(f"  ... 외 {len(to_delete) - 50}개")
        if drop_qdrant:
            url = _qdrant_url(config_path)
            manifest["qdrant_dropped"] = drop_qdrant_collections(
                url, resolve_qdrant_whitelist(reset_cfg), apply=False
            )
        _log("dry-run 종료 — 아무것도 삭제하지 않음. 실제 실행은 --apply.")
        return manifest

    # 확인 문구 (§2.3 #2)
    _require_confirmation(tier, confirm, non_interactive)

    backup_dir = project_root / BACKUP_ROOT_NAME / f"reset_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for p in to_delete:
        rel = _rel_posix(p, project_root)
        size = _dir_size(p)
        if hard:
            p.unlink()
            manifest["moved"].append({"src": rel, "dest": None, "bytes": size})
        else:
            dest = backup_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            manifest["moved"].append(
                {"src": rel, "dest": _rel_posix(dest, project_root), "bytes": size}
            )

    if drop_qdrant:
        url = _qdrant_url(config_path)
        manifest["qdrant_dropped"] = drop_qdrant_collections(
            url, resolve_qdrant_whitelist(reset_cfg), apply=True
        )

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    verb = "hard-deleted" if hard else f"moved → {_rel_posix(backup_dir, project_root)}"
    _log(
        f"{verb}: {len(to_delete)}개 {_human_bytes(total_bytes)}, "
        f"skipped {len(skipped)} protected. manifest={_rel_posix(manifest_path, project_root)}"
    )
    return manifest


def _qdrant_url(config_path: Path) -> str:
    """config.yaml vector_db.qdrant.url — ADR-013 격리: 이 값만 사용."""
    default = "http://localhost:6333"
    if not config_path.exists():
        return default
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return default
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return (
        loaded.get("vector_db", {})
        .get("qdrant", {})
        .get("url", default)
    )


def _require_confirmation(tier: str, confirm: str | None, non_interactive: bool) -> None:
    expected = CONFIRM_PHRASES[tier]
    if non_interactive:
        if confirm != expected:
            raise ResetAbort(
                f"비대화형 실행: --confirm \"{expected}\" 를 정확히 전달해야 함"
            )
        return
    for attempt in range(3):
        got = input(f"확인 문구를 정확히 입력하세요 [{expected}]: ").strip()
        if got == expected:
            return
        _log(f"불일치 ({attempt + 1}/3)")
    raise ResetAbort("확인 문구 3회 불일치 — 중단")


# ── CLI ────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--tier", required=True, choices=["T1", "T2", "T3"])
    p.add_argument("--apply", action="store_true", help="dry-run 없이 실제 삭제")
    p.add_argument("--hard", action="store_true", help="backups 이동 대신 완전 삭제")
    p.add_argument("--force", action="store_true", help="클린 트리 가드 우회")
    p.add_argument("--drop-qdrant", action="store_true", help="T2: whitelist 컬렉션 drop")
    p.add_argument("--yes-i-mean-it", action="store_true", help="비대화형 확인")
    p.add_argument("--confirm", default=None, help="비대화형 확인 문구")
    p.add_argument("--project-root", default=None, help="(테스트) 프로젝트 루트 override")
    p.add_argument("--config", default=None, help="(테스트) config.yaml 경로 override")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    project_root = (
        Path(args.project_root)
        if args.project_root
        else Path(__file__).resolve().parent.parent
    )
    config_path = (
        Path(args.config) if args.config else project_root / "config.yaml"
    )
    try:
        run_reset(
            project_root=project_root,
            config_path=config_path,
            tier=args.tier,
            apply=args.apply,
            hard=args.hard,
            force=args.force,
            drop_qdrant=args.drop_qdrant,
            confirm=args.confirm,
            non_interactive=args.yes_i_mean_it,
        )
    except (ResetAbort, ValueError) as exc:
        _log(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
