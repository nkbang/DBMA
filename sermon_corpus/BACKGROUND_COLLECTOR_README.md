# 백그라운드 데이터 수집기

## 개요

백그라운드 데이터 수집기는 별도 프로세스에서 데이터를 수집하고 JSONL 파일에 저장합니다.
대시보드는 이 파일을 읽어서 최신 데이터를 표시합니다.

## 아키텍처

```
┌─────────────────────┐         ┌──────────────────────┐
│  Background          │         │  Streamlit Dashboard │
│  Collector           │────────▶│                      │
│  (Daemon/Manual)     │  JSONL  │  (Real-time Display)│
└─────────────────────┘         └──────────────────────┘
         │
         ▼
┌──────────────────────┐
│  sources.yml         │
│  (Data Sources)      │
└──────────────────────┘
```

## 설치 및 실행

### 1. 수동 실행 (한 번)

```bash
cd ~/DBMA
source ~/envs/dbma311/bin/activate
python scripts/background_collector.py
```

### 2. 데몬 모드 (지속적 실행)

```bash
# 기본: 5분 간격
python scripts/background_collector.py --daemon

# 1분 간격 (실시간성 높임)
python scripts/background_collector.py --daemon --interval 60

# 10분 간격
python scripts/background_collector.py --daemon --interval 600

# 30분 간격
python scripts/background_collector.py --daemon --interval 1800
```

### 3. 현재 상태 확인

```bash
python scripts/background_collector.py --status
```

### 4. 한 번만 실행

```bash
python scripts/background_collector.py --once
```

## 데이터 저장 위치

- **저장 파일**: `sermon_corpus/data/collected_sermons.jsonl`
- **로그 파일**: `sermon_corpus/data/collector.log`

## 수집 소스 설정

`sermon_corpus/config/sources.yml` 파일에서 수집 대상을 설정할 수 있습니다.

```yaml
sources:
  sermonbank:
    urls:
      - "https://sermonbank.net/sermons"
    limits:
      min_delay_seconds: 5.0
      max_delay_seconds: 12.0
```

## 대시보드 연동

Streamlit 대시보드 하단에 다음 정보가 표시됩니다:

- **총 데이터 건수**: 수집된 전체 설교 수
- **파일 크기**: JSONL 파일 크기
- **마지막 수정**: 마지막 데이터 수집 시간
- **수동 수집 버튼**: 수동으로 데이터 수집 실행

## 시스템드 서비스로 등록 (선택사항)

### systemd 서비스 파일 생성

```bash
cat > ~/.config/systemd/user/sermon-collector.service << 'EOF'
[Unit]
Description=DBMA Sermon Background Collector
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /Users/David/DBMA/scripts/background_collector.py --daemon --interval 300
WorkingDirectory=/Users/David/DBMA
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# 서비스 시작
systemctl --user daemon-reload
systemctl --user start sermon-collector
systemctl --user enable sermon-collector
```

## cron으로 자동화 (선택사항)

```bash
# 매시간 실행
0 * * * * cd ~/DBMA && source ~/envs/dbma311/bin/activate && python scripts/background_collector.py --once >> sermon_corpus/data/cron.log 2>&1
```

## 데이터 스키마

각 레코드는 다음 필드를 포함합니다:

```json
{
  "record_id": "sermonbank_abc123",
  "passage_raw": "창세기 1장 1절",
  "bible_book": "Genesis",
  "chapter_start": 1,
  "chapter_end": 1,
  "title": "초림의 은혜",
  "preacher": "목사 이름",
  "church": "교회 이름",
  "published_date": "2024-01-15",
  "source_url": "https://sermonbank.net/sermons/abc123",
  "collected_at": "2026-07-22T15:30:00"
}
```

## 중복 제거

- **중복 조건**: `title` + `passage_raw` 가 동일한 경우
- **제거 방식**: 새 데이터만 JSONL 파일에 추가 (append 모드)

## 로그 확인

```bash
# 실시간 로그 모니터링
tail -f sermon_corpus/data/collector.log

# 최근 50줄
tail -n 50 sermon_corpus/data/collector.log
```

## 문제 해결

### 데이터가 수집되지 않을 때

1. `sources.yml` 설정 확인
2. 네트워크 연결 확인
3. 로그 파일 확인: `sermon_corpus/data/collector.log`

### 포트가 사용 중일 때

```bash
# 사용 중인 포트 확인
lsof -i :8502

# 다른 포트 사용
streamlit run sermon_corpus/dashboard/web_app.py --server.port 8503
```

## 파일 구조

```
sermon_corpus/
├── collector/
│   ├── __init__.py
│   ├── background_collector.py    # 핵심 수집 모듈
│   ├── polite_fetcher.py           # 정중한 웹 크롤러
│   └── sermonbank.py               # 설교은행 수집기
├── data/
│   ├── collected_sermons.jsonl     # 수집 데이터 저장소
│   └── collector.log               # 수집 로그
├── config/
│   └── sources.yml                 # 데이터 소스 설정
scripts/
└── background_collector.py         # 실행 스크립트