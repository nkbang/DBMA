#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 백그라운드 데이터 수집기 실행 스크립트
========================================================

별도 프로세스에서 데이터를 수집하고 JSONL 파일에 저장합니다.
대시보드는 이 파일을 읽어서 최신 데이터를 표시합니다.

사용법:
    # 수동 실행 (한 번)
    python scripts/background_collector.py
    
    # 데몬 모드 (지속적 실행)
    python scripts/background_collector.py --daemon
    
    # 30분 간격으로 실행
    python scripts/background_collector.py --daemon --interval 1800
    
    # 현재 상태 확인
    python scripts/background_collector.py --status

데이터 저장 위치:
    sermon_corpus/data/collected_sermons.jsonl

수집 소스:
    - sermon_corpus/config/sources.yml 에 configured된 모든 출처
"""

import sys
import os
import argparse
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sermon_corpus.collector.background_collector import BackgroundCollector


def main():
    parser = argparse.ArgumentParser(description="백그라운드 설교 데이터 수집기")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="데몬 모드로 실행 (지속적)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="데몬 모드 수집 간격 (초, 기본값: 300 = 5분)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="설정 파일 경로",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="데이터 저장 파일 경로",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="현재 상태 출력 후 종료",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="한 번만 실행 후 종료",
    )
    
    args = parser.parse_args()
    
    collector = BackgroundCollector(
        config_path=args.config,
        data_path=args.data,
    )
    
    if args.status:
        collector.print_status()
        return
    
    if args.daemon:
        print("=" * 60)
        print("백그라운드 수집기 시작...")
        print(f"수집 간격: {args.interval}초")
        print("중단하려면 Ctrl+C를 누르세요.")
        print("=" * 60)
        collector.print_status()
        collector.run_daemon(interval=args.interval)
    elif args.once:
        print("=" * 60)
        print("한 번의 수집 실행...")
        print("=" * 60)
        collector.run_once()
        collector.print_status()
    else:
        # 기본: 한 번 실행
        print("=" * 60)
        print("수집기 실행 중... (Ctrl+C로 종료)")
        print("=" * 60)
        collector.run_once()
        collector.print_status()


if __name__ == "__main__":
    main()