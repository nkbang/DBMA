#!/usr/bin/env bash
# scripts/build_corpus_bundle.sh — 베타 배포용 "기본 동봉 서재" 자산을 만든다.
#
# 배경(S6-1, docs/DBMA_S6_1_BUILD_REPORT_001.md §1): data/·output/은 전량
# .gitignore 대상이라, install_nae_beta.command가 받는 GitHub 태그
# tarball에는 코퍼스가 하나도 담기지 않는다. 이 스크립트가 만드는 산출물을
# 태그와 같은 이름의 GitHub Release 자산으로 올려야
# install_nae_beta.command가 내려받아 풀 수 있다(R4 해결 방식 A).
#
# 담는 것: TSU dataset + manifest, registry, 배포 가능 판정된 성경 본문
# placeholder(reference.json)뿐이다. tantivy_index/bible_index.sqlite3 등
# 캐시는 core/candidate_generator.py::open_or_build_index()가 첫 검색 시
# tsu_dataset.jsonl에서 스스로 만들어내므로 담지 않는다(용량 절약).
#
# knrv.json(저작권 있는 개역개정)은 의도적으로 제외한다 —
# docs/RELEASE_ASSET_PROVENANCE.md 판정 유지.
#
# Usage:
#   bash scripts/build_corpus_bundle.sh
# 산출물: dist/nae_baseline_corpus.tar.gz

set -e
cd "$(dirname "$0")/.."

OUT_DIR="dist"
OUT_FILE="$OUT_DIR/nae_baseline_corpus.tar.gz"

REQUIRED_FILES=(
    "output/bench/tsu_dataset.jsonl"
    "output/bench/tsu_manifest.json"
    "data/제련완성본/registry/documents.json"
    "data/bible/reference.json"
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "필수 파일 없음: $f" >&2
        exit 1
    fi
done

mkdir -p "$OUT_DIR"
rm -f "$OUT_FILE"
tar -czf "$OUT_FILE" "${REQUIRED_FILES[@]}"

echo "생성됨: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
echo "내용물:"
tar -tzf "$OUT_FILE"
