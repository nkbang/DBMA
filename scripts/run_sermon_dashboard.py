#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 대시보드 실행 스크립트
==========================================

설교 빈도 및 키워드 시각화 대시보드를 실행합니다.

사용법:
    # 1) 실제 데이터로 대시보드 실행
    python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl
    
    # 2) 기본 데이터 경로 자동 감지
    python scripts/run_sermon_dashboard.py
    
    # 3) 커스텀 포트
    python scripts/run_sermon_dashboard.py --port 8502

예시:
    python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl

참고:
    - 가짜 샘플 데이터 생성 로직은 제거됨. 실제 수집 데이터만 사용.
    - 기본 데이터 경로: sermon_corpus/dashboard/data_paths.py::DEFAULT_DATA_PATHS
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from sermon_corpus.dashboard.data_paths import DEFAULT_DATA_PATHS


def check_dependencies() -> bool:
    """필수 의존성 확인"""
    missing = []
    
    try:
        import streamlit
    except ImportError:
        missing.append("streamlit")
    
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
    
    try:
        import plotly
    except ImportError:
        missing.append("plotly")
    
    if missing:
        print(f"경고: 다음 의존성이 설치되지 않았습니다: {', '.join(missing)}")
        print(f"설치 명령: pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="DBMA 설교 대시보드 실행")
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="JSONL 데이터 파일 경로",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Streamlit 포트 (기본값: 8501)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/sermon_dashboard",
        help="통계 출력 디렉토리 (기본값: output/sermon_dashboard)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DBMA 설교 대시보드")
    print("=" * 60)
    
    # 의존성 확인
    if not check_dependencies():
        response = input("\n의존성을 설치하시겠습니까? (y/n): ")
        if response.lower() == "y":
            subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "pandas", "plotly"])
        else:
            print("중지: 의존성이 필요합니다.")
            sys.exit(1)
    
    # 데이터 경로 결정 (가짜 샘플 데이터 제거 — 실제 데이터만 사용)
    if args.data:
        data_path = args.data
    else:
        # 기본 경로 확인 (data_paths.py::DEFAULT_DATA_PATHS 공유)
        data_path = None
        for p in DEFAULT_DATA_PATHS:
            if Path(p).exists():
                data_path = p
                break
        
        if not data_path:
            print("데이터 파일이 지정되지 않았습니다.")
            print("옵션: --data PATH를 사용하세요.")
            sys.exit(1)
    
    # 데이터 확인
    data_file = Path(data_path)
    if not data_file.exists():
        print(f"오류: 데이터를 파일을 찾을 수 없습니다: {data_path}")
        sys.exit(1)
    
    # 기록 수 확인
    with open(data_file, "r", encoding="utf-8") as f:
        record_count = sum(1 for line in f if line.strip())
    print(f"데이터 파일: {data_path} ({record_count}건)")
    
    if record_count == 0:
        print("경고: 데이터가 없습니다. 실제 데이터를 로드하세요.")
        sys.exit(1)
    
    # 대시보드 실행
    print("\n대시보드를 시작합니다...")
    print(f"URL: http://localhost:{args.port}")
    print("-" * 40)
    
    dashboard_script = Path(__file__).parent.parent / "sermon_corpus" / "dashboard" / "web_app.py"
    
    # [버그 수정] Streamlit CLI 관례상 앱 고유 인자(--data)는 Streamlit
    # 자체 옵션(--server.port 등)과 섞이지 않도록 "--" 구분자 뒤에
    # 와야 한다 — 이전 순서는 일부 Streamlit 버전에서
    # "no such option: --data" 오류를 낼 수 있었다.
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(dashboard_script),
        f"--server.port={args.port}",
        "--server.headless=true",
        "--",
        f"--data={data_path}",
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n대시보드가 중단되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"오류: 대시보드를 실행할 수 없습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()