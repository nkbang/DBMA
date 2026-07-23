#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 설교은행 수집 실행 스크립트
==============================================

SermonBank에서 설교 제목 + 본문 참조 쌍을 수집합니다.

사용법:
    python scripts/collect_sermonbank.py [--max-records N] [--output PATH]

예시:
    python scripts/collect_sermonbank.py --max-records 1000
    python scripts/collect_sermonbank.py --output data/sermon_corpus/raw/custom.jsonl
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from sermon_corpus.collector.polite_fetcher import PoliteFetcher
from sermon_corpus.collector.sermonbank import SermonBankCollector


def load_config() -> Dict:
    """sources.yml 설정 파일을 로드합니다"""
    config_path = Path(__file__).parent.parent / "sermon_corpus" / "config" / "sources.yml"
    
    if not config_path.exists():
        print(f"경고: 설정 파일을 찾을 수 없습니다: {config_path}")
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_source_config(config: Dict, source_id: str) -> Dict:
    """특정 출처의 설정을 가져옵니다"""
    sources = config.get("sources", {})
    return sources.get(source_id, {})


def main():
    parser = argparse.ArgumentParser(description="SermonBank에서 설교 제목-본문 쌍 수집")
    parser.add_argument(
        "--max-records",
        type=int,
        default=10000,
        help="최대 수집 기록 수 (기본값: 10000)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 JSONL 파일 경로 (기본값: sources.yml에 설정된 경로)"
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        default=None,
        help="수집할 URL 목록 (기본값: sources.yml에 설정된 URL 사용)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 수집 없이 설정만 확인"
    )
    
    args = parser.parse_args()
    
    # 설정 로드
    print("=" * 60)
    print("DBMA Sermon Corpus - 설교은행 수집기")
    print("=" * 60)
    
    config = load_config()
    if not config:
        print("오류: 설정 파일을 로드할 수 없습니다.")
        sys.exit(1)
    
    # SermonBank 설정
    sb_config = get_source_config(config, "sermonbank")
    if not sb_config:
        print("오류: sermonbank 출처 설정을 찾을 수 없습니다.")
        sys.exit(1)

    # [버그 수정] enabled: false로 꺼둔 출처인데도 그대로 수집을
    # 진행하던 문제 — background_collector.py의 run_once()와 동일한
    # 문제를 이 단독 실행 스크립트도 그대로 갖고 있었다. --urls로
    # 명시적으로 지정한 경우는 사용자가 직접 원해서 실행하는 것이므로
    # enabled 체크를 건너뛴다.
    if not args.urls and not sb_config.get("enabled", True):
        print("오류: sermonbank 출처가 sources.yml에서 enabled: false로 꺼져 있습니다.")
        print("      실행하려면 sources.yml에서 enabled: true로 바꾸거나 --urls로 URL을 직접 지정하세요.")
        sys.exit(1)

    # URL 설정 — 기본 fallback도 실제 검증된 게시판 URL로 통일
    # (sources.yml 확인 결과 sermonbank.net/sermons는 404였음)
    urls = args.urls or sb_config.get(
        "urls", ["https://sermonbank.net/bbs/board.php?bo_table=sermon"]
    )
    print(f"\n수집 대상 URL:")
    for url in urls:
        print(f"  - {url}")
    
    # 저장 경로 설정
    if args.output:
        storage_path = Path(args.output)
    else:
        storage_path = Path(sb_config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/sermonbank.jsonl"
        ))
    print(f"\n출력 경로: {storage_path}")
    
    # dry-run 모드
    if args.dry_run:
        print("\n[dry-run] 실제 수집 없이 설정만 확인했습니다.")
        print(f"설정된 URL 수: {len(urls)}")
        print(f"최대 기록 수: {args.max_records}")
        return
    
    # 수집기 초기화
    print("\n수집기 초기화 중...")
    
    # PoliteFetcher 설정
    limits = sb_config.get("limits", {})
    fetcher = PoliteFetcher(
        user_agent=config.get("default_policy", {}).get(
            "user_agent", "DBMA-SermonCorpus/0.1 (academic research)"
        ),
        min_delay=limits.get("min_delay_seconds", 5.0),
        max_delay=limits.get("max_delay_seconds", 12.0),
        max_retries=config.get("default_policy", {}).get("retry", {}).get("max_attempts", 2),
    )
    
    # SermonBankCollector 설정
    collector = SermonBankCollector({
        "source_id": "sermonbank",
        "urls": urls,
        "storage": {"raw_path": str(storage_path)},
    })
    
    # 수집 시작
    print("\n수집 시작...")
    print("-" * 40)
    
    try:
        records = collector.collect_all(fetcher, max_records=args.max_records)
    except KeyboardInterrupt:
        print("\n수집이 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n수집 중 오류가 발생했습니다: {e}")
        sys.exit(1)
    
    # 중복 제거 및 저장
    print("-" * 40)
    print(f"총 수집된 기록 수: {len(records)}")
    
    saved_count = collector.save_to_jsonl(records)
    print(f"저장된 기록 수: {saved_count}")
    
    # 통계 출력
    stats = collector.get_stats()
    fetcher_stats = fetcher.get_stats()
    
    print("\n" + "=" * 60)
    print("수집 통계")
    print("=" * 60)
    print(f"처리된 URL 수: {stats['urls_processed']}")
    print(f"수집된 설교 수: {stats['sermons_collected']}")
    print(f"중복 건너뜀: {stats['duplicates_skipped']}")
    print(f"오류 수: {stats['errors']}")
    print("-" * 40)
    print(f"HTTP 요청 총수: {fetcher_stats['requests_total']}")
    print(f"200 OK: {fetcher_stats['requests_200']}")
    print(f"429 Too Many Requests: {fetcher_stats['requests_429']}")
    print(f"403 Forbidden: {fetcher_stats['requests_403']}")
    print(f"robots.txt 차단: {fetcher_stats['robots_denied']}")
    print(f"기타 오류: {fetcher_stats['errors']}")
    print("=" * 60)
    
    # 샘플 출력 (첫 5건)
    if saved_count > 0:
        print("\n샘플 기록 (첫 5건):")
        print("-" * 40)
        with open(storage_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                record = json.loads(line)
                print(f"\n[{i+1}] {record['title']}")
                print(f"    본문: {record['passage_raw']}")
                print(f"    성경: {record['bible_book']}")
                print(f"    설교자: {record.get('preacher', 'N/A')}")
                print(f"    날짜: {record.get('published_date', 'N/A')}")
    
    print(f"\n저장 완료: {storage_path}")
    print(f"총 {saved_count}건의 설교 제목-본문 쌍이 저장되었습니다.")


if __name__ == "__main__":
    main()