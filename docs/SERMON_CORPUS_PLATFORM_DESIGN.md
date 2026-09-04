# DBMA 설교 본문-제목 데이터셋 & 분석 플랫폼 설계 문서

## 1. 제품 개요

### 1.1 프로젝트 목적

실제로 설교한 혹은 출판된 설교 제목과 본문 참조의 쌍을 수집·정규화·통계·시각화하는 플랫폼을 구축합니다.

**핵심 기능:**
- 설교은행, 대형교회 유튜브, 출판 설교집에서 실제 설교 제목-본문 쌍 수집
- 본문 참조 정규화 (OSIS 표준, 한국어 성경 약어 매핑)
- 중복 제거 (동일 본문-제목 쌍)
- 성경 권별/장별 설교 빈도 통계
- 핵심 키워드 추출 및 빈도 분석
- 제목-본문 상관관계 통계 (어떤 본문이 어떤 제목 스타일로 설교되는가)
- 중심 진리 매핑 (본문별 반복出现的 신학적 주제)
- 대시보드 시각화 (Streamlit)

**범위 제외:**
- ❌ AI 설교 제목 생성 (LLM 프롬프트, Ollama)
- ❌ RAG 검색 (Qdrant, 임베딩)
- ❌ LoRA 학습 (SFT/DPO 데이터 내보내기)
- ❌ Commentary-Title Alignment 점수
- ❌ Central Truth Extraction Engine (복잡한 신학 분석)

---

## 2. 아키텍처

```
DBMA/
│
├── sermon_corpus/                   # 설교 제목-본문 쌍 플랫폼
│   ├── config/
│   │   ├── korean_bible_books.yml   # 한국어 성경 약어 매핑
│   │   └── sources.yml              # 수집원 설정
│   │
│   ├── collector/                   # 데이터 수집기
│   │   ├── base.py                  # Collector 프로토콜
│   │   ├── sermonbank.py            # 설교은행 수집
│   │   ├── youtube.py               # YouTube API 수집
│   │   └── polite_fetcher.py        # HTTP 클라이언트
│   │
│   ├── normalizer/                  # 정규화 파이프라인
│   │   ├── passage_resolver.py      # 본문 참조 파서 (OSIS)
│   │   ├── korean_bible_books.py    # 성경 약어 매핑
│   │   ├── dedupe.py                # 중복 제거
│   │   └── validator.py             # Pydantic 검증
│   │
│   ├── statistics/                  # 통계 분석
│   │   ├── frequency.py             # 권별/장별 설교 빈도
│   │   ├── keywords.py              # 핵심 키워드 추출
│   │   ├── correlation.py           # 제목-본문 상관관계
│   │   └── central_themes.py        # 본문별 반복 신학 주제
│   │
│   └── dashboard/                   # 대시보드
│       ├── app.py                   # Streamlit 메인
│       ├── charts.py                # 차트 생성
│       └── filters.py               # 필터링 로직
│
├── scripts/
│   ├── collect_all.py               # 전체 데이터 수집 실행
│   ├── build_corpus.py              # 코퍼스 구축
│   └── compute_statistics.py        # 통계 계산
│
├── data/
│   └── sermon_corpus/
│       ├── raw/                     # 원본 수집 데이터
│       │   ├── sermonbank.jsonl
│       │   └── youtube.jsonl
│       ├── normalized/              # 정규화 데이터
│       │   └── corpus.jsonl         # 최종 코퍼스 (제목-본문 쌍)
│       └── statistics/              # 통계 결과
│           ├── frequency_by_book.json
│           ├── frequency_by_chapter.json
│           ├── keywords.json
│           └── correlation.json
│
├── tests/
│   ├── test_passage_resolver.py
│   ├── test_deduplication.py
│   └── test_statistics.py
│
└── output/
    └── dashboard_report.json        # 대시보드용 통계 데이터
```

---

## 3. 데이터 모델

### 3.1 SermonRecord (설교 레코드)

```python
# sermon_corpus/normalizer/models.py

from pydantic import BaseModel, field_validator
from typing import Optional


class SermonRecord(BaseModel):
    """실제 설교 제목-본문 쌍 레코드"""
    record_id: str                    # 고유 ID
    source: str                       # 출처 (sermonbank, youtube, publication)
    source_url: str                   # 원본 URL
    title: str                        # 설교 제목
    passage_raw: str                  # 원본 본문 참조 ("고린도전서 13:4-7")
    passage_osis: str                 # 정규화 본문 (OSIS) ("1Co. 13:4-7")
    bible_book: str                   # 성경 책명 (OSIS 코드) ("1Co.")
    chapter_start: int                # 장 시작
    chapter_end: int                  # 장 끝
    verse_start: Optional[int]        # 절 시작
    verse_end: Optional[int]          # 절 끝
    preacher: Optional[str]           # 설교자
    published_date: Optional[str]     # 게시일
    language: str = "ko"
    quality_status: str = "approved"  # approved | review_required
    dedupe_key: str                   # 중복 제거 키
```

### 3.2 StatisticsResult (통계 결과)

```python
class StatisticsResult(BaseModel):
    """통계 분석 결과"""
    frequency_by_book: dict           # {"창세기": 1234, "출애굽기": 987, ...}
    frequency_by_chapter: dict        # {"창세기_1장": 123, "창세기_2장": 89, ...}
    top_keywords: dict                # {"은혜": 567, "믿음": 432, ...}
    title_passage_correlation: dict   # {"은혜": ["주님의 은혜를 기억합니다", ...]}
    central_themes_by_passage: dict   # {"고린도전서 13장": ["사랑", "은혜", "자비"]}
```

---

## 4. 데이터 수집 정책 (Crawling Policy)

### 4.1 기본 원칙

1. **공식 API, RSS, sitemap 우선**
   - YouTube는 공식 API 사용
   - 교회 사이트는 공개 목록·검색 페이지·RSS·sitemap 우선 사용

2. **robots.txt와 이용약관 확인**
   - 수집 전 `robots.txt`와 사이트 이용약관을 확인
   - 제한 경로·금지된 자동 수집은 제외

3. **최소 데이터 원칙**
   - `제목`, `본문 참조`, `설교자`, `날짜`, `출처 URL`만 수집
   - 설교 전문은 수집하지 않음

4. **차단은 실패가 아니라 중단 신호**
   - 403, 429, CAPTCHA 감지 시 자동 재시도 대신 해당 출처 작업 중단

### 4.2 출처별 정책 파일

```yaml
# config/sources/sermonbank.yml
source_id: sermonbank
enabled: true
mode: public_html
base_url: "https://sermonbank.net"
user_agent: "DBMA-SermonTitleResearch/0.1 (academic metadata collection; contact: dbma-research@example.org)"

limits:
  concurrency: 1
  min_delay_seconds: 5
  max_delay_seconds: 12
  daily_request_budget: 300

retry:
  max_attempts: 2
  retryable_statuses: [408, 429, 500, 502, 503, 504]
  stop_statuses: [401, 403, 451]

storage:
  raw_html: true
  retain_days: 30

takedown_policy: immediate_removal
robots_checked_at: "2026-07-22"
```

```yaml
# config/sources/youtube.yml
source_id: youtube
mode: api_public_metadata
api_endpoint: "https://www.googleapis.com/youtube/v3"
api_key_env: "YOUTUBE_API_KEY"
rate_limit:
  requests_per_minute: 60
  concurrency: 1
  min_delay_seconds: 1
  max_delay_seconds: 3
retry:
  max_attempts: 3
  retry_statuses: [429, 500, 502, 503, 504]
  stop_statuses: [401, 403]
daily_budget: 1000
user_agent: "DBMA-SermonTitleResearch/0.1 (academic metadata collection; contact: dbma-research@example.org)"
cache_enabled: true
takedown_policy: immediate_removal
```

### 4.3 차단·오류 대응 표

| 신호 | 처리 | 금지할 행동 |
|------|------|-----------|
| 200 + 정상 HTML | 파싱 후 캐시 | 동일 URL 즉시 재호출 |
| 301/302 | 최종 URL 기록 후 처리 | 리디렉션 루프 반복 |
| 404 | `not_found` 기록, 장기 보류 | 반복 재시도 |
| 429 | 즉시 중지, `Retry-After` 존중 | 속도 증가·IP 변경 |
| 401/403 | 출처 전체 중단, 정책 검토 | 로그인·쿠키·헤더 위장 |
| CAPTCHA/WAF | 출처 중단, 수동 문의 또는 제외 | CAPTCHA 자동 해제 |
| 5xx | 긴 backoff 후 1-2회 재시도 | 짧은 간격의 무한 재시도 |
| 구조 변경 | 파서 중지, HTML 샘플 검토 | 빈 값 대량 적재 |

### 4.4 DBMA 수집 경계

```
✅ 허용 가능한 수집:
- 공개 페이지의 제목·본문 참조·날짜·URL
- 공식 API, RSS, sitemap
- robots.txt와 이용약관이 허용하는 범위
- 낮은 빈도와 명확한 User-Agent
- 차단 시 중단하고 운영자에게 문의

❌ 제외할 수집:
- CAPTCHA, 로그인, paywall 우회
- 프록시/IP 회전으로 rate limit 회피
- User-Agent·브라우저 지문 위장
- 원본 설교문 대량 복제
- 비공개 API 또는 숨겨진 엔드포인트 역공학
```

---

## 5. 핵심 구현 파일

### 5.1 `sermon_corpus/collector/polite_fetcher.py`

```python
# 간단한 동기 수집기 (초기 버전)

import time
import random
import httpx
from urllib.robotparser import RobotFileParser


class PoliteFetcher:
    def __init__(self, user_agent: str, min_delay: float = 3.0, max_delay: float = 8.0):
        self.user_agent = user_agent
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.robots_cache = {}
    
    def can_fetch(self, base_url: str, target_url: str) -> bool:
        if base_url not in self.robots_cache:
            self._load_robots(base_url)
        return self.robots_cache[base_url].can_fetch(self.user_agent, target_url)
    
    def _load_robots(self, base_url: str):
        robots_url = f"{base_url}/robots.txt"
        with httpx.Client() as client:
            resp = client.get(robots_url)
            parser = RobotFileParser()
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                parser.parse([])
            self.robots_cache[base_url] = parser
    
    def get(self, url: str) -> str | None:
        if not self.can_fetch(
            httpx.URL(url).host, url
        ):
            return None
        
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        
        with httpx.Client() as client:
            resp = client.get(url)
            return resp.text if resp.status_code == 200 else None
```

### 5.2 `sermon_corpus/normalizer/passage_resolver.py`

```python
# 본문 참조 파서 (한국어)

import re
from dataclasses import dataclass


@dataclass
class Passage:
    osis: str           # "1Co. 13:4-7"
    bible_book: str     # "1Co."
    chapter_start: int
    chapter_end: int
    verse_start: int | None
    verse_end: int | None


class KoreanBiblePassageResolver:
    """한국어 본문 참조 → OSIS 표준"""
    
    # 한국어 성경 책명 매핑
    BOOK_ALIASES = {
        "창세기": "Gen.", "출애굽기": "Ex.", "레위기": "Lev.",
        "고린도전서": "1Co.", "고린도후서": "2Co.",
        "로마서": "Rom.", "요한복음": "Jn.", "요한일서": "1Jn.",
        # ... 전체 66권 매핑
    }
    
    def parse(self, raw: str) -> Passage | None:
        # "고린도전서 13:4-7" → Passage(osis="1Co. 13:4-7", ...)
        match = re.match(
            r"(?P<book>.+?)\s+(?P<chapter>\d+):(?P<verses>\d+-\d+)",
            raw.strip()
        )
        if not match:
            return None
        
        book_ko = match.group("book")
        book_osis = self.BOOK_ALIASES.get(book_ko, book_ko)
        chapter = int(match.group("chapter"))
        verses = match.group("verses").split("-")
        
        return Passage(
            osis=f"{book_osis} {chapter}:{match.group('verses')}",
            bible_book=book_osis,
            chapter_start=chapter,
            chapter_end=chapter if len(verses) == 1 else chapter,
            verse_start=int(verses[0]),
            verse_end=int(verses[1]) if len(verses) == 2 else None,
        )
```

### 5.3 `sermon_corpus/statistics/frequency.py`

```python
# 권별/장별 설교 빈도 통계

from collections import Counter


def frequency_by_book(records: list) -> dict:
    """책명별 설교 빈도"""
    counter = Counter(r.bible_book for r in records)
    return dict(counter.most_common())


def frequency_by_chapter(records: list) -> dict:
    """장별 설교 빈도"""
    counter = Counter(
        f"{r.bible_book}_{r.chapter_start}장" for r in records
    )
    return dict(counter.most_common())
```

### 5.4 `sermon_corpus/statistics/correlation.py`

```python
# 제목-본문 상관관계 분석

from collections import defaultdict, Counter


def title_passage_correlation(records: list) -> dict:
    """어떤 본문이 어떤 제목 스타일로 설교되는가"""
    correlation = defaultdict(lambda: defaultdict(int))
    
    for r in records:
        book = r.bible_book
        # 제목에서 키워드 추출 (간단히 공백 기반 n-gram)
        title_words = r.title.split()
        for word in title_words:
            if len(word) >= 2:  # 2글자 이상
                correlation[book][word] += 1
    
    # dict로 변환
    return {
        book: dict(words) 
        for book, words in correlation.items()
    }


def central_themes_by_passage(records: list) -> dict:
    """본문별 반복出现的 신학 주제 (제목 기반)"""
    themes = defaultdict(list)
    
    for r in records:
        themes[f"{r.bible_book} {r.chapter_start}장"].append(r.title)
    
    # 각 본문별로 제목에서 반복되는 단어/구 추출
    result = {}
    for passage, titles in themes.items():
        word_freq = Counter()
        for title in titles:
            for word in title.split():
                if len(word) >= 2:
                    word_freq[word] += 1
        # 상위 10개 키워드
        result[passage] = [word for word, _ in word_freq.most_common(10)]
    
    return result
```

### 5.5 `sermon_corpus/dashboard/app.py` (Streamlit)

```python
# Streamlit 대시보드

import streamlit as st
import json
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="DBMA 설교 본문-제목 대시보드", layout="wide")
st.title("📊 설교 본문-제목 대시보드")

# 통계 데이터 로드
with open("data/sermon_corpus/statistics/frequency_by_book.json") as f:
    freq_book = json.load(f)

with open("data/sermon_corpus/statistics/frequency_by_chapter.json") as f:
    freq_chapter = json.load(f)

with open("data/sermon_corpus/statistics/correlation.json") as f:
    correlation = json.load(f)

# 권별 설교 빈도 차트
st.subheader("성경 권별 설교 빈도")
df_book = pd.DataFrame(list(freq_book.items()), columns=["권명", "빈도"])
fig_book = px.bar(df_book, x="권명", y="빈도", title="권별 설교 빈도")
st.plotly_chart(fig_book, use_container_width=True)

# 장별 설교 빈도 차트 (상위 20장)
st.subheader("장별 설교 빈도 (상위 20)")
df_chapter = pd.DataFrame(list(freq_chapter.items()), columns=["장", "빈도"]).head(20)
fig_chapter = px.bar(df_chapter, x="장", y="빈도", title="상위 20 장별 설교 빈도")
st.plotly_chart(fig_chapter, use_container_width=True)

# 제목-본문 상관관계
st.subheader("본문별 핵심 키워드")
for book, keywords in list(correlation.items())[:5]:
    st.markdown(f"### {book}")
    st.write(", ".join(f"**{k}** ({v})" for k, v in list(keywords.items())[:10]))

# 필터링
st.sidebar.header("필터")
selected_books = st.sidebar.multiselect(
    "성경 권 선택",
    options=list(freq_book.keys()),
    default=[]
)
if selected_books:
    st.write(f"선택된 권: {', '.join(selected_books)}")
```

---

## 6. 구현 파일 목록 (Act mode에서 작성)

### 6.1 `sermon_corpus/` 디렉터리

```text
sermon_corpus/
├── config/
│   ├── korean_bible_books.yml    ← 작성
│   └── sources.yml               ← 작성
├── collector/
│   ├── base.py                   ← 작성
│   ├── sermonbank.py             ← 작성
│   ├── youtube.py                ← 작성
│   └── polite_fetcher.py         ← 작성
├── normalizer/
│   ├── passage_resolver.py       ← 작성
│   ├── korean_bible_books.py     ← 작성
│   ├── dedupe.py                 ← 작성
│   └── validator.py              ← 작성
├── statistics/
│   ├── frequency.py              ← 작성
│   ├── keywords.py               ← 작성
│   ├── correlation.py            ← 작성
│   └── central_themes.py         ← 작성
├── dashboard/
│   ├── app.py                    ← 작성 (Streamlit)
│   └── charts.py                 ← 작성
└── __init__.py                   ← 작성
```

### 6.2 `scripts/` 디렉터리

```text
scripts/
├── collect_all.py                ← 작성
├── build_corpus.py               ← 작성
└── compute_statistics.py         ← 작성
```

### 6.3 `tests/` 디렉터리

```text
tests/
├── test_passage_resolver.py      ← 작성
├── test_deduplication.py         ← 작성
└── test_statistics.py            ← 작성
```

---

## 7. 기술 스택

| 계층 | 추천 | 역할 |
|------|------|------|
| HTTP 클라이언트 | `httpx` | async HTTP, connection pooling, timeout, HTTP/2 선택 |
| 비동기 런타임 | `asyncio` | 작업 큐, semaphore, cancellation, worker |
| robots 처리 | `urllib.robotparser` | `robots.txt` 허용 경로·crawl delay 확인 |
| HTML 파싱 | `selectolax` | 빠른 HTML/CSS selector 파싱 |
| 보조 파싱 | `BeautifulSoup4` + `lxml` | 복잡하거나 깨진 HTML의 fallback |
| 스키마 검증 | `pydantic` | 원본·정규화 레코드 검증 |
| 재시도 | `tenacity` | 제한적 exponential backoff |
| URL 정규화 | `yarl` 또는 `urllib.parse` | canonical URL·상대 URL 처리 |
| 저장 | `aiosqlite` → `asyncpg` | 초기 상태 저장 → 운영 DB |
| 파일 출력 | `orjson` + Parquet | raw JSONL, normalized Parquet |
| 관측성 | `structlog`, `prometheus-client` | 구조화 로그·수집 지표 |
| 테스트 | `pytest`, `respx` | HTTP mock, 파서 회귀 테스트 |

### 설치 명령어

```bash
pip install \
  httpx[http2] \
  selectolax \
  beautifulsoup4 \
  lxml \
  pydantic-settings \
  tenacity \
  aiosqlite \
  orjson \
  pyarrow \
  structlog \
  prometheus-client \
  pytest \
  respx
```

---

## 8. 운영 지표

```text
source_id
requests_total
requests_200
requests_429
requests_403
robots_denied_total
parse_success_rate
passage_parse_success_rate
duplicate_rate
records_approved
records_review_required
mean_request_interval_seconds
```

핵심 품질 지표 (속도가 아닌):

```text
본문 참조 파싱 성공률
제목-본문 쌍 유효율
중복률
출처별 정책 준수율
차단 발생 후 자동 중단 성공률
```

---

## 9. 실행 흐름 요약

```
1. scripts/collect_all.py 실행
   ↓
2. sources/*.yml 로드 → 각 출처별 정책 확인
   ↓
3. robots.txt 로드 → 허용 경로 확인
   ↓
4. SQLite 큐에 초기 URL 삽입 (목록 페이지 등)
   ↓
5. 출처별 Worker 시작 (비동기 Task)
   ├── SQLite에서 status='queued' URL 가져오기
   ├── PoliteFetcher로 HTML/API 응답 수집
   │   ├── robots.txt 검사 → 차단 시 skip
   │   ├── rate limiting 적용 → min_delay ~ max_delay 랜덤 대기
   │   ├── 429 감지 → Retry-After 존중 → deferred
   │   ├── 403/401 감지 → source_blocked = True → 중단
   │   └── 200 성공 → 원본 HTML 저장 (JSONL)
   │
   ├── Source Adapter로 파싱
   │   ├── 목록 페이지 → 상세 URL 추출 → 큐에 삽입
   │   └── 상세 페이지 → title_raw, passage_raw 추출
   │
   ├── BibleReferenceParser로 passage_raw → passage_osis
   ├── Pydantic 검증 (RawSermonRecord → NormalizedSermonTitle)
   ├── 중복 제거 (sha256 dedupe_key)
   │
   └── 결과 저장 (normalized JSONL + SQLite 상태 업데이트)
   ↓
6. 큐가 비면 종료 (또는 계속 모니터링)
   ↓
7. scripts/compute_statistics.py 실행 → 통계 계산
   ↓
8. sermon_corpus/dashboard/app.py 실행 → 대시보드 시각화
```

---

## 10. 향후 작업 (Act mode에서 수행)

1. **1주차:** 핵심 파일 작성 (PoliteFetcher, BibleReferenceParser, sources/*.yml)
2. **2-3주차:** 수집 어댑터 확장 (sermonbank, youtube)
3. **4-5주차:** 정규화·중복제거 파이프라인 완성
4. **6주차:** 통계 모듈 완성
5. **7주차:** 대시보드 v1 완성
6. **8주차:** 전체 통합 테스트 및 문서화

---

## 11. 참고 자료

- robots.txt: https://www.rfc-editor.org/rfc/rfc9309
- YouTube Data API: https://developers.google.com/youtube/v3
- OSIS (Standard Original Text Identifier System): https://www.oasis-open.org/standards
- 한국어 성경 약어: 각 번역본 (개역개정, 새번역 등) 기준

---

*문서 작성일: 2026-07-22*
*버전: 1.0 (최종 통합안)*