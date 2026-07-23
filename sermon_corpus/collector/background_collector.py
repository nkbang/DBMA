#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 백그라운드 데이터 수집기
============================================

별도 프로세스에서 데이터를 수집하고 JSONL 파일에 저장합니다.
대시보드는 이 파일을 읽어서 최신 데이터를 표시합니다.

사용법:
    # 수동 실행
    python scripts/background_collector.py [--interval SECONDS]
    
    # 데몬 모드 (지속적 실행)
    python scripts/background_collector.py --daemon
    
    # systemd 서비스로 등록 (예시)
    systemctl start sermon-collector

데이터 저장 위치:
    sermon_corpus/data/collected_sermons.jsonl

수집 소스:
    - sources.yml에 configured된 모든 출처
"""

import sys
import os
import json
import time
import signal
import threading
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, date

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml
from sermon_corpus.collector.polite_fetcher import PoliteFetcher
from sermon_corpus.collector.sermonbank import SermonBankCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent.parent / "data" / "collector.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("background_collector")


# ============================================================
# 데이터 저장소
# ============================================================

class DataStore:
    """수집된 데이터를 JSONL 파일에 저장하고 읽습니다."""
    
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = str(Path(__file__).parent.parent / "data" / "collected_sermons.jsonl")
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일이 없으면 빈 파일 생성
        if not self.data_path.exists():
            self.data_path.touch()
    
    def save_records(self, records: List[dict]) -> int:
        """레코드를 JSONL 파일에 추가 저장합니다.
        
        중복 체크 후 새 데이터만 추가합니다.
        
        Returns:
            저장된 건수
        """
        if not records:
            return 0
        
        # 기존 데이터 읽기 (중복 체크용)
        existing_keys = set()
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            key = (
                                str(rec.get("title", "")).strip().lower(),
                                str(rec.get("passage_raw", "")).strip().lower(),
                            )
                            existing_keys.add(key)
                        except json.JSONDecodeError:
                            continue
        
        # [버그 수정] collect_from_source()가 반환하는 records는
        # SermonRecord 데이터클래스 인스턴스라 .get()이 없어 여기서
        # 항상 AttributeError로 죽었다(self.running 버그에 가려 이
        # 코드 경로가 실제로 실행된 적이 없었음) — dict로 변환 후 처리.
        new_records = []
        for rec in records:
            rec_dict = rec.to_dict() if hasattr(rec, "to_dict") else rec
            key = (
                str(rec_dict.get("title", "")).strip().lower(),
                str(rec_dict.get("passage_raw", "")).strip().lower(),
            )
            if key not in existing_keys:
                new_records.append(rec_dict)
                existing_keys.add(key)
        
        # 새 데이터 추가 저장 (append 모드)
        if new_records:
            with open(self.data_path, "a", encoding="utf-8") as f:
                for rec in new_records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            
            logger.info(f"{len(new_records)}건의 새 데이터 추가 저장 (총 {self.count()}건)")
        
        return len(new_records)
    
    def load_records(self) -> List[dict]:
        """저장소에서 모든 데이터를 로드합니다."""
        if not self.data_path.exists():
            return []
        
        records = []
        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records
    
    def count(self) -> int:
        """저장된 데이터 건수를 반환합니다."""
        return sum(1 for _ in open(self.data_path, "r", encoding="utf-8")) if self.data_path.exists() else 0
    
    def get_stats(self) -> Dict:
        """데이터 저장소 통계를 반환합니다."""
        return {
            "total_records": self.count(),
            "file_size_bytes": self.data_path.stat().st_size if self.data_path.exists() else 0,
            "last_modified": datetime.fromtimestamp(self.data_path.stat().st_mtime).isoformat() if self.data_path.exists() else None,
        }


# ============================================================
# 백그라운드 수집기
# ============================================================

class BackgroundCollector:
    """백그라운드에서 데이터를 지속적으로 수집합니다."""
    
    def __init__(self, config_path: Optional[str] = None, data_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config" / "sources.yml"
        self.data_store = DataStore(data_path)
        self.config = self._load_config()
        self.running = False
        self.stats = {
            "total_collected": 0,
            "total_saved": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "last_run": None,
            "runs": 0,
        }
        
        # [버그 수정] signal.signal()은 메인 스레드에서만 등록 가능한데
        # Streamlit은 각 세션의 스크립트를 별도 워커 스레드에서 실행한다
        # — 대시보드의 "수동 데이터 수집 실행" 버튼에서 BackgroundCollector()
        # 를 생성하면 여기서 "signal only works in main thread of the
        # main interpreter" ValueError가 나서 수집이 전혀 안 됐다.
        # CLI(--once/--daemon)는 메인 스레드라 그대로 동작하도록,
        # 메인 스레드일 때만 정지 신호를 등록한다.
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _load_config(self) -> Dict:
        """설정 파일을 로드합니다."""
        if not self.config_path.exists():
            logger.warning(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {}
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def _handle_signal(self, signum, frame):
        """정지 신호를 처리합니다."""
        logger.info(f"신호 {signum} 수신. 수집기를 안전하게 중단합니다.")
        self.running = False
    
    def collect_from_source(self, source_id: str) -> List[Any]:
        """특정 출처에서 데이터를 수집합니다."""
        sources = self.config.get("sources", {})
        source_config = sources.get(source_id, {})

        if not source_config:
            logger.warning(f"출처 설정을 찾을 수 없습니다: {source_id}")
            return []

        limits = source_config.get("limits", {})
        default_policy = self.config.get("default_policy", {})

        # [버그 수정] 이 함수가 source_id와 무관하게 항상
        # SermonBankCollector만 생성했다 — sources.yml에 youtube가
        # mode: api_public_metadata로 따로 등록돼 있어도 실제로는
        # 절대 YouTubeSermonCollector가 쓰이지 않고, urls가 없는 youtube
        # 설정은 항상 "URL이 설정되지 않은 출처"로 스킵됐다.
        # mode로 실제 수집기를 분기하도록 수정.
        if source_config.get("mode") == "api_public_metadata":
            return self._collect_from_youtube(source_id, source_config, limits)

        urls = source_config.get("urls", [])
        if not urls:
            logger.warning(f"URL이 설정되지 않은 출처: {source_id}")
            return []

        fetcher = PoliteFetcher(
            user_agent=default_policy.get("user_agent", "DBMA-SermonCorpus/0.1 (academic research)"),
            min_delay=limits.get("min_delay_seconds", 5.0),
            max_delay=limits.get("max_delay_seconds", 12.0),
            max_retries=default_policy.get("retry", {}).get("max_attempts", 2),
        )

        # SermonBankCollector 설정
        collector = SermonBankCollector({
            "source_id": source_id,
            "urls": urls,
            "storage": {"raw_path": str(self.data_store.data_path)},
        })

        try:
            records = collector.collect_all(
                fetcher, max_records=1000, max_pages=limits.get("max_pages", 10)
            )
            self.stats["total_collected"] += len(records)
            logger.info(f"{source_id}: {len(records)}건 수집 완료")
            return records
        except Exception as e:
            self.stats["total_errors"] += 1
            logger.error(f"{source_id} 수집 오류: {e}")
            return []

    def _collect_from_youtube(self, source_id: str, source_config: Dict, limits: Dict) -> List[Any]:
        """YouTube Data API로 대형교회 채널의 설교 영상 메타데이터를 수집합니다."""
        from sermon_corpus.collector.youtube import YouTubeSermonCollector

        collector = YouTubeSermonCollector({
            "source_id": source_id,
            "channels": source_config.get("channels"),
            "search_keywords": source_config.get("search_keywords"),
            "api_key_env": source_config.get("api_key_env", "YOUTUBE_API_KEY"),
            "storage": {"raw_path": str(self.data_store.data_path)},
            "max_results_per_channel": limits.get("max_results_per_channel", 50),
            "delay_between_requests": limits.get("min_delay_seconds", 1.5),
        })

        if not collector.api_key:
            logger.warning(
                f"{source_id}: {source_config.get('api_key_env', 'YOUTUBE_API_KEY')} "
                "환경변수가 설정되지 않아 API 키 없이 검색 폴백으로만 수집합니다."
            )

        try:
            records = collector.collect_all()
            self.stats["total_collected"] += len(records)
            logger.info(f"{source_id}: {len(records)}건 수집 완료")
            return records
        except Exception as e:
            self.stats["total_errors"] += 1
            logger.error(f"{source_id} 수집 오류: {e}")
            return []
    
    def run_once(self) -> Dict:
        """한 번의 수집 사이클을 실행합니다."""
        logger.info("수집 사이클 시작...")

        # [버그 수정] self.running은 __init__에서 False로 시작하고
        # run_daemon()에서만 True로 바뀌었다 — --daemon 없이 run_once()를
        # 직접 호출하면(--once, 기본 실행, 대시보드 수동 수집 버튼 등)
        # 아래 루프의 "if not self.running: break"가 첫 출처에서 바로
        # 걸려 아무것도 수집하지 않고 "0건 완료"로 조용히 끝났다.
        # run_daemon()이 반복 호출 중 Ctrl+C로 중단시키는 용도로 이
        # 플래그를 계속 쓰므로, 여기서는 시작 시 한 번만 True로 켠다.
        self.running = True

        all_records = []
        sources = self.config.get("sources", {})

        for source_id, source_config in sources.items():
            if not self.running:
                break

            if not source_config.get("enabled", True):
                logger.info(f"{source_id}: enabled=false, 건너뜀")
                continue

            logger.info(f"{source_id}에서 데이터 수집 중...")
            records = self.collect_from_source(source_id)

            if records:
                # 새 데이터만 저장
                saved = self.data_store.save_records(records)
                duplicates = len(records) - saved
                self.stats["total_saved"] += saved
                self.stats["total_duplicates"] += duplicates
                all_records.extend(records)
        
        self.stats["last_run"] = datetime.now().isoformat()
        self.stats["runs"] += 1
        
        logger.info(
            f"수집 사이클 완료: {len(all_records)}건 수집, "
            f"{self.stats['total_saved']}건 저장, "
            f"{self.stats['total_duplicates']}건 중복, "
            f"총 {self.data_store.count()}건"
        )
        
        return self.get_stats()
    
    def run_daemon(self, interval: int = 3600) -> None:
        """데몬 모드로 지속적으로 실행합니다."""
        self.running = True
        logger.info(f"데몬 모드 시작 (간격: {interval}초)")
        logger.info("중단하려면 Ctrl+C를 누르세요.")
        
        while self.running:
            try:
                self.run_once()
                
                # 다음 수집까지 대기
                logger.info(f"다음 수집까지 {interval}초 대기...")
                for i in range(interval, 0, -1):
                    if not self.running:
                        break
                    if i % 60 == 0:  # 60초마다 진행률 출력
                        logger.info(f"대기 중... {i // 60}분 남음")
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"데몬 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기
        
        logger.info("데몬 수집기 중단됨")
    
    def get_stats(self) -> Dict:
        """수집기 통계를 반환합니다."""
        stats = self.stats.copy()
        stats["data_store"] = self.data_store.get_stats()
        return stats
    
    def print_status(self) -> None:
        """현재 상태를 콘솔에 출력합니다."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("백그라운드 수집기 상태")
        print("=" * 60)
        print(f"총 수집 건수: {stats['total_collected']}")
        print(f"총 저장 건수: {stats['total_saved']}")
        print(f"총 중복 건수: {stats['total_duplicates']}")
        print(f"총 오류 건수: {stats['total_errors']}")
        print(f"실행 횟수: {stats['runs']}")
        print(f"마지막 실행: {stats['last_run'] or '아직 없음'}")
        print("-" * 40)
        print(f"저장된 데이터 건수: {stats['data_store']['total_records']}")
        print(f"파일 크기: {stats['data_store']['file_size_bytes']:,} bytes")
        print(f"마지막 수정: {stats['data_store']['last_modified']}")
        print("=" * 60)


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="백그라운드 설교 데이터 수집기")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="데몬 모드로 실행 (지속적)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="데몬 모드 수집 간격 (초, 기본값: 3600)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="설정 파일 경로",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="데이터 저장 파일 경로",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="현재 상태 출력 후 종료",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="한 번만 실행 후 종료",
    )
    
    args = parser.parse_args()
    
    collector = BackgroundCollector(
        config_path=args.config,
        data_path=args.data,
    )
    
    if args.status:
        collector.print_status()
        return
    
    if args.daemon:
        print("백그라운드 수집기 시작...")
        collector.print_status()
        collector.run_daemon(interval=args.interval)
    elif args.once:
        print("한 번의 수집 실행...")
        collector.run_once()
        collector.print_status()
    else:
        # 기본: 한 번 실행
        print("수집기 실행 중... (Ctrl+C로 종료)")
        collector.run_once()
        collector.print_status()


if __name__ == "__main__":
    main()