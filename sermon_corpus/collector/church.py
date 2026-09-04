# DBMA Sermon Corpus - 교회 웹사이트 크롤러
# 100개 이상의 한인 교회 웹사이트에서 설교 데이터를 수집
"""
교회 웹사이트에서 설교 목록 및 본문 데이터를 크롤링합니다.

지원 패턴:
  1. 그누보드 게시판 (대부분의 한인 교회)
     - /bbs/board.php?bo_table=sermon
     - /board.php?bo_table=sermon
     - /bbs/board.php?bo_table=gospel
  2. WordPress 설교 플러그인
     - /sermons/ endpoint
  3. 일반 HTML 게시판 (테이블 기반)
  4. RSS 피드
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

from sermon_corpus.collector.polite_fetcher import PoliteFetcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

@dataclass
class SermonRecord:
    """정규화 설교 레코드"""
    source: str                    # church:<domain>
    source_type: str               # "church_website"
    title: str
    passage: str                   # "창세기 1:1-3" 등
    bible_book: str                # "Genesis", "Exodus" 등 (대시보드용)
    chapter: Optional[int] = None  # 장
    preacher: str = ""
    date: str = ""                 # YYYY-MM-DD
    url: str = ""
    html_snippet: str = ""
    collected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ChurchSource:
    """단일 교회 소스 설정"""
    name: str
    domain: str
    base_url: str
    sermon_list_path: str            # 설교 목록 페이지 경로
    bo_table: str = "sermon"         # 그누보드 bo_table
    is_korean: bool = True           # 한국어 UI
    custom_selectors: dict = field(default_factory=dict)
    rss_feed_url: str = ""
    enabled: bool = True


# ---------------------------------------------------------------------------
# 교회 목록 정의 (100개)
# ---------------------------------------------------------------------------

def _make_church(name: str, domain: str, list_path: str = "/bbs/board.php?bo_table=sermon", bo_table: str = "sermon") -> ChurchSource:
    return ChurchSource(
        name=name,
        domain=domain,
        base_url=f"https://{domain}",
        sermon_list_path=list_path,
        bo_table=bo_table,
    )

# 미국 (West Coast) - 16개
_CHURCHES_US_WEST = [
    _make_church("남가주사랑의교회", "klac.org"),
    _make_church("LA나비교회", "navichurch.org"),
    _make_church("나성영락교회", "youngnak.com"),
    _make_church("ANC온누리교회", "anconnuri.org"),
    _make_church("베델교회 (LA)", "bethelusa.org"),
    _make_church("남가주동신교회", "dsch.org"),
    _make_church("은혜교회", "graceministry.org"),
    _make_church("LA 감리교회", "laumc.org"),
    _make_church("새 생명 비전교회", "newlifevision.org"),
    _make_church("주님의교회 (LA)", "thelordschurch.org"),
    _make_church("충현선교교회", "chunghyun.org"),
    _make_church("얼바인 베델교회", "irvinebethel.org"),
    _make_church("오렌지카운티 디사이플스 교회", "dc-church.org"),
    _make_church("샌디에이고 연합교회", "sduc.org"),
]

# 미국 (East Coast / NY / NJ) - 10개
_CHURCHES_US_EAST = [
    _make_church("뉴욕참된교회", "truenyc.org"),
    _make_church("뉴욕교회", "nychurch.org"),
    _make_church("뉴욕장로교회", "nympc.org"),
    _make_church("뉴욕 프라미스교회", "promiseny.com"),
    _make_church("뉴저지 온누리교회", "njonnuri.org"),
    _make_church("뉴저지 연합교회", "njuc.org"),
    _make_church("상록교회 (뉴저지)", "evergreenchurch.org"),
    _make_church("필라델피아 안디옥교회", "antiochphilly.org"),
    _make_church("워싱턴 중앙장로교회", "kcpc.org"),
    _make_church("워싱턴 연합장로교회", "yuko.org"),
]

# 미국 (Midwest / South) - 9개
_CHURCHES_US_MID = [
    _make_church("시카고 한인제일장로교회", "firstkoreanchurch.org"),
    _make_church("시카고 연합장로교회", "cuc.org"),
    _make_church("아틀란타 한인교회", "atlantakoreanchurch.org"),
    _make_church("연합장로교회 (아틀란타)", "pyuc.org"),
    _make_church("달라스 연합교회", "duc.org"),
    _make_church("휴스턴 서울침례교회", "houstonseoul.org"),
    _make_church("시애틀 연합장로교회", "seattleuc.org"),
    _make_church("벤쿠버 영락교회", "vancuveryoungnak.com"),
    _make_church("토론토 큰빛교회", "lkpc.org"),
]

# 미국 (Hawaii / Virginia) - 2개
_CHURCHES_US_OTHER = [
    _make_church("하와이 한인기독교회", "kccuhawaii.org"),
    _make_church("버지니아 한인교회", "kcbva.org"),
]

# 국내 주요 대형교회 - 40개
_CHURCHES_KR_MAIN = [
    _make_church("사랑의교회", "sarang.org"),
    _make_church("온누리교회", "onnuri.org"),
    _make_church("우리교회", "woorich.or.kr"),
    _make_church("지구촌교회", "jiguchon.org"),
    _make_church("분당우리교회", "bundangwoori.org"),
    _make_church("수영로교회", "sooyoungro.org"),
    _make_church("새에덴교회", "saedeen.org"),
    _make_church("여의도순복음교회", "fgtv.com"),
    _make_church("광림교회", "kwanglim.org"),
    _make_church("소망교회", "somang.net"),
    _make_church("영락교회", "youngnak.or.kr"),
    _make_church("금란교회", "kumran.or.kr"),
    _make_church("오륜교회", "oryun.org"),
    _make_church("선한목자교회", "gsmchurch.or.kr"),
    _make_church("남서울교회", "nsm.or.kr"),
    _make_church("왕성교회", "wangsung.or.kr"),
    _make_church("충현교회", "chunghyun.or.kr"),
    _make_church("안산동산교회", "dongsan.or.kr"),
    _make_church("하남교회", "hanam.or.kr"),
    _make_church("만나교회", "manna.or.kr"),
    _make_church("포항제일교회", "pohangjeil.or.kr"),
    _make_church("대구제일교회", "daegujeil.org"),
    _make_church("부산중앙교회", "bsjungang.or.kr"),
    _make_church("삼일교회", "samil.or.kr"),
    _make_church("높은뜻정의교회", "godislove.or.kr"),
    _make_church("높은뜻광성교회", "kwangsung.or.kr"),
    _make_church("성락성결교회", "sungrak.or.kr"),
    _make_church("신촌성결교회", "sinchon.or.kr"),
    _make_church("충신교회", "chungshin.or.kr"),
    _make_church("서울교회", "seoul.or.kr"),
    _make_church("학동교회", "hakdong.org"),
    _make_church("인천순복음교회", "icfg.or.kr"),
    _make_church("청주 상당교회", "sd.or.kr"),
    _make_church("대전중앙교회", "djcc.or.kr"),
    _make_church("전주바울교회", "baul.or.kr"),
    _make_church("제주영락교회", "jejyoung.or.kr"),
    _make_church("창원한빛교회", "hanbit.or.kr"),
    _make_church("울산대영교회", "daeyoung.or.kr"),
    _make_church("수원중앙침례교회", "swbc.or.kr"),
    _make_church("강남중앙침례교회", "kjbc.or.kr"),
]

# 침례교 계열 - 25개
_CHURCHES_KR_BAPTIST = [
    _make_church("지구촌침례교회", "jiguchon.or.kr"),
    _make_church("글로벌선진교회", "gcs.or.kr"),
    _make_church("대전대흥침례교회", "daeheung.or.kr"),
    _make_church("포항중앙침례교회", "phbc.or.kr"),
    _make_church("천안중앙침례교회", "cac.or.kr"),
    _make_church("전주침례교회", "jjbc.or.kr"),
    _make_church("부산침례교회", "bsbc.or.kr"),
    _make_church("창원침례교회", "cwbc.or.kr"),
    # [버그 수정 2026-07-22] "kjbc.or.kr"은 강남중앙침례교회(172행)와
    # 도메인이 겹쳐 있었다 — collect_churches()가 도메인 기반으로 출력
    # 파일명을 만들어 두 교회 데이터가 서로 덮어써지는 문제가 있었다.
    # 광주침례교회의 실제 도메인을 확인할 때까지 비활성화한다.
    ChurchSource(
        name="광주침례교회",
        domain="kjbc.or.kr",
        base_url="https://kjbc.or.kr",
        sermon_list_path="/bbs/board.php?bo_table=sermon",
        bo_table="sermon",
        enabled=False,
    ),
    _make_church("춘천침례교회", "ccbc.or.kr"),
    _make_church("필그림교회", "pilgrimm.org"),
    _make_church("타코마 중앙선교교회", "tacomakcc.org"),
    _make_church("시애틀 큰빛교회", "seattlelight.org"),
    _make_church("샌프란시스코 연합침례교회", "sfubc.org"),
    _make_church("달라스 세광교회", "skbc.org"),
    _make_church("애틀랜타 연합침례교회", "aubc.org"),
    _make_church("시카고 침례교회", "chicagobc.org"),
    _make_church("뉴욕 한인침례교회", "nyfbc.org"),
    _make_church("워싱턴 침례교회", "wbchurch.org"),
    _make_church("토론토 영락교회", "torontoyoungnak.com"),
    _make_church("빛과소금교회", "lightandsalt.or.kr"),
    _make_church("성문교회", "smch.or.kr"),
    _make_church("과천교회", "kwachun.or.kr"),
    _make_church("할렐루야교회", "halleluyah.or.kr"),
    _make_church("주안장로교회", "juan.or.kr"),
]

# 전체 교회 목록
ALL_CHURCHES = (
    _CHURCHES_US_WEST + _CHURCHES_US_EAST + _CHURCHES_US_MID +
    _CHURCHES_US_OTHER + _CHURCHES_KR_MAIN + _CHURCHES_KR_BAPTIST
)


# ---------------------------------------------------------------------------
# Bible book 매핑 (한국어 설교 제목에서 추론용)
# ---------------------------------------------------------------------------

BIBLE_BOOK_MAP = {
    # 구약
    "창세기": "Genesis", "genesis": "Genesis",
    "출애굽기": "Exodus", "exodus": "Exodus",
    "레위기": "Leviticus", "leviticus": "Leviticus",
    "민수기": "Numbers", "numbers": "Numbers",
    "신명기": "Deuteronomy", "deuteronomy": "Deuteronomy",
    "여호수아": "Joshua", "joshua": "Joshua",
    "사사기": "Judges", "judges": "Judges",
    "룻": "Ruth", "ruth": "Ruth",
    "사무엘상": "1 Samuel", "1samuel": "1 Samuel", "삼상": "1 Samuel",
    "사무엘하": "2 Samuel", "2samuel": "2 Samuel", "삼하": "2 Samuel",
    "열왕기상": "1 Kings", "1kings": "1 Kings", "왕상": "1 Kings",
    "열왕기하": "2 Kings", "2kings": "2 Kings", "왕하": "2 Kings",
    "역대상": "1 Chronicles", "1chronicles": "1 Chronicles", "대상": "1 Chronicles",
    "역대하": "2 Chronicles", "2chronicles": "2 Chronicles", "대하": "2 Chronicles",
    "에스라": "Ezra", "ezra": "Ezra",
    "느헤미야": "Nehemiah", "nehemiah": "Nehemiah",
    "에스더": "Esther", "esther": "Esther",
    "욥": "Job", "job": "Job",
    "시편": "Psalms", "psalms": "Psalms", "시": "Psalms",
    "잠언": "Proverbs", "proverbs": "Proverbs",
    "전도서": "Ecclesiastes", "ecclesiastes": "Ecclesiastes",
    "아가": "Song of Solomon", "songofsolomon": "Song of Solomon",
    "이사야": "Isaiah", "isaiah": "Isaiah",
    "예레미야": "Jeremiah", "jeremiah": "Jeremiah",
    "예레미야애가": "Lamentations", "lamentations": "Lamentations",
    "에스겔": "Ezekiel", "ezekiel": "Ezekiel",
    "다니엘": "Daniel", "daniel": "Daniel",
    "호세아": "Hosea", "hosea": "Hosea",
    "요엘": "Joel", "joel": "Joel",
    "아모스": "Amos", "amos": "Amos",
    "오바댜": "Obadiah", "obadiah": "Obadiah",
    "요나": "Jonah", "jonah": "Jonah",
    "미가": "Micah", "micah": "Micah",
    "나훔": "Nahum", "nahum": "Nahum",
    "하박국": "Habakkuk", "habakkuk": "Habakkuk",
    "스바냐": "Zephaniah", "zephaniah": "Zephaniah",
    "학개": "Haggai", "haggai": "Haggai",
    "스가랴": "Zechariah", "zechariah": "Zechariah",
    "말라기": "Malachi", "malachi": "Malachi",
    # 신약
    "마태오": "Matthew", "마태복음": "Matthew", "matthew": "Matthew",
    "마가복음": "Mark", "mark": "Mark",
    "누가복음": "Luke", "luke": "Luke",
    "요한복음": "John", "john": "John",
    "사도행전": "Acts", "acts": "Acts",
    "로마서": "Romans", "romans": "Romans",
    "고린도전서": "1 Corinthians", "1corinthians": "1 Corinthians", "고전": "1 Corinthians",
    "고린도후서": "2 Corinthians", "2corinthians": "2 Corinthians", "고후": "2 Corinthians",
    "갈라디아서": "Galatians", "galatians": "Galatians",
    "에베소서": "Ephesians", "ephesians": "Ephesians",
    "빌립보서": "Philippians", "philippians": "Philippians",
    "골로새서": "Colossians", "colossians": "Colossians",
    "데살로니가전서": "1 Thessalonians", "1thessalonians": "1 Thessalonians", "데전": "1 Thessalonians",
    "데살로니가후서": "2 Thessalonians", "2thessalonians": "2 Thessalonians", "데후": "2 Thessalonians",
    "디모데전서": "1 Timothy", "1timothy": "1 Timothy", "딤전": "1 Timothy",
    "디모데후서": "2 Timothy", "2timothy": "2 Timothy", "딤후": "2 Timothy",
    "디도서": "Titus", "titus": "Titus",
    "빌레몬서": "Philemon", "philemon": "Philemon",
    "히브리서": "Hebrews", "hebrews": "Hebrews",
    "야고보서": "James", "james": "James",
    "베드로전서": "1 Peter", "1peter": "1 Peter", "벧전": "1 Peter",
    "베드로후서": "2 Peter", "2peter": "2 Peter", "벧후": "2 Peter",
    "요한일서": "1 John", "1john": "1 John", "요일": "1 John",
    "요한이서": "2 John", "2john": "2 John", "요이": "2 John",
    "요한삼서": "3 John", "3john": "3 John", "요삼": "3 John",
    "유다서": "Jude", "jude": "Jude",
    "요한계시록": "Revelation", "revelation": "Revelation", "계시록": "Revelation",
}

# 장 번호 매핑 (예: "창 1:1" 에서 장 = 1)
CHAPTER_PATTERN = re.compile(r"(?:창|출|레|민|신|수|사|룻|삼상|삼하|왕상|왕하|대상|대하|에스라|느|에스더|욥|시|잠|전|아|사사|렘|애|겔|단|호| Joel|암|옵|욜|미|나|하|습|학|슥|말|마|막|눅|요|행|롬|고전|고후|갈|엡|빌|골|데전|데후|딤전|딤후|디|몬|히|약|벧전|벧후|요일|요이|요삼|유|계)\s*(\d+):")


# ---------------------------------------------------------------------------
# bible_book 및 chapter 추출
# ---------------------------------------------------------------------------

def extract_bible_info(text: str) -> tuple[str, Optional[int]]:
    """
    설교 제목/본문 텍스트에서 bible_book 과 chapter 를 추출.

    Returns:
        (bible_book, chapter) - chapter 는 없으면 None
    """
    if not text:
        return ("Unknown", None)

    # Bible book 매핑으로 검색
    for key, book in BIBLE_BOOK_MAP.items():
        if key.lower() in text.lower():
            # 장 번호도 함께 추출
            m = CHAPTER_PATTERN.search(text)
            chapter = int(m.group(1)) if m else None
            return (book, chapter)

    return ("Unknown", None)


# ---------------------------------------------------------------------------
# 그누보드 게시판 파서
# ---------------------------------------------------------------------------

def _parse_gnuboard_list(html: str, church: ChurchSource) -> list[SermonRecord]:
    """
    그누보드 기반 설교 목록 페이지에서 항목을 추출.

    일반적인 그누보드 구조:
      <table class="board_list"> 또는 <div class="board_list">
        <tr>
          <td class="name"><a href="/bbs/board.php?bo_table=sermon&wr_id=NNN">설교제목</a></td>
          <td class="subject">본문</td>
          <td class="date">YYYY-MM-DD</td>
          <td class="nickname">설교자</td>
        </tr>
      </table>
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    records: list[SermonRecord] = []

    # CSS selector 우선순위 (custom_selectors에서 오버라이드 가능)
    row_selector = church.custom_selectors.get("row", "tr, li.board_item")
    title_selector = church.custom_selectors.get("title", "a[href*='wr_id='], span.f_s_list a")
    passage_selector = church.custom_selectors.get("passage", "td.subject, span.f_d2_6")
    date_selector = church.custom_selectors.get("date", "td.date, span.f_d1_6")
    preacher_selector = church.custom_selectors.get("preacher", "td.nickname, span.member")

    rows = soup.select(row_selector)
    for row in rows:
        try:
            # 제목
            title_el = row.select_one(title_selector)
            if not title_el or not title_el.get("href"):
                continue
            title = title_el.get_text(strip=True)

            # URL
            href_val = title_el.get("href")
            if isinstance(href_val, list):
                href = href_val[0] if href_val else ""
            elif href_val is None:
                href = ""
            else:
                href = str(href_val)
            base = church.base_url
            full_url = urljoin(base, href)

            # 본문
            passage_el = row.select_one(passage_selector)
            passage = passage_el.get_text(strip=True) if passage_el else ""

            # 날짜
            date_el = row.select_one(date_selector)
            date_str = date_el.get_text(strip=True) if date_el else ""
            # 날짜 정규화 (YYYY-MM-DD 형식)
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
            date_str = date_match.group(1) if date_match else date_str

            # 설교자
            preacher_el = row.select_one(preacher_selector)
            preacher = preacher_el.get_text(strip=True) if preacher_el else ""

            # Bible info 추출
            bible_book, chapter = extract_bible_info(f"{title} {passage}")

            record = SermonRecord(
                source=f"church:{church.domain}",
                source_type="church_website",
                title=title,
                passage=passage,
                bible_book=bible_book,
                chapter=chapter,
                preacher=preacher,
                date=date_str,
                url=full_url,
            )
            records.append(record)

        except Exception as exc:
            logger.debug("parse row error (%s): %s", church.domain, exc)
            continue

    return records


# ---------------------------------------------------------------------------
# 개별 설교 페이지 파서 (보충용)
# ---------------------------------------------------------------------------

def _parse_sermon_page(html: str, record: SermonRecord) -> SermonRecord:
    """
    개별 설교 페이지에서 추가 메타데이터를 추출.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # 본문 본문이 <p> 태그로 들어있는 경우
    content = soup.find("div", class_=re.compile(r"content|article|post|view-content"))
    if not content:
        content = soup.find("div", id=re.compile(r"content|article"))
    if not content:
        content = soup.find("article")

    if content:
        paragraphs = content.find_all("p")
        full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        record.html_snippet = full_text[:2000]  # 첫 2000자만 저장

    return record


# ---------------------------------------------------------------------------
# 단일 교회 수집
# ---------------------------------------------------------------------------

def collect_church(
    church: ChurchSource,
    fetcher: PoliteFetcher,
    max_items: int = 50,
    scrape_individual: bool = False,
) -> list[SermonRecord]:
    """
    단일 교회에서 설교 목록을 수집.

    Args:
        church: ChurchSource 설정
        fetcher: PoliteFetcher 인스턴스
        max_items: 최대 수집 항목 수
        scrape_individual: 개별 설교 페이지도 스크랩할지 여부

    Returns:
        SermonRecord 리스트
    """
    records: list[SermonRecord] = []

    # 목록 페이지 URL 구성
    list_url = f"{church.base_url}{church.sermon_list_path}"
    if "?" not in church.sermon_list_path:
        list_url += f"?bo_table={church.bo_table}"

    logger.info("collect_church: %s (%s) -> %s", church.name, church.domain, list_url)

    try:
        html = fetcher.get_text(list_url)
        if not html:
            logger.warning("collect_church: no HTML for %s", church.domain)
            return records

        # 그누보드 파서
        records = _parse_gnuboard_list(html, church)

        # 개별 페이지 스크랩
        if scrape_individual and len(records) < max_items:
            for rec in records[:max_items - len(records)]:
                try:
                    page_html = fetcher.get_text(rec.url)
                    if page_html:
                        _parse_sermon_page(page_html, rec)
                except Exception as exc:
                    logger.debug("scrape page error (%s): %s", rec.url, exc)

        logger.info("collect_church: %s -> %d items", church.domain, len(records))

    except Exception as exc:
        logger.error("collect_church FAILED %s: %s", church.domain, exc)

    return records


# ---------------------------------------------------------------------------
# 배치 수집 (여러 교회)
# ---------------------------------------------------------------------------

def collect_churches(
    churches: list[ChurchSource],
    output_dir: str = "data/sermon_corpus/church",
    max_items_per_church: int = 50,
    scrape_individual: bool = False,
    delay_range: tuple = (3.0, 8.0),
) -> list[SermonRecord]:
    """
    여러 교회에서 설교 데이터를 수집하고 JSONL로 저장.

    Args:
        churches: 수집할 ChurchSource 리스트
        output_dir: 출력 디렉토리
        max_items_per_church: 교회별 최대 수집 수
        scrape_individual: 개별 페이지 스크랩 여부
        delay_range: 요청 간 딜레이 범위 (초)

    Returns:
        모든 교회에서 수집한 SermonRecord 리스트
    """
    fetcher = PoliteFetcher(
        min_delay=delay_range[0],
        max_delay=delay_range[1],
    )

    all_records: list[SermonRecord] = []
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, church in enumerate(churches):
        if not church.enabled:
            logger.info("skipped (disabled): %s", church.name)
            continue

        logger.info("[%d/%d] collecting %s (%s)", i + 1, len(churches), church.name, church.domain)

        records = collect_church(
            church=church,
            fetcher=fetcher,
            max_items=max_items_per_church,
            scrape_individual=scrape_individual,
        )

        # JSONL 저장 (교회별 파일)
        safe_name = re.sub(r"[^\w\-]", "_", church.domain)
        file_path = output_path / f"church_{safe_name}.jsonl"
        with open(file_path, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

        all_records.extend(records)

        # 교회 간 딜레이 (과부하 방지)
        if i < len(churches) - 1:
            logger.info("delay %.1f seconds between churches...", fetcher.max_delay)
            fetcher._wait()

    # 전체 합치기 JSONL
    master_path = output_path / "all_church_sermons.jsonl"
    with open(master_path, "w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    logger.info("collect_churches: total %d items from %d churches", len(all_records), len(churches))
    return all_records


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------

def main():
    """CLI에서 실행하는 경우"""
    import argparse

    parser = argparse.ArgumentParser(description="교회 웹사이트 설교 크롤러")
    parser.add_argument("--output", default="data/sermon_corpus/church", help="출력 디렉토리")
    parser.add_argument("--max-items", type=int, default=50, help="교회별 최대 수집 수")
    parser.add_argument("--scrape-pages", action="store_true", help="개별 설교 페이지도 스크랩")
    parser.add_argument("--churches", nargs="+", help="수집할 교회 도메인 (생략 시 전체)")
    parser.add_argument("--delay-min", type=float, default=5.0)
    parser.add_argument("--delay-max", type=float, default=12.0)
    args = parser.parse_args()

    churches = ALL_CHURCHES
    if args.churches:
        churches = [c for c in ALL_CHURCHES if c.domain in args.churches]

    records = collect_churches(
        churches=churches,
        output_dir=args.output,
        max_items_per_church=args.max_items,
        scrape_individual=args.scrape_pages,
        delay_range=(args.delay_min, args.delay_max),
    )
    print(f"Collected {len(records)} sermons from {len(churches)} churches.")


if __name__ == "__main__":
    main()