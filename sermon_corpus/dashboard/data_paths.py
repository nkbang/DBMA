# DBMA Sermon Corpus - 대시보드 기본 데이터 경로
#
# 실제 수집 데이터만 사용. 가짜 샘플 데이터(seed_generator, synthetic data)
# 경로는 제거됨. 실제 설교은행/유튜브/교회 웹사이트에서 수집한 데이터만 사용.

from pathlib import Path
from typing import Optional

DEFAULT_DATA_PATHS = [
    "data/sermon_corpus/raw/sermonbank.jsonl",
    "data/sermon_corpus/raw/sermonbank_collected.jsonl",
    "data/sermon_corpus/uploaded/uploaded_sermons.jsonl",
    "sermon_corpus/data/collected_sermons.jsonl",
]


def find_default_data_path() -> Optional[str]:
    """DEFAULT_DATA_PATHS 중 존재하는 첫 번째 실제 데이터 파일 경로를 반환"""
    for p in DEFAULT_DATA_PATHS:
        if Path(p).exists():
            return p
    return None
