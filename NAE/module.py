"""NAE Public Theology Module self-description/activation-check
(NAE-OPTIONAL-MODULE-PACKAGING-001).

`core/module_registry.py`가 이 모듈을 알지 못해도(즉 import하지 않아도)
DBMA Core는 정상 동작한다 — 반대로 이 모듈은 활성화 여부를 스스로 판단하지
않는다(그건 `core/module_registry.py::is_enabled()`가 유일한 정본).
이 모듈은 "활성화가 안전한가"만 검사한다: 설정/스키마/manifest/corpus가
실제로 존재하는지 확인할 뿐, embedding이나 indexing을 자동으로 시작하지
않는다.

버전 3종을 명확히 구분한다(§10):
  - Module version: 이 파일의 코드 버전(구조/로직)
  - Corpus version: `NAE/pipeline/ingest/manifests/`의 최신 generation
  - Schema version: TSU 레코드의 `tsu_schema_version`
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODULE_VERSION = "1.0.0"

NAE_ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = NAE_ROOT / "corpus" / "tsu"
MANIFEST_DIR = NAE_ROOT / "pipeline" / "ingest" / "manifests"


def _latest_manifest() -> dict[str, Any] | None:
    if not MANIFEST_DIR.exists():
        return None
    files = sorted(MANIFEST_DIR.glob("manifest_gen*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def check_availability() -> dict[str, Any]:
    """활성화 전 안전성 확인만 수행한다(READ-ONLY) — embedding/indexing을
    시작하지 않는다. 결과의 `safe_to_activate`가 False면 activation을
    성공으로 보고하면 안 된다(지시서 §11)."""
    checks: dict[str, Any] = {"module_version": MODULE_VERSION}

    corpus_exists = CORPUS_ROOT.exists()
    checks["corpus_root_exists"] = corpus_exists

    identifiers = []
    total_tsu_on_disk = 0
    if corpus_exists:
        for d in CORPUS_ROOT.iterdir():
            if d.is_dir() and not d.name.startswith("_"):
                tsu_path = d / "tsu.json"
                if tsu_path.exists():
                    identifiers.append(d.name)
                    try:
                        total_tsu_on_disk += len(json.loads(tsu_path.read_text(encoding="utf-8")))
                    except (json.JSONDecodeError, OSError):
                        pass
    checks["identifiers_found"] = identifiers

    manifest = _latest_manifest()
    checks["manifest_found"] = manifest is not None
    if manifest is not None:
        checks["manifest_generation"] = manifest.get("production_generation")
        checks["manifest_total_tsu"] = manifest.get("total_tsu")
        checks["manifest_matches_corpus"] = manifest.get("total_tsu") == total_tsu_on_disk
        checks["corpus_version"] = manifest.get("production_generation")
        checks["schema_version_from_manifest"] = None  # manifest는 개별 TSU schema_version을 담지 않음(§9 no-full-copy 원칙)
    else:
        checks["manifest_matches_corpus"] = False

    checks["safe_to_activate"] = bool(
        corpus_exists and identifiers and checks["manifest_found"] and checks["manifest_matches_corpus"]
    )
    return checks


def activate() -> dict[str, Any]:
    """활성화를 "시도"한다 — 성공은 오직 check_availability()가
    safe_to_activate=True를 반환할 때만 보고한다. embedding/indexing을
    호출하지 않는다(그건 별도 명령, `scripts/nae_incremental_ingest.py
    --apply`)."""
    checks = check_availability()
    return {
        "module": "nae_pd",
        "activated": checks["safe_to_activate"],
        "checks": checks,
        "embedding_calls_made": 0,
        "indexing_calls_made": 0,
    }
