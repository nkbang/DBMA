# DBMA Sermon Corpus - 새삶교회(saesamm.com) 설교 수집기
#
# 2026-07-23 실측 확인: https://www.saesamm.com/bbs/board.php?bo_table=sermon
# robots.txt 없음(전면 허용). 그누보드 갤러리형 스킨(Crown_Ministry 계열)이며,
# 목록에 이미 설교자/날짜가 노출되고, 상세 페이지에는 table#sermon-info에
# "설교자"/"설교본문"/"설교날짜" th/td 쌍이 명시적으로 라벨링돼 있어 다른
# 그누보드 사이트보다 필드 구분이 훨씬 명확하다(실측 확인).

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from sermon_corpus.collector.sermonbank import BibleReferenceParser, SermonRecord, compute_dedupe_key

# 목록 항목 제목은 "R479 롬(3) 삶의 방향: 믿음의 분량대로"처럼 관리번호가
# 앞에 붙는다 — 실제 설교 제목이 아니므로 떼어낸다(실측 확인).
_TITLE_PREFIX_PATTERN = re.compile(r"^R\d+\s*")


class SaesammCollector:
    """새삶교회(saesamm.com) 주일설교 게시판 수집기."""

    BASE_URL = "https://www.saesamm.com"
    LIST_PATH = "/bbs/board.php"

    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get("source_id", "saesamm")
        self.storage_path = Path(config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/saesamm.jsonl"
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
    def _list_url(page: int) -> str:
        base = f"{SaesammCollector.BASE_URL}{SaesammCollector.LIST_PATH}?bo_table=sermon"
        return base if page <= 1 else f"{base}&page={page}"

    @staticmethod
    def _detail_url(wr_id: str) -> str:
        return f"{SaesammCollector.BASE_URL}{SaesammCollector.LIST_PATH}?bo_table=sermon&wr_id={wr_id}"

    def parse_list_page(self, html: str) -> List[Dict]:
        """목록 페이지에서 (wr_id, title_raw) 후보를 뽑는다."""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for link in soup.select("a.bo_tit"):
            href = link.get("href", "")
            match = re.search(r"wr_id=(\d+)", str(href))
            if not match:
                continue
            items.append({
                "wr_id": match.group(1),
                "title_raw": link.get_text(strip=True),
                "detail_url": self._detail_url(match.group(1)),
            })
        return items

    def _parse_sermon_info(self, detail_html: str) -> Dict[str, Optional[str]]:
        """상세 페이지 table#sermon-info에서 설교자/본문/날짜를 뽑는다."""
        soup = BeautifulSoup(detail_html, "html.parser")
        info: Dict[str, Optional[str]] = {"preacher": None, "passage_raw": None, "published_date": None}

        table = soup.select_one("table#sermon-info")
        if not table:
            return info

        label_map = {"설교자": "preacher", "설교본문": "passage_raw", "설교날짜": "published_date"}
        for row in table.select("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True)
            key = label_map.get(label)
            if key:
                info[key] = td.get_text(strip=True) or None

        return info

    def parse_item(self, item: Dict, detail_html: str) -> Optional[SermonRecord]:
        title = _TITLE_PREFIX_PATTERN.sub("", item["title_raw"]).strip()
        if not title:
            return None

        info = self._parse_sermon_info(detail_html)
        passage_raw = info.get("passage_raw")
        if not passage_raw:
            return None

        passage_data = self.bible_parser.parse(passage_raw)
        if passage_data.get("kind") not in ("confirmed", "chapter_only"):
            return None

        # YYYY-MM-DD 형식이 아니면 근거 없이 지어내지 않고 비워둔다.
        published_date = info.get("published_date")
        if published_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", published_date):
            published_date = None

        dedupe_key = compute_dedupe_key(title, passage_raw)

        return SermonRecord(
            record_id=f"saesamm_{dedupe_key}",
            source=self.source_id,
            title=title,
            passage_raw=passage_raw,
            bible_book=passage_data.get("bible_book") or "Unknown",
            chapter_start=passage_data.get("chapter_start") or 0,
            chapter_end=passage_data.get("chapter_end"),
            verse_start=passage_data.get("verse_start"),
            verse_end=passage_data.get("verse_end"),
            preacher=info.get("preacher"),
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

        설교자/날짜는 목록에도 나오지만 설교본문(성경 참조)은 상세
        페이지에만 있어(실측 확인) 항목마다 상세 페이지를 함께 요청한다.
        """
        all_records: List[SermonRecord] = []

        for page in range(1, max_pages + 1):
            url = self._list_url(page)
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
                    if not detail_html:
                        continue
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
