# DBMA 설교 본문-제목 플랫폼 - 플로우차트

## 1. 전체 시스템 아키텍처 흐름

```mermaid
graph TB
    subgraph "데이터 출처"
        A1[설교은행<br/>sermonbank]
        A2[대형교회 유튜브<br/>YouTube API]
        A3[출판 설교집<br/>publication]
    end

    subgraph "수집 계층"
        B1[PoliteFetcher<br/>robots.txt 준수<br/>rate limiting]
        B2[Source Adapters<br/>sermonbank.py<br/>youtube.py]
    end

    subgraph "정규화 계층"
        C1[본문 참조 파서<br/>한국어 → OSIS]
        C2[Pydantic 검증<br/>SermonRecord]
        C3[중복 제거<br/>dedupe_key]
    end

    subgraph "저장 계층"
        D1[원본 데이터<br/>raw/*.jsonl]
        D2[정규화 데이터<br/>normalized/corpus.jsonl]
        D3[SQLite 상태 DB]
    end

    subgraph "통계 분석 계층"
        E1[빈도 분석<br/>frequency.py]
        E2[키워드 추출<br/>keywords.py]
        E3[상관관계 분석<br/>correlation.py]
        E4[중심 진리 매핑<br/>central_themes.py]
    end

    subgraph "시각화 계층"
        F1[Streamlit 대시보드<br/>app.py]
        F2[차트 생성<br/>charts.py]
        F3[통계 결과 JSON<br/>output/dashboard_report.json]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    C3 --> D2
    C3 --> D3
    D2 --> E1
    D2 --> E2
    D2 --> E3
    D2 --> E4
    E1 --> F1
    E2 --> F1
    E3 --> F1
    E4 --> F1
    E1 --> F3
    E2 --> F3
    E3 --> F3
    E4 --> F3
    F1 --> F2
```

---

## 2. 데이터 수집 파이프라인 상세 흐름

```mermaid
sequenceDiagram
    participant CLI as scripts/collect_all.py
    participant Config as sources/*.yml
    participant Robots as robots.txt
    participant Queue as SQLite Queue
    participant Worker as Source Worker
    participant Fetcher as PoliteFetcher
    participant Adapter as Source Adapter
    participant Parser as BibleReferenceParser
    participant Dedupe as Deduplication Engine
    participant Storage as Storage (JSONL/SQLite)

    CLI->>Config: 정책 파일 로드
    Config-->>CLI: limits, retry, user_agent
    
    loop 각 출처별
        CLI->>Queue: 초기 URL 삽입 (status='queued')
        CLI->>Worker: 시작 (비동기 Task)
        
        Worker->>Queue: status='queued' URL 가져오기
        Queue-->>Worker: URL 반환
        
        Worker->>Fetcher: can_fetch(base_url, url) 검사
        Fetcher->>Robots: robots.txt 조회
        Robots-->>Fetcher: 허용/차단 결정
        alt 차단됨
            Fetcher-->>Worker: None (skip)
            Worker->>Queue: status='robots_denied' 기록
        else 허용됨
            Worker->>Fetcher: get(url) 요청
            Fetcher->>Fetcher: min_delay ~ max_delay 랜덤 대기
            Fetcher->>Fetcher: HTTP GET 요청
            alt 429 Too Many Requests
                Fetcher-->>Worker: 429 응답
                Worker->>Queue: status='deferred' (Retry-After 존중)
            else 403/401 Forbidden
                Fetcher-->>Worker: 403 응답
                Worker->>Queue: status='blocked'
                Worker->>Config: source_blocked = True
                Note over Worker: 출처 전체 중단
            else 200 OK
                Fetcher-->>Worker: HTML/API 응답 본문
                Worker->>Adapter: 파싱 요청
                Adapter-->>Worker: title_raw, passage_raw 추출
                Worker->>Parser: passage_raw → passage_osis 변환
                Parser-->>Worker: Passage 객체 (OSIS 표준)
                Worker->>Dedupe: dedupe_key 생성 및 검사
                alt 중복 없음
                    Dedupe-->>Worker: 신규 기록
                    Worker->>Storage: 원본 JSONL 저장
                    Worker->>Storage: 정규화 JSONL 저장
                    Worker->>Queue: status='stored' 업데이트
                else 중복
                    Dedupe-->>Worker: 중복 기록
                    Worker->>Queue: status='duplicate' 기록
                end
            end
        end
    end
    
    Note over CLI,Storage: 큐가 비면 종료
```

---

## 3. 정규화 및 검증 흐름

```mermaid
flowchart LR
    subgraph "원본 수집"
        A[raw JSONL<br/>title_raw, passage_raw]
    end

    subgraph "본문 참조 파싱"
        B[BibleReferenceParser]
        B1[책명 매핑<br/>한국어 → OSIS]
        B2[장/절 파싱<br/>13:4-7 → chapter/verse]
        B3[범위 확장<br/>단일절 → 시작/끝]
    end

    subgraph "Pydantic 검증"
        C[SermonRecord 검증]
        C1[record_id 고유성]
        C2[source 유효성]
        C3[passage_osis 형식]
        C4[chapter 범위의존성]
    end

    subgraph "중복 제거"
        D[dedupe_key 생성<br/>sha256(title + passage)]
        D1[SQLite에서 중복 검사]
        D2{중복?}
        D2a[예 → skip]
        D2b[아니오 → 저장]
    end

    subgraph "정규화 저장"
        E[normalized/corpus.jsonl]
        F[SQLite 상태 DB]
    end

    A --> B
    B --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C
    C --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> D
    D --> D1
    D1 --> D2
    D2a --> D2a
    D2b --> E
    D2b --> F
```

---

## 4. 통계 분석 흐름

```mermaid
flowchart TB
    subgraph "입력 데이터"
        A[normalized/corpus.jsonl<br/>10만 건]
    end

    subgraph "빈도 분석"
        B[frequency.py]
        B1[권별 빈도<br/>Counter.bible_book]
        B2[장별 빈도<br/>Counter.chapter]
    end

    subgraph "키워드 추출"
        C[keywords.py]
        C1[제목 토큰화<br/>공백 기반 n-gram]
        C2[불용어 제거<br/>한국어/영어]
        C3[빈도 집계<br/>Counter.title_words]
    end

    subgraph "상관관계 분석"
        D[correlation.py]
        D1[본문별 제목 클러스터링]
        D2[공통 키워드 추출<br/>TF-IDF 기반]
        D3[본문-키워드 행렬<br/>sparse matrix]
    end

    subgraph "중심 진리 매핑"
        E[central_themes.py]
        E1[본문별 제목 그룹화]
        E2[반복 단어/구 추출]
        E3[신학 주제 라벨링<br/>수동 매핑 테이블]
    end

    subgraph "출력"
        F[frequency_by_book.json]
        G[frequency_by_chapter.json]
        H[keywords.json]
        I[correlation.json]
        J[central_themes.json]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    B --> B1
    B1 --> F
    B --> B2
    B2 --> G
    C --> C1
    C1 --> C2
    C2 --> C3
    C3 --> H
    D --> D1
    D1 --> D2
    D2 --> D3
    D3 --> I
    E --> E1
    E1 --> E2
    E2 --> E3
    E3 --> J
```

---

## 5. 대시보드 시각화 흐름

```mermaid
flowchart LR
    subgraph "대시보드 입력"
        A[statistics/*.json<br/>5개 통계 파일]
    end

    subgraph "Streamlit 앱"
        B[app.py<br/>Streamlit 메인]
        B1[권별 필터<br/>multiselect]
        B2[장별 필터<br/>slider]
        B3[키워드 필터<br/>text_input]
        B4[기간 필터<br/>date_range]
    end

    subgraph "차트 렌더링"
        C[charts.py<br/>Plotly 차트 생성]
        C1[막대 차트<br/>권별 빈도]
        C2[히트맵<br/>장별 × 키워드]
        C3[산점도<br/>본문-키워드 상관관계]
        C4[네트워크 그래프<br/>주제 연결성]
    end

    subgraph "출력"
        D[interactive dashboard<br/>localhost:8501]
        E[dashboard_report.json<br/>최종 통계 내보내기]
    end

    A --> B
    B --> B1
    B --> B2
    B --> B3
    B --> B4
    B1 --> C
    B2 --> C
    B3 --> C
    B4 --> C
    C --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> D
    C --> E
```

---

## 6. 전체 실행 흐름 (End-to-End)

```mermaid
flowchart TB
    subgraph "1. 설정"
        A1[config/*.yml<br/>성경 약어 + 출처 정책]
        A2[requirements.txt<br/>의존성 설치]
    end

    subgraph "2. 데이터 수집"
        B1[scripts/collect_all.py 실행]
        B2[robots.txt 확인<br/>rate limiting 적용]
        B3[출처별 URL 큐 처리<br/>sermonbank, youtube, publication]
        B4[원본 JSONL 저장<br/>raw/*.jsonl]
    end

    subgraph "3. 정규화"
        C1[scripts/build_corpus.py 실행]
        C2[본문 참조 파싱<br/>한국어 → OSIS]
        C3[Pydantic 검증<br/>SermonRecord]
        C4[중복 제거<br/>dedupe_key]
        C5[정규화 JSONL 저장<br/>normalized/corpus.jsonl]
    end

    subgraph "4. 통계 분석"
        D1[scripts/compute_statistics.py 실행]
        D2[빈도 분석<br/>frequency.py]
        D3[키워드 추출<br/>keywords.py]
        D4[상관관계 분석<br/>correlation.py]
        D5[중심 진리 매핑<br/>central_themes.py]
    end

    subgraph "5. 대시보드 실행"
        E1[sermon_corpus/dashboard/app.py 실행]
        E2[Streamlit 서버 시작<br/>localhost:8501]
        E3[통계 데이터 로드<br/>JSON 파일 읽기]
        E4[Plotly 차트 렌더링<br/>막대/히트맵/산점도]
    end

    subgraph "6. 출력"
        F1[interactive dashboard<br/>http://localhost:8501]
        F2[dashboard_report.json<br/>최종 통계 내보내기]
        F3[시각화 PNG/PDF<br/>보고서용]
    end

    A1 --> B1
    A2 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    D5 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> F1
    E4 --> F2
    E4 --> F3
```

---

## 7. 핵심 클래스 관계도

```mermaid
classDiagram
    class PoliteFetcher {
        +str user_agent
        +float min_delay
        +float max_delay
        +dict robots_cache
        +can_fetch(base_url, url) bool
        +get(url) str|None
        -_load_robots(base_url) void
    }

    class SourceAdapter {
        <<interface>>
        +parse(html) list~SermonRecord~
        +get_next_url() str|None
    }

    class SermonBankAdapter {
        +parse(html) list~SermonRecord~
        +get_next_url() str|None
    }

    class YouTubeAdapter {
        +fetch_metadata(api_key, channel_id) list~SermonRecord~
        +parse_response(json) list~SermonRecord~
    }

    class BibleReferenceParser {
        +dict BOOK_ALIASES
        +parse(raw) Passage
        +resolve_book(ko_name) str
        +parse_chapter_verse(ref) tuple
    }

    class DeduplicationEngine {
        +str generate_dedupe_key(title, passage)
        +bool is_duplicate(record_id)
        +add_to_index(record_id) void
    }

    class FrequencyAnalyzer {
        +frequency_by_book(records) dict
        +frequency_by_chapter(records) dict
    }

    class KeywordExtractor {
        +extract_keywords(titles) dict
        +remove_stopwords(words) list
        +compute_tf(words) dict
    }

    class CorrelationAnalyzer {
        +title_passage_correlation(records) dict
        +compute_tfidf(documents) sparse_matrix
        +find_top_terms(passage, n) list
    }

    class CentralThemesMapper {
        +map_themes_by_passage(records) dict
        +manual_label_mapping() dict
        +cluster_titles(titles) list
    }

    class SermonRecord {
        +str record_id
        +str source
        +str source_url
        +str title
        +str passage_raw
        +str passage_osis
        +str bible_book
        +int chapter_start
        +int chapter_end
        +int|None verse_start
        +int|None verse_end
        +str|None preacher
        +str|None published_date
        +str quality_status
        +str dedupe_key
    }

    class Passage {
        +str osis
        +str bible_book
        +int chapter_start
        +int chapter_end
        +int|None verse_start
        +int|None verse_end
    }

    PoliteFetcher --> SourceAdapter : 사용
    SourceAdapter <|-- SermonBankAdapter : 구현
    SourceAdapter <|-- YouTubeAdapter : 구현
    SermonBankAdapter --> BibleReferenceParser : 본문 파싱
    YouTubeAdapter --> BibleReferenceParser : 본문 파싱
    BibleReferenceParser --> Passage : 생성
    SermonRecord --> Passage : 포함
    DeduplicationEngine --> SermonRecord : 검사/저장
    FrequencyAnalyzer --> SermonRecord : 분석
    KeywordExtractor --> SermonRecord : 분석
    CorrelationAnalyzer --> SermonRecord : 분석
    CentralThemesMapper --> SermonRecord : 분석
```

---

## 8. 데이터 흐름 요약

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  데이터 출처  │ ──▶ │  수집 계층    │ ──▶ │ 정규화 계층    │
│             │     │              │     │               │
│ 설교은행     │     │ PoliteFetcher│     │ 본문 참조 파서 │
│ 유튜브       │     │ Source Adpt  │     │ Pydantic 검증 │
│ 출판 설교집  │     │ robots.txt   │     │ 중복 제거     │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                                                  ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  시각화 계층 │ ◀── │ 통계 분석 계층 │ ◀── │ 저장 계층     │
│             │     │              │     │               │
│ Streamlit   │     │ 빈도 분석    │     │ 원본 JSONL    │
│ Plotly 차트 │     │ 키워드 추출  │     │ 정규화 JSONL  │
│ 대시보드    │     │ 상관관계 분석│     │ SQLite 상태   │
└─────────────┘     └──────────────┘     └───────────────┘
```

---

*플로우차트 작성일: 2026-07-22*
*버전: 1.0*