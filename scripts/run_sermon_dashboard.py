#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 대시보드 실행 스크립트
==========================================

설교 빈도 및 키워드 시각화 대시보드를 실행합니다.

사용법:
    # 1) 데이터 수집 후
    python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl
    
    # 2) 샘플 데이터로 테스트
    python scripts/run_sermon_dashboard.py --sample
    
    # 3) 커스텀 포트
    python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl --port 8502

예시:
    python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict


def create_sample_data(output_path: Path, num_records: int = 100) -> None:
    """샘플 데이터 생성 (테스트용)"""
    import random
    
    # 샘플 성경 책 및 장
    sample_books = [
        ("Genesis", list(range(50))),
        ("Psalms", list(range(150))),
        ("Proverbs", list(range(31))),
        ("Isaiah", list(range(66))),
        ("Matthew", list(range(28))),
        ("John", list(range(21))),
        ("Romans", list(range(16))),
        ("1 Corinthians", list(range(16))),
        ("Revelation", list(range(22))),
    ]
    
    # 샘플 설교 제목
    sample_titles = [
        "믿음의 도전", "기도의 힘", "사랑의 실천", "용서의 은혜",
        "구원의 여정", "성령의 능력", "천국의 비밀", "율법의 의미",
        "언약의 완성", "은혜의 삶", "지혜의 길", "심판의 날",
        "부활의 희망", "십자가의 사랑", "소망의 확신", "예배의 본질",
        "정의의 구현", "창조의 경이", "출애굽의 여정", "예언의 성취",
    ]
    
    records = []
    for i in range(num_records):
        book, chapters = random.choice(sample_books)
        chapter = random.choice(chapters)
        verse_start = random.randint(1, 20)
        verse_end = verse_start + random.randint(0, 5)
        
        title = random.choice(sample_titles)
        
        record = {
            "record_id": f"sample_{i}",
            "source": "sample",
            "title": f"{title} - {book} {chapter}장 해석",
            "passage_raw": f"{book} {chapter}:{verse_start}-{verse_end}",
            "bible_book": book,
            "chapter_start": chapter,
            "chapter_end": chapter,
            "verse_start": verse_start,
            "verse_end": verse_end,
            "preacher": "Sample Preacher",
            "published_date": "2024-01-01",
            "source_url": "https://example.com",
            "collected_at": "2024-01-01T00:00:00",
        }
        records.append(record)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"샘플 데이터 {num_records}건을 생성했습니다: {output_path}")


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
        "--sample",
        action="store_true",
        help="샘플 데이터로 대시보드 실행",
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
    
    # 데이터 경로 결정
    if args.sample:
        sample_path = Path("data/sermon_corpus/raw/sample_data.jsonl")
        if not sample_path.exists():
            create_sample_data(sample_path, num_records=100)
        data_path = str(sample_path)
        print(f"샘플 데이터 사용: {data_path}")
    elif args.data:
        data_path = args.data
    else:
        # 기본 경로 확인 (실제 수집 데이터 우선 — large_seed_sermons.jsonl은
        # seed_generator.py가 만든 합성/가상 데이터라 기본 경로에서 제외,
        # 필요 시 --data로 명시적으로 지정)
        default_paths = [
            "data/sermon_corpus/raw/sermonbank.jsonl",
            "data/sermon_corpus/raw/sermonbank_collected.jsonl",
        ]
        data_path = None
        for p in default_paths:
            if Path(p).exists():
                data_path = p
                break
        
        if not data_path:
            print("데이터 파일이 지정되지 않았습니다.")
            print("옵션: --data PATH 또는 --sample")
            sys.exit(1)
    
    # 데이터 확인
    data_file = Path(data_path)
    if not data_file.exists():
        print(f"오류: 데이터 파일을 찾을 수 없습니다: {data_path}")
        sys.exit(1)
    
    # 기록 수 확인
    with open(data_file, "r", encoding="utf-8") as f:
        record_count = sum(1 for line in f if line.strip())
    print(f"데이터 파일: {data_path} ({record_count}건)")
    
    if record_count == 0:
        print("경고: 데이터가 없습니다. --sample 옵션으로 테스트하세요.")
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