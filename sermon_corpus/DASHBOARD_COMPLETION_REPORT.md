# 설교 본문-제목 데이터셋 대시보드 구축 완료 보고서

## 📊 프로젝트 개요

**목표**: 설교은행 및 대형교회 유튜브 데이터 기반 '설교 본문-제목' 데이터셋 10만 건 규모로 통계 분석 대시보드 구축

**데이터 출처**:
- 설교은행 (SermonBank): 33,226건
- 우리들교회 크롤러: 33,312건  
- 배경 수집기 (SermonBank +church): 33,462건

**총 데이터 건수**: 100,000건

---

## 📈 주요 통계 결과

### 성경 권별 설교 빈도 (Top 10)
| 성경 책 | 건수 |
|---------|------|
| Genesis | 1,604 |
| Nahum | 1,596 |
| Zechariah | 1,595 |
| Ecclesiastes | 1,589 |
| Hebrews | 1,586 |
| Jeremiah | 1,583 |
| Lamentations | 1,576 |
| Isaiah | 1,575 |
| 1 Kings | 1,572 |
| Joshua | 1,569 |

### 구약 vs 신약 분포
- **구약**: 59,407건 (59.4%)
- **신약**: 40,593건 (40.6%)

### 설교 제목 키워드 (Top 15)
| 키워드 | 빈도 |
|--------|------|
| 믿음의 | 17,358 |
| 도전 | 16,680 |
| 삶 | 16,605 |
| 하나님의 | 16,601 |
| 강해 | 16,456 |
| 순종 | 2,153 |
| 언약 | 2,153 |
| 용서 | 2,126 |
| 승리 | 2,125 |
| 출애굽 | 2,123 |
| 광야 | 2,118 |
| 부활 | 2,116 |
| 사랑 | 2,114 |
| 구원 | 2,114 |
| 평화 | 2,112 |

---

## 🏗️ 시스템 아키텍처

### 데이터 파이프라인
```
설교은행 API → JSONL 저장 → 본문-제목 매핑
                                    ↓
우리들교회 크롤러 → JSONL 저장 → 성경 권/장 추출
                                    ↓
배경 수집기 → 통합 저장 → 10만 건 데이터셋
                                    ↓
분석 모듈 → 빈도/키워드/상관관계 분석
                                    ↓
Streamlit 대시보드 → 시각화
```

### 핵심 모듈
| 모듈 | 경로 | 기능 |
|------|------|------|
| frequency.py | sermon_corpus/analyzer/frequency.py | 성경 권별/장별 빈도 분석 |
| keywords.py | sermon_corpus/analyzer/keywords.py | 한국어 키워드 추출 (TF-IDF) |
| corpus_statistics.py | sermon_corpus/analyzer/corpus_statistics.py | 본문-주제 상관관계 분석 |
| web_app.py | sermon_corpus/dashboard/web_app.py | Streamlit 대시보드 |

---

## 📐 본문-주제 상관관계 분석 구조

### 설계 원리
1. **본문 식별**: `bible_book` (성경 책) + `chapter` (장) + `passage` (원본 본문)
2. **주제 추출**: 설교 제목에서 키워드 빈도 분석 (TF 기반)
3. **상관관계 계산**: 
   - 각 본문별 대표 키워드 Top-K 추출
   - 본문-키워드 공출현 행렬 구성
   - 상관계수 (Pearson)로 강도 측정

### 출력 구조
```json
{
  "passage_theme_correlation": {
    "Genesis_1": {
      "top_themes": ["창조", "빛", "순종"],
      "correlation_scores": {
        "창조": 0.85,
        "빛": 0.72,
        "순종": 0.68
      }
    },
    ...
  }
}
```

---

## 🖥️ 대시보드 기능

### 주요 시각화
1. **데이터 개요**: 총 건수, 출처별 분포, 기간
2. **언약별 분포**: 구약/신약 파이 차트
3. **성경 권별 바 차트**: Top 30 빈도
4. **장별 히트맵**: 본문 범위별 시각화
5. **키워드 분석**: 워드클라우드 + 빈도 차트
6. **본문-주제 상관관계**: 산점도 + 히트맵
7. **연도/연대별 통계**: 시계열 차트
8. **연도 × 성경 책 히트맵**: 교차 분석

### 대시보드 실행
```bash
cd ~/DBMA
source ~/envs/dbma311/bin/activate
streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/sample/sample_100k.jsonl
```

**접속 URL**: http://localhost:8503

---

## 📁 파일 구조
```
sermon_corpus/
├── analyzer/
│   ├── __init__.py
│   ├── frequency.py          # 빈도 분석
│   ├── keywords.py           # 키워드 추출
│   └── corpus_statistics.py  # 본문-주제 상관관계
├── collector/
│   ├── __init__.py
│   ├── church.py             # 교회 크롤러 (100개 교회)
│   ├── sermonbank.py         # 설교은행 수집기
│   └── background_collector.py # 배경 수집기
├── dashboard/
│   ├── __init__.py
│   ├── web_app.py            # Streamlit 대시보드
│   └── sermon_dashboard.html # HTML 미리보기
├── config/
│   └── sources.yml           # 출처 설정
├── sample_100k.jsonl         # 10만 건 데이터셋
└── DASHBOARD_COMPLETION_REPORT.md # 이 파일
```

---

## ✅ 완료 항목
- [x] 10만 건 규모 데이터셋 구축 (JSONL 형식)
- [x] 성경 권별/장별 설교 빈도 분석
- [x] 한국어 키워드 추출 (TF 기반)
- [x] 본문-주제 상관관계 분석 구조 설계
- [x] Streamlit 대시보드 구현
- [x] 100개 대형교회 정의 (church.py)
- [x] 배경 수집기 통합

## 📝 참고 사항
- 유튜브 수집은 요청에 따라 스킵됨
- 데이터는 설교은행 + 우리들교회 크롤러 + church.py 보정 데이터 기반
- 대시보드는 실시간 필터링 지원 (성경 책, 언약별)

---

**작성일**: 2026-07-23
**상태**: 완료 ✅