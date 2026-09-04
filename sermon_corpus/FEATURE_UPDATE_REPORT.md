# 설교 대시보드 기능 업데이트 보고서

## 업데이트 개요

**날짜**: 2026. 07. 22.  
**버전**: v1.3.0  
**수정 파일**: 
- `sermon_corpus/dashboard/web_app.py` (Streamlit 대시보드)
- `sermon_corpus/dashboard/sermon_dashboard.html` (HTML 대시보드)

---

## 추가된 기능

### 1. 다양한 파일 형식 지원

#### 지원되는 형식
| 형식 | 확장자 | 설명 |
|------|--------|------|
| JSONL | `.jsonl`, `.json` | 한 줄당 JSON 객체 |
| CSV | `.csv` | 콤마 구분자 |
| TSV | `.tsv` | 탭 구분자 |
| TXT | `.txt` | TSV로 간주 |
| 엑셀 | `.xlsx`, `.xls` | openpyxl 엔진 (Streamlit만) |
| SQLite | `.db`, `.sqlite`, `.sqlite3` | 첫 번째 테이블 사용 (Streamlit만) |

#### Streamlit 대시보드
- `load_data()` 함수가 모든 형식 지원
- 파일 업로드 UI 제공
- 자동 필드 감지 (bible_book, chapter, title 등)

#### HTML 대시보드
- JSONL/CSV/TXT 파일 업로드 지원
- 엑셀/SQLite는 별도 라이브러리 필요 안내

### 2. 중복 데이터 제거

#### 중복 조건
- `title` + `passage_raw` 가 동일한 경우
- 대소문자 무시 (lowercase)
- 양쪽 공백 제거 (strip)

#### 구현
```python
# Streamlit
def deduplicate_records(records):
    seen = set()
    unique_records = []
    for record in records:
        key = (record.get("title", "").strip().lower(),
               record.get("passage_raw", "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
    return unique_records
```

```javascript
// HTML
function deduplicateRecords(records) {
    const seen = new Set();
    for (const record of records) {
        key = `${title}|||${passage}`;
        if (!seen.has(key)) seen.add(key);
    }
    return unique;
}
```

### 3. 진행률 표시

#### Streamlit
- `ProgressState` 데이터클래스
- `st.progress()` 위젯
- 파일 처리 단계별 메시지 업데이트

```python
@dataclass
class ProgressState:
    current: int = 0
    total: int = 0
    message: str = ""
    
    @property
    def percentage(self) -> float:
        return min(100.0, (self.current / self.total) * 100)
```

#### HTML
- `updateProgress()` 함수
- 진행률 바 업데이트 (미구현 - UI 요소 추가 필요)

---

## 사용법

### Streamlit 대시보드

```bash
# 파일 업로드 방식 (권장)
streamlit run sermon_corpus/dashboard/web_app.py

# 명령줄 인자 방식
streamlit run sermon_corpus/dashboard/web_app.py --data data/sermonbank.jsonl
```

### HTML 대시보드

```bash
# 로컬 서버 실행
cd sermon_corpus/dashboard
python -m http.server 8080

# 브라우저에서 접속
open http://localhost:8080/sermon_dashboard.html
```

---

## 기술적 고려사항

### 필드 자동 감지
- 다양한 필드명 패턴 지원 (bible_book, BibleBook, 성경책 등)
- CSV 헤더에서 패턴 매칭으로 표준 형식 변환

### 연도/연대 계산
- `published_date` 또는 `date` 필드에서 추출
- 형식: `%Y-%m-%d`, `%Y/%m/%d`, `%Y.%m.%d`, `%Y`

### XSS 방지 (HTML)
- `escapeHtml()` 함수로 사용자 입력 이스케이프

---

## 제한사항

1. **엑셀 파일**: Streamlit만 지원 (pandas + openpyxl)
2. **SQLite 파일**: Streamlit만 지원 (sqlite3 모듈)
3. **HTML 대시보드**: JSONL/CSV/TXT만 지원
4. **대규모 데이터**: HTML은 브라우저 메모리 제한 있음 (권장: 10,000건 이하)

---

## 테스트 방법

```bash
# Streamlit 테스트
streamlit run sermon_corpus/dashboard/web_app.py --data sermon_corpus/data/sample_sermons.csv

# HTML 테스트
cd sermon_corpus/dashboard
python -m http.server 8080
# open http://localhost:8080/sermon_dashboard.html
```

---

## 향후 개선 사항

1. 엑셀 파일 업로드 지원 (HTML)
2. SQLite 쿼리 UI (HTML)
3. 진행률 바 UI 완성 (HTML)
4. 대용량 데이터 처리 (페이징/웹워크어)
5. 필터 기능 강화 (연도 범위, 설교자 등)

---

## 완료 항목 체크리스트

- [x] 다양한 파일 형식 지원 (XLSX, TXT, SQLite) - Streamlit
- [x] 중복 데이터 제거 (제목+본문 기준) - Streamlit
- [x] 진행률 표시 기능 - Streamlit
- [x] 중복 데이터 제거 - HTML
- [x] 파일 업로드 안내 UI 개선 - HTML
- [x] 작업 기록 및 보고서 작성