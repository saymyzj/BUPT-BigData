import random
import threading
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests


class AntiCrawlerBlocked(RuntimeError):
    """当网站返回明确反爬信号时抛出该异常。"""


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    elapsed_seconds: float


class DomainRateLimiter:
    """按域名单独限速，同时允许不同域名之间并行采集。"""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_at: dict[str, float] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def wait(self, url: str) -> None:
        domain = urlparse(url).netloc
        with self._global_lock:
            lock = self._locks.setdefault(domain, threading.Lock())

        with lock:
            now = time.monotonic()
            last_at = self._last_request_at.get(domain)
            if last_at is not None:
                min_wait = random.uniform(self.min_delay, self.max_delay)
                sleep_seconds = max(0.0, min_wait - (now - last_at))
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            self._last_request_at[domain] = time.monotonic()


class HttpClient:
    """带重试、超时、请求头和按域名限速能力的 HTTP 客户端。"""

    def __init__(
        self,
        *,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        timeout: float = 20.0,
        max_retries: int = 2,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = DomainRateLimiter(min_delay=min_delay, max_delay=max_delay)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )

    def fetch(self, url: str, referer: Optional[str] = None) -> FetchResult:
        headers = {"Referer": referer} if referer else None
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait(url)
            started_at = time.monotonic()
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                elapsed = time.monotonic() - started_at
                if response.status_code in {403, 429}:
                    raise AntiCrawlerBlocked(
                        f"blocked by server: status={response.status_code}, url={url}"
                    )
                response.raise_for_status()
                return FetchResult(
                    url=url,
                    status_code=response.status_code,
                    content=response.content,
                    content_type=response.headers.get("Content-Type", ""),
                    elapsed_seconds=elapsed,
                )
            except AntiCrawlerBlocked:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt + random.uniform(0.2, 1.0))

        raise RuntimeError(f"failed to fetch url after retries: {url}") from last_error
