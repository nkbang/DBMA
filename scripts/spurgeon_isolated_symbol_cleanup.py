"""스펄젼 제련완성본 텍스트의 고립 기호줄(OCR 잡음) 제거.

대상: <data_dir>/Spurgeon_*.txt (베이스 텍스트만, _chunks/_meta 제외)
동작: 줄 전체가 단어문자/한글/공백이 아닌 기호로만(1~10자) 구성된 줄을 제거.
      원본은 .bak 백업 후 in-place 수정.
"""
import argparse
import glob
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.utils import calculate_noise_score

_ISOLATED_SYMBOL_LINE = re.compile(r"[^\w가-힣\s]{1,10}")


def strip_isolated_symbol_lines(text: str) -> "tuple[str, int]":
    out = []
    removed = 0
    for line in text.split("\n"):
        s = line.strip()
        if s and _ISOLATED_SYMBOL_LINE.fullmatch(s):
            removed += 1
            continue
        out.append(line)
    return "\n".join(out), removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.data_dir, "Spurgeon_*.txt")))
    files = [f for f in files if "_chunks" not in f]

    print(f"대상 파일: {len(files)}개\n")
    total_removed = 0
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        before = calculate_noise_score(text, file_type="txt")["score"]
        cleaned, removed = strip_isolated_symbol_lines(text)
        if removed == 0:
            continue
        after = calculate_noise_score(cleaned, file_type="txt")["score"]

        if not args.dry_run:
            bak = f + ".bak"
            if not os.path.exists(bak):
                shutil.copy2(f, bak)
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(cleaned)

        total_removed += removed
        print(f"{os.path.basename(f):55s} noise {before:6.2f} -> {after:6.2f}  (제거 {removed}줄)")

    print(f"\n총 제거 줄 수: {total_removed}")


if __name__ == "__main__":
    main()
