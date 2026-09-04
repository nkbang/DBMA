# DBMA Sermon Corpus - 교회 웹사이트 설교 수집기 (우리들교회)
#
# sermonbank.net과 달리 로그인 없이 설교 "요약본"(주일설교요약 게시판)
# 텍스트 전문을 볼 수 있는 실제 교회 공식 사이트를 대상으로 한다.
# 2026-07-23 실측 확인: https://woori.cc/board/G00068/list
# (robots.txt에서 /board/G00068/ 은 차단되지 않음)

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from sermon_corpus.collector.sermonbank import BibleReferenceParser, SermonRecord, compute_dedupe_key


# 실측 확인한 제목 형식: "[국문] 7월12일 사무엘하 20:18~22 [충성된 자]"
# - 월/일: 대체로 실제 설교(게시)와 같은 주라 근사 설교일로 사용
# - 책명+장:절(~절 또는 ~장:절): 본문 참조
# - 대괄호 안: 설교 제목
_TITLE_PATTERN = re.compile(
    r"(\d{1,2})월(\d{1,2})일\s*(\S+?)\s*(\d+:\d+(?:~\d+(?::\d+)?)?)\s*\[(.+?)\]"
)

# 설교자 이름 — 본문(.cont_row) 안에서 "OOO 목사" 형태의 첫 문단만 인정
# (사이트 전역 내비게이션에도 "김양재 목사" 같은 문구가 반복돼서, 본문
# 컨테이너 밖에서 찾으면 담임목사 이름을 잘못 채택하기 쉽다 — 실측 확인).
_PREACHER_PATTERN = re.compile(r"^([가-힣]{2,4})\s?(목사님|목사|전도사님|전도사)$")


class WooriChurchCollector:
    """우리들교회(woori.cc) 주일설교요약 게시판 수집기."""

    BASE_URL = "https://woori.cc"
    LIST_PATH = "/board/G00068/list"

    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get("source_id", "woori_church")
        self.storage_path = Path(config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/woori_church.jsonl"
        ))
        self.bible_parser = BibleReferenceParser()
        self._seen_keys: set = set()
        self.stats = {
            "urls_processed": 0,
            "sermons_collected": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    @staticmethod
    def _paginate_url(page: int) -> str:
        base = f"{WooriChurchCollector.BASE_URL}{WooriChurchCollector.LIST_PATH}"
        return base if page <= 1 else f"{base}?page={page}"

    def parse_list_page(self, html: str) -> List[Dict]:
        """목록 페이지에서 (wr_id, title_raw, list_date) 후보를 뽑는다."""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for row in soup.select("table.tbl_list01 tbody tr"):
            link = row.select_one("td.title a")
            date_cell = row.select_one("td.date")
            if not link:
                continue
            href = link.get("href", "")
            match = re.search(r"/board/G00068/view/(\d+)", str(href))
            if not match:
                continue
            items.append({
                "wr_id": match.group(1),
                "title_raw": link.get_text(strip=True),
                "list_date": date_cell.get_text(strip=True) if date_cell else "",
                "detail_url": f"{self.BASE_URL}{href}" if str(href).startswith("/") else str(href),
            })
        return items

    def _extract_preacher(self, detail_html: str) -> Optional[str]:
        """상세 페이지 본문(.cont_row)에서 설교자 이름을 찾는다."""
        soup = BeautifulSoup(detail_html, "html.parser")
        cont = soup.select_one("div.cont_row")
        if not cont:
            return None
        for p in cont.find_all("p"):
            text = p.get_text(strip=True)
            if not text:
                continue
            match = _PREACHER_PATTERN.match(text)
            if match:
                return match.group(1)
        return None

    def _parse_published_date(self, month: str, day: str, list_date: str) -> Optional[str]:
        """제목의 "N월N일"(근사 설교일)과 목록의 게시연도를 합쳐 날짜를 만든다."""
        year_match = re.match(r"(\d{4})", list_date)
        if not year_match:
            return None
        try:
            return datetime(int(year_match.group(1)), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    def parse_item(self, item: Dict, detail_html: Optional[str]) -> Optional[SermonRecord]:
        title_match = _TITLE_PATTERN.search(item["title_raw"])
        if not title_match:
            return None

        month, day, book_raw, passage_part, sermon_title = title_match.groups()
        passage_raw = f"{book_raw} {passage_part.replace('~', '-')}"
        passage_data = self.bible_parser.parse(passage_raw)

        if passage_data.get("kind") != "confirmed":
            return None

        preacher = self._extract_preacher(detail_html) if detail_html else None
        published_date = self._parse_published_date(month, day, item.get("list_date", ""))

        dedupe_key = compute_dedupe_key(sermon_title, passage_raw)

        return SermonRecord(
            record_id=f"woori_{dedupe_key}",
            source=self.source_id,
            title=sermon_title,
            passage_raw=passage_raw,
            bible_book=passage_data.get("bible_book") or "Unknown",
            chapter_start=passage_data.get("chapter_start") or 0,
            chapter_end=passage_data.get("chapter_end"),
            verse_start=passage_data.get("verse_start"),
            verse_end=passage_data.get("verse_end"),
            preacher=preacher,
            published_date=published_date,
            source_url=item["detail_url"],
            collected_at=datetime.utcnow().isoformat(),
        )

    def is_duplicate(self, dedupe_key: str) -> bool:
        if dedupe_key in self._seen_keys:
            return True
        self._seen_keys.add(dedupe_key)
        return False

    def collect_all(self, fetcher, max_records: int = None, max_pages: int = 10) -> List[SermonRecord]:
        """목록 페이지들을 페이지네이션으로 순회하며 설교를 수집한다.

        각 항목마다 상세 페이지를 한 번 더 요청해 설교자 이름을 확보한다
        (목록에는 "관리자"만 나오고 실제 설교자는 상세 본문에만 있음,
        실측 확인) — 요청 수가 배로 늘지만 PoliteFetcher가 매 요청마다
        정중한 지연을 적용한다.
        """
        all_records: List[SermonRecord] = []

        for page in range(1, max_pages + 1):
            url = self._paginate_url(page)
            text = fetcher.get_text(url)
            if not text:
                break
            self.stats["urls_processed"] += 1

            items = self.parse_list_page(text)
            if not items:
                break

            for item in items:
                try:
                    detail_html = fetcher.get_text(item["detail_url"])
                    record = self.parse_item(item, detail_html)
                    if record is None:
                        continue
                    if self.is_duplicate(record.dedupe_key):
                        continue
                    all_records.append(record)
                    self.stats["sermons_collected"] += 1
                except Exception:
                    self.stats["errors"] += 1
                    continue

                if max_records and len(all_records) >= max_records:
                    return all_records

        return all_records
