# DBMA Sermon Corpus - 만나교회(manna.or.kr) 설교 수집기
#
# 2026-07-23 실측 확인: https://manna.or.kr/설교/ (WordPress, "jt-" 접두
# 테마). robots.txt는 GPTBot/CCBot과 /wp-json/, /wp-admin/만 차단하고
# 일반 UA는 허용한다. 상세 페이지에 제목/설교자/날짜/본문이 각각
# .jt-content-header__title / __author / __time / __desc 로 명확히
# 구분돼 있다(실측 확인). 전문(설교 원고)은 없고 본문 성경구절 낭독과
# 짧은 안내만 있다 — DBMA는 제목/본문 성경구절/설교자/날짜만 요구하므로
# 충분하다.

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from sermon_corpus.collector.sermonbank import BibleReferenceParser, SermonRecord, compute_dedupe_key

# 목록/상세 제목은 "14. 개혁! 좌로나 우로 치우치지 않는 것(요시야)"처럼
# 회차 번호가 앞에 붙는다 — 실제 설교 제목이 아니므로 떼어낸다(실측 확인).
_TITLE_PREFIX_PATTERN = re.compile(r"^\d+\.\s*")


class MannaCollector:
    """만나교회(manna.or.kr) 설교 게시판 수집기."""

    BASE_URL = "https://manna.or.kr"
    LIST_PATH = f"/{quote('설교')}/"

    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get("source_id", "manna")
        self.storage_path = Path(config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/manna.jsonl"
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
        base = f"{MannaCollector.BASE_URL}{MannaCollector.LIST_PATH}"
        return base if page <= 1 else f"{base}page/{page}/"

    def parse_list_page(self, html: str) -> List[Dict]:
        """목록 페이지에서 설교 상세 페이지 URL 후보를 뽑는다."""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        seen_urls = set()
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if not re.search(r"/설교/\d+-", str(href)) and not re.search(
                r"/%EC%84%A4%EA%B5%90/\d+-", str(href), re.IGNORECASE
            ):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            items.append({"detail_url": href})
        return items

    def parse_item(self, detail_html: str, detail_url: str) -> Optional[SermonRecord]:
        soup = BeautifulSoup(detail_html, "html.parser")

        title_el = soup.select_one(".jt-content-header__title")
        author_el = soup.select_one(".jt-content-header__author")
        time_el = soup.select_one(".jt-content-header__time")
        meta_el = soup.select_one(".jt-content-header__meta")

        if not title_el or not meta_el:
            return None

        title = _TITLE_PREFIX_PATTERN.sub("", title_el.get_text(strip=True)).strip()
        if not title:
            return None

        passage_raw = meta_el.get_text(strip=True)
        if not passage_raw:
            return None

        passage_data = self.bible_parser.parse(passage_raw)
        if passage_data.get("kind") not in ("confirmed", "chapter_only"):
            return None

        preacher = author_el.get_text(strip=True) if author_el else None

        published_date = None
        if time_el:
            time_text = time_el.get_text(strip=True)
            date_match = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", time_text)
            if date_match:
                y, m, d = date_match.groups()
                published_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        dedupe_key = compute_dedupe_key(title, passage_raw)

        return SermonRecord(
            record_id=f"manna_{dedupe_key}",
            source=self.source_id,
            title=title,
            passage_raw=passage_raw,
            bible_book=passage_data.get("bible_book") or "Unknown",
            chapter_start=passage_data.get("chapter_start") or 0,
            chapter_end=passage_data.get("chapter_end"),
            verse_start=passage_data.get("verse_start"),
            verse_end=passage_data.get("verse_end"),
            preacher=preacher,
            published_date=published_date,
            source_url=detail_url,
            collected_at=datetime.utcnow().isoformat(),
        )

    def is_duplicate(self, dedupe_key: str) -> bool:
        if dedupe_key in self._seen_keys:
            return True
        self._seen_keys.add(dedupe_key)
        return False

    def collect_all(self, fetcher, max_records: int = None, max_pages: int = 10) -> List[SermonRecord]:
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
                    record = self.parse_item(detail_html, item["detail_url"])
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
