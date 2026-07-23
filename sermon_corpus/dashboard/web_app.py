#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 대시보드 웹 애플리케이션
============================================

설교 빈도 및 키워드 시각화 대시보드 (Streamlit 기반)

사용법:
    streamlit run sermon_corpus/dashboard/web_app.py [--data PATH]

예시:
    streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/raw/sermonbank.jsonl
"""

import re
import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
from sermon_corpus.analyzer.keywords import KeywordExtractor
from sermon_corpus.analyzer.corpus_statistics import CorpusStatisticsAnalyzer
from sermon_corpus.analyzer.keywords import CATEGORY_KOREAN_MAP, BIBLE_BOOK_KOREAN_MAP
from sermon_corpus.collector.background_collector import DataStore
from sermon_corpus.collector.sermonbank import BibleReferenceParser

# bible_book 값 정합성 검사/복구용 — 정경 66권 영문 canonical 이름 집합과
# 한글/오기 별칭 -> 영문 매핑 (frequency.py와 동일한 기준 재사용)
_CANONICAL_BOOKS = {book for book, _, _ in FrequencyAnalyzer.BIBLE_BOOKS}
_ALIAS_TO_CANONICAL = FrequencyAnalyzer.KOREAN_ABBREVIATIONS
_ALIASES_BY_LEN_DESC = sorted(_ALIAS_TO_CANONICAL.keys(), key=len, reverse=True)


def _recover_bible_book(raw: str) -> tuple:
    """bible_book 칸에 책명이 아니라 본문 참조 문자열(예: '시편 37:5-7',
    '출애굽기 29')이 들어온 경우 실제 책명(+가능하면 장 번호)을 복구한다.

    Returns:
        (bible_book, chapter_start 또는 None)
    """
    if raw in _CANONICAL_BOOKS:
        return raw, None

    parsed = BibleReferenceParser().parse(raw)
    if parsed.get("bible_book"):
        return parsed["bible_book"], parsed.get("chapter_start")

    # BibleReferenceParser가 "장"/":" 마커 없는 형식("출애굽기 29")은
    # 못 잡으므로, 별칭 접두어 매칭 + 뒤따르는 숫자를 장 번호로 시도.
    stripped = raw.strip()
    for alias in _ALIASES_BY_LEN_DESC:
        if stripped.startswith(alias):
            rest = stripped[len(alias):].strip()
            m = re.match(r"^(\d+)", rest)
            chapter = int(m.group(1)) if m else None
            return _ALIAS_TO_CANONICAL[alias], chapter

    return raw, None


# ============================================================
# 진행률 상태 클래스
# ============================================================

@dataclass
class ProgressState:
    """파일 처리 진행률 상태"""
    current: int = 0
    total: int = 0
    message: str = ""
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)
    
    @property
    def is_complete(self) -> bool:
        return self.current >= self.total


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="DBMA 설교 대시보드",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 필드 매핑 정의
# ============================================================

# 성경 책 필드명 매핑
BIBLE_BOOK_FIELDS = [
    "bible_book", "bibleBook", "BibleBook", "book", "book_name", 
    "bookName", "성경책", "성경", "책", "book_title"
]

# 장 필드명 매핑
CHAPTER_FIELDS = [
    "chapter_start", "chapterStart", "ChapterStart", "chapter", "Chapter",
    "장", "chap_start", "chapStart", "chapter_begin"
]

# 설교 제목 필드명 매핑
TITLE_FIELDS = [
    "title", "sermon_title", "sermonTitle", "SermonTitle", "Title",
    "설교제목", "제목", "subject", "topic"
]

# 본문 필드명 매핑 (raw passage)
PASSAGE_FIELDS = [
    "passage_raw", "passageRaw", "PassageRaw", "passage", "Passage",
    "본문", "scripture", "text"
]

# 설교자 필드명 매핑
PREACHER_FIELDS = [
    "preacher", "preacher_name", "preacherName", "PreacherName", "Preacher",
    "설교자", "목사", "speaker", "pastor"
]

# 날짜 필드명 매핑
DATE_FIELDS = [
    "published_date", "publishedDate", "PublishedDate", "date", "Date",
    "pub_date", "pubDate", " preaching_date", "설교일", "날짜"
]

# 교회 필드명 매핑
CHURCH_FIELDS = [
    "church", "church_name", "churchName", "ChurchName", "Church",
    "교회", " congregation"
]

# 연도/연대 계산용 필드
DATE_CALC_FIELDS = DATE_FIELDS  # 날짜에서 연도/연대 추출

# 기본 데이터 경로 탐색 (run_sermon_dashboard.py와 공유 — data_paths.py 참고)
from sermon_corpus.dashboard.data_paths import find_default_data_path


def detect_field_mapping(headers: List[str]) -> Dict[str, str]:
    """CSV 헤더에서 필드 매핑을 자동 감지합니다.
    
    Returns:
        매핑 딕셔너리: { 표준필드명: 실제헤더명 }
    """
    mapping = {}
    headers_lower = [h.lower().strip() for h in headers]
    # [버그 수정] 헤더별 매핑 여부를 추적하지 않아 "성경본문"처럼 여러
    # 패턴("성경"→bible_book, "본문"→passage_raw)에 동시에 걸리는 헤더가
    # 두 표준 필드에 중복 배정됐다 — bible_book에 실제로는 본문 참조
    # 문자열("시편 37:5-7")이 들어가는 사고가 여기서 발생했다. 한 헤더는
    # 먼저 매핑된 표준 필드 하나만 차지하도록 사용된 헤더를 추적.
    used_headers = set()

    # 각 필드 유형별로 매핑 시도
    for field_list, standard_name in [
        (BIBLE_BOOK_FIELDS, "bible_book"),
        (CHAPTER_FIELDS, "chapter"),
        (TITLE_FIELDS, "title"),
        (PASSAGE_FIELDS, "passage_raw"),
        (PREACHER_FIELDS, "preacher"),
        (DATE_FIELDS, "date"),
        (CHURCH_FIELDS, "church"),
    ]:
        for header in headers_lower:
            if header in used_headers:
                continue
            for pattern in field_list:
                if pattern.lower() in header or header in pattern.lower():
                    # 실제 헤더 인덱스 찾기
                    idx = headers_lower.index(header)
                    mapping[standard_name] = headers[idx]
                    used_headers.add(header)
                    break
            if standard_name in mapping:
                break

    return mapping


def normalize_record(record: dict, field_mapping: Dict[str, str]) -> dict:
    """CSV 레코드를 표준 형식으로 변환합니다"""
    normalized = {}
    
    # bible_book
    bb_key = field_mapping.get("bible_book")
    bible_book_raw = str(record.get(bb_key, "")) if bb_key else ""
    # [버그 수정] 헤더 오매핑(위 detect_field_mapping 수정으로 재발은
    # 막았지만, 이미 그렇게 생성된 CSV/이전 파일이 들어올 가능성은
    # 여전함) 등으로 bible_book 칸에 책명이 아니라 "시편 37:5-7" 같은
    # 본문 참조 문자열이 그대로 들어올 수 있다. "1 Corinthians"/"2 Kings"
    # 처럼 정상 책명에도 숫자가 들어가므로 "숫자 포함 여부"가 아니라
    # 정경 66권 canonical 이름 집합에 있는지로 판단해야 오탐이 없다.
    bible_book_looks_like_passage = bool(bible_book_raw) and bible_book_raw not in _CANONICAL_BOOKS
    recovered_chapter = None
    if bible_book_looks_like_passage:
        normalized["bible_book"], recovered_chapter = _recover_bible_book(bible_book_raw)
    else:
        normalized["bible_book"] = bible_book_raw

    # chapter
    ch_key = field_mapping.get("chapter")
    try:
        if ch_key:
            val = record.get(ch_key, 0)
            normalized["chapter_start"] = int(val) if val else 1
        elif recovered_chapter:
            # chapter 칸이 따로 없고 bible_book 칸이 참조 문자열이었던
            # 경우, 그 참조에서 복구된 장 번호를 사용.
            normalized["chapter_start"] = recovered_chapter
        else:
            normalized["chapter_start"] = 1
        normalized["chapter_end"] = normalized["chapter_start"]
    except (ValueError, TypeError):
        normalized["chapter_start"] = 1
        normalized["chapter_end"] = 1
    
    # title
    tl_key = field_mapping.get("title")
    normalized["title"] = str(record.get(tl_key, "")) if tl_key else ""
    
    # passage_raw (제목에서 본문 추출 시도)
    ps_key = field_mapping.get("passage_raw")
    if ps_key and record.get(ps_key):
        normalized["passage_raw"] = str(record[ps_key])
    elif bible_book_looks_like_passage:
        # bible_book 칸이 실제로는 본문 참조 문자열이었던 경우(위에서
        # 책명만 뽑아 bible_book으로 옮겼음) — 원본 문자열 자체가
        # passage_raw로 쓸 수 있는 가장 정확한 정보이므로 그대로 보존.
        normalized["passage_raw"] = bible_book_raw
    elif normalized["title"]:
        # 제목에서 본문 정보 추출 (예: "창세기 1장 - 창조")
        normalized["passage_raw"] = normalized["title"]
    else:
        normalized["passage_raw"] = f"{normalized['bible_book']} {normalized['chapter_start']}장"
    
    # preacher
    pr_key = field_mapping.get("preacher")
    normalized["preacher"] = str(record.get(pr_key, "")) if pr_key else ""
    
    # date
    dt_key = field_mapping.get("date")
    normalized["published_date"] = str(record.get(dt_key, "")) if dt_key else ""
    
    # church
    ch_key = field_mapping.get("church")
    normalized["church"] = str(record.get(ch_key, "")) if ch_key else ""
    
    # 연도/연대 계산
    normalized["year"], normalized["decade"] = compute_year_decade(normalized["published_date"])
    
    return normalized


def compute_year_decade(date_str: str) -> tuple:
    """날짜 문자열에서 연도와 연대를 추출합니다"""
    if not date_str:
        return None, None
    
    # 다양한 날짜 형식 시도
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y"]:
        try:
            year = int(date_str[:4])
            decade = (year // 10) * 10
            return year, decade
        except (ValueError, IndexError):
            continue
    
    return None, None


@st.cache_data(ttl=3600)
def load_data(data_path: str, progress: Optional[ProgressState] = None) -> Optional[List[dict]]:
    """다양한 파일 형식에서 데이터를 로드합니다.
    
    지원 형식:
    - JSONL (한 줄당 JSON 객체)
    - CSV (콤마/탭 구분자, 필드 자동 감지)
    - TSV (탭 구분자)
    - XLSX (엑셀)
    - TXT (TSV로 간주)
    - SQLite (DB 파일)
    
    CSV 필드 자동 감지:
    - bible_book, chapter, title, preacher, date 등 주요 필드명 패턴 매칭
    - 여러 필드명 변형 지원 (예: bible_book, BibleBook, 성경책 등)
    """
    if not data_path or not Path(data_path).exists():
        return None
    
    path = Path(data_path)
    ext = path.suffix.lower()
    
    try:
        if ext == ".jsonl" or ext == ".json":
            # JSONL 형식 - 표준 필드명 가정
            records = []
            total_lines = sum(1 for _ in open(data_path, "r", encoding="utf-8"))
            
            with open(data_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if progress:
                        progress.current = i + 1
                        progress.message = f"JSONL 처리 중: {i+1}/{total_lines}"
                    
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        # 연도/연대 계산
                        date_str = record.get("published_date", "") or record.get("date", "")
                        year, decade = compute_year_decade(str(date_str))
                        record["year"] = year
                        record["decade"] = decade
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            return records if records else None
        
        elif ext in (".csv", ".tsv", ".txt"):
            # CSV/TSV/TXT 형식 - 필드 자동 감지
            import pandas as pd
            
            # 구분자 자동 감지
            with open(data_path, "r", encoding="utf-8") as f:
                sample = f.read(4096)
            
            sep = "\t" if "\t" in sample[:1024] else ","
            
            df = pd.read_csv(data_path, sep=sep, encoding="utf-8")
            
            if df.empty or df.columns.tolist() == [""]:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환 (진행률 업데이트)
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"CSV 변환 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        elif ext == ".xlsx":
            # 엑셀 형식
            import pandas as pd
            
            df = pd.read_excel(data_path, engine="openpyxl")
            
            if df.empty:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"엑셀 변환 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                # NaN 처리
                record = {k: (None if v != v else v) for k, v in record.items()}
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        elif ext == ".db" or ext == ".sqlite" or ext == ".sqlite3":
            # SQLite 형식
            import pandas as pd
            import sqlite3
            
            conn = sqlite3.connect(data_path)
            cursor = conn.cursor()
            
            # 테이블 목록 조회
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                st.error("데이터베이스에 테이블이 없습니다.")
                return None
            
            # 첫 번째 테이블 사용 (또는 선택 가능)
            table_name = tables[0][0]
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            if df.empty:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"SQLite 처리 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                record = {k: (None if v != v else v) for k, v in record.items()}
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        else:
            # 알 수 없는 형식 - JSONL로 시도
            records = []
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return records if records else None
    
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        return None


def filter_records_without_bible_book(records: List[dict]) -> tuple:
    """성경 본문(bible_book)이 없는 레코드를 제거합니다.

    제거 조건: bible_book 이 None / 빈 문자열 / 공백만 있는 경우

    Returns:
        (필터된_records, 원본_건수, 제거된_건수)
    """
    kept = []
    removed = 0

    for record in records:
        book = record.get("bible_book")
        if book is None or str(book).strip() == "":
            removed += 1
        else:
            kept.append(record)

    return kept, len(records), removed


# 필수 필드: 게시일(published_date — 설교은행 등 출처의 실제 "설교한
# 날짜"가 아니라 게시판에 글이 올라온 날짜. 로그인 없이 접근 가능한
# 목록 페이지에는 이것 하나뿐이라 근사치로 사용), 설교자(preacher),
# 성경본문(bible_book), 설교제목(title) 중 하나라도 비어있으면 레코드를
# 제거한다.
_REQUIRED_FIELDS = ["published_date", "preacher", "bible_book", "title"]


def filter_records_with_required_fields(records: List[dict]) -> tuple:
    """필수 필드(published_date, preacher, bible_book, title) 가 모두
    채워진 레코드만 남깁니다.

    제거 조건: 필수 필드 중 None / 빈 문자열 / 공백만 있는 것이 하나라도 있으면 제거

    Returns:
        (필터된_records, 원본_건수, 제거된_건수)
    """
    kept = []
    removed = 0

    for record in records:
        for field in _REQUIRED_FIELDS:
            val = record.get(field)
            if val is None or str(val).strip() == "":
                removed += 1
                break
        else:
            kept.append(record)

    return kept, len(records), removed


def deduplicate_records(records: List[dict]) -> tuple:
    """중복 데이터를 제거합니다.
    
    중복 조건: title + passage_raw 가 동일한 경우
    
    Returns:
        (중복제거된_records, 원본_건수, 제거된_건수)
    """
    seen = set()
    unique_records = []
    duplicate_count = 0
    
    for record in records:
        # [버그 수정] record.get("title", "")의 기본값 ""는 키가 아예
        # 없을 때만 적용된다 — JSONL 업로드 경로는 CSV/엑셀 경로와 달리
        # 필드를 문자열로 정규화하지 않아 title이 명시적으로 null(None)
        # 이면 그대로 통과, .strip()에서 AttributeError로 업로드 전체가
        # 크래시했다. `or ""`로 None도 함께 처리.
        title = (record.get("title") or "").strip().lower()
        passage = (record.get("passage_raw") or "").strip().lower()
        key = (title, passage)
        
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicate_count += 1
    
    return unique_records, len(records), duplicate_count


@st.cache_resource(ttl=3600)
def analyze_data(records: List[dict]) -> CorpusStatisticsAnalyzer:
    """데이터를 분석합니다"""
    analyzer = CorpusStatisticsAnalyzer()
    analyzer.load_records(records)
    return analyzer


def get_background_data_path() -> str:
    """백그라운드 수집 데이터 파일 경로를 반환합니다.

    [버그 수정] 이전에는 파일이 이미 존재할 때만 경로를 반환했다 —
    그래서 아직 한 번도 수집한 적 없는 상태에서는 "수동 데이터 수집
    실행" 버튼 자체가 화면에 나타나지 않고 CLI 안내문만 보였다(버튼을
    보려면 먼저 CLI로 한 번 수집해야 하는 순환 문제). 파일 존재
    여부와 무관하게 항상 경로를 반환 — DataStore가 없으면 만든다.
    """
    return str(Path(__file__).parent.parent / "data" / "collected_sermons.jsonl")


# 업로드 플로우가 쓰는 것과 동일한 "누계 전체 데이터"(기존 DB) 경로 —
# 백그라운드 수집 검토에서 승인한 레코드도 여기에 append한다.
PERSISTENT_DATA_DIR = Path("data/sermon_corpus/uploaded")
PERSISTENT_DATA_FILE = PERSISTENT_DATA_DIR / "uploaded_sermons.jsonl"

# 검토에서 거부한 레코드의 dedupe key 목록 — 다음 수집/검토 때 다시
# 나타나지 않도록 영구 기록한다.
REVIEW_REJECTED_KEYS_FILE = Path(__file__).parent.parent / "data" / "review_rejected_keys.json"


def _record_dedupe_key(rec: dict) -> tuple:
    """제목+본문+책+장으로 레코드 중복/식별 키를 만든다.

    업로드 병합 로직(main() 안의 동일 로직)과 같은 정의를 공유해야
    "기존 DB"와의 중복 체크가 일관되게 동작한다.
    """
    title = (rec.get("title") or "").strip()
    passage = (rec.get("passage_raw") or rec.get("passage") or "").strip()
    book = (rec.get("bible_book") or rec.get("book") or "").strip()
    chapter = str(rec.get("chapter_start") or rec.get("chapter") or "").strip()
    return (title, passage, book, chapter)


def _load_rejected_review_keys() -> set:
    if not REVIEW_REJECTED_KEYS_FILE.exists():
        return set()
    try:
        raw = json.loads(REVIEW_REJECTED_KEYS_FILE.read_text(encoding="utf-8"))
        return {tuple(k) for k in raw}
    except (json.JSONDecodeError, TypeError):
        return set()


def _save_rejected_review_keys(keys: set) -> None:
    REVIEW_REJECTED_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_REJECTED_KEYS_FILE.write_text(
        json.dumps([list(k) for k in keys], ensure_ascii=False), encoding="utf-8"
    )


def _render_collection_review(bg_data_path: str) -> None:
    """백그라운드로 수집된 데이터를 검토해 선택적으로 수용/거부합니다.

    - 수용: 선택한 레코드를 기존 DB(PERSISTENT_DATA_FILE)에 append하고
      (중복은 건너뜀) 대기 목록에서 제거 — 다음 rerun에서 통계에 반영됨.
    - 거부: 선택한 레코드를 대기 목록에서 제거하고 거부 키로 기록해
      같은 레코드가 나중에 다시 수집돼도 검토 목록에 재등장하지 않게 함.
    - 체크하지 않은 레코드는 그대로 대기 목록에 남아 다음에 다시 검토.
    """
    st.markdown("#### 🕵️ 수집 데이터 검토")

    pending_path = Path(bg_data_path)
    if not pending_path.exists():
        st.caption("검토할 수집 데이터가 없습니다.")
        return

    with open(pending_path, encoding="utf-8") as f:
        pending_records = [json.loads(line) for line in f if line.strip()]

    rejected_keys = _load_rejected_review_keys()
    pending_records = [
        r for r in pending_records if _record_dedupe_key(r) not in rejected_keys
    ]

    if not pending_records:
        st.caption("검토할 새 수집 데이터가 없습니다.")
        return

    st.info(f"검토 대기 중인 수집 데이터 {len(pending_records)}건")

    review_df = pd.DataFrame([
        {
            "선택": True,
            "성경 책": _to_korean_book(r.get("bible_book", "")),
            "본문": r.get("passage_raw", ""),
            "설교 제목": r.get("title", ""),
            "설교자": r.get("preacher") or "",
            "출처": r.get("source", ""),
        }
        for r in pending_records
    ])

    edited_df = st.data_editor(
        review_df,
        hide_index=True,
        use_container_width=True,
        disabled=["성경 책", "본문", "설교 제목", "설교자", "출처"],
        key="collection_review_editor",
    )

    col_accept, col_reject = st.columns(2)
    accept_clicked = col_accept.button("✅ 선택 항목 수용 → 기존 DB에 반영", key="review_accept")
    reject_clicked = col_reject.button("🚫 선택 항목 거부", key="review_reject")

    if not (accept_clicked or reject_clicked):
        return

    selected_mask = edited_df["선택"].tolist()
    selected_records = [r for r, sel in zip(pending_records, selected_mask) if sel]
    remaining_records = [r for r, sel in zip(pending_records, selected_mask) if not sel]

    if not selected_records:
        st.warning("선택된 항목이 없습니다.")
        return

    if accept_clicked:
        existing_records = []
        if PERSISTENT_DATA_FILE.exists():
            with open(PERSISTENT_DATA_FILE, encoding="utf-8") as f:
                existing_records = [json.loads(line) for line in f if line.strip()]
        existing_keys = {_record_dedupe_key(r) for r in existing_records}

        new_records = [
            r for r in selected_records if _record_dedupe_key(r) not in existing_keys
        ]
        skipped = len(selected_records) - len(new_records)

        PERSISTENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(PERSISTENT_DATA_FILE, "a", encoding="utf-8") as f:
            for rec in new_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        st.success(
            f"✅ {len(new_records)}건을 기존 DB에 추가했습니다"
            + (f" (중복 {skipped}건 스킵)" if skipped else "")
            + "."
        )
    else:
        rejected_keys |= {_record_dedupe_key(r) for r in selected_records}
        _save_rejected_review_keys(rejected_keys)
        st.info(f"🚫 {len(selected_records)}건을 거부 처리했습니다.")

    # 처리한(수용/거부) 레코드는 대기 목록에서 제거 — 체크 안 한 것만 남김
    with open(pending_path, "w", encoding="utf-8") as f:
        for rec in remaining_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    st.rerun()


# ============================================================
# UI 레이아웃
# ============================================================

def render_sidebar(analyzer: CorpusStatisticsAnalyzer) -> tuple:
    """사이드바를 렌더링합니다.

    Returns:
        (selected_books, testament_filter) — 선택된 필터 값. main()이
        이 값으로 실제 데이터를 필터링해야 한다(과거엔 위젯만 그려놓고
        반환값을 아무도 쓰지 않아 필터가 화면에 전혀 반영되지 않았음).
    """
    with st.sidebar:
        st.header("📊 필터")

        # 성경 권 필터
        book_frequencies = analyzer.frequency_analyzer.get_book_frequencies()
        all_books = [b["bible_book"] for b in book_frequencies]
        selected_books = st.multiselect(
            "성경 책 선택",
            options=all_books,
            default=all_books,
            help="분석할 성경 책을 선택하세요",
        )

        # 신약/구약 필터
        testament_filter = st.multiselect(
            "신약/구약 필터",
            options=["구약", "신약"],
            default=["구약", "신약"],
            help="구약/신약 필터",
        )

        st.divider()

        # 통계 요약
        st.header("📈 통계 요약")
        stats = analyzer.get_full_statistics()
        st.metric("총 설교 수", f"{stats.total_records:,}")
        st.metric("독립된 성경 책", stats.unique_books)
        st.metric("독립된 장", stats.unique_chapters)

    return selected_books, testament_filter


def render_overview(stats: CorpusStatisticsAnalyzer):
    """전체 개요를 렌더링합니다"""
    st.header("📖 DBMA 설교 대시보드")
    st.markdown("""
    **설교 본문-제목 데이터셋**의 통계 분석 대시보드입니다.
    
    - 성경 권별/장별 설교 빈도
    - 설교 제목 핵심 키워드
    - 본문과 설교 주제의 상관관계
    """)
    
    # 통계 요약 카드
    summary = stats.get_full_statistics()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 설교 수", f"{summary.total_records:,}")
    col2.metric("성경 책 수", summary.unique_books)
    col3.metric("성경 장 수", summary.unique_chapters)
    col4.metric("키워드 수", summary.keyword_summary.get("unique_keywords", 0))


def render_testament_distribution(stats: CorpusStatisticsAnalyzer):
    """신약/구약별 분포를 렌더링합니다"""
    st.subheader("📜 신약/구약별 설교 분포")
    
    testament_freq = stats.frequency_analyzer.get_testament_frequencies()
    
    if not testament_freq:
        st.warning("신약/구약 데이터가 없습니다.")
        return
    
    # 파이 차트 - 구약/신약 순으로 표시
    testament_order = ["OT", "NT"]
    data = []
    for t in testament_order:
        if t in testament_freq:
            d = testament_freq[t]
            label = "구약" if t == "OT" else "신약"
            data.append({"언약": label, "설교 수": d["count"], "비율 (%)": d["percentage"]})
    
    # OT/NT가 없는 경우 추가
    for t in testament_freq:
        if t not in ["OT", "NT"]:
            data.append({"성경": t, "설교 수": testament_freq[t]["count"], "비율 (%)": testament_freq[t]["percentage"]})
    df = pd.DataFrame(data)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=df["언약"],
            values=df["설교 수"],
            hole=0.4,
            textposition="inside",
            textinfo="percent",
        )])
        fig_pie.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.dataframe(df, hide_index=True, use_container_width=True)


def _to_korean_book(book: str) -> str:
    """영어 성경 책명을 한글로 변환"""
    return BIBLE_BOOK_KOREAN_MAP.get(book, book)


def render_book_frequencies(stats: CorpusStatisticsAnalyzer):
    """66권 전체의 설교 빈도(권 이름 + 빈도수)를 렌더링합니다"""
    st.subheader("📚 성경 권별 설교 빈도 (전체 66권)")

    # 데이터에 등장하지 않은 권도 0건으로 표시하기 위해 book_counter가
    # 아니라 정경 순서(BIBLE_BOOKS)를 기준으로 66권 전부를 순회한다.
    counts = dict(stats.frequency_analyzer.book_counter)
    rows = [
        {"bible_book": _to_korean_book(book), "count": counts.get(book, 0)}
        for book, _, _ in stats.frequency_analyzer.BIBLE_BOOKS
    ]

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="bible_book",
        y="count",
        title="성경 권별 설교 빈도 (전체 66권)",
        labels={"bible_book": "성경 책", "count": "설교 수"},
    )
    fig.update_layout(xaxis_tickangle=-45, height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_chapter_frequencies(stats: CorpusStatisticsAnalyzer):
    """장별 설교 빈도를 렌더링합니다"""
    st.subheader("📏 장별 설교 빈도 (상위 20)")
    
    chapter_freq = stats.frequency_analyzer.get_chapter_frequencies(top_k=20)
    
    if not chapter_freq:
        st.warning("장별 데이터가 없습니다.")
        return
    
    df = pd.DataFrame(chapter_freq)
    df["passage"] = df.apply(lambda r: f"{_to_korean_book(r['bible_book'])} {r['chapter']}장", axis=1)
    
    fig = px.bar(
        df,
        x="passage",
        y="count",
        hover_data={"percentage": ":.2f"},
        title="장별 설교 빈도 (상위 20)",
        labels={"passage": "본문", "count": "설교 수", "percentage": "비율 (%)"},
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_keyword_analysis(stats: CorpusStatisticsAnalyzer):
    """키워드 분석을 렌더링합니다"""
    st.subheader("🔑 설교 제목 키워드 분석")
    
    # 상위 키워드
    top_keywords = stats.keyword_extractor.get_top_keywords(top_k=30)

    if not top_keywords:
        st.warning("키워드 데이터가 없습니다.")
        return

    # [기능 강화] 이전에는 트리맵이 path=["word"] 단일 계층이라 클릭해도
    # 확대/축소 외에 아무 반응이 없었다(원래도 최상위 노드라 확대할
    # 곳도 없었음). 1) 주제 카테고리 > 키워드 2단계 계층으로 바꿔
    # 카테고리 조각을 클릭하면 그 안의 키워드들로 확대되도록 하고,
    # 2) on_select로 클릭 이벤트를 받아 실제로 그 키워드가 들어간
    # 설교 제목 목록을 트리맵 아래에 표시한다.
    tree_rows = [
        {
            "category_kr": CATEGORY_KOREAN_MAP.get(kw.get("category"), "기타"),
            "word": kw["word"],
            "freq": kw["frequency"],
        }
        for kw in top_keywords
    ]
    fig_wordcloud = px.treemap(
        pd.DataFrame(tree_rows),
        path=["category_kr", "word"],
        values="freq",
        title="설교 제목 키워드 트리맵 (카테고리 → 키워드, 클릭하면 해당 설교 제목 표시)",
    )
    fig_wordcloud.update_layout(height=450)
    fig_wordcloud.update_traces(hovertemplate="%{label}<br>빈도: %{value}<extra></extra>")

    selection = st.plotly_chart(
        fig_wordcloud,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="keyword_treemap",
    )

    word_set = {kw["word"] for kw in top_keywords}
    clicked_word = None
    points = (selection or {}).get("selection", {}).get("points", [])
    if points:
        label = points[0].get("label") or points[0].get("id")
        if label in word_set:
            clicked_word = label

    if clicked_word:
        st.markdown(f"##### 🔎 \"{clicked_word}\" 키워드가 들어간 설교 제목")
        matching_titles = [
            r.get("title", "")
            for r in (stats.records or [])
            if clicked_word in (r.get("title") or "")
        ]
        if matching_titles:
            st.dataframe(
                pd.DataFrame({"설교 제목": matching_titles[:50]}),
                hide_index=True,
                use_container_width=True,
            )
            if len(matching_titles) > 50:
                st.caption(f"...외 {len(matching_titles) - 50}건 더 있습니다.")
        else:
            st.info("일치하는 설교 제목을 찾지 못했습니다.")
    else:
        st.caption("💡 트리맵에서 키워드 조각을 클릭하면 해당 키워드가 들어간 설교 제목을 볼 수 있습니다.")
    
    # 카테고리 분포 (한글 매핑)
    st.markdown("#### 주제 카테고리 분포")
    top_categories = stats.keyword_extractor.get_top_categories(top_k=15)
    
    if top_categories:
        cat_df = pd.DataFrame(top_categories)
        cat_df["category_kr"] = cat_df["category"].apply(
            lambda c: CATEGORY_KOREAN_MAP.get(c, c)
        )
        fig_cat = px.bar(
            cat_df,
            x="category_kr",
            y="count",
            hover_data={"percentage": ":.2f"},
            title="주제 카테고리 분포",
            labels={"category_kr": "주제", "count": "설교 수", "percentage": "비율 (%)"},
        )
        fig_cat.update_layout(xaxis_tickangle=-30, height=350)
        st.plotly_chart(fig_cat, use_container_width=True)


def render_passage_theme_correlation(stats: CorpusStatisticsAnalyzer):
    """본문-주제 상관관계를 렌더링합니다"""
    st.subheader("🔗 본문-주제 상관관계")
    
    correlations = stats.get_passage_theme_correlation()
    
    if not correlations:
        st.warning("상관관계 데이터가 없습니다.")
        return
    
    # 상위 본문-주제 매핑
    df = pd.DataFrame(correlations)[:30]
    
    # 히트맵
    st.markdown("#### 본문별 주요 주제 히트맵 (상위 10개 본문)")
    
    heatmap_data = correlations[:10]
    heat_df = pd.DataFrame([
        {
            "본문": f"{_to_korean_book(r['bible_book'])} {'?' if r['chapter'] is None else r['chapter']}장",
            "주요 주제": r["dominant_category"],
            "비율 (%)": r["category_percentage"],
            "설교 수": r["total_sermons"],
        }
        for r in heatmap_data
    ])
    
    st.dataframe(heat_df, hide_index=True, use_container_width=True)
    
    # 핵심 주제 per book — 성경 순서(66권 정경 순)로 정렬
    st.markdown("#### 성경 책별 핵심 주제")
    key_themes = stats.compute_key_themes_per_book()

    # FrequencyAnalyzer.BIBLE_BOOKS 에서 canonical 책명 집합과 순서를 가져옴
    try:
        from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
        _bible_order = [book for book, _, _ in FrequencyAnalyzer.BIBLE_BOOKS]
    except Exception:
        _bible_order = list(key_themes.keys())

    # key_themes 에 없는 책은 건너뛰고, 있는 책만 성경 순서대로 정렬
    sorted_books = [b for b in _bible_order if b in key_themes]
    # 성경 순서에 포함되지 않은 나머지 책(예: 데이터에만 있는 책)
    remaining = [b for b in key_themes if b not in set(sorted_books)]
    sorted_books.extend(remaining)

    theme_cols = st.columns(min(len(sorted_books), 5))
    for i, book in enumerate(sorted_books):
        themes = key_themes[book]
        with theme_cols[i % 5]:
            st.markdown(f"**{_to_korean_book(book)}**")
            for theme in themes[:3]:
                st.caption(f"- {theme}")


def render_year_decade_statistics(stats: CorpusStatisticsAnalyzer):
    """연도/연대별 설교 통계를 렌더링합니다"""
    st.subheader("📅 연도/연대별 설교 통계")
    
    # 원본 데이터를 직접 접근
    records = stats.records
    
    if not records:
        st.warning("데이터가 없습니다.")
        return
    
    import pandas as pd
    
    df = pd.DataFrame(records)
    
    # 연도별 통계
    st.markdown("### 연도별 설교 수")
    if "year" in df.columns:
        year_freq = df.groupby("year").size().reset_index(name="설교 수")
        year_freq = year_freq.sort_values("year")
        
        # 누적 합계
        year_freq["누적 설교 수"] = year_freq["설교 수"].cumsum()
        year_freq["비율 (%)"] = (year_freq["설교 수"] / year_freq["설교 수"].sum() * 100).round(1)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_year = px.bar(
                year_freq,
                x="year",
                y="설교 수",
                title="연도별 설교 빈도",
                hover_data=["누적 설교 수", "비율 (%)"],
                labels={"year": "연도"},
            )
            fig_year.update_layout(xaxis_tickangle=-45, height=350)
            st.plotly_chart(fig_year, use_container_width=True)
        
        with col2:
            st.dataframe(year_freq, hide_index=True, use_container_width=True)
    
    # 연대별 통계
    st.markdown("### 연대별 설교 수")
    if "decade" in df.columns:
        decade_freq = df.groupby("decade").size().reset_index(name="설교 수")
        decade_freq = decade_freq.sort_values("decade")
        # [버그 수정] f"{x}s"가 "1980.0s"처럼 영어 접미사 + 소수점
        # artifact를 그대로 노출했다 — "1980년대" 형식으로 한글화.
        decade_freq["연대"] = decade_freq["decade"].apply(lambda x: f"{int(x)}년대")
        
        fig_decade = px.pie(
            decade_freq,
            values="설교 수",
            names="연대",
            title="연대별 설교 분포",
            hole=0.4,
        )
        fig_decade.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_decade, use_container_width=True)
        
        # 연대별 핵심 키워드
        st.markdown("#### 연대별 핵심 키워드")
        decade_keywords = {}
        # [버그 수정] published_date가 없는 레코드는 decade가 NaN인데
        # 이를 그대로 순회/포맷하면 "nans"라는 영어 표기가 컬럼 하나를
        # 통째로 차지했다 — NaN 연대는 건너뛴다.
        for decade in sorted(d for d in df["decade"].unique() if pd.notna(d)):
            decade_df = df[df["decade"] == decade]
            decade_records = decade_df.to_dict("records")
            
            # 간단한 키워드 빈도 계산
            keyword_counts = {}
            for record in decade_records:
                title = record.get("title", "")
                for kw in ["은혜", "믿음", "기도", "사랑", "구원", "소망", "예배", "성령"]:
                    if kw in title:
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            
            # 상위 5개 키워드
            top_kws = sorted(keyword_counts.items(), key=lambda x: -x[1])[:5]
            decade_keywords[f"{int(decade)}년대"] = [kw for kw, _ in top_kws]
        
        kw_cols = st.columns(min(len(decade_keywords), 4))
        for i, (decade, kws) in enumerate(decade_keywords.items()):
            with kw_cols[i % 4]:
                st.markdown(f"**{decade}**")
                for kw in kws:
                    st.caption(f"- {kw}")
    
    # 연도 × 성경 책 히트맵
    st.markdown("### 연도 × 성경 책별 설교 빈도 (상위 10개 책)")
    if "year" in df.columns and "bible_book" in df.columns:
        top_books = df["bible_book"].value_counts().head(10).index.tolist()
        heatmap_df = df[df["bible_book"].isin(top_books)].groupby(["year", "bible_book"]).size().unstack(fill_value=0)
        
        if not heatmap_df.empty:
            # groupby(["year","bible_book"]).unstack()는 마지막 레벨
            # (bible_book)을 컬럼으로 펼치므로 x축=책, y축=연도다.
            # [버그 수정] labels=dict(x="연도", y="성경 책")로 서로
            # 반대로 표시되고 있었다 — 실제 축과 맞게 바로잡고, 책명도
            # 영어 그대로 나오던 것을 한글로 변환.
            x_labels = [_to_korean_book(str(col)) for col in heatmap_df.columns.tolist()]
            y_labels = [str(row) for row in heatmap_df.index.tolist()]

            fig_heatmap = px.imshow(
                heatmap_df.values,
                x=x_labels,
                y=y_labels,
                labels=dict(x="성경 책", y="연도", color="설교 수"),
                title="연도 × 성경 책별 설교 빈도 (상위 10)",
                color_continuous_scale="Blues",
            )
            fig_heatmap.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_heatmap, use_container_width=True)


def render_data_table(stats: CorpusStatisticsAnalyzer):
    """데이터 테이블을 렌더링합니다"""
    st.subheader("📋 데이터 미리보기")
    
    # 샘플 데이터
    sample = []
    for (book, chapter), titles in list(stats.sample_titles.items())[:20]:
        for title in titles:
            sample.append({
                "성경 책": _to_korean_book(book) if book else "알 수 없음",
                "장": chapter or "없음",
                "설교 제목": title,
            })
    
    if sample:
        df = pd.DataFrame(sample)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("샘플 데이터가 없습니다.")


# ============================================================
# 메인 애플리케이션
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="DBMA 설교 대시보드")
    parser.add_argument(
        "--data",
        type=str,
        default=find_default_data_path(),
        help="데이터 파일 경로 (JSONL, CSV, XLSX, TXT, SQLite 지원). 실제 데이터가 있으면 자동 사용.",
    )
    args, unknown = parser.parse_known_args()
    
    # 진행률 상태
    progress = ProgressState()
    
    # 파일 업로드 또는 명령줄 인자
    uploaded_file = None
    data_path = args.data or os.environ.get("DBMA_SERMON_DATA")
    
    st.header("📖 DBMA 설교 대시보드")
    st.markdown("**설교 본문-제목 데이터셋**의 통계 분석 대시보드입니다.")
    
    # 파일 업로드 섹션
    st.markdown("---")
    st.subheader("📂 데이터 로드")
    
    file_types = [".jsonl", ".json", ".csv", ".tsv", ".txt", ".xlsx", ".db", ".sqlite", ".sqlite3"]
    uploaded_file = st.file_uploader(
        "파일 업로드",
        type=file_types,
        help="JSONL, CSV, XLSX, TXT, SQLite 파일 지원\n중복 데이터는 자동으로 제거됩니다"
    )
    
    # 데이터 로드 및 처리
    records = None
    original_count = 0
    duplicate_count = 0
    
    # 영구 저장 경로 (누적 전체 데이터)
    PERSISTENT_DATA_DIR = Path("data/sermon_corpus/uploaded")
    PERSISTENT_DATA_FILE = PERSISTENT_DATA_DIR / "uploaded_sermons.jsonl"
    
    # [버그 수정] CLI 경로에서도 누계 전체 데이터를 분석에 사용 —
    # PERSISTENT_DATA_FILE 이 있으면 그것을 기본 누계 데이터로
    # 간주하고 analyzer 에 전달한다.
    cumulative_records: Optional[List[dict]] = None
    
    if uploaded_file is not None:
        # 진행률 표시
        progress.message = "파일 업로드 중..."
        progress.total = 1
        progress.current = 0
        
        # 임시 파일로 저장
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        progress.message = "데이터 처리 중..."
        
        # 데이터 로드
        records = load_data(tmp_path, progress)
        
        if records is None:
            st.error("데이터를 로드할 수 없습니다. 파일 형식이나 필드 구조를 확인하세요.")
        else:
            original_count = len(records)
            progress.current = progress.total
            progress.message = "본문 필터링 중..."
            
            # 성경 본문이 없는 레코드 제거
            records, _, no_book_removed = filter_records_without_bible_book(records)
            
            progress.message = "필수 필드 검증 중..."
            
            # 필수 필드(published_date, preacher, bible_book, title) 가 모두 있는 레코드만 남김
            records, _, required_removed = filter_records_with_required_fields(records)
            
            progress.message = "중복 제거 중..."
            
            # 업로드 데이터 내 중복 제거
            records, _, dup_internal = deduplicate_records(records)
            duplicate_count += dup_internal
            
            progress.message = "기존 데이터와 병합 중..."
            
            # 영구 저장된 데이터가 있으면 로드하고 중복 체크하여 append
            appended_count = 0
            existing_count = 0
            new_records = []
            if PERSISTENT_DATA_FILE.exists():
                existing_records = []
                with open(PERSISTENT_DATA_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            existing_records.append(json.loads(line))
                existing_count = len(existing_records)
                
                # 기존 데이터의 키 집합 생성 (중복 체크용)
                existing_keys = set()
                for rec in existing_records:
                    title = rec.get('title', '') or rec.get('sermon_title', '') or ''
                    passage = rec.get('passage_raw', '') or rec.get('passage', '') or ''
                    book = rec.get('bible_book', '') or rec.get('book', '') or ''
                    chapter = rec.get('chapter_start', '') or rec.get('chapter', '') or ''
                    key = (title.strip(), passage.strip(), book.strip(), str(chapter).strip())
                    existing_keys.add(key)
                
                # 새 데이터 중 중복 아닌 것만 필터
                for rec in records:
                    title = rec.get('title', '') or rec.get('sermon_title', '') or ''
                    passage = rec.get('passage_raw', '') or rec.get('passage', '') or ''
                    book = rec.get('bible_book', '') or rec.get('book', '') or ''
                    chapter = rec.get('chapter_start', '') or rec.get('chapter', '') or ''
                    key = (title.strip(), passage.strip(), book.strip(), str(chapter).strip())
                    
                    if key not in existing_keys:
                        new_records.append(rec)
                    else:
                        appended_count += 1  # 중복으로 스킵
            else:
                # 영구 저장 파일이 없으면 모두 새 데이터
                new_records = records
            
            duplicate_count += appended_count
            records = new_records
            
            # 영구 저장 (append 모드)
            PERSISTENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
            if PERSISTENT_DATA_FILE.exists():
                # 기존 파일에 추가 작성
                with open(PERSISTENT_DATA_FILE, 'a', encoding='utf-8') as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            else:
                # 새 파일 생성
                with open(PERSISTENT_DATA_FILE, 'w', encoding='utf-8') as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            
            progress.message = "분석 완료!"
            
            # 성공 메시지
            # [버그 수정] original_count는 업로드 파일의 원본 건수(dup_internal
            # 포함)라 duplicate_count(=dup_internal+appended_count)를 그대로
            # 더하면 dup_internal이 두 번 더해져 총건수가 부풀려졌다.
            # 처리 대상 총건수는 original_count 하나로 충분.
            st.success(f"✅ {original_count}건 처리 완료 (본문 없음 {no_book_removed}건, 필수필드 미비 {required_removed}건, 중복 {duplicate_count}건 스킵, 최종 {len(records)}건 추가, 총 누적 {existing_count + len(records):,}건)")

            # 진행률 표시
            st.progress(1.0)
            st.text(f"📊 현재 처리 중: {len(records)} / {original_count} ({progress.percentage:.1f}%)")
        
        # 임시 파일 삭제
        os.unlink(tmp_path)
    
    elif data_path:
        # [버그 수정] --data 로 지정된 파일이 누계 파일(self) 과
        # 동일하면 "새 데이터"가 아니라 "누계 전체 데이터"로 간주한다.
        # (find_default_data_path() 가 uploaded_sermons.jsonl 을
        # 반환하는 경우가 바로 이에 해당)
        if Path(data_path).resolve() == PERSISTENT_DATA_FILE.resolve():
            # 누계 파일 자체를 분석 대상에 사용
            # [버그 수정] records를 대입하지 않고 cumulative_records만
            # 채워서, 바로 아래 "if not records:" 체크가 records=None을
            # 그대로 보고 항상 "로드된 데이터가 없습니다"로 멈췄다 —
            # --data가 누계 파일(기본 경로)을 가리키는, 즉 가장 흔한
            # 기본 실행 경로가 항상 즉시 멈추던 버그.
            cumulative_records = []
            with open(PERSISTENT_DATA_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        cumulative_records.append(json.loads(line))
            records = cumulative_records
            st.info(f"📊 누계 데이터: {len(cumulative_records):,}건 (저장된 전체 데이터)")
        else:
            # 다른 파일 — "추가할 새 데이터"로 처리
            progress.message = "파일 로드 중..."
            records = load_data(data_path, progress)
            
            if records is None:
                st.error(f"데이터 파일을 로드할 수 없습니다: {data_path}")
                st.stop()
            else:
                original_count = len(records)
                # 성경 본문이 없는 레코드 제거
                records, _, no_book_removed = filter_records_without_bible_book(records)
                duplicate_count += no_book_removed
                
                progress.message = "필수 필드 검증 중..."
                
                # 필수 필드(published_date, preacher, bible_book, title) 가 모두 있는 레코드만 남김
                records, _, required_removed = filter_records_with_required_fields(records)
                duplicate_count += required_removed
                
                progress.message = "중복 제거 중..."
                
                records, original_count, dup_after_filter = deduplicate_records(records)
                duplicate_count += dup_after_filter
                st.info(f"📂 {original_count + duplicate_count}건 로드 완료 (본문 없음 {no_book_removed}건, 필수필드 미비 {required_removed}건, 중복 {dup_after_filter}건 제거)")
                
                # 누계 파일이 있으면 그것도 합쳐서 분석
                if PERSISTENT_DATA_FILE.exists():
                    cumulative_records = []
                    with open(PERSISTENT_DATA_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                cumulative_records.append(json.loads(line))
                else:
                    cumulative_records = records
    else:
        st.warning("⚠️ 데이터 파일이 지정되지 않았습니다. 파일을 업로드하거나 `--data PATH` 옵션을 사용하세요.")
        st.info("예시: streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/raw/sermonbank.jsonl")
        return
    
    if not records:
        # 업로드된 데이터가 모두 중복이어서 비어있는 경우
        if uploaded_file is not None:
            st.info("ℹ️ 추가된 데이터가 없습니다. (모든 데이터가 이미 존재함)")
            # 기존 영구 저장 데이터로 분석
            if PERSISTENT_DATA_FILE.exists():
                records = []
                with open(PERSISTENT_DATA_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
                cumulative_records = records  # 누계에도 반영
            else:
                st.error("저장된 데이터가 없습니다.")
                st.stop()
        else:
            st.error("로드된 데이터가 없습니다.")
            st.stop()
    
    # [버그 수정] 분석에는 항상 누계 전체 데이터(cumulative_records) 를 사용
    if cumulative_records is None:
        cumulative_records = records
    
    # 분석
    analyzer = analyze_data(cumulative_records)

    # 중복 제거 통계 표시
    if duplicate_count > 0:
        st.warning(f"⚠️ **중복 데이터 {duplicate_count}건**이 제거되었습니다. (중복 조건: 제목 + 본문)")

    # 사이드바 — [버그 수정] 필터 위젯 반환값을 아무도 안 받아서
    # "성경 책 선택"/"신약/구약 필터"가 화면에 전혀 반영되지 않던
    # 버그. 반환값으로 실제 records를 걸러서 analyzer를 다시 만든다.
    selected_books, testament_filter = render_sidebar(analyzer)

    filtered_records = records
    if selected_books:
        book_set = set(selected_books)
        filtered_records = [r for r in filtered_records if r.get("bible_book") in book_set]
    if testament_filter and len(testament_filter) < 2:
        wanted_testaments = set()
        if "구약" in testament_filter:
            wanted_testaments.add("OT")
        if "신약" in testament_filter:
            wanted_testaments.add("NT")
        filtered_records = [
            r for r in filtered_records
            if analyzer.frequency_analyzer._get_testament(r.get("bible_book", "")) in wanted_testaments
        ]

    if not selected_books or (testament_filter is not None and len(testament_filter) == 0):
        st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다. 사이드바에서 성경 책 또는 신약/구약을 선택하세요.")
        st.stop()

    if len(filtered_records) != len(records):
        analyzer = analyze_data(filtered_records)

    # 메인 콘텐츠
    render_overview(analyzer)
    
    st.divider()
    
    # 언약별 분포
    render_testament_distribution(analyzer)
    
    # 권별 빈도
    render_book_frequencies(analyzer)
    
    # 장별 빈도
    render_chapter_frequencies(analyzer)
    
    # 키워드 분석
    render_keyword_analysis(analyzer)
    
    # 본문-주제 상관관계
    render_passage_theme_correlation(analyzer)
    
    # 연도/연대별 통계 (NEW!)
    render_year_decade_statistics(analyzer)
    
    # 데이터 테이블
    render_data_table(analyzer)
    
    # 백그라운드 수집기 상태
    st.divider()
    _render_background_collector_status()


def _render_background_collector_status():
    """백그라운드 수집기 상태를 렌더링합니다"""
    st.header("🔄 백그라운드 데이터 수집기")

    bg_data_path = get_background_data_path()
    data_store = DataStore(bg_data_path)
    stats = data_store.get_stats()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 데이터 건수", f"{stats['total_records']:,}")
    col2.metric("파일 크기", f"{stats['file_size_bytes'] / 1024:.1f} KB")
    col3.metric("마지막 수정", stats['last_modified'] or "없음")

    # [버그 수정] 이 버튼이 st.info() 메시지 하나만 띄우고 실제로는
    # 아무 수집도 실행하지 않는 완전한 stub이었다("수동 수집이
    # 시작되었습니다. 콘솔을 확인하세요"라고만 말하고 콘솔에는 아무
    # 로그도 안 남았음) — BackgroundCollector.run_once()를 실제로
    # 호출하도록 연결.
    if st.button("📥 수동 데이터 수집 실행", key="manual_collect"):
        from sermon_corpus.collector.background_collector import BackgroundCollector

        # [버그 수정] 스피너 문구가 "설교은행에서 수집 중"으로 고정돼
        # 있어서, 유튜브 수집기를 실제로 연결한 뒤에도 유튜브가 같이
        # 도는지 화면만 보고는 알 수 없었다(실제로는 같이 돌고 있었고
        # 로그에서만 확인 가능했음) — enabled인 출처를 그대로 보여주고,
        # 결과도 출처별로 나눠서 표시.
        sources_cfg = BackgroundCollector(data_path=bg_data_path).config.get("sources", {})
        enabled_sources = [
            sid for sid, cfg in sources_cfg.items() if cfg.get("enabled", True)
        ]
        with st.spinner(
            f"{', '.join(enabled_sources) or '설정된 출처'}에서 수집 중입니다... "
            "(정중한 지연 때문에 몇 초~몇 분 걸릴 수 있습니다)"
        ):
            try:
                collector = BackgroundCollector(data_path=bg_data_path)
                result = collector.run_once()
            except Exception as e:
                st.error(f"수집 중 오류가 발생했습니다: {e}")
            else:
                by_source = result.get("by_source", {})
                breakdown = ", ".join(
                    f"{sid} {info['collected']}건(신규 {info['saved']}건)"
                    for sid, info in by_source.items()
                )
                st.success(
                    f"✅ 수집 완료 — {breakdown or '수집 결과 없음'} "
                    f"(합계 {result['total_collected']}건 수집, {result['total_saved']}건 저장, "
                    f"{result['total_duplicates']}건 중복, {result['total_errors']}건 오류, "
                    f"누적 {result['data_store']['total_records']:,}건)"
                )
                st.rerun()

    st.divider()
    _render_collection_review(bg_data_path)

    with st.expander("CLI로 직접 실행하기"):
        st.markdown("""
        터미널에서 직접 실행하려면:
        ```bash
        cd ~/DBMA
        source ~/envs/dbma311/bin/activate
        python scripts/background_collector.py --once
        ```

        또는 데몬 모드로 지속적으로 실행:
        ```bash
        python scripts/background_collector.py --daemon
        ```
        """)


if __name__ == "__main__":
    main()
