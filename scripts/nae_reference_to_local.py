#!/usr/bin/env python3
"""참고 코퍼스(신학사전·주석)를 Docker Qdrant 서버에서 내장(로컬) 저장소로 복사한다.

사용:
    python scripts/nae_reference_to_local.py            # 서버 → data/reference_qdrant
    python scripts/nae_reference_to_local.py --check    # 로컬 저장소 상태만 확인

서버(nae_qdrant, 기본 localhost:7333)가 떠 있어야 하고, 완료되면 앱은 Docker 없이
사전·주석을 검색한다. 참고 코퍼스를 서버에 새로 적재했다면 이 스크립트를 다시 돌려
로컬 복사본을 갱신한다.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from NAE.pipeline.reference import config as ref_config  # noqa: E402
from NAE import reference_local_store as store  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=ref_config.QDRANT_URL, help="원본 Qdrant 서버 URL")
    ap.add_argument("--dest", type=Path, default=None, help="로컬 저장소 폴더(기본: 설정값)")
    ap.add_argument("--check", action="store_true", help="복사하지 않고 로컬 저장소 상태만 출력")
    args = ap.parse_args()

    dest = args.dest or store.local_store_path()
    if args.check:
        if store.is_ready(dest):
            print(f"준비됨: {dest}\n" + (dest / store.READY_MARKER).read_text(encoding="utf-8"))
            return 0
        print(f"없음 또는 미완료: {dest}")
        return 1

    last = {"name": None}

    def progress(name: str, done: int, total: int) -> None:
        if last["name"] != name:
            last["name"] = name
            print(f"\n{name}")
        print(f"\r  {done:>6}/{total}", end="", flush=True)

    try:
        counts = store.convert_from_server(args.url, dest=dest, progress=progress)
    except Exception as e:  # noqa: BLE001
        print(f"\n실패: {type(e).__name__}: {e}", file=sys.stderr)
        print("서버(nae_qdrant)가 떠 있는지 확인하세요.", file=sys.stderr)
        return 1
    print("\n\n완료:", ", ".join(f"{k} {v}건" for k, v in counts.items()), f"→ {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
