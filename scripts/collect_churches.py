#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
교회 웹사이트 설교 데이터 수집 CLI

사용법:
  # 전체 100개 교회 수집
  python scripts/collect_churches.py

  # 특정 교회만 수집 (도메인 목록)
  python scripts/collect_churches.py --churches klac.org youngnak.org navichurch.org

  # 최대 항목 수 설정
  python scripts/collect_churches.py --max-items 100

  # 개별 설교 페이지 스크랩
  python scripts/collect_churches.py --scrape-pages

  # 딜레이 조정
  python scripts/collect_churches.py --delay-min 3 --delay-max 8
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# DBMA 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sermon_corpus.collector.church import collect_churches, ALL_CHURCHES

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="교회 웹사이트 설교 데이터 수집 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 전체 100개 교회 수집 (기본 50건/교회)
  python scripts/collect_churches.py

  # 남가주 사랑의교회만 수집
  python scripts/collect_churches.py --churches klac.org

  # 최대 100건/교회, 개별 페이지 스크랩
  python scripts/collect_churches.py --max-items 100 --scrape-pages

  # 국내 대형교회만 (사랑의교회, 온누리교회 등)
  python scripts/collect_churches.py --churches sarang.org onnuri.org woorich.or.kr
        """,
    )

    parser.add_argument(
        "--output",
        default="data/sermon_corpus/church",
        help="출력 디렉토리 (기본: data/sermon_corpus/church)",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="교회별 최대 수집 수 (기본: 50)",
    )
    parser.add_argument(
        "--scrape-pages",
        action="store_true",
        help="개별 설교 페이지도 스크랩 (메타데이터 보강)",
    )
    parser.add_argument(
        "--churches",
        nargs="+",
        help="수집할 교회 도메인 목록 (생략 시 전체 100개)",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=5.0,
        help="요청 간 최소 딜레이 초 (기본: 5.0)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=12.0,
        help="요청 간 최대 딜레이 초 (기본: 12.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="수집 없이 대상 교회 목록만 출력",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="디버그 로그 출력",
    )

    args = parser.parse_args()

    # 로깅 설정
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 대상 교회 필터링
    churches = ALL_CHURCHES
    if args.churches:
        domain_set = set(args.churches)
        churches = [c for c in ALL_CHURCHES if c.domain in domain_set]
        if len(churches) != len(domain_set):
            found = {c.domain for c in churches}
            missing = domain_set - found
            print(f"경고: 다음 도메인을 찾을 수 없음: {missing}")

    # dry-run
    if args.dry_run:
        print(f"수집 대상 교회 ({len(churches)}개):")
        for i, c in enumerate(churches, 1):
            print(f"  {i:3d}. {c.name:<20s} ({c.domain}) -> {c.base_url}{c.sermon_list_path}")
        return

    # 수집 시작
    print(f"=" * 60)
    print(f"교회 설교 데이터 수집 시작")
    print(f"=" * 60)
    print(f"  대상 교회: {len(churches)}개")
    print(f"  최대 항목/교회: {args.max_items}")
    print(f"  개별 페이지 스크랩: {'예' if args.scrape_pages else '아니오'}")
    print(f"  딜레이: {args.delay_min:.1f}~{args.delay_max:.1f}초")
    print(f"  출력: {args.output}")
    print(f"=" * 60)

    start = datetime.now()

    records = collect_churches(
        churches=churches,
        output_dir=args.output,
        max_items_per_church=args.max_items,
        scrape_individual=args.scrape_pages,
        delay_range=(args.delay_min, args.delay_max),
    )

    elapsed = (datetime.now() - start).total_seconds()

    # 결과 요약
    print(f"\n수집 완료!")
    print(f"  총 수집: {len(records)}건")
    print(f"  소요 시간: {elapsed:.1f}초")
    print(f"  초당 처리: {len(records)/elapsed:.2f}건/초" if elapsed > 0 else "  초당 처리: N/A")

    # bible_book별 집계
    book_counts = {}
    for rec in records:
        bb = rec.bible_book
        book_counts[bb] = book_counts.get(bb, 0) + 1

    print(f"\n성경 권별 집계 (상위 10):")
    for book, count in sorted(book_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {book:<20s}: {count:>5d}건")

    # 교회별 수집 수
    church_counts = {}
    for rec in records:
        src = rec.source
        church_counts[src] = church_counts.get(src, 0) + 1

    skipped = len(churches) - len(church_counts)
    if skipped > 0:
        print(f"\n  수집 0건 교회: {skipped}개")


if __name__ == "__main__":
    main()