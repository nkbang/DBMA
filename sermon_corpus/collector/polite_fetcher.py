# DBMA Sermon Corpus - Polite Fetcher
# robots.txt 준수, rate limiting, 재시도 규칙이 적용된 HTTP 클라이언트

import time
import random
import hashlib
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin
from typing import Optional, Dict, Set
import httpx


class PoliteFetcher:
    """
    예의 바른 웹 수집기.
    
    - robots.txt 준수
    - rate limiting (min_delay ~ max_delay 랜덤 대기)
    - 재시도 규칙 (exponential backoff)
    - 차단 신호 감지 (429, 403, CAPTCHA)
    """
    
    def __init__(
        self,
        user_agent: str = "DBMA-SermonCorpus/0.1 (academic research)",
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        max_retries: int = 2,
        timeout: float = 30.0,
    ):
        self.user_agent = user_agent
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.timeout = timeout
        
        # robots.txt 캐시: {base_url: RobotFileParser}
        self._robots_cache: Dict[str, RobotFileParser] = {}
        
        # 통계
        self.stats = {
            "requests_total": 0,
            "requests_200": 0,
            "requests_429": 0,
            "requests_403": 0,
            "robots_denied": 0,
            "errors": 0,
        }
    
    def can_fetch(self, url: str) -> bool:
        """robots.txt가 URL 수집을 허용하는지 확인"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if base_url not in self._robots_cache:
            self._load_robots(base_url)
        
        rp = self._robots_cache.get(base_url)
        if rp is None:
            return True  # robots.txt 없으면 허용
        
        return rp.can_fetch(self.user_agent, url)
    
    def _load_robots(self, base_url: str) -> None:
        """robots.txt 로드 및 캐시"""
        if base_url in self._robots_cache:
            return
        
        robots_url = f"{base_url}/robots.txt"
        rp = RobotFileParser()
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(robots_url, follow_redirects=True)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    # robots.txt 없음 또는 오류 → 모두 허용
                    rp.parse([])
        except Exception:
            # 네트워크 오류 → 모두 허용
            rp.parse([])
        
        self._robots_cache[base_url] = rp
    
    def _wait(self) -> None:
        """rate limiting을 위한 대기"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    def get(
        self,
        url: str,
        allowed_codes: Set[int] | None = None
    ) -> Optional[httpx.Response]:
        """
        URL에서 HTML 응답을 가져옵니다.
        
        - robots.txt 검사
        - rate limiting
        - 재시도 (exponential backoff)
        - 차단 신호 감지
        
        Returns:
            httpx.Response if successful, None otherwise
        """
        if allowed_codes is None:
            allowed_codes = {200}
        
        # robots.txt 검사
        if not self.can_fetch(url):
            self.stats["robots_denied"] += 1
            return None
        
        # 재시도 루프
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                self._wait()
                self.stats["requests_total"] += 1
                
                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    resp = client.get(url)
                    
                    # 통계 업데이트
                    if resp.status_code == 200:
                        self.stats["requests_200"] += 1
                    elif resp.status_code == 429:
                        self.stats["requests_429"] += 1
                        # Retry-After 헤더 존중
                        retry_after = resp.headers.get("retry-after")
                        if retry_after:
                            time.sleep(int(retry_after))
                        else:
                            time.sleep(60)
                        continue  # 재시도
                    
                    if resp.status_code in allowed_codes:
                        return resp
                    elif resp.status_code in (401, 403, 451):
                        self.stats["requests_403"] += 1
                        return resp  # 차단 신호 (호출자가 처리)
                    elif resp.status_code >= 500:
                        self.stats["errors"] += 1
                        # 서버 오류 → 재시도
                        if attempt < self.max_retries:
                            backoff = min(2 ** attempt, 30)
                            time.sleep(backoff)
                            continue
                    
                    return resp
            
            except httpx.TimeoutException:
                last_exception = "timeout"
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
            except httpx.RequestError:
                last_exception = "request_error"
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
            except Exception:
                last_exception = "unknown"
                break
        
        self.stats["errors"] += 1
        return None
    
    def get_text(self, url: str) -> Optional[str]:
        """URL에서 텍스트 응답을 가져옵니다 (간편 메서드)"""
        resp = self.get(url)
        if resp and resp.status_code == 200:
            return resp.text
        return None
    
    def get_stats(self) -> Dict:
        """수집 통계 반환"""
        return dict(self.stats)