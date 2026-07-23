# DBMA Sermon Corpus - 대시보드 기본 데이터 경로
#
# [버그 수정] seed_generator류 합성 데이터(seed_sermons.jsonl,
# sample_10k.jsonl — 실측 결과 preacher/church/youtube_channel까지
# 전부 지어낸 값)가 run_sermon_dashboard.py와 web_app.py 두 곳에 각각
# 따로 정의된 기본 경로 목록에 재도입돼, 실제 수집 데이터가 없으면
# 가짜 통계가 기본으로 노출되는 문제가 있었다. 실제 데이터 파일만
# 남기고 한 곳에만 정의해서 두 스크립트가 같이 가져다 쓰도록 통합.

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
