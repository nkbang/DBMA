# DBMA Sermon Corpus Platform

## 설교 본문-제목 데이터셋 & 대시보드

설교은행 및 대형교회 유튜브 데이터를 기반으로 '설교 본문-제목' 데이터셋을 구축하고, 성경 권별/장별 설교 빈도와 핵심 키워드를 시각화하는 대시보드를 제공합니다.

---

## 📁 프로젝트 구조

```
sermon_corpus/
├── __init__.py                    # 패키지 초기화
├── README.md                      # 이 파일
├── config/
│   └── sources.yml               # 데이터 소스 설정
├── collector/
│   ├── __init__.py
│   ├── polite_fetcher.py         # 예의바른 HTTP 페처
│   └── sermonbank.py             # 설교은행 데이터 수집기
├── analyzer/
│   ├── __init__.py
│   ├── frequency.py              # 설교 빈도 분석기
│   ├── keywords.py               # 키워드 추출기
│   └── corpus_statistics.py      # 코퍼스 통계 분석기
└── dashboard/
    ├── __init__.py
    └── web_app.py                 # Streamlit 대시보드
```

---

## 🚀 빠른 시작

### 1. 데이터 수집

```bash
# 설교은행 데이터 수집
python scripts/collect_sermonbank.py --output data/sermon_corpus/raw/sermonbank.jsonl --max 1000

# 대형교회 유튜브 데이터 수집 (추가 설정 필요)
python scripts/collect_youtube.py --channel "목양TV" --output data/sermon_corpus/raw/youtube.jsonl
```

### 2. 대시보드 실행

```bash
# 실제 데이터로 대시보드 실행
python scripts/run_sermon_dashboard.py --data data/sermon_corpus/raw/sermonbank.jsonl

# 또는 직접 streamlit 실행
streamlit run sermon_corpus/dashboard/web_app.py -- --data data/sermon_corpus/raw/sermonbank.jsonl
```

---

## 📊 대시보드 기능

### 1. 전체 개요
- 총 설교 수, 성경 책 수, 장 수, 키워드 수 요약

### 2. 언약별 설교 분포
- 구약 vs 신약 파이 차트
- 비율 테이블

### 3. 권별 설교 빈도 (Top 30)
- 성경 책별 설교 빈도 막대 차트 (구약/신약 색상 구분)

### 4. 장별 설교 빈도 (Top 20)
- 특정 장(예: "요한복음 3장")의 설교 빈도

### 5. 설교 제목 키워드 분석
- 키워드 트리맵 (빈도 기반 크기)
- 주제 카테고리 분포 (믿음, 기도, 사랑, 구원 등)

### 6. 본문-주제 상관관계
- 본문별 주요 주제 히트맵
- 성경 책별 핵심 주제 매핑

### 7. 데이터 미리보기
- 샘플 제목 목록

---

## 📈 통계 분석 모듈

### FrequencyAnalyzer

```python
from sermon_corpus.analyzer.frequency import FrequencyAnalyzer

analyzer = FrequencyAnalyzer()
analyzer.load_jsonl(Path("data.jsonl"))

# 권별 빈도
books = analyzer.get_book_frequencies(top_k=30)

# 장별 빈도
chapters = analyzer.get_chapter_frequencies(top_k=50)

# 언약별 분포
testament = analyzer.get_testament_frequencies()
```

### KeywordExtractor

```python
from sermon_corpus.analyzer.keywords import KeywordExtractor

extractor = KeywordExtractor()
extractor.load_jsonl(Path("data.jsonl"))

# 상위 키워드
keywords = extractor.get_top_keywords(top_k=50)

# 카테고리 분포
categories = extractor.get_top_categories(top_k=20)
```

### CorpusStatisticsAnalyzer

```python
from sermon_corpus.analyzer.corpus_statistics import CorpusStatisticsAnalyzer

stats = CorpusStatisticsAnalyzer()
stats.load_jsonl(Path("data.jsonl"))

# 전체 통계
full_stats = stats.get_full_statistics()

# 본문-주제 상관관계
correlations = stats.get_passage_theme_correlation()

# 핵심 주제 per book
key_themes = stats.compute_key_themes_per_book()

# 상관관계 행렬
matrix = stats.compute_correlation_matrix()

# 결과 저장
stats.save_statistics(Path("output/sermon_dashboard"))
```

---

## ⚙️ 데이터 소스 설정

`config/sources.yml` 파일을 편집하여 데이터 소스를 구성하세요:

```yaml
sources:
  sermonbank:
    enabled: true
    api_key: "your_api_key_here"
    max_records: 100000
    
  youtube:
    enabled: false
    channels:
      - "목양TV"
      - "GCN"
    api_key: "your_youtube_api_key"
```

---

## 📋 출력 파일

대시보드 실행 시 `output/sermon_dashboard/` 디렉토리에 다음 파일이 생성됩니다:

| 파일 | 설명 |
|------|------|
| `corpus_statistics.json` | 전체 통계 요약 |
| `passage_theme_correlations.json` | 본문-주제 상관관계 |
| `key_themes_per_book.json` | 성경 책별 핵심 주제 |
| `correlation_matrix.json` | 본문-키워드 상관관계 행렬 |

---

## 🔧 환경 설정

### Python 환경

```bash
# 가상 환경 생성
python -m venv env_sermon
source env_sermon/bin/activate

# 의존성 설치
pip install streamlit pandas plotly beautifulsoup4 requests lxml
```

### DBMA Python 환경 사용 (권장)

```bash
cd ~/DBMA
source ~/envs/dbma311/bin/activate
pip install streamlit pandas plotly beautifulsoup4 requests lxml
```

---

## 📝 데이터 스키마

JSONL 레코드 스키마:

```json
{
  "record_id": "sermonbank_001",
  "source": "sermonbank",
  "title": "믿음의 도전",
  "passage_raw": "Genesis 1:1-3",
  "bible_book": "Genesis",
  "chapter_start": 1,
  "chapter_end": 1,
  "verse_start": 1,
  "verse_end": 3,
  "preacher": "김목사",
  "church": "기독교교회",
  "published_date": "2024-01-15",
  "source_url": "https://sermonbank.kr/...",
  "collected_at": "2024-07-22T00:00:00"
}
```

---

## 🎯 핵심 진리 통계

각 본문이 말하는 중심 진리와 설교 제목의 상관관계를 분석하는 방법:

```python
# 1. 본문별 카테고리 분포
correlations = stats.get_passage_theme_correlation()

# 2. 상관관계 행렬
matrix = stats.compute_correlation_matrix()

# 3. 핵심 주제 도출
themes = stats.compute_key_themes_per_book()

# 결과 예시:
# {
#   "Genesis": ["creation", "covenant", "faith"],
#   "Psalms": ["prayer", "worship", "praise"],
#   "Romans": ["grace", "faith", "righteousness"],
#   ...
# }
```

---

## 📄 라이선스

DBMA Project 내부 사용용.